原始报告SHA256：`65e6c78c33f9c7a9ad81e92592cb1e012a7fbb6c51cda21901dd09737983f423`。公开稿仅替换本机目录与测试机标识。

# AT-SMM-008：SQLite 调查与 Vibe 测试停止修订独立复审

独立上下文：`/root/completion_sqlite_candidate_review`。范围为 completion-20261128 的调查设计、原停止探针、两端原始调试和测试停止候选。只读核源码及原件，仅创建本报告；未运行产品、修改断言、原始清单、PR、验收记录或执行合并。

## 判定

**passed（本次调查设计、测试修订与调试证据的限定范围），候选可以进入正式回归。** 未发现本轮已经确认、需要修改产品的 SQLite 缺陷。该结论不表示历史 disk I/O error 已修复，也不表示产品不存在潜在生命周期或 SQLite 缺陷。历史失败继续保留，成因仍为未定。不是完整 008、E/H/X、最低 Python、普通用户或系统服务交付通过；Windows 本次是家庭 Win11 管理员源码组件运行，不能代替 Windows-2022 官方 CI。

依据：AGENTS.md 的确认阶段与实现/验收约定；008 SPEC 的“不改变……对话同步、VibeInsight”边界、A11 兼容回归、A12 与证据保留要求；B9 的产品任务预算不能由测试修订延长；PLAN 的共享测试设施、完整归属后只读退出观察及保留旧失败约定。另实际阅读验收技能与 reviewer.md、design.md 边界检查。设计没有增加新产品承诺，20 秒是测试停止观察上界，不是产品任务预算；原 10 秒 terminate wait、必要时 kill 后 10 秒 wait 没有扩展。异常子树清理可能另耗时，但必定失败，不能继续重开 WAL 或冒称在截止内退出。

## 历史失败与调查能支持的结论

独立打开 six-fixes-20261127/ci-3c2c42cc 的既有报告及 push 46041856740/tests-windows-2022/official.zip，重新核 ZIP CRC、长度 19476、SHA `f7855b11246e8eebafc5524e694efed1161825c3a6dcdfd502cf199ee045cbd2`；XML SHA `6b9f6506c9f9b963f984593fbe97881fe9d98995db87024fdc9933c360739f7d`。实际失败原文是 stop(service) 后 tests/test_vibeinsight_sync.py:307 构造 Archive，core.py:204 的 `PRAGMA journal_mode=WAL` 抛 `sqlite3.OperationalError: disk I/O error`。原件没有扩展错误码、现场 DB/WAL/SHM 和句柄时序。不能从单项错误确定产品、文件系统或测试停止方式中的哪项为根因。

调查脚本保留旧 terminate→wait/必要时 kill 流程；随后立即 Archive 重开、查询三项 cursor 并 quick_check，记录真实成员创建时间/命令/解释器、存活状态、SQLite 版本及文件摘要；最后单独清理原属树。它不使用本次新 stop helper，不以重试遮蔽重开错误；脚本 exit0 本身不是成功判据，复审逐 trial 核 `reopen`、`probe_error` 和 cleanup。

| 原停止探针 | 实际环境 | 完整试次 | 重开/quick_check/cursor | launcher wait 后尚存 | 清理后尚存 |
|---|---|---:|---|---|---:|
| Mac | macOS 15.3.1 arm64 / Python 3.14.2 / SQLite 3.51.2 | 8 | 全部 ok / ok / 3，无 probe_error | 全部 0 | 0 |
| Windows | Win11 10.0.26100 / Python 3.14.10 / SQLite 3.53.1 | 16 | 全部 ok / ok / 3，无 probe_error | 全部至少 1；trial 5、8 为 2 | 0 |

Windows surviving_members 的 exe 是实际基础 Python，不只是 venv redirector；观察确实证明旧 `Popen.wait()` 不能独自证明整个测试服务树退出。**它没有证明该存活解释器造成历史 I/O 错误。** 24 次未复现也没有证明历史产品无缺陷；两端 Python/SQLite 和官方故障现场不同。探针文件 before/after 摘要只是当时的诊断元数据，不等于原故障现场的原子数据库快照。Mac 探针未单独保存全源码运行前后清单，不给它与最终全部源码严格同版的额外认领；此限制不影响它作为有限合成观察。

Windows probe 的 controller-result.source_manifest 与 windows-argv-debug1/source-manifest 完全一致；独立核对其 source.tar 全 237 文件逐 SHA，旧 test_vibeinsight_sync.py SHA `6fe87ff5a8921140b55ff447f5da43a63a49a128a4ce05b39165fd935afd9a64` 与历史 3c2c42c 一致。probe.py 与本地 sqlite_restart_probe.py 原字节一致。调查没有访问真实 VibeInsight。

## 候选源码、依赖与业务判据

stop_enrolled_test_hub（test_vibeinsight_sync.py:12–46）合并 ready 后登记成员与停止前再次递归获取的真实成员；以 PID/创建时间去重。父 launcher 用自己的 Popen handle 证明退出，其他成员循环调用只读 waiting_for_owned_exit；pending 非空到截止时，仅按原完整身份 terminate_verified 清理并抛 AssertionError。只有 pending 为空才返回，测试 :352–355 在返回之后才重开 WAL。第二次停止服务也在离线查询之前完成，finally 的第三份收据是对同一第二服务的重复确认，不是第三次独立重启。

start :294–299 在真实 Hub info 就绪后登记，非空且逐个核服务 argv（容许 argv[0] 是不同平台解释器）。共享 process_tree 使用递归子树；初始枚举严格核创建时间、argv/exe，退出观察不在进程正在退出时重读易变 argv/exe。此候选针对已登记的测试服务树，不宣称为任意不断 fork、已脱离原树的第三方服务提供 OS 全生命周期封锁。

pyproject/uv.lock diff 仅在 test extra 中显式加入已存在 documents 组且已经固定的 psutil==7.2.2；没有新包版本或产品运行依赖升级。test_vibeinsight_sync 原 96 个 Assert AST 全保留，现有 98 项仅新增登记非空/argv；没有更改业务期待、放宽 decode、skip、xfail、自动 SQLite 重试或产品 fallback。本次测试补丁不修改 src。工作树其他并行测试修改不归本报告认领。

重开处只捕获 sqlite3.Error，记录 code/name/message/runtime_stops，以 add_note 加入普通 CI 可见 traceback，选配证据目录另写 JSON 后原样 raise。没有 ACCEPTANCE_EVIDENCE_DIR 时仍有错误注记；不会把未知 code/name 填成成功。最终两端本次并未实际进入 SQLite 失败注记分支，因此对该分支的结论来自源码核验，不冒称已动态复现；也不声称此注记已经保全未来所有 DB/WAL/句柄现场。

## 反例按实际断言推演

| 合理错误 | 第一个拦截/核实位置与边界 |
|---|---|
| 只等 launcher 就返回 | stubborn 控制 test_vibeinsight_test_process.py:41–42 必须抛 descendants did not exit；错误直接返回会使 pytest.raises 失败。natural 控制 :43 逐个原登记成员核已退出。实际 managed Windows 收据两服务均登记 launcher+真实解释器。 |
| 漏掉实际子进程 | 控制 :34 要求子程序独立输出的真实父 PID 与真实 child PID 都进入登记集合；:43 对全部登记成员检查，helper :20–23/35–39 的递归重采样及逐成员循环核所有目标。Windows 原生 venv 多层树和 Mac 直接树分别实跑。不把任意更深、停止后新 fork 的额外等价样本强制为本候选阻塞条件。 |
| 立即杀所有子树再假称自然退出 | helper 正常路径只 terminate 原 Popen；后代仅在 deadline pending 非空才严格清理并失败。stubborn :41–42 不允许“强清理即 passed”；natural 的 remaining 空和 :43 共同核退出。 |
| 误杀外国进程 | :35 排除 foreign.pid；:44 要求 foreign launcher 活着；信号实现只遍历已验证成员，terminate_verified 再核 PID/创建时间/argv/exe，没有全系统名字匹配或按命令子串杀进程。此控制与源码共同支持保护，不是对任意系统进程的黑盒穷尽测试。 |
| PID 复用或访问未知被当退出 | exit_observer :18 创建时间不等立即断言失败；:15/17/22 身份未知/AccessDenied 返回 pending。cleanup 的 matching_process 再核完整身份，不会因“看不到”信号外国进程。未额外声称本批动态制造 PID 复用或权限拒绝；这些分支是源码证据，现有实际控制已区分本轮 launcher/descendant 的核心条件。 |
| 宽松解码掩盖业务错 | diff 无 decode 修改；独立核两端附件 resumed_read 的 10 条独立正文、两项目 CLI 精确 session 集、exact_reads/cli_reads、旧记录正文、unlink 后集合及离线两入口集合，不只比较两端相等。 |
| 将未来 SQLite 失败吞掉或没有附件就丢证据 | :356–363 在 record_evidence 之前 add_note，随后裸 raise；可选附件关闭不妨碍 traceback 错误码/名称/stop 记录。没有 retry/成功返回。记录写盘自身异常未专门注入；这不支持“所有未来现场均完整”的额外结论。 |

依设计边界，未发现会让有依据必测行为缺失而仍全过的阻塞性缺口。动态覆盖与只读源码推演已分开；增加任意等价 PID、额外进程数量或未来每类 IO 错误并不是 SPEC 为本测试设施规定的无穷扩样要求。

## 最终两端调试与原件核验

Mac debug3 是最终冻结版：source/result 清单完全一致，source_unchanged=true/exit_code=0；69 个列出文件逐个与当前字节一致。完整 JUnit 15 个唯一 testcase、0 failure/error/skipped，stdout 15 passed（8.89s），stderr 空。三份停止收据分别 launcher -15、remaining=[]，前两次约 .186/.238 秒，第三次为重复确认。debug1/debug2 保留为历史，不从 debug2 中途 import/except 修订推导全程同字节。

Windows debug1：source.tar 全 238 文件与 source-manifest/结果内 manifest 完全一致，逐文件 SHA 校验通过；当前只 `tests/test_document_formats_active_source.py` 后续不一致，它不是这次两个 selector 的执行依赖。本次相关两测试、platform/exit_observer/conftest、pyproject/uv.lock 和全部产品文件与当前一致；不认领“当前所有 238 文件同版”。JUnit 完整 15 个唯一 testcase、0 failure/error/skipped，stdout 15 passed（49.16s），stderr 空；result exit0、timed_out=false，69 个被控制器观察的进程、cleaned_owned_processes=[]、cleanup_errors=[]。正常结束后控制器没有靠补杀残留才制作绿灯。两真实服务的收据都含 launcher 与实际解释器，remaining=[]，约 .034/.016 秒，第三份重复确认。

两端均包含原 13 项 Vibe 回归与新 natural/stubborn 两项，均为实际子进程，不是 mock。业务附件分别完整提供 initial/status/read、重启前 3 cursors、追加后同会话 10 条正文及来源 ID、错误恢复及保存凭据、混合项目一层关联、CLI/MCP 精确读、旧来源正文、unlink 后范围和停止后的本机离线回退。复审重新按独立文字/session 预期核对，断言对应实际原件。

Windows 两份 ZIP 均独立实读每个成员 CRC；manifest 路径仅用 PureWindowsPath 拆分为正斜杠成员，不改任何 manifest 原字节。拒绝 absolute/drive/..，映射一一对应，没有完全相同或 casefold 冲突；实际 ZIP 成员全集等于 manifest 映射全集加 sha256.json，无额外/缺失/越界成员。每成员 SHA/bytes 与 ZIP/verified 原字节一致，recovered-verified 的映射及数量独立重算一致。

| Windows 批次 | ZIP bytes | ZIP SHA-256 | 成员数（含索引） |
|---|---:|---|---:|
| sqlite-probe1 | 29445 | 2881837380d19f887f05e71529a208bef9465c4e06e1e4cf44064896099938e9 | 69 |
| vibe-stop-debug1 | 40887 | a4ea05ac94dbfc87b561d6a43a526be1d5ef7daeca83a076da3425ae407f1032 | 16 |

transfer.json 长度/ZIP 摘要、原 sha256.json、恢复回执均逐字读取及独核。probe 的 68 个有索引 payload（包括 64 个原始 trial 日志）、Vibe 的 15 个 payload（包括全部 11 附件）全部匹配；Mac probe 的 32 个 setup/server stdout/stderr 均读取，所有 stderr 空。Mac 最终 11 附件全部 JSON 可解析；没有把日志或设计中的预期当作实际断言。

## 后续保留

正式回归必须使用本次最终测试字节；官方三 OS 普通 CI 及任何原生正式验证仍按各自版本另取结果。若未来 SQLite 重开失败，必须保留真实 failure 和新增注记，继续区分停止失败、测试故障、环境与产品，不能因本批 passed 自动降为偶发噪声。历史原错误与完整 R008 未验证范围持续开放。

## 本轮独立计算的关键输入

以下路径相对工作树。SHA 为原始 bytes；报告本身摘要由交接消息另列。

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `AGENTS.md` | 2824 | `e93069c4772e63e3303453f4b58d21afea931e848c0b9b681a9f3e9a3755e7c1` |
| `changes/008-document-format-support/spec.md` | 57875 | `99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986` |
| `changes/008-document-format-support/plan.md` | 111924 | `9e7b72af93b59c24552b6ce100fcb22adf98b8f7ccc7d373397fa79c4e4d58eb` |
| `tests/test_vibeinsight_sync.py` | 40216 | `fd919a8a9a49dffae51b12e7acd5f0dcf0e28e4a79f1086bb90624cd0b48ff9b` |
| `tests/test_vibeinsight_test_process.py` | 2463 | `f661390095df9b2b30db40c9bdc700011455a6b6a64d9ba2653b7f956d9fd916` |
| `tests/document_formats_platform.py` | 10580 | `ad372fb601d184ab90c0856f3f6812a07c6eb78a4dda742279a5da452506ea39` |
| `tests/document_formats_exit_observer.py` | 953 | `9716a8c257af8244fd0f70ddbf62593117ec3993e35a59820fe7875a3491630c` |
| `pyproject.toml` | 1195 | `71af34db787f9d46571efda67c9b576e3d56557c669c0c4f8bd5c942824c6646` |
| `uv.lock` | 302996 | `b086d77ca402c72aef2cffa6a0b89ea121e1c2f250d23073d402fdefbcbe7d37` |
| `.acceptance-local/008/completion-20261128/sqlite-investigation-design.md` | 1496 | `f67c24985d5b8da37fa2cd68aedc4219827d390fc250b89c7495474b9be46854` |
| `.acceptance-local/008/completion-20261128/sqlite_restart_probe.py` | 6377 | `4932b5b5f7a85617f029fc1b8a4fe2cdf078e4c4d3bf32e2492703f300fe229f` |
| `.acceptance-local/008/completion-20261128/sqlite-mac-probe1/result.json` | 24851 | `62ce7c2b87e1341512318663a3bb3c2e156658bd2f250cd0ca3a5c7976277625` |
| `.acceptance-local/008/completion-20261128/sqlite-mac-probe1.stdout` | 648 | `0fb8252e26670ec446c82ede27c5dde4a3d14a2201169b57273483d6abdb49de` |
| `.acceptance-local/008/completion-20261128/sqlite-mac-probe1.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.acceptance-local/008/completion-20261128/vibe-mac-debug3-source.json` | 7211 | `24899c58d6fa6452dcb4720750871dd4083225c654de24937d3db2728b6fffd3` |
| `.acceptance-local/008/completion-20261128/vibe-mac-debug3-result.json` | 7734 | `293db3fb567fe69a1556886648b62fee22b687858daaec18266c1c73332b05dc` |
| `.acceptance-local/008/completion-20261128/vibe-stop-mac-debug3.xml` | 2274 | `e8d4a916a4a8267bf17e51a9409670d4d0548b31d974841d6a750d67f2d6497b` |
| `.acceptance-local/008/completion-20261128/vibe-stop-mac-debug3.stdout` | 643 | `be9cd51f8f5d1ca07c67a11c512e1f39ec0d668d1afa71468c6227130e7e2959` |
| `.acceptance-local/008/completion-20261128/vibe-stop-mac-debug3.stderr` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.acceptance-local/008/completion-20261128/windows-sqlite-probe1/verified/controller-result.json` | 27988 | `7a661b005d5472e78732e525a6789325ddebf1cb3e64c60f0b957eddd193081f` |
| `.acceptance-local/008/completion-20261128/windows-sqlite-probe1/verified/probe-output/result.json` | 76403 | `f1a44b1af5ad1ae99c53dd999699e91605e15a90b9d55c843d7caf3b5310c8e5` |
| `.acceptance-local/008/completion-20261128/windows-sqlite-probe1/transfer.json` | 114 | `06cdc92f86f29f05ea225144a99b4c153274676a1b83dc0066093cecd4490698` |
| `.acceptance-local/008/completion-20261128/windows-sqlite-probe1/recovered-verified.json` | 4833 | `b1dc436b3b07b917d374211bc24aa9d3af3351f8fe7d559e8a7dabff3279b229` |
| `.acceptance-local/008/completion-20261128/windows-vibe-stop-debug1/source.tar` | 3573760 | `0658d6531274b92ee7b78194c732b10755148b20136bd2f872c4f3d58f5cc5b4` |
| `.acceptance-local/008/completion-20261128/windows-vibe-stop-debug1/source-manifest.json` | 27262 | `1b62581c6f66e0c4b18ea4a6ff574c3739c83e3b79d62fea716243272d8f544a` |
| `.acceptance-local/008/completion-20261128/windows-vibe-stop-debug1/verified/junit.xml` | 2261 | `fb402944d384f408a18dcf31c0c77689f0ccdb11eb2b81e41e71f77fbf19c36e` |
| `.acceptance-local/008/completion-20261128/windows-vibe-stop-debug1/transfer.json` | 114 | `ea71d4c7d94beaed54fc7df479a5d43ce09d133b3edbe7a16ad462fd773a87d7` |
| `.acceptance-local/008/completion-20261128/windows-vibe-stop-debug1/recovered-verified.json` | 1845 | `11f24124d6db555a2787ee83875607e98a5974f8f7a4425d804613f681dd74ad` |

Mac 全目录额外核验：按所有文件的相对路径排序，逐文件计算 bytes/SHA 后，以 `json.dumps(rows,sort_keys=True,separators=(",",":"))` 编码 UTF-8 计算索引摘要。sqlite-mac-probe1 共129文件/4116483 bytes，索引摘要 `6717b68529467358f461bd74f52435e35e37c13d48b4ad77eaf33c0c547d05ee`；vibe-mac-debug3-evidence 共11文件/191059 bytes，索引摘要 `2372956afd2487fa8b97cb21fc545b39b424e2cc79b18262b88912718e5bdfa3`。数据库当前文件只作保存目录校验，不把清理后的值伪称探针每个时点的原子现场。
