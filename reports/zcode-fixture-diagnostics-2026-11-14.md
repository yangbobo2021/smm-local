<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# ZCode 验收诊断回归

固定验收入口的失败现在包含阶段、实际传入适配器的完整 `root`、文件或目录类型，以及原有失败原因。例如：

> 验收失败：before（首次读取），root=「…/before/db.sqlite」（文件）：插件异常退出（退出码 1）

代码回归 32 项通过；`spex lint` 零错误，有两条现有归档规约警告。三平台各从新的、仅接受目录的候选开始；ZCode 看到上述诊断后自行支持文件输入，完成固定脚本的验证和注册。随后结束适配会话，新建对话，在未手动触发同步的情况下由 SMM 定时导入，再在独立 ZCode 会话调用 `smm-search` 搜索、读回，并与源库原文逐条核对。

| 环境 | 本机档案 ID | 助手原文 |
|---|---:|---|
| macOS 桌面 | 2 | `SMMSELF-MAC-DIAG-9471-REPLY` |
| Windows 11 官方 app-server | 5 | `SMMSELF-WIN-DIAG-9471-REPLY` |
| Ubuntu 官方 app-server | 4 | `SMMSELF-LINUX-DIAG-9471-REPLY` |

Windows 的 SSH 运行时验证仍把 SMM 放在一个持续的独立进程中，并关闭启动即同步。该结果不能作为 Windows 桌面端服务保活的证据。

本机原始证据：`.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/zcode/fixture-diagnostics/`。

Windows 桌面单独使用 VM 76 的交互式 Windows 会话和 ZCode 桌面应用。ZCode 亲自验收并注册 `zcode-windesk`，由注册命令启动 SMM（PID 3316，Windows Console 会话 1）。注册等待就绪超时并返回 `service_error`，但同一个进程随后自行就绪，无人干预。离开适配任务后，首次新对话自动导入用户消息，助手回复未进档：候选先按时间过滤，再判断会话是否符合范围，导致已越过游标的用户消息无法再证明该会话符合范围。

ZCode 修正了候选并重新验收、注册为版本 2；同一 SMM 进程定时补齐首次遗漏的回复。再次离开适配任务后新开另一段桌面对话，用户消息和助手回复均由同一服务自动导入，档案 4、回复位置 7。Windows 桌面 ZCode 在另一会话实际调用 `smm-search`、本机 `search` 和 `read 4`，读回 `SMMSELF-WINDESK-NEW-9472-REPLY`；重试时明确指定本机读取不带汇总参数。未重启服务，未手动同步。此次观察的是关闭适配会话后继续运行；未退出整个 ZCode 应用或注销 Windows。

首次注册的服务就绪误报仍存在；本次只改了适配器验收诊断，未改服务启动等待行为。
