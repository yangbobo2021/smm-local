# PR #43 独立只读审查 v2

审查对象：`d8894d429ebe0915e377513a637b5dfc0fc7ea1a..6c65bc9295d49ff8ff13a6cfe07277b0504d7209`，并单独核对 `a505ae9..6c65bc9` checkpoint 增量。结论：**needs_revision；R008 尚未达到交付条件。** 本意见不批准合并、发布或日常升级。

本次在独立上下文实际打开 AGENTS.md、当前 PR Review Prompt、008 Intent/SPEC/PLAN、README、TRIAL_GUIDE、验收 README、完整 PR 改动清单及风险相关 diff/源码，并对照原生定义、原始执行和独立意见。没有修改产品、测试、SPEC/PLAN或远端，没有运行保留的来源取消、C1重启或 Windows argv 用例。唯一执行性检查是标准库加载 `document_results.py` 后的内存表格窗口调用，未打开档案或创建产品状态。工作区中新出现的配置终态用例和既有三个未就绪草稿均不属于本次已提交交付；`.py.txt` 是惰性证据，不当作可执行测试。

## 审查发现

### V2-F1 · P1 · 产品功能缺失：本机入口不能下载纯 Hub 命中的原件

位置：`src/smm_local/document_search.py:362–371`；调用点 `src/smm_local/cli.py:306–307`、`src/smm_local/api.py:457–462`。

`read()` 的 `remote_reference` 分支已经支持 Hub 文本、表格和 original-info，但 `original()` 只有本机 document 和 bundle 分支，其他引用无条件报“远端原件接收能力尚不可用”。因此正常从 Local 按 Hub 根搜索、读取 original-info，再使用 `--original-output` 或本机网页“下载采集原件”，对仅在 Hub 存在的资料必然失败。bundle 也只有本机那一份仍有效时才有下载路径，不能替代源机离线后的 Hub 读回。

这是源码确定的未实现分支，**本次没有进行新的远端业务实跑**。影响是阻断 Local CLI/Web 对 Hub 自有文档及其他设备投影的原件核对；不是 Hub 本身没有保存原件。直接使用 Hub CLI/Web/认证 HTTP 是现存绕行路径。

SPEC 依据：B8 原件下载与精确路由、A9；E1 入口表明确要求 Local CLI/Web 对本机及 Hub 路由下载原字节，Local MCP 的同一有效引用还须可交对应 CLI/API 下载。TRIAL_GUIDE:198–200 对“本机检索 Hub 自有资料”的说明也承诺此路径。

建议：补齐 `remote_reference` 的认证原件请求，沿现有 Hub 身份、epoch、内层引用及原件 SHA/长度验证，不回源或重解析。验证至少分别覆盖 Hub 自有和另一设备资料的真实 Local CLI/Web 下载、同一 MCP 引用交 CLI/API 下载，以及错误 Hub/失效引用拒绝；直接 Hub 正控与本机原件路径继续可用。

### V2-F2 · P1 · 产品终态不一致：发布拒绝后会永久显示“等待发布”且不展示原因

位置：`src/smm_local/document_processing.py:28–31`、`src/smm_local/document_snapshots.py:127–129,150–159`、`src/smm_local/managed_document_uploads.py:203–215`；两端轮询分别为 Local HTML:320–354、Hub HTML:58–92。同步 reprocess 的同类出口在 `documents.py:324–327`。

正常成功路径的新 `publication_pending` 比较 CID **及结果 SHA**，避免同 CID 新 profile 被误判已发布，这是正确的。然而处理函数先将 attempt 置 ready/partial/empty-success 并返回，再由调用方执行发布。如果在两者之间合法更新 OCR 配置，`Snapshots.publish()` 正确拒绝旧 revision；`run_pending()` 只把异常写入 `document_upload_jobs.error/state`，没有将当前 attempt 置为可见的失败/失效终态。files/library 的 detail 不读取 job.error。于是该 attempt 保持成功、published 仍为旧快照或 null，`publication_pending` 持续 true，而 job 已不在 pending 队列，不再有人会完成该发布。两端网页持续等待且初次上传按钮保持忙碌；重新载入资料库也只看到等待，没有真实配置冲突原因。同步 reprocess 发布抛错后同样留下成功 attempt 与未完成发布标记。

这是从现有分支可确定的状态机缺口，**没有把尚未提交/尚未执行的配置终态 TC 当作复现证据**。新原件未被错配发布，旧已发布资料也未因此被证明损坏；问题是失败终态与诊断不再反映实际情况。当前 retry_target 可能仍能给出显式重试路径，但网页没有告知本轮已经失败而需要重试。

SPEC 依据：B4 新配置阻止旧任务发布且须显式重处理；B5 latest_attempt/失败尝试与旧快照分别展示；B7 真实状态和错误；A7/A8 配置并发及生命周期。当前双端 publication 专项只证明门释放后**成功发布**的三个分支，没有覆盖发布被拒绝后的终态，公开 summary 也明确未关闭此域。

建议：让创建端在发布失败后完成当前 CID/AID 的终态收敛和可见错误；用 CAS 防止晚到失败覆盖新的 attempt。publication_pending 应仅表示仍有实际发布工作的状态。验证配置改变、当前任务发布失败与已被新 CID/AID 取代分别处理：本轮有明确终态/原因、旧整套快照与新比较值正确、用户可按合法目标显式重试，晚到任务不能改新状态；保留现有正常发布屏障绿灯。

### V2-F3 · P1 · 原 F3 未完成的产品缺陷：失效、已提交且从未发布的候选永久占用暂存额度

位置：`src/smm_local/document_snapshots.py:50–62,79,118–122`；`src/smm_local/document_transfers.py:59–60,78–89`；`src/smm_local/documents.py:258–283,464–476`、`managed_documents.py:390–393`。

本轮确实补了未 commit 传输过期后的预约/独占 incoming 回收，不能再沿用旧意见称整个 TTL 完全没有回收。但 canonical raw/results 的计费仍是“遍历全部文件，扣除曾发布 ledger”；候选被替代、最后授权撤销或资料移除时，只变更数据库授权/资格、清 FTS，没有回收失去用途的未发布 raw/results。TTL 回收也只删除 incoming，并明确保留 canonical 字节。`capture_metadata` 切换 current_capture 后旧候选同样留在磁盘计费。

因此用户反复上传独立大文件、因依赖/格式失败后移除，或替换失败候选，仍会把这些不可再重试的字节累计进 256MiB。一旦满额，新的合法资料被拒绝；等待24小时或移除失败资料都不能自行恢复。这是确定的存储/准入路径，**本次未新增满额业务复跑**。不指称仍合法的失败候选应被按 TTL 删除。

SPEC 依据：B5 每文档至多最新未发布候选及当前已发布原件，资格失效后回收无其他用途字节；B9 256MiB 未发布暂存和合法候选保护；A8/A10。

建议：补可恢复的共享引用/活跃分配感知回收，在释放字节前永久拒绝失效资格，避免误删仍在传输、已合法 commit、当前候选或已发布原件。验证替代/移除最后用途后新合法上传可准入，同时同 SHA 活跃共享、另一连续来源、合法失败候选、当前原件及崩溃重试保持正确。raw-only TTL 专项的 passed 不扩大为此项通过。

### V2-F4 · P2 · 表格上下文缺陷：后列窗口漏掉横跨这些列的合并表头

位置：`src/smm_local/document_results.py:97–100`，同样的锚点过滤用于 `:140–142` 的超额摘要分支。

窗口和 header_context 仅检查 `c <= cell.column < ce`，没有检查合并单元格覆盖的列区间是否与窗口相交。一个合法 DOCX 表头 A1:N1 横向合并、命中 M243 时，默认窗口是 row `[231,251)`、column `[5,15)`；真实表头虽覆盖所有这些列，其锚点在1，因此返回 `header_context={role:'explicit_header',cells:[]}`。用户读取后半表能看到金额，却失去文件已有的对应表头。

本次通过只读内存调用当前 `table_view()` 得到上述精确输出；输入为两格稀疏结构，未读取产品档案，也**未声称完成 DOCX→检索的端到端复现**。这是函数层已验证缺陷，适用于合并跨入所选列的实际表格；不推论全部普通表头有问题。

SPEC 依据：B2 保留 DOCX/XLSX 合并跨度；B8/A9 返回所选列必要的真实表头/首内容行和后半表格上下文。

建议：按合并跨度与窗口相交选择必要表头/单元格，保留真实锚点与跨度，按唯一格计额度；同步覆盖常规及超额摘要分支。验证完整源表中表头锚点位于窗口左侧、合并跨度跨入窗口的命中，确保对应表头出现、定位不变且≤1000格/16000码点，不通过复制主格值填满合并续格解决。

### V2-F5 · P2 · 局部 Web 指引/状态缺口：外部路径文件详情未接入候选与重试值

位置：`src/smm_local/static/index.html:141`；已有完整字段来自 `src/smm_local/documents.py:311–315`；新 `nativeDetails` 的使用仅见项目资料库 `index.html:375`。

本机 Web 用户从“添加文档来源”纳入外部 Word/Excel/PDF、明确刷新后，点击“文件状态”，页面只画 path、membership.status、内容 version 和 membership.error，丢掉 API 已返回的 published_snapshot、latest_attempt、retry_target、processing_version。路径文件不会出现在网页上传专属的 document_library 中。因此路径首次失败或旧发布版/失败尝试并存时，用户在此局部入口不能取得指南要求的 CID/AID/V/P，某些失败 reprocess 还会继续只看到旧 membership 的 ready 和空 error。

这是静态 UI 分支确定的信息缺失，**不是所有失败资料失去管理入口**：用户仍可排除/移除该来源，并用 CLI `documents files` 或原 API 取得完整详情，属于局部路径增加操作难度和状态误读风险。原 F5 的项目资料库错误展示已修，不应将本项混称其原场景没有修。

SPEC 依据：B4 files/网页按身份显示真实状态；B5:63 路径项和网页项都可查看状态及比较值；A8/A11。

建议：在现有路径“文件状态”使用已返回的详细状态和当前重试比较值，指出创建端 CLI 重试入口，仍用纯文本安全显示；无需新增网页 OCR 配置或写操作。验证真实路径首次失败及旧发布/新失败尝试：两者可区分，显示值与同一 files 响应一致，合法当前目标可复制给 reprocess，失效目标明确不可重试。

## 原七项发现的复核结果

| v1 项 | 本 HEAD 的源码与可核证据 | 本轮判定 |
|---|---|---|
| F1 缺失/不可读后的授权复活 | `_publish` 已按 document/source 撤销 missing 或未完整捕获错误的旧授权，并保留确已捕获的新失败 CID；管理上传补传 captured_id。正式 `execute-refresh-authorization-combined-v1` 两 TC 各2项通过，1713 原件 SHA 全相符，两个正式判断已登记 passed | **原两条具体复活路径已处理。** 不关闭最后授权在途取消、5秒槽位/树回收及其余生命周期；保留的取消 TC 停在准备，不能推断产品已经失败或通过 |
| F2 Hub refresh 长持 guard | `_refresh_native` 以 mutation_context 在开始/capture_metadata/发布短锁重核身份，raw I/O 和 worker 锁外。`green-hub-refresh-read-v1` 主1+回归48，890原件完整，独立 passed 登记 | **原已复现的跨 worker 读阻塞已处理。** 服务已运行时 CLI 仍直接调用所在 CLI 的 refresh/process，没有计划中的服务队列交接；写控制/晚到/大批发布锁延迟仍未验，不认领整个 F2/SC7 |
| F3 暂存无回收 | `reclaim_expired` 已有永久过期 fence、锁内回收独占 incoming，begin/put 触发；`green-transfer-expiry-raw-v2` 主2+回归23，487原件完整，独立 passed | **部分处理。** 已提交失效 canonical 候选 GC 仍有 V2-F3；成套 raw+results/direct put/故障并发/恢复 fence 未由 raw-only 专项证明 |
| F4 新存储未进恢复清单 | prepare_restore 纳入 `.document-snapshots`；Local 在尚无 sync 表但已有持久目录时也会纳入；排除 tasks/锁/当前 expired-transfers。`green-snapshot-restore-set-v1` 主5+回归67、141原件完整、独立 passed | **原目录遗漏已处理。** 实际传输/设备投影/网页载荷/活跃任务与受管服务的完整恢复仍缺；guard 新表覆盖另列待证风险，不冒称复活已复现 |
| F5 网页过滤处理错误 | 两端 nativeDetails 现在保留 error，失败管理上传保留合法 retry CID。`green-web-failure-diagnostic-v2` 主3+回归21、209原件完整、独立 passed | **原项目资料库错误字段遗漏已处理。** 8份失败资料全部重试值/成功重试未由该项证明；路径 Web 局部入口另有 V2-F5；发布阶段错误仍有 V2-F2 |
| F6 未支持对象伪空白 | 纯 `validate` 拒绝 text 严格为空且 declared excluded 非空的 Office 结果；创建端 Builder 也走此校验。`green-unsupported-object-empty-v1` 主5+回归18、210原件完整、独立 passed | **原严格无支持文字的对象场景已处理。** 不扩大到所有空白字符、所有对象/PDF扫描终态或 HTTP 畸形结果；v1 页眉扫描时序推测不成立，已按实际预读 XML 路径更正 |
| F7 Local CLI 旧格式帮助冲突 | refresh/read 文案已区分新旧大小、创建端依赖、提取文字及准确原件；公开实际4级 help 输出与既有10项回归 | **原局部冲突已处理。** 不因此认领完整发现性/跨OS安装；Hub 上层简短帮助仍主要靠 README/指南补全 |

## Intent 角色入口回放

本表是对当前说明、CLI定义、HTML及现有原始证据的回放；本次没有假称亲自重新操作一轮浏览器或 stdio。

| 角色/结果 | 当时可见的起点与逐跳依据 | 信息是否足够、具体影响 |
|---|---|---|
| 本机 CLI 使用者纳入并核 Word/Excel/PDF | README:61–67 明示开发中、三格式、创建端责任→TRIAL_GUIDE:153/157 独立 wheel[documents]→170–178 OCR status/configure/check→180–200 project create/projects/add/refresh/files/search/read/original | 项目/来源/ref和重试参数有取得途径；PATH/DIR要求绝对路径、R来自status。Local新帮助已消除2MiB冲突。未配置OCR仍可用原生格式；远端原件下载被 V2-F1 阻断，候选回收/失败终态见上 |
| 本机 Web 使用者选择/拖入及路径纳入 | 主导航“文档”→HTML:58 格式/创建端/默认不同步→60 资料库项目/选择器/拖放；来源配置→138–141 来源及文件状态；资料库行 nativeDetails→检索 reader→表格/原件 | 选择和拖放入口均可见，失败资料库可见保存错误与比较值。外部路径分支漏详情见 V2-F5。首次尚无资料时，OCR配置提示主要要经README/指南或之后展开资料详情，不夸大为所有用户无法开始 |
| Hub 维护者在 Hub 创建并处理资料 | README:50–59、61–67→007指南:102 的 HTTPS/凭据/同一 state-dir→008安装配置→Hub根连接卡取得token，项目→库→搜索/reader；路径走 Hub CLI | Hub根明确从维护者取得凭据，内存同源认证，不要求把token放URL。ID/KEY/HID/epoch来自当前状态。前景/服务账户 OCR 探测不可互代。直接Hub下载路径存在，Local绕行下载不足见 V2-F1；服务CLI交接未完成 |
| 使用者检索已同步项目/其他设备资料 | README:55–59、63→指南:118–148 的KEY/HID/generation及默认关闭/暂停/撤回→默认联合或Hub根→精确reference | 一层范围、创建端管理与原件一并同步说明可达。接收端纯索引实现存在；未授权不应外发仍须完整C1/E/H/X证明。仅Hub命中原件在Local入口失败，不以直接Hub成功代替 |
| Agent 读取明确依据 | README:146–156→仓库 smm-search Skill:58后→list sources/projects→search→read text/table/original-info | 三只读工具和参数来源、提取/OCR局限、失效引用、原件交认证CLI/API均明确；未新增写工具。Skill所建议的远端原件交Local CLI仍受 V2-F1 影响；不把元信息通过当字节下载通过 |
| 维护者复跑/恢复 | README:67 的SPEC/PLAN/证据及179验收入口→scripts/acceptance/README:3–32 实际普通回归、材料、组件及证据回收；指南:146/371→prepare-restore | 新增008复跑章节已处理v1所指缺入口。明确普通pytest/组件/独立安装/E/H/X各自边界，完整E/H/X探针仍未落齐。恢复一致集新增目录可达；真实恢复全矩阵仍不完整 |

OCR前置材料的局部缺口仍在 TRIAL_GUIDE:170–178：普通维护者被要求“预先部署完整Tesseract及语言数据”，却没有直接可达的受支持OS获取入口或如何取得/确认两个绝对路径的步骤。验收 README 已有开发用 material prepare，技术维护者有可用路径，但它不是普通用户指南里的明确跳转。建议补短链接/离线准备及 `--list-langs`/目录确认办法；这属于完成 B4/A11 发现性所需的说明补充，**不要求产品自动安装或运行时下载**。选哪种发行来源、是否发布预制包是规格未规定的实现/文档选择，交维护者决定，不另加无依据平台承诺。

## PLAN 对照

可选依赖、OOXML自实现、PDF guarded intermediate/本地OCR、监督、CID/AID、成套分块、只读接收、CLI/MCP/Web及独立Hub vendor模块总体落在PLAN的修改区域。拆出 transfers/processed_documents、OCR预处理与PSM、回收fence、mutation_context、状态标记及测试平台设施均有PLAN调整记录，没有因实施便利改动冻结SPEC；原生定义保存的SPEC SHA `e6ba46812b4083b20820278005bb3cb0d32764372d8c8ef8e23b2e638ddfea28` 与现文件完全一致。

仍未实施完整的计划不能改写为“验证待补”：活跃服务CLI任务交接缺少实际路由；失效已提交候选GC缺少回收；完整重启/取消/配置发布终态与协议资源矩阵尚有代码或证据缺口。PLAN拟定的 E/H/X 专用平台/service/exchange及逐SPEC汇总流程没有完整可执行交付，workflow仍主要是components。这些工作多数已在PLAN日志/pending限域说明，属于明确未完成，不应重新列成隐瞒的无说明偏差。

008验收 README 仍有一处陈旧环境表述：第7行写“不使用家庭ESXi”，而PLAN本轮日志和pending已记录11月26日重新授权。它不证明产品行为错误，建议统一当前执行边界，避免维护者按旧局部说明误判允许环境。Ubuntu22.04补充诊断仍不能替代PLAN的Ubuntu24.04格。

## SPEC 逐项与证据状态

“有专项”仅表示该范围有真实记录/独立意见，不表示整条 A 或本 HEAD 所有入口通过。

| 条件 | 可复核依据 | 当前不足/判定 |
|---|---|---|
| A1 入口/创建端 | 管理上传、权限/比较值代码；本轮双端 publication 原件；失败诊断专项 | 正常发布状态子域已证；旧上传列表/ID集合、完整创建端权限与E/H未齐，V2-F2/F5未满足 |
| A2 DOCX | 已有green-docx-v1、部件/嵌套/修订实现；新增冻结Office对象反例 | 有限定C1证据；V2-F4合并表头上下文；E/H各格全目标未完成 |
| A3 XLSX | 已有green-xlsx-v1、稀疏/隐藏/公式缓存/日期读取；Office对象正负控 | 有专项；完整当前三OS实际入口/H未完成，不由夹具跨行尾filter替代Windows业务 |
| A4 原生/混合PDF | native及mixed独立样本、逐页/几何/两网格代码与历史记录 | 有专项；复杂布局负例、完整安全路径与E/H仍缺 |
| A5 OCR | 真实受控扫描专项、macOS3.11安装业务、固定组件/语言/真值 | Windows材料准备不是实际文档业务；三OS/三服务完整质量、错误/权限/取消恢复未齐 |
| A6 同步直接索引 | processed接收模块不进入格式解析器；direct-index专项及零处理探针 | X六方向无处理依赖真实接收环境未齐；源端离线后Local原件路由有V2-F1 |
| A7 成套/并发 | managed-update-replay-c1正式专项、屏障/原件、publication本轮 | C1重启五项设计遗漏和Windows argv探针保留；V2-F2；完整恶意清单/并发/重启组合未齐 |
| A8 生命周期 | 首失败/替换重试、正式missing/unreadable授权、managed captured_id修复 | 两个原F1路径已处理；保留在途取消无实测结论；V2-F2/F3/F5，完整ready/partial/共享/资格矩阵未齐 |
| A9 查询/表格/原件 | table-read/preview/multiple-hits/CLI/HubCLI/MCP及空白原件各专项 | V2-F1、V2-F4明确缺陷；完整scope/network、各格式/路由/重启旧ref未齐 |
| A10 有界/隔离 | PDF安全、预约长度、staging/raw TTL各限定专项 | raw TTL不是失效已commit GC；V2-F3。完整边界/+1、资源树/异常/5秒终态以及各OS与服务监督未齐 |
| A11 兼容/发现 | README/指南/Skill/008验收入口；clean366931e macOS3.11正式安装；新增恢复一致集 | 当前HEAD最终独立安装/最低版本三格、旧档案/保护完整证明仍缺；V2-F1/F5及OCR前置指引 |
| A12 平台与证据 | 持久原生收据、原件/独立意见；平台设施 Mac11/Windows15/Ubuntu22.04补充15 scoped debug及独审登记 | 没有完整 E三格/H三格/X六方向和完整C1链；R008不能passed。保留不是SPEC豁免 |

## 本次直接核验的原始证据与限制

1. 对以下8个原生 result 的 artifact map **逐文件重新计算存储 SHA，共5299份，无缺失/不符**：正式授权1713、Hub refresh890、恢复141、网页失败209、Office对象210、raw TTL487、publication Local825/Hub824。对应原生独立 review result 均实际打开，target SHA与本轮目标一致，判断均为各自限定TC passed，不从公开summary反推登记成功。
2. 本轮 publication Local result SHA为 `7873ca16874566ed3163da3e356f01d2f1f79461b412c5023cd238a8230f4d5c`，Hub为 `186214ac8ddbd78721981220b0cda0708c835a8d93ee13ba19c00d60677b9cff`；两份 product bindings 与本 HEAD 实际文件全部相符。读取原 execution.exit_code和stdout，分别主1通过、相关8/2回归 exit0；这是同一设计按owner的两次真实执行，不是第三次联合执行。
3. 实际打开两份 trace ZIP：Local162成员、7395条trace事件，Hub161成员、7366条事件，CRC均正常、文本可读；实际查看 Local首次partial等待图与Hub首次partial已发布图，分别可见正确V/P0等待、V/P1/1部分完成及下载资格。没有在本次逐图重审96张PNG，全部图的内容级联合逐图结论来自既有独立报告，本次仅核其原件/摘要和抽看画面，不假称全部亲自看过。
4. 联合报告 `.acceptance-local/008/publication-boundary-20261126/joint-green-review-v3.json` 实算 SHA为 `572cba232814c27cecd597e29e339efe07c76a77f342bac273abbeb7f92313b9`。两份绿灯review的 `target_sha256` 分别准确绑定上面两份result。成功门覆盖 first、同CID新profile和replacement；它们没有提供配置变更后拒绝发布的终态证据，不能反驳V2-F2。
5. 历史Hub refresh/恢复/失败诊断/Office/TTL证据均有后续product绑定变化；这些记录保持其精确旧快照的 scoped效力，不能因为原件完整就整体授予6c65bc9全部功能passed。正式授权证据声明的产品绑定较窄且与现文件匹配，也不因此扩成完整生命周期。
6. Mac11/Windows15/Ubuntu22.04补充15的平台设施独审result确实已登记passed；Windows旧9项补回归的7过2探针失败、C1新候选1失败4通过、Windows字符串argv漏记的保留事项继续有效。没有将测试设施失败写成产品无处理，也没有建议改skip/xfail。未就绪C1草稿不在已提交可执行集合。
7. `.acceptance-local/008/pr43-checkpoint-6c65bc9/pr-before.json` 只是PR draft及CI排队时点元数据，三job当时QUEUED、没有conclusion。本次**没有验证该HEAD最终三OS CI结果**，不能称CIpassed。旧a505两个常规运行的Mac/Ubuntu449通过61跳过、Windows426通过60跳过24失败仍只属旧检查点；各轮失败/跳过、原UbuntuV0失败与后续已定位的观察器原因不互相抹除。

guard覆盖仍有待证风险：Hub guard表清单 `src/smm_hub/documents.py:70–87` 没有新增snapshot/config/attempt/upload/processed-stage表，recover:1022–1028也未覆盖全部新增持久状态。本次没有构造“仅008新增状态变化的前后备份、保护文件不回退”的反例，故不把旧引用/任务复活作为已复现缺陷；应在完整恢复/保护验收中按冻结SPEC证明其拒绝与明确恢复边界。目录清单遗漏修复不自动证明这一保护域。

当前可以继续按已确认规格修复和补证；V2-F1/F2/F3是具体产品缺口，V2-F4/F5是局部可观察行为缺口，E/H/X/C1与最终包/CI链是交付证据不足。三者分别处理。维护者明确保留的取消、C1五项及Windows字符串argv缺口仍保留，不能为了把此PR变绿而直接降要求或改成预期失败。
