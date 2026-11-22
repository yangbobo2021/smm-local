# SC2 complete27 人工准备独立复审

TC-005-sc2-evidence：**当前人工准备有效，可进入实际原件核验观察**。SC2设计/match仍complete26，本轮只补人工准备意见，未造SC2 complete27 debug、未修改或覆盖SC2原自动意见。

Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:09:40.283876+00:00。AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；已读AGENTS、intent/spec/plan、PR Review Prompt和技能规则，本轮重读PLAN12.4与27交接。

实际审阅当前SC2源：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/request.json` SHA256 `32c9199d8f8d9addfd53a6e1e1fec0600d72c3acac2561828ff89bafca529494`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/result.json` SHA256 `ec27232081a21c05f713ab2702abd4c7b6c4202a5c7bc6961f29cf05be4969bb`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/request.json` SHA256 `717a52acf9d16e651ea6d65cc040dff3dbc14caf60960f88ebecf17dc0f86dea`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/result.json` SHA256 `eb8e856e009b400443b3e030b52eb15ef61c78d87640b1bbfe708561a9728bd5`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC2.md` SHA256 `ebb6da9c020c8e059dd3a648d2bf8e085f0e9e2833bbf9d8aece31661f5b0f47`


本轮共享新暂停实测来自SC1的tests/test_complete_scene_boundaries.py::test_every_policy_save_preserves_paused_and_disabled_sources，TC-005-pause-source，debug-complete27-sc1/result.json（SHA256 `69263e74c6c129a5155a25f6a2b2fc359ebe1b1a23171d996c9aed54ed02b75f`）与四个pause-source-{all,only,except,none}.json附件；准备审查见review-preparation-complete27-sc1.json及manual-preparation-complete27-sc1.md。只共享其真实输入/断言/日志，不把该TC塞进SC2不存在的debug目标，也不借尚未产生的formal execute通过证明当前业务。

| SC2 check | 可执行性/证据可用性/适用性 |
|---|---|
| full1 | 可观察。七主流程停止确认、stopped-payloads、同步观察、真实本机新增；当前dispatch fence及cross_process_save_and_dispatch共用回归补未发任务重新判定，逐请求无body，与本机内容已归档联合看，不凭无请求推断未导入。 |
| full2 | 可观察。initial/after-hub-restart-replay中版本旧及无版本均409，前后正文完整相同；E3三账户/系统服务与E4 serve-hub身份原件、旧原文均可定位。当前CAS先实际允许正文的正控防拒绝全部。 |
| full3 | 可观察。26九自动TC及其有效意见不改，triple-order真实1/2/3提交与3/2/1返回，remote race12组合，inflight两参数，stale/write两动作；41之外receipt-loss/checkpoint/crash四参数/late_reply/cross_process逐case仍按原26 MD分配。 |
| full4 | 前轮缺口已补，可观察。新增SC1 pause-source在已暂停且两来源禁用的前状态，四模式逐独立case保存后立即比较整个settings和sources，精确pauseTrue与两个enabledFalse；正常push_pending无control_only，all/only确有允许待传1仍uploaded0/Hub空且无出站body，完整messages快照不变，sync_all调用会直接让探针失败。故先all解暂停再none恢复、只一个来源启用均在第一处对应设置断言被拦截；不再以早先只在none后观察的测试作唯一依据。真实服务PID/状态目录/旧重放仍按七原事件核验，不能用这四共用参数替代实际服务身份或重启。恢复全局后遵守规则由当前四模式/停止/正常补齐与服务回归分工承担。 |
| complete-5 | 可观察。三ba8 reconcile21真实旧视图/新鲜CLI/Web，以及SC2 current stale/write/remote-CAS已审断言；使用原payload双版本、Local完整row和Hub独立head，防两端同错。三张stale-local-rejected图前次已实际看，trace.network本次亦读到各200/400请求；正式观察逐图/逐POST核对。 |

SC2九自动保持其原26真实debug版本，产品src仍ba8，当前新SC1调试已核全部bindings/输出/四附件SHA一致且4参数exit0。旧235 JUnit不包含新文件，不冒称新全套green；共享补测以当前真实debug原件支持准备。早期平台d80/f45/7c原时间/账户/包路径仍保留，当前Local双版本/CAS变化由ba8 reconcile21和对应测试补，不仅因Hub字节相等复用全部Local；标题依赖由scope11/15补。

本轮是准备判断，不是暂停在三平台重新执行，也不是正式manual通过。steps中未列新SC1路径的“暂停自动导入回归”由本意见精确指向上述当前补充原件；manual登记时需以实际附件/引用纳入，并真实读取比较后记录observed，再交另一位独立执行Reviewer。
