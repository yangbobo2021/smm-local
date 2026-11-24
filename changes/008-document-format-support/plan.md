# 实施计划：008 文档格式处理、结果同步与检索

状态：维护者于2026-11-24确认修订版PLAN，授权提交、创建及合并本阶段PR，并在实际合并后直接进入实现与验证。本阶段提交计划与组件研究记录，不代表产品已实现或通过正式验收。依据[已确认意图](intent.md)与[已确认SPEC](spec.md)；SPEC由[PR #41](https://github.com/yangbobo2021/smm-local/pull/41)合并，基线9d9faeed52d388f15a1d3fff92073d34c0156262。目录进度见[导航](../004-project-knowledge/README.md)。

## 阶段边界与进入条件

维护者确认PLAN后，经独立阶段PR提交、合并并读回MERGED，才进入测试实现、产品实施和正式验收。实现阶段的代码、说明、验收证据和干净上下文PR Review通过后再交维护者决定合并；本次不预先授权合并后续实现PR，不发布或升级日常安装。涉及已确认行为或必要验收变化，先回SPEC确认；模块/方案/方法调整在相应实现提交中更新本PLAN并说明原因。

使用独立008工作树、测试档案、证书、身份与服务；不改原始脏工作区，不连接日常Hub/VibeInsight、不读取用户文档、不使用家庭ESXi。006/007可复用代码和方法，旧执行不能作008通过证据；007未完成项继续单列，不因本次提交关闭。

## 确认前可行性门G0-P与当前事实

G0-P属于PLAN阶段：锁定方案、关键依赖和材料来源，以最小原型验证关键风险并如实记录环境能力。当前已完成本机原生PDF/OCR/离线材料、Flate边界及Linux/Windows能力观察；它们不等于R008通过。维护者确认本轮不做macOS系统服务权限预检；其他平台组件的最小安装/启动探测在G0-I中先于依赖该组件的业务步骤完成。完整PDF安全路径按实现阶段TDD落实，不要求PLAN阶段预先实现；研究CI原件回收单列证据待办，不作为需求/设计失败或本PLAN合并阻塞。正式E/H/X、额度和质量要求保持，改变已确认行为仍先回SPEC确认。

| 探测对象 | 本轮实际结果 | 仍缺什么/进入条件 |
|---|---|---|
| Python与原生PDF | macOS15.3.1 arm64/Python3.11.11安装固定候选依赖，完成两页原生文字、网格提取、渲染、XML实体拒绝与RSS读取，见[依赖记录](planning/dependency-feasibility.json) | 3.14及其他OS的依赖安装小样尚未执行，不能从PyPI元数据推定全部就绪 |
| 本地OCR/扫描网格 | 独立前缀Tesseract5.5.4/Leptonica1.87.0；两份无文字层的合成扫描PDF，经网格定位→OCR词框归格，chi_sim+eng/PSM3候选下逐格匹配、CER=0，见[含失败历史的记录](planning/ocr-feasibility.json) | 仅两份单页清晰小样，不替代多页/混合/复杂布局、其他OS或服务执行；字体仅用于研究，不作为产品/正式CI的默认分发材料 |
| 语言与运行材料 | eng/chi_sim实际文件与tessdata_fast4.1.0冻结提交的Git blob身份一致，记录各自SHA256；本机34个运行依赖包均按SHA256核对并完成离线重装/程序启动，见[离线材料记录](planning/offline-runtime-feasibility.json) | 其他OS完整闭包、可重新安装的材料及组件小样仍须取得，不能只冻结顶层版本号 |
| Linux/Windows身份与服务能力 | [临时CI预检](https://github.com/yangbobo2021/smm-local/actions/runs/45415550540)：Ubuntu普通UID1001的user-systemd可用；Windows独立标准用户凭据进程非管理员、session2，SCM创建配置成功，删除已尝试但无删除后查询，见[能力摘要](planning/platform-preflight.json) | Windows原生LocalService启动/OCR、普通浏览器以及3.11依赖尚未证明。Limited runneradmin任务实际仍是管理员，不能作E1客户端；普通任务路径失败、凭据进程路径成功须分别保留 |
| macOS系统服务 | 读取system domain成功，sudo -n不可用；本轮未注册服务 | 维护者明确本轮不做系统服务权限预检，不阻塞PLAN合并。后续正式H-mac仍须实际系统launchd证据，不能以foreground替代 |
| PDF增量预算 | PDFStream有界Flate原型证明单流/同页多流累计32MiB边界及+1拒绝、全文件128MiB边界及+1拒绝，见[原型记录](planning/pdf-budget-feasibility.json) | 非Flate/预测器、跨页共享对象归属及PDFium安全中间路径进入实现阶段测试/实现；在相应功能交付前完成，不能将未覆盖路径判通过 |
| 研究证据回收 | 原脚本/安装日志/样本/原JSON留在持久忽略目录.acceptance-local/008-plan-probe；公开probes与摘要可复核 | 本次CI artifact下载遇到网络失败，保留原件回收/校验待办；不因此改需求或阻塞PLAN合并，未回收前不将对应证据标完整或正式通过 |

后续分别追踪：①G0-I补对应OS的解释器/依赖/OCR最小安装和启动、正式字体/材料及身份权限；发现不兼容再调整方法，未就绪不能执行或判定相应平台业务通过；②完整PDF安全路径在实现中补齐，关键Flate风险已作最小原型；③研究原件回收只影响该份证据状态。无依赖的用例设计/共享实现可继续，不删必测格、不把未知写成成功，也不把完整业务验收前移到PLAN。

## 合并后执行准备G0-I

PLAN经确认、PR合并并读回MERGED后，才创建/续接AT-SMM-008和R008，登记确认版SPEC/PLAN及SHA，实施测试和产品。G0-I负责各平台组件最小安装/导入/OCR启动探测和候选专用部署，冻结材料/实际安装/观察器版本，建立TC设计、运行收据、独立Reviewer与证据索引。组件不兼容先修方案并更新PLAN，涉及SPEC行为变化先重新确认；正式业务验收留在实现后。

按本任务身份/目录重新确认TLS、浏览器、普通token/session和原生服务；注册临时unit/launchd/SCM、账户、任务或规则时保存前后查询，恢复准备改动。聊天不收密码，认证仅用于当次明确系统操作。正式执行前确认可接收独立Reviewer；缺少独立复审能力时保存记录并交接，不自签passed。处理、查询和服务启动均不下载OCR/data，材料从已核对离线包安装。

## 依赖与实现方案

### 固定候选依赖

| 用途 | 计划版本/方法 | 安装及验证约定 |
|---|---|---|
| DOCX/XLSX | Python zipfile + defusedxml 0.7.1；自行实现本稿明确的OOXML结构读取 | 有界流式读取真实成员、关系和内容类型，拒绝实体/宏/外部关系跟随；直接保留公式与缓存两份数据，不调用Office或公式引擎 |
| 原生PDF | pdfplumber 0.11.11、pdfminer.six 20260107 | 创建端worker取字符/几何和网格，不把库默认extract_text等同于全SPEC覆盖 |
| 页面渲染 | pypdfium2 5.15.2、Pillow 13.0.0 | 非V8/XFA构建；只在受监督worker处理，先查尺寸/展开预算，实际动态库和轮子SHA纳入材料 |
| 进程监督 | psutil 7.2.2 + Python标准库；Windows Job Object用ctypes | 统计任务树RSS/临时空间与单调时钟，不能只监控Tesseract PID；各OS实际终止/回收另验 |
| 合成样本生成 | reportlab 5.1.0，仅测试/验收依赖 | OOXML由独立ZIP/XML生成器构造；冻结中英字体、真值与生成器，不从待测解析结果生成预期 |
| OCR运行时 | Tesseract5.5.4/Leptonica1.87.0；本轮实际采用conda-forge的独立前缀发行 | 本机包/完整依赖闭包及SHA作为已实测候选；其他OS须分别冻结并实测。vcpkg基线2f8bf7a5bad48aaef99d80b221fca712f016ab8f仅保留替代构建研究，不把端口元数据当已安装结果；切换发行/构建必须更新PLAN并重做组件核对 |
| OCR数据 | tessdata_fast 4.1.0，提交65727574dfcd264acbb0c3e07860e4e9e9b22185，仅eng/chi_sim | 验证发布归档及实际两个文件SHA，解包到任务目录，处理尊重配置的语言顺序，数据不随查询/启动下载 |

直接依赖固定上述版本；实现时将本轮可行性环境解析到的cffi2.1.1、charset-normalizer3.5.3、cryptography50.0.2、pycparser3.12等传递依赖一并锁入按Python/平台校验的含hash安装清单，不只写宽松下限。macOS3.11安装成功不替代其他平台。两独立包各增加documents可选组，基础包不得强制装处理依赖；测试生成器不进入运行组。语言顺序比较保留全部失败记录：eng+chi_sim下第二份小样CER约8.33%，候选chi_sim+eng/PSM3在两份小样均为0；PLAN提出后者作为受控中英验收profile，仍需随PLAN确认。SPEC示例eng+chi_sim仍是合法输入，产品不能暗中换序；不同配置必须记录真实profile。无需引入NumPy/OpenCV或外部模型；扫描网格布局以Pillow二值化、线段/交点和闭合单元格检测实现，若达不到SPEC质量则修实现或回SPEC，不隐式加模型或缩小支持。

运行材料包含发行来源、实际架构、所有包/程序/DLL/dylib/so的版本/SHA、语言文件及许可。conda仅是本轮研究和验收材料准备工具，不进入SMM基础包依赖，也不由产品在处理时调用；普通用户仍可配置兼容本地OCR的绝对路径。若采用源码替代，另冻结编译器/CMake/vcpkg基线、triplet与源档。G0-P先完成离线安装小样，G0-I复用已验证材料，不在运行时访问包管理器。研究来源：[PDF库](https://github.com/jsvine/pdfplumber)、[PDFium接口](https://pypdfium2.readthedocs.io/en/stable/)、[公式缓存](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-formulas)、[OCR构建](https://tesseract-ocr.github.io/tessdoc/Compiling.html)、[冻结OCR端口](https://github.com/microsoft/vcpkg/blob/2f8bf7a5bad48aaef99d80b221fca712f016ab8f/ports/tesseract/vcpkg.json)、[语言数据](https://github.com/tesseract-ocr/tessdata_fast/releases/tag/4.1.0)。上游资料不是本项目验收证据。

### 修改位置与数据流

| 位置（新文件为拟名） | 修改职责及约束 |
|---|---|
| src/smm_local/documents.py、managed_documents.py、core.py | 保留旧文本/项目/来源语义；新增受控原件采集和来源授权、失败项管理、candidate/published分离、CID/AID及版本事务。明确refresh才开外部路径，快照读取不回源 |
| 新增document_snapshots.py、document_results.py | 不可变原件/规范结果存储、完整清单与schema、SHA/尺寸/定位校验、短事务原子发布；失败候选与已发布资料分离，额度预留和孤立文件回收不撤掉合法引用 |
| 新增document_processing.py、document_worker.py、document_formats/ | 配置CAS、单任务调度、所有格式读取/布局/OCR在worker内；标准库纯结果接收不导入这些可选处理库。DOCX部件/嵌套/修订、XLSX所有实际单元格/缓存/日期、PDF原生/混合/扫描分别实现 |
| 新增document_supervisor.py及平台实现 | 每档案跨进程唯一处理槽位，任务树1GiB、临时256MiB、总300秒及PDF各子预算；独立监督、心跳/租约/终态恢复；Win Job Object纳入worker后才允许其加载解析器，POSIX独立进程组含OCR子进程，监督退出/父进程停止也回收任务树 |
| src/smm_local/service.py、api.py及Hub lifespan | Web明确提交后后台执行，重启仅续办本端合法已捕获任务；CLI refresh/reprocess可同步等待并报告真实终态。Hub服务已运行时，CLI仍独自采集外部路径、将合法原件交同state服务worker处理并等待；无服务的明确CLI动作才使用前景调度。按需服务有活跃任务时保持生命周期；已运行创建端服务负责其队列，CLI可入队并同步等结果，独立CLI无服务时才启动自己的受监督执行器，跨进程槽位防重；MCP、纯查询及接收投影不得创建处理任务。处理不持DB/控制锁 |
| document_protocol.py、document_sync.py、src/smm_hub/documents.py、document_api.py | processed_documents_v1能力与接收schema协商、成套原件/结果分块及原子来源发布、幂等/代次/回执；旧TXT协议独立兼容，禁止接收分支进入原件处理器 |
| document_search.py、references.py、Hub读逻辑 | 扩展processing_version与双摘要去重/精确路由；旧引用验证分支保留，新增文档定位/table_context/header_context、表格命中默认窗口、原件信息/附件流；所有读取核当次连续资格 |
| Local cli.py/api.py/mcp_server.py、Hub document_cli.py/document_api.py | 完成SPEC全部新参数/输入取得、状态/配置/reprocess、分块上传和流式原件。MCP只text/table/original-info，无Hub独立MCP，无写盘/管理工具 |
| 两端static/index.html | 新格式选择/拖入、阶段与失败候选详情、当前比较值、只在创建端管理；表格定位/上下文/窗口、原件下载、依赖配置指引；文本安全渲染，凭据仍仅内存同源头 |
| src/smm_hub/_archive.py、scripts/build_packages.py、两份pyproject与锁文件 | 新增共享模块/vendor目录全部进入Hub自身命名空间，轮子不能靠源码smm_local泄漏导入；基础包接收、完整创建端分别安装验证 |
| tests/test_document_formats_*.py及fixtures | 下述稳定TC分组，独立原件/结构/状态预期、红灯、真实并发屏障和原始HTTP；保留既有006/007、对话/VibeInsight兼容测试 |
| scripts/acceptance/document_formats_*.py、.github/workflows/document-formats-acceptance.yml | 新增008专用准备、E/H/X及证据核对入口，继承已有方法但不用007状态/记录；共享生成器与观察器不能兼任独立预期 |
| README.md、TRIAL_GUIDE.md、skills/smm-search/SKILL.md、scripts/acceptance/README.md | 从安装/配置到项目纳入、同步、检索、表格/原件及失败重试的完整说明；旧层级CLI帮助同步修改，不只补叶子命令 |

迁移只补字段和表，不处理/上传资料；旧文本的version、资格及引用保持。新格式首次成功发布V/P=1，失败尝试只占CID/AID，不预先推进版本；source授权与检索资格分开，重试成功不能复活旧引用。路径refresh另用source_batch_id冻结枚举全集、source revision及顺序。先核候选/原字节预算，再在监督任务中取得各结果；完整核来源结果累计预算后才原子发布该来源的新成员/资格清单，不让前几个文件先冒称来源完成。单文件处理失败可形成partial；枚举/来源总量失败则整源失败，其他连续来源仍独立有效，不能因枚举顺序不同保留不同子集。单文件reprocess只核该CID的连续采集授权、当前AID/已发布版本、单文件结果及任务/暂存预算，不重新核算整来源历史累计量，也不要求额外refresh；已因非法/超预算采集而无授权的候选，不能借reprocess取得授权。其他来源推进的共享文件版本不按旧来源计费截断。

路径refresh另以source_batch_id冻结完整候选集合及配置/请求顺序：先核原字节累计量，处理后核完整结果累计量，再原子发布该来源的成员/资格/计数。单文件失败可形成如实partial；枚举或整源累计预算失败不发布前N份伪完整清单，按006撤销该来源旧资格，保留其他连续来源。来源批次结果未完成时仍按批次规则发布；对已经合法采集的单文件显式重处理，不把来源级refresh预算变成新的限制。文件/结果先写私有暂存并fsync，发布事务只核当前CID/AID/config/授权/顺序及绑定，提交后回收无引用文件；硬杀/回滚可恢复，不让FTS或清单先于整套原件/结果可用。

扫描PDF先找网格/闭合单元格，再对适当页/区域OCR并用词框归属单元格，不逐格无界起进程。原生文字/表格区与扫描区建立覆盖掩码，原生页OCR零调用，混合页只补缺失区。规范文本按确定顺序生成一次，正文与表格结构共享定位映射，不重复拼接同一段；search附加表头上下文不能改变text的Unicode区间。检测不到可支持网格就明确不完整，不把TSV行名当表格结构。

POSIX监督至少每100ms检查任务树/单调时间及任务目录实际字节，以进程组和已登记后代处理退出/重父化；任何持久PID记录都须同时核创建时间、任务身份及租约，不能只凭复用PID杀其他进程；执行终止前核PID、创建时间、任务token/租约及程序身份，不按过期PID记录误杀重用PID的其他进程；Windows Job Object禁止breakaway，配合RSS观察和整Job终止。访问拒绝/观察盲区时停止该尝试并报监督不可用，不继续无监督处理。完整OOM/预算实验在隔离档案串行运行，保存实际树与终止证据，不通过调低生产预算冒充1GiB实测。按SPEC实证5秒终态/槽位恢复及主服务查询存活；各OS不宣称同种内核硬限制。[Windows进程组约束](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。

### PDF有界解码的接入位置与确认门

不能直接调用库默认PDFStream.decode后再量结果。创建端worker在创建PDFParser/PDFDocument之前安装本任务受控stream工厂/解码器，覆盖普通、对象、xref及页资源中的get_data路径；只在该worker命名空间内生效，版本/接入点不匹配则报告guard_unavailable，不退回库默认批量解压。接入覆盖的调用轨迹、组件SHA与反例归入确认前原型和后续TC-008-budgets。

- Flate使用decompressobj和有上限输出块；输出块最多64KiB，最多请求剩余额度+1字节用于识别超额，超额字节不加入保存结果。原型已实际核32MiB相等/+1、同页多个流合计及128MiB全局合计，见[原型记录](planning/pdf-budget-feasibility.json)；这不是对其他滤镜或SMM路径的通过证明。
- ASCII85/Hex、LZW、RunLength、滤镜链和预测器须经相同有界sink，不调用无上限辅助函数；对象/代次、压缩链层级、循环引用及跨页共享资源有明确计数。文档元结构先计全局；页树确定后，在读取页内容/Form资源前建立页归属并增量累计，不能用“每流32MiB”冒充“每页32MiB”。缓存不重解码，实际重复解码不能逃过总量。
- PDFium是独立原生解码路径，不能因pdfminer有guard便直接加载用户原件。拟由guard取得完整校验对象图后，生成仅用于处理的私有中间PDF：通用流为有界解码结果，去除相应Filter并重算Length/交叉引用；光栅图像先核宽高/像素及已预留的解码字节，再转为受控图像流。原件不改写，始终按原SHA下载。只允许PDFium加载已验证中间材料；材料超过任务临时额度则失败，不回退加载原件。
- 实现阶段先以独立用例验证普通内容流/对象流、滤镜链/预测器、同页多流/跨页共享、图像尺寸与中间材料的文本/表格/定位保真及超限前拒绝，再接入对应产品路径。PLAN阶段已完成Flate关键风险原型；其他部分是待实施范围，不是要求提前交付的完整安全实现。中间序列化/编码支持不足时补方法并重做探测，不能在PLAN自行新增对SPEC目标文件的排除项；必须改变支持面时先回SPEC确认。

## 实施顺序与通过门

1. 前置门与需求登记：确认G0-P的方案/最小风险证据与未完成项归属后提交PLAN PR；实际合并后立即执行G0-I、创建/续接AT-SMM-008，登记R008的确认版SPEC原文及SHA，按A1–A12建立TC设计并独立复审，然后进入相应测试/产品改动。
2. 先测试与红灯：按下表将TC落到现有公共入口，新增行为缺失应产生业务断言失败，不能以import不存在的新模块冒充红灯；旧文本/对话测试先取兼容基线。测试或预期有错先修测试并重新跑旧产品红灯；由独立Reviewer核自然语言设计、实际断言与原产品红灯，确认确属业务缺失后才改产品，绿灯再独立核同版结果。按实际需修订意见再追加返修/复审，不预先登记通过或循环次数。
3. 先实现无解析依赖的骨架：结果schema、原件/候选/尝试/授权表、配置、版本/资格/引用、迁移及原子发布；再实现任务调度/监督。先验首次失败和旧发布/失败新CID并存的状态机，避免后续解析与上传各自发明版本。
4. 实现创建端格式处理：先DOCX/XLSX，再原生PDF文字/网格，再扫描网格/本地OCR/混合页；每步取得固定真值绿灯与对应错误/预算分支。质量未达标不把ready改成“看起来成功”。
5. 实现原件/结果同步：独立基础Hub只验证/保存/建索引，完成协商/分块/来源完整发布、暂停撤回/幂等回执/重启。用禁止处理入口探针及真实无依赖环境证明零解析；随后加入重叠来源和控制并发屏障。
6. 接入检索和所有入口：先准确text/table/original-info/原件路由，再CLI、HTTP、Web、Local MCP及后台恢复；完成表格后半命中默认窗口/上下文，旧引用、新CID/AID比较值和失败管理。并行意义上的独立资料可共用同一轮包，但不省任何入口。
7. 文档、回归和独立包：按用户路径更新说明/各层帮助/Skill；执行适用及全量pytest、双轮子构建、单独安装/元数据/全模块与静态资产摘要验证。创建可追溯实现候选提交与草稿PR后做正式验收。
8. 同版E/H/X正式执行与复审：固定候选与探针，逐下表执行，记录每轮独立正式意见和失败历史；不同阶段的独立Reviewer核设计与执行，当前主Agent不能自签通过。若改产品/观察器，确定受影响格、重新构建同版证据，不沿用不相容旧包。
9. 收尾：逐A1–A12形成R008判定、逐环境完整结果与可打开原件；干净上下文按当前PR Review Prompt审查最终diff、用户使用入口与证据，结论写入实现PR。必需格未完成则交付未完成及阻塞，不自降验收。维护者确认实现PR后才合并，未获后续发布授权不发布。

## TC与SPEC验收对应

以下是用例设计目标，不是已实现/已通过清单；具体原始数据、动作前状态、断言、执行记录分别归入同一稳定TC。每个TC的多文件/多单元必须先核独立全集/唯一性，再逐项核对，不以两个产品输出相等代替真值。

| SPEC / 稳定TC | 操作与通过条件 | 必需执行范围 |
|---|---|---|
| A1；TC-008-ownership | 两端空档案创建普通/全局项目，路径add pending→refresh及网页选/拖入。另一端/投影管理、旧项目键/HID/epoch/P/CID/AID逐项拒绝，配当前正控，完整状态不变 | C1；E1各格两端；H1/H2各格 |
| B4/A1/A5；TC-008-processing-config | status取得revision，绝对程序/数据路径配置持久化；旧revision/坏路径/缺语言失败不改好配置，交互check不假称服务ready；新配置使旧任务不能发布 | C1；E1配置/重启；H1/H4真实身份 |
| A2；TC-008-docx | 两份以上DOCX：多段落/表格/嵌套/合并、页眉页脚脚注尾注/修订与排除对象。全部部件/格值/跨度/文本区间与独立清单一致，不虚造页码，不重复嵌套文字 | C1完整；E1每格；H1/H3每格一种 |
| A3；TC-008-xlsx | 多文件/多sheet，hidden/veryHidden/行列隐藏、合并、shared/inline文字、类型/日期制、公式有/无缓存；按真实稀疏坐标逐一核值/公式/缓存状态，巨大空维度不扫描，外链不执行 | C1完整；E1每格；H1/H3每格一种 |
| A4；TC-008-pdf-native | 多页/两表/两文件；非首页锚点、旋转归一框、原生页禁OCR仍成功；原生页眉+扫描正文必须识别缺失区、不重复。无边框/合并/跨页负例明确不完整 | C1含负例；E1每格；H1/H3原生路径 |
| A5；TC-008-pdf-ocr | 两份以上中英清晰印刷扫描、多页网格及混合；先冻结独立真值，按SPEC白名单归一计算CER≤1%，关键锚点/金额逐项精确、结构逐格正确。原SHA不变，方法/框/覆盖真实；模糊/复杂负例不冒称完整 | C1质量；E1三OS真实OCR；H1/H4每格真实OCR |
| A6；TC-008-direct-index | 两本机身份，同名同字节独立；允许者成套同步，禁止者正文/原件/清单不外发。禁止所有解析/渲染/OCR/模型入口仍搜索/读表/下载，源端离线及路径不可见仍正确；partial不被改ready | C1；E1/H2每格；X1全部方向无处理依赖 |
| A7；TC-008-bundle-retry | 真实HTTP分块：边界、断开、少/多块、坏SHA、交叉绑定、同提交异载荷、丢回执、重启/重复commit/清单。完整前不可查询或下载，补齐一次发布，不增文档；旧回执不清新任务 | C1全组合；E1/H3/X1指定重启重试 |
| A7；TC-008-concurrency | 真实事务/线程/多进程屏障使旧CID/AID/config/来源顺序/授权代次晚到；旧发布不覆盖新版本、不复活已移除资格，网络/解析期间其他控制与数据库事务能完成 | C1完整；三OS适用回归 |
| A8；TC-008-first-failure | 首次缺OCR，published=null且V/P=0，失败项可管理、retry_target正确；配置恢复后只读保存CID字节成功。旧CID/AID、删来源、换候选、同请求重放均不能误重试或并行 | C1；E1与H4每格 |
| A8；TC-008-replacement | v1已发布→v2捕获失败，两份独立资料/负控不变；展示两状态，重试只处理v2，成功前v1原资格可用，成功后旧ref拒绝。路径变更处理失败撤销旧来源资格，恢复后新资格不复活旧ref | C1；E1每格，H4对应恢复 |
| A8；TC-008-lifecycle | ready/partial两前状态各验新原件/同字节/新profile、暂停/删除/失败/离线待确认/重连/恢复；共享另一个连续来源可保留，最后授权失效才取消。另一允许项目可推进共享当前版本，不形成暂停分支 | C1完整；E1三格式生命周期；H3持久 |
| B5/B9/A8；TC-008-budget-domains | S1合法refresh结果累计127MiB，合法CID的单文件重处理新增2MiB但仍在单文件/任务限额内：操作成功，不要求refresh，其他成员资格/ref保持；F仅处理版本变化。随后明确整源refresh累计129MiB则按来源预算失败。另由S2推进共享版本，不能以S1旧计费截掉合法成员；无采集授权的超预算候选不能借reprocess取得资格 | C1独立定长结果/真值与来源资格检查，不引入额外三OS全量重复 |
| B5/B9；TC-008-budget-domains | 来源最近合法refresh结果127MiB，重处理其中一份、结果增加2MiB且单份/任务预算仍合法时成功，不要求refresh、不撤销其他文件资格；对新一次refresh的129MiB结果则整来源失败。再由S2推进共享文件，S1不能因旧计费累计量截掉有效成员；无合法采集授权的候选重试拒绝 | C1独立累计预期及共享来源，不能只比较结果数量 |
| A9；TC-008-table-context | 第243行及第10列之后、非首表/隐藏表命中，默认窗口含命中且表头/首内容行角色正确；多段命中不伪装全覆盖。上下文与窗口合计额度、超大单格/表头明确错误，text偏移不因附加上下文改变 | C1完整；E1每格；H/X逐份正确读表 |
| A9；TC-008-reference-read | Local/Hub/合并ref逐字段篡改与合法另一文档/表ID、Unicode/LF/非BMP、过期P及资格；真实text/table/原件信息和流逐字/SHA核对，查询不回源；重建索引/正常重启保留有效ref | C1完整；E1/H3/X1按入口逐份 |
| B7/A9；TC-008-empty-original | 合法空白DOCX、全空XLSX、空白PDF分别得到empty-success、完整覆盖和保存原件；正文查询无命中仍从files/library取得original_reference，经CLI/Web/API下载核原SHA，Local MCP核信息后交同一ref下载。重启旧原件ref可读；配坏文件、OCR缺失/无识别文字负控，不能冒充空白成功，不能只按零命中判成功 | C1三格式完整；E1每格至少空白PDF的列表→原件主路径，其他纯状态分支复用C1 |
| A9；TC-008-scope-network | 普通/全局、对话C关联文档D、D关联E的一层与负控，两端同范围及本机重排；Hub离线/无新能力明确覆盖。允许既有Hub通信，私有正文/候选/文件清单及外部识别/下载调用为0 | C1；E1完整主路径 |
| A10；TC-008-budgets | 每项规模等于上限/+1与混合来源顺序无关；小PDF大解压流/巨大图像尺寸、原生解析/OCR超时、任务树RSS/临时空间/队列预留/并发唯一槽位实际测。失败/partial符合B3/B9，5秒终态回收、其他资料检索/原件可用 | C1所有预算；E1/H4每格三种监督已建立及一项真实异常恢复 |
| A10；TC-008-hostile-input | 真实改后缀/损坏/加密/宏、ZIP路径/外部实体/畸形关系、链接/junction、更新中变化、权限拒绝/越界下载；原字节/mtime、其他资料和外部路径不变 | C1完整；E1三OS路径权限；H真实身份 |
| A11；TC-008-legacy | 旧档案迁移后对话/VibeInsight/005及006/007文本/旧ref/同步保护不变，不自动扫描或授权；旧原件not_captured不假造字节；迁移中断回滚可诊断恢复 | C1既有兼容基线与回归；三OS普通CI |
| A11；TC-008-packages | 两基础包分别安装，Hub无smm_local；创建端documents组/最低Python三OS最小DOCX/XLSX/nativePDF/真实OCR；无额外依赖接收端通过X1，全部新模块/资产源码→wheel→安装摘要一致 | C1构建；最低Python三格；E1/X1 |
| A11；TC-008-discovery（人工） | 普通用户/Agent/Hub维护者从README→安装→OCR配置/状态→创建项目/纳入→检索→表格/原件→失败目标重试。逐跳真实CLI/Web/stdio回放，保存画面/输入来源/完成状态；各层帮助、同步默认关闭/共享暂停边界可见 | E1各平台适用入口；复杂导航/陈旧页面反例可集中一真实浏览器 |
| B7/A1；TC-008-stale-web | 两端真实浏览器各打开v1/P1页面并冻结其所见比较值；另一CLI/页面重处理成P2，或创建失败新候选CID2/AID2。旧页不刷新而实际更新/删除，捕获真实请求仍带所见旧P/CID/AID（未显示候选时不得提交前补抓新候选）。后端拒绝、页面显示过期，独立读取完整新状态/原件不变；刷新后以新值提交为正控。保存前后DOM/画面及请求/响应，不用手工API负控代替网页路径 | 一套实际浏览器集中完整验证Local/Hub两端；E1其余OS复用正常用户路径，不机械重复故障组合 |
| A12；TC-008-e1-{mac,linux,win}（人工主路径） | 按下节E流程完成，不只启动；实际身份/组件/所有文件集合/各入口/更新与旧引用/重启后的文本表格原件一并复核 | 三格全部 |
| A12；TC-008-h-{mac,linux,win}（人工服务） | 下节H1–H5全部，当前服务真实身份+OCR子进程、缺依赖恢复、旧ref精确读取及清理后查询 | 三格全部 |
| A12；TC-008-x-{origin}-{target} | 下节六方向，实际源OS产物在无处理依赖目标Hub通过认证协议接收、保真、故障和重启；不造platform字段或直写DB | 六方向全部 |

## 平台执行步骤及证据

### C1与包门

源码阶段运行pytest适用组及全量回归；安装依赖组的测试不得靠skip变绿。分别运行python3 scripts/build_packages.py，在两个新venv中各只安装对应wheel，并核所有模块/资源和METADATA；另建仅基础Hub环境供X1。新增document-formats-acceptance.yml，将3.11最小业务、3.14完整E1、三OS服务、三个producer及六个receiver作为独立可读job/阶段，不混在旧007模式。

预备新增document_formats_fixture.py（独立真值与负控）、document_formats_prepare.py（环境/包/身份/任务状态）、document_formats_platform.py（E1）、document_formats_service.py（H）、document_formats_exchange.py（X）、document_formats_verify_evidence.py（逐SPEC核完整性）。命令契约由这些脚本的--help暴露，统一接收--target-config、--work、--output及明确阶段；这些是待实现探针，不冒称当前已有命令。CI使用固定uv版本0.13.8及固定浏览器/编译器材料，源码cwd外运行产品，不借PYTHONPATH源码。

最小Python门在macOS/Linux/Windows各用3.11安装全部创建依赖，实际采集一个DOCX、XLSX、原生PDF及一页扫描PDF，再查询/读回，保存业务和组件/身份，不只有pip/import。共享恶意输入、完整并发及全部预算在一个隔离开发平台穷举；各OS进程监督/路径/身份风险仍在E/H实际证明，不用平台字符串模拟。

### 实施后采用的复跑命令

以下新探针/测试文件是本PLAN要求实现的命令契约，当前不能当作已有可执行入口。prepare根据本次wheel、实际OCR材料、身份与专用目录生成target.json；该文件包含私有连接位置，不公开。E/H/X每轮都用新输出目录，不复用旧passed。

```text
uv sync --extra test --extra documents --extra acceptance
uv run python -m pytest -q tests/test_document_formats_contracts.py tests/test_document_formats_parsers.py tests/test_document_formats_resources.py
uv run python -m pytest -q
uv run python scripts/build_packages.py
uv run python scripts/acceptance/document_formats_prepare.py probe --work <任务根> --output <准备收据>
uv run python scripts/acceptance/document_formats_prepare.py prepare --local-wheel <Local轮子> --hub-wheel <Hub轮子> --ocr-manifest <G0-P材料清单> --work <任务根> --output <准备收据>
uv run python scripts/acceptance/document_formats_platform.py --target-config <任务根/target.json> --work <E任务根> --output <E原始证据>
uv run python scripts/acceptance/document_formats_service.py --target-config <任务根/target.json> --work <H任务根> --output <H原始证据>
uv run python scripts/acceptance/document_formats_exchange.py produce --target-config <任务根/target.json> --work <源任务根> --output <源产物>
uv run python scripts/acceptance/document_formats_exchange.py receive --target-config <无处理依赖Hub配置> --input <真实源OS产物> --work <目标任务根> --output <X原始证据>
uv run python scripts/acceptance/document_formats_verify_evidence.py --manifest <本轮证据索引> --output <逐A与平台覆盖报告>
```

上述占位值由prepare输出或操作者明确指定，脚本负责跨OS路径，不依赖shell通配符。配置冻结后，实际创建端CLI回放至少包括documents processing-status --check、processing-configure、明确refresh、search→read，以及reprocess --document-id ID --capture-id CID --expected-attempt-id AID --expected-version V --expected-processing-version P；R来自status，ID/CID/AID/V/P来自失败详情retry_target，不按发布版猜新原件。产品命令前缀按SPEC分别使用smm --db <档案>或smm-hub hub --state-dir <既有任务服务目录>；不使用日常默认档案。

### E1三平台共同流程

每格以两份独立Local身份及独立foreground Hub、普通账户和合成库执行SPEC E1；Local CLI/Web/stdio与Hub CLI/Web/HTTP严格按SPEC入口表分工。Mac用当前普通UID或托管普通UID，Linux用非root UID，Windows用另建标准账户的实际交互token/session。保存真实PID/父PID/token/session、argv/cwd及安装模块，不只取管理员控制器whoami。

1. 从README准备独立包、冻结OCR/data，创建普通/全局及同名负控；status→CAS configure→add pending→明确refresh。两端各含至少两DOCX、两XLSX及原生/扫描/混合多页PDF。
2. 每种格式分别真实选择与拖入，不以设置input.files一项冒充两种交互；从返回的当前项目/文档状态取得版本、CID/AID。逐资料按项目命中、读text/table、核定位/隐藏/公式缓存；表格后半/后列命中默认窗口及header_context正确。
3. CLI、Web、Local真实stdio分别用自己搜索返回的ref读取。MCP只核text/table/original-info，并将同一ref交Local CLI/认证API下载；Hub无独立stdio。原件每份实际下载核原SHA，不以metadata SHA一致冒充字节正确。
4. 设置文档D与只含对话C一层关联及第二层负控；一项目默认不允许、一项目允许。允许者成套同步，接收阶段禁处理入口并观测0；源文件路径不可见/源端停止后Hub仍可查表/读原件。恢复创建端处理条件后继续更新，不在同一Hub卸依赖又要求它处理自有新文件。
5. 合法空白PDF在零正文命中下，仍通过列表original_reference读原件；再验证三格式分别更新/旧ref拒绝/第二份资料不变；首次无OCR失败V/P=0、旧发布/失败新CID并存后重试，partial与暂停/撤回/离线待确认及重连准确。捕获后使外部路径不可用，再重试仍只用缓存，失去最后采集授权时明确拒绝。
6. 实际停止Local和Hub，在无待处理任务时以固定state、OCR绝对路径、非交互PATH/非源码cwd重启；逐份网页资料及CLI来源重新项目检索、用各入口原有有效ref读text/table/信息/原件。查询/启动不打开外部源或OCR；新引用验证不能替代旧引用持久性。
7. 每OS核三种监督已建立，实际触发一次任务超限或worker异常，记录树终止/5秒槽位恢复、另一资料查询/原件及后续合法任务成功。最后实际核PID/子进程/端口退出，保留失败记录及原件，不操作日常进程。

### H三类原生服务

| 环境 | 实际部署与身份步骤 | 必须补的证据 |
|---|---|---|
| H-mac | 优先独立macos-15 CI runner；使用现有系统级launchd安装路径、安装者UserName及专用state/label。实际bootstrap/bootout/停启，普通浏览器与Local访问 | 系统domain/label/ProgramArguments、服务PID/UID及OCR子进程UID；不是同UIDforeground替代。CI不可用才安排本机认证，不复用007例外 |
| H-linux | Ubuntu24.04实际user-systemd；必要linger/user manager准备只作用临时runner/身份，独立unit/state。使用实际unit环境停启 | unit/MainPID/UID、user manager、运行环境与OCR子进程；容器后台普通进程不算。清理原linger等准备改动 |
| H-win | Windows2022 SCM/LocalService，独立标准账户Local/浏览器；管理员仅部署/配置私有state、程序/语言目录ACL | SCM配置/StartName、PID、SID S-1-5-19/session0及OCR树；标准客户端真实非管理员token/session，直接读Hub state/raw实际拒绝；程序/data可执行/可读、任务tmp可写 |

每格H1–H5步骤都执行：H1服务所在state配置；Hub CLI采一份路径资料，普通网页在服务新建项目上传DOCX/XLSX/nativePDF/scanPDF，服务实际完成处理并逐份查询/读表/下载。H2再由普通Local同步已处理扫描PDF，服务调用数0且只能由创建端管理。H3真实停启后查回H1全部网页四类、CLI资料和H2投影，所有旧text/table/信息ref与原件字节正确；OCR进行中另停启，按同CID/AID缓存恢复，移除/换版旧任务不复活且无游离进程。H4在任务私有组件目录构造缺语言/不可执行，记录服务真实错误，其他原生与接收资料仍可读；恢复后按retry_target完成首次失败及替换失败的正确原件重试，再验一项真实worker超限/异常及后续任务恢复。H5保存移除前后真实注册/配置/防火墙规则、进程树和端口查询，服务不再注册或可启动，不能只看exit0。客户端MCP分工仍遵守E1表。

### X1六方向与CI产物流

macOS→Linux、macOS→Windows、Linux→macOS、Linux→Windows、Windows→macOS、Windows→Linux全部执行。producer在实际源OS用本候选创建端组件取得DOCX/XLSX/nativePDF/OCRPDF的合法原件/结果，输出不含token的manifest、版本/profile、原SHA/结果SHA和完整结构清单；OCR结果允许因OS不同而不同，冻结实际源结果作保真期望。

每个target新建只安装基础Hub的隔离环境，确认处理库不可import、OCR/data不可用，阻断处理入口并记录调用0；通过实际认证HTTPS、项目授权、原件/结果stage/publish输入接收，不直写DB。逐文件核独立源集合、文本字节、全部表/页/单元格/覆盖及原件下载SHA，再做丢回执重传、接收进程重启、少原件块不可读→补齐可读及源创建端停止后读取。授权/签名上下文按新目标合法建立，不改原件/结果内容或绕过校验。

CI用上传/下载artifact传实际producer产物，再在目标OS本机HTTPS调用合法协议；这证明跨OS结果可消费，不宣称两台物理机器已联网。008不另新增物理跨机强制格的依据沿SPEC D2；若实施改变TLS/认证/绑定/网络相关OS行为，先回SPEC重评，不能在PLAN自我豁免。所有receive格下载实际raw/结果，只有文本摘要对比不够。

## 证据、复跑与交付判定

每次执行输出独立run目录，保存候选提交、SPEC/PLAN/探针SHA、wheel及所有安装模块/资产SHA、实际OS/Python/身份/session/服务、OCR程序/依赖/语言/font摘要、真值与样本原SHA、源字节/mtime前后、请求响应/退出码、CID/AID/config/版本/资格、完整文件/单元集合、真实下载字节、监督记录、重启前后旧ref读回和清理查询。原始浏览器trace、PNG及对应真实请求都须实际可打开；不能只存测试截图或step名字。

本地原件保存在持久工作树.acceptance-local/008下；公开脱敏件进changes/008-document-format-support/evidence/，记录原SHA/公开SHA及删改规则。证据状态独立记录generated、uploaded、recovered_verified、reviewed；业务job success不推进后续状态。

- 控制端在启动正式CI前持久保存私钥并用小样验证解密；runner只得到公钥。业务job的always收尾先完成H5清理并留结果，再加密/上传包括失败记录的原始证据和manifest，保留run/job/artifact ID、实际摘要及保留期限。上传失败/取消导致证据不完整则该格证据未完成，后续无法复原的正式步骤须重跑，不重造passed。
- 区分托管runner自动销毁与持久artifact/中转证据删除。runner可以在上传结果已记录且持久artifact可回收、私钥已事先验证的条件下结束，不要求它等待尚不存在的外部人工确认协议。控制端随后按artifact ID下载、校验归档与逐文件SHA、解密并实际打开关键trace/原件，写recovered_verified回执；本地run清单必须收到该回执后才可给Reviewer和形成通过结论。
- 持久artifact、中转副本和私钥不得在收到回收核验回执前主动删除；正式复审前检查剩余保留期，不足则先完成持久复制。失败下载可在保留期内重试；缺钥/坏hash/解密失败保留原错误、暂停passed，不假称业务失败也不拿摘要代替原件。回收脚本/证据核对脚本分别拥有下载与校验职责，二者以run/job/artifact与manifest摘要匹配，不凭文件名配对。
- 在TC-008-evidence-recovery中演练上传失败、控制端离线后恢复、错误密钥、损坏包/摘要、缺清理记录和过期不可回收，预期分别为证据未完成/需重跑；成功分支实际得到持久回执并可打开原件。先做不依赖产品的小样演练，再接正式E/H/X材料；公开件不含私钥或凭据。

独立设计意见、红灯/绿灯、正式执行意见与逐A判定分别保留原件及版本；结论逐项引用证据。某格测试环境故障与产品失败分别记，修订用例/观察器后须重新检查独立断言，不为“两个端内部ID不同”等预期错误改产品。原生场景/用例关联完整后再给R008结论；缺任一E三格、H三格、X六方向、最低Python门或关键原件不可读，整008未通过，旧007缺口仍单列。

最终PR列出通过、失败、未验证、阻塞及实际包/命令入口，附README使用路径和干净上下文Review结论。CI全绿只能作为回归，不能替代本PLAN的实际用户/服务/原件验收。提交PLAN不表示后续实现或测试已经完成。

## 确认记录与剩余工作归属

维护者确认本修订版PLAN、提交创建合并PR，并要求实际合并后直接开始实现与验证。chi_sim+eng/PSM3作为已探测的候选验收profile，按实际配置记录语言顺序，不自动改用户配置；SPEC示例eng+chi_sim仍是合法配置，不能把不同配置的质量冒称等同。

本轮免macOS系统服务权限预检；正式H-mac保持。其他平台组件安装/启动由G0-I先完成，完整PDF安全路径由实现/TDD完成，CI原件回收为证据待办；这些状态不再被混称为PLAN不能确认。对应平台/功能/原件未实际验证前仍不判交付通过，不降低SPEC范围、质量、预算或平台要求。实现PR仍需完成独立验收与PR Review后交维护者决定是否合并；本轮授权不包含发布或升级日常服务。
