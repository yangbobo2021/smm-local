原始报告SHA256：`f2fce16770e0e8779fca4053f6aaaafcc69c5287af9689b77246c9ec1072948a`。公开稿仅替换本机目录与测试机标识。

# AT-SMM-008 共享 native argv 观察器候选独立复审

独立 Reviewer：`/root/completion_argv_design_review`。项目：`[isolated-worktree]`。本轮只写本报告，未修改产品、测试、旧证据、PR或运行产品测试。复审对象为 `completion-20261128/argv-design.md`、四个既有测试设施文件的修改、新增四控制及 Mac/Windows 实际调试原件。

## 结论

**passed：本次限定的 argv 观察器设计、实现及最终调试有效，未发现需要退回 scene/design/implementation 的必测缺口。** Mac debug2 四控制全过；Mac 相关回归19过；Windows 同源批19过、0失败、0错误、0跳过。原 Windows 官方普通CI四个失败实例仍为失败，首轮Mac错误预期仍为测试故障，不追认通过。本结论允许该观察器候选继续后续流程，不等于新head普通CI或正式E/H/X、最低Python、完整C1/R008通过，也没有宣称实际独立安装Hub worker已被本控制执行。

## 原始依据与判据合法性

实际读取该树 AGENTS.md、008 SPEC/PLAN，以及交付验收技能的 `SKILL.md`、`references/execution/reviewer.md`、`references/case-preparation/design.md` 边界检查和 `implementation.md` 探针自检。

| 本轮判据 | 原始依据与边界 |
|---|---|
| 原生argv完整规范化，保留顺序、中文/空格/空参/引号/反斜杠；未知顶层类型不静默漏记 | SPEC A10/A12、D2、证据条款要求真实平台进程/身份及可核原始参数；技能探针自检要求已知输入正负控制。具体argv编码是测试观察契约，不新增用户功能。 |
| 只识别真实worker模块、flag位置和合法token；原始argv/type与规范结果并存 | SPEC A10的任务树监督、A11/C1回归和证据身份要求；PLAN的共享观察器只修误判、不替代实际平台。真实产品 `document_supervisor.py:257` 的 `python -B -m <package>.document_worker --task-token TOKEN` 布局是观察对象；`document_windows.py:122–123` 明确产生原生str。模块布局不是额外产品行为要求。 |
| 子进程hook实际导入，受保护源open/Popen参数被拦、允许命令能执行，源字节/mtime不变 | SPEC B4/B5/B6、A8/A10要求保存快照重试/恢复不重新开源、原字节不变；现有source guard对传入源路径的子进程提前拒绝是测试设施控制，新增控制验证该设施能力，未要求产品任意命令行参数都禁止路径。 |
| 原重启计数仍为两目标各一次，stable restart零处理，handoff真实父身份/token/count约束保留 | SPEC A8/A9/A10、B4/B5及PLAN同档案CLI交接/重启约定；本次没有改业务断言/count/阈值，已有测试仍只代表其实际分配子路径，不据本补丁把旧测试提升为完整C1或完整场景。 |

候选自然语言设计只修观测盲区，没有新增或缩减SPEC行为。完整C1同项目双目标、所有生命周期状态、E/H/X各入口与原生身份仍由对应场景履行；该范围之外的旧缺口不被本次观察器通过关闭。

## 实现与版本核对

Windows `source-manifest.json` 包含237文件；独立实读 `source.tar` 全237成员核SHA，与清单及复审时当前文件全一致。head基线 `1899488f30af617252982d5bf356a8fe35f6eeb6`；已有文件相对head仅四个测试设施变化，新增四控制也在清单中；未发现产品文件变化。

| 文件 | SHA256 |
|---|---|
| tests/document_formats_platform.py | ad372fb601d184ab90c0856f3f6812a07c6eb78a4dda742279a5da452506ea39 |
| tests/document_formats_restart_server.py | 84d4c5e3c70f1abb880762eeedbc4900d911ba9523c8ac8958438fbeb1fac4e7 |
| tests/document_formats_handoff_observer.py | d3388ca74ff8b17a39ee6230a1ca41ff8641a5455e442da0995ec00a2a5c40a9 |
| tests/test_document_formats_retry.py | fc9e8ea11a58cef833c31900c4bfd91dccb224895fa9b41e4fc6020bacb44c7c |
| tests/test_document_formats_process_arguments.py | 85fe7b698481b44c62937db2b4a33e1799e94f22fdf26ad83f86ba0c19230aba |

`process_arguments` 对list/tuple复制，Windows str由 `CommandLineToArgvW` 解析并在finally释放，其他顶层形态直接TypeError；未使用POSIX shlex或空白split。`document_worker_token`核定位置/模块/flag/32位小写hex。restart/handoff两消费点均无忽略未知argv的catch；handoff旧实现抽为同一个共享函数，身份控制保留。restart原始argv/type/token与规范argv同次落盘。

动态source hook在 `test_document_formats_retry.py:38–52` 显式导入helper，将 `ROOT/tests`、`ROOT/src` 与hook目录放入PYTHONPATH，未依赖当前工作目录。sitecustomize安装失败可能被Python启动机制打印后继续，因此不能只据空日志认活跃；本轮真实open与Popen拒绝、允许子进程成功及期望日志集合共同证实其实际安装。其他消费者原有自检和身份绑定仍在。源码Hub执行仍经源码 `smm_local.document_worker`；`smm_hub._archive.document_worker` 只在shape单元控制中被识别，未冒称隔离安装实际运行。

## 必须反例与首次拒错位置

行号取本轮冻结源码；P代表 `test_document_formats_process_arguments.py`。

| 推演反例 | 首个拒错位置及原因 |
|---|---|
| 只首参数正确，后续中文、空串、引号或尾斜线丢失/重排 | P:18直接与预先写定的完整command比较；若只真实子进程传参错，P:22与独立literal tail比较。不是两个规范化结果互证。 |
| 只有第一个worker模块shape被识别 | P:34–36遍历source与vendor两模块，第二次直接要求相同已知token。vendor shape只承诺shape。 |
| 只有首业务目标或一端重启正确，第二目标/另一端恢复错误 | 两端参数化主项分别运行；`upload_restart.py:199`先核全集ID，202–204逐目标核版本/CID/AID/ready，205–218逐目标核独立词/全部表格/原件；stable阶段225再次复用全集断言。遗漏第二目标不能过。 |
| pending可恢复，但已ready的稳定重启仍重复处理；或只普通项目正确 | 既有重启主项同时包含ordinary/global与pending→ready、ready→stable两阶段。225逐份读回后226要求audit空；错误状态/内容在202起先被拒。这里只验证这两个原有动作前状态，不声称覆盖A8全状态。 |
| 两边一起使用同一错误目标/错误文本，比较仍相等 | P:18/22独立literal预期；重启 `upload_restart.py:206–218`核目标id、独立truth及原件bytes，214–216逐表完整格集合；handoff `hub_cli_handoff.py:67–91`核目标路径/id、独立truth/原件及完整表格。它们不只做两结果相等。 |
| 未知argv顶层形态被静默跳过 | P:23–28分别要求None/int/dict以及POSIX str抛TypeError；helper对应拒绝分支在消费点直接传播，不能返回空列表。list内非字符串不是本轮所承诺的未知顶层形态，真实Python可接受的bytes参数也没有被误改为未知。 |
| 普通-c参数中含worker字符串、假worker模块、错flag或非法token被误计 | P:37–43逐个负控，错flag/token首次在43被拒；真实-c和fake module在P:60核真实退出，再62要求恰一事件且argv等于唯一正控。handoff observer:74/79还核真实非worker、fake、substring命令只留下正控一个事件。 |
| Windows整条字符串包含受保护中文空格路径却漏拦 | P:78–82真实子进程分别open保护源、在Popen argv传入该路径、传入允许路径，要求失败/失败/成功。漏Popen时82首先失败；若伪造退出，83要求具体guard错误，85要求两事件的完整event集合，86要求路径，87核源bytes/mtime。Windows实际附件给出open/Popen两行与[1,1,0]。 |
| sitecustomize未安装或导错helper，空审计被误作没有处理 | P:62强制存在实际worker事件；P:82–86强制两种拒绝事件；handoff observer:77核真实PID/ctime/argv安装记录。不是只看正常调试文字。 |

上述均已有首次拒错断言，未发现违反本轮原始承诺仍可全过的缺口。进一步增加等价token、同条件路径或更多等价worker样例属于可选扩样，不作为阻塞。实际独立安装vendor运行、三OS/身份和完整业务状态属于已保留正式矩阵，不能以本表的shape/源码控制代替。

## 原失败核对

实际打开 `six-fixes-20261127/ci-1899488f/independent-review.md`，并独立实读push46046414305及PR46046422474的两份Windows官方ZIP/XML。ZIP CRC有效、XML与落盘逐字相同，SHA分别为 `d62f0ba7177f2ed5ac16f9a097c06d452e86855ba6e74b9765d4fc1a1648e1fb`、`eac0b6a3b92f81de2f54d6b232f193cdecaa6e15d6c7bd5802831b3f6b03a12f`。四个Local/Hub实例均在224行计数0==2，225后半稳定重启未到达。旧hook只接受list/tuple，与产品Windows实际str事件相冲突，测试观察器故障分类有原始依据；不更改其失败状态，不证明此前stable阶段成功。

首轮 `argv-mac-debug.xml` 为3过1失败（SHA `b4286d2eaae525ea700ff4204c8737351bc90d33e070c942302645328ec33ff9`），要求带合法token、空stdin的两个源码模块退出2，实际[1,1,0,1]，属于错误控制预期，不能授予产品expected_failure。最终控制改为实际source worker `--help`退出0；产品未改，vendor实际执行声明撤回，vendor shape单元覆盖仍在。

## Mac最终调试

- `argv-mac-debug2.xml`：4测试、0失败/错误/skip；stdout 4 passed，stderr空。XML SHA `b544bc7e9890cd352667fccc38d55a389510253edbbda99d9a2c0eeaf9c8684f`。
- `argv-mac-regression1.xml`：19测试、0失败/错误/skip；stdout 19 passed in25.61s，stderr空。XML SHA `d228459a3ecf88f9ebf7458b298412bba9c809690265f968578c6f556c2592fb`。身份集合为四新控制、九平台控制、五restart控制/两端主项，以及一handoff；对应源码断言有效。Mac现有材料主要为JUnit/stdout，不把未单独打开的Mac下载附件描述为已核。

## Windows同源真实调试与原件

实际只读核 `windows-argv-debug1/controller.py`、run_remote、preflight/transport、source tar/manifest、transfer，以及ZIP所有成员；没有只相信主控verified摘要。ZIP **673866 bytes，SHA `02f12de395a1b6afa93ec2f0b62a7882b6a6dfb155e3a1a63b1f62614c5e28dc`**。478唯一成员，其中477清单项逐字节长度/SHA与CRC全通过；无漏列/额外成员。result内source manifest与上传原件一致。

Windows11 `[windows-test-machine]`、账户 `[windows-test-user]`、admin=true；Python3.14.10/win32。实际pytest19过、0失败/错误/skip，stdout155.00秒；controller总156.61秒，exit0、timed_out=false、cleanup_errors=[]。本批不是普通标准账户或SCM身份。

- `attachments/00001-native-argv-real-child.json`保留原生字符串、完整规范argv及真实child tail，中文/emoji、空串、引号和尾反斜线均与冻结literal一致。
- `00002-restart-native-worker-controls.json`真实退出[0,0,1]，唯一事件raw_type=str、模块/token/argv正确，raw_argv可读。
- `00003-retry-native-source-guard-controls.json`真实退出[1,1,0]，保护中文空格路径各有open/Popen两事件；源码87行实际执行过原字节/mtime断言。
- 两端恢复阶段 `00108-restart-server-stop.json` / `00185-restart-server-stop.json` 分别有两个str型worker事件且正常退出；稳定重启 `00128` / `00207` audit为空、forced=false。原paused阶段 `00070` / `00154` forced=true是测试屏障期间既有强制停机路径，不伪称全部生命周期优雅退出。
- 实际打开四份inputs及八份resumed/stable-restart下载，逐份比较输入==恢复下载==稳定重启下载，四目标彼此不同。该原件证据补上旧Windows224之后未执行的部分，仅适用于本轮冻结候选。
- `00208-handoff-observer-controls.json`真实[2,0,1,1]、唯一str型正控事件；`00268-handoff-initial-parent-identities.json`六个不同token服务worker、CLI零worker、PID/ctime/exe/argv/nonce绑定；`00319-restart-server-stop.json`服务累计12个str事件。其余CLI不同state/无服务前景等断言通过，不冒称launchd/systemd/SCM。
- 原件JUnit SHA `da7cd05cd00ac1a367cbad5a6037468e8b945f4de4c64b3ea62b7b9d44e7b58b`；result SHA `df508e92160dca2f22d76186ffe6e2c424d630d689e0c57bfae0cb91f988091e`；清单SHA `de6eb0aa38a7494f59a781c7336ae930aa28053be94f3194fd52877706c1035b`。

本轮最终无已确认产品失败，无需修订项。旧失败、错误预期、故意负控stderr、正式矩阵未完成范围均按各自原事实保留。
