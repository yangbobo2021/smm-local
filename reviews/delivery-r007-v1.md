# AT-SMM-007 R007 需求级独立判定 v1

结论：**blocked**。当前正式证据尚未确认产品违反必测行为；SPEC A9 明确要求的 E1 三格及 E2 三项仍各有必要证据缺口，不能判 passed。资源不足、停止补跑的授权、准备工具失败、普通 CI 成功都不改变这一结论。

唯一原样意见先写入 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/delivery-r007-v1.json`，随后立即通知主 Agent 登记，再撰写本报告。JSON 仅含 `status` 与 `reason`，只判 R007。本报告不代主 Agent 登记、不重新执行业务。

## 依据、版本与只读边界

独立读取验收 Skill、`references/execution/reviewer.md#需求级交接`、`execution/entry.md#逐需求交付判定`、AGENTS、007 intent/spec/plan、`reviews/authorization.md` 和 `project-library-authorization.md`。采用 `work/delivery-r007-v1-view.json` 的定义 000007，SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`，R007 关联 SC1–SC16、35 TC（27 自动、8 人工）。

核对时 HEAD 为 `425f1409c98da66bb40c7574f390dcc30a0cc283`，实际 `git diff 245c236 HEAD -- src` 为空；当前产品与 `245c236ddc41057cd78694902283574d1175e309` 相同。后来验收工具的冻结版本分别核对，不把相同产品推成相同工具或相同执行。

直接读取正式结果和独立意见，并复核证据入口 README、acceptance-index、public-manifest。逐字重算：

- 当前结果视图全部 **6773** 件 evidence SHA，无缺件或不符。
- 35 份正式执行/人工收据和 35 份当前独立复审收据 SHA，均与逐项索引一致。
- 正式收据中 **3186** 个 bindings 引用和 **6512** 个 artifacts 引用，共 **9698** 次文件核对，无不符；这些是引用数，不是不同文件数。
- 公开 manifest 的 **36** 件文件长度与 SHA 全匹配。

这些检查证明当前材料的字节关联，不能证明业务自动通过。业务结论同时参照正式执行复审、Mac 人工 v3、Mac 协议重核 v4、E1 CI v1、服务 v1、回归 CI v1 的独立原样意见。当前统计是 29 passed、6 insufficient_evidence。没有将 debug/TDD 结果代作正式执行，也没有继承历史 Mac 完整 passed。

本轮未执行产品、pytest、服务、GitHub 操作或访问 ESXi、日常 Hub/VibeInsight/真实资料；仅写指定意见和本报告。对已由执行 Reviewer 实际打开检查的画面，沿用其对应检查的独立证据，不宣称本轮重新逐张视觉验收。决定性缺口由原协议、冻结执行顺序和原始资源记录直接核实，不依赖截图观感。

## 完整需求范围的证据归属

以下“有效”限实际分配检查及相应执行范围，不表示跨平台全组合成立。

| 场景 / 原需求 | 当前有效依据与边界 |
| --- | --- |
| SC1 / A1、B1–B2 | policy-choice 正式执行与独立意见支持默认关闭、文档/对话独立、多项目资格、KEY/HID/generation CAS、改名/合并/重启/切 Hub；真实旧页面由 user-discovery 补足。 |
| SC2 / A2、B4 | sync-publication/retry/boundaries 支持多来源完整清单原子发布、暂存不可查、丢回执与中断重试、2MiB/16MiB 边界及非法清单拒绝；进程内和 loopback 不能替跨 OS HTTPS。 |
| SC3 / A3、B3 | paused-lifecycle/overlap-publication 支持允许/已发布后暂停两前态、失效撤回与同字节不复活、共享当前版本及最后资格退出、全局暂停控制与手动同步；不推出所有真实入口/系统已完成同样组合。 |
| SC4 / A4、B4–B5 | origin-identity/ordering-concurrency/recovery-controls 支持独立设备身份、旧配置/版本/回执 fence、网络等待不持锁、保护失配及显式恢复；真实平台差异由 SC9 承接。 |
| SC5 / A5、B5–B6 | hub-native/project-scope 支持明确 CLI refresh、自有来源与设备投影边界、普通/全局/同名身份、Local 与 Hub 文档 D 和对话 C 的公共一层双向入口。 |
| SC6 / A6、B6 | search-candidates/fallback 支持独立预期候选、至多 2limit 统一 BM25、同版合并/异版并列、Hub 根与同号 Local 不混用、合法回退与覆盖说明。 |
| SC7 / A7、B7 | read-exact/rejection 支持旧 Local/native/device/combined 精确引用、规范化文本/码点/LF 行号/16000 边界及逐字段拒绝、同版本精确回退；不证明未执行的 stdio 原文路径。 |
| SC8 / A8、B7 | compatibility、packages、user-discovery、regression-ci 各自通过兼容副作用、独立包全模块、使用发现/旧页面/浏览器内存凭据/纯文本及所记版本回归 CI；这些检查不替 A9。 |
| SC9 / A9、E1/E2 | 六项均当前 insufficient_evidence，决定整体受阻，详见下节。 |
| SC10 / A10、B8 | library-ingest/update/project-ownership 支持两创建端资料库、原始/规范化字节、身份/版本/CAS、幂等/删除墓碑、安全边界及伪造管理拒绝。真实 CLI epoch 竞态本次为写成功/恢复互斥失败；不冒称恢复先赢的另一竞争路径已实测，其他旧 epoch API 负控按其实际范围保留。 |
| SC11 / B6–B7 | listing-coverage 支持默认列表兼容、显式两端覆盖、离线保 Local、只读无隐式扫描/同步。 |
| SC12 / B6 | snippet-conflict 支持同版同窗/部分重叠冲突排除 Hub 候选、保可信 Local 正文，正常同文仍合并。 |
| SC13 / B1、B5 | cli-scan-boundary 支持远程认证 HTTP 无路径添加/refresh 能力、明确 Hub CLI 采集正控与原文；不把预期 404/405 当失败。 |
| SC14 / B6–B8 | web-review-feedback 支持两端逐份批次反馈、无凭据 Hub 管理入口、出处与精确回退实际读取端；真实 Chrome 经 TestClient 映射的范围不扩为平台 TLS。 |
| SC15 / B2–B3、B5–B6 | hub-status-provenance/retained-state 支持身份/项目/采集接收时间、暂停保留与允许状态、共享版本推进、来源/命中/原文一致。 |
| SC16 / B1、B8 | folder-guidance 支持实际目录拖放明确创建端目录指引、混合批次真实逐份结果与原文、未隐式扫描目录。 |

27 自动正式项对应 31 个实际分配检查，逐项 passed 只支持这些检查。SC8 的两个人工项单独有效；SC9 六项仍不足。与需求的完整映射不是按“35 项大多数通过”投票。

## 决定性未满足条件

### E1 三平台共有的两个原文证据缺口

SPEC `spec.md:154` 与 PLAN `plan.md:102` 明确真实 stdio 对本机未传、另一逻辑设备、Hub 自有独立正文的联合检索与准确原文；PLAN `plan.md:105` 明写产品停启后 CLI/MCP/Hub/Web 新进程读取同档案和有效 ref。不是额外要求所有入口乘上每个生命周期状态。

本轮直接枚举 Mac `/private/tmp/smm-007-macos-e1-v16`、`work/manual-evidence/linux-e1-ci-222-v1/platform` 和 `windows-e1-ci-222-v1/platform` 的全部五组 stdio 原协议：`mcp-1` 列来源/项目并查 A 项目，`mcp-3` 恰四次 read_document，`mcp-5` 只有 all search_documents，`mcp-7/9` 为对话 search/read。冻结 `mac-v16/hub_documents_platform.py:1663` 起的 stdio_checks 与 `e1-222e0e5` 同一结构：只有 A/B 的四文档经过 read，private 和 Hub D/E 只进 search 集合。缺少这些正文经 stdio 路由读回后的独立全文、码点及行号结果；短片段或 Web/CLI 正确不能排除入口特有的错误。

冻结 execute 顺序为 stdio → Hub Web → Local Web → lifecycle。实际协议与独立执行复审的 trace 时间一致，均先于生命周期停启。后段确有旧 native ref 的 CLI/API 读取，缺停启后 Web/stdio 读取；较早在创建/采集前的 prepare 停启也不能验证当前 ref。新进程连接、页面或 stdio 引用恢复条件可能改变结果，现有证据不能排除。

因此 `manual-e1-macos-final-v3` 以 `macos-protocol-recheck-v4.md` 的当前不足意见为准；原 `manual-mac-user-review-v3.md` 的完整 Mac passed 保留历史及有效局部。Ubuntu/Windows 的 `e1-ci-manual-review-v1.md` 同判不足。三平台的普通身份、包、CLI/Web/已经调用的 stdio、生命周期及清理局部均保留，不因缺证一并否定。E1 专项托管 Mac 取消不等于 Mac 产品失败；Ubuntu/Windows job 成功也不能补未执行动作。

### E2 两个真实服务的网页资料持久与清理缺口

`services-manual-review-v1.md` 对 run45201802511/head465d27e 的两服务有有效局部实测：Ubuntu UID1001 的 user-systemd；Windows SCM LocalService、SID S-1-5-19/session0，管理 CLI 与普通 Local 分开、普通 Local 无法直读 Hub DB；实际网页两份不同原文及更新删除、获准同步、外部 native 来源移走后停启仍读、PID/端口清理。

但 SPEC E2、SC9 `e2-linux-service-5`/`e2-windows-service-6` 还要求网页管理副本按新项目命中/read 及重启持久。本轮读取冻结 `service-465d27e/hub_documents_platform.py:1666–1744`，停启后只遍历 `d_entries + e_entries` 的外部 native 原文，没有保留网页 dropped 文档在原新建项目下的查询与旧有效 ref 读取。网页副本/资格持久化与外部采集档案在服务重启时可能有不同结果，不能由 native 成功推出网页持久成功。

Windows 冻结 SCM helper `:412–433` 发出 disable、sc delete、netsh delete，service-cleanup 仅保存 failures；netsh 结果未核且没有两者不存在的后验查询。已有真实 PID/端口退出有效，不能证明服务与防火墙配置均无残留。这是清理证明不足，未确认产品清理失败。

维护者明确选择“保留缺口，先完成其他验收”，所以不应用补证草稿、不再重跑。停止动作的授权不是豁免规格，两个完整服务检查仍不足。

### E2 不同 OS 真实机器未执行

直接读取 `work/manual-evidence/cross-machine-resource-v1/resource-observation.json`，actual_business_execution 为 not executed，明确禁止家庭 ESXi 且暂时没有替代。没有两台不同 OS 机器间认证 HTTPS、远程 Hub 浏览器创建上传更新、另一端按项目精确 read、版本/断线恢复和通道清理的业务证据。同机 A/B 独立档案证明逻辑身份，托管 SCM/systemd 证明指定服务条件，都不能排除跨机器网络、TLS及远程浏览器条件的差异。资源不足仍是 A9 阻塞，不是产品失败。

## 回归、推论与最终门禁边界

`regression-ci-review-v1.md` 的独立结论 passed 仅认 packages-2-gate：本机完整 pytest 334 passed、1 skipped；所记 `222e0e5` 常规 CI run45205399891 三系统测试/双包构建/分开安装 success。JUnit 每系统335项，Mac/Ubuntu329 passed+6 skipped、Windows330 passed+5 skipped；五个浏览器参数格因 test extra 无 Playwright 跳过，不能说各系统334全过或浏览器已由普通CI执行。本轮只读所记材料，未查询最终425f140 head CI，最终 head 项目门禁另核。

相同产品源码、Python/SQLite 共用实现与自动负控可支撑平台无关的协议/事务边界；不能证明本应实际执行却缺失的 stdio、停启网页资料或物理机器路径。本判定没有靠源码把这些缺口推成 passed。此前工具 IPC/权限/证据导出失败、预期拒绝或审计负控与正式产品失败分开：当前有效证据没有确认某必测产品行为实际失败，因此不判 failed。

依据完整 R007，必要环境与必需动作证据不足且条件可能改变结果，最终判 **blocked**；整体交付和合并前要求尚未满足。
