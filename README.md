# Super Right Click

为 macOS Finder 添加第一层右键菜单 **“使用iTerm打开”**。在文件夹内部的空白处右键，点击菜单即可新建一个 iTerm 窗口，并切换到当前目录。

通过原生 Finder Sync 扩展实现。菜单直接出现在右键菜单中，不放在“服务”或“快速操作”子菜单里。

## 使用效果

| 右键位置 | 新 iTerm 窗口进入的目录 |
| --- | --- |
| 文件夹内部的空白处 | 当前浏览的文件夹 |
| 文件夹图标 | 被点击的文件夹 |
| 普通文件 | 文件所在的文件夹 |
| 多选文件或文件夹 | 每个不同的目标目录分别打开一个窗口，相同目录去重 |

支持中文、空格、单引号和 `$()` 等路径字符。路径先编码进 URL，再分别做 AppleScript 和 Shell 转义，不作为可执行代码拼接。

## 环境要求

- macOS。构建目标最低版本为 **13.0**，实际验证环境为 **macOS 26.5.2 / Apple Silicon / iTerm 3.5.4**；其他系统版本尚未实机验证。
- 已安装 [iTerm2](https://iterm2.com/)。功能使用其默认 Profile 新建窗口，默认 Profile 应运行支持 `cd --` 的本地 Shell。
- Python **3.9+**，仅使用标准库。
- Apple Command Line Tools，提供 `clang` 和 macOS SDK。无需完整 Xcode 或 Apple 开发者账号。

如果尚未安装 Command Line Tools：

```sh
xcode-select --install
```

## 构建与安装

```sh
git clone git@github.com:hcmdgh/super-right-click.git
cd super-right-click
make install
```

`make install` 会先编译并进行本机临时签名（ad-hoc signing），再把应用安装到：

```text
/Applications/iTerm Finder Menu.app
```

安装脚本会注册并尝试启用 Finder 扩展。它只更新相同 Bundle ID 的本应用，拒绝覆盖无关应用、普通文件或符号链接；更新失败时会尝试恢复旧安装。脚本不会请求 `sudo`，也不会重启 Finder。

如果没有 `/Applications` 的写权限，可以安装到用户应用目录：

```sh
make build
python3 scripts/install.py --applications-dir ~/Applications
```

也可以不使用 Make：

```sh
python3 scripts/build.py
python3 scripts/install.py
```

只编译、不安装：

```sh
make build
```

构建产物位于 `build/iTerm Finder Menu.app`，默认编译为当前 Mac 的架构。仓库不包含预编译二进制，也未进行 Developer ID 签名或公证；建议在使用的 Mac 上从源码构建。

## 首次启用与权限

1. 如果菜单没有出现，打开 **系统设置 → 通用 → 登录项与扩展 → Finder 扩展**，启用 **“使用iTerm打开”**。不同 macOS 版本的入口名称可能略有不同。
2. 在普通本地文件夹的空白处右键，点击 **“使用iTerm打开”**。
3. 如果 macOS 提示该应用请求控制 iTerm，请允许。也可在 **系统设置 → 隐私与安全性 → 自动化** 中检查对应的 iTerm 权限。

辅助应用没有设置窗口，也没有 Dock 图标。不需要添加登录项：Finder 扩展由系统管理，点击菜单时会按需启动辅助应用。辅助应用启动后保持空闲，处理后续点击。

## 项目结构

```text
.
├── src/
│   ├── App.m                     # 接收目录请求，通过 AppleScript 打开 iTerm
│   └── FinderExtension.m         # 生成 Finder 第一层右键菜单
├── resources/
│   ├── App-Info.plist            # 辅助应用与 URL Scheme 配置
│   ├── Extension-Info.plist      # Finder Sync 扩展配置
│   └── Extension.entitlements    # 扩展沙箱与所选文件只读权限
├── scripts/
│   ├── build.py                  # 编译、组装 Bundle、临时签名和校验
│   └── install.py                # 安装、注册、更新失败恢复
├── tests/
│   └── test_install.py           # 安装目标保护与恢复测试
├── Makefile
└── README.md
```

实现流程：

1. Finder 扩展根据菜单类型读取当前目录或所选项目，计算目标目录并去重。
2. 扩展通过 `genghao-open-iterm://open?path=…` 把目录传给辅助应用；辅助应用只接受约定的 Scheme、动作和绝对路径参数。
3. 辅助应用调用 iTerm 的 AppleScript 接口，新建默认 Profile 窗口，在该窗口的会话中发送经过转义的 `cd -- …`，再激活 iTerm。

扩展注册的目录范围为 `/`，以便覆盖普通本地文件夹及其子目录。它不设置文件徽标、不修改 Finder 文件，也不连接网络。辅助应用不需要先读取目标目录的内容。

为兼容最初已安装的版本，保留现有标识：

| 项目 | 标识 |
| --- | --- |
| 辅助应用 Bundle ID | `local.genghao.itermfindermenu` |
| Finder 扩展 Bundle ID | `local.genghao.itermfindermenu.findersync` |
| URL Scheme | `genghao-open-iterm` |

## 验证

```sh
make check
```

该命令执行原生编译、代码签名校验、安装脚本的保护/恢复测试，以及 `git diff --check`。单元测试只使用临时目录，不安装应用、不修改 Finder 设置，也不打开 iTerm。

原始安装已在上述实机环境中验证：

- 文件夹空白处的第一层菜单能够打开当前目录。
- 文件夹图标上的第一层菜单能够进入被选中的文件夹。
- 通过实际 Shell 进程的工作目录，确认中文、空格、单引号和 `$()` 路径正确。

仓库中的多选、普通文件、侧边栏行为仍建议按下面步骤手动检查：

1. 在包含中文、空格的目录内部右键并点击菜单，确认出现新窗口，运行 `pwd` 检查目录。
2. 右键一个子文件夹，再检查新窗口的 `pwd`。
3. 右键普通文件，确认进入其父目录；多选同目录文件时确认只新建一个窗口。
4. 打开另一个目录，重复操作，确认使用新的目录。

## 常见问题

**菜单没有出现**

先在普通本地文件夹中测试，并确认系统设置中的 Finder 扩展开关已打开。可以关闭再打开此扩展，然后重新打开 Finder 窗口。虚拟位置（如“最近使用”或搜索结果）不一定提供可用的目录；其他 Finder 扩展也可能影响菜单显示。

检查注册状态：

```sh
pluginkit -m -v -i local.genghao.itermfindermenu.findersync
```

**点击菜单后报错，或无法控制 iTerm**

确认 iTerm 已安装，并检查自动化权限。应用使用 iTerm 的默认 Profile；如果默认 Profile 自动执行 SSH、进入其他交互程序，或 Shell 启动配置覆盖目录，可能无法进入预期的本地路径。可以先把默认 Profile 切换到普通本地 Shell 后测试。

**重新构建后再次提示权限**

本机临时签名的代码身份可能随编译内容变化，macOS 可能要求重新允许自动化，或重新启用 Finder 扩展。这不是经过公证的公开发行版本。

## 关闭与卸载

临时关闭：在系统设置的 Finder 扩展列表中关闭 **“使用iTerm打开”**。

也可以在终端关闭扩展：

```sh
pluginkit -e ignore -i local.genghao.itermfindermenu.findersync
```

卸载：先关闭扩展，再在 Finder 的“应用程序”中把 **iTerm Finder Menu.app** 移到废纸篓。如果使用了用户目录安装方式，则从 `~/Applications` 移走对应应用。之后如菜单仍暂时保留，可重新打开 Finder 窗口。
