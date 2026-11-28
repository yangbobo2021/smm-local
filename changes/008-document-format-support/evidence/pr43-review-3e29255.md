# PR #43 独立检查点审查：3e29255

结论：**首个独占档案 canonical 候选容量子例的限定红绿证据可信；本轮六个产品文件未发现新的、有充分依据的确定误删或锁次序缺陷。PR 整体仍 needs_revision / draft，R008 未完成，不能合并或发布。** 当前代码对先前 receipt 误归属、path-only owner 复用反例已有针对性阻断；两项都只有静态修订认可，不能记为多档案/数据库改名动态通过。实际发生过的 watchdog AccessDenied 仍是未修复的产品监督问题，v3 成功不追认其已修。

## 版本、方法与 Prompt 覆盖

- 本地实际核得 HEAD：`3e29255ea57701d03997ef3212f3cb314d1347ec`。前检查点：`f1334a275e89c5079313eb7bdfc8436b62c422b7`。全 PR 基线：`d8894d429ebe0915e377513a637b5dfc0fc7ea1a`。PR：<https://github.com/yangbobo2021/smm-local/pull/43>。本轮未联网核 GitHub 推送、线上正文或 draft 标志；推送身份来自任务指定，本地提交身份已实际核验。
- 审查为**本轮 30 文件增量与既有交付缺口核查**，不是重跑全 PR 验收。完整读六个产品文件的增量及直接调用上下文、两份新增测试，核前检查点意见及当前必要行为。未宣称重新逐行审查全部历史 PR diff。
- 首先实际读工作树 `AGENTS.md` 和 `changes/_templates/pr-review.prompt.md`，随后读 008 Intent/SPEC/PLAN、指定的 pending/development 和五份安全/owner/监督报告、`pr43-review-e8bb1bd.md`、自然设计、红绿/独立意见与下述私有原件。用户主入口回放实际读取 README、TRIAL_GUIDE、检索 Skill、验收 README、CLI/Web 源码；没有本轮真实 UI/CLI 业务导航。
- 只使用 Git 及标准库作文件读取、JSON/gzip/ZIP 解析与摘要核对；没有运行 pytest、native、构建、产品/观察器进程、服务、浏览器、远程或网络动作；没有改产品、测试、既有证据或 Git。唯一写入为本报告。四份未跟踪的保留 Python 草稿未作为已提交交付或正式测试引用。

冻结文档 SHA256：Intent `12a585c4601a087f77a852ea851cad51da19bf74503ab433c755668d43a11394`；SPEC `99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986`；PLAN `c0cab8b9e30fe87f077373e7c8bed63023167115b01aa81284f74469b094d617`；Review Prompt `6a7cc899a5eca649dffa4cd4202dc746d7b58bfd0c5ec4e2321abecb5bfacdb4`。

| Prompt 要求 | 本次执行及判定 |
|---|---|
| 先核 PLAN 的位置、方案、验证及未说明偏差 | 对六产品/两测试和 PLAN:329–335 核对，详见下一节；没有发现本增量未说明的方案变更。完整验证步骤仍未完成，不能因专项符合计划而判交付。 |
| 从 Intent 确定用户/调用方/维护者及目标 | 下文列 Local、Web、Hub 维护者、Agent/调用方、验收维护者五条实际入口路径。 |
| 主入口逐跳、当时可见内容、操作/知识/下一步 | 逐条记录 README→指南/Skill/验收说明→具体操作入口与结果确认方式，明确只作静态回放。 |
| 局部必要输入含义/取值/取得方式 | 单列档案/state、OCR、revision、项目/source、CID/AID/V/P、REF/table/window、输出路径、Hub 凭据与同步比较值。 |
| 逐 SPEC 核可复核证据；功能、文档、发现分别判 | 下文分开限定测试通过、已更新说明/可发现、整体未完成，并逐 A1–A12 判定。 |
| 缺口性质、用户/影响、可用路径、适度建议及通过条件 | 下文区分已观察监督错误、确定源码路径缺陷、静态队列风险、仅缺动态证据，以及用户路径局部缺口；不把未覆盖等同已复现。 |

## PLAN 与实施核对

六产品修改落在 PLAN:72–76 的快照、传输、处理、创建端上传、接收与恢复职责内；PLAN:329 明确补充本轮实际方案与原因：保守证明独占/最后用途，以持久 pin 覆盖正文到元数据窗口，先退休 CID/AID/UID，再删无其它用途 canonical。`document_protocol.py:176` 将 reclamation 纳入恢复排除，避免旧备份覆盖当前 fence；不是新增用户操作或额度。两测试对应 PLAN:81、107 的自然设计→有效红灯→同测试绿灯→独立意见。本轮没有改 SPEC，所做行为可由 B5/B7/B9 推出。

具体静态核对：`document_snapshots.py:25–37` schema context 先结束，再以既有 material 初始化档案身份；`core.py:180–185` 确认连接退出会提交/关闭。`_gc_owner:60–65` 绑定持久 archive identity 和 resolve DB 路径，collector:106–130 用同一 SQL 读快照取用途/owner，capacity 内不初始化身份。`_own_blob:66–76` 不凭既存未知正文认领独占；旧 v1 owner 和多 owner 保守留存。`capture:215–223`、`document_processing.py:9–11,34–37`、`managed_document_uploads.py:116–119`、`processed_documents.py:74–79` 的 raw/results pin 覆盖 put→capture、处理读→attempt、commit→receipt/stage。pin 创建/退出的容量锁不跨内容解析、网络、guard 或 SQL 写事务。

`reclaim_candidates:108–130` 保护发布 ledger/当前发布、仍连续授权的当前 CID、最新 AID 结果和 stage；并非用“当前库没有行”直接删共享目录。`:133–143` 持久 fence 在 unlink 前；`:138–140` 只用属于本 archive 的 managed receipt 推导 UID 退休，另一 archive 同 submission 不跨过归属判断。`document_transfers.py:193–202` 既有 UID 完整核 binding/blobs 后返回，新增 canonical GC 只发生于新 admission；既有 TTL 回收仍会执行，不声称 replay 对所有真实过期元数据都无任何维护副作用。授权、process、publish、retry/detail 和 prior 增加退休检查，防旧 SQL 恢复单独复活身份。`:151–158` 只删精确独占、未保护的普通文件，Windows PermissionError 不假记释放容量。

这些静态机制未见新增反向锁环或确定误删路径，但不构成在途/崩溃/恢复/Windows 删除安全实测。共享最后 owner、旧登记、残留 pin、无回执 committed transfer、无用 results/stage 的完整回收能力仍未交付，PLAN:335 明确保留。此为内部回收，不要求为了满足审查而固定修改 README；实际用户入口和诊断路径见后文。

## 审查发现与仍未完成的问题

### S1 · P1 · 当前产品监督缺陷：watchdog 的身份读取异常退出未被 controller 作为健康失败处理

性质：**实际观察到 watchdog 异常；更坏清理分支为静态风险，未声称已发生。** 容量 Hub-v2 原件与 `candidate-reclamation-supervisor-failure-v2.md` 保留 `watch:114 → matching:60 → cmdline → psutil.AccessDenied`，而 `matching:62` 只捕获 NoSuchProcess/ZombieProcess。`run:147–164` 只 poll worker，不监测 watchdog 退出；worker/watchdog 共用 stderr（:136–144），worker 非零时把共享尾部写成原生解析错误（:163）。因此一次预期缺 OCR 失败混入真实监督 traceback，容量负控正确拒绝该轮。

影响两端 POSIX 创建端任务及维护者诊断：独立兜底监督可以先退出，主进程未及时明确报告其健康失效；若之后 controller 也退出，独立兜底已不在。持续 AccessDenied 在 `stop_tree:67,72` 再抛，可能绕过 `run:170–180` 的失败/等待/lease 收尾。这些源码条件违反 B9/PLAN:74,91 的必要监督及失败安全要求。**本次旧任务实际已 failed/lease 清理，未证明游离子进程、永久 processing、资源越界或持续拒绝发生。** 正常退出竞态仅假说，不是已证根因。

建议及可验证通过条件：另作 PID 观察与 watchdog 健康用例；区分可证退出/身份变化和仍属本任务但不可观察，持续盲区应失败并经已证 containment 清理；controller 能识别 watchdog 异常退出，保留原错误/清理错误。用真实退出窗口、live AccessDenied、PID 复用、watchdog 异常，以及原缺 OCR/预算/后续合法任务作独立红绿验证。不能 blanket 忽略 AccessDenied、过滤 traceback 或放松当前容量负控。此建议不触发本轮实施，既有保留用例不重开。

### S2 · P1 · 既有确定路径缺陷仍在：路径 refresh 发布拒绝可绕过终态收尾

`documents.py:428` 先写 refreshing；`:429–431` 只保护扫描；`:432–433` 的最终 `_publish` 在其外，而 `:459 → snapshots.publish:263` 可因当前配置/CID/AID/授权变化抛错。因而真实结果已生成、最终发布被拒时，可保留 refreshing 来源及已提取 ready/partial 的非发布尝试，未按 B4/B5/B9 报该尝试发布失败。影响显式路径 refresh 的两端用户；managed 上传/缓存 reprocess 已有自己的 fail_current 收尾，不能据其限定 passed 关闭此路径。

可用路径是 files/sources/CLI 查看当前状态；它不能补产品终态。建议在维护者授权的后续范围按冻结身份 CAS 收尾并保留旧发布/其他来源资格，以被拒发布后来源/尝试真实终态、旧请求不改新状态、下一次合法处理可用作通过条件。`path-finalization-retained.json`、PLAN:314 明确候选产品补丁未应用，Hub 搜索封套测试缺口保留；本轮没有修订或专跑，不把 Hub 尚不合格测试当有效业务红灯。

### S3 · P2 · 既有局部用户信息缺口：路径 Web“文件状态”没有候选/重试比较值

Local 主导航文档→来源行“文件状态”（`static/index.html:138–141`）确实进入 `/api/documents/files`，但渲染只展示 path/status/version/error，未显示 published_snapshot/latest_attempt/retry_target、P/CID/AID。影响需要从网页判断失败新候选并取得重试值的路径用户，违反 B5:63 的网页详情要求；不是所有入口阻断。CLI `documents files --source-id ID` / API 返回现成详情，是已有可完成的替代路径；项目文档库 nativeDetails 的完整说明不能当此局部 UI 已实现。

建议在该真实入口呈现当前详情/比较值或明确直达可取得这些值的操作说明；验同一普通/全局路径的首次失败 V/P0、旧发布+新失败候选及过期值，用户能取到正确 CID/AID/V/P 并确认对应原件。无需新增另一套 GC 管理 UI。

### S4 · P2 · 已说明但未完成的 PLAN 行为：活跃服务的 CLI 内容任务交接

PLAN:75 要求同 state 服务已运行时由服务 worker 处理、CLI 入队并等待。`hub_admin.py:441–445 → document_cli.py:54–85` 仍构造自身 HubDocuments、直接调 native refresh/reprocess，没有交接既有服务身份；前景路径可用。影响依赖服务账户 OCR/语言/临时目录权限的 Hub 维护者，交互 processing-status --check 不能证明服务任务身份。此为明确未完的计划实现/证据，不是本增量隐瞒偏差。

建议后续补真正同 state 服务交接，或在改变已确认方案前回相应阶段确认；以实际 H 服务身份/worker/原件、CLI 等待终态和重启恢复为通过条件。本轮基础 Hub smoke 不覆盖这件事。

### S5 · P1 · 已保留的静态队列风险，没有新增复现结论

`Snapshots.root:24` 同父目录不同 DB 共根，`managed_document_uploads.py:193–205` 共用 upload-queue.lock，而持有者 drain/释放后只查自身 DB。另一 DB 的 kick 忙退后，其 pending 可能无人继续唤醒。仍是有具体静态路径、尚未实测复现的既有风险；单档案 Windows/Mac 改善及本次同档案容量通过不能关闭。维护者已明确保留且不专跑/不应用拟议补丁，本报告不重开决定，不将其记为 SPEC 豁免。

### E1 · 必要证据缺口，不能改写成已复现缺陷

多档案同 submission 的有效分块/当前回执、停机 DB 一致改名后旧路径复用、CLI 首个失败候选 owner 初始化、共享 SHA 最后用途、连续重叠来源、无用 results/stage、put/commit→登记窗口、未知/legacy owner、崩溃 pin/旧 DB 恢复、Windows in-use 等仍须各自动态证据。当前审查认为 receipt/owner 修订阻断了**已知静态反例**，不因此证明这些必要场景已运行。补证应逐原身份/CID/AID、真实字节及前后资格/物理容量核独立真值；只比两产品输出相同不足以通过。完整 C1/E/H/X/最低三平台与当前提交 CI 缺口见逐 A 判定。

## Intent 角色、主入口与具体值的取得

以下是本轮实际读取可见说明/代码后的静态回放。各步可发现/局部信息充分不等于已从真实浏览器或安装包完成全路径。

| 角色和要完成的结果 | 起点→当时可见内容→下一步与确认结果 | 局部充分性及整体判断 |
|---|---|---|
| Local 使用者：纳入 Word/Excel/PDF、项目检索、核原件 | README:33–48 介绍 Web“文档”、CLI、保存 pending/明确 refresh；:61–67 直接介绍 008/创建端/OCR/未发布并链接指南。TRIAL_GUIDE:155–180 给同构建 wheel、独立档案、材料准备、status/configure/check；:184–208 给 project create/projects→add→refresh→files→search→text/table/原件。 | 可以发现并开始；当前原件/表格读取说明完整。整体仍受 S2/S3/S5、完整平台未验限制。 |
| Web 用户：选择/拖入、更新/移除、判断处理中或失败候选 | README:54–65→指南:184–186,212–224；实际两端 file accept/上传列表介绍新格式/20MiB、接收不代表可检索，资料行详情给处理与重试值，reader 给范围/表格/原件。Hub 首屏明确从维护者取 HTTPS 地址/凭据、内存认证。 | 正常项目库入口有支持对象及指引；本轮没实际重做选择/拖入。路径来源局部 S3 单独成立；SC1 保留上传/生命周期验收不能以说明补齐。 |
| Hub 维护者：独立部署、配置 OCR、确认执行身份 | README:55,63–67→指南:168–180；Hub 使用实际 state-dir 而非另开默认库，程序/data 来自材料清单，status/check 显示实际身份与 revision；指南:180 明确交互与服务身份分别核。 | 前置条件取得路径清晰；S4 活跃服务交接未完，故不能认定实际服务业务可完成。 |
| Agent/API 调用方：准确引用、只读检索、从元信息转取原件 | README:9–23 接入 Skill，:35 文档工具→检索 Skill:60–72。先核实际 schema，list_sources 看覆盖，list_projects 取项目，search 返回 exact REF，read text/table/original-info，原件转 CLI/认证 API。 | 只读/管理/创建端边界可发现，参数来源有说明；本轮未新增 MCP 行为或实际 MCP 回放，全同步/路由/平台不由本次容量证明。 |
| 验收/运维维护者：复跑、诊断容量并判交付 | README:67→SPEC/PLAN/证据目录；TRIAL_GUIDE:172→验收 README:3–32→pending-verification 当前 checkpoint→candidate development/独立报告；指南:228 说明256MiB及候选不按24小时淘汰，CLI/API真实错误报告超额。 | 内部 GC 无新用户参数，沿现有 admission 触发，未发现因未改 README 而新增操作阻断。维护者能从档案路径定位 `.document-snapshots` 并沿证据索引核限定范围；未要求普通用户手改 owner/fence。旧 e8 D1 历史字段已显式标历史（pending:425–427）。 |

| 必需值 | 含义、适用取值和取得/确认路径 |
|---|---|
| Local DB、Hub state-dir、Python/入口 | 操作者指定独立档案；Hub 取实际 hub status/安装状态目录，不能用无关新目录；指南:168 给 bin/python 与 Scripts/python.exe 及对应独立 smm/smm-hub。 |
| OCR PATH/DIR/languages、R | 指南:172 的材料清单 `ocr_executable`/`ocr_data_dir`；自部署须 `--version`、指定 data 的 `--list-langs` 实见 eng/chi_sim。持久 configure 的 R 原样取当前 status revision，两个绝对路径在创建端，语言顺序按实际配置；--check 只证当前账户。 |
| project_id/source_id | project create/projects 返回真实所在端项目 ID；add 返回 source ID，之后 sources 可确认；Local/Hub ID 不互猜。指南:189–200 与 Local help:155–166。 |
| document_id/CID/AID/V/P | 从当前 files/library/适用网页详情 `retry_target` 原样取得，失败新 CID 不能取旧发布版替代；无发布 V/P0。指南:218–224；路径网页缺值局部见 S3，CLI/API有替代。 |
| REF/table_id/行列/输出路径 | REF 原样取本次 search，空白原件可取列表 original_reference；table_id 取同快照 hit/read tables；CLI/API 1起、终点不含，Web结束行列包含。输出为操作者指定尚不存在的新路径，拒覆盖；指南:195–214。 |
| HTTPS/token、KEY/HID/generation | HTTPS 与 hub-token 文件由 Hub 维护者提供（README:55、Hub首屏:6）；同步比较值取 sync-status，默认关闭，暂停/共享及待确认见 README:56–59、Skill:68；认证值不放 URL。 |
| 验收材料与输出目录 | 验收 README:17,22–26 给显式 prepare 输出清单及三个实际字段、全新 ACCEPTANCE_EVIDENCE_DIR/源码 PYTHONPATH。这些为维护者验收工具，不是普通查询自动准备步骤。 |

上述材料没有在本轮提供完整真实入口执行；整体可完成性因此仍待 E/H/X。已展示局部明确缺值的 S3 不以“其它入口未知”搪塞；有清晰 CLI 替代路径，也不夸大为无任何办法重试。

## 原件、测试与构建证据复核

定义为 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`，v3 自然设计实际 SHA `75a141a115693f4302b1a88a15f6f0bdbfc1585ee29224290d950d56e0b46a70`。设计/匹配投影指向现存原件且摘要相同；设计明确 `canonical-other-paths` 等必要 gaps。实际 partial 夹具是原生文字页+需 OCR 扫描页、零表；四份 ready 各含三表，承担非空全表保护。不能写成本次 partial 表格处理已覆盖。

| 实际收据 | 本次实际复核 |
|---|---|
| Local red-v3 | result SHA `6b243b214c068ef4d0c1f7a11cb03dc055dcc22a4ed3dc4f10323a31db16c784`；666 artifacts/2,974,749字节逐SHA匹配；24 test bindings 与绿灯完全相同。独立 red-review SHA `f16bd6da9f6de56350353c1df33b1420c0b7148110dbc4db600a45db9ec685bf`，expected_failure。 |
| Hub red-v3 | result SHA `eeb17a1efb6ee47ac5c12d5fd9ecb447b0a803444762c9ede0aad1b3c74f37ac`；670 artifacts/3,637,091字节逐SHA匹配；24 test bindings 与绿灯相同。独立 red-review SHA `7e01894f6ae89df1710944dd72401395b670ac87b20eed5a798f9da8e3af126b`，expected_failure。 |
| Local green-v3 | result SHA `09393a7d0038519b77712d6ccffb938b5b6b45d2a88de045a961ba1be527ef67`；3002 artifacts/5,454,832字节与91 bindings逐SHA无不符；主项 exit0，1 passed/130.23秒；回归 exit0，9 passed/101.07秒，无skip。独立 review SHA `2f51c85170210a608c9b15b49ec3acf1251e0e2605d76af4f3b9469f920b24d7`，仅该 TC passed、covers=[]。 |
| Hub green-v3 | result SHA `845f16d9b6b94c567de0ecd21a4c0777baf28e5652d3916869b8210b203b378a`；3006 artifacts/6,892,950字节与91 bindings逐SHA无不符；主项 exit0，1 passed/169.96秒；回归 exit0，8 passed/36.97秒，无skip。独立 review SHA `d5ec26c0d251b2368fbbabe1940ae0969432a61fba25f35441823eefcd1462f5`，仅该 TC passed、covers=[]。 |

两端红绿主 business_command 也逐值相同，主测试 SHA `6f3057f4debe36c6808985a2a115e88bec0e4d56c86aa89809ffad4828f5554e`。绿灯六产品 SHA 与 `candidate-v3-source-sha256.json`、当前已提交文件相符。红灯产品绑定不同是预期旧产品，不把与当前源不等当证据漂移；本轮没有重新执行红灯。

两绿灯 lossless 索引 2904/2908 JSON 全部解压、解析并核原/压缩 SHA 和长度，原 JSON 分别13,463,496/17,115,584字节；每端54份 gc 输入 gzip 全部解压核双摘要/原长度，原量746,619,144/746,619,132字节。不是把压缩体积计入生产额度。每端12份 target-complete 的 index精确0–11、ID唯一，普通/全局×none/ready/partial×2。每端26份 physical-capacity 记录：1次247,463,936=236MiB，25次268,435,456=256MiB；254MiB是236+18的替换阶段合计推导，没有独立物理采样。12份满额拒绝事件 body_events 均为空；测试:56–74 有真实元数据/正文事件正负控，:290–305逐旧请求完整 frozen 比较及真实 CLI 业务拒绝。测试:181–215、Creator.read 用源真值核完整正文/表/原件，不能只首目标或两个产品同错通过。

另外打开两份私有回归目录所有文件，Local1149份/5,264,840字节，Hub450份/4,059,666字节；JSON/JSONL可解析、OOXML ZIP CRC正常。排序相对路径+NUL+长度+NUL+SHA+LF 的完整清单摘要分别 `60830db727e9fe2877106dc8a4c35f0058b4371a68d39f3eaffd16098a32714e`、`a69add971500a32f51b1bad48aa73737c7846e118ef30ceb85b424c152515a4a`，与独立意见所录一致。9和8是两批实际执行数，restore项有重复，不能称17个互异用例；Hub回归也没有另含精确+1容量主项。本文未重新手工穷举独立 Reviewer 已记录的全部逐格/服务清理断言，不把摘要核验再包装为第二次业务执行。

构建原件实际 ZIP CRC、成员摘要/当前源码核对：Local45 Python成员逐字一致；Hub46直拷成员逐字一致，另1个 `_archive/__init__.py` 与当前 shim 的既定替换逐字一致；Local1个 HTML资源相符。两 wheel 分别198,170字节/SHA `d16c1180f4d1079ce5abce6858124ad1e3df3cf6b68f815e4bcddd061df86bf0`，182,314字节/SHA `e469e62d42f1ff978283ea4cbdcfc4f4bf0dc94ef1cef05afb34db1dab724554`。这只认构建/入包。

`build-v3/base-hub-smoke-commands.json` 六命令日志摘要逐个核对：venv/install/import/公布入口status exit0；`python -m smm_hub` exit1、“smm-hub documents” exit2错误完整保留，不当产品承诺。实际 `smm-hub hub --state-dir DIR documents processing-status` 成功，原输出为Python3.11.11、无Local/处理extras、持久archive identity与owner可用，status接收schema为stdlib且解析/OCR不可用。因此仅补充 Mac基础Hub导入/构造/公开status smoke，**不是**最低Python全部格式/OCR、安装后GC业务、服务或X无依赖接收。

v1回放回归失败、v2 owner静态问题、Hub-v2实际监督失败及旧独立意见原文均保留。当前 development/pending/PLAN 对上述限制表述一致。e8六份官方 CI是旧版本证据：不能覆盖本次 GC源码；当前提交新CI尚待完成/回收，不能提前以成功或skip计通过。本轮未联网重核旧官方artifact，也未确认线上 PR正文，以上是本地可复核材料结论。

## SPEC A1–A12 当前判定

| 条件 | 现有增量能支持什么；仍未关闭什么 |
|---|---|
| A1 入口/创建端 | 本TC两ASGI创建端普通/全局真实上传/替代/移除、认证Hub及当前比较值有效；不覆盖真实浏览器拖入/所有入口，S3/S4与SC1保留项仍在。 |
| A2 DOCX | 回归含既有Office路径，不能用其代全部部件/平台支持验收；本容量主项全为PDF。 |
| A3 XLSX | Hub同步回归含源结果保真，不是全部sheet/隐藏/日期/公式或平台重新验收。 |
| A4 PDF原生/表格 | 旧ready原生正文/三表与partial覆盖被保护；不是全混合/复杂表格负例矩阵。 |
| A5 OCR | 故意缺OCR的失败与partial真实可见，负控不放松；不是三OS/服务OCR质量通过。S1仍待修。 |
| A6 直接索引 | 8项Hub回归中有源结果/原件保真及零处理的既有子路径；不是X六方向或服务/无依赖全部接收。 |
| A7 成套/并发 | 当前旧begin/part/commit/retry拒绝与pin机制有静态/限定证据；动态多档案、在途、stage、崩溃/恢复完整矩阵未齐，S5保留。 |
| A8 生命周期 | **只认可首个独占候选替代/移除容量子例**与当前候选/旧发布保护；S2、连续重叠来源、取消、完整生命周期不关闭。 |
| A9 查询/原件 | 本TC旧有资格正文/全表/原件及原ref保持；此前纯Hub路由/处理版本隔离/合并表头限定结论不重开，也不因此补全所有入口。 |
| A10 有界/隔离 | 真实236/256MiB回收准入与满额正文写入前拒绝可信；全GC/全部资源/监督异常和五秒释放、Windows差异未完成，S1明确未修。 |
| A11 兼容/发现 | README→指南/Skill/验收的静态发现路径可达；两包入包与Mac基础Hub3.11 smoke成立。当前全回归/CI、最低Python三平台完整安装业务/全部迁移兼容仍未满足。 |
| A12 平台/证据 | 本限定原件可读、摘要/独立意见相符；E三格/H三格/X六方向及完整C1和requirement-level独立验收仍未完成。 |

功能专项通过、说明可发现、全部用户路径可完成分别判断：首项容量专项和本轮证据可保留限定 passed；说明有实际可达路径，局部 S3仍缺；完整 R008 受产品/证据缺口约束，继续未完成。维护者保留取消/C1/共享Windows argv/跨档案队列/路径refresh封套与未应用path产品补丁的决定不变，本轮没有改测试、加skip/xfail或重开这些工作。

**当前交付结论：needs_revision。** 可以将本报告与精确HEAD、上述限定passed/仍失败/未验证清单交维护者继续评估；不能作为合并、发布或R008通过依据。
