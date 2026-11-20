# 已确认 SPEC 的逐项覆盖

基线：已合并 SPEC #24、PLAN #25；本轮正式执行 15 个 TC 均退出 0，全部取得独立执行复审。下列结果针对明确环境，不按一个系统推断其他系统。

| SPEC 验收节 | 必需验证 | 对应正式证据 |
|---|---|---|
| 1 环境覆盖 | Linux systemd / macOS launchd / Windows LocalService；一个自行管理进程；三平台 CLI/MCP | H 三平台各 initial+lifecycle；P 四项；C 三项。见[正式收据](native/execution-services-v1.json)与[总索引](README.md)。 |
| 2 配置与服务恢复 | 每台服务实际 psql/身份/凭据；300 秒周期、最小/无效周期；坏连接/权限/口令保持旧配置及档案 | 各 `hub/<OS>/H1-*`、`H2-status`、`H3-status`、`retained-originals-*`、`commands.jsonl`；凭据文件/配置只公开摘要。 |
| 2 停机续跑 | 同一 T 的 3→5 轮、停机新 N、独有新增可检索、重复不增、原 ID 与精确引用保留 | 各 `H6-before`、`H6-source-append`、`H6-after-original`、`H6-new`、`H6-new-content-search-*`、`H6-repeat`；[引用复算](hub/reference-audits/linux.json)及 H 独立复审。 |
| 2 无新增及凭据 | 真停止/启动、PID 改变、完整进度/旧原文/引用不变；同目标换凭据后无需重输 | 各 `H7-restarted`、`H7-no-new-restart`、`H5-restarted`、`H5-replaced-and-restarted`、`retained-originals-*`。P 还实际导入新 140/141。 |
| 2 失败批次/依赖/连接 | 第一条未提交、第二条 ABORT；无半批/越过游标，恢复只一份；三类故障后实际新 2 条 | 各 `H8-failed`、`H8-recovered-original`、`H8-recovered`、`H4-*` 与每类 `recovery-*-new-original`。真实服务自动轮次，未加产品测试后门。 |
| 2 凭据保护/只读 | 限制非授权访问、秘密扫描；所有来源查询为显式只读事务 | 各 H9/只读 SQL；[Linux DAC 方法](hub/linux/H9-posix-access-audit.json)明确为推论；Mac/Win `H9-denied-read` 为实际拒读。 |
| 3 全部可读历史/新项目 | C/D 历史、新发现/后可见项目补早期，未获准项目不导入 | H1 双项目独立原文；G `G3-*`、`G1-later-visible-original`。 |
| 3 顺序/进度/窗口 | 两个不同 K 的 24h 内/恰好/外、长停服、同时间及重读、批次固定上界 | G `G3-starting-positions`、独立输入清单、七个逐会话原文、`G2-same-time-and-repeat`；默认流式/批次回归及[真实 SQL](compatibility/current-postgres.json)共同覆盖。外边界仅观察，不承诺补齐或强制排除。 |
| 3 连接身份 | host/port/database 参数化隔离；实际 SQL 换库补早期、同库换凭据/重启/继续追加、旧来源保留 | `TC-boundaries-default` 六项回归；G `G4-*`（含早期 0/1、换凭据后 2/3、完整进度及旧精确引用）。三个字段不是三次 SQL 实测。 |
| 3 历史原地改写 | 原始正文保留，另加新事件正常追加 | G `G5-independent-before`、`G5-original-edit-boundary`；完整旧十条对独立清单。 |
| 4 项目及关系 | 同名设备区分、双向唯一一层；A/B 两方向各目标命中；解除仍全局可查/旧引用可读 | 三平台 C1 实际范围/独立目标；G `G6-links`、`G6-scope-*`、`G6-unlinked-search/global/old-reference`。 |
| 4 名称/仓库/旧历史 | 显示名真变化、稳定 ID/关系不变；仓库身份新项目再关联；旧无归属历史不增消息补传 | 三平台 C6 前后完整会话及名称响应；仓库 host/port/path 默认参数化 + G7 实际 path；[真实旧 Hub 升级](compatibility/current-upgrade.json)。 |
| 5 三平台两入口 | 每个系统 CLI/MCP 各自在线/全局/自身精确引用/旧引用；断线/本机/恢复；schema/help | `clients/<OS>/verify/` 的 C1/C2/C3/C4/C5/C6；来源字段/角色/独立正文与位置逐项比对；stdio 进程退出 0。 |
| 5 旧客户端全局 | 真实 d2dee18 旧进程上传/搜索/完整读回 | 各 `prepare/C6-before-metadata` 的实际模块 SHA；旧客户端及旧 Hub 升级探针。 |
| 用户入口/发行回归 | README→指南/Skill→实际 CLI/MCP；默认测试与独立 SQL 分层 | README/指南/探针指南；C5 schema/help；[三平台 CI](environment/ci-results.json)；最终 PR 独立审查另记录。 |

相应独立执行判定：[H 六项](reviews/review-execution-services-v1.json)、[P 四项](reviews/review-execution-standalone-v1.json)、[C 三项](reviews/review-execution-clients-v1.json)、[G 两项](reviews/review-execution-shared-v1.json)。

旧 R1–R7 / SC1–SC7 留作历史定义，不把旧七项自动翻成新平台通过。本轮选定交付基线为新 SPEC 全量 R8 与自行管理计划 R9，正式场景 SC8–SC11；最终需求级判定与 PR 审查采用本表、完整 SPEC/PLAN 及实际原始证据，不以计数或表格自证。
