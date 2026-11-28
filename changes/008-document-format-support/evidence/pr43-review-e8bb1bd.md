# PR #43 检查点独立审查：e8bb1bd

结论：**本次新增采样修复及其限定红绿证据可采信，未发现新增的实质产品问题；PR 整体仍 needs_revision，SC1/R008 未完成。** 一次完整重扫符合先行确认的 SPEC/PLAN。Windows 实际采样 1 项与 Mac 原 staging 6 项通过，不代表完整 SC10、原 CI 完全根因、安装业务、服务或 E/H/X。额外 Windows 容量回归超时，无 JUnit，不计通过。

## 范围、方法与审查方面清单

冻结 HEAD：`e8bb1bd322507a3c405dd1d9ec470a22731ffa4c`；本轮增量：`a04ac4cd987a29de9970071060df94de0ad2d5d5..e8bb1bd`，包括先行确认提交 `160124e0f0e41c77082ae4ab31779a54f908783d`。全 PR 基线：`d8894d429ebe0915e377513a637b5dfc0fc7ea1a`。这是**新增量审查与既有问题核查**，不是完整重审全部历史 diff 或重新验收整个 PR。既有整体/检查点依据为 `changes/008-document-format-support/evidence/pr43-review-a04ac4c.md`、`pr43-review-7c2348a.md`，已读全文。

首先实际读取工作树 `AGENTS.md` 与 `changes/_templates/pr-review.prompt.md`，随后读取 Intent、SPEC、PLAN、13 份增量、相关产品与测试、原生设计/结果/独立意见和下述私有原件。没有运行 pytest、native 验收、构建、服务、远程、浏览器或 CI；没有访问或写入 GitHub。只用 Git 与标准库进行只读文本、JSON/XML、摘要、ZIP/tar/gzip 静态核对，唯一写入是本文。

| 审查方面 | 实际入口与结果 |
|---|---|
| PLAN 的位置、方案、顺序和验证偏差 | 产品唯一变更为 `src/smm_local/document_supervisor.py`，测试唯一新增为 `tests/test_document_formats_live_temporary.py`；与 PLAN:91、320–324 相符。规格先确认保存，再实施；验证失败/拆分如实记录。 |
| Intent 角色与主入口逐跳 | 实读 README、TRIAL_GUIDE、检索 Skill、验收 README 及相关源码；下文区分局部信息与整体可完成性。仅静态回放，没有本轮实际操作 CLI/Web/MCP。 |
| SPEC 行为、边界与逐 A 条件 | 核 B9/A10 新约定、完整 B/A/C/E/H/X 边界；A1–A12 单列判断，不将专项通过推广为整域交付。 |
| 代码正确性与回归影响 | 核最多一次重扫、路径错误边界、根失效、部分计数丢弃及预算/调用点不变；旧问题模块与 a04 字节相同。 |
| 测试预期、真实探针及独立真值 | 读全部 214 行冻结测试和 driver/controller；Win32 真实句柄错误，48/69/78/37、256MiB/+1 来自独立输入，非两个产品结果互比。 |
| TDD 与证据可复核性 | 有效 red-v2、green-v3 同字节测试；逐 SHA 核原件/绑定、tar、JUnit、回归输入，复读独立意见及旧失败历史。 |
| 构建、平台及交付范围 | 只读核两 wheel 的 CRC/源码成员；额外 Win 原件回收未完成状态属实。没有认领当前 CI 或安装/服务/普通用户。 |
| 公开表述、索引与 PR 正文 | 公共摘要与主要限定事实相符；发现一个非阻断历史标签建议，详见下文。未进行全仓库秘密扫描。 |

## Findings 与旧问题核查

### 本轮新增实质问题

无新的、已有充分依据的产品缺陷或验收通过误报。此次批准的行为变更不再与旧“权限异常立即失败”约定冲突；不能把旧 v1 的无效红灯追认为有效，也不能继续以旧约定否定新 v2。

### D1 · 非阻断文档建议：同一索引对象仍残留未标历史的旧诊断文字

冻结 `changes/008-document-format-support/evidence/pending-verification.json:411–426` 的 `windows_pdf_temporary_directory_error` 已用 `status`、`clarification`、`delivery_evidence` 准确说明恢复已实施、专项通过、当前 CI 待核；但 `limitation` 仍写 `no confirmed cause or product fix`，`investigation` 仍写 `needs_revision/design` 和 `Not accepted product red`，没有在这两个字段内明确其为旧 v1 调查状态。

影响维护者从 README→证据目录→待验索引复核时的状态理解；读完整对象和新摘要仍能区分先后，因此不构成产品操作阻断，也不意味着原意见应被改写。建议仅把这两段显式标为历史，并保留“原 CI 完全因果未证明”的当前限制。可验证条件是索引一眼可区分旧 v1 设计冲突与新定义 v3 下 red-v2/green-v3 的限定结论，不删原失败/意见。本文只评价 e8 冻结字节；之后的文档修订不倒算为本提交已修。

### 既有问题仍在，非本轮新发现

| 原问题 | 本轮依据与判断 |
|---|---|
| F1 / P1：失效已 commit、未发布 canonical 候选缺安全 GC | `document_snapshots.py:24,50–79` 仍按实际 raw/results 与发布 ledger 计费，未见本轮新增最后用途/活跃分配感知 GC。相关模块与 a04 字节相同；raw-only 未 commit TTL 修复不能关闭此项。 |
| F2 / P1：路径 refresh 发布拒绝后缺终态收尾 | `documents.py:428–433,459,482` 仍先置 refreshing，扫描外的发布异常可绕过来源终态。未应用保留候选补丁；既有有效 Local/Hub 红灯结论保留，没有本轮重跑。 |
| F4 / P2：路径 Web 详情缺候选/重试值 | `src/smm_local/static/index.html:141` 的“文件状态”仍只输出 path/status/version/error；API/CLI files 为已有可用详细路径。局部信息缺口保留，不能夸大为所有入口均无法操作。 |
| F5 / P2：活跃服务 CLI 内容任务未交服务 worker | `hub_admin.py:435–445` 仍直接分派文档命令；PLAN:75 的同 state 服务交接未由本轮完成。前景/SSH 源码采样不是实际服务处理身份。 |
| N2 / P1：同父目录不同 SQLite 档案队列丢唤醒静态风险 | `Snapshots.root` 仍以数据库父目录定根，`managed_document_uploads.py:183–206` 的锁共用但只查本库待办；维持“有静态依据、尚未实测复现”的既有结论。单档案修复的限定缓解与旧 native needs_revision/design 均保留。 |
| 已有限定关闭/缓解 | 合并表头、纯 Hub 原件路由、处理版本隔离、managed/缓存收尾及单档案队列改善不被重新列作同流程仍失败；本轮没有重新授予全部历史通过。 |

维护者保留的在途来源取消、C1 五项、Windows 字符串 argv 共享审计、跨档案队列和路径刷新 Hub 搜索封套均未专跑或修订，不据此豁免 SPEC。四份保留 Python 草稿仍未进入 Git；新的 live-temporary 测试已通过限定审查后进入本提交。

## SPEC/PLAN、实现与测试核对

Intent 保持创建端处理、真实可检索/核原件、清楚覆盖与合理预算的目标。当前 SPEC SHA256 为 `99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986`，与 160124e 字节相同；Intent 也相同。PLAN 的产品/验证结果追加在 e8，属于本次约定的实施记录，不是把新行为先做再补确认。

当前定义 `.acceptance/native-v1/AT-SMM-008/definitions/000003.json` 实算 SHA256 为 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`，冻结 SPEC 和 SC10 新判据一致。000002→000003 的场景 scope 未变；要求原文仅把可能误读正常 0 的“返回0”措辞改为“以0代替采样失败”。旧定义和 v1 冲突意见均保留，不重新解释原判定。四个新增设计/匹配/复审公开投影的私有 result SHA 均实核相符。

`temporary_bytes` 的新外层 `range(2)` 至多调用两次完整采样：每轮先在 try 外 `root.stat()`；只有第一轮、带 filename 的 PermissionError 才进入路径判别。`abspath` 加平台 Path 的相对关系排除根本身与范围外路径；未知路径也不重试。第二轮异常直接传播。`_temporary_bytes_once` 每次独立 `used=0`，仍将 os.walk 的 PermissionError 经 onerror 抛出，仅沿用原来对正常清理 FileNotFoundError 的容忍，逐文件单次 stat，末尾再次核根。根缺失、不可读和扫描末端根失效不返回伪计数。未见跳过拒绝成员、复用首轮部分计数或第二次失败后继续。

本轮另读本机 Python 3.14.2 标准库 os.walk 源码，核 scandir 错误向 onerror 传播、根枚举后遍历已列子路径的机制；这不是 Windows 3.14.10 已安装标准库的逐文件摘要证明。Windows 原 stdout/JUnit 的 `<frozen os>` 错误链与真实 Win32 scandir 探针提供实际平台依据。新逻辑不依赖把所有 PermissionError 都认作删除待定；持久错误仍失败。

`RSS_LIMIT/TEMP_LIMIT/TIME_LIMIT`、`run` 的唯一调用点、单调起始时间、256MiB 比较、300 秒检查及整个内容任务路径均未改；没有新增 sleep、任务重跑或重置时钟。helper 抽取后的实际遍历体保留旧语义。该静态判断不冒称本轮实测完整任务树终止、五秒槽位恢复或所有根中途失效交错。

测试用 CreateFileW / SetFileInformationByHandle(FileDispositionInfo) 及直接 scandir 产生真实条件；walk 包装只安排文件系统交错并转交真实 walk/onerror，不伪造异常或返回值。先独立核正常 69=37+13+19，两个目录都验证删除待定 WinError5；首次清单外再写 11 字节，错误传播时只关闭测试自有句柄。完整恢复必须得到 48=37+11，恰两次 walk，目录实际消失，late/kept 原字节不变；故沿用37、漏11、重复计原37、继续累计旧13/19均会失败。持续拒绝、根不可读/缺失、正常空0、原256MiB/+1及清理分别有断言。测试没有承诺整个 SC10 或所有任务入口。

## 实际原件复核与局限

1. **有效红灯与新绿灯链**：实算 red-v2 result SHA `1b92ef90e479ded98bdc7abe9fe9d8eba88fed7430247e00c9225d31d506ca03`；26 artifacts / 67,080 字节全匹配。其旧 supervisor SHA `d9255fb51e1efce7b070d8a493b961199db87c2c91a92a414edadd0c6481bbf7` 与 160124e Git 原件相同，当前已修源码与旧绑定的预期差异不是漂移。green-v3 result SHA `7acc792cac28652021f8498773ed87f656bb85fb9210eba04b9d4c594f4d686d`，274 artifacts / 1,413,750 字节及 280 bindings 逐份核对无不符。有效红灯全部测试绑定与绿灯相同，主测试 SHA `24595e406d304d030d271401be30673774f48cfb142a37602f8394a3927a7742`。
2. **Windows 主项原件**：red/green 各自 source.tar 六成员均与对应 manifest 字节相符，回收五项 checksums 全核一致。driver/controller 先核上传归档/远端逐源/回收全集，最终取实际 pytest exit，不能把 execute 传输 exit0 当业务通过。红灯原 stdout/JUnit 确为 1 failed，首次 pdf-one WinError5 经真实 onerror 由旧产品直接抛出，最终48断言未到达。新绿灯为 1 passed、0 skip/failure/error，stdout 1.04 秒、JUnit suite 0.975 秒；实际观测含 persistent Walk=2、root Walk=1、48、268435456/268435457、全部句柄关闭及保留原件 SHA。Windows11/Python3.14.10 是 SSH 管理员源码组件记录，不是标准 token、安装包或 SCM 证明。
3. **独立意见**：red-v2-format SHA `bc19250c7159aa208c3ad0dde93a51689f7505a8bfb21fcfee577079b3323c57`，目标精确对应 red-v2，结论 expected_failure；green-v3 review SHA `328bdcf3f3322ee91de417414811bf1edd338b11a25e18f718481bd87d1ac478`，目标对应 green-v3，结论 passed，covers=[]。已实读意见及其两项 artifacts，定义/目标/摘要一致；不能因设计/匹配列了七个 SC10 TC 就认为七项全执行。
4. **Mac 正式回归**：实读 regression.process/输出/JUnit，实际仅 `tests/test_document_formats_staging.py` 六项，exit0，6 passed、0 skip/failure/error，134.903 秒；28 份 gzip 输入依原 manifest 解压核原长/SHA。原 `assert_missing_ocr_failure` 仍要求 OCR 含义并拒暂存额度错误，测试与 a04 Git 字节相同，没有为 WinError5 放宽。此处复核完整性和所到达断言，没有本轮重新手工建立全部历史格式业务逐格真值。
5. **失败历史**：v1 blocked 的29 artifacts、v2 blocked 的285 artifacts均实核无摘要不符。v1 regression.stderr 确为缺 ACCEPTANCE_EVIDENCE_DIR，未启动项目回归；v2 Mac6 已过但总调用超时、regression exit=null。v3 调整调用拆分没有改主测试或产品。v1旧 red 的正式 needs_revision 仍存在，不能追认。旧两次 blocked 也不能反写 passed。
6. **额外 Windows 大容量回归**：`regression-recovery-v2/evidence.zip` 实际45,315字节，SHA `317ea07a663d4b907da048eb36c3af6e3a7f30af2f1c93ed9ef5fdc176f886a8`，28成员 CRC正常；27项清单逐长/SHA及解开字节一致。result 确为 exit15、timed_out=true、240.189秒、cleanup_errors=[]，stdout空，无JUnit。只证明失败原件已追回，不能认Windows六项通过、完整H5清理、原CI根因，或推断产品300秒预算本身被触发。
7. **保存的构建**：只读两wheel，CRC正常，Local46/Hub47声明源码成员逐字匹配当前源，Hub变换shim亦相符。Local195,987字节/SHA `eb235697645323eb732f6ef8bd9033257808b2b65915752ad7f83e3999e75ff6`；Hub180,087字节/SHA `0ce4dc275f8365e427b887ad5040c2e2f0475fb0df0b3095a2b42608ff252a6b`。构建原 result exit0；只认构建与源码入包，没有安装后业务结论。

当前 e8 普通 CI 结果本轮没有取得/核验，也没有启动联网或等待；7c 的六份旧 CI 结论引用前检查点，不能覆盖新 sampler。未重开保留测试、未进行完整 C1/E/H/X/最低Python三平台或真实浏览器回放、未重核全部历史清理/逐字逐格结果。

## Intent 角色与主入口静态回放

| 角色与目标 | 主入口、当时可见内容、下一跳及值来源 | 局部充分性与整体结果 |
|---|---|---|
| Local 用户纳入格式并检索核原件 | README:33–48 介绍文档主导航/CLI及未发布边界，61–67直达008指南；指南:155–180给同构建wheel、独立档案、材料清单取程序/data绝对路径、status取revision/check；184–208给项目ID、add返回source-id、搜索reference/table_id及原件新路径 | 能发现并开始；新恢复没有新增用户输入。整体仍受F2/F4/N2及平台缺口限制，不能判完整完成。 |
| Web 用户上传/更新并判断结果 | README:54–65说明本机文档/Hub认证项目资料；指南:184–186、212–218给选择/拖入、处理与发布状态、reader表格和下载、失败候选说明 | 已有必要说明；本轮不是实际拖入/浏览器上传验收。路径“文件状态”局部缺详情仍F4，不能以library说明替代该路径已实现。 |
| Hub维护者准备处理依赖与服务 | README:55,63–67→指南:168,172,180，使用实际state-dir、材料清单绝对路径并区分check身份与服务身份；Hub CLI/网页为真实管理入口 | 程序/data/revision意义和来源可达；F5服务交接未完成，当前Windows管理员组件不能确认服务处理结果。 |
| Agent/同步资料使用者按出处读取 | README:9–23的Skill接入与33–37的只读文档工具→`skills/smm-search/SKILL.md:60–72`，先验实际schema、选真实项目、用返回exact reference读text/table/original-info，再交CLI/认证API下载 | 只读/管理边界和参数来源充分；本轮无新增MCP读写行为。完整scope/同步/平台入口未由采样专项证明。 |
| 维护者复跑与判交付 | README:67规格/计划/证据→`scripts/acceptance/README.md:3–32`给普通pytest/构建、OCR材料、组件/安装/E/H/X区别及回收方式→待验索引 | 复跑/证据入口清晰可达；D1旧字段增加理解成本，有完整当前路径可用。不能以目录、job success或一份passed代替整体验收。 |

以上逐跳有本轮实际读取的内容依据，但没有实际启动界面或命令来完成导航。说明已更新、功能专项通过、用户能发现开始与全部用户路径可完成，是不同结论。

## A1–A12 检查点判断

| 条件 | 本轮可支持的结论及未关闭范围 |
|---|---|
| A1 入口/创建端 | 没有新增完整入口验收；静态可发现，F2/F4/F5/N2及SC1保留项仍在。 |
| A2 DOCX | Mac staging控制含既有DOCX，不是全部部件/表格/平台验收；前限定结论保留。 |
| A3 XLSX | 没有新XLSX完整业务证明，不扩展既有结论。 |
| A4 原生/混合PDF | 真实大PDF容量回归有证，不代表全部解析布局/质量通过。 |
| A5 OCR | 原缺OCR断言未放宽；真实三OS/服务质量与故障恢复仍缺，Win临时错误不被解释为OCR通过。 |
| A6 直接索引 | 本轮未改/重验同步接收；无依赖接收、零处理及X六方向仍不由本项完成。 |
| A7 成套/并发 | 单次采样恢复不证明全成套、队列或控制并发；N2、路径收尾及保留C1继续未关闭。 |
| A8 生命周期 | 没有新增GC/授权取消/路径终态/服务重启完整闭环；旧F1/F2等保留。 |
| A9 查询/原件 | 没有新路由/读取变化；已有远端原件/版本隔离/合并表头限定结论保留，全入口仍未齐。 |
| A10 有界/隔离 | **只关闭新B9/A10的Windows采样恢复子域**，Mac原容量六回归成立；完整任务树、所有预算、根中途变化、五秒回收/E/H仍不能判通过。 |
| A11 兼容/发现 | 静态README→指南/Skill/验收路径可达，双wheel源码入包；当前CI、最低三平台安装业务/全部兼容与发现性未齐。 |
| A12 平台/证据 | 本轮限定原件可打开并有独立意见，额外Win未完成如实保存；E三格/H三格/X六方向、完整C1与最终交付仍未完成。 |

## PR 正文与最终判定

实际读取本地正文原件 `.acceptance-local/008/windows-temp-observation-20261126/pr-body-e8bb1bd.md`，SHA `f1a57eba5216c49c788c57cc0a3547765969febdede21f1b6b82c332ca30566a`。它准确限定Win1/Mac6、274/280、构建范围、两blocked与额外Win超时、不确定原CI因果、旧CI不覆盖e8，并保留草稿/needs_revision/R008未完成及五类维护者保留项。没有把未就绪四Python草稿当正式测试。此正文内容与实核结果一致；本轮未查线上正文是否发布及GitHub draft实际标志。

**本增量可保留采样修复的限定passed事实；整体 PR #43 继续 needs_revision，R008 不满足完成条件。** D1可用轻量文档标历史修正，不能靠索引润色关闭仍缺的产品/平台验收。本轮没有提交、发布或修改其他文件。
