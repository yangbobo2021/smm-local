# PR #21 最终独立审查

审查对象：[PR #21](https://github.com/yangbobo2021/smm-local/pull/21)，HEAD `ccce1f1dc7569d32a23f26396a03b6de4d371341`，base `af65cb4e3ac978a7324370656822aae2eec475de`（`origin/main`）。本意见由新的独立上下文形成；只读源码、定义和证据，仅写本轮意见。没有操作服务、修改数据库或重写原始记录。

结论：**未发现需要返修的 actionable finding。R8、R9 的需求交付判定均为 passed，可交维护者审查；本意见不执行合并。** 判断覆盖当前完整产品 diff、已确认 Intent/SPEC/PLAN、用户发现及操作路径、当前正式验收和证据边界。不能把该结论扩大为所有操作系统版本、生产性能或重新执行真实 staging。

## 依据、范围和版本

按 `AGENTS.md` 及 `changes/_templates/pr-review.prompt.md` 回放。已读取 `changes/003-search-vibeinsight-conversations/{intent,spec,plan}.md` 和原生交付 Reviewer 规程。验收 ID 为 `AT-SMM-VIBEINSIGHT-003`；定义 `000003.json` 实算 SHA-256 为 `1be6849cdb9134e38205f236f0c333e4675d0949fea9db3c91dd92df5c056db9`。当前交付范围为完整新平台验收 R8（SPEC99–191，SC8–11）与自行管理 R9（PLAN43–49，SC8）。历史 R1–R7/SC1–SC7 留作历史，没有把旧“七项通过”直接换算成新平台通过。

实际审查产品位置包括 Hub 的 `cli.py`、`hub_admin.py`、`vibeinsight_settings.py`、`vibeinsight.py`、`projects.py`、`hub.py`、`_archive.py`，以及 Local 的 `core.py`、`federation.py`、`mcp_server.py`；同时检查相应用例、验收控制器、CI、README、指南、Skill 与新旧证据索引。完整比较以 `git diff origin/main...HEAD` 为准。`AGENTS.md`/`CLAUDE.md` 没有本 PR 改动。

本轮基于原始正式附件独立复算，而非只看控制器的 `status: passed` 或主 Agent 的摘要：四份正式收据的 269/70/53/184 个 artifacts（合计 576）逐文件 SHA-256 全相符，全部 bindings 与当前文件相符；公开 manifest 的 407 个文件 public SHA-256 全相符。三个平台的安装清单分别与实际 Hub wheel 全部 21 个 Python 模块、Local wheel 全部 19 个模块一致；原产品文件与当前源码摘要一致。旧客户端 core/federation 的摘要另用 `git show d2dee18…` 实算匹配。旧 revision、dirty 状态和失败轮次均没有改写成新的成功。

## PLAN 对照与实施偏差

计划中的实际产品缺口已补：`src/smm_hub/cli.py:44` 起解析 `--state-dir`，默认使用该目录的 `smm-hub.sqlite3`，冲突在读取 Token 和创建 Archive 前拒绝；允许指向同一实际数据库。该目录的 `VibeInsightSettings.lifespan` 被传入 `create_hub`，无新参数时保留旧 db/Token/TLS/无来源入口。没有新增来源启停开关或更改确认的同步范围。

H/G/C/P 控制器拆分、Windows 实际依赖 ACL 与 Limited 普通进程、默认 UTF-8、macOS runner 替换、Windows 路径夹具修复、准备审查后的断言补强和两轮之间的任务夹具复位均在 PLAN 第10节说明，未发现未说明且会改变判定的实现方案偏差。三个连接身份字段用默认参数化回归，实际 SQL 端到端选择换库；三个仓库字段用参数化回归，实际服务选择 path 变化。这是明确的分层验证，没有冒称所有字段均做了真实 SQL。

Linux H9 将另一 UID 的实际 open 改为真实服务读凭据加完整 owner/mode/POSIX ACL 审计，是实质验证方法变化；计划与公开材料明确披露，需求级结论在下文独立评估，不能隐去这项区别。

默认 CI 与受控 SQL 分离，日常 pytest 不依赖 PostgreSQL；平台服务由实际机器完成，未以托管 CI 身份代替 systemd/launchd/LocalService。S7 当前索引和 PR 正文仍说明“最终审查进行中”，这是发布本意见前的状态，交接时应把本意见及需求判定追加到 PR/索引，不应改写历史执行记录。

## 用户发现、说明和操作路径回放

Intent 中的实际用户分为日常检索使用者、负责连接和关联的 Hub 维护者，以及调用 CLI/MCP 的 Agent；项目维护者还需要复核和重跑验收。以下从实际主入口开始，逐步核对当时可见的信息。

| 角色与步骤 | 当时需要知道什么 | 可见内容、下一步及结果依据 |
|---|---|---|
| 日常使用者发现能力 | 能否在原入口检索其他电脑及 VibeInsight 项目；谁负责配置 | README:52–56 明确介绍自动归档、直接关联、维护者与日常使用者的分工，原位链接到指南的来源配置与关联管理；不是只在详细命令中暗藏能力。 |
| 初次或旧版使用者取得本机入口 | 安装/升级什么、如何触发搜索 | README 快速开始列 Skill 安装位置、首次执行说明和实际自然语言例子；TRIAL_GUIDE:9 给现有安装环境的取得位置和各系统 Python 路径，:34 起说明实际提问。未要求用户猜测源码内部接口。 |
| 使用者搜索并确认原文 | 当前项目和全局有何区别、返回的是哪份档案、怎样核对正文 | 指南:38 明确在线关联由 Hub 管理，本机 Web 只管理/检索本机；Skill:39 先 resolve_project 再 project search，缺线索可扩大 all；Skill:42/46 保留 hub_id/hub_message_id 并读原文、报告 effective_projects/fallback_reason。指南提问与故障段落均没有把 Hub 引用引到本机 Web。三平台 C 的 CLI/真实 stdio MCP 分别验证这些路径。 |
| Hub 维护者部署运行环境 | 地址/证书/Token 从哪来，服务账户有什么要求 | README 多机章节给 HTTPS 前提、uv 安装、setup/status、Token 交付及“安装与使用指南”链接；指南部署章节给各系统服务方式、Windows LocalService 的 Python 环境要求、启停/升级及旧状态接管。 |
| 维护者取得来源条件并配置 | host/port/database/user/password 含义、同步范围与表权限、psql 路径 | 从 README 的明确锚点到 TRIAL_GUIDE:88；:90–92 要求向数据库维护者取得连接信息和只读账户、确认全部可读项目获准、列完整 fact_events 字段并确认部署结构和读取权限。示例给端口、库名、用户；密码由提示输入，缺省 psql 不可用可指定绝对路径。 |
| 维护者确认同步及处理故障 | 什么时候生效、怎么判断终端配置不等于服务成功 | 指南说明默认300秒/有效interval、失败不覆盖、同目录配置、已保存凭据和持久进度、24h窗口及不支持原地改写。:105 要求在实际服务检查最近成功时间并检索/读原文，同时解释 PATH/权限差异和自动重试。H 三平台有实际对应结果，既非只配置成功，也非只看文件存在。 |
| 自行管理进程用户 | 是否必须注册服务、目录/数据库/Token/TLS 怎样对应 | 顺着来源章节可读到紧随其后的 TRIAL_GUIDE:107；给完整 configure 与 serve-hub --state-dir 命令、独立目录、至少32字符ASCII Token、地址/证书/私钥前提、Windows 引号提示、同目录状态查询及冲突说明。无需借助计划文件才能找到新参数。P 从公开入口真实运行并停止/重启，旧无来源入口与冲突另有证据。 |
| 维护者建立并调整项目关联 | 项目ID从哪来、何时列表才有项目、关系作用在哪 | README 直接跳到指南:120；先让设备同步，再用 project list 取得 Hub ID，示例明确把1/2换成返回ID，给 links/link/unlink 和双向直接关系说明。自定义目录已在前文说明，:132 起给仓库身份变化后重新列项目、关联新ID、检索确认的完整后续步骤。G 与 C 证明有效集合及实际内容都符合。 |
| 调用方 Agent | 可用参数、引用格式、断线及本机范围 | README Agent 接入链接到 Skill；Skill 工具/launcher 参数与实际 C5 工具 schema、CLI help 一致。C2 每入口用自己的查询引用读取；C3/C4 分别覆盖断线 all 和显式 local 项目关系，旧无范围请求仍全局。 |
| 项目维护者复核/重跑 | 从维护入口如何找到新判据、原始响应和执行方式 | README“规约与验收”链接 AGENTS，AGENTS 的 changes 阶段流程进入本次 PLAN，PLAN 第7–10节及开头链接进入新证据；PR 正文也直达新平台索引/覆盖表/manifest。索引的“复审及复算”直达 scripts/acceptance/README，说明工具、目标JSON字段、隔离来源、权限、前置状态、完整P/G入口、引用复算和清理。无需寻找私有控制器才能重跑公开合同。 |

局部信息和整体路径均足以完成本次任务。没有确认的入口缺失、局部必填值解释缺失或相互冲突指引。首次安装/公开包版本实际发布不属于本次授权的发布任务；本轮用独立安装的候选 wheel 验证产品路径，没有宣称已发布新包。

## SPEC 逐节与实际证据

原始入口为 `.acceptance-local/native-v1/AT-SMM-VIBEINSIGHT-003/execute/`，公开脱敏等价入口为 `changes/003-search-vibeinsight-conversations/evidence/platforms-2026-11-17/`。四组正式 TC 各有单独独立执行意见；本审查另对需求完整范围判定，不只累计 TC 数量。

| 新 SPEC 节 | 实测及独立核对 | 判定 |
|---|---|---|
| 1 环境覆盖 | H 实际 systemd UID1000、系统 launchd UID501、LocalService；各 H1-service-psql-process 的真实 psql 父进程分别与服务PID74216/14215/2860相符。P 是Mac公开serve-hub进程；C是三个平台普通本机CLI和真实stdio MCP。 | 通过，运行身份有原始进程/管理器依据。没有使用一个系统结果代替另一系统。 |
| 2 配置、服务身份、恢复 | 三个平台 H1–H9 均完整；实际默认300秒与自定义周期、非法值/错误配置保持原配置凭据和游标、3→5轮/新会话/重复轮次、无新增重启、换凭据、未提交ABORT及三类依赖/连接故障后新内容。每个恢复动作有对应实际状态、原文和引用。 | 通过；Linux保护的方法区别单列如下。 |
| 3 历史与增量 | H1双项目历史、G1行权限边界/后来可见早期历史、G2同时间四事件及重读、G3两个不同K的边界与窗口内、长停服/更早新项目、G4目标隔离与同目标凭据续跑、G5保留原地改写前旧文。纯读取复算七份G3原文与独立输入清单全部一致。固定上界/跨批/流中断另有当前默认回归和真实SQL探针。 | 通过；窗口外仅观察，不擅增“必须排除”或“必须补齐”的判据。 |
| 4 项目归属/关系/身份 | G6双向唯一一层集合、每目标必有内容、解除后范围/全局/原文；C6三平台旧历史无新增补归属和真改显示名；G7新仓库重新关联，host/port/path参数化回归；当前旧Hub升级探针保留旧Hub/消息引用。 | 通过，未仅用元数据集合或两响应相等代替命中和独立正文。 |
| 5 三平台CLI/MCP | 各C1初始/恢复/改名，C2全局两来源/各自精确引用/旧引用，C3回退三本机项目及原因，C4显式本机两项目，C5 schema/help/stdio退出0，C6归属与显示名；实际旧d2dee18进程无范围全局上传/搜索/读取。 | 通过；每个平台的两个入口分别有执行材料。 |

H 旧引用原控制器追加后采集不足，不能单靠“正文相等”通过。本审查对三个正式 `attachments/report` 只读调用证据复算：H1追加前6条完整对象及ID恰等于H6十条的前缀；以16条锚定引用逐条核对 `retained-originals-7` 至 `-12` 的六阶段真实单条HTTP响应，均相同。由此支持旧引用保持，额外 reference-audits 为可重跑证明，不修改原始H记录。P则在任何追加前直接捕获8条引用，追加及legacy恢复后实读；六个真实子进程的主动终止exit为-15，外层exit0没有冒充自然退出0。

C 原始补归属前后本设备全部三会话逐条比较 hub_message_id/position/role/text/timestamp 与数量，均不变，项目从空变有效；Mac/Linux/Windows各初始、恢复、改名的CLI/MCP集合分别严格为 `{4,7,1}`、`{7,4,2}`、`{9,1,2}`，每个适用目标由断言独立验证会话和合成正文。没有只验证首个目标、首个平台或共用CLI引用来冒充MCP读取。

未逐输入穷举的共用行为有源码支撑：`VibeInsightSync.run/_sync_stream/_commit` 固定upper、按项目持久K回看、未知项目从历史起点、归档和游标同SQLite事务；来源键由host/port/database构造而不含凭据，仓库键由host/port/path构造。参数变化进入同一无OS分支的归档路径，具体OS身份差异另由各H实测。`HubProjects` 按kind/owner/source_key保持身份、只改显示名，`effective`沿现有直接一层关系；`core.search`在项目FTS和消息层限范围；`federation._push_projects`在无新增消息时也发送元数据，`search_archive`发送稳定项目键，Hub不可用回本机all，显式local沿本机关联。上述分支都有相应G/C实测，源码推论只补充输入范围，不替代必要的平台实测。

## 权限与证据的明确限制

Linux 没有执行另UID的open。原始 H9 数字POSIX ACL、owner和模式表明目录0700、秘密文件0600、owner1000、无named/default ACL、group/other均无权限；实际该UID服务已用秘密同步成功。依据Linux DAC，其他非特权UID不可读。此为权限审计推论，足以支持SPEC“限制非授权账户访问”；不包括可绕过DAC的特权管理员，也不是另一身份实读拒绝。Mac/Windows分别有真正另一普通身份的 attempted/denied 结果。公开索引、计划和PR均披露该限制，无需扩大或弱化判据。

Windows 部分psql/ACL本地化文字有替换字符；错误仍保留可识别的英文FATAL/role拒登录或中文“无法启动PostgreSQL客户端psql”，权限主体/规则和实际拒读结果明确，SPEC未指定固定语言或逐字文案，故不构成失败。改善本地化stderr编码可作为后续可选完善，以完整可读诊断且保持既有失败/恢复结果为验证条件；不作为本次返修项。

新数据全部为隔离合成PostgreSQL，查询显式BEGIN READ ONLY，服务父子进程与按后端PID的SQL导出共同支持真实psql路径；旧staging仅支持其原日期/版本的同步，不支持本轮平台结论。长停服使用固定事件时间构造，不宣称真实等待多日。两轮间SQLite/Q快照复位只构造独立验收前置状态，没有穿插被测恢复流程或充当产品能力。默认UTF-8，不宣称旧式ANSI控制台兼容；不承诺窗口外迟到和无新增事件的原地改写。上述限制均没有被隐藏成“平台全部任意情况实测”。

## 回归、CI及最终交接

已核对公开当前本机全量日志为 **83 passed, 1 skipped**（Windows专用项在Mac跳过，实际Windows CI执行），并检查真实SQL和旧Hub升级探针及独立包安装证据。此次只读审查没有重新运行会写产品档案/证据的测试。

公开 `environment/ci-results.json` 绑定 `ff816bd…`，三系统回归、构建、独立安装/CLI-MCP入口成功。另在本次审查通过 `gh pr view` 只读实时核对 PR HEAD/base 和checks：当前 `ccce1f1…` 的 push/PR 两套 Ubuntu24.04、macOS15、Windows2022 共六个check均 SUCCESS，最后Windows完成时间2026-11-17T12:06:07Z。该实时观察与仓库内ff816bd收据是不同版本证据，不能静默替换。CI只证明其层次，不代替上述系统服务矩阵。

需求级独立结果已分别写入 `review-inbox/delivery-r8-platform-v1.json` 与 `delivery-r9-standalone-v1.json`，均为passed。审查未确认产品失败、明确违反SPEC或阻断用户路径的缺口；没有需要返修的未说明PLAN偏差。交接时保留本报告的提交/base与上述边界，把当前需求结果和本意见放入PR供维护者决定；后续仅发布这些意见/索引不等于重新执行产品验收。
