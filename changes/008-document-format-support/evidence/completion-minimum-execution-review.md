独立意见脱敏副本；私有原报告SHA256：6a885afd85eefa090413352f516bcdbe4739217001156ed3e8551983236a2378

# 最低 Python 正式执行独立复审

结论：**passed**。仅适用于 AT-SMM-008 / SC11 / TC-008-minimum-installed-platform，本轮唯一认领 `minimum-installed-platform`。未运行产品、未修改源码；仅读取项目与原始证据，写入本轮意见及此报告。

## 基线与版本

已读取 AGENTS.md、changes/008-document-format-support/{intent,spec,plan}.md 和交付技能 references/execution/reviewer.md。SPEC A11/C1要求最低3.11实际依赖安装和DOCX/XLSX/原生PDF/一页真实OCR最小业务，当前自然设计将本native批限定为Mac，其他OS另验。

- 定义：.acceptance/native-v1/AT-SMM-008/definitions/000003.json，SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。当前spec SHA与定义源一致。
- 已审设计：case-design/design-completion-sc11-minimum-v3/request.json；候选复审：review/review-completion-sc11-minimum-candidate-v3/result.json。
- 本次执行：.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc11-minimum-v1/result.json，SHA256 `a7860632f19d4d259be5b7466bf1aea8b507e5bc86b58467cb83cfa2f0642709`。
- 96 bindings、361 artifacts 全部实际读取并核SHA，无缺失或差异；与已审候选的96运行绑定逐项一致。

## 原始退出与精确时长

实际打开本次 TC 下 attachments/installed-minimum/run.stdout、run.stderr、junit.xml、result.json 以及外层执行记录。stdout为 `7 passed, 1 warning in 18.85s`；JUnit为7 tests、0 errors、0 failures、0 skipped，精确18.853秒。Local业务7.930秒，Hub业务10.533秒，两个采证控制分别0.056、0.034秒。外层entry实际exit0，外层stdout/stderr空；测试的一个Starlette弃用警告与产品业务无关。未用候选调试的19.552秒替代本次正式结果。

## 独立安装、最低版本与身份

准备目录为 .acceptance-local/008/completion-20261128/minimum-mac-prep-v1/。实际打开target、prepare-commands与全部准备stdout/stderr，含hash锁定依赖sync及准确wheel安装均exit0且摘要吻合。两产品实录均Python3.11.11、Darwin/macOS15.3.1 arm64、UID501、isolated1，两个独立prefix/site-packages，不同于源码控制器3.14。

Local wheel SHA `fa6b038d35bf09cd8faed08440425bf06df463ef621244a250ed4550c89e1cc7`；Hub wheel SHA `843e34dcd478937ad6ae8ed4cf548b74693db88b3224279b2db292b2ba6c28b3`。原ZIP CRC均正确。Local47/Hub50源码资产与wheel全成员映射一致；加入METADATA后的Local48/Hub51安装文件，实录、wheel及实际安装字节逐一SHA相同。Hub wheel无smm_local包，实际隔离身份探针find_spec为None；错误SHA和PYTHONPATH源码导入负控两端均实际exit1，诊断分别为installed bytes differ及source package is not installed origin。

源码依据：tests/test_document_formats_minimum_platform.py:19–39、113–145；scripts/acceptance/document_formats_minimum.py:28–68、72–105；minimum_entry.py:14。246个原始产品命令全部由相应安装Python -I、新进程执行，源码外cwd，exit0且stderr空。

## 原件、独立真值与全部业务返回

逐原件打开16份inputs及独立truth，包括四份DOCX全部XML、四份双sheet XLSX XML、四份两页原生PDF及四份一页扫描PDF。扫描PDF全部文本层为空；实际渲染查看四页，分别为LOCALSCANALPHA/BETA及HUBSCANALPHA/BETA，第二行金额12345.67，与源定义及实际OCR文本一致。真值来自独立fixture，不来自产品输出。

逐文件重核246份原始CLI返回，而非仅依赖complete摘要：64次search（32正确命中、32其他项目负控），32次全文，64次完整全表，32次original-info，32次实际下载；另6次项目命令、2次配置、2次状态、4次add、4次refresh、4次files。两端普通/全局项目各四类材料，各端8目标唯一，全集16份，无只验证首目标情形。

全文逐源单元唯一、无遗漏重复额外文字，DOCX正文与PDF源规定顺序吻合；OCR仅空白归一后逐字一致。全表集合、全部行列格值/跨度与源真值一致，位置绑定正确。额外独立核304个单元格定位：DOCX64个部件/嵌套路径、XLSX96个sheet/A1位置、PDF144个按源页尺寸和几何计算的bbox。每份origin/document/source身份、原SHA、V/P=1、ready正确；原件信息长度/SHA/可用性及32份实际下载与原件字节完全一致。

已实际确认16份外部源路径均不存在。逐份before/after全文、表格、信息及旧reference保持相同，下载字节不变，处理版本不变；查询命中仍为相同目标。代码依据为minimum_platform.py:157–225；独立反查验证没有使用两端相等代替源真值。

## 新增采证子进程控制

原JUnit显示两项custody控制均实际执行。已打开本次temporary-location指向的持久任务目录中两个控制的collection.json、context.json、原stderr及业务失败/原件：

- test_minimum_collector_retains0：work与materials manifest均不存在，target未创建；仍保留30字节 `original preparation error\r\n\xff\x00`，含CRLF、无效UTF8、NUL，无转码。SHA256 `1c4c628dbacb5f7b1b000a06ededc9f6842de19455fec812614b3f7c01fbef9e`。
- test_minimum_collector_keeps_b0：上述stderr与业务failure.json（status=failed）、materials.json、真实控制用下载字节同时保留，没有覆盖或丢失准备日志。

两个context均精确为run_id=123、job_key=minimum-Windows、commit=40个a、artifact_name=008-minimum-Windows-123-1；这是采证控制输入，不代表Windows业务执行。collection的status实际为collected，work/manifest存在值分别false/true，未把采集成功改成业务passed。断言依据custody.py:29–52；collector.py:30–50。

## 覆盖边界

仅认Mac普通用户、已准备环境、最低Python3.11的独立安装业务和本用例明确分配项。Windows/Linux CI不属于这份执行证据，不认其他OS通过；本项不关闭完整SC11、基础无extras接收、Web/MCP/E/H/X、完整OCR质量/安全或资源矩阵，也不把来源删除等同真实源机器离线。完整三OS及E/H/X继续按各自原件与独立意见判断。
