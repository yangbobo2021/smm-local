# Watch observer 独立候选复审

AT-SMM-008，定义 000003（SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`）。只写本 Reviewer 意见；未改产品、测试、原证据及历史判定。

## Local 候选

`debug-completion-sc10-watch-local-v1` 的 `TC-008-watchdog-health`：passed，仅 covers `watchdog-health`。真实 pytest 1 passed / 38.32s / exit0。93 bindings、6296 artifacts 的摘要均逐字通过，source 快照与实际文件一致。普通/全局各 none、ready、partial 两目标，12份不同 document/CID/AID，分别真实未处理 AccessDenied 与 exit0。终态、树、槽位和实际临时 payload 的观测用时 0.075669–0.143086s。12次同保存CID新AID CLI重试、12次服务后续上传均有完整发布/读取断言和证据。最终40历史成员均 absent、服务 exit0/forced=false、cleanup errors=[]。可登记的独立意见已先写 `review-inbox/review-completion-watch-local-candidate-v1.json`。

## Hub 候选

`debug-completion-sc10-watch-hub-v1` 同TC：passed，仅 covers `watchdog-health`。真实 pytest 1 passed / 220.63s / exit0。93 bindings、6054 artifacts 全SHA通过，source与实际文件一致。同样完整12目标及两种实际退出；终态/树/槽位/payload用时 0.243056–0.431566s；12同CID新AID重试及12后续服务任务、40历史成员 absent、服务正常退出均已独立核验。意见另写 `review-inbox/review-completion-watch-hub-candidate-v1.json`。

## 判据及反例

已读 AGENTS.md、SPEC B5/B9/A10/C1、PLAN、定义000003和自然设计 v1、match/runtime v3。必要监督失效时终止、五秒回收及合法候选/旧快照/其他资料保护均有已确认原文依据，场景未凭空新增产品行为。测试仅分配 watchdog-health；RSS/temp/time所有额度与平台矩阵不在本项通过认领中。

`test_document_formats_watchdog_health.py:234-248`明确覆盖所有项目/前状态；259起逐一执行。假设只第一目标正确：第二目标在283-300同AID failed/finished、监督原因、释放、V/P、retry CID和原字节断言被拦。假设只有none正确：ready/partial的292-298及126-140旧发布保护会拦。假设两边都误读第一文档：snapshot的当前文档ID、独立源SHA、完整源词顺序、独立所有表格单元/跨度和原字节（90-115）先拦截，不以两个产品结果相等作真值。故障前158-196独立登记真实worker/后代/watchdog全身份、父子关系、任务根和nonce；275再核仍活，之后才注入；现场错误类别注入不是内核权限错误重现。

## Ubuntu 正常退出调查

原包 `watchdog-normal-ubuntu-output.tar.gz` 的 results 共有32次（Local20、Hub12），31个watcher exit0、Hub index11 exit1；所有entry ready。其原始stderr明确在测试hook第113行 `assert ... token in result` 抛 AssertionError。该证据证明观察器可在正常任务结束时自行造成监督异常；它不是原生解析/OCR错误。

修订包 v2：40次（各20）watcher均exit0且entry均ready。原件保留6个真实 `argv=[]` transition（Local3、Hub3），ctime仍匹配期望值。修订保留真实原cmdline返回值；额外exe/cwd/status元信息不可观察时不从观察器新增产品异常。故障注入仍要求已独立核验的当前活目标，两个完整creator debug已实际验证两种注入有效。

原输入包至当前源仅两测试文件变化：health hook与active-source controls；产品源码字节未变。Ubuntu22.04此处只是补充调查，不能替代必需24.04 E/H格，也不能归因早先历史内核AccessDenied。

## Mac 与 Windows 真实控制

Windows v2 原包输入SHA与执行result输入SHA一致，包内src/tests逐字匹配当前源。实际stdout 6 passed / 7.65s，JUnit6项、0失败/错误/skip，exit0。真实launcher PID14520，实际门内Python PID15104、PPID14520；完整owned tree保存两个不同exe，worker ctime/argv及完整参数、当前物理解释器路径、token、raw路径/SHA逐一核验，释放后真实原字节输出及source-open正负控制有效。

Mac stdout 6 passed / 0.71s，JUnit同6项无失败/skip；门内PID87571为该平台真实Framework Python，allowlist加入控制器 `psutil.Process().exe()`，与Server既有策略一致。该修订仍保留owned tree、ctime/argv、exact token/path/SHA及物理解释器比对，不将任意PID当本任务。

双方两个独立live进程的cmdline拒绝及cmdline+status拒绝均显式抛AccessDenied；Mac另有真实zombie分类，Windows明确不适用POSIX zombie。两端各两份helper cleanup均exit0、未强杀、全部登记成员gone、errors=[]。参数与source guard控制按真实子进程及实际open/启动事件通过。这些是设施控制，不证明Windows标准token、Windows Job或H服务。

## 历史失败保留

CI 46093631770 / HEAD68112386：三份official.zip已独立核SHA与official digest、ZIP CRC及XML计数。Mac532通过91skip；Ubuntu531通过1失败91skip（正常对照watcher exit1）；Windows531通过1失败91skip（错误要求实际worker3588等于launcher2508）。Ubuntu官方XML没有watcher内部stderr，补充22.04观察器复现只能提供有依据的机制，不能把原CI根因定为已完全证明。

Combined `debug-completion-sc10-watch-observer-v3` 原stdout仍为1失败12通过/288.25s，两个health参数通过，额外activecontrol因Mac实际Framework exe未列入allowlist失败；同时12195附件共34,600,049字节超过25MiB，原生result/pending均blocked。拆creator没有删任何health检查/样本/生产预算，新controls单独验证修订；这些新结果不把原failed/blocked追改通过。

本次只认可两个creator的watchdog-health候选及补充控制通过；完整SC10、RSS/temp/time边界、controller死亡/重父化、历史内核根因和E/H/X仍不由本报告关闭。完整原包、关键源和官方证据SHA在同名JSON中。
