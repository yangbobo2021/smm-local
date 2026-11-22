# SC2 complete28 人工准备独立复审

TC-005-sc2-evidence：**准备有效，可进入真实原件核验观察**。SC2仍design/match/debug26与原九自动TC，本轮只更新人工MD，未创建假debug或自动意见。Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:20:02.329501+00:00；AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。AGENTS/intent/spec/plan/PR Review及技能规则已读，本轮28交接与共享新证据实际核对。

当前SC2自然设计/匹配/步骤真实摘要：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/request.json` SHA256 `32c9199d8f8d9addfd53a6e1e1fec0600d72c3acac2561828ff89bafca529494`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/result.json` SHA256 `ec27232081a21c05f713ab2702abd4c7b6c4202a5c7bc6961f29cf05be4969bb`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/request.json` SHA256 `717a52acf9d16e651ea6d65cc040dff3dbc14caf60960f88ebecf17dc0f86dea`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/result.json` SHA256 `eb8e856e009b400443b3e030b52eb15ef61c78d87640b1bbfe708561a9728bd5`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC2.md` SHA256 `ebb6da9c020c8e059dd3a648d2bf8e085f0e9e2833bbf9d8aece31661f5b0f47`


共享SC1当前28暂停实测：debug-complete28-sc1/result.json SHA256 `b82cbc716931e67b958127ed30a4b5696d9de1e5330800a5e6c6be255e363304`，TC-005-pause-source四附件pause-source-{all,only,except,none}.json及当前tests/test_complete_scene_boundaries.py::test_every_policy_save_preserves_paused_and_disabled_sources。已实际读每附件，全部输出/附件/源码绑定SHA一致；其准备意见review-preparation-complete28-sc1.json已就绪，仍不是SC2自动执行或manual正式结果。

| check | 当前可执行核验分工 |
|---|---|
| full1 | 七主流程stopped-state/stopped-payloads/sync/本机新增及命令顺序，cross-process保存/派发与配置/身份快照变化当前共用case支持，确认无新冲突body同时核本机已归档数据。 |
| full2 | E3三系统真实服务及E4 serve-hub的initial/after-restart两次旧版/无版409、完整before==after、旧原文；当前CAS有效正文正控确保不是拒绝全部请求。 |
| full3 | 26九自动及其有效原意见保持：triple提交1/2/3返回3/2/1、remote-race12、inflight/stale/write；当前28 full JUnit也逐case覆盖。41外lost-receipt/crash四参数/checkpoint/late_reply/cross_process继续按26原分配，不只看总数。 |
| full4 | 共享当前28 pause-source四参数补准备：保存前两来源disabled+pauseTrue，保存后立即整个settings/sources不变和每个enabledFalse；正常push无control_only、all/only允许待传1仍0body/Hub空，无sync_all启动、持久消息完整不变。若all解除暂停再none恢复，all即时设置比较已失败；只一个来源开启由逐source断言失败。真实服务重启账户/PID/状态目录与限制重放仍由七原事件支持，此共享测试不冒充三平台新暂停业务。 |
| complete-5 | 三ba8 reconcile21真实CLI/Web陈旧/fresh双版本及两端完整状态，26当前有效stale/write/remote-CAS断言支持。已实际看过三旧视图拒绝PNG与trace.network；正式观察还须逐图和POST核对。 |

28完整回归已结束10:15:57Z/exit1，252 JUnit=248pass、3fail、1Windows专属skip；三fail均SC3构造message.reference KeyError，未进入其业务动作，不关联SC2暂停失败。当前pause四参数与SC2所分配共用case均实测pass，不宣称整套green。全input绑定重算一致，七离线audit0是核原件而非平台重跑。

产品src仍ba8、原平台d80/f45/7c时间/安装包/账户保持；受影响Local双版本/CAS与范围标题仍由ba8三reconcile21/scope11/15及当前测试补证，不能单靠Hub相等复用全部Local。SC2全check准备范围可进入实际人工读取/比较，R005整体仍有SC3待修；manual须把共享28原件准确列附件/引用并记录本次observed，再由另一位独立执行Reviewer复审。
