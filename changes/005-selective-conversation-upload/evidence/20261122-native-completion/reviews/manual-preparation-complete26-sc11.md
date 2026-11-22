# SC11 人工项准备独立复审

AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_c；时间 2026-11-22T10:00:44.886932+00:00。

结论：needs_revision，最早 design。TC-005-sc11-evidence 分配 full1/full2/full3/full4/complete-5。这里只审准备，不是正式manual结果。

## 实际审阅及摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc11/request.json` SHA256 `62331a825106bf8507f59be145ce396eb777497314a8f8530b35470f2ca800da`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc11/result.json` SHA256 `eebf830e17bdddc33d355121528e1925a8a98494b618263c000449178e2ac947`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc11/request.json` SHA256 `6cfc95586d0b425179e8caeb91b5150d36ed1cf8e6e9f6d6e3d86400e4195bb4`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc11/result.json` SHA256 `6b00f5e746e3183b52e97fe8fbd5d920587a92870f8788e90e77072e67f3712b`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC11.md` SHA256 `879c02bcb98de45a1c4e9d619606665d2133eff9e148c40a9133179ea422b2f9`。

已读取确认intent/spec/plan、AGENTS、PR Review Prompt及技能。SC11 criteria由A11/B8/D1/D4及B1双版本条件更新推出，无额外义务。

## 逐检查可执行性与版本

| 检查 | 准备判断与原件 |
|---|---|
| full1 | 可执行。mac-run8（E1/E4）、linux-client-run8/windows-client-run8（E1）、mac-login-run11（E2）、linux-hub-service-run8/mac-hub-main15/windows-hub-service-run8（E3）均有实际manifest、安装模块、local-restart none/confirmed、local-restarted三入口原文、stopped-payloads、backfill完整Hub结果、旧引用读回和cleanup无失败。service-events实读：serve-hub PID54870→55420，systemd-user147555→148725，Windows服务2504→11036且owner LOCAL SERVICE，Mac系统launchd57818→58048且UID501/PPID1/UserName <ordinary-user>。E1 Windows是elevated_admin=false普通<ordinary-user>，不能把E3管理员编排身份当成E1。登录服务另查commands中的真实launchctl print/definition/PID，不拿本机前台进程替代。7份新offline audit receipt分别exit0；其探针代码及正反自检在tests/test_selective_upload_audit.py/test_selective_upload_probe.py和本轮JUnit可核，正式观察仍要核原件，不靠audit passed。 |
| full2 | 可执行。R1 prepare清单含SQLite/.hub.json并排除guard/lock，原业务停本机服务后用SQLite.backup恢复并重启，差异local all/conflict、Hub none；R2为真实serve-hub prepare、停止、原目录重启，保护guard原字节不变、epoch改变且Hub restore_pending/conflict。原始commands、backup-identity、restore-preparation、difference-before-decision、adopted-stop、allowed-backfill可串联。当前两个auto分别验证明确采用Hub和未决定时真实正文/指纹阻断，不以status自证。 |
| full3 | **需修订design：实际Hub已确认消息丢失的前置状态未落实**。SPEC A11 E5要求“Hub数据库回到缺少最近消息及限制的旧备份”；B8要求旧确认失效并重补当前允许缺失。实际selective_upload_recovery.py::initial在初始all及消息均已上传之后做备份，随后stop_and_append立即none后才新增；R2/R3 commands从all同步直接到none/追加/prepare，没有backup后新正文先被Hub确认的阶段。因此其恢复会丢新限制，却没有丢已确认近期正文，allowed-backfill的追加此前从未在Hub，不能验证旧正文确认会否错误跳过丢失内容。当前test_hub_loss_of_receipts_rebuilds_from_exact_existing_messages的确以空备份→发送first exact→恢复验证confirmed_messages归0/再传1/重复0，JUnit passed，应分配本check共享分支补充；但源码TestClient不能替代A11点名E5独立安装包恢复情形。最小补足为一个E5支持平台独立任务：先备份，后实际允许并确认一条独立新消息，再形成新限制/禁止消息，prepare→停Hub→恢复→原目录重启→明确对账，仅补当前允许的已确认后丢失集合并比较完整正文/身份/重复同步。无需重跑3OS全矩阵。R3配套hub.json在恢复清单内且guard始终排除，按受支持流程核对，不要求违规覆盖恢复标记。R4原件upgrade-failure-recovery显示真实Hub.upgrade/systemd重启/health异常/restore，stop_before_failure none→新epoch/conflict，明确保留offline-installer success stub边界，不宣称真实下载迁移。 |
| full4 | 可执行。TRIAL_GUIDE.md:189–210给真实状态目录取得方式、SQLite一致性备份/停服务、prepare恢复清单/禁止覆盖guard、重启差异与CLI/Web两版本和不支持任意回滚；README主路径链接可达。当前test_public_prepare_restore_command_marks_the_actual_standalone_archive、test_stale_diff_and_target_changes_require_explicit_new_choice等JUnit passed。只读对账用当前原始row/Hub规则前后全结构断言核，不只读expected。 |
| complete-5 | 可执行，必须引用ba8。mac/linux/windows-reconcile21均manifest ba8，真实CLI旧本机generation exit2、Web旧本机与旧Hub均400；请求绑定所显示双版本，拒绝前后local_rule/Hub头不变，rejected_policy_calls中无该设备set；fresh CLI confirmed/all，刷新后Web采用Hub none。三个stale-local-rejected.png均已打开，见红色“本机规则已改变，请重新查看对账差异”；还应按步骤观察stale-hub/accepted原图及trace，不能以我本轮准备图检替代后续manual。当前12组合remote_race、stale_local两use、write_window两use、fresh四mode、uncertain两fault在JUnit逐case通过，归到此项。 |

## 当前证据适用性与反例

产品ba8冻结。原主流程d80、登录f45、MacHub7c和恢复d80保留原时间/版本。已实读d80→ba8 diff：API/CLI/Web只双版本对账，references新范围title，upload目标核对/对账实现改变；core、federation、project_control及服务/锁基础闭包未变，最终Hub完整模块相等。旧恢复的prepare/服务/guard证据仍可用；旧Local对账不能证明当前拒绝不改规则，必须用ba8 reconcile21和当前完整row CAS断言补。不能仅凭Hub模块相等宣称整个恢复闭包不变。

本轮full-pytest receipt已完成exit0（09:51:54→09:53:42 UTC），inputs SHA2f79acd1d49efec1b4043a1616ed4d21b76499f695e4e9d5e646b1b4e2eec4d1、stdout SHA b6499cb14c758394b549bc2bf0c9b57f508fc0a90b894f3a1d7c55a2685173d3实算一致。逐case核对恢复/对账/standalone声明，41TC外的test_hub_old_database_and_joint_restore_never_reopen_stopped_rule、test_missing_control_never_defaults_to_allow_and_can_be_explicitly_repaired、test_hub_checkpoint_crash_recovers_only_committed_submission等分配到full2/full3保护路径；未把本机Windows startup skip冒充执行。

首目标/前状态：unreconciled用两个本机独立原文及完整物理Hub空集合，任一一条违规上传会在完整物理集合/无upload-known载荷断言拦截，两个view_first前状态各检查conflict/desired/remote none；local restore明确正向采用Hub none作正控，单纯永远阻断无法通过confirmed。reconcile两端同错由独立fixture none/all及完整row、真实Hub CAS新头拦截。full3所缺“曾确认、恢复后丢失”与“从未发送”是A11有据的不同动作前状态，现有平台断言放过前者错误，不是换标识的等价补样本。先补该前状态的设计/原件并刷新匹配，保留现有通过分项。
