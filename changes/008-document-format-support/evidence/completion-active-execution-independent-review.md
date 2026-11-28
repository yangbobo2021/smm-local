本报告为独立意见的脱敏副本；私有原件SHA见 completion-acceptance-20261128.json。

# AT-SMM-008 / SC8 正式执行独立复审

结论：**passed**，仅认领 TC-008-active-source-removal 本次执行的 active-overlap-retained、active-last-auth-cancel、active-stale-replay-slot。Reviewer：/root/completion_active_execution_review。未运行产品业务、未修改待审源码、证据原件、PR或其他记录；只写本报告与指定 review-inbox JSON。

## 正式目标与原始依据

工作树：<CHECKOUT>。
正式目标：.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc8-active-v1/{request,result}.json。
result.json SHA256：eb66623911500d4aa9f6219d8f4222dba572f7d047ff57b474f32c662f05b2b8。
request.json SHA256：a979f70003a7ec2ef68a8abdde210ac797f6340049d39f95ccbcc4ddd2e2b970。

实际读取 AGENTS.md、changes/008-document-format-support/spec.md、plan.md，以及 <HOME>/.agents/skills/app-delivery-acceptance-native/references/execution/reviewer.md。原始业务依据为 SPEC B5（71、77、79行）：原连续授权保留同一原件、最后授权丢失才取消、旧请求不能改状态或复活引用；B9（140行）：五秒内终态和活跃槽释放；A8（188行）：ready/partial和旧CID/AID/移除请求的行为。PLAN 43、71–91行约束独立真值、已保存快照、实际监督身份和同档案Hub服务接手。没有据此新增产品行为。

当前公共定义原件实际为 .acceptance/native-v1/AT-SMM-008/definitions/000003.json，独立重算 SHA256=16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633，与正式请求、正式结果和SC8一致。当前SPEC整文件 SHA256=99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986，等于定义 source.sha256；PLAN SHA256=dec2c26f2a1e2a91c375240a68aba7def11e4e25478cae27fff2ee6efc0b1626。

## 绑定与原件完整性

逐字节计算正式结果的86项bindings和2031项artifacts，全部存在且摘要一致。测试主文件 SHA256=9f12d6e6bdef98ce5309bd55a4162c393bae5595ae1ee8cf8f9b6132f631903b，屏障hook SHA256=1b7ba939281c26b33215f951082281fb0f04f9f15e1c76f9eb239e96466df8d8。

独核下列全部request摘要、result摘要及其bindings/artifacts；无缺失或不一致。match保存的source.text也与本次实际测试文件逐字一致，正式execute、debug、runtime及候选review的86项绑定完全相同，implementation_sha256及case_design指针一致；正式case_obligations仅包含上述三项。

| 收据 | result SHA256 |
|---|---|
| case-design/design-completion-sc8-active-v4 | 8a62967195756b68d4fe19411e969efd4e958d9be217a418f73096890bcb7653 |
| match/match-completion-sc8-active-v4 | 0ac46385148e38d5b96f8e6b6c5a9a26ede71de1ecec078654dfe276324c4a26 |
| runtime/runtime-completion-sc8-active-v4 | 2c703f68dd7decdc5dff61c7b89a7c405c31af559e74541400471cbed7ca940b |
| debug/debug-completion-sc8-active-v4 | cc136f23e9192026e5965371603415e5d8c08863731d9cab956b23492bd04b61 |
| review/review-completion-active-candidate-v4 | b15306b9e636ee536ae670a50908b815f282b18130bc277845b3d7c36279fd17 |

正式附件lossless-evidence.json的1671项逐一核gzip长度/摘要及解压后原长度/摘要，全一致；另核4份diagnostics清单的540项blob引用，全一致。本结论基于正式execute原件，候选调试结论只用于检查注册链，没有代替正式证据。

## 本次实际执行与三个检查

正式run.stdout原文为“3 passed, 1 warning in 38.45s”，exit_code=0，无skip；run.stderr为空。执行时间2026-11-28T00:18:37.034000+00:00至00:19:15.786000+00:00。三个实际测试为屏障/源读拒绝自检及Local、Hub参数化业务两项。

1. **active-overlap-retained**：tests/test_document_formats_active_source.py:53、59–61、153–165按两端×普通/全局×ready/partial×各两份生成并逐个执行，共16个独立document_id、16个独立取消token。157–159确认每目标实际两个不同source_id、同一document_id/完整快照身份；183核当前尝试仍绑定原CID且processing；185–189移除第一来源后，原worker和CLI仍在途，SQL对原CID的连续授权精确剩第二来源，旧ref仍读原文、全表和原件。不是另建CID后仅看文本相同。独核正式read与truth，16目标共176次全文逐全部源词恰好一次、无额外文字数字或排除文字；216次完整表格逐行列、单元格、跨度和location匹配独立生成真值；176次目标原件请求的SHA/字节数与实际下载及输入匹配，16原件下载逐字节摘要正确。所有目标已成功读响应相对其初始响应，只有允许的source_ids以及Hub sync_states因来源移除发生变化，其余字段保持。ready每份有3表，partial为原生第一页和像素超限第二页，115要求partial和具体第二页1600万像素失败。两个前态分别实测。
2. **active-last-auth-cancel**：132–147严格登记实际worker PID/创建时间/argv/exe及同token supervision路径唯一watcher；Local父为实际CLI，Hub父为已核验同state档案的实际HTTP服务（PID42151及创建时间），没有沿用旧“Hub归CLI”假设。191–198在最后来源DELETE前开始计时，五秒内同时要求failed、finished_at、active.json消失以及已登记worker+watcher每个身份退出；不是只等父CLI。本次16份原始事件的耗时0.031216334–0.129863958秒，16树均为真实worker+同token watcher两成员；对应workers与supervision原件的token/身份逐项一致。所有事件终态均failed且错误含采集授权失效。200核剩余资料/控制资料可读，201核被移除目标自身搜索零命中。
3. **active-stale-replay-slot**：202释放已取消token屏障，原CLI实际非零退出。204对每目标旧CID/当前取消AID/V/P的真实CLI拒绝前后核完整raw_state；207–210对每条旧text、每一旧table及original请求分别取before_read、要求400并核raw_state()==before_read==before。raw_state在126–131枚举documents及所有document_%、hub_document_%、hub_processed_%表的全部行，Hub强制包含hub_document_processing_jobs，故包括尝试、授权、来源、版本、处理ticket和receive/stage，而非只查公开状态。正式测试无skip且已走到每目标232观察事件，证明这些逐请求断言在本次实际执行到达并通过；并未把未运行的设计认作执行证据。16份旧CLI原始stderr分别为Local“重处理目标已过期或采集授权已撤销”、Hub“当前捕获没有有效采集来源”，均exit2。正式服务access原件每端20次旧read及8次旧original为400，共56旧引用，加16旧retry共72次拒绝。223–230每次再启动不同token的真实控制worker并核同保存CID、ready、槽消失和worker+watcher退出；两个控制资料的旧有效ref、正文/全表/原件仍正确。

屏障/禁源探针不是解析返回替身：lifecycle_hook只对相应raw SHA、真实--task-token和armed文件暂停原件打开，解析仍执行产品代码；源读审计先落事件再抛错。19–49的正式控制原件证明不带token/不同路径不会被门误拦、匹配token实际入门且释放后读到known raw bytes、明确禁止源读实际失败并留下唯一事件。75将hook安装到服务/CLI及实际worker；163删除合成原路径，164启用deny-sources，231逐目标核无source-opens记录。16正式取消事件均source_reopens=0，不把源路径消失本身当禁回源证据。

## 正式逐目标原件索引

以下文件均位于本次execute的TC附件目录，不是debug复制品。

| 正式原件 | 创建端/项目/前态 | document_id | 取消、终态和槽位秒数 | 树成员 | 旧请求数 |
|---|---|---|---:|---:|---:|
| 00214-active-source-last-removed.json.gz | local/普通/ready | 8f0b095a19bf46eb944a8fe54b0728e3 | 0.123618250 | 2 | 6 |
| 00322-active-source-last-removed.json.gz | local/普通/ready | 4ca0726743e04580be85b4309012e2ad | 0.096782750 | 2 | 6 |
| 00413-active-source-last-removed.json.gz | local/普通/partial | 3a9a84af315048a89f9d8becbe6c44c9 | 0.075443875 | 2 | 3 |
| 00496-active-source-last-removed.json.gz | local/普通/partial | e3858c0bcb6e41b087696a8eea08e754 | 0.076052875 | 2 | 3 |
| 00574-active-source-last-removed.json.gz | local/全局/ready | 72e08e9545c84f28908224a2096470ac | 0.097573208 | 2 | 6 |
| 00638-active-source-last-removed.json.gz | local/全局/ready | 6f3837c4ed01451395b2baf4135cde73 | 0.121175916 | 2 | 6 |
| 00685-active-source-last-removed.json.gz | local/全局/partial | 1dce3baf240e4bd0948b39d29ccc564b | 0.072000625 | 2 | 3 |
| 00724-active-source-last-removed.json.gz | local/全局/partial | ae4b0c65793243db8e6dd36596d1c179 | 0.102115666 | 2 | 3 |
| 00940-active-source-last-removed.json.gz | hub/普通/ready | 5ef85ac5105b4d689686f55124c63c21 | 0.031216334 | 2 | 6 |
| 01048-active-source-last-removed.json.gz | hub/普通/ready | 1b64664dd88e4195b77f46cc5031c712 | 0.129863958 | 2 | 6 |
| 01139-active-source-last-removed.json.gz | hub/普通/partial | 80ae73913c2b48a8a7ee55ccb6537a4d | 0.108154625 | 2 | 3 |
| 01222-active-source-last-removed.json.gz | hub/普通/partial | 3075a31cb16b4bb38304e13fcf84ba56 | 0.104001000 | 2 | 3 |
| 01300-active-source-last-removed.json.gz | hub/全局/ready | 62edc8ee1eff46e69832f2e0c5d042f1 | 0.032039833 | 2 | 6 |
| 01364-active-source-last-removed.json.gz | hub/全局/ready | 2259e2034e7f433a90341134836f3815 | 0.055419750 | 2 | 6 |
| 01411-active-source-last-removed.json.gz | hub/全局/partial | e325d3348e4d442f9dc50beb55ff9236 | 0.082364417 | 2 | 3 |
| 01450-active-source-last-removed.json.gz | hub/全局/partial | 296054eb6de24087918e90cf2edc172b | 0.063595583 | 2 | 3 |

## 反例逐断言核对

- **只首目标、普通项目或ready正确**：53及59–61建立并实际执行全部适用组合，165的循环没有在首项退出。后续目标在183/188会因原CID/授权错误失败，在198会因取消/槽错误失败，在209–210会因旧读或状态变化失败；缺组或状态也与16唯一document_id事件和项目创建原件矛盾，不能以首项正确通过全部。
- **Local、Hub两边同错，或两边误读同一目标**：99精确命中当前document_id、101自身原SHA与V/P、103另一项目零命中；110–115精确身份、origin、状态和各自源全文；116–123逐全部表格与各自原字节独立真值。若两个端都漏同一源词，111先拦；串成同一目标，99或110先拦；表格同错在120–122拦；不是比较两产品结果相等即可通过。
- **只CLI退出、漏watcher或错误归属**：136实际worker父身份断言先拦错误归属，143–146要求同token精确watch路径且唯一watcher；只CLI结束而worker或watcher仍活，198的all(not waiting_for_owned_exit(...))失败。exit observer对AccessDenied按仍等待处理，不把观察拒绝当退出。本次实际登记16取消树及16控制树，每树两成员。
- **返回400却悄悄修改业务状态**：旧retry在204完整比较首先失败；任一旧text/table/original在210独立before/after/基准三者比较首先失败。改旧attempt、版本、来源/授权、Hub processing ticket或receive stage均在126–131枚举范围内，不能借removed目标随后不再读而逃过。这正是v2的缺口，v4及正式执行没有再仅核HTTP状态。
- **仅单来源失效便取消，或失最后授权后恢复旧任务**：第一类在186 worker仍活/188原CID授权先拦，第二类在198终态树/槽或204、210业务状态比较拦。原件/结果已生成后的晚到发布另属未覆盖竞态，本用例未声称释放一个已退出worker屏障可以证明该竞态。
- **重开源文件或取消后槽永久占用**：源读审计落事件/拒绝及231逐目标零事件拦源读；若槽仍占用则198失败，若之后无法处理合法控制则223/226–228失败。实际正负探针和16控制成功记录同时支撑这两项。

## 身份、清理与范围

本次为macOS普通用户前景Python/CLI和独立认证HTTP服务。原件记录Python.app实际可执行路径、pytest-of-boboyang隔离临时档案及已核验服务/worker身份，当前宿主实读euid=501；命令直接从该前景上下文启动，没有sudo或系统服务调度。执行原件没有额外UID字段，不能把它包装成Windows标准账户或系统服务身份测试。

两个正式restart-server-stop原件exit0、forced=false；两端gate-finally cleanup原件errors=[]且original_error=null。保留的32个任务树（每端8取消+8控制）均完整登记，测试stop还验证服务停止及端口不可达。

设计/实现对本TC分配三检查充分且实际到达，未发现本范围需要返修的遗漏。覆盖不扩张到完整SC8、全部R008、Windows、系统服务、其它生命周期、总资源矩阵或真正结果已生成后的晚到发布竞态；这些不因本结论关闭。

历史保持：debug v1原始1 failed/2 passed为Hub worker父PID被错误假定为CLI的测试归属故障；debug v2即使3 passed，其review-inbox原始意见仍为needs_revision/implementation（旧引用读仅核400、缺逐请求状态对照），登记result仍blocked，reason=bound project files have changed。本次未修改/追认历史，也没有把上述测试故障或blocked登记改称产品红灯。
