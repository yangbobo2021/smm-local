<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# 本机来源插件试用验收

2026-11-15 的同版三平台复测另见 [ZCode 三平台最终版交付验收](zcode-final-delivery-2026-11-15.md)。以下保留首轮试用结果。

范围来自用户确认的现场 Python 适配方案及分角色验收讨论。
行为依据为 [来源插件规约](../specs/packages/source-plugins.md)、[导入档案规约](../specs/packages/archive.md)、[入口规约](../specs/packages/access.md)和[汇总规约](../specs/packages/federation.md)。

| 角色 | 验收场景 | 执行范围与证据 |
| --- | --- | --- |
| 使用者 | 用同一适配 Skill 入口接入两种新来源，后台随后自动导入并可读取原文 | macOS 使用本机安装的 Aider 和 Gemini CLI 记录器生成受控对话样本。通过相同的固定脚本验收并注册，由后台正常周期追加，检索并核对全文。Aider 先写完用户消息，再单独写入助手回复。证据 `real-recorders.json`。 |
| 产品 | 按来源显示状态、暂停全局、停用单个来源、单独同步、零新增、读取已归档内容 | Chrome 实际点击与截图，另用自动测试验证失败、不可用、未同步和暂停状态。证据 `web-checks.json`、`web-import.png`、`web-search.png` 及测试日志。 |
| 开发 | 并发请求复用、运行中注册或停用、重启续跑、版本切换、不兼容候选拒绝 | CLI、Web、MCP 汇入同一后台任务，独立测试覆盖错配候选、全量期间注册、停用后阻止在途插件提交和服务重启。证据 `pytest-final.log`、`pytest.xml`。 |
| 测试 | 核对角色、正文、顺序、来源位置、会话边界、重复正文、追加和重放 | 内置验收器及 JSON、SQLite 集成夹具，加两种真实记录器产物。自动测试验证无效消息和来源位置被拒绝。 |
| 安全与隐私 | 超时、异常退出、输出超限、非法记录、事务冲突 | 单来源失败后主服务仍可检索，其他来源继续导入，修复后补入且无重复。Linux 容器另外实测执行器读取、重放和回收超时脚本。证据 `linux-executor.log`。 |
| 维护 | 版本回退、批次追溯与清理、原 ID 回放、项目归属修正、安装搬迁、旧汇总兼容 | 清除整段误导入后旧 ID 不会指向别的对话，回放可修正项目归属。发行包通过干净目录安装、重装、搬迁和卸载验证。经真实 HTTP 连接已构建的 0.2.0rc16 汇总端，内置来源可继续上传，现场来源可本机读取。证据 `install-relocation-packaged.log`、`previous-hub.log`。 |

最终全量回归为 29 项通过，Spex 结构检查为 0 个错误及 2 个既有警告。

证据在工作区 `.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/`，其中 ID 用作本地资料标识。
原生交付工具已有活动验收 `AT-SMM-MULTI-DEVICE-001`，拒绝创建本功能的正式收据。
独立复审直接核对候选及运行证据，复审指出的来源位置、调度覆盖、旧会话身份、项目归属和 Aider 分次写入问题已修正并复跑。

此次验证覆盖真实记录器和隔离样本，独立同事通过自然语言接入陌生 Agent 的试用仍待实测。
Windows 测试机可通过 SSH 到达，当前账户没有可用的 Python 3.11+，便携版下载未完成，未取得 Windows 运行证据。
Linux 验证范围为 Python 3.11 执行器。
同账户 Python 子进程提供故障隔离，插件沿用用户账户的文件和网络权限，试用对象为受信任脚本。
