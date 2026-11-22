# 双版本对账与 macOS 系统服务实测

本目录是产品 `7c72c92` 的真实安装包证据，保留该实际版本。两个包元数据仍为未发布 `0.4.0`；来源提交、wheel摘要、全部实际模块/HTML字节见每轮manifest。没有升级日常 SMM。

| 运行 | 实际范围 | 证据 |
|---|---|---|
| mac-reconcile15 | macOS普通用户、CLI/Chrome；旧本机代次、缺参数、旧Hub版本拒绝，fresh CLI与Web明确成功 | [结果](mac-reconcile15/result.json)、[请求/两端规则](mac-reconcile15/reconcile-result.json)、[清理](mac-reconcile15/cleanup.json) |
| linux-reconcile15 | Ubuntu普通用户、CLI/Chromium；同一限定范围 | [结果](linux-reconcile15/result.json)、[请求/两端规则](linux-reconcile15/reconcile-result.json)、[清理](linux-reconcile15/cleanup.json) |
| windows-reconcile15 | Windows普通交互Limited任务、CLI/Edge；同一限定范围 | [结果](windows-reconcile15/result.json)、[请求/两端规则](windows-reconcile15/reconcile-result.json)、[进程退出](windows-reconcile15/outer-process.json)、[清理](windows-reconcile15/cleanup.json) |
| mac-hub-main15 | 实际系统级launchd，服务UID501/PPID1、真实重启；最小登记、限制旧批次、补传、CLI/MCP范围与原文、归属传播 | [结果](mac-hub-main15/result.json)、[服务身份/重启](mac-hub-main15/service-events.json)、[补传](mac-hub-main15/backfill.json)、[归属](mac-hub-main15/affiliation-propagation.json)、[清理](mac-hub-main15/cleanup.json) |
| mac-hub-scope15 | 实际系统级launchd，protocol_only；共享会话仅X消息/标题、旧无范围兼容、重启引用 | [结果](mac-hub-scope15/result.json)、[服务](mac-hub-scope15/service-events.json)、[范围原文](mac-hub-scope15/split-scope.json)、[清理](mac-hub-scope15/cleanup.json) |

三平台对账专项只证明规则操作；成功界面仍可能存在另行记录的传输失败，不能扩称完成正文补传。服务轮的scope生产者标签通用，protocol_only模式实际没有浏览器/离线全部检查，不将其计作E1。

**本版本仍未整体通过。** 独立PR审查另实际复现调用中Hub变化后拒绝仍保存本机规则的窗口（P2，无正文外发）；旧值专项未触发该窗口。后续修复采用原Hub revision做CAS、成功后才条件保存本机，另保留真实红灯/绿灯及最终新包补验，不能改写本目录旧记录。

[package-comparison](package-comparison.json)证明f45→7c72c92全部Hub模块字节不变，Local仅API/CLI/upload/HTML改变。既有f45/d80服务/入口结果保留原版本；不能把本目录执行标成后续CAS顺序修复已通过。

公开文本替换测试账户、IP和私有绝对路径；PNG为真实合成任务界面，含任务生成路径，无用户对话/秘密。配置、Token、私钥、数据库和浏览器trace不公开；私有trace与原始控制器摘要见各目录controller-provenance。[provenance](provenance.json)同时列原始与导出摘要，`SHA256SUMS`校验公开文件。
