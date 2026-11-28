本报告为独立意见的脱敏副本；私有原件SHA见 completion-acceptance-20261128.json。

# SC10 数值边界与 PDF 正式执行独立复审

验收：AT-SMM-008。目标：execute-completion-sc10-boundaries-v1。两项在各自已分配范围内均 passed；本报告不作整场景或需求通过判定。

## 证据身份与绑定

独立正式执行复审；实际读取AGENTS.md、008 intent/spec/plan、当前定义000003、已审设计v3、已登记候选复审v3，以及本次正式执行源码与原始附件。定义SHA为16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633；执行result SHA为05da6aabdc1194ff4505ac078a8332fe90a98d325627183f9507596f86295802。80个当前bindings与已审debug-v3运行绑定完全相同，80份debug source原件逐SHA与绑定相符；正式126个artifacts、两TC共119份附件和4份stdout/stderr均逐摘要匹配。设计收据SHA e202d707bb1baabb709ddbcd0e34d2b455f6f672179d49acbe9213fd1f1ed008与目标引用相符，case_obligations准确为本TC单项。复审只读原证据，没有复跑或修改产品/测试。

设计：design-completion-sc10-boundaries-v3。候选复审：review-completion-sc10-boundaries-candidate-v3（result SHA 5809d54e6ffee3a8866fec7d4ec089dd13f50c3e405cdd9d7ecf1b344b20d6c9）。本次仅写独立意见及本报告。

## 六项数值边界

本项passed，仅covers literal-numeric。SPEC B9固定默认上限、A10等于上限/+1与PLAN逐目标独立真值支持已审设计的六项组件范围。正式run.stdout原文为“6 passed, 1 warning in 1.44s”，exit_code=0，stderr空；记录起止00:57:09.697Z—00:57:11.407Z，外层1.710秒。warning为既有Starlette TestClient httpx弃用提示，无skip、失败或未到达项。tests/test_document_formats_numeric_limits.py:35–44核10000实际成员全集/展开字节与10001拒绝；:50–61核100MiB实际payload/总量及加1拒绝；:67–77核独立Unicode全文/UTF8 SHA及8MiB+1拒绝；:87–95核完整规范JSON实际16MiB及加1拒绝；:107–114核所有64个工作表名称与独立VALUE1至VALUE64、65拒绝；:124–132核200实际reader页数、201拒绝且无输出。独立读本次附件ZIP实际成员10000/10001、展开104857600/104857601字节；64/65个表名称和各独立格值完整匹配。两个gzip结果解压后规范文本8388608字节、完整JSON16777216字节，对应观察记录和SHA均符；PDF附件有200/201个实际Page对象，结合本次通过的PDFium 200页断言证明允许边界。超额拒绝由各pytest.raises实际执行证明，不把观察字段自报当拒绝证据。仅首sheet正确/重复首sheet或非首值错误分别在:107/:108/:109拦截；只有首页而自报200在:126拦截；文本/结果两边同错由:72独立真值与:89实际序列化长度拦截。不认100000非空单元、原件/来源/HTTP/暂存/任务预算、旧快照更新保护、其他OS/E/H/X或整SC10。

## 真实 PDF 预测器、对象与滤镜

本项passed，仅covers real-pdf-streams。已审设计范围由SPEC B2/B3原生内容与原件保持、B9/A10及PLAN:93–100私有中间材料/滤镜预测器保真约定支持。正式run.stdout原文为“17 passed, 1 warning in 1.13s”，exit_code=0，stderr空；记录起止00:57:11.410Z—00:57:12.772Z，外层1.362秒。17为7预测器参数+2对象结构参数+7滤镜参数+1实际reader守卫自检，参数内部各有两个源样本，全部到达。tests/test_document_formats_pdf_safety_complete.py:25–29在guard前先让真实源PDFium打开、核1页并渲染全部6点，与手写固定expected逐项相等；:31–39再核私有材料图像全部6解码字节、尺寸3×2/Filter移除与私有PDFium全部6点。本次14个guard-predictor-pixels附件全集覆盖TIFF2/PNG10–15×variant0/1；source_pixels和rendered_pixels均各自匹配独立10/20/30/40/50/60或70/80/90/100/110/120，source/private SHA分别匹配本次原件附件。不是只让源和私有两边互相相等。:53–57在纳入前由源PDFium/pdfplumber核全部源词；:63–76经公开Local API纳入、项目检索两个唯一目标、逐文件完整原文及词序/无表格错误/原件逐字下载/源字节与mtime保持。本次12份API附件均status200，两个safe-form-object-read各两份分别为ALPHA/BETA，嵌套Form含HEADER/OUTER/INNER全部顺序正确，压缩字体对象词准确；原件下载SHA与对应源附件及reader-events原SHA一致。两份reader-events各2次成功guard/2次pdfplumber实际私有路径读取，guard/read路径/私有SHA/源SHA成对相符，无rejected；纯原生文字未走PDFium符合B3。:97–102对五通用滤镜ASCIIHex/ASCII85/RunLength/LZW/Flate和两级ASCII85-LZW、ASCIIHex-Flate各两份，源PDFium先核独立ALPHA/BETA词，私有pdfplumber和PDFium再分别核同一独立词；14份real-filter-pipeline的原件/私有SHA全部匹配。tests/test_document_formats_resources.py:155–161既有实际reader探针自检本次也执行，observer/selfcheck.json可见1次完成guard、pdfium/pdfplumber各1次合法读取，5次拒绝分别覆盖两reader原件路径、内存原件及被改私有副本，实际退出/计数/guard与源SHA身份均断言。反例：源fixture和guard共同误解预测器先被guard前:29独立源点拒绝；只首variant/首像素正确被:29/:35/:39逐点拒绝；只首文件成功被:63/:66拒绝，漏INNER/错词序/错原件分别被:71/:72/:75拒绝；两个私有reader误取首key由:100对第二独立key拒绝。只认本次8bit Gray 3×2预测器、短LZW与列明滤镜/两级组合、嵌套Form与压缩对象流子域；不认其他位深、LZW宽度/EarlyChange、JBIG2、完整解码/像素超限安全、任务监督、其他OS或E/H/X，不据有限子域认整个SC10。

## 未认领范围

本次Mac隔离组件与Local API证据仅支持 literal-numeric、real-pdf-streams。100000非空单元、其他文件/来源/传输/暂存规模、完整PDF安全与资源超限、实际任务树监督、Windows Job、其他OS、普通账户独立安装、Hub服务及E/H/X保持其各自待验状态。既有其他记录的失败或缺口不由本意见改写。
