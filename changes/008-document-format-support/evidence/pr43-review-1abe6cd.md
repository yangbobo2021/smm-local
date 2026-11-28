# PR #43 独立检查点审查：1abe6cd

**总体结论：needs_revision；R008 未完成。** 本次 matching 身份分类改动及其限定证据可信，未发现该 11 行产品增量引入的新实质缺陷。它不能关闭 watchdog 健康处理、路径 refresh 终态等现存产品问题，也不能覆盖旧提交的 CI 失败或替代完整 C1/E/H/X。

## 审查版本、方法与边界

- 仓库 `/Users/boboyang/work/smm-008-impl`，完整 PR 范围 `d8894d429ebe0915e377513a637b5dfc0fc7ea1a..1abe6cd4de5b40fca7bf0152fc17da6fbdda0fcc`；重点增量 `3e29255..1abe6cd` 为 22 文件。
- 实际读取 `AGENTS.md`、`changes/_templates/pr-review.prompt.md`，按其顺序核 PLAN、Intent 角色与真实入口、逐项 SPEC 及证据。依据为 `changes/008-document-format-support/{intent,spec,plan}.md`。阅读前版报告 `evidence/pr43-review-3e29255.md` 作为历史，并对当前源码和新原件重新判断。
- 通过只读 `gh pr view` 核到线上 PR head/base 与上述一致、OPEN、isDraft=true；当前正文明确 helper 限定范围、旧 3e CI 失败及完整交付未完成，没有把新 CI 当通过证据。本文不发布评论、不更改 PR。
- 本轮只做 Git/源码/文档/JSON/XML/归档及摘要核对，**没有运行 pytest、构建、产品、远程探测或任何保留用例**。下文“实测”均指实际打开的既有执行原件；“静态”指本轮代码/说明回放，不是新业务执行。唯一写入为本报告。
- 四个 untracked 历史测试草稿未作为交付代码或通过证据读取；保留取消/C1/共享 Windows argv/跨档案队列/路径刷新封套的决定不重开，不作 SPEC 豁免。

## PLAN 与完整 PR 改动核对

完整 diff 覆盖两端原有入口、可选处理依赖/独立打包、OOXML/PDF/OCR、规范结果与快照/资格/版本、监督及后台队列、成套同步、查询与原件、两端网页、CLI/MCP、用户说明和验收设施。主要职责与 PLAN“修改位置与数据流”对应：接收端走 `processed_documents.py` 和标准库结果校验；格式库仅在创建端 worker 导入；新增处理组不强制基础接收端安装；原件与结果经快照及引用绑定；原件输出为排他新建文件。PLAN 中拆出 transfers、混合 PDF、发布边界、GC pin/owner、临时空间一次完整重采样等调整均有记录；一次重采样行为已同步 SPEC B9/A10 的确认记录，不能当未说明降格。

本次增量唯一产品改动是 `document_supervisor.py:60–69`：在创建时间校验后读取 token 命令行，AccessDenied 时才独立确认退出/zombie；仍存活或状态不可读继续抛出。没有增加等待、重跑、预算变化或“所有权限错误均忽略”。新 240 行测试、原生设计/匹配/复审投影、两份证据索引、pending 及 PLAN:337–339 对该限定范围说明相符。未见本增量隐瞒的方案或验证变更。

**尚未实现的 PLAN 行为不能视为计划已完成：** PLAN:75 的活跃服务 CLI 交接仍缺；PLAN 的独立安装最低 Python 三平台业务、完整 E/H/X 探针/编排和逐项结果仍缺。现有 `document-formats-acceptance.yml` 明确仅 components，验收 README 也明示没有一条命令完成 C1/E/H/X。这是已披露的未完成项，非新 helper 的回归。

## 产品发现（当前源码仍成立）

### F1 · P1 · watchdog 异常退出未被 controller 作为必要监督失效处理

性质：旧真实任务已有 watchdog 异常退出；当前更坏清理结果为静态风险。`document_supervisor.py:119–130` 的 watch 调用 matching/children，存活身份仍不可读会抛出；本次正确保留此类异常。`:152–156` 启动 watchdog 后，主循环只 poll worker，没有 poll/健康确认 watchdog；`:172–174` 可以在 watchdog 已异常退出时把 worker 结果作为完成返回。worker 与 watchdog 共用 stderr（:145–153），worker 非零时又把其尾部归为原生解析错误（:172），此前 Hub-v2 的真实 AccessDenied 已因此混入缺 OCR 诊断。`stop_tree:76,81,91` 的持续权限异常也没有稳定收尾保护，`run:175–189` 可能在清理调用中再次抛错。

影响两端 POSIX 创建端：独立兜底监督失效可以未及时显式报告；若 controller 随后停止，所依赖的兜底已不在。违反 B9 必要监督、失败终态与回收要求。**未观察到本次绿灯有游离任务、永久 processing 或预算突破；原现场正常退出竞态仍未证明。** helper 测试证明的是已核退出与 live 拒绝分类，未触达真实内容任务/watchdog 健康。

建议按已登记 task-supervision 缺口补 controller 对异常 watchdog 的健康处理，保留原错误与清理错误，经已核身份/containment 收尾；以真实 watchdog 异常、live 拒绝、任务树结束、5 秒终态/槽位恢复、另一资料读取及下一合法任务成功为通过条件。不得吞 AccessDenied、过滤 traceback 或放宽现有容量/OCR 负控。

### F2 · P1 · 路径 refresh 的最终发布拒绝仍绕过终态收尾

`documents.py:428` 写 refreshing，`:429–431` 只保护扫描，最终 `_publish` 在其外（:432–433）；`:459` 调 `snapshots.publish`，后者 `document_snapshots.py:263` 会因配置/CID/AID/授权变化拒绝。真实结果生成后在此拒绝，会保留 refreshing 来源及提取 ready/partial 的未发布尝试，未按 B4/B5/B9 报告该尝试发布失败。两端路径 refresh 受影响；managed 上传和缓存 reprocess 的 `fail_current` 不能替代本路径。

`path-finalization-retained.json` 与 PLAN:314 明确产品补丁撤回、Hub 封套测试仍不合格。现有 files/sources/CLI 可查状态，但不能补终态。建议以后按冻结身份 CAS 收尾、拒绝旧请求修改新状态，并核旧发布及其他连续来源保留、下一合法任务可用。本轮未修改或专跑该保留用例，也不把无效 Hub 测试当有效红灯。

### F3 · P2 · Local 路径 Web“文件状态”缺少新格式候选及重试信息

真实路径为主导航“文档”→来源行“文件状态”（`src/smm_local/static/index.html:125,138–141`）。该按钮确实请求 files API，但 :141 只渲染 path/status/version/error，未呈现 published_snapshot/latest_attempt/retry_target、P/CID/AID。B5 要求网页详情区分旧发布和失败新候选，此局部入口尚不满足；用户不能在此取得正确重试比较值。

已有可用替代路径为 `documents files --source-id ID`/同一 API，指南:193,218–224 说明取 retry_target；项目管理库 `nativeDetails` 也不是这个路径入口。故这是局部功能/信息缺口，不是所有用户都无法重试。建议此处展示当前详情或明确直达取得值的路径；用首次失败 V/P0、旧发布+新失败 CID、过期值三个状态验证用户能辨认并取得 CID/AID/V/P。

### F4 · P2 · 活跃 Hub 服务的 CLI 处理交接仍未实现

PLAN:75 要求同 state 服务存在时，CLI 采集/入队，由服务身份 worker 处理并等待；`hub_admin.py:441–445 → document_cli.py:54–85` 仍直接构造 HubDocuments 并调用 native refresh/reprocess，无交接。前景 CLI 有可用路径，但依赖服务账户 OCR/data/临时目录权限的维护者不能据交互 `--check` 推定服务任务可用。

这是明确的计划实现未完成，非新 helper 隐藏偏差。建议补同 state 服务队列交接，或先确认方案变化；通过条件为实际 H 服务/子进程身份、CLI 等待终态、真实原件及服务停启恢复。

### F5 · P1 · 保留的跨档案队列唤醒静态风险仍在

`document_snapshots.py:24` 同父目录 DB 共用 snapshots root；`managed_document_uploads.py:193–205` 共用 upload-queue.lock，忙退后只有当前 owner 查询自身 DB pending。另一档案在锁忙时提交的任务可能无人继续唤醒。单档案 Mac/Windows 通过不覆盖此路径。

这是具体静态路径，尚未实测复现；维护者已明确保留、不新增用例或专跑，本报告不重开授权。若后续纳入，需以两个独立 DB 的真实交错提交、两份队列均终态及无重复任务为通过条件。它继续限制 B9/C1 完成判断。

本轮不把尚缺动态证据的 GC 共享/恢复分支推断为新确定误删缺陷。当前保守 owner/pin/退休与发布 ledger 静态机制仍在；首个独占候选容量子域改善可保留，其余分支不自动通过。

## Intent 角色与主入口回放

以下逐跳依据为本轮实际读取的当前 README/指南/Skill/帮助声明与 UI 代码；未启动浏览器或产品，因此不宣称整体动态完成。

| 角色/目标 | 用户做什么、需知道什么；当时可见内容及下一跳 | 局部与整体判断 |
|---|---|---|
| 本机用户纳入 Word/Excel/PDF 并核对依据 | README:33–48 先介绍现有 Web/CLI 和 pending→明确刷新，:61–67 明确 008、创建端依赖/OCR/未发布并直链“008使用指南”。指南:155–180 给同构建独立 wheel、Python路径、材料与 status/configure/check；:184–208 给创建项目→add→refresh→files→search→text/table/原件。 | 能发现并开始；格式限制、前置条件及正常操作说明充分。F2/F3/F5 及完整平台未验限制整体完成性。 |
| 网页用户上传/替换/移除并判断结果 | README:54–65→指南:184–186,212–224；两端 input accept/拖入区列明新格式，Hub首屏说明凭据从维护者取得。资料库 nativeDetails 提供处理状态/重试信息；reader 提供提取覆盖、表格窗口和原件按钮。 | 主项目库入口可达，收到不等于已索引、partial/failed 可见。路径“文件状态”另有 F3；已知浏览器 TC 的断言/证据未完成，不能由静态说明当实际完成。 |
| Hub 维护者部署与服务 OCR | README:55,63–67→指南:159–180 的独立 Hub wheel、实际 state-dir、绝对组件路径和执行身份；:172 明确材料清单字段及自部署验证办法。 | 前置值的取得路径清楚，不需要另猜 PATH；服务完整业务受 F4/H 缺口限制。 |
| Agent/调用方检索、引用、核原件 | README:9–23 安装 Skill，:35 指明三工具；Skill:60–72 先核实际 schema→list sources coverage→list projects真实ID→search exact REF→read text/table/original-info→CLI/认证 API 原件。 | 管理/只读及创建端边界可发现；参数含义与来源充分。新 helper 无新用户参数；本次不把既有 MCP 子路径证据算全格式/所有平台通过。 |
| 维护者复跑与诊断/判交付 | README:67→SPEC/PLAN/证据目录；指南:172→验收 README:3–32→pending/current或historical项→各 development及独立意见。验收说明区分普通CI、组件、安装、E/H/X及逐skip原因，:228 指出256MiB与候选保留。 | 现有准入错误/诊断入口可用；内部 GC/helper 不要求用户手工操作 owner 或新增专用 UI。当前/历史和未通过范围可找到，完整验收仍未完成。 |

具体所需输入均有可达出处：Local `--db` 是操作者指定的同一独立档案；Hub state-dir 从既有安装/status取得（指南:168,180）；OCR 程序/data 从材料清单 `ocr_executable/ocr_data_dir`，自行部署用 version/list-langs核，R取刚查看status；项目ID取 create/projects，source ID取 add/sources；ID/CID/AID/V/P取当前 files/library 的 retry_target，不能借旧发布猜新候选；REF取本次search或空白列表original_reference，table_id取同快照hit/read tables，CLI/API行列1起终点不含，网页终点含（指南:202–214）；输出路径为尚不存在的新文件；Hub HTTPS/token由维护者提供，KEY/HID/generation取sync-status且默认关闭。F3的局部缺值仍单列，不能以其他入口存在而抹去。

本轮未确认额外的规格外用户路径阻断，不为假设补新要求。功能专项、说明可发现与全路径动态完成分别判断。

## 新身份 helper 证据的实际复核

读取 `evidence/process-identity-development.json`、自然设计/匹配投影及原生执行/复审原件。以下摘要是本次实际计算，非沿用历史报告。

| 原件 | 实际复核结果 |
|---|---|
| red-sc10-process-observation-v3 | result SHA `414d0d211aa8ab28709e7aed28a9e73f4d7eea082866e148a88af149afb984e8`；18 artifacts均核SHA；64 bindings中当前仅supervisor不同，其红灯摘要 `e4af95b631dbeb558c2678dbdbce4ba5e43aebc00d94ef46536299f04e8c8d23` 对应原3e产品，不能当漂移。stdout明确测试:213→原matching:60→cmdline AccessDenied，1 failed/0.63s。两个目标真实live与zombie原件可读，第二次产品zombie分类未到达，不追认红灯已执行完。 |
| green-sc10-process-observation-v3 | result SHA `272434a63a7be61403e05faea870ff7cc4e04730e4b77aba4d3c3046d8f04326`；23 artifacts/68 bindings均与现存字节一致。红绿4个test_bindings完全相同，60个product_bindings仅supervisor改变；主测试SHA `2a5bb383c12f1c093d8dbc027bed10d88125a4ef2a934e413281079b5d569171`。主项exit0、1 passed/0.61s；两目标42946/42947分别通过live拒绝/真实zombie分类，完整cleanup记录exit0/forced_kill=false/逐成员gone/errors空。 |
| debug-sc10-process-observation-win-v2 | result SHA `69f9c2372845b76e175569955f93c17a3d0608ac7db108ad65fb35888d6b42d9`；36 artifacts/69 bindings一致。source.tar 68成员中的67声明项逐SHA及当前源码一致；13份remote checksum全匹配，JUnit/9证据JSON可读。真实launcher6120→解释器14748、10928→13552，四历史成员均gone、无强清理、exit0。1 passed/2.26s，Windows无POSIX zombie明确不适用。 |
| 三份独立意见 | red-v3 result SHA `d03838cc49b2b05387349aecef40727b5f286569ae97e9f097f2444d4cab794b`，expected_failure；green-v3 `8fa3614db744ad79102eb46b4af5e05655c4ecfac60be15c895cae57de07d573`，限定passed；win-v2 `5362c6342d74259c3668890e7598bc42207868447cea93b96652a1074ef9abce`，Windows适用helper限定passed。原文可读，未用它们认领完整SC10。 |

测试独立预期来自 psutil 的创建身份、真实树与nonce握手，不取待测 matching 的返回作为真值。:35–38 先登记清理责任；:96–132 累积历史成员并在 launcher.wait 后逐成员复核，避免 Windows 解释器PID与启动器不同的问题。:169–174 分别核两个正确身份/错ctime/另一合法token；:176–185 两种live拒绝要求明确异常及PID，注入外再核真实存活；:191–219 两个真实未wait zombie各要求None；:237–238退出后各核None。恒返None、误用首目标、忽略ctime/token或吞live拒绝不能靠相互比较通过。green两目标的status拒绝事件实际出现，非仅靠断言存在推测执行。

这是对真实进程状态的受控方法拒绝注入，**不是重现历史内核拒绝根因**；Windows是SSH管理员源码组件，不是标准用户/Job/独立安装/SCM/E/H/X。准备失败和强制升级分支只作静态核对，不冒称动态通过。旧 Windows-v1、红-v2清理缺口、早green-v2监督异常与传输失败保留；新成功不覆盖旧失败。

六项原 `tests/test_document_formats_staging.py` 回归实际exit0、6 passed/140.43s、stderr空，测试绑定未改。额外原件目录 `.acceptance-local/008/process-observation-20261126/green-v3-regression` 共244文件/1,344,716字节，214 JSON全部解析；28 gzip按manifest解压核原/压缩SHA及长度全部一致。实际错误只有预期缺OCR组件的原生解析错误与“未发布暂存超过256MiB”两类；未含 AccessDenied/watchdog/document_supervisor/sysctl。27份retained诊断正文一致，不能仅凭宽泛“含OCR”断言将别的错误算预期。

两wheel原件实际核长度/SHA/ZIP CRC及所有声明Python/HTML与当前源：Hub182432字节/SHA `533e71d4a79d334a442c932594bc594925d581e0b19d3f079e3e81869b2ec752`，47py+1HTML；Local198293字节/SHA `fb34b70296bbc6426f6396989c49bfbfaba6f50d2cf5f42383ba41763b88db6a`，45py+1HTML；Hub shim按既定导入替换逐字相符。只认构建/入包，不认当前wheel安装后的业务。

## 旧 CI、当前版本与证据边界

对 `evidence/ci-3e29255.json` 所指本地持久原件实际核六ZIP长度、SHA与记录official digest、ZIP CRC、完整JUnit SHA及case身份；两个failed-jobs日志长度/SHA也相符。未重新联网证明官方签名，核验基于已回收官方元数据与原件，未伪称本轮重新执行CI。

| 3e29255工作流 | macOS | Ubuntu | Windows |
|---|---|---|---|
| PR 45803273804 | 466 passed / 69 skipped / 1 failed：Hub GC | 467 / 69 / 0 | 467 / 67 / 2：保留restart审计 |
| push 45803265223 | 465 / 69 / 2 failed：Local及Hub GC | 467 / 69 / 0 | 467 / 67 / 2：同两保留项 |

两workflow都failure。Mac GC在错误守卫失败，但短JUnit和完整失败job日志未给出实际error值，不能确定为容量/时间/RSS/PermissionError任一项，也不能从helper绿灯反推已修。Windows的0!=2审计失败不能改成skip/xfail或passed；本轮未改或专跑。旧六staging各实际passed也不覆盖新helper字节。

**当前1abe6cd的新CI尚无本轮回收/判读结论。** 普通CI、components、源码helper、Mac旧独立安装与本轮wheel构建是不同证据层，不能相互代替。pending中旧checkpoint标历史，新增helper单列；本轮没有发现证据将整体R008虚报passed。

## 逐 SPEC A1–A12 判定

各A都含完整范围及平台要求；下列“有限支持”均不等于整条passed。本轮深入核新helper原件，其余历史专项仅按当前源码/索引限定使用，没有把所有旧执行重封为同HEAD通过。

| SPEC | 当前有何依据 | 仍未关闭/当前判断 |
|---|---|---|
| A1 入口/创建端 | 两端CLI/API/Web及只读MCP接入、managed上传/管理/发布专项、项目普通/全局负控已有分域证据。 | F3/F4/F5、初始上传/旧页/完整E/H入口证据未齐；未通过整条。 |
| A2 DOCX | `word/ooxml`及parsers用例覆盖正文/嵌套/合并、页眉脚注等，旧开发专项/最低Mac安装有限证据。 | 全部部件独立真值、每OS/服务同版完整集合不由helper或GC回归补齐；未完成。 |
| A3 XLSX | `spreadsheet`/xlsx用例支持多sheet、稀疏坐标/隐藏/公式缓存/日期，说明区分missing/unknown不重算。 | 全平台/服务同版逐坐标及全部边界仍未完整验收；未完成。 |
| A4 原生/混合PDF表格 | `pdf`及native/mixed专项、原生/扫描强网格与覆盖有分域证据，原生优先路径存在。 | 复杂布局负例/所有入口和平台覆盖仍未齐；未完成。 |
| A5 本地OCR | 旧OCR质量专项与组件材料可保留其版本范围；本轮27预期缺组件诊断可信。 | 本轮不是真实OCR质量验收；取消及全三OS/服务CER/权限/恢复矩阵未齐，F1保留；未完成。 |
| A6 同步直接索引 | `ProcessedDocuments`不导入格式库；direct-index专项、原件/结果同步和源离线子路径已有证据。 | 六方向实际无依赖HTTPS接收、全部E/H零调用及原件证据未齐；未完成。 |
| A7 成套/并发 | transfers/metadata/CAS/pin及上传回放/分块重启等有专项，旧字节不混用机制可见。 | 保留C1重启/跨DB队列及完整故障/迟到/服务恢复矩阵未齐；未完成。 |
| A8 生命周期 | 失败候选分离、config-finalization、missing-auth、managed替换/重试、独占GC有分域证据。 | F2、在途取消/连续重叠来源/完整ready-partial生命周期及全E/H未完成。 |
| A9 查询/原件 | CLI/MCP、远端原件/处理版隔离、merged-header及empty-original有专项；表格窗口/摘要/原件路由当前源码对应。 | 真实Web reader/管理证据及全部格式入口/一层范围/旧ref持久矩阵未齐，F3；未完成。 |
| A10 有界/隔离 | 既有PDF安全/容量/一次完整采样、独占候选GC与本次helper有明确限定证据；本次原6staging真实通过。 | F1、完整RSS/temp/time/5秒树与槽位、共享/未知owner、在途/崩溃/恢复/Windows拒删及其余边界未验完；未完成。 |
| A11 兼容/发现 | README→指南→CLI/Skill/材料/证据实际可达；本轮双包入包通过、历史Mac3.11独立安装有其版本证据。 | F3/F4；最终HEAD三OS CI未回收，最低Python三系统完整独立安装业务/迁移恢复仍不足；未完成。 |
| A12 平台/证据 | 本轮指定helper/回归/Windows组件原件和独立链可读、摘要相符，旧CI失败真实保留。 | E三格/H三格/X六方向及完整C1、requirement-level独立复审未完成，必要格不能以组件/管理员源码/构建代替；未通过。 |

**分别判断：** 产品增量的身份分类限定修复可保留；当前产品仍有F1–F5及已披露未完工作。证据方面，新限定通过可复核，旧CI真实失败、当前CI未判定，完整验收不足。主入口方面，README/指南/Skill可发现并开始，F3是已展示局部缺口，整体路径仍受实现及平台验收制约。保持draft/needs_revision，不支持把本检查点作为合并、发布或完整R008通过依据。
