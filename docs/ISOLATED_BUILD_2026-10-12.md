# 独立固件分支与 OTA 容量验证

两份独立工作副本位于 `F:\WorkSpace\VSCodeSpace\echoear-firmware-fix-20261012`，目录下分别是 `esp-echo-ear-xiaozhi` 与 `esp-echoear-base`。两仓库修复分支均为 `codex/echoear-firmware-ota-fix-20261012`，基线分支均为 `codex/echoear-baseline-20261012`。

本体基线提交：`84525aa`；底座基线提交：`7d3721e`。基线保留用户原先未提交的业务代码与板型设置；本体也保留已完成的本地底座组件依赖修复。修复代码在后续提交中，基线与修复相互独立。

原项目目录保留隔离前的当前文件，包括本次已完成的修改；没有自动恢复、删除、移动或覆盖原项目文件。若要运行修改前固件，使用基线分支的新工作副本即可，不必动原目录。根目录的 `snapshots` 保存隔离前的相关文件与完整 tracked diff。

## 本体新布局

| 分区 | 起始地址 | 容量 |
|---|---|---|
| nvs | 0x9000 | 16 KiB |
| otadata | 0xd000 | 8 KiB |
| phy_init | 0xf000 | 4 KiB |
| ota_0 | 0x10000 | 6 MiB |
| ota_1 | 0x610000 | 6 MiB |
| assets | 0xc10000 | 3.5 MiB |
| model | 0xf90000 | 300 KiB |

最后一个分区结束于 `0xfdb000`，位于 16 MiB Flash 范围内。现有资源 2,732,489 字节与模型 291,066 字节完整保留；SHA256 分别为 `0a6e6a6c8ce73d91e9ceef3de3eb7450b35f40e4c42ab2850a1c15257214b711` 和 `7183e030be52a41b0147d4c2ba05537c59d28c08992f5c2c623df0c75da5fe89`。

原表的 ota_1 只有 0x37f000 字节，小于当前约 5.03 MiB 固件。新表两个 OTA 分区相同，给两端升级都留出约 1 MiB 空间。构建验证脚本 `scripts/check_echoear_partitions.py` 读取生成的二进制分区表，核对容量、重叠、地址、Flash 上限和现有资源哈希。

## 构建与回退

在 `C:\Espressif\tools\Microsoft.v5.5.4.PowerShell_profile.ps1` 环境下，从独立本体目录运行 `idf.py build`，从独立底座的 `software\echoear_rotating_base` 运行同一命令。使用全新 build 目录，不复用原目录 CMake 缓存。

回退时可在独立工作副本中切换到 `codex/echoear-baseline-20261012`；也可使用 `git worktree add <新的空目录> codex/echoear-baseline-20261012` 新建基线副本。Git 不跟踪的 sdkconfig、工具环境和组件下载需在新副本中配置；已有独立副本保留了实际构建配置。

本次仅编译和静态资源验证，不烧录。设备当前分区表不会因此自动改变；普通应用 OTA 不会迁移分区表或移动资源。将来部署新布局时需要同时使用新的分区表与匹配地址的完整构建产物。
