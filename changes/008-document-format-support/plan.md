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

### 实现阶段的方法调整记录

2026-11-25：实际冻结的双份双页Noto中英扫描样本暴露两类本地OCR错误：直接使用整页PSM3将“关”误识别为“天”，单一块分割又遗漏另一份资料的中文段落。保留原样本与失败结果，采用统一180阈值二值化、完整网格一次PSM3、剩余正文区域PSM11；仍使用配置的语言顺序和同一Tesseract，不逐格启动、不接外部模型。每页全部布局/渲染/OCR仍共用30秒，强承诺质量/逐格真值和所有SPEC验收条件保持。实际组件/语言文件摘要、预处理和分割模式写入结果profile/coverage，以最终同版测试与平台验收确认；研究或开发调试通过不等于整体验收。

2026-11-25：将原TC-008-pdf-native和TC-008-pdf-ocr中预留的混合页检查独立为TC-008-pdf-mixed，保留两个原用例的纯原生/扫描检查和ID。新用例覆盖两份多页资料的原生页眉遮罩、扫描正文补全、同页两张纵向分离的完整网格及后续纯原生页不调用OCR；复杂布局负例仍独立待验，不以本用例替代。该拆分只调整测试组织，不改变SPEC范围或质量。

2026-11-25：CI原始证据使用控制端持久私钥与runner公钥的X25519/HKDF/AES-256-GCM封装。新增独立下载及核验脚本：先核GitHub artifact的run/commit/name/ID/长度/摘要，再解密、核逐文件清单并用实际格式读取器打开，清理证据不完整不能形成回收通过回执。先以真实浏览器下载/轨迹小样和故障控制演练，不把小样的前景HTTP清理当H5原生服务验收；正式E/H/X仍逐格复用同一证据链。

2026-11-25：TC-008-empty-original先取得Local路径来源/files/HTTP的独立子路径证据：空白成功不依赖FTS命中，列表按已发布的原件/结果处理版本及当前连续有效来源资格签发原件引用，不打开外部源路径；失败候选不获得已发布原件资格，旧文本未捕获原件保持not_captured。网页资料库、CLI/MCP/Hub、真实重启和完整档案迁移仍按原矩阵后续逐项验收，不用本子路径替代。另以TC-008-reference-local-cli单列CLI传输/写出验证，原件信息与输出按各自SPEC契约核字段，不要求下载JSON复制全文视图的附带元数据。

2026-11-25：混合PDF的真实双网格红灯暴露同宽分离网格被合并的问题；按连续外侧竖边拆分连通网格组件，单行网格同样可识别，profile记录connected-v2。保留原生文字遮罩、同页OCR预算与全部逐格/覆盖/位置要求；两份混合资料的开发证据不替代复杂布局或平台矩阵。CLI读取独立验证真实非零命中范围，再接入text/table/original-info及原件新路径写出，未给start/end时保持引用范围；原件只从已验证快照写出，使用排他创建拒绝覆盖。

2026-11-25：成套同步将纯字节分块/容量预约独立到document_transfers.py，将Hub的纯结果验证/快照安装独立到processed_documents.py；stage/publish仍承担设备来源投影完整发布，网页自有资料管理不借此授权。原件与结果分别冻结SHA/长度并按1MiB分块发送，首份同步前已删除源路径并安装零处理探针；已完成的十份资料、重复读回与独立包证据仅证明分配子路径，不替代坏包/并发/回滚保护/TTL及平台矩阵。Hub基础包增加该标准库共享模块，包验证器同步登记后仍检查完整文件集合与逐文件SHA。整批相关回归工具时限由180秒调至300秒，产品内容任务300秒限制不变；旧超时/失败保留。

2026-11-25：MCP的text/table/original-info以真实stdio独立验证，保留三只读文档工具并转发完整行列参数。原件信息不提供写盘或大段base64。Windows普通CI的12项共享探针误拦已独立定位为标准库socketpair自管道；维护者明确决定保留该缺口、继续其他工作，故未应用候选探针补丁，也不把受影响业务或Windows整格标通过。SPEC平台要求不变，最终按实际失败/未验证状态交付。

### 修改位置与数据流

| 位置（新文件为拟名） | 修改职责及约束 |
|---|---|
| src/smm_local/documents.py、managed_documents.py、core.py | 保留旧文本/项目/来源语义；新增受控原件采集和来源授权、失败项管理、candidate/published分离、CID/AID及版本事务。明确refresh才开外部路径，快照读取不回源 |
| 新增document_snapshots.py、document_results.py | 不可变原件/规范结果存储、完整清单与schema、SHA/尺寸/定位校验、短事务原子发布；失败候选与已发布资料分离，额度预留和孤立文件回收不撤掉合法引用 |
| 新增document_processing.py、document_worker.py、document_formats/ | 配置CAS、单任务调度、所有格式读取/布局/OCR在worker内；标准库纯结果接收不导入这些可选处理库。DOCX部件/嵌套/修订、XLSX所有实际单元格/缓存/日期、PDF原生/混合/扫描分别实现 |
| 新增document_supervisor.py及平台实现 | 每档案跨进程唯一处理槽位，任务树1GiB、临时256MiB、总300秒及PDF各子预算；独立监督、心跳/租约/终态恢复；Win Job Object纳入worker后才允许其加载解析器，POSIX独立进程组含OCR子进程，监督退出/父进程停止也回收任务树 |
| src/smm_local/service.py、api.py及Hub lifespan | Web明确提交后后台执行，重启仅续办本端合法已捕获任务；CLI refresh/reprocess可同步等待并报告真实终态。Hub服务已运行时，CLI仍独自采集外部路径、将合法原件交同state服务worker处理并等待；无服务的明确CLI动作才使用前景调度。按需服务有活跃任务时保持生命周期；已运行创建端服务负责其队列，CLI可入队并同步等结果，独立CLI无服务时才启动自己的受监督执行器，跨进程槽位防重；MCP、纯查询及接收投影不得创建处理任务。处理不持DB/控制锁 |
| document_protocol.py、document_transfers.py、document_sync.py、src/smm_hub/processed_documents.py、documents.py、document_api.py | processed_documents_v1能力与接收schema协商、成套原件/结果分块及原子来源发布、幂等/代次/回执；旧TXT协议独立兼容，禁止接收分支进入原件处理器 |
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

POSIX监督至少每100ms检查任务树/单调时间及任务目录实际字节，以进程组和已登记后代处理退出/重父化；任何持久PID记录都须同时核创建时间、任务身份及租约，不能只凭复用PID杀其他进程；执行终止前核PID、创建时间、任务token/租约及程序身份，不按过期PID记录误杀重用PID的其他进程；Windows Job Object禁止breakaway，配合RSS观察和整Job终止。临时空间采样的子路径首次PermissionError后，立即从任务根完整重扫一次，不等待、不复用前次部分计数；完整重扫成功且根仍可观察才继续，否则停止该尝试并报实际监督错误。任务根缺失/不可读直接失败，持续访问拒绝/观察盲区不继续处理；不改任务预算或重跑内容任务。完整OOM/预算实验在隔离档案串行运行，保存实际树与终止证据，不通过调低生产预算冒充1GiB实测。按SPEC实证5秒终态/槽位恢复及主服务查询存活；各OS不宣称同种内核硬限制。[Windows进程组约束](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。

### PDF有界解码的接入位置与确认门

不能直接调用库默认PDFStream.decode后再量结果。创建端worker在创建PDFParser/PDFDocument之前安装本任务受控stream工厂/解码器，覆盖普通、对象、xref及页资源中的get_data路径；只在该worker命名空间内生效，版本/接入点不匹配则报告guard_unavailable，不退回库默认批量解压。接入覆盖的调用轨迹、组件SHA与反例归入确认前原型和后续TC-008-budgets。

- Flate使用decompressobj和有上限输出块；输出块最多64KiB，最多请求剩余额度+1字节用于识别超额，超额字节不加入保存结果。原型已实际核32MiB相等/+1、同页多个流合计及128MiB全局合计，见[原型记录](planning/pdf-budget-feasibility.json)；这不是对其他滤镜或SMM路径的通过证明。
- ASCII85/Hex、LZW、RunLength、滤镜链和预测器须经相同有界sink，不调用无上限辅助函数；对象/代次、压缩链层级、循环引用及跨页共享资源有明确计数。文档元结构先计全局；页树确定后，在读取页内容/Form资源前建立页归属并增量累计，不能用“每流32MiB”冒充“每页32MiB”。缓存不重解码，实际重复解码不能逃过总量。
- PDFium是独立原生解码路径，不能因pdfminer有guard便直接加载用户原件。拟由guard取得完整校验对象图后，生成仅用于处理的私有中间PDF：通用流为有界解码结果，去除相应Filter并重算Length/交叉引用；光栅图像先核宽高/像素及已预留的解码字节，再转为受控图像流。原件不改写，始终按原SHA下载。只允许PDFium加载已验证中间材料；材料超过任务临时额度则失败，不回退加载原件。
- 实现阶段先以独立用例验证普通内容流/对象流、滤镜链/预测器、同页多流/跨页共享、图像尺寸与中间材料的文本/表格/定位保真及超限前拒绝，再接入对应产品路径。PLAN阶段已完成Flate关键风险原型；其他部分是待实施范围，不是要求提前交付的完整安全实现。中间序列化/编码支持不足时补方法并重做探测，不能在PLAN自行新增对SPEC目标文件的排除项；必须改变支持面时先回SPEC确认。

2026-11-25：将已commit路径候选的暂存容量另拆为TC-008-staging-dedup与TC-008-staging-plus-one，与既有PDF解码/像素子域分别取证。用真实256MiB、20MiB合法PDF和独立原SHA/字节总和验边界，不降低产品限额；批次需约70秒，原生工具外层改为180秒，单个产品任务300秒不变。仅证据原件无损gzip保存并核双摘要，实际输入/快照不压缩。字节准入采用专用跨进程锁，按实际raw/results及未完成临时文件统计、验证已有相同摘要后复用，容量检查先于原件/结果打开写入；数据库读取在字节I/O之前结束，解析/OCR、网络及查询不持有该锁。成功发布在同一发布事务记录永久快照摘要，历史发布字节不转回未发布计费；不再按逻辑捕获行数重复计原件。传输暂存、并发预约/回收及其余预算仍按原SPEC/PLAN单独验收，本子域不替代完整B9、E/H/X或归档恢复保护。

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

2026-11-25：新增缓存重处理在途开发验证：真实 CLI 在调用原监督器前以测试屏障暂停，查询进程分别核两份 ready Word、两份 partial PDF 与独立控制资料的旧整套快照；来源文件采集后删除，完成后逐份核新尝试终态、同原件新处理版本及旧引用退出。测试专用屏障不替换处理输出，源路径审计和元信息/终态拒错自检单独执行；独立复审通过仅覆盖 cached-inflight，不替代网页更新、刷新新原件、重启或平台验收。

2026-11-25：创建端新格式HTTP上传开发路径新增 raw-only 暂存模式（设备同步仍要求原件＋结果），共享已有分块容量预约与快照字节路径。完整原件提交后，以短事务登记本端资料、CID/AID和持久等待任务；响应后由后台调用既有受监督处理器，处理不持DB或Hub控制锁，成功才成套发布。library补充现有快照详情，旧文本API不变。两端普通/全局项目共12份独立原件、32个源定义表格及24份实际下载通过独立复审，相关100项回归通过；首次整组超时及隔离复核保留。持久记录不等同于已验证服务启动续办，重启续传、更新CAS、真实网页及平台矩阵继续按原SPEC补齐。

2026-11-25：创建端服务启动时以独立队列线程续办仍合法的本端已捕获等待任务；Local接入现有lifespan，Hub保留调用者原lifespan。提交回执重放返回原CID/AID对应的实际当前终态，已换项目或候选/尝试时拒绝。实际HTTP前景进程在两端各验证两份DOCX的半传续传、等待任务恢复、原件离线读取、回执幂等及完成后正常重启；主项2条与104项回归通过独立复审。测试屏障阶段两端均在优雅超时后按真实PID/创建时间/命令校验并强制结束；其余三个生命周期正常退出，不把该项当作正在处理任务的优雅停止或受管服务证明。外层MCP调用300秒超时后从原生已完整写入的green结果恢复，核main/regression exit0及settled，不复跑、不抹去工具超时。

2026-11-25：Hub CLI补齐text/table/original-info、四个行列窗口参数及original-output，读取和导出均复用现有Hub资格/引用核验与共用独占写盘函数；不改变旧默认text读取。真实Hub CLI两份DOCX、完整六表/表头、非零窗口及非默认四参数、原件与所有互斥/拒覆盖经主项和38项相关包/007/CLI/MCP/上传/重启/兼容回归并独立复审通过。后者为两处纯CLI/导出函数暴露改动选择相关回归，不以本次再跑未受影响OCR全套替代最终C1。原生验收CLI现可用原请求stdin和业务argv独立落盘执行，已先做runtime/settled自检；保留启动PID/参数/请求SHA/stdout/stderr，再从原生完成记录判定，避免交互MCP300秒时限导致重复执行。Windows常规CI回收显示390通过/23跳过/13失败：12项共享探针误拦仍保留，另一MCP初始化断连缺内层stderr，原因未判定；不对其假定同因或改判通过，新增上传主项在三OS均通过。

2026-11-25：空白管理资料两端列表原件引用补齐：Local files/library在同一DB快照中复用原件引用签发；Hub files/library复用原search的Hub上下文外层签名，仍由原read验证HID/epoch、身份/版本及连续资格。Hub内部_files在既有控制锁内供两入口共用，避免嵌套控制锁；不通过放宽read校验接纳裸内部引用。12份合法空白DOCX/XLSX/PDF的两列表24份真实下载、完整状态与零回源/处理/网络，以及62项相关回归经独立复审通过。空内容终态沿用empty-success，连接合成Hub的Local设备身份与档案身份分别核验；准备时两处错误预期与证据量阻止记录均保留，不算产品失败或通过。

2026-11-25：创建端原件分块入口增加同格式更新及当前文档/V/P/来源版本、适用CID/AID比较；替换捕获授权与旧发布资格分开，失败保留旧整套，新候选可仅由创建端CLI使用保存字节重试。重复commit先核自身当前回执，任务完成按原payload比较，不能清掉新等待项；Hub自有reprocess将实际处理放在控制锁之外，最终复用短发布事务。两端ready/partial各双目标PDF及控制资料共18个原件版本、1225次HTTP和12次真实CLI的主项与69项相关回归经独立复审通过。先前请求时限错误、主项超时/诊断、回归入口错误及70项整组超时均保留；仅把已通过的重型旧同步边界项留在同字节前次记录，剩余69项独立完成，不宣称70项曾合批全过。新增格式旧小文本入口隔离、移除P/CID/AID/零版本、路径链接、完整任务/GC及实际网页仍待各自测试。README、使用指南与检索Skill补008使用入口和未发布边界；新普通CI原件核验后记录Mac/Linux各412通过24跳过，Windows394通过23跳过19失败，新增重启身份探针问题与原网络探针/MCP缺口分别保留，不算平台通过。


2026-11-25：新格式终态管理单列TC-008-native-management-fence：旧小文本PUT在幂等回执/写盘前拒绝DOCX/XLSX/PDF；移除核稳定项目、V/P、来源revision及适用未发布候选CID/AID，允许首次失败V/P0移除。共享资料库增加创建端项目校验回调，Hub保留已验证source_key，不误用Local项目键规则。实际PDF任务清理暴露临时文件枚举/stat竞态，监督器改成单次stat，容忍工作进程正常清理导致的ENOENT，仍对权限异常/任务根消失报错，不放宽资源上限。主项5通过及71项相关回归已同版独立复审通过；28次合法移除、568次拒绝和逐份读取见[验收记录](evidence/native-management-development.json)及[脱敏实际观测](evidence/native-management-observations.json)。用户批准的证据修订只按SHA去重完整files/library响应，每次请求/状态/原字节摘要仍保留；6077份证据共13,191,179字节，1650次列表响应对应170份完整原响应，未删断言。早期正确Hub删除被拒、证据超限及PDF竞态的失败记录保留。构建首次因非交互PATH无uv失败，使用既有--uv绝对路径后两包构建成功；不据此认领安装/最低Python或E/H/X。实际网页、active取消、完整生命周期/GC与跨平台缺口继续单列，不以本项关闭。

2026-11-25：实际浏览器上传TC-008-web-native-upload的额外修订已按维护者决定停止，保留第二轮处理期间旧资料状态/详情、项目切换及处理中/完成后的网页资料ID全集两项证据缺口；未应用retained-and-project-ui补丁，不登记该上传用例passed。正文/表格/原件浏览器用例独立准备数据，只覆盖SC9读取，不代替SC1上传阶段断言。Windows共享socketpair观察器的补丁同样按维护者决定不应用，19项常规CI失败分别保留原因及未判定项，Mac/Linux常规CI通过也不等于E/H/X矩阵通过。

2026-11-25：SC9空白资料网页读取单列TC-008-web-empty-original：两端真实浏览器逐普通/全局项目DOCX/XLSX/PDF共12份合法空白原件，从资料列表实际下载并核身份、V/P、长度/SHA及逐字输入；4份旧TXT仍可查全文，列表/reader无可用原件下载且明确not_captured。Local列表并发刷新曾重复追加同4项为8项，现以请求次序和项目双重检查只接纳最新响应。主项2通过、14项相关回归及322份证据经新上下文独立复审通过，见evidence/web-empty-original-development.json。正文/深表读取的39项相关回归通过，但主项遇到本机嵌套section被全局CSS隐藏及Hub测试误用Playwright响应status_code；前者已改可见div，后者单行补丁待维护者决定，未宣称该主项通过。纯HTML修改的两包已隔离构建并逐ZIP/静态网页摘要核对，未安装到日常环境。保留SC1上传两项缺口、完整scope/query-network及E/H/X，不能把空白列表项当作完整SC9或008交付。

2026-11-25：SC7新增TC-008-managed-update-replay，真实创建端HTTP确认更新已接收后丢弃调用方回执，从同一begin恢复；先前两端均因该提交自身新CID/AID而被误判过期。begin/part现先复用commit已有的同指纹、当前候选且仍有采集授权的回执检查，否则继续原目标CAS。独立两端普通/全局DOCX目标在pending及ready各重开/重复同块/提交，异块与异SHA拒绝，后续V3及移除后旧begin/part/commit拒绝且完整业务/保存状态不变；28组实际全文/全表/原件逐字核独立源。主项2通过、30项相关回归和333份原始证据经新上下文独立复审通过，见evidence/managed-update-replay-development.json。两包构建exit0并核当前回执模块及网页静态字节。这里只模拟调用方不持有已保存的200回执，不冒称实际网络中断或本项重启；完整SC7/E/H/X、Windows及网页保留缺口不变。

2026-11-25：路径用例复审核对C1原文后，进一步盘点发现此前SC7 managed-update-replay与managed-upload-restart各用普通/全局一份DOCX，未满足同项目至少两个适用目标的数据要求。历史真实红灯/绿灯/独立意见保留，但不据其认领完整C1；最终C1前须将这两项扩为同项目双目标及明确负控，再核当前版本。SC10管理路径用例已按此修订为每端普通/全局各两份DOCX，并保留跨项目空结果、成功换版后旧ref拒绝。

2026-11-26：SC10新增TC-008-managed-update-paths，原新格式更新缺少旧文本入口已有的完整管理路径检查，文件链接被替换、父目录链接曾让两端实际写到私有外部控制文件。_target现复用管理库根检查并逐路径/父项调用原_link（含Windows reparse判定），在替换和登记CID前拒绝现存链接；仅容忍缺失普通项以保留明确上传恢复既有普通路径行为，不放宽已提交旧回执、项目或CAS保护。先后保留tree漏空目录/悬空链接、同项目数据不足两份的两轮测试修订意见；最终每普通/全局各两份DOCX，完整lstat树自检、跨项目零命中、成功更新后旧ref拒绝。主项6通过、39项相关回归及3102份证据经新上下文独立复审通过：48拒绝/48还原后同payload成功更新、408组全文/全表/实际原件、72份输入和72份去重下载；见evidence/managed-update-paths-development.json及managed-update-paths-observations.json。原生JSON保存为无损gzip，公开件保留存储SHA与解压原JSON SHA并脱敏link目标绝对路径。两包构建exit0且模块/网页字节匹配当前候选。仅当前macOS C1 HTTP TestClient，Windows junction、请求内系统调用竞态及完整恶意输入/E/H/X继续未验；不据此关闭SC1/SC9保留缺口。

2026-11-26：更新回执TC沿用原ID，活动声明迁移至test_document_formats_update_replay_c1.py，保留原聚焦回归及material/state/settle原函数字节不变，避免改其它用例的共享辅助代码。每端普通/全局各两份Word，原全部检查保留，新增完整项目ID集合/跨项目零命中和24份源真值自检；未新增产品行为。全SC7尚有缺口，原生purpose=tdd-baseline登记因要求全场景完整匹配而被拒且未执行，改走限定检查的候选debug→独立设计复审→正式execute→独立执行复审，不伪称整场景基线。正式主项2通过8.59秒，916份证据逐摘要核验，16当前回放、16旧请求组、104组完整读回/跨项目负控及24输入/下载均独立通过，见evidence/managed-update-replay-c1.json。managed-upload-restart准备阶段已用完两轮测试修订，其同项目扩充和按实际SHA去重下载的具体补丁另待维护者授权；未应用，不从本项关闭。

2026-11-26：SC8实际网页管理单列TC-008-web-ready-management：既有ready资料每端普通/全局各DOCX/XLSX/PDF共6份，真实选择不同名同格式原件更新并保留原显示名/path/归属；全部逐目标核旧v1引用退出、源定义全文/所有表及实际下载，随后从网页移除并核旧v2引用拒绝及其余资料准确。初次红灯为PDF同页表匹配测试错误，下一红灯只停accept字符串；独立意见合并修正六项设计/断言后，真实chooser两端均以旧文本PUT收到400 binary NUL，红灯复审有效。产品网页改走已有分块原件协议，冻结所示V/P/revision/CID/AID及Hub上下文，移除补P/适用候选比较；更新轮询核自身CID/AID，不把接收当成功。原始主测试报告2通过35.55秒，但36张整页PNG与两轨迹使本轮1494份证据达54,253,080字节，原生工具因25MiB上限blocked，未保存命令退出码、未启动回归，未送绿灯复审或判该TC通过。另行执行原拟相关回归24通过169.12秒、exit0，两包隔离构建exit0并核字节；见evidence/web-ready-management-development.json。只截业务区域、保留全部断言/原件/网络/完整轨迹的具体补丁待维护者授权，未应用；SC1上传与Windows保留缺口不变，完整生命周期/E/H/X继续待验。

2026-11-26：已验回执与路径保护独立提交并推送5126cd1（网页WIP及待授权测试未纳入），普通三平台CI45661390239原件逐ZIP/官方SHA及JUnit XML实际回收：Mac/Ubuntu各432通过28跳过0失败，Windows409通过27跳过24失败；新增17项中Windows六项实际产品路径隔离均通过，4项回执业务仍停在原Server启动器PID与实际HTTP进程PID比较，1项悬空链接自检把Windows\\?\命名空间表示误作不同目标。对比f3e6f90全部19旧失败保留、仅新增上述5项：13个stdlib socketpair观察器误拦、8个启动PID探针、1个normcase审计预期、1个命名空间自检，另1个MCP initialize Connection closed原因未判，不合并为同因或改判通过。网络观察器补丁继续按维护者决定不应用，新增路径自检具体单行补丁另待授权；无ESXi使用，源码CI不代E/H/X。见evidence/ci-regression-5126cd1.json。

2026-11-26：SC11最低版本安装业务单列TC-008-minimum-installed-mac：两个全新3.11环境各离线安装对应本轮wheel[documents]，产品命令始终由安装环境Python -I、非源码cwd执行；按wheel核安装本包全部资产/METADATA，Hub不能import smm_local，UID501及错误SHA/源码导入实际负控。普通/全局每端各四类资料共16原件，246次真实CLI、32全文、64全表304格、32信息与32实际原件下载；捕获后移除测试源仍用旧ref读回。首次字段误读与第二版原生全文序列化过严分别保留；两轮测试修订后按独立源单元/明示顺序与合法排版自检，正式主项2通过17.24秒、352份原件2,236,903字节，经新的候选及正式执行Reviewer分别通过。见evidence/minimum-installed-macos-development.json。安装命令补存来自真实宿主调用及原日志SHA，缺原逐进程PID/起止，未重造计时收据。该wheel含尚未提交网页资产，本用例尚为WIP，按精确wheel/test/source摘要认领此快照，最终cleanHEAD重建须再核；其他OS最低门、基础接收/迁移/完整发现性及E/H/X仍缺，不称整个SC11/008通过。

2026-11-26：SC10新增TC-008-reservation-lengths，实际两端原256MiB未提交预约曾被同SHA较短声明覆盖计费，随后新有效小DOCX预约得到200。受影响模块document_transfers现按(kind,SHA)保守合并承诺，再减实际incoming一次；新begin写状态前拒已知SHA/长度冲突，状态创建后任意失败清理自身新文件/目录，旧绑定及同长复用保持。首个1byte元数据探针红灯保留，测试仅修订一轮加入有效DOCX正控/探针，防止格式提前拒绝掩盖计费；14种原字节每端恰256MiB，只预约、0正文/0CID/AID/任务，26份大输入无损gzip和4份有效DOCX完整保留。目录控制只对真实同一成员集合换合法次序，不模拟计费。冻结v2主项2通过3.71秒、物理暂存/精确+1/成套接收/上传/重启/回执19项相关回归通过173.91秒，571份证据经全新独立绿灯复审通过；296HTTP、136合法目录次序、28拒绝状态对、原14绑定逐次恢复见evidence/reservation-lengths-development.json。两包构建exit0并核新增transfers及原模块/网页实字节。新构建未执行最低安装门，先前3.11证明仅对应其原wheel；最终cleanHEAD须重建重核。只认领本计费子项，已commit/部分字节/24h回收/共享GC/并发及E/H/X继续缺口，未降低SPEC或抹去Windows失败。


2026-11-26：实施草稿PR #43已创建，cleanHEAD366931e独立审查按当前PR Review Prompt核Intent角色入口、PLAN、逐A1–A12和原件。结论需修订，未认领交付完成：确认缺失成员的授权缓存可复活、Hub路径refresh长持guard、过期/失效暂存无回收、新快照目录未纳入恢复清单、网页过滤实际处理错误、仅未支持对象被误作空内容成功，以及CLI旧格式帮助冲突；详见evidence/pr43-review-v1.md。guard新增表覆盖风险另待实际回退反例，不写成已复现损害。优先按当前已确认行为补来源授权红灯/修复、并行可用性和恢复清单；其余及完整C1/E/H/X仍待验，用户保留的SC1/Windows缺口不变。

2026-11-26：对cleanHEAD366931e重建两包并在两个全新环境离线安装各自[documents]，保存四个安装进程原argv/PID/起止/exit收据；复用同一冻结最低版本测试，无新测试修订。候选2通过26.40秒并经独立设计复审，正式2通过18.80秒及352份原件2,238,129字节经另一新Reviewer正式passed且登记；246实际CLI、16独立原件、32全文/64全表304格/32信息及32下载、删除源后旧ref均核。精确wheel及记录见evidence/minimum-installed-macos-clean-366931e.json。该证据补当前提交macOS普通UID安装子项；Linux/Windows最低业务、旧档案/完整发现性、服务/协议矩阵与E/H/X未据此关闭。


2026-11-26：PR #43 F1的两个已复现路径分别补独立TC：正常目录枚举确认missing、目录可枚举但单文件真实非root POSIX PermissionError。每端普通/全局各2ready DOCX+2partial PDF，另2无关控制；只有该来源失效时撤对应捕获授权，保留连续重叠来源。新格式采集完成后在process前记录captured_id，单项错误只保留确实完成捕获的失败新候选，避免将正常OCR/解析失败误作无授权。主missing红灯2失败、同版绿灯2+12回归通过；第一轮身份预期错误保留。其绿灯独立passed但因先推进SC8设计导致原生登记blocked，未篡改记录或补假通过。不可读红灯2失败、绿灯2+15回归通过并独立登记。随后两冻结TC合并到同一设计、其它生命周期显式列5项缺口，最终共同产品普通debug各2通过并独立候选passed，再正式各2通过19.77/20.21秒、1713份原件16,111,197字节，经另一新Reviewer正式passed并成功登记，见evidence/refresh-authorization-combined-development.json。每TC56全文/96全表/56信息/56实际下载、16合法与16拒绝重试及288旧ref拒绝逐份核；相同字节重新明确refresh不复活旧ref。统一复验采用独立--basetemp保留合成源，避免pytest滚动清理；原测试内容未改，missing控制输入2槽覆盖和20份独立SHA下载的对应如实保留。只关闭上述授权复活子域，不据此关闭在途取消、完整SC8/C1、其它PR发现或E/H/X；新源码后需最终重建/安装复验。


2026-11-26：修复PR #43 F7已确认的Local CLI局部帮助冲突，只改refresh/read说明：旧文本2MiB/来源16MiB与新格式原件20MiB、原件/结果各来源128MiB分清，保持1000候选及现有命令/参数/实际限额不变；指出创建端依赖、OCR configure/check、提取文本与准确原字节导出。第一版实际输出会在命令名称中折行，补ASCII命令前后空格后4级真实help均exit0，未创建虚设DB；现有help及文档CLI回归10通过3.02秒，见evidence/cli-format-help-development.json含实际无敏感help原输出及摘要。低影响文案修订未新增镜像测试；未据此认领完整发现性、Hub帮助建议或平台安装门。


2026-11-26：PR #43 F2先关闭已复现的Hub路径refresh跨内容worker持全局guard子域。新增可选内部mutation_context，由Hub冻结来源集合，并在刷新开始、capture_metadata事务、最终_publish各短持经HID/epoch/own-source复核的锁；原文件读取、raw/results不可变写盘及worker锁外，Local无上下文调用和Hub原返回结构保留。没有把全部refresh无保护移出锁。真实HTTP Hub与真实CLI共用专用档案，普通/全局各2ready DOCX+2partial PDF旧控制、各2DOCX/2XLSX/2nativePDF新目标；12实际worker raw-open屏障逐PID/PPID/模块/UID/AID/rawSHA核验，每屏障46条HTTP逐旧ref检索/全文/全表/信息/实际原件及状态在释放前正确返回。初始阻塞红灯1失败13.47秒、释放后同请求恢复，经独立expected_failure；冻结主项1通过18.65秒、48项相关Hub/Local来源/项目/生命周期/重试/在途/两类资格/HubCLI回归通过277.48秒，890原件6,655,575字节经新独立Reviewer passed并登记，见evidence/hub-refresh-availability-development.json。20源/原件逐字及mtime、15进程和端口清理已核，无测试修订。5秒仅屏障观测上限，不新增产品SLA。该子项不代表已实现活跃服务的CLI任务交接；该队列方案、写控制/取消/晚到、完整大批量发布锁时延和E/H/X仍未完成，不把本项称完整F2/SC7交付。

2026-11-26：按草稿独立审查F4补恢复一致集：共用DocumentGuard.prepare_restore纳入已有.document-snapshots持久原件/结果/传输目录，排除tasks与capacity/upload-queue运行锁；LocalUpload除同步表也检查实际存储目录，避免先采集私人文档后连接Hub时遗漏。TRIAL_GUIDE补一致集与当前保护文件排除说明，不改变既有恢复后正文停止/重新确认约定。新增TC-008-snapshot-restore-set；公开configure_hub函数只连任务随机回环Hub，不启动日常服务，三分支为未初始化同步本机、已初始化同步本机、Hub自有，普通/全局各DOCX/XLSX成功及未配OCR的有效扫描PDF失败，共18原件12结果。前两轮参数/准备错误保留，冻结v3真实清单遗漏红灯经独立expected_failure；同版5主项通过25.98秒、67项既有上传恢复/独立Hub/文档生命周期回归通过156.58秒、141原件证据全SHA核验并获独立绿灯passed登记。按清单实复制数据库及30blob、保留当前guard并核元数据/SQLite及冲突状态；未测试真实传输块/接收投影/已有.documents管理载荷、活跃任务/损坏保护/实际正文拒绝或平台系统服务恢复，不以此关闭完整A11/E/H/X。见evidence/snapshot-restore-set-development.json。

2026-11-26：F5补两端nativeDetails明文展示后台latest_attempt.error；新真实浏览器TC准备时另外复现此前F1集成遗漏：ManagedDocumentUploads.run_pending已完整捕获却未在失败item传captured_id，共用_publish误撤本次合法授权。按B5补CID传递，不执行active=1或重开失效授权。两次准备/断言故障保留，冻结v3两端在retry_target=null处业务红灯经独立expected_failure，浏览器尚未到达，不冒称UI红灯。三处产品改动后同版主项3通过12.44秒、管理绕过/移除/失败替换/重试、缺失/不可读授权、空白原件及实际网页下载21回归通过260.95秒；209证据4897529字节全SHA核验，独立绿灯passed已登记。8份合成扫描/加密PDF在普通/全局两端实际管理上传，8图/2trace逐文档详情与原始后台错误核对；加密诊断尾部超pre截图滚动视窗但完整DOM/trace可读。只自动核retry CID及可见latest_attempt五字段，不声称全部可见retry/published值或这8份首次失败后CLI重试成功已验；不关闭原SC1上传/ready管理及平台缺口。见evidence/web-failure-diagnostic-development.json。c13de61常规CI已结束：Mac/Ubuntu439通过56跳过0失败，Windows416通过55跳过24失败；三份官方ZIP/CRC/XML已回收核验，失败测试身份集合与5126cd1一致，MCP断连原因仍未定，均不改passed。

2026-11-26：F6按B2/B7第103行修复Office严格无支持文字但coverage已有排除对象的空白误判：在共享pure document_results.validate拒绝这类结果，创建端Builder也经该校验转failed；接收端仍仅校结果、不解析原件，PDF分支未改。复核更正原审查附带的扫描时序推测：Package已预解析全部XML，页眉/footer drawing此前已发现，真实问题是终态分类及结果一致性。新增16份独立SDK生成并只读重开的冻结Office原件（186内部关系、12非白PNG），普通/全局的body/header/footer仅图、XLSX仅图与真空白/文字加图对照；CI只消费冻结字节，生成SDK不入产品或测试依赖。0次测试修订，冻结红灯4失败1正控通过、同版绿灯5通过32.59秒，解析/空白原件/同步直接索引/HubCLI/恢复18回归通过64.88秒，210证据全SHA核验及独立passed登记。两端32实际文档/CID逐原件核，16对象失败保留合法捕获，16正控检索/正文/原件准确。新增特定.gitattributes锁生成脚本LF与这组原件binary，实测core.autocrlf=true的17文件filter回读原字节/SHA一致；不代Windows运行。TRIAL_GUIDE补状态说明。仅认领严格无文本图片对象与纯校验，HTTP拒绝、未识别扫描PDF、其他对象/空白字符变体、完整B2/B7/生命周期及平台E/H/X仍待验。见evidence/unsupported-object-empty-development.json。

2026-11-26：补 scripts/acceptance/README.md 的008实际复跑入口，分别说明普通pytest/构建、真实OCR材料准备、组件CI、独立安装及E/H/X边界和原件回收。回收db798ea同版本两条常规CI的全部六份官方ZIP并核SHA/CRC/JUnit：Mac两次447通过61跳过0失败；Windows两次424通过60跳过24失败，失败测试身份集合与c13de61一致；Ubuntu push为446通过61跳过1失败（Hub重启恢复应发布V/P=1，实见V=0），pull_request为447通过61跳过0失败。保留两条原始结果，缺worker诊断，尚不判断失败原因或认领重启正确；五个新增Office对象分类用例在六格均通过，只是普通组件证据。pytest失败的job跳过后续构建和独立安装，不能以其JUnit代替包验收。见evidence/ci-regression-db798ea.json；网页上传/Windows保留缺口及未批准修订不变。

2026-11-26：维护者恢复关键验收、测试证据与最终检查，并允许使用家庭ESXi。VM76 Windows11与VM75 Ubuntu22.04连接/身份已核，后者仅补充诊断，不替代SPEC Ubuntu24.04；Windows SSH管理员不作为普通身份通过。原已保留/待定补证按本轮继续指示恢复，保留旧记录并逐项独立复审，不无限增加修订轮。跨平台调查与生命周期补齐按原SPEC开展，不改验收条件。

2026-11-26：修复未commit过期预约和独占incoming长期占用。document_transfers在现有容量锁内先写永久过期身份，再释放无活跃共享的预约/分块；保留state供重复清理，不按TTL删canonical原件/结果。begin及Snapshots.put准入触发回收，binding取同锁保证到期标记与commit串行；prepare_restore排除当前expired-transfers保护，指南补规则。获准9行满额后保护检查后冻结v4业务红灯2失败并独立expected_failure；同版主项2通过10.11秒、23回归208.40秒通过，487证据全SHA核验，独立passed已登记。首次组合回归300秒超时blocked保留，recover inspect确认settled且无残留worker；另拆真实容量两业务及四自检，6通过187.83秒，247证据及绑定经独立补充审阅通过，仅普通回归。见evidence/transfer-expiry-raw-development.json。raw+results/直接put的TTL、故障并发/保护恢复、失效已commit与在途分配GC仍未据此通过。

2026-11-26：按真实跨平台失败补共用测试设施document_formats_platform：显式UTF8与本机换行、词法/物理路径身份、只许可真实stdlib内部socketpair、鉴别venv启动器与实际服务后代，按创建时间/完整命令/物理解释器校验清理，并保留主体失败及原日志。获准combined-v2追加轮修复正常退出竞态与重启完成谓词，新增同项目双目标C1候选；设施Mac11、Windows15、Ubuntu22.04补充15项实际通过，独立复审逐份记录（Ubuntu本轮仍待登记时不先称通过复审）。该设施只减少观察器误判，不代替不同OS原生运行、普通身份、系统服务或E/H/X；Windows最新已推CI仍是a505的24失败，待新提交实际复跑。

2026-11-26：实际网页屏障复现两端“提取ready但尚未发布即显示成功”。Snapshots.detail补publication_pending比较CID与结果SHA；两页以等待发布继续轮询，不改真实attempt状态或数据库结构。按维护者批准的额外采证轮，改为有界等待刷新目标行，并按创建端拆同一TC的完整执行，保留每端24流程/48原PNG和全部DOM/原件，不裁删以绕限额。两端新版各先在原产品重取红灯并独立expected_failure登记，恢复同一产品补丁后各主项通过；共享及两端回归按原10项拆8+2，不减少检查。两份绿灯passed分别登记，联合独审核48流程/96PNG/1649证据及全部源绑定一致，见evidence/publication-state-development.json；联合意见不是虚构的第三次执行。只关闭发布状态子域，不关闭用户保留的在途来源取消、配置变化/发布失败终态、原网页上传列表等缺口或完整SC1/E/H/X。

2026-11-26：获准combined-v2的同项目双目标重启候选首次实跑为Local字段KeyError、Hub及三个设施控制通过（1失败4通过12.88秒）。独立复审合并提出五项设计/实现/绑定遗漏，已登记needs_revision，不冒称五项通过。相同最终overlay的Windows旧9补充回归为7过2失败161.06秒，两端已完成恢复检索/全表/原件，但worker审计0!=2中断，最终稳定重启未到达；真实原生audit探针及同安装stdlib源码确认Windows argv=str、旧hook只接list/tuple导致漏记。维护者对统一修订草稿（SHA3a01af4368e00edc7058c6cb8fd651b1f7f3973ba8058d85255fcd5aca32118b）选择保留缺口，不再修订/专门复跑这组C1与共享审计用例；不改产品或验收预期，不将未就绪新C1草稿作为可执行测试提交，其他独立工作继续。已有常规CI规则不被关闭或改成预期失败。

2026-11-26：6c65bc9两条常规CI的全部六份官方artifact已实际回收核SHA/ZIP CRC/JUnit。Mac/Ubuntu各两次458过63skip无失败，Windows各两次457过62skip2失败；逐身份核旧24失败中的22项这次确实passed而非遗漏/skip，余2仍worker计数0!=2，属于维护者保留的Windows argv审计缺口，不改xfail/跳过。该CI早于下述失败收尾修复，不能覆盖新产品版本。见evidence/ci-regression-6c65bc9.json。

2026-11-26：新TC-008-postprocess-config-finalization只验证真实结果完成/发布前的配置变化，明确不执行已保留取消/C1/argv用例。首版2个真实终态红灯但候选独审需修订，统一一次修订补同步入口、错误含义、所有已发布非目标保持、旧请求全表/任务无副作用；L3新待办重叠明确另列。v2按上传队列/同步缓存、Local/Hub拆4份同字节红灯：前三在配置失效后仍ready，Hub缓存第四份是在processing-status被admin.lock拒绝，未到终态断言，四份分别expected_failure登记，不混称同一原因。

2026-11-26：五文件实现调整：Snapshots.fail_current以document/currentCID/latestAID/frozenrevision的事务CAS收尾，旧任务不改新尝试且保留已有解析错误；managed上传在有效Hub/项目上下文内收尾，Local与Hub同步reprocess捕获发布失败并暴露当前失败。HubAdmin将documents分派移出跨内容worker持有的OS admin.lock，改依已有短DocumentGuard、SQLite CAS和内容槽协调；OS部署等命令仍串行。此为B4/B5/B9要求，不新增schema/CLI参数；服务CLI的执行身份/队列交接仍不据此认领。四份绿灯各12主目标（普通/全局每none/ready/partial各2），合48；56真实门含8个缓存首次合法捕获准备，四档案52文档；27项相关回归、15884证据73609553字节全SHA核及四份独立passed登记/联合意见均完成。删除原管理路径后显式retry同CID新AID、oldpub及所有非目标保持、独立正文全表/原件、旧ref退出和过期请求业务拒绝前后完整文档表/library不变均实跑。见evidence/config-finalization-development.json。仍只Mac前景子域，路径refresh发布失败资格/终态、旧payload与新待办重叠、在途/恢复/GC/资源全矩阵及E/H/X不关闭。

2026-11-26：同一批准publication用例未再修订，针对以上新产品重验两端原正常发布：各24流程/48PNG、Local2与Hub3回归通过，1648证据24586096字节及全部绑定经独立新意见passed登记和新联合复审；5个回归是前述27的子集，不合称32个独立用例。两个新wheel构建并逐新模块/HTML核源码一致，不冒称安装后业务。材料预备入口补到TRIAL_GUIDE，明确从清单取可执行文件/语言目录及显式验证；验收README更新当前ESXi授权，并将007停用环境说明限定为历史记录。新PR只读审查及处理版本隔离补充均原文保留，远端原件路由/处理版本混合/合并表头/路径Web详情与已commit无用候选GC继续待修。


2026-11-26：按已确认B8/A9补纯Hub原件路由与处理版本隔离，不新增CLI参数或调整SPEC。DocumentSearch.original沿配置Hub认证二进制通道读取，验证当前HID、引用epoch/材料、原件资格、长度及SHA，不回源或解析；联合候选身份加入P，同V/P的结果SHA冲突排除并报告partial，远端命中P/result与引用一致。旧bundle读取前只作拒绝性快照核对，真正资格/签名仍由各端验证；不同P/result/raw混用拒绝并要求重新检索，同快照和旧文本兼容。专用测试observer与既有共享restart_server分离，未修改被保留Windows字符串argv逻辑。新用例按设计补服务source/network正负控与不可吞异常基线、每入口全文/profile/全表/信息和原字节独立预期；首轮needs_revision及后续表格绑定遗漏均保留。第二次版本用例修订后曾因磁盘仅约140MiB在准备时SQLite I/O错误，原生独审记insufficient_evidence；未将其当产品红灯，保留全部原始证据。仅移除无绑定旧可重建安装venv；旧pytest-93在任务残留服务PID/ctime/完整argv/exe/cwd核对后正常停用，全文件无损归档逐SHA校验再移除临时副本，释放空间后32MiB SQLite提交/quick_check实测通过。同测试字节重取完整四目标红灯并独立expected_failure登记。新产品两主项分别1通过99.18/72.90秒，相关回归分别12/34通过34.89/213.82秒，1261/896份证据及同版绑定逐SHA核验；两份新上下文独立绿灯passed均已登记，见evidence/remote-query-routing-development.json。双包构建成功，Local包内新DocumentSearch逐字匹配；只认构建/源码核验，不认安装业务。不预先认领整条SC9/A9或Web/服务/HTTPS/E/H/X。另092ab9d的两条普通CI六份官方ZIP/SHA/CRC/JUnit已回收：Mac/Ubuntu各458过67skip，Windows457过66skip2个保留审计失败；四个配置终态用例在普通CI因未备实际OCR材料skip，依其独立Mac专项，不能把skip算passed。见evidence/ci-regression-092ab9d.json。

2026-11-26：按B8/A9修复合并列主格起点在默认窗口左侧时表头缺失：document_results以真实column_span判表头与列窗相交，merged_into仍只占本坐标；正常table及超额fallback共用，正文格锚点语义、解析和预算不改。新TC两端分别24目标（普通/全局×DOCX/XLSX×64/2001/16000码点×两份），未修订测试，均在遗漏A1真实红灯并独立expected_failure；同版主项各1通过12.21/20.31秒、相关回归7/10通过96.33/68.06秒，491/494份证据和全部当前绑定核验，两份独立绿灯passed已登记。ASGI TestClient真实上传/处理/读取及独立全格定位、全文、原字节，删除源后查询；不称TCP/TLS/Web画面/服务或全SC9/E/H/X通过。双包构建CRC及包内源码逐字一致，只认构建。见evidence/merged-column-header-development.json。abf两条CI六份官方原件SHA/CRC/JUnit回收：Mac/Ubuntu各两次459过68skip，Windows两次457过67skip3失败；2个为保留的argv审计，新增1个为准备阶段HTTP断连。家庭Windows在全273源文件一致的独立档案实跑复现，日志明确run_pending队列锁超时后HTTP断连；作为新产品问题待修，不能混入保留缺口。见evidence/ci-regression-abf46ca.json及windows-upload-queue-diagnostic.json。abf全PR新上下文审查needs_revision原文已补PR并保留，合并表头以外GC/路径refresh收尾/路径Web详情/服务CLI身份及完整验收仍未关闭。

2026-11-26：针对Windows实机后台队列锁超时，run_pending重复启动改非阻塞合并，取得协调权后的真正故障继续抛出；消费函数原样抽出，释放OS锁后再查本DB持久待办，防空队尾丢启动。测试前两次因TestClient等待后台的门依赖及强制第二kick进OS锁而needs_revision，均保留；冻结第三版以真实commit持久pending/原SHA/CID事件启动独立释放Timer，原产品四分支真实RuntimeError红灯独审expected_failure。Mac同版4主项通过4.29秒、8相关回归通过119.50秒，183证据/94绑定核验；独立绿灯意见仍needs_revision/design：同父目录不同DB共享队列锁而owner只查自身DB，当前补丁存在另一档案丢启动的静态风险，尚未复现。维护者明确保留此缺口，不新增拟议TC、不应用cross-archive-proposal进一步修复、不专跑，不算SPEC豁免。此前启动的Windows11独立274源文件复验完成：4队列+1远端原件共5通过无skip，终端389.54秒/JUnit suite367.87秒计时面不同；ZIP3483660字节/1508成员及1507项清单全SHA/CRC核验，24远端原件/逐入口身份与实际字节、控制/日志、6次正常服务停用经独立补充复审，无队列RuntimeError，cleanup_errors空。只认SSH管理员源代码组件，不认标准用户/包安装/SCM/E/H/X；原native needs_revision不变。双包构建CRC及46/47源码成员一致，只认构建。见evidence/upload-queue-development.json、windows-upload-queue-supplement-review.md。12e5128只读PR检查点意见已补PR并保留，旧表头F3关闭，其余既有缺陷及完整验收未完成。


2026-11-26：路径refresh终态独立TC在Local真实HTTP、Hub真实CLI入口重取红灯；首轮不存在Hub API及后续把实时来源资格当作快照字段的问题均保留。v3 Local expected_failure已登记，Hub仍因把搜索根封套身份误当命中字段而needs_revision；维护者明确保留该测试缺口，不应用待授权封套修订、不专门复跑。候选产品补丁已撤回并仅以惰性patch.txt存档，当前PR的路径refresh发布拒绝终态缺陷仍未修复，15项普通回归不能代替主项验收。见evidence/path-finalization-retained.json。

2026-11-26：7c2348a的push/PR两轮共六份官方CI ZIP按官方digest、CRC、JUnit实际回收。Mac/Ubuntu每轮465过68skip0失败；Windows PR464过67skip2失败、push463过67skip3失败，其中两份共享argv审计按维护者决定保留，另一新增staging-dedup的WinError5临时目录错误仍单独调查；同项PR轮passed不抹去push失败。新增4队列、1远端原件、2合并表头在六份产物均实际passed，共42实例。见evidence/ci-regression-7c2348a.json。7c独立PR检查点needs_revision原文保留，组件改善不关闭完整SC1/R008。

2026-11-26：Windows临时目录错误另作原生环境调查。普通RemoveDirectory得到ENOENT，真实FileDispositionInfo删除待定且句柄未关闭时scandir/旧walk得到WinError5，最后句柄关闭后目录消失。新采样用例先核持续共享拒绝、根缺失、256MiB及+1精确计数，之后真实PermissionError失败；原始证据/清理有效，但独审needs_revision/design已登记：强制异常后成功与本PLAN权限异常即失败约定冲突，不能认作产品expected_failure。未修改监督器或放宽既有OCR断言。一次完整重采样的具体SPEC澄清及未应用产品补丁另待维护者确认；相同症状复现不等于此前CI根因已查明。见evidence/windows-temporary-observation-diagnostic.json。

2026-11-26：维护者确认上述一次完整重采样澄清，SPEC B9/A10已同步，替代此前权限异常一律立即失败的采样细节；保留持续拒绝/根异常时的失败保护。实施只改共享document_supervisor临时空间采样，首次子路径PermissionError后废弃部分计数并立即完整重扫一次，第二次异常继续抛出，不添加sleep/任务重试/额度更改。TC-008-live-temporary-observation修订设计后先在原产品重取红灯并独立复审，再冻结同字节绿灯；真实Windows分别核恢复后的完整计数、持续拒绝、根异常、原256MiB/+1与清理，保持既有staging缺OCR断言不变并实际回归。Mac/Linux相关回归与三OS普通CI另行保留实际版本结果；不认领整个SC10、原CI根因或E/H/X。此条按本次明确确认的建议执行，不重新打开已保留取消/C1/共享argv/跨档案队列/路径刷新封套用例。

2026-11-26：按确认的B9/A10一次完整采样规则，仅document_supervisor加入首次已知子路径PermissionError的立即完整重扫；原部分计数丢弃，根异常/未知或范围外错误路径/第二次异常仍失败，未加sleep或修改256MiB/300秒。自然用例修订为真实Windows两删除待定目录13/19字节、保留37及根首次清单外新增11字节，恢复必须完整48；持续子目录拒绝最多两次walk、根拒绝不重扫、空目录0、根缺失、真实256MiB/+1及句柄清理均有独立断言。原产品有效红灯和绿灯测试字节相同，分别新上下文expected_failure/passed登记；原v1设计冲突及格式修正前意见保留，不追认旧红灯。

2026-11-26：绿灯第一轮主项通过但回归调用漏证据目录，第二轮同主项/Mac6通过但串行两OS总300秒超时，均blocked保留，不据此认交付；未改产品或测试断言，第三轮按平台拆调用取得formal green：Windows真实采样1过（JUnit0.975秒）、Mac原6staging回归6过134.90秒，274证据/1413750字节及280绑定全SHA核验、独立passed登记。额外家庭Windows容量回归因整个测试看门狗240秒终止（首20MiB PDF实际74.468秒、预期缺OCR失败），无JUnit、exit15，27原件及ZIP CRC/SHA完整追回，cleanup_errors空；这是未完成补充，不是passed或维护者豁免。C1数值共享部分由Mac完整回归支撑，三OS常规CI继续验证相同已提交测试；不更改产品每任务时限来迁就整批执行。见evidence/temporary-observation-development.json。两个wheel构建exit0，Local46/Hub47源码成员及变换shim逐字/CRC核，仅认构建不认安装。原CI一次WinError5的完全因果链仍未证明；GC/路径refresh收尾/路径网页详情/服务CLI及E/H/X未关闭。

2026-11-26：e8bb1bd的push/PR六份官方CI原件全部回收并核官方digest/长度/ZIP CRC/JUnit：534项，Mac/Ubuntu每轮465过69skip0失败，两Windows均465过67skip2失败。新增Windows原生采样两轮passed，其他OS对该专用用例skip不计通过；原6项staging在六份产物全部实际passed，共36实例，含此前随机WinError5的dedup。余2失败均为维护者保留的旧共享argv worker-audit0==2，未改skip/xfail/断言。Mac/Ubuntu构建/独立安装步骤success，Windows因pytest失败后续构建/安装skipped，不推断已验。家庭Windows额外容量watchdog未完成事实不被新CI追认；原一次错误的完整因果链仍不宣称已重构。见evidence/ci-regression-e8bb1bd.json。新上下文PR增量审查未发现新实质产品问题、整体needs_revision，意见已补PR；其D1建议把旧诊断index显式标历史，随后仅改标签和当前状态，旧意见原文保留。GC容量候选尚在本地准备，不混入本提交已验产品或该次CI。


2026-11-26：已commit失效候选GC首个子域采用保守用途证明，而非仅扫当前DB缺少引用即删文件。修改document_snapshots、document_transfers、document_processing、managed_document_uploads、Hub processed_documents及document_protocol六处：put→capture、处理原件/结果→attempt、commit→receipt/stage用持久pin覆盖；capacity.lock只串行短准入/用途读取/退休/删除，不跨解析、网络、guard或SQL写事务。先持久退休CID/AID/UID，再unlink无最后用途字节，保留发布ledger、连续授权当前候选、最新结果和活跃用途。独占owner同时绑定持久archive identity与DB路径，schema提交后、capacity锁外先初始化身份；同父目录另一档案的同submission不能据当前库receipt退休，既有合法UID回放先精确校验返回，不做新增canonical GC。旧path-only/未知/多owner、崩溃pin、未登记回执或接收stage均保守保留，不能把未删字节当已释放；reclamation加入恢复排除目录，Windows拒删仍计费。此为既定B5/B7/B9的内部实现，无新用户参数或额度变更。

2026-11-26：TC-008-canonical-candidate-capacity按自然设计先在两创建端取得v3同字节红灯并独立expected_failure，再用最终同版产品绿灯。每端普通/全局×none/旧ready/旧partial×两份共12目标逐个替代/移除最后用途；26次物理记录覆盖起始236MiB及恢复准入后的256MiB，254MiB为替换阶段合计推导，不冒称另有物理采样。每份当前原件/CID/AID/可重试目标、旧八份独立全文/全表/覆盖/原件及原ref保留，旧begin/part/commit/CLI retry逐拒绝且状态/字节不变，12次满额拒绝在正文写入前。主项Local1过130.23秒+9目标回归101.07秒，Hub1过169.96秒+8目标回归36.97秒，无skip；各注册独立passed，17为两批执行数，其中恢复用例重复，不称17个互异用例。见evidence/candidate-reclamation-development.json。两wheel构建CRC/源码核对通过；另Mac最低Python3.11独立基础Hub安装，无Local或处理extras时构造档案/owner并执行已公布processing-status入口通过，仅为补充smoke，不代替完整安装/跨OS E/H/X。

2026-11-26：早期候选与失败不覆盖：v1 Local容量主项过但两端上传回放回归失败；静态独审另发现跨档案同submission误退休UID。v2修订后Local主项+11回归通过，owner路径复用另经独审确认P1，v3把稳定档案身份加入owner并保守处理旧登记。Hub v2已到第11目标时watchdog的matching→cmdline出现真实AccessDenied，未处理退出的堆栈混进缺OCR错误，容量TC正确拒绝，主项仍失败；25回归通过不追认主项，最终v3成功不证明监督已修。各独立报告和实际失败摘要保留。正常退出竞态仅假说，监督源码本轮未改，需要另按B9/A10补PID观察及watchdog健康红绿灯，不能放宽当前断言。

2026-11-26：本子域不关闭完整GC/SC10/R008：共享SHA最后owner、连续重叠来源、无用results/stage、put/commit登记窗口、未知/旧登记、崩溃/旧DB恢复及Windows in-use仍需各自动态验证；跨档案同submission和停机DB改名/旧路径复用目前只有独立静态修订证据，不称已实测。既有维护者保留取消/C1/共享Windows argv/跨档案队列/路径refresh封套决定不变，不修改或专跑。路径refresh产品终态、路径Web详情、服务CLI交接和其他完整交付要求仍未闭环；e8普通CI早于本次GC代码，后续最终源码CI须另取实际原件。当前PR继续draft/needs_revision。

2026-11-26：针对真实监督日志里的cmdline AccessDenied，另建TC-008-process-identity-observation，仅验证身份辅助函数：创建时间核验后命令行不可读时，只有独立确认已退出/僵尸才视为不存在；仍存活、状态也不可读时仍明确失败。以两个真实自有进程的存活正控、错token/创建时间、拒绝注入及POSIX真实僵尸状态先取红灯，再冻结同字节绿灯和原6项staging回归。Windows源码组件验证另取同源证据，不把Popen启动器PID当解释器PID；复用公共创建时间/进程树/argv/exe/cwd核验，准备断言前登记清理责任、累积历史成员，并在启动器等待后逐一复核。仅改matching的已确认退出分类，不改预算、等待或任务重跑，不认定此前现场异常根因；完整watchdog健康监控、5秒失败/任务树/槽位恢复仍待另验。测试v1 Windows准备失败及两轮测试修订、原始红绿和意见均保留；已决定保留的其他用例不重开。

2026-11-26：上述身份helper最终v3红灯在原3e产品复现并注册expected_failure，冻结测试SHA2a5bb383c12f1c093d8dbc027bed10d88125a4ef2a934e413281079b5d569171；新matching后Mac主项1过0.61秒、原6staging回归6过140.43秒，独立passed登记。回归214份JSON中的27份保留错误经独立逐字核为缺OCR组件，无本轮watchdog堆栈混入；早一轮green-v2确有AccessDenied的事实保留，不因本轮通过关闭现场问题。家庭Windows同源源码组件1过2.26秒，两实际launcher→解释器、四历史成员退出/exit0/无强清理及存活拒绝正控均独审passed登记；POSIX zombie在该OS不适用，不冒充Windows Job/普通用户/安装或服务验收。两wheel构建成功，Local45py+1HTML、Hub47py+1HTML逐字/CRC核对，仅为构建证据。见evidence/process-identity-development.json。原3e的两轮三OS普通CI六官方原件也已追回并核digest/长度/CRC/JUnit：Ubuntu均467过69skip0失败，Windows均467过67skip2保留重启审计失败，Mac分别466过69skip1失败与465过69skip2失败，均为新GC错误守卫；短JUnit及完整失败job日志未给出实际error值，不能确定四候选原因中的哪一项，也不能从当前helper断言反推已修。该CI不包含本次未提交helper字节；见evidence/ci-3e29255.json。整体draft/needs_revision及其余SPEC缺口不变。

2026-11-26：1abe6cd新上下文PR审查已按角色/主入口逐跳、PLAN差异、A1–A12及原件完成：matching增量未见新实质产品问题，限定红绿/Windows组件证据可信，F1监督健康、F2路径refresh终态、F3路径网页详情、F4服务CLI交接、F5保留跨DB队列及完整验收仍needs_revision；原报告原字节归档evidence/pr43-review-1abe6cd.md，已补PR。其后两轮三OS普通CI六官方ZIP/digest/长度/CRC/完整JUnit已全部回收：两Ubuntu均468过69skip；Mac PR468过69skip0失败、push466过69skip2GC守卫失败；两Windows均468过67skip2保留重启审计失败。新身份helper六份产物均实际passed，不能据一次Mac通过盖掉另一次GC失败，也不能反推未知error值或宣称watchdog已修。两workflow仍failure，见evidence/ci-1abe6cd.json。未提交的监督健康开发用例及其审批不属于该CI或本次交付代码；生产监督健康逻辑尚未修改。


### 2026-11-27—28 六项问题修复的实施调整

维护者要求修复监督健康、路径刷新终态、路径资料详情、Hub CLI服务交接、同目录多档案队列和失效候选回收六项问题，重新开放相应队列及路径用例；2026-11-28明确授权必要测试修订、执行及独立复审继续进行，不再逐轮询问。其余已保留的在途来源取消、C1重启、旧Windows共享argv审计等缺口不因此关闭。本轮已重新允许家庭ESXi，Windows仅VM76（MAC 00:0c:29:8f:cb:f6）、Ubuntu仅VM75，在独立任务目录执行；Ubuntu实机为22.04，不替代SPEC的24.04平台格，Windows管理员源码执行不替代标准账户/SCM验收。

实现顺序及变更位置：

1. `document_supervisor.py`为受核验的worker注册内核退出事件（macOS kqueue NOTE_EXIT、Linux pidfd），在退出竞态中只凭确证归类退出；存活进程的拒绝访问仍报错。控制端同时监测独立看守，意外退出包括exit0均终止自有任务树并以失败收尾；持久记录精确token/worker的清理证明，之后才释放槽位和负载。Windows新增`document_windows.py`，用CreateProcessW扩展属性JOB_LIST在创建时原子加入私有kill-on-close Job，不采用启动后再绑定的窗口；包含实际创建时间身份和控制端退出后的回收核验。两个独立wheel及Hub内置共享模块均须纳入该新文件。
2. `documents.py`与`document_snapshots.py`将路径refresh的发布拒绝收尾限定为相同document/CID/latest AID/config的短事务CAS，保留原解析错误与已发布快照，不改新尝试。普通/全局、首次/旧ready/旧partial、重叠连续来源分别验证；恢复后旧text/table/original-info/download引用逐一拒绝，过期请求前后完整业务表（含Hub处理jobs与receiver表）保持不变。
3. 本机`static/index.html`的路径资料行复用已有保存详情组件，展示published/latest/retry，partial覆盖读取保存结果。独立DB/保存原件与结果物理SHA构造期望，再核API和实际页面，禁止查询重新打开源文件或解析。
4. Hub新增`document_execution.py`：同state活跃服务持内核lease、发布状态并消费持久处理jobs；CLI先保存原件，再提交精确上下文，让服务执行新DOCX/XLSX/PDF。无活跃同state服务时明确CLI前景处理；活跃服务故障不静默降级。多HTTP生命周期允许同state后继协调器接班；managed pending仅在服务启动续办一次，不周期性改变用户任务状态。`document_cli.py`、`hub.py`与`_archive.py`接入。专用handoff观察器与旧共享argv观察器隔离，实际自检及逐解释器身份/任务token证明服务与CLI各自执行位置。
5. `managed_document_uploads.py`按规范化DB路径维护进程内启动协调器，保留父目录OS全局内容槽。不同DB各自等待并只消费本库持久队列；同库重复kick仍合并。验证同父目录两库、各两文档，仅一次kick也全部完成，且第二份不靠人工重启或重复触发。
6. `document_snapshots.py`用明确注册的稳定档案身份与实际DB路径读取同目录其他库的只读用途快照，汇总最后合法用途/发布ledger/接收stage后才回收；未知/旧/重用路径归属不猜测。pin使用OS持有的租约；处理pin须有同token整树退出和负载清理证明，Windows以实际Job约束及原生退出核验恢复。先持久退休过期CID/AID/UID再删除字节；拒删仍计费，历史发布字节继续保留。`document_processing.py`将任务token写入pin关联。

验证方法的调整：正式TDD保持同版红灯→独立复审→冻结测试绿灯及相关回归→新上下文复审。总容量回归从单次300秒原生批次拆为独立补充控制器，不增加产品每任务300秒/1GiB/256MiB预算，也不以超时批次追认通过。平台补充按业务分组落盘退出码、完整JUnit、原始附件、源码清单与传输ZIP摘要，全部校验后才供复审。单平台通过不能代替平台特有内核行为验证。

测试基础设施修订与产品边界分开：新只读退出观察器仅在完整归属登记后按pid/创建时间等待真实退出，不在退出中重读易变argv/exe；身份无法确认仍等待原截止，不延长时限或发送信号。Windows仅测试自有JSON就绪文件在原deadline内重试短暂PermissionError/FileNotFoundError，坏JSON立即失败；原产品输入及预算扫描不使用该helper。文本握手按各OS真实换行核验，不改变正文/结果字节要求。此前真实失败、超时与工具环境错误全部保留，后续通过只适用于实际冻结版本。


2026-11-28补充：独立定点诊断用公开采集与SQLite backup复现同父目录复制库保留相同archive_id时的跨库退休：副本移除来源后，原库SQL授权仍有效，但共享retired可使原CID/AID失效，后续准入删掉候选。回执重复身份保护不足以防止该路径。按既有未知/歧义归属保守规则，在产生任何canonical退休、pin清理或字节删除前，将持久registry与当前实际DB身份/路径共同检查；复制身份存在多个路径时整次跳过canonical GC，仍按物理残留计费，不自动决定权威副本，不修复历史retired或复活旧引用。验证覆盖已登记副本、尚未登记副本首次准入及第三个独立库触发，原库合法候选、原字节、重试及实际账目保持；不同身份的正常共享最后用途仍须真正回收。

Ubuntu实机健康补证705.87秒批次13过1失败的原始记录保留：Local12目标、Hub前8目标完整，Hub第9目标在所有protected资料核对期间先耗尽测试30秒准备门，watcher正常退出，之后故障命令无法握手；不据此认产品五秒恢复失败或Hub剩余4目标通过。修订仅增加测试准备进度握手：父端在完整保护检查之间写当前token/nonce与递增step，worker/helper据新进度续其30/60秒idle门；重复/错身份/倒退step不能续门，未使用进度的旧用例保留原门。产品总任务300秒及资源限额、故障观察8秒、五秒失败/整树/槽位/负载回收判据不改；所有protected检查保留，注入前再次核真实三成员活着且无gate超时。实际响应耗时在五秒断言处采样，避免后续旧资料读回把证据计时字段延后。新增5项进度控制与原11项身份/就绪控制组成16项独立证据，再重取受影响红灯、绿灯和平台执行；不能用测试修订反向改判原失败。


本轮定点结果（2026-11-28，源码以evidence/six-fixes-development.json逐文件SHA为准）：F1最终Mac Local/Hub各12故障目标完整通过，原生主项各1过与16/15项相关回归、两新上下文passed已登记；GC最终Mac14过1Windows skip、7回归及独立passed已登记。F2两端各12路径目标、F3路径详情12画面已有独立passed，其原生执行源码早于新增复制身份保守分支，保留精确版本，不伪称全源码相同。最终代码的服务交接/跨库队列5实例与24相关回归另捕获29过；原生补跑在业务执行前因SC1整体设计版迁移blocked，未更改状态或伪造新native green，当前独立补充复审另列。Windows最终GC/Job与控制29过2POSIX skip、Ubuntu22.04最终Hub健康12目标及5进度控制共6过，原件已恢复核验并独立passed；Windows两端路径各12目标先前同源切片通过，保留其SHA/身份边界。最终两包构建/全成员/独立安装97映射、18命令及基础文本检索读取独立passed；不替代三OS最低Python/原生OCR安装。剩余Linux补充、普通CI、最终PR审查与完整R008义务继续待办，旧失败/超时不改判。来源与各意见见evidence/six-fixes-development.json。


2026-11-28完整PR独审3c2c42c按角色入口及A1–A12核验，发现F3网页详情虽提供三JSON，但缺CLI必填document_id；另指出Hub父层/add/refresh/reprocess帮助缺支持格式/参数取值来源，README→指南路径实际可达，均属局部信息不足而非解析故障。按既有B4/B5/A11补齐：Local nativeDetails以textContent显示当前文档ID并标明--document-id，不增加API字段或网页重试按钮；Hub document_cli仅补argparse help/description，参数/类型/必填/default/dispatch剔除说明后的AST与3c2c42c严格相同。独立DB身份→每个真实页面ID可见/唯一，既有三JSON、coverage、12目标及禁回源/禁解析全部保留；SC1自然设计v4后，旧产品真实缺ID红灯经独立expected_failure，再冻结主项1过+3相关回归、12张本轮PNG/trace并独立passed登记。最早覆盖指针元数据blocked（尚未执行业务）保留，不伪称产品红灯。

本补丁最终v3只改变Local静态HTML及Hub CLI说明，两者相对已验六批v2均明确列SHA差异，不再称全部64源文件仍逐字相同；其余62产品文件相同，Hub CLI除帮助值外AST相同。验证风险限定为页面交接、UTF8帮助和打包资产：Mac真实浏览器12ID/三JSON及3回归；Mac独立安装Hub与Windows/Linux源码各4只读帮助原字节、模块归属、未创建state；两包97源/wheel/安装映射、18命令以及安装后4帮助均经独立复审。没有据此豁免完整E/H/X、最低Python/身份或资源矩阵。完整PR旧报告原样脱敏归档，最终源码新上下文补充审查与每head普通CI结果通过PR持续记录，不用docs-only自引用CI制造循环；公开入口见evidence/six-fixes-followup.json中的稳定PR验收评论链接。


### 2026-11-28 全量剩余验收续办

维护者明确重新开放PR43全部剩余问题和验收，授权必要测试修订、执行与独立复审直接继续，不逐轮询问；完成更新PR但不合并、发布或升级日常实例。旧的保留决定及失败原件继续追溯，不再作为本轮停止依据；SPEC行为与验收条件不降低。继续沿AT-SMM-008当前定义，先修Windows观察与调查数据库停止后错误，再补取消/重启/读取、PDF/回收、最低Python和E/H/X，最后做需求级验收与PR新上下文复审。

共享测试设施`document_formats_platform.py`集中使用Windows CommandLineToArgvW正规化原始str，POSIX列表原样保留，worker按精确模块/任务token识别；restart、retry子进程源读守卫和handoff复用，并记录raw类型。四项真实参数/worker/源读正负控制及Mac/Windows原重启回归分别19过，独立候选复审通过，完整平台/普通CI仍单列。

历史Windows一次SQLite WAL重开I/O错误保留成因未定。Mac8/Windows16次原停止方式未重现该错误；Windows实际记录到venv启动器wait返回时真正Python仍可能存活。只修测试停止证明：先登记实际树，保留原硬停止，重开数据库前另等待全部已登记后代退出；不响应者清理后使测试失败，不能只凭启动器退出宣称已停。新增真实自然退出/不响应后代及外国进程控制，未来SQLite失败保存扩展错误码与停止证据。测试extra显式加入已有固定psutil，默认产品依赖不变，离线lock仅补该extra元数据。Mac和Windows各15项原同步/凭据/混合检索与新控制通过，独立调查/候选复审通过，不宣称历史I/O已确定根因或已修产品数据库错误。精确版本、范围和原件摘要见evidence/completion-checkpoint-20261128.json。

2026-11-28续办：来源取消SC8三项在Mac普通用户前景完成正式3过及独立passed登记；共享C1重启SC7补原半传/首次pending默认配置0，并覆盖每端12目标的partial、empty-success、旧ready加新pending配置1。逐目标冻结CID/AID/config/created_at、独立全文顺序/全表/原件及旧请求存储不变，正式4过44.71秒，新上下文执行复审passed。18次停止中的4次屏障强停与14次正常停止分别保留，不认运行中worker或原生服务恢复。

新增SC10两个有限组件用例：六项真实字面数值边界及加1拒绝，17个真实PDF过滤器/预测器/嵌套Form/压缩对象及reader守卫实例。预测器原件在guard前由原生reader核固定像素；所有真值来自源材料，纯原生文字不强迫渲染。正式分别6过1.44秒、17过1.13秒，新候选和新执行Reviewer均passed。只认各自分配项，不从这些小样关闭完整PDF安全或其他资源预算。原错误和需修订意见保留，脱敏入口evidence/completion-acceptance-20261128.json。

最低Python补充采用独立可移植驱动而保留原Mac专用测试不变：从锁文件导出含hash的documents依赖，两环境分别同步后仅安装对应准确wheel，逐文件核安装资产，实际产品均3.11、-I、非源码cwd、Hub不能import Local；普通/全局每端八份四类文档，完整文本/全表/原件与移除源后的旧引用逐份核对。Mac准备调试5过，正式最低版本与其他OS仍按各次原件/复审记录判断。三OS专用CI使用实际普通身份，Windows新建独立无Administrators组账户，不能拿filtered管理员代替；只把控制端公钥交runner，私钥在启动CI前持久化并解密自检。CI调试/正式证据需官方artifact摘要核验、解密、逐文件打开及独立意见才能认passed。本补充不改变SPEC，不以最低安装替代完整E/H/X。

首轮专用CI 46091817689两POSIX作业成功，Windows真实标准账户两业务在输出全局项目中文名时因隔离测试命令-I屏蔽PYTHONUTF8而在cp1252编码失败，尚未到文档采集；测试CLI改为与通用Probe相同的-I -X utf8。采证另查明同一公钥的Windows CRLF字节指纹误拒绝：新producer以解码公钥的规范PEM计算指纹，decoder兼容同一精确公钥已生成的LF/CRLF指纹，原GCM/AAD、官方归档和逐成员摘要验证不变。合法UTF8-BOM JSON/清理记录可读，坏JSON仍拒绝；pack前独立冻结原字节，源和恢复分别核冻结值。两份opaque采证控制误用.docx后缀改.bin，真实格式样本不改。旧原包117成员认证/摘要正确但格式检查不完整的记录原样保留，未给recovered_verified。新最低版本和证据小样CI均统一使用启动前已持久化、自检的控制端公钥；失败原件继续保留，按新版本真实重跑及完整回收再认平台通过。见evidence/completion-cross-platform-diagnostics-20261128.json；不改变产品或降低SPEC。

2026-11-28续证：6811238的最低版本CI 46093625455三OS七项均实际通过，官方原ZIP逐摘要/长度核验、解密并逐成员打开后，各平台另取得独立限定范围passed意见。Windows实际无Administrators组的临时标准账户；Ubuntu24.04普通UID；Mac普通UID。每平台两包隔离3.11，16资料/32完整文本/64表格/304源单元及32次原件下载。Mac本机同候选另有正式7过19.051秒及新执行意见；证据格式正式19过1可选旧样本skip，当前真实CI原件回收正式14过无skip并独审。该回收小样只有一个HTTP服务及其监听/线程，不是H服务验收。各原件和脱敏意见入口见evidence/completion-platform-proof-20261128.json；历史错误不改判，完整E/H/X仍未关闭。

为覆盖常规CI未安装OCR/浏览器导致的跳过，增加独立source回归入口及三OS专用CI。先安装锁定依赖、明确准备真实OCR/语言/字体和Chromium，再在普通身份执行全部document及hub_documents源码测试；Windows仍创建不含管理员组的新用户。每个pytest item单独分配原始证据命名空间；整个任务work连同pytest-tmp、准备/控制器原始stdout/stderr完整加密保存。敌意格式原件保持原字节装入tar并逐SHA核验，不按扩展名冒充有效文档；链接/junction在递归前识别，只保存目标及类型元信息，禁止跟随。采证和加密使用独立于产品依赖安装的解释器/cryptography入口，准备失败不靠重新安装产品掩盖。该方法属于C1源码回归，所有skip、失败和原始stderr按实际记录，不能替代E安装包、H受管服务或X无组件接收。候选先独立复审、小型本机/Windows真实junction控制，再进入三OS调试，正式覆盖按所得原件及独立意见单列。

2026-11-28跨平台继续：真实Windows CI把venv启动器PID与门内实际Python后代PID相等比较而失败，改为验证登记启动器树内的实际PID/ctime/完整argv/物理解释器、源路径与token；Mac补声明当前控制器实际framework executable，与已有Server设施一致。当前Mac/Windows各六项实际进程/源读控制通过。Ubuntu22.04补充正常处理32次中一次复现看守退出1，原stderr精确指向测试hook对正常退出空argv的断言；观察器仅对可核验活任务注入故障，退出/额外观察元信息消失时原结果原样返回，不修改产品监督逻辑。新40次无异常且实到6次空argv；原24.04CI与历史内核AccessDenied完整因果链不据此认定。Local/Hub各12故障目标候选分别1过38.32/220.63秒并独立passed；组合首轮附加控制失败及34MiB证据超限保留。拆创建端只为保存全部原件，不减目标或断言；最终同版正式复验仍待完成。

同轮发现清晰扫描原件的编号73428被读成/3428，CER为1/48=2.0833%。保留原debug8并以相同原件/独立绘制真值补入原OCR质量TC，与原中英双页网格同次执行；红灯实际1失败3通过，经独立原图核对为expected_failure。修补仅将固定二值化阈值180替换为实际灰度直方图的有界256级类间方差阈值，pipeline记为v3并保存实际阈值；300dpi、16MP、30秒、整任务预算、OCR次数/PSM、本地组件路径及保存的旧结果均不改变。相同冻结测试4过8.02秒，原生零OCR、混合PDF和首次失败重试13相关回归过13.03秒，独立绿灯passed已登记；只关闭该质量修复，不认完整E/H/X。新两包已重建并核OCR模块逐字等于当前源，最低安装CI及source CI触发增加产品/依赖路径，确保此类修补实际触发新版本回归。旧CI和旧包证据保留精确版本；最终CI/原件回收、完整平台业务及需求级判定另列，不以本段数值代替。


2026-11-28：补齐实际完整源码回归时，保留并逐份回收4edd旧三OS官方artifact、GCM原件及内部raw tar。Linux为345过8失败14跳过，Mac6失败、Windows15失败；不将旧结果重写。修订C1测试设施：Hub CLI已交服务执行，因此配置发布门/刷新worker按实际service PID、ctime、argv和owned tree核身份；仅并发刷新项启用request-scoped读守卫，读请求仍实际拒源文件/解析/子进程，明确的创建动作可正常处理，默认全局读守卫不变。统一Windows launcher-tree与实际exe路径比较，冻结历史CLI字节为LF，restore内部清单键用POSIX相对表示；发布等待绑定实际CID/AID及非publication_pending，网页下载绑定本次真实response而非上一条事件。C1控制器显式放入源码namespace、按pytest item隔离全部原始证据，并准备SHA绑定的任务自有uv副本，避免Windows凭据子进程丢失setup-uv PATH。后者仍须新真实Windows CI；28项Mac同版分item实跑通过216.99秒、286源码before/end相同，经同候选独审passed，不能替代三OS或完整E/H/X。

2026-11-28：实际Windows旧完整源码原件另暴露真实产品问题：两端网页更新在替换reclamation/retired.json时WinError5，新CID失败而旧发布保留。真实Windows组件复现覆盖三个GC元信息JSON，先登记测试观察器exe大小写/链接回收故障needs_revision，再以真实DOCX两次公开refresh准备非空旧集合、独立磁盘JSON和真实CID/AID取得3失败1正控通过的业务红灯并独立expected_failure。实现仅在Snapshots中为archives/owners/retired的短读与原子写统一metadata.lock，不持到解析/网络，不重入capacity.lock，链接/特殊文件仍拒绝；既有prepare-restore已排除整个reclamation目录。完全冻结同版测试真实Windows4过12.95秒，Mac last-use/pin/身份/备份等相关回归22过2Windows专属跳过46.67秒，独立绿灯passed登记。此Windows SSH组件身份为管理员，不认E/H普通客户端或网页修复已通过；实际两端网页更新、新head三OS CI和原件回收继续。两独立wheel已重建并核shared模块逐字等于修复源。

2026-11-28：最低Python311实际三OS新run46101806180在e233848源上均独立passed，1720清单原件全部重算/打开；每平台16原件、208源文字单元、32源表/152源格，前后32全文/64表/304格次/32下载。仅最低安装，POSIX未有独立最终树/端口扫描，不冒称完整E/H/X。两端watchdog-health补动态工厂绑定至94文件后，12目标各完整正式执行/独审：Local41.41秒、Hub241.79秒；第一次Hub正式请求漏timeout而默认60秒，保留insufficient_evidence，另精确正常关闭该任务孤儿服务/子进程及端口后以300秒新记录完成，不改产品预算。上述watch及最低安装适用GC修复前的精确源；最终当前源覆盖另据新CI/需求级结论。

2026-11-28：提交可复用的独立安装包CLI/HTTP/stdio/网页主路径驱动与只读/定位探针。Mac e233848 wheel的32份ready资料、路径/选择/拖入、普通/全局和正常无待办重启已候选v3独审passed；Word cell path与可选字符span按独立源部件定位桥接，32全文/72完整表正控和316拒错控制完整保留。只认ready读取子域，不据此取消完整E1生命周期/关联/同步/深表及三平台、H1–H5和X六方向。新脱敏汇总见evidence/completion-current-recovery-20261128.json，原始证据/旧失败仍私有持久保存；PR保持draft，不合并。


2026-11-28：继续补齐网页上传原缺口：两端真实浏览器在普通选择/全局拖入两轮三格式中，逐空项目、pending/processing、ready及最终切换项目核完整DOM ID集合/数量/唯一性；第二轮门内逐全部旧三份核状态/详情及独立全文、全表、原件保持。观察器以实际浏览器DOM正控及漏首/漏后/重复/外项目/空项目残留/坏行反控验证。两端候选分别4过并独立passed，正式再各4过并取得新上下文执行passed，已原生登记。原25MiB超限及Local v2有效调试均保留；完整证据不减，既有JSON无损包装改为JSON超过8MiB或全部附件超过20MiB时启动，保存gzip及原字节双摘要/长度，所有截图/trace保持原字节；每次绑定全部产品与实际递归测试/动态helper113文件，不复制无关测试设施。Hub轮询先清空后await造成部分截图瞬时空库，独审实际打开对应trace完整DOM和门内旧资料读回，不声称连续每帧展示或据此关闭E/H/X。

0320622新最低Python CI46107496120三平台各7过0跳过，官方ZIP长度/摘要/认证信封及1720解密原件均实际打开，另取独立最低安装passed。每平台16资料、32全文、64全表、304源格次、32原件下载，均保留源移出后原ref；POSIX仍不认未记录的最终树/端口扫描。脱敏报告和精确版本入口evidence/completion-web-and-minimum-20261128.json。完整源码C1、E1生命周期/关联同步/监督、H三服务、X六方向及最终需求/PR审查继续，PR保持draft不合并。


2026-11-28续证：0320622完整源码原件分开核验：Linux357过1失败15跳过（已完整回收），Mac356过2失败15跳过、Windows347过3失败23跳过（两者仅认证选定原始诊断，不冒完整成员回收）。旧网页失败来自各次DOM重绘后分次innerText读到空第三面板；观察器改为单次实际浏览器evaluate冻结connected/open/可见文本和三个JSON，只在断开或details关闭时有界重取，错值仍立即拒绝。真实同步整行替换/三错值反控保留；两端新正式各5过并取得独立执行passed。旧CI不改判；Windows该轮GC四组件与两端真实网页更新/删除在原JUnit均passed，仅按精确旧版记结果。

同轮Windows另一失败为实际备份复制PermissionError：Hub正在持有的services/hub-processing锁被公开prepare-restore误列作可恢复数据。新增真实活Hub租约并按公开清单复制，与原三分支、六资料和旧布局一起执行；有效红灯Mac1失败5过、Windows2失败4过并独立expected_failure。产品仅在运行排除集合加入services，不在测试里跳锁；冻结同版绿灯Mac6过28.75秒、Windows6过90.82秒，另18相关回归过/1Windows专属跳过，新上下文独审passed登记。各分支持久raw/results/transfers、数据库、当前保护逐字一致；Windows SSH管理员身份只证明锁组件，不认E/H普通客户端或原生服务。

发布提示的旧Windows原trace另核实：上传结果先显示成功，随后await资料列表刷新，通知在同步读取后59.443ms真正变为完成。保留原24流程/端及48状态图，最终通知使用原拒绝/成功表达式有界等待，另真浏览器控制拒绝永久processing或错误终态；候选独审通过，完整新执行另列。为避免每次诊断都必须下载数百MiB整体，源码CI新增固定名单的原始诊断小集合并独立加密上传，逐原字节/SHA保留，准备失败也列missing。完整归档、认证、上传及验收实际打开原件要求不减少，小集合不能认full recovery或业务passed。上述两项是观察/采证方法调整，不修改产品行为或SPEC。脱敏入口evidence/completion-c1-browser-and-restore-20261128.json；E/H/X及最终交付继续，不合并。


2026-11-28 X1候选方法补齐：使用三个实际OS creator与六个不同OS基础Hub receiver独立CI，传输包仅含合成原件/创建端结果/独立真值/实际平台与身份收据摘要；token、DB、签名材料和完整身份仅在私有原件。接收端在实际-I产品解释器中先核处理库不可导入、产品prefix/PATH/显式OCR变量/常规OS路径中无OCR和语言数据，再安装任务私有观察hook；不能以configured=false或禁止调用代替未安装证明。少块、缺结果与stage阶段用同一组合法未来引用逐份核text/table/info/original拒绝，正式发布后相同引用成功，并核完整唯一文档/origin全集、丢回执重试及真实重启；签名只从任务独立库只读取得用于观察，不写库或绕过HTTP接收。

共享E/X观察设施增加实际system/spawn/fork/exec、UDP/stream/DNS通道，stdlib socketpair及任务已accept的stream回复采用真实调用帧/套接字端点限定。MCP仅放行冻结完整实际argv与准确DB；实测Windows3.14.10原生CreateProcess事件命令行损坏，因此仅在即时canonical subprocess.Popen._execute_child代码对象/模块全同的调用帧中读取实际参数，原始事件原样保留，直接private API及错命令仍拒绝。Mac29过1Windows专属跳过、真实Windows管理员SSH24过6API缺席跳过，独立候选v2 passed；同OS协议组件4资料passed但明确x1_qualified=false。三creator/六receiver均待实际CI、完整原件回收和独立执行意见，不认X1或整R008已通过。只调整验证方法，不改变SPEC行为；入口evidence/completion-x-candidate-20261128.json。


2026-11-28安装内容子域续证：新增installed_extended与独立执行入口，在原32份基础上补两端各两复杂XLSX（两日期制）、243行深Word/深XLSX及混合PDF共10份。Mac普通UID在精确restore修复wheel、冻结v4探针完成42份各入口与源文件移除后旧引用/正常重启读回；独立候选v2 passed仅该子域。2983真实命令原字节181787323在结束后无损gzip，保留双SHA/长度、10原trace/130PNG及全部原始响应/下载；不因压缩删减观察。工作进程仍是产品原有-B/-m并实际isolated=0，入口才是-I，均记真实prefix/cwd/身份。新document-formats-installed-content.yml在三实际OS复跑同内容子域，不能冒全E/H/X；Windows普通账户清理改为按已保存SID先撤ACL再删账户。真实Windows小控逐根/子文件核SID已去、其他ACL保持、账户/目录实际消失，独立候选v2通过；刻意先删账户后的旧SID实验1332失败保留。实际三OS业务、完整原件回收及独立执行意见另列。冻结Mac结果早于后续网页刷新稳定性改动，不称最终全部资产同版。入口evidence/completion-installed-content-20261128.json。


2026-11-28网页稳定性补充：真实状态采证另观察到两端资料库在同项目刷新请求发出后、响应返回前先清空旧行。用真实服务响应route.fetch后仅延迟交付（字节不改）的双项目浏览器控制取得两端红灯，独立意见确认有效UI复现，未据此签成原SPEC失败或错clip唯一根因。两HTML改为同项目await期间保留旧行，切项目立即清空；最新响应校验后同步重绘，陈旧响应继续拒绝。同冻结测试两端2过，另实际验证切B待答旧A不出现、先回B后回A仍为B，独立绿灯passed，4原PNG/原trace已打开。该小型健壮性修复不改变业务授权/引用或SPEC边界，Hub只读与无项目分支仅静态核对。完整发布24流程/48图每端继续单独原生执行和新上下文复审；候选passed不代替正式结果。入口evidence/completion-library-refresh-20261128.json。


2026-11-28发布状态采证补齐：原两端各24流程/48业务画面及各48全文/72全表/48原件不减。实际Locator截图成功仍可能是已替换节点的错clip，故观察设施v5显式绑定同一ElementHandle的before/screenshot/after；仅实际断开可重取，成功还须同Handle连接和绝对文档几何稳定，已生成的拒收PNG原字节另存，不改图或抹去。真实静态离屏像素、首截图后实际DOM替换红→蓝、独立等待中替换及连接但隐藏时原错传播均有正反控制。候选两端逐图/逐原件passed后，同源正式Local4过49.51秒、Hub4过53.84秒，新上下文执行Reviewer分别核815/801附件、58/52PNG及115冻结源，三publication分配passed均已原生登记。原错图、detached、v4 Local正式失败及Hub旧私有passed但因提前改公共源导致native登记blocked均保留；v5在全部登记前不再动所绑源。只关闭该子域，不认整个SC1或E/H/X；精确源/意见/限定证据入口evidence/completion-publication-state-20261128.json。


2026-11-28 Windows E/X准备修订：df7真实标准账户SID/session2已启动，安装Local资产核验exit0后控制器读取原wheel遇PermissionError，两条都尚未开始文档业务。原失败未留ACL，不推断protected DACL/deny ACE或uv机制。新入口复用minimum的wheel-only ACL处理，限定本任务Work内实际.whl且拒link/reparse祖先；Local可缺、Hub必有，以兼容基础receiver。即时记录通用Work grant之后、wheel修订前后ACL；E/X实际业务控制器在Probe之前另记录同SID/session/实际ACL与整wheel字节SHA，继续保留原安装校验。Mac实际双包/Hub-only正控及错误预备SHA拒绝；HomeWin私有session0子进程微控未取得completion，保留失败，不据此认ACL可读或猜启动原因，也不豁免正式session>0。独立静态和Mac控制意见认为ready_for_actual_CI，后续以真实CI普通token继续取证；私有NoNewWindow探针不带入正式入口。仅改变测试材料准备/诊断，不改产品权限规则、SPEC或E/H/X验收义务。入口evidence/completion-windows-wheel-preparation-20261128.json。

2026-11-28 Windows新一轮原件诊断：4d真实标准账户通过原wheel读取且E完成16份路径资料；首个浏览器失败定位控制器转账号后未继承PLAYWRIGHT_BROWSERS_PATH，非产品异常。测试准备将任务绝对browser cache写入配置/read_paths，实际控制器在Playwright driver启动前恢复；准备时目录尚未下载允许不存在，执行时须存在。显式browser优先，不受另一个失效cache设置阻断。两方向Windows X原日志显示发布请求在boundary读body时ClientDisconnect，尚未发布而非已保存丢回执；修订为真实HTTPS读取200响应头、关闭并丢弃应用层回执正文（不read/JSON解码，底层可能预读），再独立确认四份已发布后幂等重试，保留未来引用、完整集合及真实重启。两次旧失败及原件保留；Mac同OS组件通过只证明协议探针，不认X方向通过；最终按真实CI原件和独立意见判定。不改变SPEC或产品行为。

2026-11-28 生命周期实际补测发现并修复首次失败后重试的来源标识遗漏：真实安装包中本机重试发布ready，但captured_by_source_id仍NULL，获准同步后processed/begin两次400，其他五份可接收；独立从实际HTTP CAS和wheel/源快照确认。创建端_publish_reprocess在发布同一事务内选当前capture连续有效且revision匹配的来源，仍合法旧collector优先，否则确定性选择；不放宽Hub边界，无源回滚。旧实验档案通过当前retry_target明确reprocess恢复，同原件/profile/结果时不改已发布V/P或引用，不增加隐式同步迁移。保留真实初次失败红灯、缺失/退休来源2红1绿、修复6绿、确定排序补强4绿和受影响10回归；这些执行有重叠，不合称独立总数。新wheel安装后完整生命周期/同步、三平台和服务继续另验；入口evidence/completion-retry-collector-20261128.json。

2026-11-28 原生Windows服务能力先行验证：新增实际SCM/LocalService的最小Word上传探针，使用精确安装包、原服务启动及工作进程，无解析器/PYTHONPATH/服务环境替身。项目由固定白名单管理员CLI创建，真实非管理员交互会话客户端经认证HTTPS上传并读取；先验证服务工作进程可导入安装模块，再展开H1–H5。复用007SCM设施的可选factory/runner/wrapper，默认启动方式保持，008仅向受限Work复制同摘要wheel。公共清理观察变严：每次原生命令保存实际返回码及原stdout/stderr，删除前后实际查询本任务SCM注册项和防火墙规则，查询错误、超时或残留必须失败，不能以删除命令exit0代替不存在证据。候选独立v2仅判静态ready_for_actual_windows_ci；不据此认Windows业务、OCR或完整服务验收通过。方法调整不改变SPEC及产品权限，后续保留实际失败和完整私有加密原件。

2026-11-28 原生SCM最小Word实际红灯：CI46133002388的标准非管理员session2通过HTTPS提交，LocalService19/session0父服务正常，真实任务因base Python找不到smm_hub失败且无发布。官方artifact15258334469完整188成员认证回收并独立确认P1，不以Mac组件代替Windows证据。修复监督器仅no_site服务上下文：同一base解释器直接进入原Job，用-I-S及显式当前受保护安装根加载包/依赖后runpy；不使用venv launcher、不继承cwd/PYTHONPATH/base site，不改变stdin门、资源预算或清理。普通前景仍原-B-m。实际Mac无site/污染cwd与PYTHONPATH模块入口及相关观察3过1Windows跳过，仅局部；同一冻结SCM Word重验及完整H1–H5继续，不能据静态候选就绪关闭红灯。

2026-11-28 服务导入红灯闭环：10d真实SCM Word复验46133972702完整191成员认证回收并取得独立执行passed，实际服务Job worker完成发布，标准账户检索/读回正确，原失败保留。仅关闭该导入缺陷，不认完整H；防火墙前后0只证明无残留，未冒称删除了存在规则。

继续新增统一安装态生命周期与原生服务驱动，普通E沿用同一业务/断言，由真实三OS身份分别执行；POSIX H使用实际system launchd/user-systemd而非前景等价。新Web创建项目四资料用独立命名，不复写已有fixture原件；缺语言期间读原生三格式和已接收扫描件，真实OCR进程与native stop发出相配，停后启前须未发布才认中断，pending同AID或failed按公共retry_target同CID新AID恢复分别记录。测试设施调整：HTTP解析前持久保存原status/bytes；详情截图绑定同一handle展开及JSON/几何前后，拒收图原字节保留；任务门由.pth显式绑定参数以适配服务无登录环境；默认关闭检查历代正文/身份/结构文件名，授权前先全SHA验证接收缓存，合法received全offset复用不强制重发，冷raw/result仍实际观测且逐origin公开完整读回不减。E7实际SQLite I/O根因未定；E8重绘折叠、E9文件名桥接、E10过严缓存重发控制分别独审为设施问题，均保留失败，不改判整E通过。完整E、H三服务、当前CI原件及最终PR Review/需求判定继续；入口evidence/completion-lifecycle-native-candidates-20261128.json。

2026-11-28 生命周期设施续修：项目归属拒绝测试通过真实sources的source_id→revision映射取比较值，不要求files提供未约定字段；完整读回增加独立Unicode/LF窗口公式，实际网页选择合法limit=50，并核可见全文和逐格坐标/跨度/文本全集。可选Playwright导入移到实际浏览器测试函数内，普通CI无acceptance依赖时仍可收集并明确skip，不能用该skip代替E/H。真实Chrome正文/表格观察正反控制另运行。E12已进入真实重启后的读回，但本机SQLite I/O/Tracing.stop ENOSPC造成未完成，原失败、不可正常打开的trace和实际PNG均保留，不改判通过；已结束环境及浏览器证据完整SHA校验后无损归档到任务私有测试机，后续以提交冻结的真实三OS CI重验，避免本机空间继续干扰。方法增强不修改SPEC义务。

Windows服务验收分层补齐：先独立运行四格式真实标准浏览器能力组件（不称完整H），复用原SCM安装、保护ACL和固定维护RPC，依次核项目创建、四格式全文/全表及可见DOM和原件SHA。管理员只配置冻结OCR路径/权限和观察，不承担实际解析；采样真实OCR、worker、SCM进程token的SID/session/内核创建时间，与前后PID创建戳、argv、父链及原子Job监督记录绑定。身份观察器以真实Windows self/own-child、whoami SID及错SID/session/AID/parent/creation控制；网页观察以真实Chrome缺cell、错坐标/跨度/文本反例控制。组件之后仍按专用H驱动补H2接收零处理、H3持久/活动OCR停启、H4缺语言与真实worker异常及H5实际清理，不减少已确认H1–H5。只调整测试实施方法，不改变产品权限与SPEC。

完整Windows H使用专用SCM驱动继续：普通Local仅复制自己的测试观察环境，不能复制或写Hub程序/档案；Hub观察器由管理员预置在本任务受保护安装根，分别接受已实测维护身份和LocalService，内容入口及worker/OCR启动仅允许LocalService。维护RPC固定当前任务路径和动作，保留每次真实CLI返回码及stdout/stderr供拒绝理由核对；当前活动任务的AID、PID/创建时间、模块/参数、服务祖先和原子Job同时核对后才故障注入。H1四份网页及一份CLI路径、H2扫描投影/零处理/真实OS拒读/越端管理、H4首次与替换缺语言保存重试和实际worker异常后五秒回收/下一合法任务，H3三类真实OCR在途停启及原文引用持久读回，均独立保留实际结果。原生清理仍复用受限SCM删除前后注册/规则查询和进程端口验证，不触碰日常服务；长客户端的测试设施截止时间单独增加，不改产品预算。候选先编译与独立复核，再进入真实CI调试/正式执行；此前Word及四格式组件不代替完整H。
Hub CLI原件由管理员实际输出到管理员自有、标准账户只读的任务目录，再以实际SHA/长度核对的IPC收据交标准账户自行保存，避免标准账户可改目录决定管理员输出位置。真实OCR允许任务的自动续办单独绑定当前授权AID，在resume-captured窗口启动并等终态；不把普通查询/服务控制窗口全局开放解析。无待办正常重启从启动前开始收集全局事件，仅将实际维护身份、当前state-dir、冻结SCM映像及本任务sc/netsh/ACL完整命令相符的管理启动排除；所有业务子进程/解析/OCR/源文件读取仍必须为0。
Windows E新失败46139824520已独审：真实负控子解释器拒绝连接，但计数窗混入已有Local进程的合法Hub流量。自检现在按本窗唯一实际owner/argv/身份/PID归属，继续要求隔离/UTF8/实际SID/session/is_admin、准确解释器prefix及精确拒错类型；他进程任何源文件/处理/child或被拒网络仍失败，业务assert_read_only继续全局不筛PID。原失败与396原始事件不改判，身份归属回放只为测试修订依据，新冻结CI另执行。
POSIX新H中断失败的实际原件另核：Linux读日志时遇尚未追加完的JSON尾行，最终日志均完整；macOS真实新launchd进程的合法process入口被service-control观察阶段拒绝，未启动新worker，不能据此判产品不能恢复。统一观察修订为仅消费LF已提交记录、跨文件保持已消费前缀稳定，停止全部写入进程后必须严格核无残尾，完整坏JSON/日志截短仍立即失败。真实split UTF-8/JSON写入和较早时间戳迟到记录正反控另验，绝不丢完整事件。续办窗口在三平台复用当前AID匹配：服务父入口核frame的capture.attempt_id，worker解析入口核实际task-token；启动到终态不得出现观察器拒绝，不得把设施造成的failed转为成功retry。正常无待办重启包含启动前全局观察，只排除核实维护身份/当前state及本任务完整原生命令，业务子进程/解析/OCR/源文件打开仍为0。此为修正测试干扰，不改变产品或SPEC。
C1失败详情用例新增采证修订：旧Windows6e1官方triage仅足以确认分次inner_text→JSON解析失败，旧DOM未在该小集合中，不能独立推断具体重绘。沿用已审同ElementHandle前/截图/后原语，保留两端各普通/全局两个项目、OCR/加密两类独立原件及全部错误/CID/AID/retry_target和源字节/mtime断言；不改产品。Mac真实Chrome新调试3过、8图与两trace已独立核验，可进入三OS source CI，但不称新Windows或整C1通过。长错误在真实可滚动详情中，单截图只体现当时视窗，完整字段与trace仍保留。
原生SCM四格式4370实际组件46140116105已完整回收369成员并独立限定passed，仅关闭Web四格式能力；不认完整H/E/X。完整H25d首轮46141857743另有真实H1红灯：管理员合法CLI采集的2601字节Word原件保存正确，实际LocalService worker读该raw报PermissionError，V/P0且未发布。独审排除字段桥接、异步pending及观察器故障门；第一轮没有raw icacls，具体DACL根因不猜。下一轮测试只增加管理员只读原raw/目录icacls及SDDL、owner和字节SHA收据，不在验收中修权限，保留实际产品失败供定点修复。脱敏入口evidence/completion-native-formats-and-cli-permission-20261128.json。
后续补证还将首次实际OCR UID/创建时间、父worker/AID和服务创建事件即时保存，不等全部三动作完成；取得完整采样并落盘后才将其当作held目标。异常中止时由probe保留拥有的stop线程，外层清理先有界等其结束，仍未结束只报告deferred/error，不并发发送第二disable。该边界已独立静态复核就绪，新的真实业务仍待执行；验收不会修文件ACL或代替产品权限修复。

2026-11-28 Windows跨创建者快照权限修复：f50真实SCM第二轮已完整回收689原件，实际raw目录owner为LocalService但DACL仅OWNER RIGHTS/SYSTEM/Administrators；四网页raw由LS创建可读，管理员CLI的2601字节raw由管理员拥有，实际LS worker读同SHA原件PermissionError。独立复审支持真实H1权限缺陷，快照根本身仍有继承LS权限，不把它误写为根也无LS。
实现限定受管Windows Hub新008快照目录：Hub显式配置db目录工厂，Local、无服务profile前景Hub、POSIX及007 `.documents` 均保持原策略。setup/enable明确管理员动作以固定root handle仅设置OWNER为Administrators；不设置DACL或递归改子项。内容目录先核真实Admin/LS actor与根owner/DACL，用NtCreateFile的RootDirectory逐单组件创建/打开，新建时原子附固定BA/SYSTEM full、LS modify的继承DACL；existing仅核不维修，reparse拒绝，既有未发布008坏目录明确报错。管理员家目录等外部祖先不增加list/read-security要求；不通过扩大祖先ACL帮助产品通过。shared snapshot桶、processing AID和transfer ID使用同一工厂；旧文本管理路径、旧文件ACL/owner/内容不改，不新增全树迁移。官方API依据为NtCreateFile的相对目录与仅创建时应用SecurityDescriptor、SetSecurityInfo的OWNER单独标志；不用filesystem禁用的SetKernelObjectSecurity。
Home真实Windows管理员SSH只做组件：v2 rename pin失败保留；v3补实质目录read access后2过；v4为机器默认owner假定错误，未通过；最终v5显式构造个人SID owner再做负控，2过9.04秒。新目录并发/继承、existing700拒绝、旧child及外部hardlink的完整owner/DACL/字节不变、root仅owner改变而DACL不变、rename/junction/越界/宽根拒绝均实际检查。此不是LS处理或普通交互客户端证据；新SCM完整驱动另把Hub放在LS仅X/RA的任务祖先下，真实LS逐项验证祖先LIST/READ_CONTROL被拒且state可读，再按H1–H5完整业务复验。两wheel构建且新模块与shared文件逐字匹配，不据此宣告H通过。
POSIX f50中断恢复另实际取得原CID显式重试成功、旧引用原文/全表/原件一致及服务清理；首失败只有新增文档后旧命中的动态bm25_score改变。测试仅将hit.bm25_score从发布稳定值比较中归一，仍要求有限数值，保留其余完整hit、origin/V/P/资格/正文/表格/原件与旧ref逐项一致；新增真实前后分数及错身份/版本/资格/正文/单元格/字节与非有限分数拒错控制。历史run仍失败，remove/replace及最终全入口重放需新实跑，不以局部恢复冒完整H。
