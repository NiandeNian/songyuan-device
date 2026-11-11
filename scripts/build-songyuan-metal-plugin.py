#!/usr/bin/env python3
"""Build the production Metal bundle and Turnip library without a probe daemon."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/adreno-metal-plugin'
if OUT.exists():
    shutil.rmtree(OUT)
bundle = OUT / 'NativeAdrenoMetal.bundle'
bundle.mkdir(parents=True)
turnip = ROOT / 'build/mesa-tu-ios/src/freedreno/vulkan/libvulkan_freedreno.dylib'
if not turnip.is_file():
    raise SystemExit('Build Turnip first with build-turnip-darwin.py --target ios')
subprocess.run(['python3', ROOT / 'scripts/build-native-metal-bridge.py', '--target', 'ios'], check=True)
sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
exe = bundle / 'NativeAdrenoMetal'
subprocess.run(['xcrun', 'clang++', '-target', 'arm64-apple-ios17.0', '-isysroot', sdk,
                '-std=c++17', '-O2', '-fstack-protector-strong', '-fobjc-arc', '-Wall', '-Wextra', '-Werror',
                '-Wno-deprecated-declarations', '-bundle', '-I', ROOT / 'drivers/NativeMetal',
                '-I', ROOT / 'drivers/NativeMobileDisplay', '-I', ROOT / 'drivers/NativeAdreno',
                '-I', ROOT / '.cache/mesa-work/include', '-x', 'objective-c++',
                ROOT / 'kits/songyuan/SongyuanMetalPlugin.mm',
                ROOT / 'drivers/NativeMetal/NativeBridgeMetalFrontend.mm', '-x', 'none',
                ROOT / 'build/native-metal-bridge/ios/libnative_metal_bridge.a',
                '-Wl,-dead_strip', '-lobjc', '-framework', 'Foundation', '-framework', 'Metal',
                '-framework', 'IOSurface', '-o', exe], check=True)
subprocess.run(['strip', '-x', exe], check=True)
library = bundle / 'libvulkan_freedreno.dylib'
shutil.copyfile(turnip, library)
subprocess.run(['strip', '-x', library], check=True)
(bundle / 'Info.plist').write_bytes(plistlib.dumps(dict(
    CFBundleIdentifier='org.blu-sharky.NativeAdrenoMetal', CFBundleExecutable='NativeAdrenoMetal',
    CFBundlePackageType='BNDL', CFBundleVersion='1', CFBundleShortVersionString='1',
    NSPrincipalClass='NativeAdrenoMetalDevice', MinimumOSVersion='17.0')))

def sign(path, identifier):
    subprocess.run(['codesign', '--force', '--sign', '-', '--pagesize', '4096',
                    '--identifier', identifier, path], check=True)
    subprocess.run(['codesign', '--verify', '--strict', path], check=True)
    detail = subprocess.run(['codesign', '--display', '--verbose=4', path],
                            capture_output=True, text=True, check=True).stderr
    if not re.search(r'^Page size=4096$', detail, re.M):
        raise SystemExit('Signature page size differs')
    return re.search(r'^CDHash=([a-f0-9]{40})$', detail, re.M)[1]

turnip_hash = sign(library, 'org.blu-sharky.turnip')
plugin_hash = sign(bundle, 'org.blu-sharky.NativeAdrenoMetal')
(OUT / 'trust.json').write_text(json.dumps(dict(cdhash=plugin_hash, turnip_cdhash=turnip_hash,
    bundle=bundle.name, executable_bytes=exe.stat().st_size,
    source_sha256=hashlib.sha256((ROOT / 'kits/songyuan/SongyuanMetalPlugin.mm').read_bytes()).hexdigest(),
    purpose='production Metal discovery and GPU scanout; no diagnostic launchd jobs'), indent=2) + '\n')
print('PASS: production Metal bundle and Turnip built, signatures verified; no probe daemon')
