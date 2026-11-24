# PR #39 独立审查 v3

结论：**需要修改；继续保持 Draft，当前不能交付通过或合并。** 本轮确认一个新的产品缺口 F8：没有配置 Hub 时，显式 Hub 项目根查询丢失“远端范围无法确定”的覆盖与原因，返回正常空结果形态。F1–F7 的原问题在当前实现中已补齐。另有六个必要平台项仍为证据不足，必须与 F8 分开处理：三系统 E1 的协议/重启入口缺证、两项实际服务 E2 的网页资料重启持久缺证，以及缺少获准资源的真实跨 OS 不同机器 E2。

## 审查边界和方法

Reviewer：`/root/pr39_review_v3`，独立新上下文。首先实际读取 `AGENTS.md`、`changes/_templates/pr-review.prompt.md`，再读 007 Intent、SPEC、PLAN、原阶段授权及项目文档库补充原话。按 Prompt 先核计划，再从角色的真实主入口逐步回放发现、说明、前置、操作和确认，最后区分产品行为、可发现性与验收证据。

实际 Git HEAD 和 `gh pr view 39` 的 head 均为 **`425f1409c98da66bb40c7574f390dcc30a0cc283`**；base 为 **`83b50fcbbad1f29484aa54104ca0f9e75d0498e3`**。审查范围是该 base 到该 head 的完整 PR diff，包括产品、测试、安装打包、说明、工作流、验收工具与版本化证据，不只是 v2 后的增量。PR 实际为 OPEN / Draft。`git diff 245c236ddc41057cd78694902283574d1175e309..HEAD -- src tests scripts/build_packages.py packaging/hub/pyproject.toml` 无差异，证明后续证据/工具提交未改变这组被验产品和测试字节；不能据此把后续工具变动当成产品换版，也不能预先认可未来修复。

只新增本报告。产品、测试、现有报告及原件均未改动；未发 GitHub 评论、发布或合并，未访问 ESXi、日常档案、日常 Hub 或真实 VibeInsight。新反例仅在自动清理的 `TemporaryDirectory(prefix='pr39-v3-')` 内创建合成档案，用当前 `.venv/bin/python` 调用真实 CLI、真实 Local app 的 TestClient 和 MCP 工具；未启动持久服务。其观察原样摘入下文，未另外写产品或验收文件。

## 新的已确认产品发现

### F8 [P2] 未配置 Hub 时，显式 Hub 根查询被标成“本次未请求 Hub”的正常空结果

性质：**明确违反 SPEC B6 的范围不可得须“明确未覆盖”和零命中/不可用分开显示的要求**，涉及 A6；不是新增离线缓存或权限需求。影响 CLI、API 和 MCP 调用方识别查询是否实际覆盖所请求的 Hub 项目。

`src/smm_local/document_search.py:212–214` 已识别这个分支，设置 `reason="未连接Hub，无法确定Hub根项目范围"` 和 `hub_coverage="unavailable"`。但第224–240行的 `if local or not config` 随后覆盖为 `coverage.hub="not_requested"`、`fallback_reason=None`、`coverage.local="complete"`。先前第121–122行把本机项目集设为空，确实没有按同号本机项目猜范围；错误在结果解释，而非返回了越界正文。

本轮实际反例：全新、未配置 Hub 的隔离档案先创建本机项目 #1，然后通过公共 CLI 分别传 `--scope project --hub-project-id 1` 与 `12345`。两次都退出0。对 `/api/documents/search` 的相同请求返回200，真实 MCP `search_documents` 返回相同业务 JSON。关键原输出为：

```json
{"results": [], "scope": "project", "effective_project_ids": [],
 "archive_scope": "local", "coverage": {"indexed_files": 0, "sources": [],
 "local": "complete", "hub": "not_requested"}, "requested_scope": "project",
 "effective_projects": [], "fallback_reason": null, "candidate_failures": []}
```

实际 CLI 入口是：

```text
.venv/bin/python -B -m smm_local.cli --db <本轮临时档案> documents search independentneedle --scope project --hub-project-id 1
```

调用方明确请求了远端根，却没有收到无法解析该根的原因；不能依该响应区分“当前档案没有 Hub 连接”与正常无命中，也不能把 `local=complete` 理解成该 Hub 根已经获得本机覆盖。对话查询的 `src/smm_local/federation.py:474–475` 在同类无连接分支会保留 unavailable 和原因，可作为当前产品已有的一致路径参考。

已有补救路径：调用方先执行 `projects --hub` 或 `list_projects(include_hub=true)`，会得到未配置/不可用说明；README/指南也要求先配置连接并从列表取得真实 Hub ID。因此影响限定为显式远端选择器的失败响应，不声称首次正常网页用户无法发现配置，也不声称数据泄漏。正常网页项目列表不可得时已有提示，本轮未把该反例扩大成实测的浏览器选择器故障。

建议：在无配置且显式 Hub 根的分支保留未覆盖状态和具体原因，或按既有输入契约明确拒绝；同时保持不映射同号/同名本机项目。可验证的通过条件：公共 CLI/API/MCP 在无 Hub 配置、传合法正整数 Hub 根时明确报告不可得/未覆盖，不能返回无原因的 `not_requested`；有同号且含命中的本机项目时仍不得猜出本机结果；普通独立本机查询和显式 local 的006行为保持。`tests/test_hub_documents_contracts.py:906–985` 已测“有配置但断线”的 Hub 根，并未覆盖“没有连接配置”的这个早退分支，故现有 `TC-007-search-fallback` passed 不能排除本反例。

## 与 PLAN 的对照

完整 diff 的主要职责和计划一致：纯 `Documents` 增加规范化摘要和精确项目集合；`ManagedDocuments` 管理本端副本、CAS、submission 与墓碑；共享协议/保护与 Local 项目同步分离；Hub 暂存、完整清单发布、连续资格、epoch 恢复；联合查询和精确引用路由；CLI/API/只读 MCP、两端 Web、后台重试、Hub 自有项目与一层关联；独立 Hub vendoring/HTML 打包及使用入口。`project_control.py` 未改，当前使用的项目绑定迁移和同步重算路径没有因此发现已确认的行为遗漏。AGENTS/CLAUDE 未被本 PR 修改。

计划末尾已记录并解释测试/方法调整：无损 gzip 原件、包原双流保存、控制竞态补测、SC11–16补充、普通 Windows 身份/ACL 准备、真实服务工具、CMS trace 回收、SC8包与完整回归门禁拆分，以及 E1/E2 新发现的证据缺口。当前35项/27自动8人工与定义000007、维护入口相符。未发现另一个应由维护者确认却被默默改写的范围决定。

**执行未完成仍是 PLAN 差距。** PLAN第102行要求各入口的准确原文，第105行明确重启后 CLI/MCP/Hub/Web 读取；当前平台探针尚未完成相应 stdio/Web 动作。PLAN第110–114行的服务网页持久和跨 OS 实机也未全部取证。末尾如实登记缺口不等于这些通过条件已被豁免。用户明确选择保留 E2 缺口，授权只支持继续其他验收，不能解释为删去 A9 或允许合并。E1额外轮草稿尚未应用，不属于本轮已审字节。

F8是已确认的 B6 行为遗漏，应先按现有范围修复并取得受影响回归；不需要扩成远端配置管理功能。此报告没有提出规格外的新产品阻断要求。

## 按角色从真实主入口逐步回放

Intent 的受影响者是跨设备项目资料使用者与管理 Hub 来源/项目/状态的维护者；项目实际还向 Agent 调用方和复跑维护者提供入口。以下每一跳依据当前当时可见的说明/页面/实际原件。静态可达性、既有实测和本轮反例各自只支持相应步骤。

### 本机使用者：新建项目，纳入资料，确认正确项目和原文

1. 起点 README第33–61行：主使用路径介绍006/007、支持格式、默认不同步、创建端管理及公开0.4.0/首次安装器尚不支持，链接 TRIAL_GUIDE 和007验收入口。用户能判断自己需要含007的源码/独立包。
2. 指南007节（第84行起）给双包构建、两个全新环境、Windows解释器替换、独立DB与空Agent根；继续到“本机创建和管理”，说明打开本机 Web“文档”、先建项目、再选择/拖入资料。上一节还给外部路径属于服务电脑、pending→明确refresh、项目ID/来源ID从列表取得、预算/格式/排除及失败含义。必要前置和输入取得可达。
3. 实际 Local 主导航“文档”提供项目创建、项目库选择、文件选择/拖放、目录来源、同步选择、检索及阅读区。当前源码 `static/index.html:58–73,126–160,189–207` 给出当步提示、逐份结果及后续按钮，不要求用户先知道内部源码路径。
4. 正式 SC14 原 PNG `local-web-review.png` 本轮实际打开：A成功/B严格UTF8失败/C成功，库仅A/C、ID与报告对应；当前 SC16 Local 原 PNG 本轮实际打开：目录明确未处理并引导“添加文档来源/保存后刷新”，合法文件仍成功。SC14 原文区清楚显示实际 Hub 读取端、原设备/档案/文档和版本。这支持已修的局部完成/确认路径；截图不单独承担整个 E1。

判断：正常发现、前置与资料管理/确认路径可达，原 F2/F7 的局部提示已补齐。本轮未确认另一处阻断这条正常主路径的缺口。

### 跨设备使用者：独立允许项目，理解快照和失败范围

1. README007小节直接说明独立项目文档许可、暂停保留、默认联合查询；下一跳指南“选择本机项目同步”（第118行起）给 configure-hub、sync-status→sync-policy→sync 的顺序。KEY/HID/generation含义、取得和失效后重新查看均明确。
2. Local文档页“项目文档同步选择”展示目标、稳定KEY、代次、本机选择与Hub确认/待办。第181–186行闭包绑定页面当时的值；正式用户发现的两次真实旧页原请求和拒绝原件分别对应同Hub旧G、换Hub恰相同G。不能把普通点击成功代替这两个CAS检查。
3. 指南“按项目检索与原文”给 projects --hub、互斥两种ID、local、共同一层范围、精确ref和覆盖边界；页面有项目端和档案范围选择。Local文档页的无凭据“打开Hub管理文档”及凭据来源说明可直接到创建端；Hub来源明确只读，未把关联当写授权。
4. 正式 SC15 的 Hub 原 PNG 本轮实际打开：P来源/命中写“暂停保留/共享文件可由其他允许来源更新”，Q为允许同步，原设备与接收时间可见。对应源码 `HubDocuments.sources/_snapshot_metadata` 按资格表达状态，不建立冻结分支。正常准确读取由 SC7/SC14原响应与源码支撑。
5. 失败确认：有配置但断线的范围/原因已有正式反例与产品分支；**没有配置时显式传Hub根出现F8**，必须修补这条公共调用路径。不能据其他失败分支已测而宣布全部错误说明一致。

判断：正常发现、独立授权、创建端跳转和保留状态可达；F8局限于一个错误前置分支的结果解释。

### Hub维护者：取得凭据，管理Hub库和外部来源，核采集/接收状态

1. README第55行→指南“Hub创建和管理”（第102行起）→既有汇总安装章节，提供HTTPS/TLS、state-dir、Hub地址与维护者交付纯文本hub-token文件。浏览器根匿名空壳本身也说明文件来源、同源头/仅内存及刷新后重选；不是只有SPEC里才有前置说明。
2. 认证后Hub页有创建普通/全局项目、选择/拖入、正确项目search→read→更新/移除；设备/Vibe投影只读。外部文件/目录在页面来源区明确转Hub电脑CLI，指南给 project create/list→documents add→refresh→sources/search→read；SOURCE来自add/sources，ID来自对应Hub项目列表，state-dir须与服务一致。
3. 当前 `document_api.py` 没有远程add/refresh外部路径路由，CLI仍可明确采集；Hub后端 `_own_project/_own_source` 校真实创建端，远程网页字节纳入和CLI外部采集路径没有再混成一个入口。原 F1关闭。
4. 从sources→files查看混合资料库：当前 `HubDocuments.files` 装饰原设备/档案/文档、来源、项目、采集/接收、状态及资格；CLI/API共用。SC15正式文件/来源原响应及真实CLI输出可定位，不必靠搜正文猜出处。F5关闭。暂停/恢复状态由控制行推导，F6关闭；Hub目录拖入的原PNG本轮实际打开，明确Hub电脑CLI和本机目录两种适用路径，F7关闭。
5. 故障恢复可沿指南第146–150行到recovery-status取得不透明state、审影响后recover，再显式refresh/项目重新选择；说明旧ref永久失效和保护文件不能被旧备份覆盖。维护输入取得与后果可判断。

判断：可发现性、局部输入、创建端管理和状态解释充分；指定服务身份的完整交付仍缺下述原件，不能由正常前景流程代替。

### Agent调用方：只读搜索、读取并解释覆盖

1. README“Agent接入”给实际 `skills/smm-search/SKILL.md` 链接；Skill第58–70行先要求核当前安装schema/CLI，说明预览版本边界，再给sources/projects→search→read。
2. include_hub列表的两端/coverage、互斥本机/Hub根、local、仅直接一层、失败不猜范围、正文必须按ref读回、Unicode码点及实际出处均在当步可见。MCP schema暴露相应参数和三个只读文档工具，没有新增文档写工具；管理转Web/CLI。
3. 当前正式列表TC验证默认本机数组、双端返回以及失败保留Local。正常文档工具及精确ref有正式原件；本轮又实际通过MCP复现F8，因此Agent不能只因收到正常JSON便声称远端根已覆盖。

判断：发现和正常参数链完整；F8影响失败解释。没有把只读annotations扩大解释为禁止既有最小项目登记。

### 复跑/交付维护者：找到独立包、执行条件和可复核证据

1. README007末行→`scripts/acceptance/README.md`007节。此处列27自动8人工、完整pytest、独立双包、acceptance/浏览器依赖、普通身份、合成档案、服务/实机边界和ESXi限制，继续链接SPEC/PLAN及manual-cases。
2. 包、平台、浏览器凭据、独立检查器和四种workflow模式可由同一路径找到；公钥证书取得、输入及下载解密核SHA说明在验收README末尾。`document-installed-e1`明确跳过服务；不能以该模式success代替E2。
3. 指南第150行和证据README提供当前结果入口；`acceptance-index.json`列35项收据/独立意见，`public-manifest.json`列36选件的原/公开摘要并区分派生内容。证据页明确未整体通过，Mac旧passed和新不足并列说明，没有继续把历史完整passed当当前E1已满足。
4. 维护者可运行公开校验器。本轮实际加`--original-root /private/tmp`退出0：36件原/公开SHA与长度、35唯一身份和登记对应均通过。工具明确输出`integrity_does_not_mean_delivery_passed=true`。这是完整性入口，不是业务验收入口的替代。

判断：相比前两轮的陈旧导航，当前数量、版本、执行边界和后续缺口已可从真实维护入口复核；未发现新的已确认发现障碍。

## 既有发现的独立关闭复核

| 发现 | 本轮当前实现/正式证据复核 | 结论 |
|---|---|---|
| F1 服务可由远程接口扫描外部路径 | `document_api.py:63–81`只保留既有来源set/remove及库字节管理；无HTTP add/refresh。SC13对两个来源及省略ID拒绝、完整状态/源打开守卫和真实CLI明确refresh有正式原件 | 原缺口关闭；不据TestClient等同服务身份验收 |
| F2 混合批次无逐份确认 | 两端逐文件catch、始终刷新库和逐份结果；SC14 Local原PNG本轮已打开，A/C成功、B编码失败，Hub当前同样代码与正式原件 | 原缺口关闭 |
| F3 Local到Hub创建端入口缺失 | Local文档页已有无凭据Hub链接、创建端/凭据说明；SC14正式真实点击到匿名空壳和URL/认证观察 | 原缺口关闭 |
| F4 Local阅读区丢实际读取端/出处 | 当前provenance阅读区使用响应archive_scope；本轮已打开正式SC14同bundle回退后图，实际读取端Hub及独立原身份可见 | 原缺口关闭；不将其说成所有平台重启后的回退实测 |
| F5 Hub文件状态缺元信息 | files与sources由Hub层共用装饰；正式SC15 HTTP与真实CLI逐来源/文件的原身份、项目、资格和时间断言，现产品绑定相符 | 原缺口关闭 |
| F6 暂停后保留状态不可见 | sources/search/read及coverage按各资格带sync_states/retained_snapshot；正式暂停→恢复、共享P暂停/Q允许推进V2的原件；实际打开Hub暂停PNG | 原缺口关闭，保留共享文件级版本语义 |
| F7 目录拖入缺适用指引 | 两端真实isDirectory分支及对应创建端说明；正式SC16两张原PNG本轮已打开，目录未处理/valid成功，目录扫描守卫和原件支持 | 原缺口关闭 |

这些判断来自当前源码、绑定与正式原件，v1/v2报告用于定位历史而非替本轮结论。原红灯/不足意见应继续保留。

## 验收证据复核与必要未完成项

本轮对索引的35份执行/人工目标及35份独立意见，实际读登记指向的私有result并逐目标重算SHA；进一步重算 **6582份唯一artifacts**，没有缺件或摘要不符。合并出的 **110项当前bindings** 全匹配。定义000007摘要为`d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。这证明原件存在/字节一致；业务结论还须结合断言、分配检查和下列适用范围。

当前索引29项passed = 27自动 + 用户发现 + 完整回归/所记CI门禁；六项insufficient_evidence = 三格E1 + 两服务E2 + 跨机器E2。它不表示A1–A10全部通过。27自动正式意见认领31个分配检查，包项只认build，不吞并人工gate。本轮读当前断言和正式执行报告/相关原件，没有重跑完整335项，也没有替代原生逐TC独立意见。

| 验收 | 现有可复核依据 | 本轮结论/适用边界 |
|---|---|---|
| A1 授权与入口 | 默认off/独立对话选择、KEY/HID/G、并发/ID复用/换Hub、真实旧页两次拒绝；SC1及用户发现正式意见 | 正常行为有通过依据，保留真实页面与接口分工 |
| A2 完整发布 | 两源多文件、双摘要/长度、原子清单、暂存不可读、中断/重试、2MiB/16MiB边界的正式SC2 | 自动检查有通过依据，不等于E2实机 |
| A3 生命周期 | active/paused分别覆盖撤回/离线/恢复、重叠连续资格和全局后台暂停；SC3与SC15共享推进 | 自动检查及局部平台有依据；完整平台尚缺项 |
| A4 身份顺序/恢复 | 独立origin、版本/配置/发布/授权/旧ack fences、独立保护和恢复冲突；SC4及补充竞态 | 未在本轮确认新的数据一致性缺陷；不是穷尽所有竞态证明 |
| A5 Hub自有 | 原生CLI明确采集、只读投影、项目关系及文件元信息；SC5/SC13/SC15 | 产品和自动检查有依据，指定服务完整证据仍不足 |
| A6 联合范围排序 | 正常共同一层范围、limit候选BM25、同版合并/异版独立、已配置失败分支 | **F8明确遗漏一个无配置失败分支**；不能称全部A6完成 |
| A7 准确原文 | SC7独立正文/Unicode范围/资格拒绝及同bundle回退；当前UI显示实际端 | 自动及已执行入口有通过依据；三格E1的私有/Hub stdio读取仍缺证 |
| A8 兼容/发现/包与回归 | 正式兼容/包/用户发现；完整本机回归334 passed+1 skipped；所记222e0e5常规三系统CI及独立gate | 已记候选有依据；当前最终head CI另核，F8不因回归绿灯消失 |
| A9 实际平台 | 已有大量真实普通身份、独立包、HTTPS/浏览器/stdio及真实服务原件 | **六个必需TC不足，整体不通过** |
| A10 网页库 | 两创建端项目、选择/拖放、精确读、更新/删除、纯文本、真实越端8拒绝及不变快照；SC10/SC14/SC16及人工局部 | 自动/用户发现和已有局部实测有依据；必要完整E1/E2不可省略 |

### 三格E1：已有入口证据不能补出未发生的调用

本轮实际读取三平台各五组stdio协议原件并解析各自两个完整原trace ZIP（全成员读取、CRC通过）。三个平台调用计数相同：`search_documents`2、`read_document`4、`list_document_sources`2、`list_projects`1、对话search/read各1。**四份文档read正文都只有A one/A two/B one/B two**；private、Hub D/E只在all搜索中出现。当前冻结探针`stdio_checks`也只循环`a_entries+b_entries`读取。这独立确认 `e1-ci-manual-review-v1.md`、`macos-protocol-recheck-v4.md` 指出的第一缺口，不依据报告文字推测实际执行。

第二缺口的源码顺序同样明确：`execute()`先stdio，再两端Web，最后`lifecycle()`真实停启；生命周期后只有CLI/API读。三格原trace最后网络分别是Mac Local `15:19:07.273Z` / Hub `15:19:01.062Z`，Ubuntu `15:31:35.346Z` / `15:31:26.286Z`，Windows `15:29:48.221Z` / `15:29:34.170Z`，均对应前置Web段；没有停启后的Web/stdio原文请求。PLAN第105行的入口义务仍未完成。

这是两项明确已写的证据缺口，不要求“每入口×每生命周期状态”无限组合。Mac历史v3完整passed保留，新请求v4对同一目标判insufficient_evidence是当前完整E1依据；用户发现TC的独立passed不受此自动撤销，也不能反过来代替E1。原件中的包/身份、CLI、Web、A/B stdio、准确原文及生命周期/清理仍是有效局部证据。

### E2服务：网页资料的停启持久和Windows后验清理仍缺证

本轮对照SPEC/PLAN/manual-cases、实际服务探针及`services-manual-review-v1.md`：Ubuntu user-systemd和Windows SCM/LocalService实际启动/身份、管理CLI明确采集、普通Local同步、服务网页两份资料及更新删除均已有有效原件。服务包装器复用的生命周期停启后只遍历native外部D/E采集资料，未再按新建网页项目查询保留的网页文件并用旧有效ref读取。不能将`native_cached_after_process_restart=true`扩成网页副本的持久验证。

Windows清理代码已发出disable/sc delete/netsh delete，PID/端口退出有证；但`service-cleanup.json`仅记录failures，netsh删除返回未核验，没有服务/规则不存在的后验查询。故不能认领完整服务/规则清理。未由这些缺证确认产品失败或残留真实存在。

维护者已明确选择“保留缺口，先完成其他验收”。此报告不建议擅自应用已展示草稿或继续服务重跑；必要项继续不足即可，不能升级整体通过。

### E2跨机器：缺获准资源，不是已经测出的产品错误

用户已排除家庭ESXi，且确认暂无替代机器。当前没有不同OS的两台真实机器之间HTTPS同步、远程网页上传和另一端精确读取/断线恢复的业务原件。托管各OS同宿主的服务、同机两个档案或环境能力探测都不能替代。保持uncertain/独立insufficient_evidence，等待用户提供获准资源；不擅自访问禁用资源、不缩减SPEC。

### 完整回归、公开完整性与最终head CI分别判断

正式回归原输出/JUnit为335项、334 passed/1 skipped；三系统所记CI JUnit各335项，Mac/Ubuntu329 passed+6 skipped，Windows330 passed+5 skipped，普通test extra缺Playwright造成的五个浏览器格明确跳过。对应实际浏览器由独立TC补证，不能把三系统单测说成三格E1都完成。包的18条命令及Local30/Hub31全部模块映射与当前绑定相符，Hub独立安装不依赖Local发行包；这些不代替服务或跨机器业务。

本轮实际运行公开校验器输出：

```json
{"integrity":"passed","public_files":36,"originals_checked":true,
 "case_count":35,"acceptance_status_counts":{"passed":29,"insufficient_evidence":6},
 "integrity_does_not_mean_delivery_passed":true}
```

最后一次GitHub只读快照：head仍为425f140；常规 Test packages 两组run `45211551148` / `45211535430` 中Ubuntu均SUCCESS，后一组Mac也SUCCESS，其余Mac/Windows仍IN_PROGRESS。此处只记录审查时状态，不预判最终结果。即使后续全部成功，F8与六项必要缺证也不会因此消失；本报告提交后产生的新最终head还须重新核其CI。

## 后续通过条件

先保留本候选和本轮反例，按现有B6修F8、补“无连接配置+显式Hub根”的公共入口正负控，并按项目阶段流程记录相关实施/验证调整；不要只改说明把当前错误覆盖合理化。保留F1–F7历史及已关闭依据。E1补证若获额外轮授权，只补既有明确义务并由独立Reviewer核新原件；E2继续遵守已选择的保留缺口和资源限制。

只有产品缺口修复、全部必要当前同版TC/平台和需求级独立判定通过、最终head三系统CI实际通过后，才具备PLAN要求的交付与合并条件。本轮仅提供PR审查意见，不授R007/整体需求passed，也不执行合并。
