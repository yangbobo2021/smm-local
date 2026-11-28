> 脱敏公开副本：任务工作区绝对路径替换为 `<TASK_WORKTREE>`；Windows完整机器/用户SID隐去。原始独立意见私有持久保存，正文判断不改。

# AT-SMM-008 网页上传正式执行独立复审 v1

Reviewer：`/root/completion_web_ui_execution_review`；本轮仅只读项目、执行证据和 SQLite（mode=ro），只写两个指定意见 JSON 与本文。未运行或修改产品/测试，未重新上传。

## 判定基线与边界

已实际打开本工作树 AGENTS.md、changes/008-document-format-support/{intent,spec,plan}.md，以及 app-delivery-acceptance-native/references/execution/reviewer.md。SPEC B1 规定两端普通/全局项目与选择/拖入、创建端处理和同步默认关闭；B5 规定原身份/原SHA/内容及处理版本和成套发布；B7 明确同名新上传独立身份、有界分块和真实状态；B8 提供全文、表格与原件核对面。PLAN采用独立任务档案/合成资料与真实服务/浏览器，不以本次开发源码运行代替平台安装矩阵。

采用定义 `.acceptance/native-v1/AT-SMM-008/definitions/000003.json`，独立SHA256为 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。SC1的本项唯一TC为 `TC-008-web-native-upload`，唯一认领检查 `creator-web-native-upload`。设计是 `case-design/design-completion-sc1-web-ui-v1/result.json`（c771444d5a1556f8d0d444715ceed8622a38f32f9f78b806d643206c084a9090）；已读 match-completion-sc1-web-ui-v4、runtime-completion-sc1-web-ui-v3及两份candidate-v3复审收据。候选意见仅用于确定已审分配，下面判断直接来自正式原件。

**Local与Hub各自通过本次正式执行；不把单端结论推广到另一端。两端合并也只证明网页初次ready上传子域，不判整SC1或008通过。** 路径、失败/替换、投影、陈旧页、扫描OCR质量、Web检索/下载交互、完整E/H/X由其他TC负责；新增三个installed脚本不在本项执行argv，不据此扩认。

## 代码及证据完整性

实际阅读 tests/test_document_formats_web_uploads.py 全部357行、tests/conftest.py、真实动态 Server 工厂/启动hook、观察与保留函数、native_input/upload_input与其独立生成器入口。网页用例测试文件SHA256 `98efc0b92420358b06dfa2c0d4486dcca731f48ea283f96f5fcdf1f4b1281add`；两份trace内src原文SHA256也相同。两份运行绑定各113文件全部按当前字节重算一致，包含真实helper和运行代码；match的286查阅绑定与运行113绑定职责不同，不据数量差异判失效。

`verify_original`（21行起）逐目标检索、错项目拒回、全文全部独立词句/排除项、全部表维度/格值/跨度/定位、原件信息和真实下载；`assert_upload_events`（63行起）逐目标begin、所有块、commit；`assert_ui_snapshot`（89行起）逐行格式/状态/V/P及published/latest/retry三组JSON；`assert_ui_ids`（106行起）读取全部真实DOM行且比数量/全集/唯一性，不按expected筛掉外来行。主项147行起，214-236行逐新pending目标与旧目标详情/全文表原件，250-258行逐新旧ready，268行后最终切换与同步默认关闭。末尾finally保留失败截图/trace和清理错误。

会后 `pytest_sessionfinish` 对JSON压gzip并记录原路径/长度/SHA和gzip长度/SHA；其代码不改原件、断言、stdout或exit。复审逐份独立解压到内存，核两种字节的SHA与长度，逐项恢复原JSON并用于后续核对；未覆盖证据文件。

|正式目标|result SHA256|artifacts全量校验|运行绑定|gzip逐项还原|原JSON总字节|原始结果|
|---|---|---:|---:|---:|---:|---|
|Local execute-completion-sc1-web-ui-local-v1|eae90e4069d903d129cd2e4d8031ee494ded7c15bd53a9f0ae12e907a1f52d94|752/752|113/113|634/634|4,732,522|4 passed, 1 warning in 14.19s；exit0；run.stderr 0字节|
|Hub execute-completion-sc1-web-ui-hub-v1|39c6f7dc30e13377a1455ff3e7b5734143f8972e2e37fbb6b36e4db27ad2c58e|751/751|113/113|637/637|6,181,398|4 passed, 1 warning in 22.68s；exit0；run.stderr 0字节|

stdout警告为FastAPI TestClient依赖的StarletteDeprecationWarning，不是失败。实际服务stderr另保存正常Uvicorn启动/退出日志，不能把外层stderr空误写为服务没有输出。

## Local 正式执行

证据根：`.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments`。以下八张均实际通过view_image打开原PNG；长图工具可能缩放展示，文件摘要仍按原PNG计算。

|原图|实际所见与支持边界|原trace对应|
|---|---|---|
|[local-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-chooser-1-pending.png)|普通#1；same.docx/xlsx/pdf三行pending，V/P0，原件已接收/正在处理；PDF展开published与retry均null；下方两项目默认不同步。|ohla@282集合3；截图@284|
|[local-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-chooser-1.png)|普通#1三份ready/V/P1，上传回执成功，PDF详情为真实已发布快照及最新AID。|ohla@404集合3；截图@406|
|[local-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-chooser-2-pending.png)|普通#1旧三行ready/V/P1与新三行pending/V/P0同时出现，旧PDF详情仍为原CID/AID/原SHA。|ohla@537集合6；旧详情直到@611；截图@613|
|[local-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-chooser-2.png)|普通#1六份同名但ID独立，全部ready/V/P1；多份展开详情，未把第二轮作为覆盖。|ohla@791集合6；截图@793|
|[local-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-drop-1-pending.png)|全局#2三份pending/V/P0；选择器显示全局；PDF无发布快照及可用原件。|ohla@940集合3；截图@942|
|[local-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-drop-1.png)|全局#2三份ready/V/P1；XLSX及PDF展开为各自快照，来源列表保留此前普通项目来源。来源列表为跨项目管理面，不与当前library全集混算。|ohla@1054集合3；截图@1056|
|[local-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-drop-2-pending.png)|全局#2旧三份ready与新三份pending并列，旧PDF原快照保留。|ohla@1179集合6；截图@1255|
|[local-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-local-v1/TC-008-web-native-upload/attachments/local-drop-2.png)|全局#2六行均ready/V/P1，旧三份与新三份分别保持各自身份及快照。|ohla@1433集合6；截图@1435|

逐文档复核如下。每份均有pending无发布快照/V=P0及ready成套V=P1；下表的“读取次数”是本文独立遍历正式HTTP记录得到的text/table/original-info总和，重复读取仍逐份核原身份、格式和原SHA。所有32张独立源表（152源单元格）、200个文字检查点都来自冻结truth；200次table视图包括按位置找表时的候选窗口，不冒称200张独立源表。每端另有60次全文、60次original-info及60次真实原件响应；12份下载文件逐字等于输入。

|输入标签|真实文档ID|项目|真实块数|读取次数|原SHA256|
|---|---|---:|---:|---:|---|
|localchooser1docx|5d11e5c5891a4de7952c31770f19c2fb|1|2|35|82e723df1b39446cfd8e3e4fc815cfafd97595e48a4bde080a9de7eff5c97e84|
|localchooser1xlsx|5b64c538e06e4d0b963a62df7ede5190|1|1|28|b5a854a0d308887fc845581bafea1a69bc58fdc39de63d324729bc128cf24d93|
|localchooser1pdf|a3b06b1ab84c44cb879563e70215c908|1|1|49|1807544edc022fe487306774d2897c2e1c4e05c8f8c8619fd9f67c0a05434bc2|
|localchooser2docx|6885741631db4967b7b36e69e888a9f7|1|1|25|a73e322cc69a191a7f652fb0a4664675051ac0cca8c639a69e93b278f113ee93|
|localchooser2xlsx|38107a38f4e24e0b8858dd288bafa5e4|1|1|20|46573dfdba3b3ce8ac1925a6e168175de6941236568981dc3746465ece089a77|
|localchooser2pdf|1da7711281174b3f96b878958675df98|1|1|35|1b5a3f6f03cdd99789d3cac1780e8fcc60aa80aa9c1a91331f0f78a21c3297dc|
|localdrop1docx|4f630016aa064ce9bff99240c5698cdd|2|2|25|0a1ed9fe4bc2a9ded0fbe5bb3e0bfdcb430a808e9acd8339372851eaa0b9e98b|
|localdrop1xlsx|6fd00f725fa045e9b766ddb7886b67e7|2|1|20|cf7de9f9fc1a114115ef3746c8274151d0389d508c3a6c6cf1059125764e603f|
|localdrop1pdf|046a241d02af428386298182ebf75930|2|1|35|a2f48d4c828f0815e13d9083ded60e899acdb969f9887d4c6c35f38c95f90ac0|
|localdrop2docx|b9f311d5e8a947489e1bde8a4b067ce6|2|1|15|6375f7f6420f7ca5cdd055d379b6f94f044526bc78d82d3ac52603667df3e19b|
|localdrop2xlsx|a1f13226224a423fb7215c81966b04a1|2|1|12|475d0ca25edb7616816c6a962345f3bdce64d3a6bd4457c77d45b70ed9dfc4c4|
|localdrop2pdf|9c2fbb6313774ccab198a37cb5fec1db|2|1|21|434db389d9be2f857787a83fbd0bbe97b896f2c9ef8e8aa5693ab7e66f61c82b|

两份首轮DOCX各大于1MiB，真实两块，其余各一块，共14块。begin按实际创建项目响应逐字段核稳定键、显示名、独立原SHA/长度/submission；commit核真实document/CID/AID。实际打开trace.network每一PUT的postData资源，14块全部逐字等于冻结输入的对应边界；不是仅核自报摘要。每份全部原始HTTP全文、表、original-info核V/P1、格式、原SHA和完整origin；逐真值词句/排除文字与全部表格维度/格值/跨度/定位，逐份错项目检索均空。独立读取主服务SQLite archive:identity核实archive身份：`abf91d4e57b5454599ff35fe38738944`（device_id相同），document_id分别为上表各自身ID。

`00035/00040/00073/00106/00163/00220/00225/00257/00346/00403/00516/00517-web-library-ui-id-set.json.gz`共12个产品观察，覆盖普通/全局刚选中空列表、每轮pending/ready及最终切换；actual=expected且行数及唯一性精确，没有筛除错项目行。

第二轮门内保留：00106后00107-00131、00346后00347-00371分别读取旧DOCX/XLSX/PDF全文、全部表、original-info和原件。旧ready完整library对象在重复观察中相等；trace旧三组详情真实返回与其API值逐字段相同。主项trace有693对before/after动作、143网络、1117帧DOM snapshot，实际选择动作ohla@158/@419，drop动作@815/@1060，最终@1451/@1467各六行。108次详情innerText结果逐一独立与原始HTTP的published/latest/retry对象比较，全部匹配；无动作错误和失败HTTP。最终sync-status两项目均enabled=false、state=default_off，原图也可见默认不同步。

观察器实际自检记录00003/00006：Local和Hub各2正控、8反控（漏行/重复/外来行/切换残留/非法标签）；00007为有效分块与元数据正控及20处改变拒绝。实际gate正控（00030）先真实pending两次，再释放到真实ready并完整读取；门仅包装真实ManagedDocumentUploads.run_pending开始时机，随后原处理函数照常运行，不替换结果、状态或HTTP响应。

|服务证据|PID|端口|正常退出|强制回收|复审时连接|
|---|---:|---:|---:|---|---|
|00031-restart-server-stop.json.gz|88767|59180|0|false|独立socket连接不可达|
|00622-restart-server-stop.json.gz|88774|59189|0|false|独立socket连接不可达|

两次服务分别为gate正控与主网页用例；真实启动身份含PID/ctime/argv/物理exe/档案/nonce，正常关闭日志完整，stop实现还按已登记进程树核无剩余并验证端口不可达。浏览器结束证据page_errors和cleanup_errors均为空。

## Hub 正式执行

证据根：`.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments`。以下八张均实际通过view_image打开原PNG；长图工具可能缩放展示，文件摘要仍按原PNG计算。

|原图|实际所见与支持边界|原trace对应|
|---|---|---|
|[hub-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1-pending.png)|认证Hub，普通#1三份pending/V/P0；未宣称可检索，PDF发布快照与retry为null。|uddc@274集合3；截图@276|
|[hub-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1.png)|普通#1三份ready/V/P1，上传成功；可见XLSX/PDF各自已发布快照/最新尝试/重试目标。|uddc@394集合3；截图@396|
|[hub-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2-pending.png)|普通#1上传回执为新三份pending/V/P0，library在截图瞬间为空。此图本身不能证明旧行保留；下文用原trace和门内HTTP补足。|uddc@527六行旧V1+新V0；旧详情@545-601；截图@603|
|[hub-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2.png)|普通#1六份ready/V/P1，旧三份和新三份均能发现；并有独立已发布/最新/重试详情。|uddc@775集合6；截图@777|
|[hub-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1-pending.png)|全局#2三份pending/V/P0，DOCX/XLSX/PDF详情均为未发布及真实pending尝试。|uddc@920集合3；截图@922|
|[hub-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1.png)|全局#2三份ready/V/P1，XLSX/PDF有对应原SHA及已发布快照。|uddc@1040集合3；截图@1042|
|[hub-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2-pending.png)|全局#2新三份回执pending/V/P0，library在截图瞬间为空；不能从此图单独判断旧三份状态。|uddc@1165六行旧V1+新V0；旧详情@1183-1239；截图@1241|
|[hub-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-ui-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2.png)|全局#2六份ready/V/P1，逐份展开正确原SHA、CID/AID与重试目标。|uddc@1417集合6；截图@1419|

逐文档复核如下。每份均有pending无发布快照/V=P0及ready成套V=P1；下表的“读取次数”是本文独立遍历正式HTTP记录得到的text/table/original-info总和，重复读取仍逐份核原身份、格式和原SHA。所有32张独立源表（152源单元格）、200个文字检查点都来自冻结truth；200次table视图包括按位置找表时的候选窗口，不冒称200张独立源表。每端另有60次全文、60次original-info及60次真实原件响应；12份下载文件逐字等于输入。

|输入标签|真实文档ID|项目|真实块数|读取次数|原SHA256|
|---|---|---:|---:|---:|---|
|hubchooser1docx|595f1c4403c6499e8ad95bd32cdfa983|1|2|35|d688867682ca5f5d39c9545952dacb58123934e8a455f54b2680c527d1c20922|
|hubchooser1xlsx|7e52759c3bb54b33a2dd87ad0ef1d3c8|1|1|28|6f232ad49e84ce1c651ceab598a499eece4a463fd40e9a1003645cb231510a1e|
|hubchooser1pdf|bf52f537b26b46729dc8d4d344b28430|1|1|49|c170e8b4b8c4165feef3cd3caf1a047e96ccdf408cd5afae2010e516736af110|
|hubchooser2docx|6895d0a512514e2f8e11d4bad05cdf0e|1|1|25|72842509ec07d93f64b0e63a1f0c4802cc14b891bef7684578e3c6c7c5c8438e|
|hubchooser2xlsx|7c7b2d59595b4340aba701b4a8938677|1|1|20|5bc82cc2ce0d09a4158271d9bd1c321b2397d6ab3126103c29d6965a8aae1e20|
|hubchooser2pdf|490b0715c27d44ffb57bd4277160cede|1|1|35|4b84e09964fc51df85c1de56cdf13212fdd09069d4e9ba2d43ee85793388d44b|
|hubdrop1docx|e5a6bea33edd45e2ada2599a2b5cc0b0|2|2|25|1fc964de3a50a59248ef9d82255eadf790d9435374fa1cc3ab6dc2251ad88415|
|hubdrop1xlsx|f4586dab15b040938a8fa06020cb7763|2|1|20|75c66d8551fa9f899d8cc565f542feb34fce3cc40f7e8cb0e60766f351694da6|
|hubdrop1pdf|4d644264584c4e15bbe84bcec88a3797|2|1|35|ab9459ab1022a3aaca31562977c270cb74dd55eca925bdbb688417e7fe7b8794|
|hubdrop2docx|901f9cd3c89d48278a5d757f14235732|2|1|15|dab6de72d925826f436d39bfa3190540f34e93e48db3e26edcfa76bc03a9a772|
|hubdrop2xlsx|0a981400c80c4261a711cfff871bee37|2|1|12|147c4c182e15a0163de580f16cc3ec31430e180ea3c36ddb083e71e3c8f069a7|
|hubdrop2pdf|9d5d9828a22842e9a608ac8721319043|2|1|21|d49b7377b3c294130ab1cdbf6b6f832f8bdfe29f048528d3db41077bffab605f|

两份首轮DOCX各大于1MiB，真实两块，其余各一块，共14块。begin按实际创建项目响应逐字段核稳定键、显示名、独立原SHA/长度/submission；commit核真实document/CID/AID。实际打开trace.network每一PUT的postData资源，14块全部逐字等于冻结输入的对应边界；不是仅核自报摘要。每份全部原始HTTP全文、表、original-info核V/P1、格式、原SHA和完整origin；逐真值词句/排除文字与全部表格维度/格值/跨度/定位，逐份错项目检索均空。独立读取主服务SQLite archive:identity核实archive身份：`ca5839b7e61a4874b1a644fd539154ae`（device_id为Hub `64788b5663924a5d96d0496089b7b9aa`），document_id分别为上表各自身ID。

`00039/00044/00077/00110/00166/00223/00228/00261/00350/00407/00520/00521-web-library-ui-id-set.json.gz`共12个产品集合观察；实际DOM全集与两项目各自累积收据ID精确相等且唯一。所有/v1浏览器请求均有认证；begin/commit的HID与epoch为当前认证身份，原trace请求中逐块保持同源。

第二轮两张pending截图的library为空须明确保留，不能在图注中写成“图上可见旧三份”。本轮直接打开原trace核定：uddc@527（5237.30ms）返回六行，其中旧595f…/7e527…/bf52…版本1、新6895…/7c7b…/490b…版本0；@545-601逐三个旧资料的三组详情实际返回其原发布和ready尝试。随后截图@603为5785.216-5893.222ms。全局对应uddc@1165（12440.51ms）六行、@1183-1239逐旧e5a6…/f458…/4d644…详情，截图@1241为13082.198-13231.123ms。源码src/smm_hub/static/index.html:105在renderLibrary开始replaceChildren，第108行等待真实library响应后才重绘，与轮询重绘空窗相符。图像空窗不是旧发布或正文资格丢失的证据；也不把本次通过表述为连续每帧从无空窗。

门内原请求00110后00111-00135、00350后00351-00375，分别完整读回旧三份全文/全部表/原件信息与原件，均在主项代码gate.touch前完成。独立检查所有旧ready library对象未变。完成截图与uddc@775/@1417六行ready吻合，最终@1435/@1451分别返回普通/全局各六份，没有串入另一项目。主项trace有685对before/after动作、136网络、1112帧DOM snapshot；选择@146/@409、drop@799/@1046；108次三类详情innerText真实值逐项与原始HTTP匹配，无动作错误、失败HTTP、page_errors或cleanup_errors。默认同步关闭属于Local项目配置，本Hub执行不据此另认Local同步。

观察器实际自检记录00003/00006：Local和Hub各2正控、8反控（漏行/重复/外来行/切换残留/非法标签）；00007为有效分块与元数据正控及20处改变拒绝。实际gate正控（00032）先真实pending两次，再释放到真实ready并完整读取；门仅包装真实ManagedDocumentUploads.run_pending开始时机，随后原处理函数照常运行，不替换结果、状态或HTTP响应。

|服务证据|PID|端口|正常退出|强制回收|复审时连接|
|---|---:|---:|---:|---|---|
|00033-restart-server-stop.json.gz|89838|59509|0|false|独立socket连接不可达|
|00625-restart-server-stop.json.gz|89947|59527|0|false|独立socket连接不可达|

两次服务分别为gate正控与主网页用例；真实启动身份含PID/ctime/argv/物理exe/档案/nonce，正常关闭日志完整，stop实现还按已登记进程树核无剩余并验证端口不可达。浏览器结束证据page_errors和cleanup_errors均为空。

## 交付意见

Local意见：`.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-sc1-web-ui-local-execution-v1.json`，已先单独通知主Agent登记。Hub意见：同目录`review-completion-sc1-web-ui-hub-execution-v1.json`，完成后已单独通知。每份仅含TC-008-web-native-upload，status=passed，covers仅creator-web-native-upload；reason明确限定本端、本次网页上传子域。

没有重跑、改变输入或修测试来取得这些结论。图像可见范围、trace实测、HTTP真值核对与源码解释分别标明；完整008、平台安装、服务矩阵、同步投影及其他独立TC的缺口仍由原记录维护。
