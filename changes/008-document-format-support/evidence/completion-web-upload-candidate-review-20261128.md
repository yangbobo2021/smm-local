> 脱敏公开副本：任务工作区绝对路径替换为 `<TASK_WORKTREE>`；Windows完整机器/用户SID隐去。原始独立意见私有持久保存，正文判断不改。

# SC1 网页上传候选 v3 独立复审

日期：2026-11-28。项目：`<TASK_WORKTREE>`。验收：AT-SMM-008 / SC1。仅审实际 TC-008-web-native-upload，分配项 creator-web-native-upload。结论：Local、Hub 两份当前候选分别 **passed**，不需修订。两份意见已分别写入 review-inbox 并即时通知主 Agent 登记。

## 基线、场景与自然设计

已先实际打开 AGENTS.md、changes/008-document-format-support/intent.md、spec.md、plan.md、tests/conftest.py、tests/test_document_formats_web_uploads.py；随后核独立 Reviewer、自然设计边界检查与探针自检规则。依据为实际 definitions/000003.json，SHA `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`，SC1 原文“**两端支持新建普通/全局项目、明确纳入路径及网页选择/拖入，并显示真实处理状态，文档同步默认关闭。**”

场景判据保持业务行为，没有把浏览器定位器、文件数量或具体命令强加为产品规则。本 TC 的网页上传子域依据 SPEC B1（9–17行）、B4（57–59行）、B5（63–79行）、B7（97–103行）和 A1（181行）。同名新上传独立身份、真实 pending/processing 与 ready、发布前 V/P0、发布后 V/P1、published/latest/retry 展示及已发布整套保留均有已确认依据。PLAN 规定集合/唯一性与逐全部适用目标核验（TC表前及E1步骤），因此不能只看首份或只看 API。

自然设计 design-completion-sc1-web-ui-v1（SHA `c771444d5a1556f8d0d444715ceed8622a38f32f9f78b806d643206c084a9090`）覆盖每端普通 chooser/全局 drop，每项目两轮各 DOCX/XLSX/native PDF，独立原字节共12份。新项目空态、首轮 pending/ready、已有三份 ready 时第二轮 pending、六份 ready、最终切换两个项目是有行为差异的前置状态。失败/替换/空白/投影/陈旧页、路径纳入、完整 E/H/X 在设计及匹配中明确分配到其他用例，不能被本候选关闭；也不因这些既有分工反向阻塞此限定子域。Local 默认不同步通过两个项目完整集合及每项 enabled=false 实际核验；Hub 没有伪称拥有 Local 的同步配置。

## 版本与源码绑定

- match-completion-sc1-web-ui-v4 result SHA `98fefa733983b78e2840e67a30d1e55a026fc9193dba69871d268d586f964012`。
- runtime-completion-sc1-web-ui-v3 result SHA `0ab344a8d9be567ad242ec76adda4ef6650fecf7cea6bc810364a941b53974e5`。原 smoke stdout 为6项 collected，exit0、stderr空，无以收集成功代替业务通过。
- 当前测试文件 SHA `98efc0b92420358b06dfa2c0d4486dcca731f48ea283f96f5fcdf1f4b1281add`。本轮diff增加53行真实DOM全集/保留状态及探针补证，没有减少原断言。
- 两目标与 runtime 的113绑定完全一致，64个全部产品 .py/.html +49个测试/辅助文件；每个绑定SHA与实际文件及各自source冻结副本逐字一致。match的286查阅文件与运行113文件职责不同，无需强行相等。
- 从实际 import AST 递归核22个所用测试模块全部在绑定内：conftest、web_uploads、management、replace、retry、upload_restart、document_helpers、hub_document_helpers、test_005_contracts、test_federation、test_hub_documents_contracts、test_vibeinsight_sync，以及 document_formats_exit_observer/fixtures/managed_empty_fixture/partial_fixture/pdf_fixture/platform/restart_server/sync_observer/table_fixture/upload_fixture。动态 `-m document_formats_restart_server`、生成 sitecustomize 的 install_audit 和子进程中的 platform import 均已核入。所有src产品模块/HTML均绑定，未发现动态工厂遗漏。

仅对下表v3结果出具意见。Local v1、Hub v1、Hub v2 result 均原样 blocked，reason 为 evidence exceeds the per-attempt byte or image limit；Local v2 实际为 debugged，不能把它改述为 blocked。本轮不改旧记录、不给旧版补过。

## 原始运行与附件核验

|目标|result SHA|原 stdout / stderr|绑定 / 全artifact|原附件总字节 / 全artifact字节|
|---|---|---|---|---|
|Local v3|fddb4529d8b5a5db4c23c591258974317193daba96c7fe3d5014d556c95453db|4 passed, 1 warning in 12.70s；stderr空；exit0|113 / 861，全部逐SHA通过|21,428,989 / 22,762,488|
|Hub v3|4da15de586f71ae46b44c1cebe650e957c1fac70b6924916cf622ca948ed40fd|4 passed, 1 warning in 18.09s；stderr空；exit0|113 / 858，全部逐SHA通过|21,030,048 / 22,363,541|

两个 run.stdout 的warning均是既有Starlette/httpx弃用提示，没有业务失败、skip或隐藏stderr。原始server stop证据各两次 exit0、forced=false；浏览器 page_errors=[]、cleanup_errors=[]。实际HTTP观测分别588/589条；浏览器请求141/130条。除gate独立正控外，主项两端各12实际文档、14完整上传分块（两个超过1MiB的DOCX各两块，其余一块）。独立重新读取原附件核每份begin的输入SHA/长度与项目，全部分块序号/长度/摘要和commit身份，逐份独立真值正文60次、完整表200次、original-info60次，12个不同输入SHA对应的实际下载均逐字相等。每个表行列、格值、合并跨度及定位均对源真值，不只比较两个产品响应。

### 无损压缩

实际查看 conftest 第20–48行：只有原JSON累计 **>8MiB** 或整个附件 **>20MiB** 才压缩JSON；mtime=0，压缩后立即解压与原字节相等，manifest登记压缩/原始两组SHA和长度。截图及完整trace不改字节。不改变stdout、exit、输入或断言。

|目标|逐份 gzip 数|原 JSON 字节|gzip 字节|manifest 字节|重建压缩前附件字节|
|---|---:|---:|---:|---:|---:|
|Local|630|4,703,011|1,185,274|220,519|24,726,207|
|Hub|631|6,114,846|1,786,857|220,998|25,137,039|

逐份实际打开lossless-evidence.json、读取每个gzip、解压原字节，再对原始SHA/长度和压缩SHA/长度；全部通过且JSON可解析。压缩前JSON都未超过8MiB，两端总附件均超过20MiB，实际触发与新增条件一致。根artifact清单覆盖PNG/trace及其原SHA，全部核验通过。未把gzip内容摘要冒充原JSON。

## 实际浏览器轨迹

读取两份zip内部trace.trace、trace.network、resources与源码，并用本轮Python包附带Playwright1.65.1 CLI实际trace open/action/requests/snapshot。较旧全局Viewer不支持v10 trace，因此改用本轮同版本Viewer后正常打开；未下载替代浏览器，snapshot使用冻结PLAYWRIGHT_BROWSERS_PATH。

|目标|平台/视口|动作/请求/错误|实际输入动作|最终项目切换和DOM|
|---|---|---|---|---|
|Local|darwin /1280×900|685/141/0|chooser vevt@158、411；drop vevt@807、1048|1421/1437实际切项目；1451 after快照项目2完整六ID及各ready V/P1|
|Hub|darwin /1280×900|669/130/0|chooser yoim@146、393；drop yoim@783、1018|1389/1405实际切项目；1419 after快照项目2完整六ID|

chooser trace中的所有payload原字节实际base64解码与冻结inputs逐字匹配；drop实为DataTransfer+File事件送入真实产品drop入口，不是将input.files重命名为拖入。两端trace POST可见2次创建、12次begin与12次commit，全部200；14次PUT全部成功。Hub /v1请求认证头实际记录为存在，无URL token。两端主trace无错误，动作结束清理记录有正常进程退出。

## 已实际打开的原始PNG及所见

以下路径均为本轮v3原始PNG，逐张通过view_image打开，不使用接触表或文字摘要代替。长图在显示工具中等比缩放，精确身份/详情同时用原trace DOM及断言核对。展开details会被周期性刷新折叠，不声称每一张图都同时展示每份三JSON。

|原图绝对路径|所见及支撑|
|---|---|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-chooser-1-pending.png`|普通#1；三格式列表pending、V/P0，原件下载禁用，处理后再检索提示可见。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-chooser-1.png`|普通#1；三份格式DOCX/XLSX/PDF均ready、V/P1，成功回执及下载入口可见。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-chooser-2-pending.png`|普通#1；新三份pending V/P0与旧三份ready V/P1共存，第二轮没有覆盖旧身份；详情展开状况随轮询变化，精确三JSON以trace和断言为准。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-chooser-2.png`|普通#1；两轮六份同名独立文档ready V/P1，旧三份身份保留，部分或全部详情展开。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-drop-1-pending.png`|全局#2；三格式列表pending、V/P0，原件下载禁用，处理后再检索提示可见。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-drop-1.png`|全局#2；三份格式DOCX/XLSX/PDF均ready、V/P1，成功回执及下载入口可见。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-drop-2-pending.png`|全局#2；新三份pending V/P0与旧三份ready V/P1共存，第二轮没有覆盖旧身份；详情展开状况随轮询变化，精确三JSON以trace和断言为准。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-local-v3/TC-008-web-native-upload/attachments/local-drop-2.png`|全局#2；两轮六份同名独立文档ready V/P1，旧三份身份保留，部分或全部详情展开。 下方普通/全局同步选择均“默认不同步”。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-chooser-1-pending.png`|普通#1被选中；三个same.docx/xlsx/pdf上传回执pending、V/P0；截图恰在轮询重绘空library，不能认作三行详情截图。紧邻trace DOM/全集与逐项断言补证。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-chooser-1.png`|普通#1；三份格式DOCX/XLSX/PDF均ready、V/P1，成功回执及下载入口可见。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-chooser-2-pending.png`|普通#1；新三份pending V/P0与旧三份ready V/P1共存，第二轮没有覆盖旧身份；详情展开状况随轮询变化，精确三JSON以trace和断言为准。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-chooser-2.png`|普通#1；两轮六份同名独立文档ready V/P1，旧三份身份保留，部分或全部详情展开。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-drop-1-pending.png`|全局#2被选中；三个same.docx/xlsx/pdf上传回执pending、V/P0；截图恰在轮询重绘空library，不能认作三行详情截图。紧邻trace DOM/全集与逐项断言补证。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-drop-1.png`|全局#2；三份格式DOCX/XLSX/PDF均ready、V/P1，成功回执及下载入口可见。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-drop-2-pending.png`|全局#2；新三份pending V/P0与旧三份ready V/P1共存，第二轮没有覆盖旧身份；详情展开状况随轮询变化，精确三JSON以trace和断言为准。|
|`<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-ui-hub-v3/TC-008-web-native-upload/attachments/hub-drop-2.png`|全局#2；两轮六份同名独立文档ready V/P1，旧三份身份保留，部分或全部详情展开。|

Hub首轮pending两张截图的library重绘空态不是永久缺失证据：已实际用trace snapshot yoim@266 after取得普通项目三行精确ID/V0及三pending回执，与00043-web-library-ui-id-set.json.gz相符；drop同样有00226全集观测和逐三份details断言。第二轮pending图和四张ready图实际显示完整列表。需求未规定轮询刷新不得短暂清空重绘，不新增连续可见SLA；可选在截图前等待渲染稳定，使单图证据更直观，当前断言+轨迹已足以判断，不阻塞。

## 必测反例逐断言核对

|反例|需求依据|首个实际拦截位置及原因|
|---|---|---|
|只上传/处理/显示首个目标，非首份错或遗漏|SPEC9/59/97、PLAN逐全部目标|web_uploads:221–224逐每份commit ID/CID/AID、pending/V/P0、项目；UI遗漏先由89–102该ID唯一行/格式/版本/详情拦截；若额外、重复或跨项目行，228调用106–118核全部DOM行并保留重复，actual必须严格等于预期全集。ready与最终切换分别257/273再核。|
|刚选空项目仍残留另一项目|SPEC9/97项目边界|199的expected=[]直接进入106–118，任一旧行即不能通过；不是先筛当前ID再数。|
|第二轮上传pending时清掉/改坏第一轮非首份旧资料，但ready后恢复|SPEC63–79完整整套/保留、97新上传独立身份|231 current==retained.entry完整比较首先拦状态；232逐每个retained调用89–102 UI身份、状态、三JSON；233调用21–51独立读正文/全表/原件，均在gate.touch之前执行，不能只靠最终ready证明。|
|第二轮覆盖同名旧文档，普通/全局误用同一份|SPEC97同名独立身份|第二轮221–224要新pending无published，旧ready同一ID首先冲突；231旧entry保存与257六份全集、268全12唯一ID再拦；不同项目29明确零命中。|
|UI和API两面同错，返回另一目标或同一错误内容|SPEC75–77完整origin/V/P/摘要，PLAN独立真值|24必须唯一正确ID；27–33在search/text逐独立origin、V/P1、格式、原SHA、源词及排除词；44–47 table全单元和合并跨度、50–51原件逐字。不是仅UI==API。|
|两个端同用错误处理版本或拼旧内容|SPEC75–79版本与成套发布|223独立V/P0，251独立V/P1；15–18元信息每观察面核V/P1/格式/SHA；独立正文和全表真值及原字节使两端同错不能仅因相等放过。|
|begin/parts/commit共同误发项目、部分分块漏/换/错序|SPEC B7分块原件/绑定|70独立稳定项目/键/长度/文件名，71新上传不含document_id，74–81全部chunks数量/序号/边界/长度/摘要，83–86 commit顺序和本份ID/CID/AID。|
|只有pending提示成功，未处理却宣称可检索|SPEC59|223无published/V/P0、226–227 UI禁止ready/可检索与实际搜索零结果；解除gate后必须247–252真实完整ready/当前CID且非publication_pending再读取。|

真实DOM探针：121–142在两种真实浏览器容器均有正常全集/空集合正控，非首份遗漏、仅另一份、重复、foreign、多份重复、陈旧空项目、不可解析行各8拒错；原附件00003/00006记录实际拒错数。307–333独立分块与metadata正负控共20拒错，00007原件已核。336–357用真实服务器捕获后两次pending、释放后ready及可读原件核gate；gate仅延迟run_pending调用起点，仍调用original处理，不伪造响应/结果/解析器。失败分支保留PNG/trace并收集cleanup_errors，未删异常或改exit。

未发现原始依据已要求、但当前限定候选仍能放过的非首目标/动作前状态/两面同错反例。增加等价目标或更换同条件标识没有新的判定分支，属于可选补测；不无依据阻塞。partial/failed/empty/替换等有不同预期，但已明确归属其他检查，本意见不认领其通过。

## 意见交付与边界

- review-inbox/review-completion-sc1-web-ui-local-candidate-v3.json，SHA `b75fdb976da1bed37bb9b2b571b159e7632c5ad5a05d1eec47c2bdd98892ffe7`。
- review-inbox/review-completion-sc1-web-ui-hub-candidate-v3.json，SHA `91c3ebc2c749b0cd52305e4cd4c4d38ba4fb4d79f317cd3631cd46acd9fae5ba`。

两JSON均只含目标真实TC，covers仅creator-web-native-upload。设计/实现有效且此轮适用断言全部实际到达，无需revision_target。仅网页上传候选通过，需要两端共同构成此子域；不是完整SC1、完整C1、三系统安装/服务、E/H/X或008总体验收结论。本轮未改产品、测试、原证据或旧结果，只写本轮两意见及本报告。
