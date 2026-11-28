# Hub v2 容量执行失败：监督器独立只读归因

AT-SMM-008。结论：**本次实际失败由 watchdog 命令行身份核验中的未处理 AccessDenied 进入产品诊断、触发容量用例的监督异常负控；不是首次容量准入红灯，也没有原件支持将其认定为 GC 误删。** 独立观察器异常退出是已观察到的产品监督问题；底层为何返回 EINVAL，是否 worker 预期失败后的正常进程退出竞态，尚不能确定。不能把假说写成根因，不能据前十个目标完成判本次 green passed。

本轮只读执行原件、现存任务诊断与源码，没有运行测试/native/构建/远程或进程探测，没有修改源码、测试或既有文件，只新增本报告。监督器当前 SHA256 为 `e4af95b631dbeb558c2678dbdbce4ba5e43aebc00d94ef46536299f04e8c8d23`，Git 对该文件无未提交改动，最近修改提交为 e8bb1bd；本轮 GC 源码仍按 v2 冻结。

## 实际原件与执行到达范围

执行根：`.acceptance-local/native-v1/AT-SMM-008/tdd-green/green-sc10-canonical-capacity-hub-v2/`。

- 主项 `TC-008-canonical-candidate-capacity/run.stdout`：1 failed，153.07 秒。失败为主测试 `:287 client.failed(probe, probe_raw)` → `GCClient.failed:106`，error 中存在 `PermissionError`；不是 begin 的容量拒绝。
- attachments 内实际有 **10** 份 `gc-target-complete`，index 精确为 0–9，覆盖 none/ready/partial 的此前目标。共 21 份 `gc-physical-capacity`；最后三份 `02133/02198/02312` 均为 268435456 字节、14 个未发布 canonical blob。后续第 11 个目标 index=10 的 probe 尚未完成其容量/保护/旧请求/移除检查，index=11 与 final admission 也不能认完成。
- `02373-native-management-hub.json.gz` 显示末块 parts/19 HTTP200；`02374` 显示 upload `ebb7c21d3ed5ef9e6e1066d7da2bc928` commit HTTP200，登记 document `318ea9124d8a45438d3b2b411787c876`、CID `84a1b792d1e4455cb6b2c54484eafdd2`、AID `ca6e1c2ee07b4932b92ecc13c1c4a846`、pending、V/P=0。说明该 20MiB probe 已通过准入并完成完整 raw 提交。
- `02376` 指向指定 library 响应 `responses/f5d26423220e9e806cd541315f0c3b31c8557d98c4c47f3a951a2ec66aca6bca.json.gz`。实际解压后 SHA256 与文件名一致，长度 52398；末项 `hubprobe10.pdf` failed，V/P=0，保留上述 CID/AID 的 retry_target，原SHA `3350b3127174707757af38e77348a5925d94f0438930e6886e4393fcf08e8df3`。

该项 error 同时包含预期的“PDF没有可用支持内容 / 未取得当前配置的有效组件探测 / method=ocr”与非预期 traceback：`document_supervisor.py:114 watch` → `:60 matching` → `psutil.Process.cmdline` → `_psosx.py:405 cext.proc_cmdline`；底层为 `PermissionError: [Errno 13] force permission denied (originated from sysctl(KERN_PROCARGS2) -> EINVAL)`，psutil wrapper 在 `_psosx.py:352–353` 将其转换为 `psutil.AccessDenied: (pid=56064)`。

只读检查了当次现存 task 目录：
`.acceptance-local/008/drafts/canonical-candidate-reclamation/red-hub-v3-tmp/test_replaced_and_removed_cand0/hub-state/.document-snapshots/tasks/ca6e1c2ee07b4932b92ecc13c1c4a846/`。

`worker.stderr` 实际 2913 字节，SHA256 `8c8809ac9ac37c1cdd52a0427798f0f0b6ebc603e90aca5f3ea721cc2a5a4f43`，包含完整 OCR 配置失败栈，随后是上述 watchdog 栈；不是报告拼接出的假异常。`supervision.json` SHA256 `2c222a08530fb6c57d130a670b52265c85c35cf384a7b025aa5403a2a85ad656`，status=failed，seconds≈0.473，peak_rss=91947008，worker PID56064/create_time=1795688107.741146，controller PID53692/create_time=1795687955.605058，token 即 AID；其 error 与 library 一致。stdout 空，结果文件不存在，任务根的 active.json 当前不存在。

这些任务文件是本轮只读的现存诊断，不冒称它们已由本轮 native attachments 完整归档。读取时顶层 result.json 尚不存在；回归仍未形成完整结束收据，本报告不登记或预判正式 green。

## matching / watch / run / stop_tree 的真实路径

`matching:55–62` 先取 PID、核 creation time，再在给 token 时读 cmdline 检查 task token。只把 NoSuchProcess / ZombieProcess 当失去目标返回 None，没有处理 AccessDenied。本次 traceback 进入 cmdline，说明该次 matching 已通过 creation time 比较；它没有记录命令行读取失败瞬间的活跃/僵尸/退出状态。

`watch:110–121` 在独立 POSIX watchdog 进程每 50ms 调用 matching(worker,token)。AccessDenied 从 `:114` 直接逃出整个进程，没有进入 `:119–120` 的 controller/worker 失效清理分支，也没有 finally 或结构化故障通知。**“本次 watchdog 因未处理身份读取异常退出”已经由真实独立 traceback 证明。**

`run:136–146` 把 worker 和 watchdog 的 stdout/stderr 指向相同文件。主循环只 poll worker，并不检查 watchdog 的运行/退出码。`:163` 在 worker 非零退出时把该共享 stderr 的末 2000 字符拼入“原生解析失败”，所以 OCR worker 的预期失败与 watchdog 的独立异常混入同一用户诊断。当前 supervision.error 和 `document_processing.py:39–41` 保存到 SQL 的失败信息，正与这个分支吻合；不是主进程 `:153` 的“无法建立完整任务树监督”分支。

`run:166–180` 捕获异常后调用 stop_tree，再写 failed supervision；finally 关闭 Job、必要时 stop_tree、wait worker、wait watchdog（超时则杀 watchdog），最后删 lease。本次存在 failed supervision、正常格式 failed attempt、active.json 不存在，说明此任务之后确实到达了失败落盘和 lease 清理；没有本轮证据显示它永久 processing 或槽位被留死。没有外部逐进程树清理证据，不能仅凭 lease 不存在证明所有可能后代均已退出。

`stop_tree:65–84` 首先再 matching(parent,token)，再枚举子进程和 creation-time 核验 known。若 AccessDenied 在这里持续出现，当前代码同样未处理，可能在实际清理之前抛出：异常分支只 catch UnboundLocalError，原诊断与 failed-state 写入可被第二异常遮蔽；finally 再次清理若仍抛出，还可能阻止 worker wait、watchdog wait 与 lease unlink。这是源码中需要保持失败安全的缺口，**本次没有证据证明该更坏分支实际发生**，不能把它写成本轮游离进程或永久槽位事故。

此外，watchdog 的退出码未纳入主循环健康判定，意味着如果 watchdog 先出错而 worker 仍继续运行，主 controller 可以暂时只靠自己的 RSS/时限/授权循环继续；若此后 controller 又失去，独立观察兜底已经不在。该静态路径说明不应仅消除 traceback 字样而忽略观察器存活性。本次 worker 本来已因 OCR 失败退出，不证明实际发生了监督失守后的继续解析或资源越界。

## 分类及能证明的限度

**监督产品问题：** 真实独立 watchdog 在核自己登记的 worker 身份时异常退出，主 run 没有结构化检测/报告其健康失败，而通过共享 stderr 混入 worker 失败。PID56064 不是任意陌生 PID：任务 state 明确登记其 PID、creation time 和 token。该问题源于既有监督器，未在六文件 GC diff 中引入，不因此应从当前执行抹去。

**测试不是本次故障来源：** 用例故意用缺 OCR 的合法 PDF 建失败候选，`:103–105` 要求 failed 且原因包含 OCR，`:106` 另排除容量/预算/权限等非预期失败。实际 error 确有监督 PermissionError，独立任务日志也确认。断言没有错把正常缺 OCR 文案或单纯不同 ID 当失败。它成功拦截了混合异常；放松或删除该负控不能形成有效绿灯。

**环境观察：** 已知是在本机 macOS psutil 的 proc_cmdline 系统调用读取中出现 EINVAL 并转成 AccessDenied。这只证明该次 OS/psutil 观察失败，不等于服务账户权限配置永久错误，也不等于已知 macOS 缺陷或库缺陷；没有本轮动态权限/状态证据可继续归因。

**正常退出竞态仅是假说：** worker 的预期 OCR 失败栈出现在前，watchdog 在核 cmdline 时失败，且整个任务不足半秒，这与 worker 退出窗口交错相容。可是共享 stderr 没有每次采样时间，原件没有失败瞬间的进程状态、wait/exit 时间线、第二次 liveness 与 creation-time 核验，也没有同一条件可控复现。故既不能证明是正常退出竞态，也不能证明 PID 重用、持续权限拒绝或其它具体底层原因。worker 的“正常进程退出”还不等于内容处理成功：此 worker 明确因预期缺 OCR 非零退出。

**GC 行为：** 当前 probe 已获得完整 200 commit，先前十个循环包含物理容量、当前候选/旧发布保护、旧请求拒绝、满额拒绝与移除检查；本次首失败点是第 11 个 probe 的监督诊断负控。没有原件显示 canonical 缺失、错误原SHA、所有权误判或256MiB准入拒绝。不能将其登记为原容量缺失继续 expected_failure，也不能因此宣布整个 GC 无缺陷；此前 owner 路径复用风险是另一独立静态问题，仍成立。

## 后续修复必须保留的约束（本轮不实施）

SPEC B5/B9、PLAN 的 PID 身份核验与监督失败终止要求仍适用。不能 blanket `except AccessDenied: return None` 把仍活跃但不可观察的已登记任务当作退出，不能继续跳过不可读子进程累加 RSS，不能杀未证明归属的陌生/已重用 PID，也不能降低监督、延长预算或只过滤 stderr。

允许研究的修复应先区分“已明确退出/身份已变化”与“仍属本任务但持续不可读”：可用本端已拥有 worker 的 Popen 退出证据，或独立可验证的 PID/create_time/任务租约状态来闭合短退出窗口；任何仍不能建立完整监督的 live 任务保持 failed，并通过已验证的 containment/任务树路径清理和报告。watchdog 需要向 controller 提供可观察的结构化健康终态；清理异常应保留原错误及清理失败，不能把 failed-state/lease 收尾全部跳过后悄悄继续。具体机制仍需设计和独立测试，不能由本报告预先认定某个宽泛重试安全。

必要证据应分别证明：受控退出窗口不会误报或误杀；已登记 live worker/子进程持续 AccessDenied 时确实失败并回收；陌生或 PID 重用目标不被误杀；watchdog 异常终止能被 controller 识别；原缺 OCR 失败、原 1GiB/256MiB/300秒和后续合法任务仍保持。未经这些动态证据，不将本次诊断简称为“瞬时权限错误已恢复”，不判 native green passed。
