# 007 验收状态（候选，未判交付通过）

本实现按已合并 SPEC #37、PLAN #38 推进，PR #39 保持 Draft。全部材料使用独立合成档案；不连接日常 Hub、VibeInsight 或家庭 ESXi。维护者确认没有非 ESXi 替代机器，先继续本机与 CI；必要实机项保持待验证。

| 范围 | 已取得的有限证据 | 仍需补齐 |
|---|---|---|
| 本机完整 pytest | 当前产品：334 passed、1 skipped（Windows 专属服务启动时限项） | 三项补充修复已包含；XML 335 项、0 失败/0 错误/1 跳过 |
| 独立包 | 当前产品 v4 的 Local/Hub 新环境，18 条构建/安装/模块 SHA/CLI/MCP 检查通过；Hub 不安装 Local 发行包 | 源码→wheel→安装逐模块校验通过，实际平台及正式逐项独立意见继续补齐 |
| macOS 安装包流程 | 候选 v3 / macOS v9：普通账户、两逻辑 Local、前景 HTTPS Hub、实际 CLI/两端 Web/stdio、混合批次、项目范围/准确原文、暂停撤回/离线重连/重启与源指纹 | 最终同版重跑及正式逐项复审；不是物理跨机器或 launchd |
| 三系统常规 CI | [f7bb 测试及打包](https://github.com/yangbobo2021/smm-local/actions/runs/45167908741) 三系统 success，另一次 push 同版运行也 success | 后续产品修复的最终同版 CI |
| 托管实际业务与服务 | [a44 安装包运行](https://github.com/yangbobo2021/smm-local/actions/runs/45167073148)、[准备修订后运行](https://github.com/yangbobo2021/smm-local/actions/runs/45173850806)：macOS/Ubuntu 前景业务及 Ubuntu 实际 user-systemd success | 原件完整回收/解密及独立复核；仍为托管同机逻辑档案 |
| Windows 安装包普通账户 | 保留编码、wheel 权限和 Get-Acl 准备失败历史；[48bc7 额外一轮](https://github.com/yangbobo2021/smm-local/actions/runs/45178028154) 已实际通过 Windows 普通账户完整业务，随后首次 SCM 路径失败 | 普通账户结论限当时 a44 产品；SCM 原始业务 stderr 未完整回收，另有 export 读取 build.stderr 的权限错误，不能判服务通过或臆测产品原因 |
| 必要实机 E2 | 当前无获准的非 ESXi 不同操作系统物理机器环境 | 真实跨机器认证 HTTPS 路径；同机档案、CI 服务或能力探测不能替代 |

独立 [PR 复审 v1](../../../../reviews/pr39-review-v1.md) 的 F1–F4 已经补充真实红灯、同测试绿灯及 [独立绿灯意见](../../../../reviews/pr39-green-review-v1.md)，并在 [PR 复审 v2](../../../../reviews/pr39-review-v2.md) 中复核关闭。v2 另外发现 Hub 文件元信息、暂停保留状态及文件夹拖入指引遗漏；这三项已经补充独立有效红灯、同测试绿灯与[绿灯复审](../../../../reviews/status-green-review-v1.md)。正式全项及最终 PR 复审继续补齐，不将局部通过升级为整体交付通过。

原生验收 ID 为 `AT-SMM-007`。当前定义 000007 在原 31 项基础上补 SC15/16；SC15 元信息与保留状态按独立复审拆分独立判定后，共 34 项（27 自动 / 7 人工）。原有 TC 身份、历史失败和复审意见保留。定义/设计/关联在 `.acceptance/native-v1/AT-SMM-007/`；私有原始记录在 `.acceptance-local/native-v1/AT-SMM-007/`。本次补充红灯、最终正式逐项执行、人工记录、公开脱敏原件/SHA 索引及需求级意见尚未收口。

CI 业务原件包含输出、模块/源指纹、截图、实际身份/服务与清理记录。完整浏览器 trace 使用公开 X509 证书加密回收；私钥仅在任务本机保存，不能进入仓库、workflow 或 artifact。回收后核对密文 SHA、解密后的原始 SHA；具体方法见[验收复跑说明](../../../../scripts/acceptance/README.md)。操作说明或加密自检不能替代实际平台原件复核。本页仅导航当前证据及限制。
