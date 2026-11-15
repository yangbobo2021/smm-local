<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# ZCode 自适配端到端验收

同一台机器上依次运行三段独立对话：让 ZCode 用 `smm-source-adapter` 写适配器、运行固定的 `validate` 和 `register`；结束适配会话后生成新的测试对话；等待 SMM 自动同步，再让 ZCode 通过 `smm-search` 执行本机 `search` 和 `read`。每台机器使用独立的 SMM 档案，未执行手动同步。

| 环境 | 关闭适配会话 | 后台导入并读回 | 助手原文 |
| --- | --- | --- | --- |
| macOS，已登录的 ZCode 桌面 | 完成适配后在桌面切换到新对话 | 本机档案 2，原文位置 7，用户消息与助手回复分两轮导入 | `SMMSELF-MAC-NEWTURN-9371-REPLY` |
| Windows 11，官方包内 app-server | `session/close` 返回 `closed: true` | 本机档案 4，原文位置 9，用户消息与助手回复同一轮导入 | `SMMSELF-WIN-NEWTURN-9372-REPLY` |
| Ubuntu，官方包内 app-server | `session/close` 返回 `closed: true` | 本机档案 3，原文位置 9，用户消息与助手回复分两轮导入 | `SMMSELF-LINUX-NEWTURN-9371-REPLY` |

三个 Python 脚本由各机 ZCode 生成，摘要互不相同。每个脚本的首读和追加验收均为两条消息，注册版本为 1。后台归档中的位置、角色、原文已与 ZCode 源库逐条比对。为使测试可复核，预先准备了独立快照、限定归档范围及隔离库路径；远端工具操作按测试范围授权。只验证了受控对话，以及 Windows 和 Ubuntu 的官方运行时，未验证远端桌面操作、开机自启或整个账户历史。

首次生成未在三台全部一次通过。macOS 和 Ubuntu 遇到快照是文件、实际来源配置是目录的差异，ZCode 修正了适配器；macOS 给出了具体路径诊断，Ubuntu 在单次驱动超时后续接同一会话。Windows 对流式完成状态和命令格式做了迭代。Windows 首次用 SSH 驱动注册时服务随后结束，该次新对话未及时导入。重试时先让隔离服务持续运行并禁用启动即同步，再新建另一段对话，证实是正常周期导入。Windows 桌面环境中的服务自动保活仍未验证。

测试工件保存在 `.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/zcode/self-service/`。远端测试凭证已清除。
