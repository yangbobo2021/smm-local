# SC1 人工准备独立复审 complete26

结论：TC-005-sc1-evidence **needs_revision（implementation）**。其余可执行核验继续准备；本文件不授予manual业务通过或R005通过。

Reviewer：独立子会话 /root/review_complete26_prep_a；实际只读审查时间 2026-11-22T09:57:39.187369+00:00。验收AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。已实际打开AGENTS、intent/spec/plan、PR Review Prompt和reviewer/design/implementation/execution规则。

实际审阅文件（相对项目根<task-path>
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc1/request.json` SHA256 `ea8e5969602098deed13ec774654266ef59fc377a1b9293d6b7b45a9e02ce0f9`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc1/result.json` SHA256 `150c675a5c50c9ae366f40b5620cbf1ac9d94d934bb63111c55b0db5d7d626e3`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc1/request.json` SHA256 `a1d959b3388dcecbf79f99c3e1b9747e2363ac553cdcef527df59bba062e0bc6`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc1/result.json` SHA256 `de129936fe8abc1d6a12212404d4f238250b2faaa96f275fc893305e30438072`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC1.md` SHA256 `446f0d5c4768f72853531131fa71da40c6ad853ffc472a3607f136dcbd5bac56`


当前源码为ba8产品字节，HEAD额外测试；所有SC1 debug bindings与当前字节一致。full-pytest完成receipt为work/complete26-observations/full-pytest-receipt.json，09:51:54Z–09:53:42Z，exit0；逐case读取235 JUnit，234通过、Windows专属slow-background启动项在Mac跳过。输入清单所有hash已逐文件重算一致，不能用234总数代替下面分配。

## 检查分工及证据准备

| check | 准备判断 | 实际原件、断言与适用性 |
|---|---|---|
| full1 | 可观察 | 七个主流程new-connection-status、commands、payloads及Hub查询；三客户端新连接均有A/G/U/插件多目标。自动default以独立remote正文对照、本机session/body标记和metadata字段白名单；人工须按连接至首次明确选择的真实时间窗检查全部请求及初始Hub集合，不能仅看needs_selection。 |
| full2 | 可观察 | 三客户端browser-configuration的六个保存响应和实际CLI状态，config-0到5截图/trace。共用JUnit另分配test_upload_mode_matrix六参数及test_upload_policy的六模式/空名单和invalid_choices；这些不在41身份内也仍是full2证据。独立expected集合分别覆盖A/B/G/NEW，错误后比较原规则和generation；若只首项目正确，模式集合比较首先拦截。 |
| full3 | 需修订实现/证据准备 | 原文B2及A1明确“保存规则不改变本机来源启停或全局暂停”。当前步骤说核对“暂停/来源开关的回归断言”，但tests/test_upload_recovery.py:213–222只在开始设sync_paused=True，choose(all)之后用control_only=True禁止正文，最终仅在choose(none)后读一次sync_paused。它没有验证每次规则动作后暂停保持，也未设置/断言任一来源禁用状态。主平台流程未配置这一前状态。合理错误：choose(all)把暂停解除/把已禁来源开启，choose(none)又恢复暂停；现有该测试仍可全过，其他源启停测试未在这些动作之间观察，不能拦截B2违反。需用已禁用来源及已暂停的前状态，在每次适用规则保存后检查实际来源状态/暂停及自动导入与正文不启动；至少把准确回归选择器/原件绑定到本check。单纯读取src中当前没有写这些字段只是推论，不能作为“已核对回归断言”。 |
| full4 | 可观察 | 三平台manifest独立安装包、local-service/commands、browser-configuration及配置trace，逐操作先定位目标mode/projects，再分别比Web/CLI及持久状态。已实际查看三平台config-4-none.png，均有配置标签、全部不上传、项目ID/类型及状态，不能仅凭Web/CLI两端相等排除两端同错，须与操作输入比较。 |
| complete-5 | 可观察 | 三平台reconcile21原包ba8、reconcile-result、commands、payloads和reconcile-browser-trace。已实际查看三平台stale-local-rejected.png，均明确显示本机规则已变/需重新查看。每个平台还应查看stale-hub-rejected/adopted-hub-current并定位POST；SC1 CLI/Web输入、SC2 stale/write-window/remote-race/fresh为当前细粒度补证。 |

full3的旧包迁移/真正目标切换原件实际在platform-debug/{compat-run8,linux-compat-run8,windows-compat-run8}/{migrated-old-device,actual-hub-change,old-smm-local-identity,manifest,commands}.json（commands为jsonl）；本次已打开对应身份/结果：旧包模块路径、真实旧设备、迁移all confirmed且uploaded0、另一hub_id变needs_selection。SC1步骤原目录清单未列这些，正式核验时须明确附这些原件而不是只用新包仿造legacy测试。same-Hub URL/token/device_name变更由当前test_upload_dispatch_fence三参数另分配full3：保留all，旧派发0，随后新派发1；正常空目录不等价于来源已禁用。

## 版本与探针

已读d80→ba8实际git diff：改变Local api/cli/static的双版本入口、upload的reconcile/CAS/目标栅栏，以及references.read的范围标题；其余导入/项目/服务模块不是只挑一个hash判断。七个audit的当前receipt exit0，原包安装清单保持各自d80/f45/7c真实身份；不能凭Hub模块相同就声称Local对账已修复。对账由ba8三平台reconcile21及当前竞态补足；标题读取由scope11/15补足，SC1主要观察规则配置，不借旧标题证明新行为。已读audit源码及正控/五种负控自检，JUnit含这些实际case；audit只复核原件，不是平台重跑。

目前full3缺少上述已停来源/逐保存暂停的真实断言准备，因此此manual项暂不可作为完整覆盖进入正式观察后报告全通过。修订应限补这类前状态观察与准确源绑定；其余相同条件下更换标识属于可选补测。SC1四自动TC已按其各自实际covers单独给passed，不用人工缺口伪造自动失败。
