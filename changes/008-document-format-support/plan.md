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

POSIX监督至少每100ms检查任务树/单调时间及任务目录实际字节，以进程组和已登记后代处理退出/重父化；任何持久PID记录都须同时核创建时间、任务身份及租约，不能只凭复用PID杀其他进程；执行终止前核PID、创建时间、任务token/租约及程序身份，不按过期PID记录误杀重用PID的其他进程；Windows Job Object禁止breakaway，配合RSS观察和整Job终止。访问拒绝/观察盲区时停止该尝试并报监督不可用，不继续无监督处理。完整OOM/预算实验在隔离档案串行运行，保存实际树与终止证据，不通过调低生产预算冒充1GiB实测。按SPEC实证5秒终态/槽位恢复及主服务查询存活；各OS不宣称同种内核硬限制。[Windows进程组约束](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)。

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
