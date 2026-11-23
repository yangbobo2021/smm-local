# 007 验收状态（候选，未判交付通过）

本实现按已合并SPEC #37及PLAN #38推进。使用独立合成档案，不连接日常Hub、VibeInsight或家庭ESXi。维护者确认当前没有非ESXi替代机器，先继续本机与CI；不能覆盖的必要平台项保留待验证。

| 范围 | 当前证据 | 边界 |
|---|---|---|
| 完整pytest | 本机候选 `327 passed, 1 skipped`；跳过Windows专属服务启动时限项 | 不是三系统实际平台或完整交付结论 |
| 独立包 | Local/Hub全新环境，18条构建/安装/模块SHA/CLI/MCP检查通过 | Hub不安装Local发行包；正式原生逐项证据继续补充 |
| macOS安装包流程 | 两逻辑Local、普通账户前景HTTPS Hub，真实CLI、两端Web选择/拖放/更新/删除、stdio、项目一层范围、联合排序/原文、暂停撤回、离线/重连、重启及源指纹通过 | 不冒称物理跨机器或系统launchd；最终正式收据/独立意见待补 |
| 用户路径 | README→指南→独立CLI帮助/实际Web/Skill/维护入口；两条真实旧页面请求均以原KEY/HID/G提交并拒绝，完整新选择保持 | 最终正式人工记录/独立意见待补 |
| 自动用例复审 | [原准备复审](../../../../reviews/preparation-design-review-v3.md)、[原绿灯复审及发现](../../../../reviews/green-review-v3.md)、[补充红灯复审](../../../../reviews/review-gap-red-v3.md) | 保留原包证据不足及列表/片段缺陷历史；已修复后重新取最终证据 |
| 托管CI三系统 | 已新增显式 `document-installed` 模式；待本候选提交后实际执行 | Windows必须观察真实标准账户；不得只标配置就绪 |
| E2跨OS真实机器/Ubuntu用户服务/Windows SCM | 待验证 | 普通前景Hub或能力探测不替代实际服务和物理跨机器 |

原生验收 `AT-SMM-007` 当前29项（22自动/7人工）；原27项身份与旧声明保持，新增SC11/SC12补齐已确认B6/B7遗漏。源定义/设计/关联在`.acceptance/native-v1/AT-SMM-007/`；私有执行原件在`.acceptance-local/native-v1/AT-SMM-007/`，不直接公开凭据、私钥、档案或浏览器完整trace。公开脱敏原件/SHA索引、正式逐项结果及独立PR Review在后续证据提交补齐。本页是当前状态导航，不是替代独立passed意见。
