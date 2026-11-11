# 小米 15 RAM 启动包对 songyuan 的参考价值

审阅日期：2026-11-11。用户提供目录：
`C:/Users/Administrator/Desktop/UniXNU/Xiaomi15-iOS26.2-Dev-fastboot`。
本次读取脚本、对应 Mu/XNU/GPU 归档中的关键源码及构建记录，没有运行该包的手机启动脚本。

这份材料对 RAM 启动和用户空间适配有明显帮助。它提供已组装系统与实际源码；不能把其中的小米 15 UEFI、内核、触摸或 GPU 参数直接用在 SM8850 songyuan 上。

## 实际版本和证据

目录名是 iOS26.2，但 `boot-config.json`、工具说明和载荷清单记录的是
**iOS 26.6.2 / 23G90**。内核二进制实际包含 `Darwin Kernel Version 25.6.0`，
来自 `xnu12377` 的定制 DEVELOPMENT ARM64 构建。

本次重新计算并匹配了 UEFI、载荷、独立内核、小根盘的 SHA-256；解析的全部七个 XNUP 条目也与清单一致。
System 文件大小为 5,371,183,104 字节，检查了 raw APFS 的 NXSB 超块；本次没有重新散列整份 System。
校验结果保存在 `.local/next/reference-local/xiaomi15/package-verification.json`。

包内 `ios-payload/build-info/STATUS.json` 记录小米 15 已启动 iOS，用户确认桌面和触摸。
这是提供方的测试记录，本次没有在小米 15 上独立复测。记录同时明确 Wi-Fi 无法开启、尚未出现 en0，应用返回与系统停顿问题未完全验证。

## 最有价值的实现

| 实现 | 源码位置 | 对 songyuan 的用途 |
|---|---|---|
| USB 分块上传 System | `tools/dada/boot_ram.py`、`xnuloader/loader_ramdisk.inc` | 256 MiB 分块、接收长度核对、失败状态、全部接收完才公开 RAMDisk；避免把完整 System 塞进 fastboot boot.img |
| 小型引导载荷 | `xnuloader/mkpayload.py`、`build-info/boot-config.json` | 七个条目仅包含 loader、kernel、ramdisk、cmdline、memsize、identity、usb；小根盘约 32.26 MiB，完整载荷约 51.11 MiB |
| 两份 APFS 的内存布局 | `xnuloader/loader_05_layout_run_kernel.inc` | 已上传 System 作为 md0，载荷内小根盘作为 md1；由 UEFI 分配实际可用窗口并排除载荷地址 |
| 内核返回加载器 | `loader_02_platform_cpu_ufs_survey.inc`、XNU `osfmk/arm64/loader_return.c` | 保存/恢复页表、MMU、TPIDR、栈与中断状态，并保留 RAM/USB 日志，可用于后续内核故障诊断 |
| 图形和桌面兼容 | GPU 归档、`graphics-r4/`、`userland-r2/` | NativeMetal→metal2vulkan→Turnip/NativeAdreno 的连接方式，图标方向、原生 XR 表面、SpringBoard XPC 对象生命周期与有界等待等实现可逐项参考 |

这些是 xnuloader/HackiOS 路线的实现；当前 songyuan 采用 UniXNU 菜单和 DarwinBoot。
可移植上传协议、组装方式和兼容处理，但两种加载器的载荷/设备树/内核 ABI 不能直接视为相同。

## RAM 预算与 Android 数据

启动参数 `--window 240000000` 是十六进制，即 **9 GiB**。
接收缓冲中 System 从窗口偏移 `0x08000000`（128 MiB）开始，另保留
`0x30000000`（768 MiB）给内核。该窗口最多接收 8.125 GiB 的 System。
本包约 5.00 GiB 的 System 放得下。

`choose_window()` 读取 UEFI 内存表，只选 ConventionalMemory，并用 AllocatePages 占有窗口。
当前 songyuan 内存表的显式 ConventionalMemory 主区是
`DXE_Heap=0xB8000000..0xC3DD0000`，约 189.81 MiB；不能凭手机装有 16 GB RAM 就认为这个上传器能取得 9 GiB。
后续必须按实机 `/memory` 和保留区补全高地址可分配内存，再计算实际窗口。

已准备的原始 iOS 27 OS+SystemOS 约 15.6 GiB，也不能照搬此包的 9 GiB 参数。
小米 15 的精简 System/小根盘组装方法有参考价值，但 iOS 27 的缓存、系统卷关系、信任缓存和启动身份仍需对应其版本重新制作。

BAT 本身只执行 `fastboot boot` 与 USB 上传；`DADA_USB_RAM_ONLY` 绕过自动切槽、存储调查和菜单倒计时。
不过完整 loader 源码仍含 `write_logs()`：找到 `logdump` 时会写该分区，显式 `oem logwrite` 还可允许写 boot_a。
因此“BAT 没有 flash”不等于整个运行路径零写盘。songyuan 的保留 Android RAM 方案应关闭磁盘日志及显式分区写命令，使用屏幕、USB 和主机日志。
本包默认没有 iOS 数据持久化条目；RAM 内 iOS 写入不能据此认为重启后会保留。

## 不能直接复用的硬件部分

| 项目 | 小米 15 包 | songyuan |
|---|---|---|
| SoC / GPU | SM8750，A830 路线 | SM8850，A840，需对应 gen80200 固件及寄存器/GMU/HFI/SMMU 实现 |
| GIC | `0x16000000 / 0x16080000` | 已采集 `0x17000000 / 0x17080000` |
| 显示 | 1200×2670 | 1200×2608；同为 4800 字节行跨度不代表面板时序相同 |
| 触摸 | Synaptics TouchComm/TCM，GPIO40–43，reset161、IRQ162 | FocalTech FT3683；报文、复位、供电、引脚和时钟需按 songyuan 数据实现 |
| 原厂 FD | donor map 扫描 `0xA7000000`，1 MiB | 实机 stock ELF 在 `0xC6800000`，2.65625 MiB，还依赖后方运行时内存 |
| 固件和平台选择 | annibale/warsaw 配置、dada 显示覆盖 | 需原生 songyuan 配置和实机固件输入 |

其帧缓冲地址选择也不能作为可靠机型识别：多个机型共用 `0xFC800000`。
源码自己使用编译宏强制选择平台；songyuan 应使用明确的设备配置和匹配 DTB。

## 对当前 UEFI 故障的结论

donor 保存 TPIDR 的代码发生在 UEFI 已运行、准备跳入 XNU 之后，不能修复本机更早的 SEC PlatformPeim 异常。
本机照片已证实 TPIDR 在 MMU 初始化前后保持 `0xC6EF02D8`；
`0xC6808300` 的 `ldrb w0,[x20,#0x328]` 访问 `0xC6EF0600`，ESR 为 `0x96000006`。
这是漏掉 stock 线程所在内存的 L2 翻译错误，而非需要构造一个假线程。

songyuan 已新增独立 `XBL_Runtime` 保留映射，代码扫描仍限于原 ELF FD。
同一故障指令在旧 Actions FD 的 QEMU 页表中复现原 ESR/FAR，在新 FD 中成功完成读取。
这验证了映射修复。随后真机测试（菜单 Actions `43029794779`，UEFI `43028929595`）
已通过 SEC 并进入 DXE；新照片显示 `ArmCpuDxe` 的异常处理器，
ELR `0xC22E3D84`、ESR `0x96000007`、FAR `0x01106000`。
该地址是实机设备树中 IPCC 的一页 MMIO，正在补齐映射。UniXNU 菜单仍未确认。

后续采用顺序：先完成本机 UEFI/DXE/菜单，再适配纯 RAM 的 USB 上传和精简系统组装，
然后分别推进 FT3683 与 A840。小米 15 的系统、用户态库和内核补丁应按实际 iOS 27 ABI 复核，不能把它的定制 Darwin25 内核直接等同于已下载的 Darwin27/ARM64e 原始内核。
