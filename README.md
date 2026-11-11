# songyuan-device

UniXNU device sources for **Redmi K100 Pro Max** (`songyuan`, SM8850/Canoe),
adapted from [Typeun/myron-device](https://github.com/Typeun/myron-device).

The port uses this phone's captured base/live device trees: a 1200×2608 framebuffer,
FocalTech FT3683 on QUP4 SE0, IRQ GPIO 158, reset GPIO 66, AVDD GPIO 117, and
16 GB RAM. `scripts/data/songyuan-hardware.json` contains the measured public board
parameters; unique device identifiers and Android boot images are kept locally.

`Myron*` source and boot argument names are retained as the existing SM8850 driver
ABI. They are selected for songyuan with `myron-touch=5` and `myron-gpu=11`, both
normal run modes. The paired IPI pending-bit fixes are enabled. No entry/panic
screen, boot diagnostic page, hardware probe stage or automatic test reboot is enabled.
Production mode also skips the inherited GPU scratch-write, client-round and cache-coherence tests.

`drivers/NativeAdreno` pins the upstream `zg7681/NativeAdreno-myron` **a8xx**
branch at `5bbeb3b8d049a637a595090319835a49e58a8b56`. Its chip register table,
ring, CP init, IRQ decoder, timer and continuation submissions match this device
code. The base repository's A740 submodule is overridden by this device module.
Clone this repository with `--recurse-submodules`.

## Build profiles

- `songyuan_bootstrap_defconfig`: source-kernel ABI carrier used during compilation.
- `songyuan_graphics_defconfig`: production FT3683/HID, A840/GMU/HFI, display and
  PMGR libraries linked against the current Darwin 23 ARM64 kernel.
- `songyuan_defconfig`: inherited full owner-root pipeline; requires separately
  generated signed OS/SystemOS policies and a Data seed.

GPU firmware is fetched outside Git from a pinned Xiaomi SM8850 vendor source.
GMU/SQE/AQE/ZAP are checked by exact size and SHA-256 before compilation. The
updated Xiaomi GMU image is checked with the existing host parser tests. Its
runtime compatibility on this phone remains to be tested.

The production Metal builder uses `SongyuanMetalPlugin.mm`: device discovery,
native Metal translation and GPU scanout only. Its NGPUADD2 addon carries the
plugin, signed Turnip library and publish marker; it carries no probe daemon,
launchd overrides, background test worker or renderer memory-patching experiment.

## iOS 27 target

`profiles/ios27.2.1.json` records the inspected official iPhone17,1 / 24B156 IPSW.
Its kernel is Darwin 27.2 / XNU 13432.42.3, ARM64e, with 305 fileset entries.
The matching Apple OSS tag is unavailable, and the inherited source/driver ABI is
Darwin 23 ARM64. iOS 27 has not been booted or made compatible by changing the
version string. The existing qualified Apple component profile remains iPadOS 17.7.11.

## Storage and verification

No myron GPT offsets are retained. This phone's previous pinned iOS 16 HFSX file
does not supply the APFS root and signed policies this new boot chain expects.
The phone is online. Firmware menu boot currently remains black; storage
installation and physical touch/GPU validation are still pending.
Actions validates board parameters and runs the existing touch/GPU host tests;
it cannot verify touch, GPU or an iOS desktop on the physical phone.

See the sibling [songyuan-uefi](https://github.com/NiandeNian/songyuan-uefi) and
[UniXNU-songyuan](https://github.com/NiandeNian/UniXNU-songyuan) repositories.

License: BSD-2-Clause-Patent.
