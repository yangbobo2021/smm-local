# SC2 人工准备独立复审 complete26

TC-005-sc2-evidence：**needs_revision，revision_target implementation**，仅full4的暂停动作证据准备不充分；不把此结论伪装为产品缺陷或正式manual业务结论。Reviewer独立会话/root/review_complete26_prep_a；时间2026-11-22T09:59:01.473147+00:00。验收AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。

已实际读AGENTS、已确认intent/spec/plan、PR Review Prompt及reviewer/design/implementation/execution；以下文件均实际打开：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/request.json` SHA256 `32c9199d8f8d9addfd53a6e1e1fec0600d72c3acac2561828ff89bafca529494`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc2/result.json` SHA256 `ec27232081a21c05f713ab2702abd4c7b6c4202a5c7bc6961f29cf05be4969bb`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/request.json` SHA256 `717a52acf9d16e651ea6d65cc040dff3dbc14caf60960f88ebecf17dc0f86dea`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc2/result.json` SHA256 `eb8e856e009b400443b3e030b52eb15ef61c78d87640b1bbfe708561a9728bd5`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC2.md` SHA256 `ebb6da9c020c8e059dd3a648d2bf8e085f0e9e2833bbf9d8aece31661f5b0f47`


全套回归work/complete26-observations/full-pytest.xml及完成receipt已读取：235个实际case，234pass+1 Windows专属startup在Mac跳过；exit0，finished09:53:42Z，非仍运行的中间日志；input绑定全部重算一致。当前SC2九个debug真实执行各自选择器，含12参数remote-race、4模式fresh、两种inflight/两动作stale/write；不是历史green。

| check | 准备判断 | 真实核验入口/分工 |
|---|---|---|
| full1 | 可观察 | 七个主流程stopped-state、stopped-payloads、sync-observations、commands及重启前后原件。当前test_upload_recovery::test_cross_process_save_and_dispatch_share_one_durable_fence另分配此check：跨进程保存none后旧rows dispatch None，当前确认none，bodies空；test_upload_dispatch_fence三种配置和三种身份变化亦补旧快照派发。不能把无新正文仅解释成未导入，须结合本机新增及已结束同步。 |
| full2 | 可观察 | 主流程initial-stop-replay，E3三服务+E4/mac-run8的after-hub-restart-replay，实际两attempt均409，完整before==after；各有旧副本原文。当前CAS正控有效正文先成功，mixed-batch正控/拒绝补非“全部拒绝”。原账户与安装包由manifest、commands、service-events核实。 |
| full3 | 可观察 | 当前triple-order附件真实commit1/2/3及return3/2/1，Local全部ack字段；当前inflight失回执/新none、remote-race及stale/write。41以外明确分配test_upload_recovery的lost_policy_confirmation、control_interruption四参数、hub_checkpoint_crash、late_policy_reply及cross_process，JUnit逐case实际完成；不能只用一条triple日志代表崩溃全表。 |
| full4 | 需修订实现/证据准备 | 服务重启部分有原件：Linux systemd-user PID147555→148725，Windows真实NT AUTHORITY\LocalService 2504→11036，Mac系统launchd UserName <ordinary-user>且UID501 PID57818→58048；E4 serve-hub54870→55420，同状态目录与旧批次重放。E1本机重启及Mac专用登录服务有local-restart/login记录。但“暂停期间修改策略不恢复自动导入或正文上传”没有可判定的现有动作证据：test_upload_recovery.py:213–222只在choose(all)后显式control_only=True，而该参数自身抑制正文；直到choose(none)后才断言sync_paused。若all暂时取消暂停并启动导入，再none重新暂停，该测试仍可全过。平台步骤没有已暂停前状态及这两个动作后的导入/正文记录。需按原文B2/A2准备已暂停含待导入数据的状态，逐次规则保存后核对实际暂停、后台/显式同步均不导入/正文，恢复全局后新规则仍生效。test_maintenance中单独的preserve_pause未在upload选择动作上观察，不能替代。 |
| complete-5 | 可观察 | 三平台ba8 reconcile21的真实CLI/Web陈旧及fresh原件+当前stale-local和write-window、remote-race。必须按真实payload的hub revision/local gen及两端完整状态独立核对，不能只看错误文案。已实际查看三张stale-local-rejected.png，均显示本机规则改变需重新查看；其余adopted/stale-hub画面及trace可打开并应在观察逐项阅读。 |

版本闭包：已读d80→ba8 git diff及final-package-comparison21/reconcile-package-comparison15，完整Hub模块未变，Local upload/api/cli/static双版本/CAS路径已变，references标题亦变。原d80/7c停止/重启服务原件保留原提交、运行账户和原业务时间；不由单个Hub hash推出全部Local可复用。当前upload._verify_target/_save/reconcile的受影响路径以ba8三平台reconcile21与当前共用竞态补足；scope标题更改不改这里的正文停止，但涉及读回仍用scope11/15及当前引用检查而非沿用旧标题结论。七audit是当前离线审计不是平台重跑，已核对正/负自检实际JUnit。

本次不把其他同条件目标/规则名称变化无限扩成必测。缺口是原文明示“动作发生前已暂停”的状态和动作后导入/正文观察，具有不同业务预期，故需补准备；其余检查可以进入各自读取准备，整个人工TC仍待该缺口修订后正式观察。当前九自动TC各自分配checks有效且passed，未越界替manual认领。
