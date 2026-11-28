# AT-SMM-008 atomic-row 正式执行独立复审 v1

Reviewer：`/root/completion_web_ui_execution_review`。独立判定两个新execute，未借旧web-ui passed；本轮只写两份指定意见和本文，未改产品、测试或原证据，未读key。SQLite仅mode=ro查询archive:identity核来源身份。

## 重新核对的基线

本轮重新打开AGENTS.md与008 intent/spec/plan及definitions000003。SPEC B1的创建端、普通/全局及选择/拖入和默认关闭同步；B5的成套身份/版本；B7的同名独立上传、有界分块及真实状态；B8的全文/表/原件核对；PLAN独立工作树、合成资料、真实服务/浏览器与完整平台边界，均继续适用。

定义SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`；唯一TC是`TC-008-web-native-upload`，covers仅`creator-web-native-upload`。已读本轮candidate-v1收据及web-row-candidate-review-v1.md核分配；下面依据当前正式原件，不采用候选图片/结果作为正式实测。自然设计design-completion-sc1-web-ui-v1（SHA c771444d5a1556f8d0d444715ceed8622a38f32f9f78b806d643206c084a9090）的逐目标、两轮、旧资料保留与可见详情义务不变。

Local/Hub各自passed仅本端当前网页初次ready上传子域。路径、失败/替换、投影、陈旧页、OCR扫描质量、Web检索/表格/下载交互以及完整008/E/H/X不在此判定。新installed脚本未出现在业务argv，不扩认其能力。

## 原子观察及反例

实际打开当前测试全部代码、conftest、Server及sitecustomize动态restart_server/gate、真值生成和HTTP/保留helper。各113绑定含64产品py/html、49测试源，当前字节全符；另递归AST从主测试、conftest及动态restart_server解析38个当前本地模块，全在绑定中。两trace内嵌测试源SHA `45f02f8dc646986bf3414a5032b963f23f7c2416adf5eb524d2f330d7ec45671`等于绑定测试。

assert_ui_snapshot第89–116行：一次row.evaluate读取connected/details.open/innerText/三JSON，只关闭或脱离时有界重开；取得连接且展开行后在循环外断言格式、状态、V/P及三个对象等值，错误值不会重试等到正确。latest核capture_id/attempt_id/status/config_revision/error五字段，其他两对象完整比较。

第119–143行真实浏览器控制：第一次summary click同步innerHTML换成新关闭行，观察器实际重开新行；分别把三个面板CID改foreign，每次立即AssertionError。每端正式第五项pytest实到；两owner原控制记录actual_replacement_reopened=true、wrong_capture_panels_rejected=3。仅改合成DOM。

每端38份原web-visible-row-snapshot中36产品、2控制；逐份核connected/open为真，三块完整JSON文字均在同份innerText里，再逐对象与该文档原HTTP值独立比较，涵盖12pending及24ready/保留。没有把关闭details中textContent独自当可见证据；当前nativeDetails三pre均位于同一details。trace未记录本次Element.evaluate返回，因此同回合值据已核SHA的原JSON，不虚称trace承载这些值。

适用反例及首拦截：首份正确后续错绑由261–267逐份receipt/ID/CID/AID/pending拒绝；API/UI两面同错由21–51独立origin/原SHA/全文全格/原件拒绝；漏/重复/外项目行由146–158完整多重集拒绝；第二轮旧资料丢失或改变由270–273完整entry、原子可见三面板、全文全表原件逐旧目标拒绝；错CID在113–114循环外等值立即失败；换代关闭行在99–104重开且有真实控制。另保留两DOM容器各2正8反、身份分块20反、真实gate hold/release正控。

## 原件完整性与执行

全部artifacts逐件重算SHA，包括stdout/stderr/PNG/trace/输入/响应/下载和lossless manifest，无缺件或不符。每gzip条目实际读压缩字节，核gzip长度/SHA，解压到内存再核原JSON长度/SHA并解析。conftest仅会后无损包装，不改输入/断言/退出、PNG或trace原字节。

|正式目标|result SHA256|artifacts|bindings|gzip条目|原JSON字节|原stdout|
|---|---|---:|---:|---:|---:|---|
|execute-completion-sc1-web-row-local-v1|6c7b72bb919b9f595d5465e6b484d3cb66ba56fa3704c522e22a141a241ac2cb|792/792|113/113|672/672|4,796,902|5 passed, 1 warning in 15.81s|
|execute-completion-sc1-web-row-hub-v1|b02147780b7114c8ef5366049777afbaa8a81d2eaf3e09e616aea6817362fbb1|789/789|113/113|674/674|6,232,531|5 passed, 1 warning in 20.00s|

两次exit0，run.stderr空，无skip；唯一warning为Starlette TestClient的httpx弃用。实际服务stderr另有正常Uvicorn启动/退出，不把外层stderr空说成服务无输出。

## Local 正式复核

证据根：`.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments`。以下八张本轮原PNG均实际view_image打开，长图展示可能缩放，摘要按原PNG核。

|原图|实际所见|原trace|
|---|---|---|
|[local-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-1-pending.png)|普通#1三份pending/V=P0、下载禁用，三详情截图中折叠；两项目默认不同步可见。|xmdj@242三行；截图@244|
|[local-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-1.png)|普通#1三份ready1，三详情展开，各自CID/AID及原SHA可见。|@320三行；截图@322|
|[local-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-2-pending.png)|普通#1六行旧三ready1/新三pending0，旧PDF展开，其余折叠。|@425六行；截图@461|
|[local-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-2.png)|普通#1六份ready1，旧三及新XLSX/PDF展开，新DOCX折叠，同名ID独立。|@567六行；截图@569|
|[local-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-1-pending.png)|全局#2三份pending0，三详情折叠，正在本端处理提示。|@676三行；截图@678|
|[local-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-1.png)|全局#2三份ready1，PDF展开、DOCX/XLSX折叠。来源列表是全部来源，不能当作当前library集合。|@758三行；截图@760|
|[local-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-2-pending.png)|全局#2六行旧三ready1/新三pending0，详情折叠，旧原件按钮可用。|@847六行；截图@883|
|[local-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-2.png)|全局#2六份ready1，旧三及新PDF展开，新DOCX/XLSX折叠。|@993六行；截图@995|

截图在原子断言之后，轮询可能再次折叠或清空；图注依实际所见，不将折叠面板当展开内容。三面板可见值依据同回合原快照与原HTTP独立比值。

|输入|文档ID|项目|真块数|原SHA256|产品row原快照编号|
|---|---|---:|---:|---|---|
|localchooser1docx|785dd19917ab48289275c65a268834f6|1|2|0302faff27f0eeaed3e3800ad6baccb80661c6cb14ebcd586e745d3602e87f6f|00036, 00057, 00114, 00176|
|localchooser1xlsx|e1eff160baa64d959f07ae14f3d259a9|1|1|b650ce7e72762cb06a009b1c5c414edc1b66a78dafcc90f307d6db830d3b07d3|00038, 00065, 00123, 00177|
|localchooser1pdf|f605795846d745c494e5df51d81965a5|1|1|1807544edc022fe487306774d2897c2e1c4e05c8f8c8619fd9f67c0a05434bc2|00040, 00076, 00131, 00178|
|localchooser2docx|56eecda7943641b5869c9030ee11a700|1|1|69966e96a36fb3708f6c16b4e6c7ceb0c049ce154a7a4ffacb379da519b30719|00107, 00156|
|localchooser2xlsx|291118575c8040ec85eb9343c813772b|1|1|bbfd5c826f9a10e04f69fc5ebf5e82300aaed0f58af84e1fe4667dcbc545a12b|00109, 00164|
|localchooser2pdf|31429f450a87494ab3900fd6dcbb9a93|1|1|1b5a3f6f03cdd99789d3cac1780e8fcc60aa80aa9c1a91331f0f78a21c3297dc|00111, 00175|
|localdrop1docx|21081c7843934488ac4fc2b241d6fabe|2|2|1659188cff39ca0ae12dd27a26637182971506c9f1edf3a61e585f8bc38a2185|00238, 00259, 00372, 00434|
|localdrop1xlsx|ee5c9984606e4a728689e7a182a1955e|2|1|9bcfab80b3c37099f10ec78c76788772cdb711fd6e28dcd5c5982d2ee3fcc9ec|00240, 00267, 00381, 00435|
|localdrop1pdf|86cd7aed6eff4e069fd8f68710b117d3|2|1|a2f48d4c828f0815e13d9083ded60e899acdb969f9887d4c6c35f38c95f90ac0|00242, 00278, 00389, 00436|
|localdrop2docx|258b2e2f1f0e47578b5040624aff2c62|2|1|96e3fc380266dac88ac3218a97cb54b514d3b7d501d2f796fd04bad99a647511|00365, 00414|
|localdrop2xlsx|ce394b42a01c4a4e8e1e658fcc3daf64|2|1|b9722efa4c0e392e25b12a1b4e2d8b1c1dda987dfd75fcd472c4bf751f5e04cf|00367, 00422|
|localdrop2pdf|fbb4134a8d204dc39b03643ef1152cee|2|1|434db389d9be2f857787a83fbd0bbe97b896f2c9ef8e8aa5693ab7e66f61c82b|00369, 00433|

12独立原件/ID，普通选择、全局drop各两轮三格式，首轮两份DOCX各超过1MiB真两块，其余一块，共14块。独立核每个browser response文件SHA/长度，从真实创建响应核ordinary/global和begin稳定项目键；逐begin项目/显示名/原长度/SHA/submission、每块序号/边界/双SHA及commit document/CID/AID。实际打开trace.network所有PUT的postData资源，14块字节与冻结输入对应段逐字相等。Hub另核HID/epoch及认证。

每份原library pending无pub/original ref,V=P0；ready单一项目/V=P1/原SHA/CID/AID准确，重复完整entry相等。读取完整origin/版本/格式/原SHA分别核独立DB与原件真值。每端truth含200文字检查点、32表/152源格；正式60全文、200次table视图所有格值/跨度/定位、60original-info及60original响应全部复核，12下载原件逐字等于输入。200表视图包含按位置找表的候选窗口，不冒称200张独立源表。错项目每份均空，自己的每个非空结果恰为该ID。

独立只读DB archive为`533afd11b7e346899d4a7621ebc01d45`，device同archive，document分别为各自身ID。12产品全集观察00034/42/77/113/179/236/244/279/371/437/550/551覆盖空、每轮pending/ready、最终切换，actual=expected且行数/唯一性精确。第二轮00113后00114/123/131三旧可见row、00115-00141全文全表原件；全局00371后00372/381/389旧row与00373-00399原读取，均gate释放前，未仅核首份旧资料。

原local-trace.zip实际打开trace.trace/network/资源：437对动作、612帧DOM snapshot、139网络，零动作错误/失败HTTP。选择xmdj@158/@335，drop@591/@764；pending集合@242/@425/@676/@847，完成@320/@567/@758/@993，最终@1011/@1027各项目六正确ID。@417等真实返回轮询空集合后有界等待完整集合，未隐去这些空窗，不认连续每帧展示。内嵌测试源与绑定同SHA。sync-status两项目enabled=false/state=default_off，截图也可见默认不同步。

新行替换控制00658/00660每owner重开成功、三错CID拒绝；00029真实gate held/released正控。所有page_errors/cleanup_errors为空。

两容器ID观察器00003/00006各2正8反，身份分块00007的20反完整实到。gate仅延后真实run_pending开始，随后执行原函数，不替换解析/结果/响应。

|服务stop原件|PID|端口|exit|forced|本次复审独立socket连接|
|---|---:|---:|---:|---|---|
|00030-restart-server-stop.json.gz|35059|63615|0|false|不可达|
|00656-restart-server-stop.json.gz|35074|63624|0|false|不可达|

两个服务分别为gate正控和主网页流程，真实PID/ctime/argv/物理exe/档案/nonce均留存，正常Uvicorn关闭；stop核登记树无剩余并请求端口不可达，复审另逐端口独立连接确认。

## Hub 正式复核

证据根：`.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments`。以下八张本轮原PNG均实际view_image打开，长图展示可能缩放，摘要按原PNG核。

|原图|实际所见|原trace|
|---|---|---|
|[hub-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1-pending.png)|普通#1回执三份pending0，library瞬时为空；本图不能单独证明行和详情，见下文原trace/原子快照。|kkqa@230三行V0；截图@232空窗|
|[hub-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1.png)|普通#1三份ready1，XLSX/PDF展开、DOCX折叠。|@314三行；截图@316|
|[hub-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2-pending.png)|普通#1六行旧三ready1/新三pending0，图中详情全部折叠。|@411六行；截图@451|
|[hub-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2.png)|普通#1六份ready1，旧三及新XLSX/PDF展开，新DOCX折叠。|@559六行；截图@561|
|[hub-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1-pending.png)|全局#2三份pending0，三详情展开，pub/retry=null，latest=pending。|@668三行；截图@670|
|[hub-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1.png)|全局#2三份ready1，XLSX/PDF展开、DOCX折叠。|@740三行；截图@742|
|[hub-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2-pending.png)|全局#2六行旧三ready1/新三pending0，详情全部折叠。|@829六行；截图@865|
|[hub-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2.png)|全局#2六份ready1，旧三及新XLSX/PDF展开，新DOCX折叠。|@969六行；截图@971|

截图在原子断言之后，轮询可能再次折叠或清空；图注依实际所见，不将折叠面板当展开内容。三面板可见值依据同回合原快照与原HTTP独立比值。

|输入|文档ID|项目|真块数|原SHA256|产品row原快照编号|
|---|---|---:|---:|---|---|
|hubchooser1docx|1cbeaa578a6441158c7c922d0da449d4|1|2|e22e6a3693c66e2956105abf9d67ac165cc719f35c874465dbd0b49ee41cd325|00040, 00062, 00119, 00181|
|hubchooser1xlsx|f96e577263df480389faf7a2457b372f|1|1|22bbd71be4dd4ee4768643cf2b645b3b34986d30226bb38b7a08483a1789a56c|00042, 00070, 00128, 00182|
|hubchooser1pdf|61108a762d9747c08922ee08800ac3d0|1|1|c170e8b4b8c4165feef3cd3caf1a047e96ccdf408cd5afae2010e516736af110|00044, 00081, 00136, 00183|
|hubchooser2docx|58bc404c0a214cf2be27bbfefc4d90a9|1|1|f02990e078178bdc20e8abe0e22f7300286bebce044d67f197333cecd2b4f38a|00112, 00161|
|hubchooser2xlsx|e0efeb9093194e68a34b81f37e9ed884|1|1|5fc9ff25f6dd64d9391c76d3a3af4f2bdfc5aa1b2bf2fd6bb0063a39b1bfd280|00114, 00169|
|hubchooser2pdf|3082545eef7f4160b959ed01d420fda6|1|1|4b84e09964fc51df85c1de56cdf13212fdd09069d4e9ba2d43ee85793388d44b|00116, 00180|
|hubdrop1docx|b1a1dd96b8e94e08b74dd1b7c9650bf8|2|2|f7ea19346bf5ee43cbd5ef9103eb6e35ce4e69308d867a3fb98e4a43c3032be8|00243, 00263, 00376, 00437|
|hubdrop1xlsx|e875515ded8e4674b9690c040991dc35|2|1|37ba1336ec3363933e4d7dfe38ec7a8f116f468c642418bdc543c83041223017|00245, 00271, 00385, 00438|
|hubdrop1pdf|3719a152597d48579f483db39b41b8be|2|1|ab9459ab1022a3aaca31562977c270cb74dd55eca925bdbb688417e7fe7b8794|00247, 00282, 00393, 00439|
|hubdrop2docx|3e13ba9e39cf421295469cb744fd19c8|2|1|e5e078ce9201f86df137a6c6fac2f3096b10bdf01aa891628d61a44897c0b837|00369, 00417|
|hubdrop2xlsx|cccee16456a24771bdc74f5d847046d0|2|1|e470ebc66ed502f6e82d4cec29df77d3fc394a7ea60155991960a2d736ff3be9|00371, 00425|
|hubdrop2pdf|5f56bb5c983d42a0ab0bb0d66aa18f14|2|1|d49b7377b3c294130ab1cdbf6b6f832f8bdfe29f048528d3db41077bffab605f|00373, 00436|

12独立原件/ID，普通选择、全局drop各两轮三格式，首轮两份DOCX各超过1MiB真两块，其余一块，共14块。独立核每个browser response文件SHA/长度，从真实创建响应核ordinary/global和begin稳定项目键；逐begin项目/显示名/原长度/SHA/submission、每块序号/边界/双SHA及commit document/CID/AID。实际打开trace.network所有PUT的postData资源，14块字节与冻结输入对应段逐字相等。Hub另核HID/epoch及认证。

每份原library pending无pub/original ref,V=P0；ready单一项目/V=P1/原SHA/CID/AID准确，重复完整entry相等。读取完整origin/版本/格式/原SHA分别核独立DB与原件真值。每端truth含200文字检查点、32表/152源格；正式60全文、200次table视图所有格值/跨度/定位、60original-info及60original响应全部复核，12下载原件逐字等于输入。200表视图包含按位置找表的候选窗口，不冒称200张独立源表。错项目每份均空，自己的每个非空结果恰为该ID。

独立只读DB archive为`35b7693299234c48b4941dadfdf6c6b1`，device为本轮HID `f6d10d60f286400c99759e20c8c675b5`，epoch `1701578ad11444b48c7842149648901a`。12全集观察00038/46/82/118/184/241/249/283/375/440/553/554均完整唯一。第二轮00118后00119/128/136旧三row、00120-00146全文全表原件；全局00375后00376/385/393旧row、00377-00403原读取，均gate释放前；完整旧entry保持。

原hub-trace.zip实际打开trace.trace/network/资源：425对动作、600帧DOM snapshot、132网络，零动作错误/失败HTTP。选择kkqa@146/@329，drop@583/@746；pending集合@230/@411/@668/@829、完成@314/@559/@740/@969，最终@987/@1003各项目六正确ID。首轮chooser pending图library为空，图本身不证明三行：此前@230实际返回三个正确V0标签，原00040/42/44各connected/open且三面板完整在innerText，与pending HTTP相符。源码src/smm_hub/static/index.html:105先清空列表，108行await后重绘，与此空窗相符。证明有界观察及旧资料持续读取资格，不添加连续展开/无闪烁SLA。Hub不另声称本端执行Local同步设置。

新行替换控制00660/00662每owner重开成功、三错CID拒绝；00031真实gate held/released正控。所有/v1请求认证，page_errors/cleanup_errors为空。

两容器ID观察器00003/00006各2正8反，身份分块00007的20反完整实到。gate仅延后真实run_pending开始，随后执行原函数，不替换解析/结果/响应。

|服务stop原件|PID|端口|exit|forced|本次复审独立socket连接|
|---|---:|---:|---:|---|---|
|00032-restart-server-stop.json.gz|35577|63672|0|false|不可达|
|00658-restart-server-stop.json.gz|35580|63683|0|false|不可达|

两个服务分别为gate正控和主网页流程，真实PID/ctime/argv/物理exe/档案/nonce均留存，正常Uvicorn关闭；stop核登记树无剩余并请求端口不可达，复审另逐端口独立连接确认。

## 意见交付

两指定review-inbox/review-completion-sc1-web-row-{local,hub}-execution-v1.json分别写好即通知主Agent登记；每份仅cases.TC-008-web-native-upload，status=passed，covers仅creator-web-native-upload，reason绑定对应本轮execute原SHA。

交付前全部当前artifacts和113绑定再次核相符。结论不覆盖其他TC/平台/安装或完整E/H/X，不改写旧失败/blocked。
