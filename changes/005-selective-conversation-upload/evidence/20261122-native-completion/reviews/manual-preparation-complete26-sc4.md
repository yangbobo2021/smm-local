# SC4 人工准备独立复审 complete26

TC-005-sc4-evidence：**needs_revision（design）**，complete-3尚缺A4明定“单个项目反复失败”的可判定跨轮检查，其他原件核验路径可执行。本意见不构成正式manual业务passed、执行复审或R005判定。Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:02:24.193771+00:00。

AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。已实际打开AGENTS、intent/spec/plan、PR Review Prompt及技能reviewer/design/implementation/execution规则。

本轮实际审阅源：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc4/request.json` SHA256 `6b6367de44bfdaea97c3f49c1636a37d6166baaeaa970c71cb29d05282dccdb8`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc4/result.json` SHA256 `88856694f8e1a51b9f7821358b06249c0d06335a3b84be83d0aea2d3ef403157`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc4/request.json` SHA256 `5ab4bed3c08bbb474c7972d20e0247c6ee2832a74df4374d8f4d325eda28de01`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc4/result.json` SHA256 `ce32666b8ab227f7f552e9826ca0675e74c31b00491476271556e9d80235685d`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC4.md` SHA256 `3f35c32460dd0b642427aac92865403c473f30bf5203d796dcb1ada2831f54c6`


| check | 准备判断 | 可核验的输入、结果与断言 |
|---|---|---|
| complete-1 | 可观察 | 七主流程fixture-local与命令时间线显示A旧/追加/新会话，B先推进，stopped-state与backfill。当前backfill TC独立expected完整4条及A有序原文，bounded TC独立35条含角色/时间集合。七audit当前读取每份backfill的expected会话集合、A两完整正文及new正文，必须人工再定位来源身份、顺序与对应原文引用，不能以audit.status代替。 |
| complete-2 | 可观察 | 当前batch-failure两故障/两会话、mixed-batch两个顺序、unknown-receipt和timestamp版本、offset-prefix保留；41之外分配test_upload_recovery::invalid_batch_receipt_remains_unknown_then_resolves_exactly、hub_loss_of_receipts_rebuilds_from_exact_existing_messages及test_federation::federation_offline_recovery_dedup_and_provenance（不同设备同源副本完整回归），实际JUnit各case存在且完成。七主流程backfill前后canonical_id列表及精确old read保留，不能把扫描数量等于确认。 |
| complete-3 | 需修订设计 | 当前bounded覆盖“队列没清空前”本机新增导入/检索及B推进，最后全部35条独立集合。fair-upload仅一轮一次A失败，B初始单条成功。A4原文明确共用故障须覆盖“单个项目反复失败”；若首轮A失败容许B、第二次以后A失败就堵其他项目，现有所有断言与正常平台原件仍可全过。需新增保持A持续失败、首轮后导入新B、后续轮实际再次A失败时新B仍被提交/查询读回、A继续待确认的检查。最早design补该状态，不需改现有TC身份/源码，也不要求平台整跑。 |
| complete-4 | 可观察 | E1三客户端，E2登录，E3 Linux systemd-user/Windows LocalService/Mac系统launchd，E4 mac-run8独立serve-hub各自有manifest安装清单、commands/local-service/service-events、backfill实际Hub命中及新旧精确read。后者实际状态pending0/inflight0/confirmed，A正文顺序old→assistant append及new会话都逐项核对。逐入口指适用入口，不额外要求E3也有E1浏览器。 |
| platform | 可观察 | 与complete-4共享必要环境原件，保留步骤原文“Windows/macOS系统级E3仍待完成”作为历史缺口描述；现在对应原件windows-hub-service-run8/mac-hub-main15已在清单，准备或观察只能由实际读取给出当前事实，不能删除旧描述或用历史passed填值。Windows真实NT AUTHORITY\LocalService，Mac系统launchd UserName <ordinary-user>/UID501；两者真实PID均改变，Linux用户服务亦不同PID。 |

已读当前debug8 TC全部实际命令、exit0及日志；batch两附件、mixed两个顺序附件均读取，源码绑定与摘要全部一致。work/complete26-observations/full-pytest的完成receipt 09:53:42Z/exit0已核对，235 JUnit中234passed+Windows专属startup skip，input绑定全部逐文件重算一致。已读审计器源码与已知正常/五负控自检（missing append/wrong original等故意假passed仍失败），其JUnit实际完成；新七audit为离线核验，绝不改称当前平台重执行。

版本闭包已用实际d80→ba8 diff核对：Local upload改变对账/CAS/目标栅栏，api/cli/static改变双版本，references改范围标题；导入/项目/federation补齐排队及Hub全部模块未因后续修改改变字节。旧业务原件保留原安装包/账户/时间；SC4无对账正常停止/补齐并非仅因Hub相同便全复用，受影响Local路径须由ba8 reconcile21及当前相关完整回归支撑，引用标题用scope11/15。七主流程original_files与包清单、service-events身份相互支持，不只单模块相等。实际读取旧批次前后完整集合和重启事件：E4 mac-run8 PID54870→55420、Linux E3 147555→148725、Windows2504→11036、Mac系统57818→58048，各重放两attempt均409且before==after。

反例边界：只处理首个会话/消息不能通过batch-failure两会话、backfill新旧追加、bounded35独立集合；允许/禁止混批首目标错误由两个顺序各拦截；被比较两端同错由手写expected内容/角色/位置与实际Hub完整集合拦截。待修订的是明确要求的持续失败条件，不是仅增加等价样本。补齐此设计及真实debug后再取得准备意见，manual整体才可进入正式观察并认领完整covers。
