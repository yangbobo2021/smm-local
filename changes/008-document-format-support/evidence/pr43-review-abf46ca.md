# PR #43 检查点独立只读复审：abf46ca

审查对象：基线 `d8894d429ebe0915e377513a637b5dfc0fc7ea1a` 至已提交 HEAD `abf46cab699f07214af07038b0ae5a22b1389a2d`；重点增量为 `092ab9d8be112481618ffe158a407103147d2ed0..abf46ca`。结论：**两条本轮具体修复在限定专项内可以关闭；PR 整体仍为 needs_revision，R008 未完成。** 本报告不批准合并、发布或升级日常安装。

本轮实际读取仓库 AGENTS.md、当前 PR Review Prompt、008 Intent/SPEC/PLAN、README、TRIAL_GUIDE、验收 README 和检索 Skill 的用户入口说明；检查完整改动清单、重点增量与相关调用链，并打开本轮原始执行、正文/表格/原件与原生独审记录。仅写本报告；没有运行 pytest、产品调用、浏览器或验收用例，没有修改产品、测试、规格、计划、native 或远端。以下“源码确定”是静态可达分支判断，“既有实测”是本次重新读取并核绑定的原始执行，不表示本轮重新实跑。

## 主要问题与依据

以下都是当前整体交付仍存在的可操作缺口；不是声称本轮 DocumentSearch 补丁新引入或隐瞒了它们。PLAN:278、290、302、307 和公开 pending 已分别限域；维护者保留的测试范围也不因此豁免 SPEC。

### F1 · P1 · 失效且已提交的未发布候选仍永久计入 256MiB 暂存

位置：`src/smm_local/document_snapshots.py:50–62,79,118–122`；`src/smm_local/document_transfers.py:59–89`；`src/smm_local/documents.py:258–283`；`src/smm_local/managed_documents.py:390–393`。

**源码确定，未新增满额实跑。** `_unpublished_bytes()` 遍历 canonical raw/results 的所有文件，扣除曾发布 ledger 后全部计费；`capture_metadata()` 替代 current_capture 只更新数据库。路径来源移除和资料库移除只删除来源、撤资格并清 FTS，没有回收失去最后用途的 canonical 未发布字节。`reclaim_expired()` 已正确实现未 commit 身份的到期 fence/预约释放/独占 incoming 删除，但明确保留 canonical，不能覆盖此分支。

触发：用户反复上传不同 SHA 的大文件，处理失败后移除，或用新候选替代从未发布的失败候选。旧 CID 已不能合法重试，raw/results 仍累计占用，最终使下一份合法资料因 256MiB 拒绝。等待 24 小时也不会释放这些 committed canonical 字节。现有删除/查询资格保护不等于容量恢复。

违反 SPEC B5:71 的“至多最新未发布候选及当前已发布原件、先拒资格再回收无其他用途字节”，以及 B9:136、A8/A10。建议补共享用途与活跃分配感知的可恢复 GC；验证替代/移除最后用途后新合法上传可准入，同时保留同 SHA 活跃共享、另一连续来源、合法失败候选、在途分配及当前原件。不得用 TTL 删除仍合法候选来掩盖此缺口。

### F2 · P1 · 路径 refresh 在配置变化导致发布拒绝时，缺少终态收敛

位置：`src/smm_local/documents.py:418–434,436–459,482`；`src/smm_local/document_snapshots.py:139–145,166–170`；`src/smm_local/document_processing.py:28–31`。

**源码确定，未运行保留的竞态/生命周期用例。** `refresh()` 先把来源持久置 `refreshing`，`_scan()` 完成真实处理后 attempt 已写为 ready/partial/empty-success。另一入口此时合法更新处理配置，`Snapshots.publish()` 会拒绝冻结 revision 的旧结果，符合禁止旧配置发布的要求；但 `_publish()` 调用不在失败收尾的 try/except 内。其事务回滚并向调用方抛错，来源仍停在 `refreshing`，当前 attempt 仍保留“提取成功但未发布”，detail 的 `publication_pending` 持续为真，来源没有保存此次发布拒绝原因。

影响：路径纳入用户看到 CLI/API 失败后，状态仍像在处理/等待发布；原来仅经该来源有效的旧引用也会因来源不是 ready/partial 而暂时不能读取，直到用户另行采取恢复动作。这里没有证据表明错误新结果已经发布或原件被混用；缺陷是失败终态与诊断不反映实际结束。现有 `documents files`/明确再次 refresh 是可用排查入口，不能代替准确终态。

SPEC 依据为 B4:53/59、B5:63–81、B7:103 及 A7/A8；B9:140 另要求监督终止/取消/失授权后的终态，本次不把未执行的 5 秒取消断言算成已失败。建议按来源批次与当前 CID/AID/冻结配置做 CAS 收尾，保留既定路径旧资格撤销语义，防止晚到失败覆盖新刷新或新尝试；对配置变更后的发布拒绝验证来源/attempt 均终态且原因可见、旧快照资格符合 B5、当前 retry_target 可用。此前 managed 上传及同步缓存 reprocess 的 `fail_current()` 修复不能扩成路径 refresh 已修。

### F3 · P2 · 后列窗口遗漏从左侧跨入的合并表头

位置：`src/smm_local/document_results.py:97–102,139–142`。

**源码确定；本轮未调用该函数或执行文档端到端测试。** 所选格与 headers 都只用锚点列 `c <= cell.column < ce` 过滤，不检查 `column_span` 是否与窗口相交。合法 DOCX 的 A1:N1 合并表头、M243 命中，其后列窗口可从第 5 列开始；表头锚点在第 1 列便被排除，尽管真实合并范围覆盖所选列。超额摘要 fallback 使用同样过滤。

影响限定为合并格跨入窗口的表格：用户能看到后半表数值，却拿不到文件已有的对应表头/上下文；普通未合并表头不由此推定失败。违反 SPEC B2:24–30、B8:111–115 和 A9。建议按真实合并跨度与窗口相交选入必要格，保留原锚点/跨度，唯一格计预算；验证锚点在窗口左侧、跨度跨入所选列的完整源表，表头可见、位置不变且额度正确，不复制主格值填充续格。

### F4 · P2 · 外部路径“文件状态”没有展示候选与重试比较值

位置：`src/smm_local/static/index.html:138–141`；已有字段 `src/smm_local/documents.py:299–316`；完整 `nativeDetails()` 仅在项目资料库使用，见 HTML:294–302、375。

**源码确定，未重新操作浏览器。** 用户从本机 Web“添加文档来源”纳入路径并刷新，再点“文件状态”，页面只输出 path、membership.status、内容 version 与 membership.error，丢弃 API 已返回的 published_snapshot/latest_attempt/retry_target 及处理状态。外部路径资料不会自动进入上传专属的 document_library 行，因此该局部入口无法复制指南要求的 CID/AID/V/P；缓存重处理失败时还可能只看到原 membership 的 ready，而不是最新 attempt 的失败。

影响是该 Web 路径的信息缺口和状态误读风险，**不是所有用户都没有重试入口**：CLI `documents files --source-id` 和同一 files API 仍能取得详情，来源仍可排除/移除。违反 SPEC B4:54/59、B5:63 及 A8/A11。建议在现有文件状态区展示 API 的详细状态和当前 retry_target，并指向创建端 CLI 显式重试；无须新增网页 OCR 配置或自动重试。验证真实路径首次失败及旧发布/新失败候选并存时，可见值与同一次 files 响应一致。

### F5 · P2 · 活跃服务的 CLI 内容任务交接仍未实现

位置：`src/smm_hub/hub_admin.py:435–445` → `src/smm_hub/document_cli.py:54–85` → `src/smm_hub/documents.py:323–343,353–370`。PLAN:75 明确“服务已运行时 CLI 采集后交同 state 服务 worker；独立 CLI 无服务才前景调度”。

**源码确定的计划未完成；没有声称本轮实测了 OS 服务。** 当前 dispatch 无活跃服务判断，直接构造同档案 `HubDocuments`；refresh/reprocess 直接调用本 CLI 进程的 `Snapshots.process()`。单槽和短 guard 可以防重及减少阻塞，却不会把任务执行身份变成已运行的 launchd/systemd/LocalService。服务账户与 CLI 账户对 OCR/数据/tmp 的权限不同，因而 CLI 成功不能证明 H1/H4 指定服务身份处理成功。

这是 PLAN 实施方案未落齐，已在 PLAN:278/302 公开承认；本轮没有发现未说明的新偏差。建议完成同 state 服务的合法已捕获任务交接和等待结果，再以实际服务及其 OCR 子进程身份验证；无服务时保留明确前景路径。不能由本轮 foreground 的路由专项关闭 H 矩阵，也不将此项误写成“Hub 自有资料完全不能处理”。

## 本轮关闭项及限制

### C1 · 纯 Hub 命中原件经 Local 路由下载的缺失分支已补齐

`document_search.py:419–441` 现在取得当前配置 Hub，比较 wrapper/内层材料与 HID，先用精确引用读取 original-info，再沿现有 `_request_binary()` 认证通道 POST `/documents/original`。`federation.py:66–90` 使用配置地址和 Bearer 头，并把二进制响应限制为 20MiB；下载后核 bytes、SHA 以及内层引用声明的原 SHA。

epoch/签名/连续资格仍由目标 Hub 校验：`smm_hub/documents.py:928–955,975–981`、`smm_local/documents.py:554–581`。本机没有把未验证的 routing metadata 当作读权限，也没有回源读取或解析分支。当前 epoch 不匹配在目标 `_context()` 拒绝；本地 `_hub_info()` 仅看身份不等于绕过目标校验。

同字节测试 `test_document_formats_remote_original.py:27–116` 对 Hub 自有/另一设备投影、普通/全局、DOCX/XLSX/原生 PDF 各两份共 24 目标，从 CLI search、Local HTTP search 和真实 stdio search 分别取得引用，核 original-info，再把同一引用交 CLI 导出及 Local HTTP 下载。原始记录有 72 个 verified-download，按三入口各 24；24 份保存的下载原件与对应冻结输入逐字相同。wrong Hub 的 24 个 HTTP 业务拒绝及相应 CLI 拒绝均有记录；测试明确源路径删除、源端停止后再查询。

因此原 V2-F1 的“Local 无远端 original 实现”已关闭。限制：这是 Mac 前景源码 CLI/HTTP 与 stdio 引用交接，未执行实际浏览器下载、独立安装包业务、真实 HTTPS、其他 OS 或系统服务。本轮新用例未分别注入错误二进制长度/SHA、换 epoch 和资格撤销；这些拒绝机制是源码核对，不冒称本次新专项实际跑过所有负例。

### C2 · 不同处理版本误合并和旧 mixed bundle 跨快照回退已处理

`document_search.py:22–26` 将 P 纳入 identity；`:171–184` 对新格式要求合法 P/resultSHA 并与 Hub 引用一致；`:249–257` 在同 identity/V/P 内比较 resultSHA（及原件/文本摘要），冲突排除并标 Hub partial。不是把 resultSHA 加入 key 后把冲突伪装成两个合法版本。

`:317–355` 在 bundle 真正读取前，递归拒绝不同 archive/document/V/P/result/raw 快照混用；`:373–381,412–418` 随后仍由实际目的端核签名/资格，只在同处理快照的副本间回退。该 precheck 不联网，故 Local 有效的同版 bundle 不因为 Hub 离线而先被探测阻断。旧文本缺两项新处理字段时保留 legacy 路径。实际远端可读能力依旧由 `read()` / Hub 校验，不能只凭未认证内层声明放行字节。

同版专项实测前置是四份普通/全局 DOCX：origin/V/rawSHA/textSHA/text_length 相同，Local P2 与 Hub P1、resultSHA 不同。四份原始 preconditions 已重新核对。CLI/HTTP 默认联合结果分别保留两条未 bundle 的快照；text/table/original-info/original 都按自己的 P 读取，旧 mixed 引用对 text/table/info/original 拒绝后，合法两端引用仍可读。另有同 P 镜像 dedup、12 个同 P 异 result/命中与引用不符的负控，以及 legacy 文本 bundle 读取。

本次独立解析保存的 CLI/HTTP 响应，在四个目标的 292 个响应中重新核 V/P/rawSHA/resultSHA/profile，52 个全文重新核长度、实际文本 SHA、独立源 words/exclusions，192 个表响应重新核独立源完整格集合/跨度/位置；均无不符。12 个协议负控实际均 Hub partial 且只保留 1 个本机正确结果，四个目标均有完成记录。

因此处理版本补充意见所述两条具体联合分支已关闭。限制：同 P 异 result、hit/ref 元字段错误是显式构造的协议负控；真实业务双端差异分支由创建端合法重处理产生。不能把二者统称全为真实服务自然冲突；不扩大为所有 scope、断网、共享资格/重启、三格式处理版本交叉及 E/H/X 已验。

### 其他既有修复的本次定位

旧 V2-F2 在 managed 上传及同步缓存 reprocess 的发布失败子域已有 `Snapshots.fail_current()` CAS，且 `documents.py:319–326`、`HubDocuments.reprocess():338–350` 与 `managed_document_uploads.py:214–224` 都调用；不能继续笼统写成“这些入口仍无失败终态”。其四份绿灯/正常 publication 重验属于前一检查点材料，本次未重新逐份核这 15,884 份原件，故不重授整域通过；剩余路径 refresh 另见 F2。

本次同样不沿用旧意见中已被后续说明消除的文档问题：TRIAL_GUIDE:172 已给出材料准备入口、清单中的两个绝对路径和 list-langs/check；验收 README:7 已明确 11 月 26 日当前测试环境授权。没有据旧稿重复报告这两项为当前缺陷。

## 计划与实际修改核对

最近增量 24 个文件中，产品只改 `src/smm_local/document_search.py`；新增两个主测试、remote fixture/observer，更新 PLAN/公开证据和原生设计/复审投影。PLAN:77 本来要求 P/双摘要去重与精确路由，新增调整记录在 :307 说明实际方法、TDD 修订历史、磁盘准备失败、各专项边界。SPEC 未改，当前 SHA 为 `e6ba46812b4083b20820278005bb3cb0d32764372d8c8ef8e23b2e638ddfea28`，未由计划降级行为。

专用 observer 与既有共享 restart_server 的 Windows 字符串 argv 审计逻辑分离；本增量没有修改那个被保留的逻辑。F1/F2/F5 及完整 E/H/X 探针/最终门仍属计划未完成，不改写成仅剩文案或普通回归待补。当前三份未跟踪 `.py` 草稿未计入已提交交付、绑定或可执行用例；已提交 `.py.txt` 仅是历史证据。

## Intent 角色与入口回放

下表是本次沿当前文档、命令定义与 HTML 进行的可发现性回放，引用既有原始入口调用佐证适用动作；不是本次重新操作浏览器/stdio。

| 角色及结果 | 可见起点、下一跳与所需值来源 | 判断及局限 |
|---|---|---|
| 本机使用者按项目纳入三格式并核原件 | README:61–67 明示开发中/正式 0.4.0 不含能力 → TRIAL_GUIDE:153–168 独立同构建 wheel 与 `[documents]` → :170–180 材料准备、清单中的程序/数据绝对路径、status revision → :188–200 project/add/refresh/files/search/reference/read/original-output | 能发现支持范围、安装及参数来源；不必猜 ID、ref 或 OCR PATH。远端下载实现已补。当前外部路径失败详情与发布拒绝仍受 F2/F4 影响；实际三 OS 完整安装/入口未证。 |
| Web 使用者选择/拖入或纳入路径并看真实状态 | README:65 → 指南:184–186、212–216 → Local HTML:58–65 的格式/创建端说明、项目、选择器/拖放、来源配置、检索和 reader；库行 :375 使用 nativeDetails | 正常使用入口清楚，状态与“收到不等于可检索”已说明；路径“文件状态”局部信息不足见 F4。没有把指南存在误当作实际 UI 全部可完成。 |
| Hub 维护者创建项目、准备处理环境 | README:50–59/61–67 → 007 指南的 HTTPS、hub-token、实际 state-dir → 008 指南:168/180 的 Hub 前缀 → Hub HTML:6–11 的凭据选择、项目、只读/自有库与搜索 | 凭据从维护者取得并仅内存认证，项目/管理端及状态目录含义可见。不能以交互账户 check 代替服务身份；服务 CLI 交接仍有 F5。 |
| 检索已同步/其他设备资料的使用者 | README:55–59 与指南:118–148 的 KEY/HID/generation 选择、默认关闭、暂停/撤回 → 默认联合/Hub 根 → 每条精确 reference | 来源和一层范围说明可达；本轮 24 远端资料证明 Local 原件路由专项，未把 all-scope 专项等同项目根/一层/离线 fallback 全矩阵。 |
| Agent 读取可核出处 | README Agent 接入 → `skills/smm-search/SKILL.md:58–72` → list projects/sources → search → read text/table/original-info → 同一 ref 交认证 CLI/API | 三只读工具、行列参数及处理/OCR局限明确；MCP 不写文件、不返原件 base64。实际 stdio 元信息/同 ref 下载已见本轮原件；版本隔离未在 stdio 上单独重跑。 |
| 维护者复跑和判断交付 | README:67 的 SPEC/PLAN/证据、规约验收入口 → scripts/acceptance/README:3–32 的普通回归/材料准备/组件/独立包/E/H/X/回收说明 → pending 索引 | 已有复跑命令和所需值来源，明确没有一条命令完成整体验收。公开结果未把基础组件和普通 CI 等同 E/H/X；未就绪专用平台流程仍是交付不足。 |

## SPEC 逐项判定

本表逐 A 条给出当前可见依据及尚不能通过的原因；“存在专项”不等于本次重验所有历史原件，更不等于该 A 整项 passed。

| 条件 | 当前可核依据 | 本轮可给结论 |
|---|---|---|
| A1 入口/创建端 | README/指南/Web/CLI 入口，创建端与投影校验；公开管理专项 | 限定路径有实现/历史证据；F2/F4、完整旧页/权限及 E/H 未齐，整项未完成。 |
| A2 DOCX | Word 部件/嵌套/跨度实现与历史 docx 专项；本轮四 DOCX 独立全表复核 | 路由/版本目标读回正确；F3 及完整 E/H 各目标仍未满足。 |
| A3 XLSX | 稀疏多表、隐藏/缓存/类型实现和既有专项；本轮远端原件含 XLSX | 不由原件下载推出完整格式行为；当前三平台入口/H 未齐。 |
| A4 原生/混合 PDF | PDF native/mixed 模块及既有专项；本轮 8 份远端 native PDF 原件 | 新下载路径受证；布局负例、完整资源和 E/H 未由此关闭。 |
| A5 OCR | 冻结 OCR/runtime/质量专项和 macOS 最低版历史安装记录 | 本轮主要 DOCX/XLSX/native PDF，没有新 OCR 质量实跑；三 OS/服务质量、错误/取消恢复未齐。 |
| A6 直接索引 | processed 接收实现；本轮另一设备 12 资料投影，源路径删除/源端停止后下载 | 该只读后续子域有证；不替代 X 六方向实际无依赖环境与完整禁止者/partial 矩阵。 |
| A7 成套/并发 | 成套协议/重放/配置终态等既有专项；本轮同版精确读 | F2、保留 C1 重启五项及完整并发/坏清单/恢复仍在；未判整项通过。 |
| A8 生命周期 | 既有缺失/不可读授权、首次/替换重试、managed 收尾；本轮 P1/P2 合法差异 | F1/F2/F4及共享/最后授权/取消全矩阵未齐；保留用例未到达的取消断言不判产品通过或失败。 |
| A9 查询和原件 | 本轮两项 green、原始全文/表格/原件、同版绑定/独审；table/CLI/MCP 历史专项 | 两具体缺陷关闭；F3、scope/network 全矩阵、实际 Web/重启旧 ref、平台分工未齐。 |
| A10 有界/隔离 | PDF guard/监督/预约/staging/TTL 既有专项；新查询 guard 控制 | F1、完整限额/+1/任务树/5 秒槽位/各平台服务仍缺；guard 自检或所有 artifact 完整不等于资源功能通过。 |
| A11 兼容/发现 | 当前入口链、legacy bundle 正控；双 wheel 构建摘要及历史 macOS 3.11 安装 | 本轮新源码构建核验不等于已安装业务。F4、最终 HEAD 的最低版本三平台/兼容/恢复证据未齐。 |
| A12 平台/证据 | 持久 native、公开限域、原生独审与当前源码绑定 | E 三格/H 三格/X 六方向和完整 C1、最终提交 CI/安装链不足；R008 未通过。 |

## 本次实际证据核验

1. 逐文件重新计算两份 green 的 artifact SHA：原件路由 1,261 份/4,479,209 字节；版本隔离 896 份/4,196,212 字节；均无缺失或不符。各 91 个 bindings 均与现盘相符；各 62 个 product_bindings 及 27/26 个 test_bindings 又与 `git show HEAD:<path>` 逐项相符，未混入未提交文件。
2. 原件路由 result SHA `a28b987e9bda25971a78a9a845dbcbd85e7251688e4238481d591ba4a5abcbee`；版本隔离 result SHA `2616195b6c6ee6b5d6a51f409f75e1806db60b2b9059f8621c8e15013b9985db`。原始 run/regression stdout 及 exit0 分别是主 1 通过/99.18s、相关 12 通过/34.89s；主 1 通过/72.90s、相关 34 通过/213.82s。相关组是记录中的实际文件集合，不称全量回归。
3. 原生 `review-remote-original-green-v1/result.json` SHA `f0ee359bce39b49237f3294abc244eb0b9c164efe538d50c44eff1941862d61c`；`review-version-isolation-green-v1/result.json` SHA `9875eec10a16308b4fa2267dfaa8449a67b66d2b09c52dc847cd21d034dccad2`。两份 target SHA 精确指向上述 green，各自 TC judgments.status=passed；各自两份 artifact 及 91 个 bindings 完整。它们不是 SC9/A9/R008 全域 passed。
4. 红灯 `red-sc9-remote-original-v2` SHA `77b622207eea94e2d804398f64a096a6bbe01032260c4994b3e1fbaa7d9649c5`，原 stdout 在真实 CLI 导出报旧产品“远端原件接收能力尚不可用”；`red-sc9-version-isolation-v4` SHA `f6b2a68d04b37287cc00d11c399b5a9e28ca504e669bac426ee984240f409b57`，原 stdout 为联合结果 1 != 2。对应 green 的全部 test_bindings 与各自红灯一致。v3 的磁盘 I/O 准备失败保留为 insufficient_evidence，不以环境失败冒充功能红灯。
5. 本次除核哈希，还实际解析远端路由事件（72 下载/48 stdio 调用/24 wrong-Hub 记录）、24 冻结输入与保存下载字节、四份版本前置、12 协议负控，以及上述 52 全文/192 表格。服务/CLI/controller guard 代码有实际正负控与最终日志基线比较，吞掉禁用异常仍会因新增日志事件不等而失败；限定允许配置 Hub 通信。没有把测试探针当产品行为，也没有把 checksum 完整当功能全通过。
6. `remote-query-routing-development.json` 的 product SHA `185b4486513f863607c336139970b8f8d51e8359541cdd5f845cf5463a6b4ff3` 与已提交模块、green 绑定相同；公开文件的两 result/review SHA、文档数量和专项通过范围与原件相符。build 部分明确仅构建/源码字节核验；本次没有重新构建、安装或打开 wheel 全成员验证，因此不额外授予包业务通过。
7. 092ab9d 的普通 CI 属较早检查点；公开记录为两次各 Mac/Ubuntu 458 passed/67 skipped、Windows 457 passed/66 skipped/2 retained failures。本次没有重新下载/逐 ZIP 复核其六份 artifact，也未把这些旧结果套到 abf46ca。abf46ca 的最终 CI 未在本轮取得结果，保持未验证；普通 skip 不能算 OCR/浏览器/配置终态通过。
8. 来源取消、C1 重启五项和共享 Windows 字符串 argv 修订继续按维护者决定保留：不执行、不改 skip/xfail、不把保留写成 SPEC 豁免。三个未跟踪草稿仅在 status 看见，未用于审查绑定或当作可执行交付。审查前后 HEAD 均为 abf46ca，已跟踪交付文件没有盘上 diff。

## 结论

本轮 DocumentSearch 补丁对纯 Hub original 路由及处理版本隔离的具体修复是成立的：源码行为与限定同版原始证据一致，未发现需要单独新增的可确认回归。两份 scoped passed 可保留，旧意见相应两条应标“本轮限定关闭”。

当前 PR 仍 **needs_revision / R008 未完成**：F1–F4 是当前可观察行为缺口，F5 是明确未实施的计划方案，完整 C1/E/H/X、最终 HEAD CI/最低版本安装/独立交付链也不足。它们应分别修复或补证；不得由本次两个 green、原件 SHA 完整、前景服务自检或旧 CI 推出整 SPEC 通过。PR 继续 draft；本报告没有向 PR 发消息、没有登记 native、没有合并或发布动作。
