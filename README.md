# echoear · 语音交互本体

基于 ESP32-S3 的 EchoEar 本体固件，承担语音采集、唤醒与对话、表情显示、声源方向估计（DOA）以及旋转底座控制。项目沿用小智固件 2.0.5 的基础代码，针对本体与底座的联动进行维护。

配套底座：[zhxil/rotating_base](https://github.com/zhxil/rotating_base)。本体通过 UART 向底座发送方向和动作指令，接收心跳、动作完成和磁滑块事件。

## 版本选择

| 分支 | 用途 |
|---|---|
| `main` | 修改前的本地基线，加上本仓库说明；保留原有业务代码和板型设置 |
| `codex/echoear-baseline-20261012` | 保存的回退基线，含本地底座组件依赖修复 |
| `codex/echoear-firmware-ota-fix-20261012` | 本体／底座协议修复、DOA 跟踪改进与双 OTA 分区调整 |

联调时建议本体和底座都使用修复分支。基线保留原行为，不包含后续固件修复。

## 本体配置与代码入口

- 芯片：ESP32-S3；Flash：16 MiB；本次验证环境：ESP-IDF 5.5.4。
- 板型：`CONFIG_BOARD_TYPE_ECHOEAR`；当前本地配置选择 PCB V1.2，见 `main/boards/echoear/config.h`。
- 板级初始化与显示：`main/boards/echoear/echoear.cc`。
- 音频分析与 DOA 跟随：`main/boards/echoear/audio_analysis.cc`。
- 底座状态和校准：`main/boards/echoear/base_control.cc`。
- 底座 UART 协议：`components/echoear_base_control`。

硬件接口在本次维护中没有调整。UART 为 115200、8N1；帧格式为 `AA 55 LEN_H LEN_L CMD DATA... CHECKSUM`，长度包含命令字，校验为命令与数据的逐字节累加低八位。

## 本地目录与归档

当前修复版开发入口（2026-10-12）：

```text
F:\WorkSpace\VSCodeSpace\
├── echoear\                           本体工程，根目录直接构建
├── rotating_base\                     底座工程，根目录直接构建
├── esp-echo-ear-xiaozhi\               原本体项目，保留原有改动
├── esp-echoear-base\                   原底座项目，保留原有改动
├── ECHOEAR_DIRECTORY_INDEX.md          本地目录索引
└── archives\echoear-20261012\          历史版本与备份
    ├── body-fix-old\                  旧本体修复工作树与历史构建
    ├── base-fix-nested-old\            旧深层底座工作树与历史构建
    ├── body-main-docs\                本体 main 文档工作树
    ├── base-main-docs\                底座 main 文档工作树
    ├── snapshots\                     隔离前快照与差异
    ├── original-restoration-backup\    恢复原项目前的文件和构建
    ├── rotating-base-all-branches.bundle 归档时的底座 Git 完整备份
    └── branches.json                   首次隔离时的历史路径与提交
```

VS Code 分别打开 `echoear`、`rotating_base` 即可；两者均不再需要从旧深层目录进入。底座当前根目录只保留固件，不含 `hardware` 和 `3D_models`；这些资料仍可在回退分支、历史版本或上游仓库查阅。

本地 `echoear` 使用 `codex/echoear-local-20261012`，`rotating_base` 使用 `codex/rotating-base-flat-20261012`；其修复代码对应 GitHub 的 `codex/echoear-firmware-ota-fix-20261012`。`main` 保留基线代码行为并同步目录和文档；回退分支 `codex/echoear-baseline-20261012` 保留原始快照，不随 README 更新。

归档工作树用于历史查看和回退，移动后的旧 `build` 缓存不作为当前构建入口；需要重新构建时，应使用新构建目录。原项目与回退分支保留，当前修复版和两份构建产物也保留。归档目录及 Git bundle 只存在于本机，不随 GitHub 克隆下载；`branches.json` 中的首次隔离路径仅作历史记录。

## 已配置工作副本的构建路径

在验证机 PowerShell 中执行：

```powershell
. 'C:\Espressif\tools\Microsoft.v5.5.4.PowerShell_profile.ps1'
Set-Location 'F:\WorkSpace\VSCodeSpace\echoear'
idf.py build
python scripts/check_echoear_partitions.py
python scripts/test_base_integration.py 'F:\WorkSpace\VSCodeSpace\echoear' 'F:\WorkSpace\VSCodeSpace\rotating_base'
```

固件产物：`F:\WorkSpace\VSCodeSpace\echoear\build\xiaozhi.bin`；构建记录：同目录根下的 `build-validation.log`。本地 SDK 配置已保留，无需为了目录迁移重新执行 `set-target`。新克隆仍需按下面步骤配置。

## 首次克隆与构建

```powershell
git clone --branch codex/echoear-firmware-ota-fix-20261012 https://github.com/zhxil/echoear.git
cd echoear
# 先激活本机 ESP-IDF 5.5.4 环境
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
```

在 menuconfig 中选择 EchoEar 板型、16 MiB Flash、自定义分区表 `partitions/v2/16m.csv`，以及自定义资源文件 `wn9_nihaoxiaozhi_tts-font_puhui_common_20_4-echoear.bin`；同时确认实际设备的屏幕、音频和唤醒模型配置。`sdkconfig` 和 `dependencies.lock` 未纳入 Git，首次克隆需要配置和解析依赖。

Windows 验证机使用安装器提供的 `C:\Espressif\tools\Microsoft.v5.5.4.PowerShell_profile.ps1` 激活环境。其他机器应使用自己的 SDK 安装路径。

## 修复分支的 OTA 与资源布局

| 分区 | 起始地址 | 容量 |
|---|---|---|
| ota_0 | `0x10000` | 6 MiB |
| ota_1 | `0x610000` | 6 MiB |
| assets | `0xc10000` | 3.5 MiB |
| model | `0xf90000` | 300 KiB |

现有资源文件完整保留。已验证固件为 5,272,000 字节，每个 OTA 分区剩余 1,019,456 字节。新布局需要匹配的分区表和资源地址；普通应用 OTA 不会迁移旧分区表。

## DOA 与验证状态

修复分支保留底层声源估计与原有声学补偿，修正音频短读和滤波启动偏差；采用 5°量化，限制无语音、非跟随模式和本体播音时的控制输出。进一步校准麦克风间距、通道延时、噪声筛选和角度补偿需要双通道录音与真实角度标注。

2026-10-12 已完成本体和底座编译验证、15 项真实 C 串口解析回归、721 项量化测试，以及分区容量、地址和资源哈希校验。没有烧录或实际电机／定位精度验收。

修复分支中的详细记录：`docs/BASE_DOA_FIX_2026-10-12.md`、`docs/ISOLATED_BUILD_2026-10-12.md`。回归入口：`scripts/test_base_integration.py`、`scripts/check_echoear_partitions.py`；前者需要 Windows Visual Studio C 编译工具，后者需要已有构建产物。

## 来源与许可

本项目基于 [ESP Friends EchoEar 小智工程](https://gitee.com/esp-friends/esp-echo-ear-xiaozhi) 和 [小智 ESP32](https://github.com/78/xiaozhi-esp32)。许可见仓库 `LICENSE`，各组件保留其原始许可声明。
