# SC3 人工准备独立复审 complete26

TC-005-sc3-evidence：**needs_revision（design）**。SC3 criteria源于B3/A3，没有发现额外产品要求；complete-3/complete-5的自然设计及可用原件未覆盖下列必需差异。不是产品failed、不是manual正式执行结论。Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:01:01.521200+00:00。

AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。已实际读AGENTS、intent/spec/plan、PR Review Prompt和所要求技能四份规则。

实际打开并绑定意见的源：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc3/request.json` SHA256 `17665051675ef93d0fe7816ceb35972e3f0754f183bd66c88d2087f2876d8619`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc3/result.json` SHA256 `db7073a256711fa31d2442efdb272accab59b8205950f489019e9cbd4357e1dc`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc3/request.json` SHA256 `f0897c9519538b4a8f887457e0c95827f17e956db8bc862b8a3024ca2ac7d8ee`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc3/result.json` SHA256 `7335a7176af925ebe199f4df7b34b2548949b9628d0152c93bf101c9bdc7068a`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC3.md` SHA256 `0f6e69041dc4595f86a9f5cf2e629936cc37340c79699180ae661e03163b94d9`


| check | 准备判断 | 核验内容与来源 |
|---|---|---|
| complete-1 | 可观察 | 三客户端browser-configuration/global/preview/applied/read_after_reimport，三global-cli11的完整G集合/取得结果，当前global Contract及test_project_preview_coverage实际数据库唯一集合。未知cwd用原始session_meta及明确project_id None，不能把空cwd直接认global。 |
| complete-2 | 可观察 | 当前global-query以独立A/G/unknown集合分别断言；三scope11及三global-cli11可核实际项目/全项目查询。必须定位本次A目标/显式A-G link前后，不能从两个查询相等推导范围正确。 |
| complete-3 | 需修订设计 | 当前identity/test_project_preview_coverage支持不同设备同名及rename保持，也支持assign/map/mergefresh和规则generation过期；但B3明定“会话归属、目标及规则版本，任一变化后须重新预览”。现设计action只改变generation，所有旧token负例同条件。若token只绑定generation而忽略target/affected仍全过。需保持规则版本不变，分别改变已预览会话归属和请求目标（另一有效项目）后用旧token提交，明确拒绝且完整项目/路径/关系/会话/assignment快照不变。源project_control._snapshot包含data/target/affected的静态阅读支持当前实现可能正确，不是实测拦截。 |
| complete-4 | 可观察 | 七主流程+scope原件的manifest、Hub project list/link命令、payloads逐项目字段白名单和禁止标记；当前default metadata白名单、query_only_registration及审计器检查补证。记录Hub真实id而非本机整数，逐owner/stable_key核对。 |
| complete-5 | 需修订设计 | move-project与move-batch逐assign/map/merge，禁止B阶段无known/upload且Hub按B无A、按A仍有A；允许B后独立消息/角色/物理实体完整、旧引用仍正确。move-retry真实丢归属确认及恢复另证充分。但B3/A3要求禁止B期间旧A引用也“仍可用”；源码两个move用例及scripts/acceptance/selective_upload_platform.py:578–595均等到允许B后才read old reference。平台affiliation-propagation只保存允许后的old_reference_read。合理错误仅在禁止B期间旧A引用报错、允许后恢复，所有当前断言/原件都不能拦截。需在禁止阶段立即逐旧reference读回独立原文，不能把A搜索命中等同于引用可读；多消息/多会话均受原承诺，不用只首个旧引用证明所有可读。 |
| minimal | 可观察 | 与complete-4相同的真实载荷与Hub最小项目登记；步骤中的“共享SC12”应引用SC12所用原始payload，不可依赖SC12将来的整表passed来证明自身。当前已有七主流程原件，不必循环等待R005或SC12最终通过。 |

当前debug7真实TC（含9个参数化move/preview分支）bindings与日志SHA都已重算，exit0；准备JSON中global/query/identity/retry各实际check有效，preview/move-project/move-batch的缺口如上，未以green日志掩盖。完整回归work/complete26-observations的receipt已完成09:53:42Z/exit0，235项234pass+1Windows专属startup skip；逐case查到global原contract、project_preview、project_identity、move三动作及retry，没有额外旧token改target/归属或禁止阶段旧引用读取。41以外的test_upload_mode_matrix六参数另分配complete-1（G与普通同级）与complete-4最小登记/未知来源不旁路；不是只看总数。

版本适用性需保留真实事件d80/f45/7c/ba8身份。已读d80→ba8实际diff及两份package comparison；core/project_control/importers/Hub项目和策略正文代码闭包不变，references.read增加范围标题，Local api/cli/static/upload改变双版本及CAS。三scope11与mac-hub-scope15对新范围读取补证，不用d80标题结论；三平台reconcile21对新对账补证。项目preview的state哈希实现虽未改，也不能因此把未设计必需变体称已测。七当前audit已读源码、已知正常/五负控测试及原receipt（所有exit0），只是离线原件核验。实际查看三客户端config-4-none画面（项目ID/普通与global并列）及三reconcile21旧视图拒绝图，完整人工观察仍须逐PNG/trace按check读取，准备意见不代替它。

只需为上述两种明确行为差异增加独立验证项/原件，不需修改或削弱已完成TC，也不要求同条件无限增加标识样本。新增后重新匹配、真实debug和准备复审，再进行当前manual观察。
