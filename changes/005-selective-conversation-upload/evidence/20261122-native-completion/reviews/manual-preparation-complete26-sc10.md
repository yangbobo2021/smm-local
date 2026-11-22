# SC10 人工项准备独立复审

验收 AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_c；时间 2026-11-22T09:57:56.988544+00:00。

结论：needs_revision，最早 design。TC-005-sc10-evidence 分配 complete-1/complete-2/complete-3；本意见不登记正式人工观察。

## 实际审阅及摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc10/request.json` SHA256 `b6687cde8cf91a1a27d90f9835970f5aff3a0a2c2572d03d1584ba44cedb1182`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc10/result.json` SHA256 `1dfff4df9472990ede2a518c62833090fb1276a751edeb35a4335698af36cb8c`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc10/request.json` SHA256 `7e424267cb25483fbdd7092c542cedae6f196221929a2270d31db56a2c479197`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc10/result.json` SHA256 `11d78458310f300c46aee3a69a71b703b158d55d6e8d86a3b57ebcb0e1e36c15`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC10.md` SHA256 `639ce2a995cb095ca304e139c89e368882b121d0a2f63e1340c8d3ca4e988149`。

已实际读取确认意图/SPEC/PLAN、AGENTS/PR Review Prompt和技能复审约定。SC10三条criteria来自A10/B8/D1-D2，无额外产品义务。

## 逐项检查

| 检查 | 可执行性与证据准备 |
|---|---|
| complete-1 | 可执行。compat-run8、linux-compat-run8、windows-compat-run8的manifest保留各OS、d80候选、独立Local/Hub安装；old-smm-{local,hub}-identity.json记录真实v0.4.0源码4d58202、19个Local/21个Hub模块、0.4.0版本与旧wheel摘要。new-local-old-hub.json中sync实际uploaded=0/pending、说明旧Hub不支持规则；combined有new-device与old-device及capability_limitations，scoped仅new-device、hub=unavailable。commands.jsonl记录新/旧解释器的-I命令与原文读取，不是新库伪造旧库。new/new也由同目录升级后真实新Hub及新Local同步/状态覆盖。正式观察须核对请求路线没有scoped对应全局Hub /search，不仅看最终结果。 |
| complete-2 | 可执行。三个目录migrated-old-device.json均旧设备升级后state confirmed/all；旧进程追加被拒，exit1且HTTP409，旧整数/Hub消息定位读回独立夹具原文selective compatibility old-device original；before/after实际正文保留。unmanaged-old-local.json含另一旧设备unmanaged-legacy实际正文。current TC-005-register还比较完整Hub正文集合，仅other-device合法历史，避免只看错误码。actual-hub-change.json记录新Hub needs_selection和同设备旧进程拒绝、Hub无正文。 |
| complete-3 | **需修订 design：缺升级前已有关联状态**。A10原文明确“显示名、项目键、旧关系及引用保留”，当前自然设计只写“核对……项目身份和旧引用”，没有建立非空旧关系的前置数据与观察动作。实际selective_upload_compatibility.py::new_archive只建一个A，execute_combinations没有link/rename；三个commands.jsonl亦无link/rename，全部原件没有可比较的旧关系快照。migrated-old-device before/after保留相同owner/source_key/name的A，可以核对该身份及旧原文，不能证明非空旧关联保留。tests/test_project_identity_boundaries.py:9–36虽有非空Hub links对照，但动作是新库改名，不是已有旧库升级；test_existing_legacy_upload_migrates_on_background_restart_without_reconfigure仅单A+合成游标。错误实现若升级时清空project_links但保持项目行/消息，现有真实兼容及当前回归仍能全过。最小补足是用真实旧包创建至少两个项目及非空关联，保存独立项目键/关系/旧引用，升级前后逐集合比较并验证该关联查询；先补设计，再匹配实际原件或最小专项实跑，无须重跑全部三平台组合。 |

## 版本、证据和边界

原业务时间分别为mac 2026-11-22T05:54:42.652447+00:00、Linux05:54:44.360122、Windows05:55:07.374637；版本d80不能改标ba8。本轮不是平台重执行。三个cleanup均failures=[]。旧Hub→新Hub保同状态目录/同hub_id，实际新Hub更换另目录/另身份。旧包来源模块清单可独立核；对当前适用性须沿federation.configure/push/legacy候选/read、LocalUpload迁移/sync_policy、Hub register/legacy gate与旧引用闭包检查。已实际读git d80→ba8相关diff：API/CLI/Web只新增双版本对账，references仅新范围title，upload新增目标检查及重写reconcile；federation/core/项目模块不变，Hub最终完整模块相同比较保留。对账变化须由当前CAS回归及reconcile21补，不能用旧拒绝先改本机的原件证明新拒绝语义。SC10旧式读取不走新reference标题生成分支，可复用其真实正文/定位结果；不据此认领新范围标题。

full-pytest完成receipt exit0、inputs摘要2f79acd1d49efec1b4043a1616ed4d21b76499f695e4e9d5e646b1b4e2eec4d1已实算；逐case读取JUnit：test_legacy_hub_global_search_is_readable_but_project_search_stays_local、test_existing_legacy_upload_migrates_on_background_restart_without_reconfigure、test_database_without_managed_flag_still_rejects_old_client、test_query_only_registration_fences_same_device_legacy_writer passed，分配到complete-1/2及游标正文补充，不把它们当成旧非空关联迁移实测。

首目标/前状态推演：自动adoption以managed与unmanaged两个真实不同设备分支、独立expected正文区分，误把二者同目标或一律拒绝分别由200/409与正文集合拦截；等价同状态设备改名属于可选补测。complete-3缺的是动作前已有非空关系，A10明确要求保留，不能用升级后才创建的关系或新库改名替代。因此人工项整体现不能作为完整已准备通过；已有有效兼容原件应保留，不需推翻已测分项。
