# PR #43 独立审查 v1

审查结论：**需要修改，当前不满足合并/交付条件。** 草稿身份不改变此结论。已确认的产品问题包括失效采集授权可经缓存重试恢复、Hub refresh 跨解析持全局控制锁、暂存容量无回收路径、恢复清单遗漏新增快照目录，以及网页失败诊断和空白状态不符合规格。PR body 对未完成验收的表述基本审慎，没有把当前专项通过冒称 R008 通过。

## 审查对象与方法

- 仓库：yangbobo2021/smm-local，草稿 PR https://github.com/yangbobo2021/smm-local/pull/43 。实际读取当前 PR body、draft 状态及 headRefOid。
- 实际 `git rev-parse HEAD`：`366931e78a72f55d5bbfeb28e3193997e5ab75f5`；PR head 一致。比较基线：`d8894d429ebe0915e377513a637b5dfc0fc7ea1a`。开始审查时 `git status --short` 为空。
- 已读仓库 AGENTS.md、实际 `changes/_templates/pr-review.prompt.md`、008 intent/spec/plan、README/TRIAL_GUIDE、CLI/MCP/两端 Web 入口及相关实现。定义为 `.acceptance/native-v1/AT-SMM-008/definitions/000001.json`，覆盖 SC1–SC12；本意见是 PR 审查，不是原生 TC 绿灯或需求级 covers 判定。
- 只读源码/原始证据，不重跑长测试，不注册服务、不操作日常档案、不调用业务写接口。以下“源码确认”是可追踪的静态调用链，**没有声称本次实际执行了故障复现**。本次唯一写入是本意见文件。
- `pending-verification.json:3` 的 snapshot 是 `4906918d8f1f854da48d4eee21109819781d287c`，其汇总不能直接当成本次 HEAD 的执行回执。各结论另核原生记录、实际字节及适用版本。

## 已确认发现

### F1 · P1 · 明确违反 B5/A8：目录刷新确认文件缺失后仍允许缓存重处理恢复来源资格

位置：`src/smm_local/documents.py:455–457`；关联 `documents.py:258–262,318–337`、`document_snapshots.py:89–90,136–150,152–161`。

源码路径：目录来源中一份已采集新格式文件被删除，本轮目录枚举正常完成且其他文件仍存在时，`_publish` 对未见成员只把 membership 改为 missing；对文件单项读取失败也只把 membership 改 failed。两处都没有撤销对应 `document_capture_authorizations.active`。`_prune` 仅清正文/FTS，不撤采集授权。`authorized` 仅检查 active、来源存在和 revision；来源 revision 未变，所以 `detail` 仍能产生 retry_target。之后 `reprocess` 不回源，`_publish_reprocess` 将这些授权来源的 missing/failed membership 改 ready，并把来源改回 ready/partial。

这不是网页替换失败保留旧发布的合法情形：B5:71、79 明确要求后续 refresh 确认缺失/不可读后撤销该来源采集授权，不能以旧缓存 reprocess 复活。影响 Local 及复用同实现的 Hub 创建端，用户可能重新得到已明确退出该来源的资料。**限定**：整源失败已有 `documents.py:430` 的 active=0；这里报告的是整源正常/部分完成时的单成员缺失/不可读分支，不泛称所有删除均无保护。

建议：在单成员被确认缺失/不可读时原子撤销该来源对应采集授权，保留其他连续有效来源；同事务让重试目标和任务资格及时反映。验证条件：同目录至少两个目标与负控，删除其一→refresh→该来源 retry_target 不可用/旧重试拒绝，正文/原件不能恢复；再加重叠来源证明另一原有连续授权仍可支持同一快照，最后授权失效后终止在途任务。

### F2 · P1 · 明确违反 B9/A10 及 PLAN：Hub 路径 refresh 持全局文档锁直至解析/OCR完成

位置：`src/smm_hub/documents.py:343–369`；读取竞争方 `documents.py:844–846,907–909,954–956`；处理调用 `src/smm_local/documents.py:395–398`。

`native` 在 `guard.hold()` 内执行 `self.documents.refresh`，后者同步采集并进入 `snapshots.process`/受监督 worker。一次 OCR/解析可持续到总预算 300 秒。Hub search/read/original 和来源/控制操作也使用同一 guard lock，因此它们必须等待该 refresh 释放锁。即使仅刷新一份新格式，另一个已有有效文档的读取也会等待。现有 `reprocess` 已将解析移出锁（Hub `documents.py:335–338`），路径 refresh 没有同样处理。

B9 要求状态、控制、检索和旧有效原件读取不等待内容处理；PLAN“修改位置与数据流”还明确约定处理不持 DB/控制锁，并由已运行创建端服务处理队列。该分支仍是 CLI 自己同步处理，也未见已运行服务的交接路径。此处既是可确认产品阻塞，也是尚未记录为实施调整的方案缺口。

建议：短锁冻结授权/来源/CID/顺序，锁外处理，短锁核比较值并发布；服务存在时按计划交队列，不用简单移锁丢失原子性。验证条件：真实 Hub 路径 refresh 屏障暂停在解析/OCR中，同时完成另一资料 search/read/原件、状态、暂停/移除；旧任务晚到不能发布，解除屏障后状态正确。

### F3 · P2 · 明确违反 B5/B9：过期传输和失效未发布字节没有可达回收路径

位置：`src/smm_local/document_transfers.py:14–57,71–86,128–143`；关联 `document_snapshots.py:49–61,108–117`、`documents.py:258–281`。

24小时仅在 `_load` 中使未commit传输报“已过期”；`reservations` 枚举所有 state.json 并继续计入承诺长度，不检查 created_at/committed，也不删除过期预约。新 begin 继续按这份总量准入。源码中没有清理 transfer 目录的调度/管理入口；唯一删除 state 的分支是本次 begin 失败回滚。于是累计预约达到256MiB后，等待24小时仍无法重新开始新传输，旧传输又已被拒绝，不能自行恢复。

此外新候选替代、来源移除/失效时没有 snapshot 字节 GC：`_unpublished_bytes` 继续统计未发布 raw/results；`_prune` 仅清正文。因此已无重试用途的候选也可能持续挤占容量。B5 要求每份只保留一个最新候选，失效后先拒资格再回收无其他用途字节；B9 区分24小时未commit与不应TTL删除的已commit合法候选。当前专项 reservation-lengths 仅证明准入保守计费，原独立意见也明确不证明TTL/共享GC。

建议：在容量锁下提供可达、可恢复的回收流程，按所有共享引用/传输/当前候选/发布状态判活；不要仅在计费时跳过过期项而遗留共享 incoming，也不要将已commit合法失败候选按TTL删掉。验证条件：满容量未commit预约老化后新有效文档可传；仍活跃的同SHA共享上传可续传；替代/移除最后候选回收正确，当前失败候选及当前发布原件仍逐字可读。

### F4 · P1 · 恢复用户路径的产品集成缺陷：备份/恢复清单未包含新增原件和结果库

位置：`src/smm_local/document_protocol.py:161–177`；新存储根 `document_snapshots.py:23`；用户说明 `TRIAL_GUIDE.md:146,371`。调用方：Local `upload.py:529–539`，Hub `hub_admin.py:370–371`。

`prepare_restore` 的 restore_files 仍只补 `.documents`，但008完整原件与规范结果实际在数据库旁 `.document-snapshots/raw`、`results` 等位置。指南明确让用户备份 DB + `.documents` 的一致集，并按 restore_files 恢复。在新机器/空目录按此集恢复，数据库保留 published snapshot 的摘要和ID，却没有所指 blob；结果读取和原件下载无法完成。对同步投影，`.documents` 本来就不含这些原件；不能用回源重处理替代接收端保存结果的恢复。

这延续了公开恢复入口的“完整副本目录”承诺，并触及 SPEC 边界“不改变归档恢复保护”和 A11兼容。未实测恢复，但存储/清单/读取依赖的路径是确定的。**不声称当前已实际丢失用户数据**。

建议：将新增快照目录、需要保留/恢复的任务及配置状态纳入一致性备份/恢复契约，明确保护文件排除项并更新指南；恢复后不得自动重授权或重处理投影。验证条件：包含 Hub自有、Local路径、网页资料及设备投影的008独立档案，按公开清单在新空目录恢复；原始字节、完整表格/结果、配置和保护恢复流程均可核，缺失目录的负控明确失败。

### F5 · P2 · 明确违反 B3/B7：网页失败详情过滤掉实际错误原因

位置：Local `src/smm_local/static/index.html:298–302`，Hub `src/smm_hub/static/index.html:36–40`；错误已在后端提供：`document_snapshots.py:147`；状态轮询 Local `index.html:348–350`、Hub对应 trackNativeUploads。

两端 `nativeDetails` 将 latest_attempt 缩成 capture_id/attempt_id/status/config_revision，明确丢掉 error。资料列表没有其他错误输出，上传/更新轮询仅给 failed、版本和ID。缺OCR引擎/语言、权限、坏文件或监督超限等首次失败资料无法搜索，用户也无法转到搜索reader看原因；详情只有失败和比较值，不能判断要补什么前提。后端 files/library 的 latest_attempt.error 已存在，CLI完整JSON仍是可用的绕行路径。

建议：在网页安全显示实际错误、缺失组件及适用覆盖/重试提示，保持不泄露凭据/不执行文本；在尚无任何资料时也放可见的OCR准备指引。验证条件：两端从网页上传真实缺语言/损坏文件，失败行详情分别给出可区分原因；配置恢复后使用当前CID/AID重试，旧发布/失败候选能分别辨认。

### F6 · P2 · 明确违反 B7：只有未支持对象的 Word 可被标成空白成功

位置：`src/smm_local/document_results.py:37–39`；调用 `document_formats/word.py:13–23,87–89`。

Builder.finish 在 text 为空时无条件选择 empty-success，没有检查 coverage.excluded 或未支持对象。Word解析器会记录 drawing/object 等排除项，跳过其内容，最后仍无条件 finish。因此合法仅含插图/嵌入对象而无普通文字的DOCX，会得到 empty-success 和部件ready。B7明确规定空内容成功只用于真正空白且完成支持范围检查，只有未支持对象的文件不能伪装空白成功。此次没有运行此文件；结论来自该输入类型的确定分支。

建议：由创建端根据支持范围与已发现排除内容显式决定状态，不能仅以文本长度决定空白；无可用支持内容时报告具体不可用原因。验证条件：真正空白DOCX维持empty-success；分别含图片、嵌入对象且没有正文的合法DOCX不得标空白成功；带正文加排除图片的文件仍保留正文及明确excluded，不要求新增图像理解。

### F7 · P2 · 明确违反 B8 的局部使用说明：refresh帮助仍把所有新格式说成2MiB文本

位置：`src/smm_local/cli.py:157`，关联 `cli.py:168`。

documents 上层帮助已列 .docx/.xlsx/.pdf 和处理依赖，但用户继续到 refresh --help，只得到“每文件2MiB、每来源…16MiB”，没有说明这是旧文本边界；read描述仍将“仅去BOM/换LF，其他原样”用于所有格式。008实际需要区分20MiB原件、提取文本/结果与原字节。使用CLI逐层找操作的用户会误以为合法大于2MiB Word/PDF不被支持，或误读提取文字等同源文本。README→008指南给出正确边界，是可达替代路径；此项是局部冲突和增加使用难度，不是所有用户被阻断。

建议：在已有帮助说明中限定旧文本规则，补新格式准入、创建端处理和提取文字语义，并指向指南/状态命令。验证条件：从顶层help→documents→refresh/read，用户可确定三格式大小、依赖、取值来源和原件核对方式，无互相冲突的信息；不需要新增命令。

## 按 Intent 的用户角色回放

下表为本次从实际主入口开始的静态回放；不把阅读HTML/命令定义说成本次浏览器操作。历史真实浏览器证据另列在后面。

| 角色与结果 | 实际可见起点→跳转 | 所需前提、操作与确认 | 判定 |
|---|---|---|---|
| 本机使用者通过CLI纳入并核对Word/Excel/PDF | README:61–67明确008对象/未发布→008指南:153→安装:157→状态/配置:172→项目/来源/refresh:186→search/read/table/original | 独立wheel及[documents]、独立DB；项目ID从projects，source ID从add；REF/table_id/重试比较值从各返回取得；原件输出须新路径，窗口端点解释可用 | 主线可发现，输入来源大体充分。F1/F3/F4/F7使生命周期、恢复或局部帮助不完整；全局项目沿README/007/CLI ensure-global有可用入口，不要求重复创建专用项目 |
| 本机Web使用者选择/拖入、观察状态、读取及管理资料 | 主导航文档（Local HTML:58–65）→项目创建→资料库选择器/拖放→状态与详情→搜索→reader动态控件/原件下载；README:65和指南:182–219说明相同路径 | 文档页可见格式、默认不同步、源文件不改写；项目/ID由列表取得；更新同格式、移除绑当前比较值；真实旧空白资料有原件按钮 | 初次上传“成功前提”中OCR配置指引只藏在已有新格式资料详情，且F5缺错误。表格/原件控件实现存在；完整初次上传及A正文/深表的当前浏览器验收仍未完成，不能据空白下载专项通过宣称整条路径实测通过 |
| Hub维护者创建和处理自有资料 | README:50–59/61–67→007指南:102取得HTTPS/凭据/同一state-dir→008安装/配置→Hub根网页认证/创建项目/上传；路径来源走Hub CLI | 凭据来源/存放内存、Hub身份/epoch来源清晰；实际服务目录从已有部署取得。创建端配置需本机维护者权限，不交给浏览器传程序路径 | 有可达主线；F2直接阻断并行读取/控制，F3/F4/F5仍适用。H真实身份/权限/重启未完成。Hub CLI documents上层仅“管理Hub自有文档…”，并未像Local层介绍格式/依赖，发现性还可补强 |
| 检索Hub投影/跨端资料的使用者 | README:55–59/63→指南:118–148、224→默认联合范围/Hub根→各条REF读回 | 同步默认关闭，KEY/HID/generation从sync-status；投影只读且回创建端管理；原件/结果一起同步，Hub无处理依赖也可接收 | 源码 direct-index分支不导入处理器；有历史专项证据。全X六方向、暂停/共享/撤回完整状态和当前HEAD真实入口证据缺失，不能判端到端完成 |
| Agent读取明确依据 | README:35/146–156→仓库smm-search Skill:58–74；MCP工具描述 mcp_server.py:73–86 | sources覆盖→实际项目身份→search引用→read text/table/original-info。Skill说明窗口参数、失败非无内容、创建端责任、只读边界；原件交认证CLI/API | 可发现且输入来源明确。MCP描述/Skill/代码未增加写工具。本次没有重新启动真实stdio；已有专项仅Local Word，不能推广成三格式/跨Hub/三OS完成 |
| 维护者验收/恢复 | README:67→SPEC/PLAN/证据目录；README:179→验收说明；指南:146/371→prepare-restore | PLAN有详细E/H/X/证据规则，pending能看到未完成项；验收README没有008复跑章节，新增workflow也只有components | 状态可发现但尚未形成计划承诺的完整008可复跑入口；恢复清单确有F4。该缺口没有被当前普通CI或build代替 |

### 尚未完整覆盖的前置条件路径（适度补充建议）

TRIAL_GUIDE:170要求“预先部署完整Tesseract5及eng/chi_sim”，174再要求两个绝对路径，但README/指南没有指向支持OS的组件/语言数据取得方法、已验证离线材料位置或判断正确数据目录的步骤。懂Tesseract且已部署的维护者能继续，首次配置者从SMM主入口走到这里仍需自行外查；PLAN的研究记录不能直接当用户安装说明。规格B4要求独立安装/OCR准备可发现，但没有规定必须由哪种系统包管理器安装，因此不建议扩成产品自动安装功能。建议加一个可达的“取得/检查本地OCR和语言数据”说明，给支持OS适用获取入口和 `--list-langs`/目录确认方法；通过条件是新维护者可取得两个绝对路径，check识别两语言且身份明确。是否纳入本次交付由维护者决定，但A11完整路径判通过前应解决或明确已有替代指南。

## PLAN 对照与未说明/未完成部分

1. 新模块、可选依赖、Hub自命名空间vendor、结果协议、分块上传/更新、CLI/MCP/Web、解析/OCR/监督基本落在计划列出的区域。`word/spreadsheet` 自行读取OOXML符合既定方案；PDF guard→私有中间材料→渲染、OCR不同PSM及预处理调整已在PLAN:49以后记录；后续路径保护/回执/网页/预约等调整在PLAN:231–264解释了原因和限定证据，不是无说明新增范围。
2. F2 的路径refresh持锁与“无长控制锁、已运行服务接收CLI任务”约定不符，未见对应调整说明。未因分项reprocess已锁外就认领所有创建入口均满足计划。
3. 快照/传输GC、旧档案/恢复保护、取消/崩溃/共享授权仍是尚未实现完整的计划工作，F1/F3/F4已给具体源码缺口。guard审查还见下述待证风险，不把“剩余测试”一词掩盖确定代码缺陷。
4. PLAN列明修改 `scripts/acceptance/README.md`，当前diff未改该文件，文件内容无008章节；`.github/workflows/document-formats-acceptance.yml:15,23–40`仅components矩阵，没有已实现E/H/X业务编排。与pending所列“E/H/X未完成”一致，应保持未完成而非未经说明宣称方案全部实施。
5. 当前HEAD全回归/干净构建/最低Python最终门及各平台实际业务尚没有这份PR内可复核的完成链。两包早先构建/安装与常规CI只能在原记录范围引用，不替代实施顺序第7–9步。

## SPEC逐项与证据复核

“有专项证据”表示看到对应记录及范围，不表示本次重跑或整个A条通过。私有路径均以本工作树为根。

| 条件 | 现有可引用依据 | 当前判定/不足 |
|---|---|---|
| A1 入口/创建端 | managed-upload/native-management专项；两端HTML和CLI管理入口，默认同步关闭 | 部分实现/部分证明；F5，SC1网页第二轮旧资料状态/ID全集保留缺口，E/H未完成。不能A1全过 |
| A2 DOCX | 原生 `tdd-green/green-docx-v1/result.json` main/regression exit0，word.py部件/嵌套/跨度路径 | 历史C1专项可引用；F6空白分类反例未覆盖；当前三OS/E/H完整证明缺失 |
| A3 XLSX | `green-xlsx-v1` main/regression exit0；spreadsheet.py稀疏单元/hidden/日期/公式缓存 | 有专项；每格式全部当前实际入口和平台要求未完成，不能由一个开发格认领全部 |
| A4 PDF native/混合 | `green-pdf-native-v2` exit0，v1失败保留；mixed-pdf-development限定两份三页/6表等 | 有专项；复杂布局负例/完整PDF资源安全及当前E/H未完，不假称所有原生/混合PDF验证完毕 |
| A5 本地OCR | `green-pdf-ocr-v1` exit0，PLAN锁组件/语言profile；minimum mac有真实一页OCR | 受控样本已有证据；完整错误/取消/权限、三OS真实OCR、服务身份/H4缺失 |
| A6 直接索引 | direct-index-development：8 complete/2 partial、20下载/44表，基础Hub及禁处理探针 | 专项证明接收方向；所有授权/平台及X六方向未完成 |
| A7 成套/并发 | 正式 `execute-managed-update-replay-c1-v1`，同项目双目标；上传restart早项另有记录 | 回执C1补充为当前有效专项，未拿早期单目标数据充完整C1；restart双目标修订未应用，完整并发/故障矩阵未完；F2/F3相关 |
| A8 生命周期 | first-failure、managed-replace、cached-inflight各专项；旧/新CID分离代码 | F1已确认不符合；完整ready/partial/共享/最后授权/取消/恢复未完 |
| A9 查询/表格/原件 | table-read/preview/multiple-hits，CLI/HubCLI/MCP，空白网页真实下载专项 | 多个功能专项有效；完整scope/query-network、跨格式/联合/当前浏览器A主项仍未完成，旧ref生命周期受F1等影响 |
| A10 有界/隔离 | green-pdf-safety-v1；staging-capacity、paths、reservation专项 | F2/F3不符合；完整PDF滤镜/资源与所有边界/异常/监督平台格未完成；Windows仍有失败 |
| A11 兼容/发现 | README/指南/Skill更新，macOS3.11安装业务有正式记录 | F4/F7及上述OCR前置路径；当前HEAD最低版本/独立包最终复验、Linux/Windows最低业务、旧档案迁移保护仍不足 |
| A12 平台/证据 | 有原始记录、故障历史、公私脱敏链、部分CI回收 | 当前没有E三格/H三格/X六方向完整链，不能通过；pending与PR明确承认此点 |

### 本次实际打开/摘要核验的关键证据

- `tdd-green/green-reservation-lengths-v1/result.json` 存储SHA `b6abdc83e3667a39910d932bfd1465ef1bacd722eb420b236c6108027df77260`，main/regression原记录exit0；关联原始文件571个的存储SHA均相符。26个大输入为二进制 `.bin.gz`，不能按JSON解析；已实际解压其中一份20MiB输入，未把二进制解析失败当证据损坏。当前product绑定40/40、test绑定30/30匹配；独立review目标SHA一致、结论限预约计费。**不证明TTL/共享GC/真实已收部分字节。**
- `tdd-green/green-web-empty-original-v1/result.json` SHA `ea0f11ad28284f9c801a006203665d26b01ec52a72b63ce91bc03b180dd42c3f`，322份原始文件存储SHA匹配；实际打开一张资料行PNG，可见DOCX、empty-success、V/P及原件下载按钮。Local/Hub trace ZIP CRC通过，分别104/96个成员，trace记录1523/1457行可读取；不是只有不可读哈希。其当前product绑定仅36/40一致（两端HTML、transfers、managed_document_uploads随后改变），所以维持历史同版专项结论，不能直接授予本HEAD整SC9通过。
- `execute/execute-minimum-installed-mac-v1/result.json` SHA `b55ce87afdcf5d3be751d06199fa3c533d49bd5dd5eaeb33857a85fde962b7c9`，命令exit0；本次核原记录内356个私有路径存储摘要（含输出记录）均匹配。公开摘要352份业务原件与该计数口径不同，不据计数差异报告损坏。wheel包含较早WIP网页字节；仅证明该精确wheel的macOS3.11安装业务。
- `execute/execute-managed-update-replay-c1-v1/result.json` SHA `89f81c24fa653ce721bc53f9486ab78932abd123b96485a1a5baf8986310df2a`，916个存储摘要匹配，执行exit0；正式C1补充不能把旧回执聚焦用例所有历史执行改写成完整SC7。
- `tdd-green/green-managed-update-paths-v1/result.json` SHA `d0e317d9a0dba3a20e643556fc38083c5ca0c5d0c128cff4404254f21e480f27`，3102个文件存储SHA相符，其中2937份 `.json.gz`实际解压可解析；当前product绑定35/36匹配（transfers已变）。这不是Windows junction/请求内TOCTOU的实测证明。
- `tdd-green/green-web-ready-management-v1/result.json` SHA `46f1c6043457a746081aca36e7a5ad091ec6c01b57c5acead6d5553329fdfab6` 明确status=blocked、reason=evidence exceeds the per-attempt byte or image limit；不能用原stdout“2 passed”替代缺失exit/原生回归/独立绿灯。另行24项回归只属于其单独范围。
- `web-reader-development.json` 的A主项为2 failed：Local旧section隐藏问题已改HTML但未获该主项新版通过；Hub是Playwright `status_code`属性错误。后者是测试故障，不等于产品400行为失败，也不等于产品已通过。
- 当前公开常规CI检查点5126cd1：macOS/Ubuntu各432 passed/28 skipped，Windows409 passed/27 skipped/24 failed。13观察器socketpair、8启动PID、1normcase预期、1命名空间自检归为已诊断测试/探针问题，另1 MCP initialize断连仍未知。没有本次重新下载该CI全原件；仅核PR/公开CI记录及本地已存在索引，不将旧摘要扩成当前HEAD绿灯。

### guard与恢复边界的待证风险

Hub `documents.py:69–86` 的 DocumentGuard表集合未纳入008新增的 `document_captures`、capture_authorizations、processing_attempts、snapshot_state、processing_config、upload_jobs、hub_processed_stages；`DocumentGuard.fingerprint`只检查列出的表。`recover` 也仍只删除旧stage/receipt等表（Hub:1010–1016）。这确认了保护覆盖没有扩展，特别是仅配置/处理状态变化是否能检测回退尚无用例证明。**本次没有构造足以证明旧已失效引用复活的数据库回退，不把此推论列成已经复现的产品损害。** 需要一个仅008新状态变化的合法前后快照恢复反例、当前保护文件不回退、旧ref/旧任务/旧stage拒绝和重新明确授权正控；再据实际输出决定是否另增缺陷。F4的目录遗漏则已可从清单与存储路径确定，不依赖此风险成立。

## 交付意见

先修复F1/F2/F4的授权、并行可用性与恢复问题，并补F3/F5/F6/F7的对应小范围回归；修复均落在当前已确认行为内，无须降低规格。保留维护者已明确不应用的测试修订和现有失败历史，不为本次审查自行改判passed。随后在冻结候选上补足当前HEAD构建/安装/回归、完整C1与E/H/X及原始证据回收，重新做最终干净上下文PR审查。现阶段可继续开发，但不可把本意见或已有分项绿灯当作008合并/发布批准。
