# PR #33 独立审查与返修复审

## 审查对象与结论

Reviewer：`/root/review_006_pr`，独立于实现者。本上下文在 PR 创建后接手，实际读取并执行 [PR Review Prompt](../../_templates/pr-review.prompt.md)、仓库 AGENTS.md、006 [意图](../intent.md)、[规格](../spec.md)及[计划](../plan.md)，没有实现产品、改测试或降低验收条件。

审查基线为已合并 PLAN 的 `f797fe843430b48faf379cd76b4ae18fd52f5c64`；产品、测试及探针最终审查头为 `a66deeb15ad2480d1cb9b6a9555822d299daa996`。本次同时审查该头之后待提交的维护证据入口 `scripts/acceptance/README.md` 以及实际存在的 `evidence/` 脱敏导出，不能只按已提交的旧进度判断。

当前代码、用户/Agent/维护者路径及 A1–A8 所需执行证据的审查通过，未发现尚未关闭的产品或路径缺陷。最初发现的 P2 Unicode 定位错误和返修中额外大小写等价抢占片段的问题已由最终实现及新轮证据关闭。平台独立审查指出的 Windows 首次停服缺证，也已在新轮以真实服务 PID 与端口的时间线关闭。

本稿初次落盘时，原生 8 个场景均为 passed、29 项用例有独立 passed 意见，R006 为 `pending_delivery_review`。这不是 R006 已通过或已合并的声明。合并前仍须读回独立需求判定、最终原生收据/看板、最终证据导出和最终提交 CI；后续仅增补这些材料时在本稿追加复核记录，不把尚未形成的证据预写为通过。

## PLAN 对照与实际范围

- P4–P7 的位置与职责一致：`documents.py` 保存来源、成员资格及文件级当前快照；`core.py` 创建普通项目并在合并事务迁移文档绑定；`project_control.py` 将相关绑定纳入确认摘要；CLI/API/MCP 与 Web 使用共同后端。没有将文档伪装为对话、进入 federation 上传/查询，或新增后台 watcher。
- add/set 保存 pending 配置，只有明确 refresh 打开源正文。扫描先检查完整来源预算，再有界读取并核对文件身份；发布检查配置版本、刷新身份和跨来源请求序号；失败/缺失后的连续资格与内容版本分别处理。search 在一次 SQLite 读快照内固定范围、来源与文件，read 校验档案/版本/原资格后只读采集文本。当前源码及场景证据支持这些边界。
- 共用 core 只在 Local 文档表存在时迁移绑定，不导入 documents；独立 Hub 包回归验证这一方案。现有对话 DTO/CLI/MCP、上传规则及默认联合查询继续保留。
- 测试按职责拆为 `test_document_*.py`、独立 checker/MCP worker、Windows NUL 设备名与 TestClient portal 调整、Unicode 返修及 Windows 真实服务退出核对，均已在 PLAN“实施时的验证组织调整”说明原因与验证方式。未发现未说明的方案/修改位置偏差，也没有以实现困难缩减 SPEC。
- 007 Hub 文档、008 其他格式、语义检索、历史全文读取、编辑/上传授权及正式发布没有被声称交付。当前未发布版本仍使用 0.4.0 字符串，材料以源码/wheel/安装摘要证明版本，避免用字符串代替实际字节。

## 从实际主入口逐角色回放

意图影响两类主要使用者：希望明确纳入项目文档并查回准确原文的人，以及需要用文档原始依据回答项目问题的 Agent；另审查维护者取得包、复跑并核对本次结果的路径。以下每跳均实际读取可见内容，Web 操作用本轮原始轨迹/响应/画面核对。

| 角色及步骤 | 当时可见内容、下一步 | 判断 |
|---|---|---|
| 普通用户发现能力 | README:33–48 主使用路径有“本机文档检索（006，尚未发布）”，介绍 Markdown/TXT、文件/目录、项目绑定、显式刷新、CLI/Web、三个只读 MCP 及仅本机边界；37 行指向源码开发或文档使用指南 | 用户能判断何时进入；明确快速开始 0.4.0/首次安装器不支持，未引导重复安装同版取得新能力 |
| 取得前置环境 | README 源码开发给 Python3.11+、venv、安装与 serve/Web 地址；README→TRIAL_GUIDE:58–68 给构建 wheel、独立环境、各系统 Python/入口及每命令同一 --db、MCP 同档案、无 Hub/管理员要求 | 已存在源码及 wheel 两条清楚路径；Windows 可以沿指南安装，不依赖仅 POSIX 的源码示例 |
| 取得路径和项目 ID | 指南第1–2步及 Web 文档表单说明：SMM 服务所在机的可读绝对文件/目录路径，不能用浏览器另一台机器的路径；Web 创建普通项目或“项目”页、CLI projects 取得本机 ID；全局独立、零/多绑定含义明确 | 输入含义、可选值与取得方法足够；新档案可以开始，不要求先有对话或目录映射 |
| 保存、刷新、确认覆盖 | README 示例及指南第3–5步、实际 CLI add/set/sources/files/refresh 帮助、Web 主导航“文档”给 pending→明确刷新、递归/默认排除/自定义 POSIX 模式、完整替换、状态/计数/错误及恢复 | 保存未伪装成已索引；不能把零命中当完整覆盖；局部必要信息充分 |
| 查到并读取准确依据 | 指南第6–8步、CLI search/read 帮助及 Web 查询/reader 给本机项目/一层关联、原样 reference、采集时间/版本/SHA、码点 [start,end)、2000/16000 限制、旧引用失效/重新搜索 | 三入口完成 search→read；不必查 SPEC；纯文本渲染脚本内容；采集文本未被称作实时文件 |
| 修改/移出/移除 | 指南第4/8/9步、Web 编辑说明及移除确认显示完整替换、根不改、来源独占材料退出、重叠来源保留当前版本、原文件不删除 | 用户能理解影响并恢复；没有隐式扫描或物理安全擦除承诺 |
| Agent 发现与使用 | README:127–137 的 Agent 接入可打开 Skill；Skill 描述包含文档，58–72 行有版本检查、list_document_sources→search_documents→read_document、真实本机 ID/原 reference、覆盖/采集版本及引用规范 | 文档/对话引用分开；管理走已授权 CLI/Web；不默认刷新、扫描或上传，旧安装会准确报告不支持 |
| 维护者取得结果并复跑 | README→TRIAL_GUIDE:82→scripts/acceptance/README 的006段首行“实际验收证据”→evidence/README；后者逐 A/E 链接29项覆盖、正式结果及独立意见、平台业务/画面/安装/身份/服务、回归/双包/两CI/原SHA/公开校验 | 原 user-v2 缺证据入口已关闭。复跑说明另给两个环境/浏览器依赖、目标JSON字段、Windows Limited、全新输出、摘要和清理；不要求维护者猜私有根或仅凭状态找原件 |

已实际执行 CLI documents/add/read 帮助等入口核对，且新一轮 user-discovery-v3 保存了11份实际安装帮助及完整逐跳记录。文档已写、功能测试通过、用户能发现并开始操作三者分别有上述依据，而非相互替代。

## 已确认发现及关闭依据

### P2：Unicode 小写文本偏移误用于原文（已关闭）

原 `documents.py` 在 `text.lower()` 中找位置，再用该位置切原文。独立临时新档案中，严格 UTF-8 正文 `"İ"*3000 + " needle tail"` 成功刷新 ready，search("needle") 却因原文3012码点、小写文本命中偏移6001而抛范围错误。该问题明确违反 B5/B6/A5 的合法长文及 Unicode 坐标要求，影响整个搜索，不是缺证或环境故障。

第一修复使用 IGNORECASE，独立再复现 `"ı"*3000 + " i tail"`：FTS 因尾部真实 i 召回，但正则把无点 ı 当 i，返回前2000码点、预览不含真正匹配词。另一正式反例以 `ſtopuniquemarker` 前缀检验同一问题。两轮都保留真实业务红灯，未改成预期成功：[展开红灯](../evidence/red-unicode/red-r006-unicode-v1-search-rank/result.json)、[等价字符红灯](../evidence/red-unicode/red-r006-unicode-v2-search-rank/result.json)，本 Reviewer 分别重算原件/绑定并给出 expected_failure、covers=[]。

最终 `documents.py:381–392` 保留全文 lower.find 语义，按原码点小写长度映回原索引。本 Reviewer 独立新档案复核原展开、dotless-i、长s及展开+emoji+组合字符+大写查询四例：窗口覆盖真实词，read 等于原串码点切片。正式 search-rank 的独立原串还核出长s反例窗口 [3200,3421)、展开反例 [2801,3026)，与 [新绿灯/旧引用回归](../evidence/tdd-green/green-r006-v3-search-rank/result.json)和[正式v3及独立复审](../evidence/reviews/review-r006-formal-v3-search-rank.json)一致。三平台新包均含实际3000个İ前缀，三入口窗口 [2801,3027) 可查可读。因此关闭该P2；未将旧包通过继承给新包。

### Windows 首次真实服务退出证据（已关闭）

这是平台原件充分性问题，由另一独立平台 Reviewer 在旧轮提出 needs_revision；不是推断产品已失败。旧启动器 PID 退出不能证明其子服务在重启前已停。新探针记录实际 serve PID，终止本任务进程树后独立检查 PID/端口；本 Reviewer 重读新轮 services/product 身份与正式意见。

Windows 首启动器12692、实际12608，在18:03:11.364888Z确认 actual_alive=false、port_closed=true；第二服务18:03:11.425776Z才启动。末次实际9088亦确认消失/端口关闭。Mac/Linux同样有首停早于重启及末尾检查。相应[当前Windows独立正式意见](../evidence/reviews/review-r006-platform-formal-v2-windows.json)支持关闭，旧需修订历史保留。

用户入口旧 user-v2 缺维护证据入口的意见也保留；本次实际逐跳到证据README/覆盖索引以及[独立 user-v3 通过意见](../evidence/reviews/review-r006-formal-v3-user-discovery.json)支持关闭，没有要求任意固定根文件重复堆叠同一份说明。

## SPEC 验收证据复核

[覆盖索引](../evidence/coverage.json)的29个TC身份不重复，24自动+2交叉+3平台；本 Reviewer 逐项打开其正式结果和当前独立意见入口，核独立意见均为 passed。24项自动正式v3的全部 artifacts/bindings 摘要与实际文件一致、实际退出0，未把 executed 字段本身当 passed。逐项判据的独立业务解释由索引对应意见给出。

| SPEC | 当前证据与本次判断 |
|---|---|
| A1 来源/输入 | SC1 source-config、entrance-contract：新项目/空档案、add/set pending、非法输入不替换、配置持久、CLI/MCP真实契约；平台Web表单及pending画面补实际入口。充分 |
| A2 扫描边界 | SC2 scan-scope/decode/budgets/read-races及cross-files-v2：真实上限、独立集合/计数、OS错误/竞态与链接/编码；平台原生换行、Unix chmod与Windows junction实际范围区分，未声称Windows ACL。充分 |
| A3 项目/去重 | SC3 project-scope/maintenance/overlap-version覆盖零/多/全局/一层、身份维护、重叠当前版本及资格；完整时间线和独立项目/文本集合。充分 |
| A4 生命周期 | SC4三个TC含改回旧字节、内容/资格不复活、失败恢复/重叠/移除，平台编辑旧ref/删除/重启另有真实入口。充分 |
| A5 检索/原文 | SC5四TC及本次P2返修：排序/文件去重/窗口/码点/行号/范围/引用负例/零命中覆盖，原字符串预期独立于产品切片。充分 |
| A6 并发 | SC6五TC用确定屏障/同次事务，核新意图/版本不被旧任务覆盖、资格中断与冻结范围；中断用例明确是持久状态注入，未冒称真实进程崩溃。充分 |
| A7 兼容/隔离 | SC7 isolation/compatibility/packages及user-v3：正文不走网络/对话设置，旧参数/帮助、双包独立安装，当前源码回归及三系统CI。充分 |
| A8/E1 | mac/linux/windows formal-v2均为新轮、普通账户、独立Local wheel/无Hub，真实CLI+Web+stdio、文件/目录/Unicode/项目/旧ref/失败恢复/删除移除/重启与清理；各有独立正式意见。充分 |

三平台 `installation.json` 的 expected=installed，本 Reviewer 将全部26个模块/HTML摘要与 git a66deeb 的 src 字节逐个比较，均相等；同轮 Local wheel 完整SHA为 `7ee93bfe55a6ceb9ad251144677c611b8099c5975b3c85c740318a04da631bd3`。各源/安装环境及真实产品身份有原件，不用控制机身份代替普通账户。Mac UID501、Linux UID1000、Windows Limited session1/is_admin=false。

本 Reviewer 另实际读取新轮9个原始trace ZIP中的动作/网络/帧记录：每平台主轮133动作/202快照，partial 13/18，restarted 50/65，无action错误；主轮有真实导航→配置→刷新→项目search/read、旧read400、重搜、set与remove，重启轮各五个read200。实际打开Mac原文、Linux partial、Windows restarted PNG，核采集元数据、错误可见、脚本按文字显示和展开字符命中。完整逐条平台原文/坐标重算及7张画面/3trace的独立复审见[平台索引](../evidence/README.md#e1-三平台实际完整入口)；这里没有声称重新跑了三台机器。

## 验证方法、原件与公开字节

本 Reviewer 在前次代码审查独立复跑来源/检索/并发/项目确认18项，18 passed；随后亲自复现两类Unicode缺陷、审两轮真实红灯并在最终映射实现上独立跑四组新档案反例。没有重复运行未变化的整套业务，当前整套通过来自原件而非本稿推断。

当前完整回归v4原process exit0，JUnit302项/0错误/0失败/1跳过，即301 passed、1平台限定skip；双包正式探针逐源码→wheel→安装验证 Local26/Hub24模块。a66deeb的[push](https://github.com/yangbobo2021/smm-local/actions/runs/45051663197)与[PR](https://github.com/yangbobo2021/smm-local/actions/runs/45051669927)两次CI元数据各有macOS/Windows/Ubuntu三个success job。本 Reviewer读回headSha和六job conclusion，不把该结果外推到尚未产生的最终文档提交CI。

本次实际执行 `python changes/006-local-document-search/evidence/verify.py --raw-root <本工作树>`，结果为 `Verified 1767 published files and private original SHA`。原/导出双SHA与脱敏方式清楚，合成正文、Unicode坐标、时间、状态、PID保留；完整trace、数据库/签名/配置/wheel不公开。公开清单与私有原件均能核验，受限原件的本次核验时间没有替代原平台业务时间。

## 初次落盘时尚待补录

R006独立需求级审查/原生delivery-judge、最终当前看板/finish、最终只增证据提交及CI和最终PR正文尚未作为本稿初次结论的通过依据。它们属于正在完成的交付步骤，不是已确认代码/用户路径缺陷；后续实际形成后追加确认。PR正文应记录本次通过项、真实历史失败及不发布/不升级日常SMM/不实施007–008的范围，不能保留过期“尚待平台”状态。

收尾检查另记录一项 P3 公开证据脱敏遗漏：`evidence/support/full-regression-v4/pytest.xml` 的 testsuite hostname 仍是实际个人设备名。影响限于公开副本，产品功能和原始验收不受影响；建议替换为中性 `TEST-HOST`，保留私有原件 SHA、更新导出 SHA/清单后核验，不需要重跑业务。此项须在最终公开前关闭。
