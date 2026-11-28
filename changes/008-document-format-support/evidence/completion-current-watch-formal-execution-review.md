# AT-SMM-008 正式 watchdog-health 独立执行复审

Reviewer: `/root/completion_watch_formal_review`。本上下文未参与本批候选设计或调试；仅写本轮意见和报告，不修改产品、测试或历史，不执行业务。

依据：实际读取项目 AGENTS、008 intent/spec/plan、app-delivery-acceptance-native 与 reviewer 规则。当前定义 `000003` SHA `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。分配仅 `TC-008-watchdog-health` / `watchdog-health`；设计 `design-completion-sc10-watch-observer-v1`，match/runtime v5，候选 debug Local/Hub v3。

正式执行不直接沿用候选判定。逐目标核验原始 result 字节、全部 artifacts SHA 和 94 bindings；与当前源码及候选 source 冻存字节比较。动态 `tests/document_formats_restart_server.py` SHA `08be26fa4abc0e3eb220dd8b15cb94ff486977c7f02fe7b7f955283aca4a13c8` 已纳入。正式 execute 本身没有 source/ 副本，所述冻结源由同绑定候选 source/ 核验，不虚称 execute 自带源归档。

## Local 正式 v1：passed

Result SHA `da5d1649a77476571c98f2e4d2539bd35b7558f4669b21270c28cb743d501a50`。6,208 artifacts / 14,196,616 字节、94 bindings 全部匹配；pytest 退出 0，1 passed in 41.41s。

12 个独立目标完整覆盖普通/全局 × none/ready/partial × denial/exit0，含正常对照共 13 组真实 worker、后代、独立 watchdog 登记。故障注入前已独立核 ctime/argv/exe/cwd、父子、token/nonce 与真实存活；只针对已登记活 worker 的命令行观察注入 AccessDenied 或使 watchdog 实际 exit0。故障后的同 AID failed/finished、进程树与 active 槽位、临时 payload 回收为 0.071670–0.140328 秒。

5780 个实际 HTTP、199 组相同引用全文/表/原件信息/原件响应均已独立解引用并核一致；下载原件与保留原字节 SHA/长度一致。测试中源真值全文与全表断言实际通过，none 无发布，旧 ready/partial 及其他资料保留。12 次同 CID 新 AID 明确 CLI 重试和 12 个后续服务任务均到达合法完成及读取断言。40 历史成员最终 absent，服务 exit0、forced=false，端口不可连接断言实际通过。

| 目标 | 故障 | 失败与回收秒 |
|---|---|---:|
| localhealth0none0.pdf | denial | 0.140328 |
| localhealth0none1.pdf | exit0 | 0.082272 |
| localhealth0ready0.pdf | denial | 0.120921 |
| localhealth0ready1.pdf | exit0 | 0.104600 |
| localhealth0partial0.pdf | denial | 0.095934 |
| localhealth0partial1.pdf | exit0 | 0.115771 |
| localhealth1none0.pdf | denial | 0.071670 |
| localhealth1none1.pdf | exit0 | 0.102908 |
| localhealth1ready0.pdf | denial | 0.106128 |
| localhealth1ready1.pdf | exit0 | 0.134149 |
| localhealth1partial0.pdf | denial | 0.128048 |
| localhealth1partial1.pdf | exit0 | 0.123488 |

意见：`.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-watch-local-execution-v1.json`。

## Hub 正式 v1：insufficient_evidence

Result SHA `60ed485c1516e5827a1868e354e3f8ad273bedef44435f3295054519adef9306`。2,026 artifacts / 20,672,165 字节、94 bindings 全 SHA 匹配。执行器 60 秒超时：03:42:23.264Z–03:43:23.273Z，exit_code=null，stdout/stderr 空。原生 status=executed 只说明执行记录存在。

只有普通项目 none/ready × denial/exit0 的四个目标完整到达失败、同 CID 新 AID 重试及后续任务；六次登记含正常对照与第五目标。其余 8/12 故障链、最终测试内清理及 pytest 结果缺失。不能从候选通过或 Local 结果补成 Hub 通过，也无证据将执行器超时判为产品缺陷。

单列后续清理 `watch-hub-formal-v1-exact-cleanup.json` SHA `d9e85e2ef9553fa723000ab61d29ee794c0d939f015de71a7c7616bec2c3ba83`：PID/ctime/argv/exe 对应本轮服务，shutdown200、所属进程/后代消失、端口关闭。该文件不证明原测试 finally 完成或服务 exit0/forced=false。

意见：`.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-watch-hub-execution-v1.json`。

## Hub 正式 v2：passed

Result SHA `7e389a37361b534773a25f13b9f1b0951195c88dc2c6dfbc619d2e00375233f4`。5,963 artifacts / 20,438,812 字节及 94 bindings 全 SHA 匹配当前源和候选 Hub v3 冻存，match/runtime v5 所用同版。实际 pytest 退出 0，1 passed in 241.79s；执行器记录 03:46:33.265Z–03:50:35.313Z。

12 个独立目标完整覆盖普通/全局 × none/ready/partial × denial/exit0，13 组真实进程登记含正常对照。12 故障的同 AID failed/finished、三成员退出、active 槽位及临时 payload 回收为 0.195249–0.432980 秒。5500 条实际 HTTP 和 199 组同引用读取/原件响应已独立解引用核一致，保留下载原件摘要/长度与原字节相符。源真值全文/所有表、旧快照/原引用、未关联资料保护的实际断言均通过。

12 次同 CID 新 AID 明确 CLI 重试及 12 个后续同服务任务均成功；40 历史成员最终 absent，服务 exit0、forced=false，端口退出断言通过。该新尝试与 v1 分别判定，v1 仍为 insufficient_evidence。

| 目标 | 故障 | 失败与回收秒 |
|---|---|---:|
| hubhealth0none0.pdf | denial | 0.275031 |
| hubhealth0none1.pdf | exit0 | 0.290210 |
| hubhealth0ready0.pdf | denial | 0.195249 |
| hubhealth0ready1.pdf | exit0 | 0.335528 |
| hubhealth0partial0.pdf | denial | 0.337997 |
| hubhealth0partial1.pdf | exit0 | 0.365839 |
| hubhealth1none0.pdf | denial | 0.408602 |
| hubhealth1none1.pdf | exit0 | 0.432980 |
| hubhealth1ready0.pdf | denial | 0.277975 |
| hubhealth1ready1.pdf | exit0 | 0.263367 |
| hubhealth1partial0.pdf | denial | 0.278897 |
| hubhealth1partial1.pdf | exit0 | 0.276640 |

意见：`.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-watch-hub-execution-v2.json`。

## 范围限制

结论只限本轮实际执行的 Mac POSIX 前景服务 watchdog-health 子域；不关闭完整 SC10/R008、E/H/X、Windows Job、所有资源边界、普通账户安装或服务身份交接。不将定向 AccessDenied 注入视为历史内核权限错误的完整原因重现。图像判断不属于本检查，没有以缩略图替代必须的原图检查。逐目标身份、证据路径、版本、完整94绑定见同名 JSON。
