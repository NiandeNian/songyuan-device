// SPDX-License-Identifier: MIT
// Production Metal discovery and GPU scanout; no bring-up tests or diagnostic workers.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "NativeBridgeMetalFrontend.h"
#include "GpuScanoutPresenter.h"
#include "NativeGOPWire.h"

@interface _MTLDevice : NSObject
@end
@interface NativeAdrenoMetalDevice : _MTLDevice
- (id)initWithAcceleratorPort:(unsigned)port;
@end

namespace {
using Open = int (*)(unsigned, unsigned, uint32_t, unsigned *);
using Close = int (*)(unsigned);
using Map = int (*)(unsigned, uint32_t, unsigned, uint64_t *, uint64_t *, uint32_t);
using Unmap = int (*)(unsigned, uint32_t, unsigned, uint64_t);
using Retain = int (*)(unsigned);
using Release = int (*)(unsigned);
using RegistryID = int (*)(unsigned, uint64_t *);

static bool sibling(const char *name, char *path, size_t bytes) {
    Dl_info info = {};
    if (!dladdr((const void *)&sibling, &info) || !info.dli_fname) return false;
    const int size = snprintf(path, bytes, "%s", info.dli_fname);
    if (size < 0 || (size_t)size >= bytes) return false;
    char *slash = strrchr(path, '/');
    if (!slash) return false;
    *slash = 0;
    slash = strrchr(path, '/');
    if (!slash) return false;
    const size_t room = bytes - (size_t)(slash + 1 - path);
    const int n = snprintf(slash + 1, room, "%s", name);
    return n > 0 && (size_t)n < room && access(path, R_OK) == 0;
}

struct Scanout {
    id<MTLDevice> device;
    unsigned port, connection = 0;
    Open open;
    Close close;
    Map map;
    Unmap unmap;
    Release release;
    volatile uint32_t *mailbox = nullptr;
    uint64_t mailboxAddress = 0, scanoutAddress = 0;
    uint32_t sequence = 0;

    // The existing NativeAdreno mailbox ABI carries normal presenter requests.
    int call(uint32_t method, const void *input, size_t inBytes, void *output, size_t outBytes) {
        if (!mailbox || inBytes > 0x700 || outBytes > 0x700) return -1;
        if (inBytes) memcpy((void *)(mailbox + 0x10), input, inBytes);
        mailbox[3] = 0x7000 + method;
        mailbox[5] = (uint32_t)inBytes;
        mailbox[6] = (uint32_t)outBytes;
        __sync_synchronize();
        mailbox[1] = ++sequence;
        __sync_synchronize();
        for (unsigned i = 0; i < 6000 && mailbox[2] != sequence; ++i) usleep(500);
        if (mailbox[2] != sequence) return -2;
        __sync_synchronize();
        const int result = (int)mailbox[4];
        if (!result && outBytes) memcpy(output, (const void *)(mailbox + 0x200), outBytes);
        return result;
    }

    void serve() {
        if (open(port, mach_task_self(), 0x4148, &connection) || !connection) return;
        uint64_t length = 0;
        if (map(connection, 0xC0DE, mach_task_self(), &mailboxAddress, &length, 1) || length < 4096) return;
        mailbox = (volatile uint32_t *)(uintptr_t)mailboxAddress;
        if (mailbox[0] != 0x4d41494c) return;
        sequence = mailbox[1];
        NGPMode mode = {};
        if (call(NGP_METHOD_MODE, nullptr, 0, &mode, sizeof mode) || mode.version != NGP_VERSION ||
            mode.format != NGP_BGRX8888 || !mode.width || !mode.height || mode.stride < (uint64_t)mode.width * 4 ||
            mode.height > mode.bytes / mode.stride || mode.width > UINT32_MAX || mode.height > UINT32_MAX) return;
        if (map(connection, 0x5343, mach_task_self(), &scanoutAddress, &length, 0x101) || length < mode.bytes) return;
        const size_t page = (size_t)getpagesize();
        if (length < ((mode.bytes + page - 1) & ~(page - 1))) return;
        gpupresent::Presenter presenter(device, {(void *)(uintptr_t)scanoutAddress, (size_t)length,
                                                (size_t)mode.stride, (uint32_t)mode.width, (uint32_t)mode.height});
        if (!presenter.ready()) return;
        for (;;) {
            @autoreleasepool {
                NGPWait wait = {500};
                NGPSwap swap = {};
                const int result = call(NGP_METHOD_WAIT_SWAP, &wait, sizeof wait, &swap, sizeof swap);
                if ((unsigned)result == 0xe00002d6u) continue;
                if (result) return;
                uint32_t status = 0xe00002bcu;
                @try {
                    if (presenter.present({(const void *)(uintptr_t)swap.address,
                            (size_t)((swap.bytes + page - 1) & ~(page - 1)), (size_t)swap.stride,
                            swap.width, swap.height}) == gpupresent::kOk) status = 0;
                } @catch (NSException *) {}
                NGPComplete done = {swap.sequence, status, 0};
                if (call(NGP_METHOD_COMPLETE_SWAP, &done, sizeof done, nullptr, 0)) return;
            }
        }
    }
    ~Scanout() {
        if (scanoutAddress) unmap(connection, 0x5343, mach_task_self(), scanoutAddress);
        if (mailboxAddress) unmap(connection, 0xC0DE, mach_task_self(), mailboxAddress);
        if (connection) close(connection);
        release(port);
    }
};

static id makeDevice(unsigned port) {
    char loader[1024], marker[1024];
    if (!sibling("NativeAdrenoMetal.publish", marker, sizeof marker)) return nil;
    Dl_info info = {};
    if (!dladdr((const void *)&sibling, &info) || !info.dli_fname) return nil;
    const int size = snprintf(loader, sizeof loader, "%s", info.dli_fname);
    if (size < 0 || size >= (int)sizeof loader) return nil;
    char *slash = strrchr(loader, '/');
    if (!slash) return nil;
    const size_t room = sizeof loader - (size_t)(slash + 1 - loader);
    const int n = snprintf(slash + 1, room, "libvulkan_freedreno.dylib");
    if (n <= 0 || (size_t)n >= room || access(loader, R_OK)) return nil;
    void *iokit = dlopen("/System/Library/Frameworks/IOKit.framework/IOKit", RTLD_NOW | RTLD_LOCAL);
    if (!iokit) return nil;
    auto entryID = (RegistryID)dlsym(iokit, "IORegistryEntryGetRegistryEntryID");
    uint64_t registryID = 0;
    if (!entryID || entryID(port, &registryID)) return nil;
    CFPreferencesSetAppValue(CFSTR("CAEnableDeepFramebuffer"), kCFBooleanFalse, kCFPreferencesCurrentApplication);
    CFPreferencesSetAppValue(CFSTR("CAEnableFramebufferCompression"), kCFBooleanFalse, kCFPreferencesCurrentApplication);
    CFPreferencesSetAppValue(CFSTR("CAEnableIOSurfaceCompression"), kCFBooleanFalse, kCFPreferencesCurrentApplication);
    setenv("CA_DISABLE_FRAMEBUFFER_COMPRESSION", "1", 1);
    setenv("TU_DEBUG", "sysmem,nocb", 0);
    char cache[2][512] = {};
    confstr(_CS_DARWIN_USER_CACHE_DIR, cache[0], sizeof cache[0] - 16);
    confstr(_CS_DARWIN_USER_TEMP_DIR, cache[1], sizeof cache[1] - 16);
    id device = nil;
    for (auto &path : cache) {
        if (!path[0]) continue;
        strlcat(path, "m2v", sizeof path);
        if (mkdir(path, 0700) && access(path, W_OK)) continue;
        @try { device = native_bridge_metal_open(loader, path, registryID, nullptr); }
        @catch (NSException *) { device = nil; }
        if (device) break;
    }
    if (!device || strcmp(getprogname(), "backboardd")) return device;
    auto retain = (Retain)dlsym(iokit, "IOObjectRetain");
    auto open = (Open)dlsym(iokit, "IOServiceOpen");
    auto close = (Close)dlsym(iokit, "IOServiceClose");
    auto map = (Map)dlsym(iokit, "IOConnectMapMemory64");
    auto unmap = (Unmap)dlsym(iokit, "IOConnectUnmapMemory64");
    auto release = (Release)dlsym(iokit, "IOObjectRelease");
    if (!retain || !open || !close || !map || !unmap || !release || retain(port)) return device;
    Scanout *job = new Scanout{device, port, 0, open, close, map, unmap, release};
    pthread_attr_t attributes;
    pthread_attr_init(&attributes);
    pthread_attr_setdetachstate(&attributes, PTHREAD_CREATE_DETACHED);
    pthread_attr_setstacksize(&attributes, 1u << 20);
    pthread_t worker;
    if (pthread_create(&worker, &attributes, [](void *p) -> void * {
            Scanout *job = (Scanout *)p;
            @autoreleasepool { @try { job->serve(); } @catch (NSException *) {} }
            delete job;
            return nullptr;
        }, job)) delete job;
    pthread_attr_destroy(&attributes);
    return device;
}
}

@implementation NativeAdrenoMetalDevice
- (id)initWithAcceleratorPort:(unsigned)port {
    self = [super init];
    if (!self || !port) return nil;
    static id device;
    static bool attempted;
    @synchronized([NativeAdrenoMetalDevice class]) {
        if (!attempted) { attempted = true; device = makeDevice(port); }
        return device;
    }
}
@end
