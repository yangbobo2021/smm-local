# PR30 最终产品独立审查：ba8c6d5

审查对象：`78973cf7ae6759332c0a320f630f5ebfb44204b6...ba8c6d5e86dbe0ecbb58214db14a22d4a556b7a0`。本轮从干净上下文实际读取 `AGENTS.md`、`changes/_templates/pr-review.prompt.md`、005 的 intent/spec/plan，然后审查产品 diff、测试和原始验收材料。写作期间 HEAD 到达 `9473a61779b6fd78e0ad64ca963478675333d462`；独立核对 `git diff ba8c6d5 -- src tests` 为空，产品和测试仍为 ba8，后续仅文档/证据更新按其实际内容审查。本文不是维护者的合并决定。

## 结论与发现

**本轮未确认新增产品缺陷或阻断使用的文档/导航缺口，PR Review 可通过。** 已知旧视图、远端竞争和范围读取标题问题在最终产品中有对应修复、同版测试及新证据。初稿时尚缺的 Windows 最终 ba8 安装包对账专项已经实际回收，本轮另读其原始安装清单、请求/两端状态、3张PNG、trace、包装器身份、退出和清理，原缺证项已补齐。各A/E必要行为均可由下文分版本证据支持；不把这句话扩大为每个平台重新执行了全部检查。专门平台Reviewer的最终归档意见和原生整体交付登记当时仍在进行，本PR意见不冒充它们已经出具，也不代替维护者合并决定。

发现分类如下：

1. **已确认产品缺陷：无新增。** 没有把规格未规定的全局跨端原子操作、已派发请求撤回、所有系统组合遍历等当作承诺。
2. **计划记述偏差：已修正，无功能影响。** 原 plan §3.1 写“通过类型唯一约束”保证唯一 G；实际 `core.py:604-609` 是 `BEGIN IMMEDIATE` 内查询已有 G 后条件插入。审查指出后，当前 plan §3.1 已改成这一真实方案。SQLite 写事务串行覆盖公开创建入口，SC3 还核对完整持久 G 集合，未观察到第二个 G。纠正只改计划文字，产品/测试字节未变，不需因此重跑平台。
3. **原待补证已补齐：最终 Windows reconcile21。** 真实普通交互身份、最终 Local wheel/全部安装字节、CLI 与浏览器旧双版本拒绝/刷新后成功、两端规则和请求、退出与清理证据已齐。最终页面的 `state=confirmed` 与 `transfer_state=failed` 是不同状态，后者保留外部规则变化时的实际传输错误，`allowed_pending_messages=0`；本专项只证明对账，未据它声称正文补传完成，也未因该真实显示新增一个无依据的产品缺陷。专门平台意见及原生整体交付登记仍需按实际完成状态记录。
4. **规格外建议：本轮无必须新增的要求。** README 已在正确位置介绍能力、适用对象与版本边界并链接指南；不提出再次修改固定文件的要求。

## 先对照 PLAN 的核对

- §2–3 的实际模块与计划一致：Local `upload`、`archive_protocol`、`project_control`，Hub `upload`，`federation`、`references`、`search_merge`、共享 core/importers，以及 CLI/API/MCP/Web。`project_control.py` 独立拆分、known-upload-messages、引用材料专表/Hub 自签、旧 Hub 逐消息兼容核验均有 §10 调整记录。
- Hub 的策略 CAS 和正文检查同在保护锁及 `BEGIN IMMEDIATE` 内；保护文件持久屏障、SQLite 提交及检查点分开，未把两文件宣称成一次原子提交。手工恢复和 `Hub.restore()` 都先 prepare-restore。新包构建 vendoring 包含协议及引用基础模块，Hub 不依赖安装 Local 网络层。
- §11 的 A→B 归属补充使用独立项目回执，当前允许时核对 Hub 同版本并增加消息归属；禁传 B 时不发送会话指纹，A 旧归属/旧引用保留。assign/map/merge 全部走绑定预览及条件确认。最终补强覆盖多会话、多消息与真实源头重放。
- §12/12.1 的对账补充已落到实际实现：CLI `--use local` 必须带所见双版本，Web 两种采用均带双版本；先取本机快照，锁/SQLite 内再核代次与目标，只登记不授权正文的 submission，释放锁做真实 Hub CAS，成功后用原本机代次条件保存回执（`upload.py:235-295`、`:136-167`）。CAS 409 不先改变规则，未知回执只对原 generation 标 conflict，不能覆盖较新保存。正文派发/控制派发各有当前目标与代次检查。
- 新增/改写测试、工具拆分、Windows 锁/环境处理、安装包恢复控制器、原生执行时限和清理边界均有计划调整说明。默认 CI 已有三系统全套 pytest、独立 wheel 安装和 CLI/MCP 烟测；新增用例由原工作流自动执行，无需为“计划列了该文件”而制造无意义 diff。
- §5–9 所需实际平台、三入口、系统账户、旧正式包和恢复证据在下表分版本核对。旧失败保留，新结果另建目录；未见把旧结果重标为 ba8 的做法。plan 的唯一 G 方案表述偏差已按上述方式纠正。

## 按真实角色回放发现、输入、操作与恢复

### 本机使用者与其 Agent：控制上传，同时检索全部应查资料

| 步骤与所需知识 | 当时可见内容与实际可达下一步 | 判定 |
|---|---|---|
| 从项目主入口理解是否适用 | README:33–50“多台电脑共用档案”先讲 HTTPS Hub、维护者提供凭证文件及配置；紧接 :52–68“选择上传项目与联合检索（005，尚未发布）”介绍四模式、新目标先只查询、默认两端查询和逐条 reference，并明确正式 0.4.0/首次安装器尚无005 | 能识别适用对象与版本，不会被指向重装0.4.0来启用新能力 |
| 取得运行组件和连接前提 | README:54 指向源码开发 :76–87；其指南链接进入 TRIAL_GUIDE:139–145，说明构建两个 wheel、独立 Local/Hub 环境、各平台 Python/CLI 位置、独立 db 以及 configure-hub。HTTPS/凭证由 README:35–48、指南 Hub 配置段给出 | 有实际可操作的预览安装与既有凭证取得路径；无需凭空假设目标已配置 |
| 取得项目选择值 | README:59–64 明确运行本机 projects；指南:148–158 解释本机 ID、Hub ID 不同、四种替代命令、空名单和无效名单。CLI help :111–126 直接指明 ID/版本来源；Web“项目”显示 ID、类型、允许状态及展开的稳定键（HTML:110），配置页展示四模式/项目复选框 | 同名项目可据稳定身份和设备区分，必要值不是只在 SPEC 中存在 |
| 保存并确认真实状态 | Web 主导航“导入进度”有上传摘要及“设置上传范围”（HTML:36–43），跳到“配置”上传卡（:58）；CLI upload status/set 共用 LocalUpload。界面解释保存/Hub确认、在途、旧副本与补齐，指南:158–160 给 state/transfer_state/计数/暂停边界 | 不把本机保存等同 Hub 已生效；停止不隐式恢复来源或全局暂停 |
| 明确全局归属，避免静默扩大允许 | README:64 提及唯一全局项目；指南:162–173 给 ensure-global→仅本机搜索取得会话ID→预览→confirmation提交。Web 项目卡 :50–51 明确会话ID来源、影响列表和确认按钮 | 归属未知不等于全局；扩大范围及过期确认处理可发现、可执行 |
| 联合查询后读准确原文 | README:66/:98–122，指南:175–187 给项目/仅本机、reference读取；Web 检索页 :54 有档案范围与项目选择，结果 :163–164 展示档案/范围/部分失败，:148–153 的按钮只传该结果引用。CLI read 与 MCP reference 共用 read_archive | 顶层combined不被当成每条来源；不将本机数字ID拼上顶层Hub ID |
| 断线、补传或恢复后处理 | 指南:185 说明范围失败只查A、有效快照后的部分覆盖、双失败与零结果；:189–210 明确支持版本、prepare-restore、停服务/一致性备份、保护文件排除、查看差异与双版本来源、过期刷新。Web差异按钮实际保存页面所见双版本（HTML:197–207），错误不显示保存成功 | 局部输入、下一步和不支持的任意手工回滚边界明确；正常断线及恢复有完整路径 |

### Agent/MCP/CLI 调用方：保持引用与范围语义

README:110–122 的 Agent 接入直接链接本仓库检索 Skill，并给 MCP/CLI 后备入口；Skill 的开头提供 MCP 或 first-use 全程处理路线。搜索步骤要求先取得状态、resolve_project 和本机 project_id，然后看逐条来源/位置、沿 reference 读原文、引用来源位置。新增段明确 combined、origin_references、两端候选重排、Hub共同一层范围、显式本机、本机A回退以及 coverage/candidate_failures/capability_limitations。配置段说明上传需用户明确选择且 MCP 不新增写规则工具，用 Web 或 launcher upload；ID/空名单/在途与恢复双版本均有说明。

实际工具入口 `mcp_server.py:36-53` 的描述、签名和返回路径一致，旧整数定位仍可用，`reference` 单独可用且冲突参数拒绝；`first_use.py` 增量放行 upload/project/read-reference，并先探测当前0.4.0不支持时给可识别错误。Skill 明确发布边界，没有将其新增说明冒充正式旧包已经具备功能。该调用方路径可通过。

### Hub 维护者：不要求先收正文即可关联项目，并安全恢复

README“多台电脑共用档案”→指南“安装和管理汇总端”（TRIAL_GUIDE:70–86）可找到 HTTPS、运行账户、uv安装、setup/status与凭证；README:70–74 的“搜索 VibeInsight 和关联项目”明确由维护者配置并直接链接指南:120–136。该局部入口说明“005不要求上传正文”、用 `smm-hub hub project list` 取得 **Hub ID**、再 links/link/unlink，并解释稳定项目改名和单层关系。自行管理进程 :107–118 给同一 state-dir 和启动参数。

恢复指引 :193–210 从当前 `hub status.database` 父目录确认实际状态目录，再 prepare-restore、停止实际服务、恢复清单并保留 guard/lock；Local明确采用 Hub或所见本机规则。Hub CLI dispatch 已将 prepare-restore 的连字符映射到真实方法，恢复标记先于还原。本轮没有发现维护者必须先上传禁传会话、猜本机ID或猜另一份默认目录才能完成任务的缺口。

## 源码关键边界与本轮验证

- `upload.py` 的规则保存和正文 dispatch 共用跨进程保护锁/SQLite写边界；派发前重核真实连接、暂停、规则确认、归属、身份/版本以及会话 catalog 完整性。网络不持长锁。候选遍历按项目轮转，正文/归属接收账本独立于扫描游标。
- Hub `upload.py:108-160/:185-214` 持久 CAS、旧式门禁与整个批次权限检查先于正文写入；拒绝批次回滚。`hub.py` 的 known-message核对只认真实同版本，增加当前允许项目消息归属而非重复正文。最小项目登记没有正文/会话枚举。
- `federation.py:451-556` 统一三入口：合法共同范围映射只用设备+稳定键，按项目失败回退仅A；有效快照后部分失败保留快照，缺全文候选单独排除，不扩大召回。`search_merge.py` 在完整消息去重后用规格BM25，未知同源不误归并，长消息展示在评分后压缩。
- `references.py:56-76/:101-121` 绑定档案、消息、内容版本及所选消息集合；范围读的标题来自实际selected消息。Hub读取也限制projects/origins，旧无范围路径保留。相同整数ID、Hub不可用、篡改/版本变更不会改读别的档案。
- 独立重跑：`.venv/bin/python -B -m pytest -q -p no:cacheprovider --basetemp=/private/tmp/smm-pr30-ba8-review-tests`，测试文件为 reconcile_snapshot/dispatch/remote_race/uncertain、combined_search、archive_references、scoped_read_metadata、upload_project_moves、project_preview_coverage，**54 passed**（5.06s）。只有既有TestClient/httpx弃用warning。仅使用合成临时档案，没有访问日常档案或外部数据库。
- 另实际读取 `<task-path> **220 passed, 1 skipped**。这是所提供全量原始日志，本审查没有把自己的54项写成重新跑过全量。
- 对 final20 SC1/SC2/SC3/SC11 的每份 result，逐一重新计算 **70份bindings** 及各自13/25/22/7份artifacts，均与当前文件一致；真实子进程21个TC均exit0，参数展开为44个pytest执行。四份执行独立意见均已回收，只认领所列TC覆盖，不将其full/gaps字段当作平台已经执行。
- red-remote-race20/green-remote-race20冻结测试相同；原7c红灯12组在完整本机row不变断言失败，最终ba8绿灯12组到达末尾本机row/Hub head/全部正文/无正文派发断言。SC2还含未知回执与较新选择、目标切换、新鲜四模式正控。没有只测“所有提交都拒绝”。
- SC3最终测试实际改3份合成来源首行，`files_changed==3`，由head_hash变化进入offset0重放，再比完整会话→项目映射。G测试核对完整公开列表和持久projects/key集合；assign/map/merge均比较五表预览/过期拒绝无副作用，保留原全局/类型边界职责。

## A1–A12 与 E1–E5 证据独立核对

下列历史任务路径除说明外相对 `.acceptance-local/native-v1/AT-SMM-005/platform-debug/`；公开脱敏版本在 `changes/005-selective-conversation-upload/evidence/` 下 d80/f45/7c/cas-repair 四目录。覆盖导航只作入口，本轮继续读原始JSON/请求/安装清单/进程及部分真实图片/trace；没有只信result.status。

| 条件 | 本轮核对到的实际依据与判定 |
|---|---|
| A1 默认/入口/参数 | d80 mac-run8/linux-client-run8/windows-client-run8新连接needs_selection、最小项目、四模式/非法输入回归；最终SC1双版本输入与SC2 fresh；三平台reconcile21最终安装CLI/Web专项已核。文档发现路径如上。 |
| A2 停止/暂停/竞态 | 主流程stop/replay、真实各Hub旧/无版本请求HTTP403/409且前后正文集合不变；最终SC2旧视图/写窗口/12组远端竞争/在途与目标边界；full-v13相关暂停/崩溃/乱序回归与最终三平台对账专项。 |
| A3 项目/全局/最小登记 | 主流程Web、三平台global-cli11及最终SC3；最小metadata项目仅id/name/kind且无membership；同名设备稳定键分离、改名保持关系；三操作多会话多消息、禁传指纹隔离、允许增归属、正文实体/旧引用保留、丢确认重试都有直接断言。 |
| A4 补齐/幂等/公平 | 对7个主/Hub/登录目录重算离线audit均通过：确认停止→原目录服务重启→允许后A原轮/停传追加/新会话完整读回，allowed_pending=0/inflight=0/complete；旧引用与旧内容版本仍准确。35条独立全集、有界队列及失败项目公平推进由当前共用测试/正式SC4补充。 |
| A5 隔离/保留 | isolation-run9请求与完整结果，以及各真实Hub重放旧接口；甲停A后允许关联D、乙、合成V继续；旧A原文保留，禁传新A留本机。VibeInsight保持现有自动测试，不声称连接真实服务。 |
| A6 范围/三入口 | 七个主目录audit比较A/A-new/B/V精确集合、逐入口自己的引用与全文；三平台入口专项 local-project/local-all/combined-all 的3/7/10会话完整集合及CLI/MCP/Web逐条读回均独立比对一致，显式本机无Hub search。共同一层/当前会话/各N不扩召回由共用测试补足。 |
| A7 排序/隐私 | 主流程原始候选用独立词频/df公式重算得分、比CLI/MCP一致；payload形状与stopped-payloads无禁传正文，长尾全文/旧新内容版本实际读回；SC7与当前回归覆盖副本不增权、不同轮次/会话/版本、空时间与平局。 |
| A8 引用/范围/冲突 | 本轮直接复核六份split-scope（3平台客户端、Linux/Windows真实服务、Mac系统scope15）：所有新引用/扩大区间/重启旧引用只返回X正文、X标题及scope-X项目，旧无范围仍Y+X；三客户端另有浏览器。读取/范围共用负例及独立54项通过。 |
| A9 回退/失败/恢复 | 主流程三入口按A断线仅A/A-new，恢复联合；三平台scope11 offline-all独立比对六来源集合与三入口完整读回，Hub unavailable明确；范围/本机/Hub/全文/双失败和非法输入由共用测试覆盖。服务protocol_only轮未跑offline-all，不从通用scope标签认领。 |
| A10 版本兼容/迁移 | d80 compat-run8/linux-compat-run8/windows-compat-run8真实0.4.0独立环境；新对旧0正文、项目仅本机及能力限制；旧设备未迁移仍可写，采用控制后真实旧进程HTTP409且旧读可用；升级保留all、旧游标不截历史、更换真实Hubneeds_selection。后续未改这部分方案，最终回归补强。 |
| A11 生命周期/恢复 | E1/E2/E3/E4主流程原目录/账户重启、补齐有结果；R1旧本机all/Hubnone，R2/R3/R4保护恢复后都conflict、显式采用后none、再允许补完整A原/追加/新内容。R4离线成功安装桩仅覆盖真实Hub.upgrade/systemd/健康失败/restore顺序，不证明发布下载或未来迁移。最终SC11及SC2更新对账核心，三平台最终入口另证。 |
| A12 发现/交付 | 角色路径、参数值/状态/恢复说明一致且可达；旧来源管理帮助未退化。所有必需行为已有原始证据支持；专门平台意见/整体原生交付登记应另按其实际完成状态记录，本报告不代填该结果。 |

| 环境 | 版本与实际运行/独立复核边界 |
|---|---|
| E1 Mac | d80 mac-run8 + d80 entrances10 + f45 scope11/global-cli11，7c reconcile15，ba8 reconcile21。普通UID501、实际CLI/真实stdio MCP/本系统浏览器、后台停启。已核最终Mac21全部25/24模块和wheel、3张原图、trace六次POST=200/400/200/400/200/200、旧值无set、新鲜CLI/Web成功、cleanup无失败。 |
| E1 Linux | d80 client8/entrances10 + f45 scope11/global-cli11，7c reconcile15，ba8 reconcile21。UID1000，实际Chromium；最终21同样正确双版本请求、旧本机/旧Hub400、新鲜采用200、CLI错误非零、最终none/confirmed，本轮核安装全部字节、3张原图及trace请求；cleanup=[]。 |
| E1 Windows | d80 client8 + f45 entrances14/scope11/global-cli11 + 7c reconcile15，最终ba8 reconcile21。manifest非管理员，冻结包装器Interactive/Limited，outer PID13852/exit0；全部25/24模块与最终wheel一致、环境独立。三张PNG分别为旧本机拒绝、旧Hub拒绝、新鲜采用none；trace六POST状态与Mac/Linux相同且请求精确带2/1、3/3、4/3双版本；实际服务HTML摘要等于安装HTML。旧CLI/缺参exit2且无stdout，新鲜CLI成功；最终local generation5/none、Hub revision6/none。两个stop-on-demand exit0，显式stop后Hub子进程exit1与Windows边界一致，cleanup=[]。旧entrances10/12失败保留，不当作通过。 |
| E2 Mac登录 | f45 mac-login-run11真实专用LaunchAgent及原目录重启，持久限制、本机可查、允许后完整补齐；离线audit99份原始文件事实检查通过，实际登录定义/PID另在login-service-*.json，不拿Hub serve-hub事件冒充。 |
| E3 Linux | d80 linux-hub-service-run8真实systemd用户服务 + f45 hub-scope11；service-events有真实unit/MainPID/用户，重启后拒绝旧批次、补齐及X范围读成立。 |
| E3 Windows | d80 windows-hub-service-run8 + f45 hub-scope11，CIM owner=NT AUTHORITY/LOCAL SERVICE，服务PID2504→11036。控制器管理员身份与服务真实账户不同；不把前者冒充服务账户。 |
| E3 Mac | 7c mac-hub-main15及scope15真实系统LaunchDaemon；UID501/PPID1、main PID57818→58048，同目录。已核main停止/补齐/audit与scope精确读；已有五次实际运行独立审查补充账户/命令/清理。protocol_only无浏览器/offline-all认领。 |
| E4 自管 | d80 mac-run8真实serve-hub，PID54870→55420同状态目录；f45 mac-scope11补X范围/重启引用。主流程及清理通过。 |
| E5 | 真实三平台旧包组合、R1–R4实际过程和R5/R6共用故障/最终对账回归；文档路径在本环境逐链核对。最终三平台对账入口已补齐。 |

## 包与历史证据能否复用

本轮独立打开最终wheel核对：Local `416799968bfc5a22bf2dc1baee6b16491ae3995de0266cf68afa980c980222ee`、Hub `eac8b57564d463ca74fd4ad40e02a0052c062b4cacbace45335bb39d11135800`。全部25/24产品文件与Mac/Linux21 manifest的candidate及实际安装清单相同、环境均分别安装。旧7c wheel独立逐文件比较：Local仅 `smm_local/upload.py` 不同，Hub全部模块（含vendored核心与引用）完全相同；符合final-package-comparison21。

补审Windows21后，其全部安装文件和wheel摘要同样吻合上述最终包。另实际读取 `<task-path> 45002908134 Ubuntu/Mac为220 passed/1 skipped，Windows为221 passed；三系统均成功构建Local及Hub wheel并执行独立安装/CLI/MCP烟测。它验证通用回归与构建，不替代上文真实系统服务账户或浏览器状态变化证据。

7c→ba8新增的是reconcile的成功/拒绝/回执条件分支，普通choose调用仍走原_save默认分配submission与pending路径，候选/正文派发、Hub、排序/范围/读取模块字节未变。旧平台执行不改标；可按相同Hub与未受影响功能的真实证据，加最终源码回归和受影响三平台对账专项形成覆盖。原f45范围标题修复已有三平台/服务专项，原d80其它主流程并未被误称修复后新执行。无需无依据重做所有E1–E5或笛卡尔积组合。

本报告仅修改本文件。没有写产品、测试、规格、原始收据或外部数据，没有连接真实VibeInsight、日常用户档案或服务器数据库。
