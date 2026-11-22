# SC4 complete27 人工准备独立复审

TC-005-sc4-evidence：**当前人工准备有效，可进入真实原件核验观察**。新增持续故障补充已区分前轮反例；本意见不是manual正式业务通过或R005判定。

Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:10:34.913373+00:00；AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。此前已实际读AGENTS、intent/spec/plan及PR Review/技能规则，本轮读PLAN12.4与全部27设计/匹配/调试/步骤，摘要：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc4/request.json` SHA256 `1e60555079df844ac7a600ff2b0bc4c03dd2d0a0056f1cd55fbafb760362bef1`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc4/result.json` SHA256 `0b71d084aa1652b8dfc99987ae9fa32a4d999522cee8973146f8eabb06bbfa08`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc4/request.json` SHA256 `0c198f806e5cce9e7600a992914f566c1fe8b731eae092d14c9853e989a3260b`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc4/result.json` SHA256 `5fcbdd32eeca1f161e20d51ab5259ac2714e02a094cb06e0fc3a074db7263875`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC4.md` SHA256 `4b9a24f53c34500e5bf78940732c4b7a1d44bb4e61612c32784abc38f47645de`


| 人工check | 可执行性、原件与版本准备 |
|---|---|
| complete-1 | 可观察。七主流程fixture-local/commands/stopped-state/backfill；独立old A、新A及旧会话assistant追加集合、B先推进，当前backfill四条精确集合/A顺序与bounded35完整session/position/role/body/time预期，真实原文/identity对照。 |
| complete-2 | 可观察。当前batch-failure两会话/两个故障、mixed两个顺序、unknown-receipt、timestamp与offset原断言不改；41外invalid_batch_receipt、hub_loss_of_receipts及federation跨设备同源副本/旧账本删除完整case继续分配。七平台真实前后canonical列表及old read保证平台身份链，当前单测不代替其环境。 |
| complete-3 | 前轮持续失败缺口已补，可观察。原bounded保持首次uploaded25且pending时B已推进、本机能新增/检索，最终独立35全量；新增repeated-fairness真实三轮A known均失败，每轮后仍pending，轮1/2前新B已经过真实add_local/sync，B完整集合从round0到round0/1/2且每轮uploaded1。若只第一轮B能推进，第二轮独立数量/正文断言立即失败。新附件读到A错误持续且allowed_pending1、B精确1→2→3；没有以队列清空后的可用代替中途进展。 |
| complete-4 | 可观察。E1三客户端/E2登录/E3 Linux systemd-user、Windows LocalService、Mac系统launchd/E4独立serve-hub七原事件均有安装包manifest、命令、真实账户/服务状态目录及backfill新旧完整read。按适用入口检查，不给E3额外加E1浏览器要求。 |
| platform | 可观察。与complete-4共享七真实原件，步骤保留的旧“某E3待完成”只能由实际原件及当前适用性核验得出新事实，不直接沿用历史passed；不依赖SC12未来总表/最终R005构成循环。 |

本轮debug-complete27-sc4九TC共11pytest参数真实10:05:52–10:05:57Z、全部exit0；全部运行bindings、stdout/stderr和附件SHA一致。新增repeated-fairness附件已实际逐轮读取，原批次/混批附件与真实调试绑定；41旧源码/身份/断言保留。原26 full-pytest235个case/完成receipt保留其实际范围，不声称其已包含本轮新文件；新增证据是本轮debug，正式execute仍须实际运行。

版本适用性沿用前轮已实际核对的完整依赖：ba8产品src未变，d80→ba8的Local upload/API/CLI/static对账及reference标题变更由ba8 reconcile21/current tests及scope11/15补，早期服务/导入/federation/Hub补齐相关闭包不变，不能只据单模块相等概括。原平台包、时间、账户不改；七新离线audit和正/负自检证明原件可核，不冒充平台重跑。已实际查看的原图均保留，当前SC4主要查完整消息/规则/服务原件；涉及画面时观察者仍逐图打开。

反例：只处理首消息/首会话由batch两会话、backfill追加/新会话及bounded35独立集合拦截；混批只接受首允许目标由allowed-first的bodies[]/receipts[]拦截；新跨轮B遗漏由第二轮集合/数量拦截。其余同条件更换名称/无限增加轮数是可选，不构成新的阻塞。

步骤末尾execute路径是后续正式入口，准备时只认已实际存在的debug；人工仍需实际读取/比较、如实写当前observed和原业务原时间/版本两层事实，并交另一位执行Reviewer。
