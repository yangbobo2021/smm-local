# 项目知识检索：父子意图导航

更新日期：2026-11-23。

本目录记录[父意图](intent.md)及六项独立变更的关系。005已由[PR #30](https://github.com/yangbobo2021/smm-local/pull/30)实现、验收并合并。维护者于2026-11-22授权代理自主推进006的SPEC、PLAN、实现与验证，每阶段经PR合并后继续；006的规格与计划已分别由[PR #31](https://github.com/yangbobo2021/smm-local/pull/31)和[PR #32](https://github.com/yangbobo2021/smm-local/pull/32)依序合并；实施、验收及独立审查记录见[PR #33](https://github.com/yangbobo2021/smm-local/pull/33)和[当前证据](../006-local-document-search/evidence/README.md)。006 实现 PR #33 已合并。007 首版边界于2026-11-23获维护者确认，开始按阶段PR推进；008–010仍为草稿，不将其余范围一并视为确认。

## 子意图

| 编号 | 子意图 | 交付关系 | 当前阶段 | 功能 PR / 验收证据 |
|---|---|---|---|---|
| 005 | [对话上传控制与本机 / Hub 联合检索](../005-selective-conversation-upload/intent.md) | 首先形成对话联合检索语义；与 007 对齐上传边界 | 已实现并验收 | [PR #30](https://github.com/yangbobo2021/smm-local/pull/30)；[证据](../005-selective-conversation-upload/evidence/20261122-native-completion/README.md) |
| 006 | [本机文档检索](../006-local-document-search/intent.md) | Markdown/UTF-8文本、本机明确纳入与刷新 | [SPEC](../006-local-document-search/spec.md) / [PLAN](../006-local-document-search/plan.md)已合并；[实施与验收记录](../006-local-document-search/evidence/README.md) | [PR #31](https://github.com/yangbobo2021/smm-local/pull/31) / [#32](https://github.com/yangbobo2021/smm-local/pull/32) / [#33](https://github.com/yangbobo2021/smm-local/pull/33) |
| 007 | [Hub 文档检索与同步](../007-hub-document-search/intent.md) | 承接 006；按项目同步、两端网页资料库及创建端管理 | [意图](../007-hub-document-search/intent.md) / [SPEC](../007-hub-document-search/spec.md)已合并，[补充SPEC #37](https://github.com/yangbobo2021/smm-local/pull/37)已合并，补充PLAN独立审查中 | [#34](https://github.com/yangbobo2021/smm-local/pull/34) / [#35](https://github.com/yangbobo2021/smm-local/pull/35) |
| 008 | [常用文档格式支持](../008-document-format-support/intent.md) | 扩展 006 / 007；覆盖 Word、Excel、PDF、图片 | 意图草稿 | 尚无 |
| 009 | [本机飞书聊天历史检索](../009-feishu-history-search/intent.md) | 可独立调研和交付；与 006 协调新增内容的检索路径 | 意图草稿 | 尚无 |
| 010 | [飞书长对话与关联内容理解](../010-feishu-context-understanding/intent.md) | 承接 009 的聊天记录及 008 的通用文件、图片处理能力 | 意图草稿 | 尚无 |

以上是能力的交付关系，不预先约定代码结构，也不表示任一前置能力已经存在。推荐先推进 005、006，再推进 007；008 和 009 可按前置条件准备，010 在相关基础能力上推进。具体实施顺序由后续计划确认。

## 文档职责

- 父意图说明整体问题、用户目标、共同边界和共同待确认问题。
- 每份子意图按项目模板完整说明自身问题、用户、期望结果、范围和未决事项，并链接父意图及相关子项。
- 各子目录在自身意图确认后，分别生成 SPEC 和计划，独立记录平台覆盖、验收条件、实施及证据；按项目流程确认、提交后进入下一阶段。
- 父意图的共同边界与某个子意图确认后，该子意图可进入自己的下一阶段；无关子项仍为草稿不构成额外阻塞。
- 整体使用结果和跨子意图验证的安排，在后续规格、计划阶段明确，并在此汇总证据入口。当前不预先记录“已通过”。

## 边界与未决事项归属

本轮已明确：“全局项目”与普通项目同级，“全部项目检索”是不限定单个项目的查询；不上传正文的项目仍可登记名称供 Hub 配置关联；两端各自正常返回结果后，对合并集合按原查询重新检索排序。005 已确认必要稳定身份、同源去重和本机重排的约束，避免把应留在本机的候选隐式发送 Hub。停止确认与旧副本保留、全部未确认历史补齐、默认策略、联合查询范围、入口及首版来源也已确认，不再列为待决事项。

| 事项 | 主要归属 |
|---|---|
| 各类新增入口、文档和飞书资料组织、图片与长对话处理位置 | [父意图的共同问题](intent.md#待确认问题) |
| 005 的上传策略、停止恢复、历史补齐、默认选择、检索范围与入口、现有可汇总来源，均已确认 | [005 的已确认约束](../005-selective-conversation-upload/intent.md#范围与约束) |
| 基础文档首批格式、纳入与更新方式、旧版本及源文件移除后的原文 | [006](../006-local-document-search/intent.md#待确认问题) |
| Hub 自有文档、文档上传选择、重复来源与同步停止后的副本，已确认 | [007](../007-hub-document-search/intent.md#已确认的首版边界) |
| 文件扩展名、扫描件、图片理解层次、Excel 内容范围 | [008](../008-document-format-support/intent.md#待确认问题) |
| 飞书读取方式及可读范围、持续更新、编辑撤回与权限变化 | [009](../009-feishu-history-search/intent.md#待确认问题) |
| 长对话处理程度、关联材料读取范围、飞书云文档与图片的理解层次 | [010](../010-feishu-context-understanding/intent.md#待确认问题) |

005 后续仍需核实现有 Agent 实际记录怎样表示全局会话；额外 Agent 的上传扩展须另行明确。此类来源调查不能被写作已经验证，当前确认也不代表功能已实现。

只影响一个子意图的调整在该子项处理。影响共同边界时先更新并确认父意图，再同步受影响的子文档。日常进度、PR 和证据链接更新于本导航，避免用进度改动替代需求确认。
