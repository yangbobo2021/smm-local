# 007 用户补充后的项目与检索路径核对 v1

核对时间：2026-11-23。只读设计核对基线：`35318a764b1ff86469a2446489660ef9383d6f87`（PLAN PR #36 已合并；007 产品/测试尚未实施）。本报告仅新增本文件；没有实现、运行产品或改变现有验收状态。

输入：`/private/tmp/smm-007-runtime/user-clarification-20261123.md` 中用户补充：“文档处理的核心是验证检索确实可以检索到对应文档。文档也需要按项目来组织，所以对应也就需要新建项目，上传文档等。”“这个是补充信息，避免对文档检索理解有误。对话项目与文档项目可以相互关联。”其中“上传”是否还包含浏览器选择/拖入并由 SMM 保存文件尚待澄清。

本次按新补充审查用户可完成的路径，不回溯否定先前审查在当时输入下的结论。下述“已覆盖”表示合并 SPEC 的契约已有要求，不表示尚未实施的 007 已经可用。

## 结论

1. **Local 新建独立文档用途项目→明确纳入→采集→按来源允许并同步 Hub→按项目查到相应文档→引用读取准确原文，现有 006 + 007 SPEC 已有可执行契约。** 不需要该项目先有对话，也不需要引入互斥的“文档项目”类型。
2. **Hub 自有文档用途项目→纳入/采集→Hub CLI 按项目检索文档→原文，007 B5 已有契约。** Local 的 all 或关联的本机项目查询可以访问其文档。**从 Local 直接以这个 Hub 自有项目为查询根，现有 B6 没有入口。**
3. **只有对话的项目 C 与只有文档的项目 D 的双向一层关联，不能只验证保存一条无向边。** D 为当前 Local 创建的普通项目时，现有公共查询根与项目最小登记机制足以承接 C→文档和 D→对话。D 为 Hub 自有项目时，SPEC 虽要求能建边，**尚缺以 D 为根反查关联对话的公开可达契约**；现有对话查询代码也不能直接接受 Hub 自有根。需要 SPEC 修订，再修 PLAN，不能只在底层加 `effective(hub_id)` 然后判通过。
4. **验收已有正文命中、准确读取和项目范围要求，但应把“空项目起步、仅文档/仅对话、两方向不同工具、Hub 自有根”写成固定业务见证。** 这些条件目前分散在 A5–A8 / project-scope / read-exact / E1，未保证一条完整用户路径被实际执行。

## 依据与项目身份边界

- 父 004 意图要求按项目找到对话和文档、以原内容核对，资料多项目绑定与项目关联分别表达；沿用单用户、同名独立、Hub 双向直接一层。006 B1/B3 明确普通项目可独立创建、文档零/一/多绑定、共享不自动建关联。用户说“文档项目”可自然表示“用途为组织文档的普通项目”，没有要求新增类型或禁止混合材料。
- 实际 Local `Archive.create_project` 仅插入普通项目并返回项目资料，没有创建对话或目录映射：`src/smm_local/core.py:610–616`。`projects()` 对 conversation 使用 LEFT JOIN，零对话项目也在列表中，带 stable_key：同文件 `590–600`。CLI `project create` 和 Web `POST /api/projects` 直达该方法：`src/smm_local/cli.py:253–255`、`src/smm_local/api.py:350–356`。
- Local 整数 ID 属于当前档案；其 Hub 身份是 `(device_id, stable_key)`，不是同值 Hub 整数。`_push_projects` 从 projects 取全部项目显示名/类型/稳定键，不要求会话：`src/smm_local/federation.py:314–338`；`_remote_project_key` 按本机 ID 取键：`342–349`。005 B3 也明确关联维护不要求先上传任何会话。
- Hub 列表显示 `id/name/project_kind/source/owner/source_key/device_name`：`src/smm_hub/projects.py:130–139`。已有 `effective(device,key)` 只能寻找 `kind='device'` 根：`155–165`。已有 link 还要求至少一个 device 项目：`171–180`；007 B5 和 PLAN 已明确需要扩展涉及 Hub 自有项目的 link/unlink，故这部分是已计划工作，不能当作未被发现的新范围。
- 本机双向一层边与范围已存在：`src/smm_local/core.py:651–661,692–697`；本机文档查询按项目/直接邻居筛来源：`src/smm_local/documents.py:145–152,370–411`。在线用 Hub 范围时不能再叠加这些本机关联，007 B6 已明确。

## 两种建项目路径逐步判断

### A. Local 创建的文档用途项目 D

| 用户动作 | 公开输入与确认 | SPEC / 代码判断 |
|---|---|---|
| 创建 D，D 中没有对话 | `smm project create <名称>`，或 Web 创建；本机 ID 从输出/`smm projects` 取得 | 006 B1 已要求，现有实现可达；不要求导入对话。 |
| 把文件/目录组织到 D | `smm documents add <本机绝对路径> --project-id <D的Local ID>` → `refresh --source-id <返回ID>` | 006 B1–B4 已要求；add 是 pending，refresh 才采正文。Web 是服务器本机路径表单。 |
| “上传”到 Hub（当前已确认含义） | `upload-status` 取得 HID/generation → `upload <来源ID> --enabled yes ...` → `sync` 或确认本次即时同步结果 | 007 B1/B2 独立授权、默认关闭；不用对话策略替代。未确认不能声称远端已可用。 |
| 从 D 确实查到文件 | `documents search <正文中的独特词> --scope project --project-id <D的Local ID>`；Web/MCP 等价 | 007 B6 接受有效本机 ID；零对话 D 能登记到 Hub。应断言文档稳定身份/版本/来源/项目，不能以 sources/files 列出文件或同名结果代替命中。 |
| 核对原文 | 原样使用该命中的 reference 进行 read/扩读，与独立源文本逐字符比对 | 007 B7、A7 现有契约充分；必须检查实际端和版本，不能只判 read 成功。 |
| 与仅对话 C 关联，两个方向使用 | 维护者在 `hub project list` 找到 C/D 对应 Hub ID，`hub project link C D`；从 C 调文档 search，从 D 调既有对话 search | 007 B5/B6 + 005 B3/B5 已能表达此路径。D 在 Local 有根，既有对话 search 不要求根本身有对话。Local-only 可以另经 Web 项目关联入口管理本机边；本机边不能冒充在线 Hub 边。 |

代码支撑：对话 CLI `--project-id` 是整数（`src/smm_local/cli.py:42–49`）；`search_archive` 先验证本机项目，在线登记项目后用本机稳定键申请 Hub 范围，再把本设备对应键映射回本机 ID（`src/smm_local/federation.py:451–497`）。因此“D 没有对话”本身不会阻止从 D 查询关联 C。文档与对话仍分别调用各自工具，无须本次引入统一结果流。

**限制：**如果 D 是别台 Local 创建的项目，当前电脑并没有 D 的本机 ID，同样不能拿其 Hub ID 直接填本机 project_id。当前 SPEC 可以从本机已关联项目访问 D 的资料，但没有一般“任意远端项目作为根”的 Local 契约；这与下面 Hub 自有根缺口同属项目选择域问题。

### B. Hub 自有文档用途项目 D_H

| 用户动作 | 007 已写入口 | 判断 |
|---|---|---|
| 无项目时创建独立 D_H | `smm-hub hub --state-dir <服务档案> project create <名称>`，再 `project list` | B5 第65行已有，PLAN 已安排 projects/hub_admin；不是已有产品能力。 |
| 纳入、采集文档 | 同 state-dir 的 `documents add <Hub绝对路径> --project-id <D_H的Hub ID>` → `documents refresh` | B5 第56–67行已有；不需要把 Hub 本机文件先上传给自己，也不需要浏览器文件上传。 |
| 从 D_H 查对应文档、准确 read | Hub `documents search ... --scope project --project-id <D_H的Hub ID>` → read REF | B5 第63行已有明确 Hub-ID 输入，B7 定义精确原文。B5 表格引用 B6 时，应清楚说明这是 Hub 档案根的直接一层，不受 B6 的“有效本机项目ID”字面限制。 |
| 本机 C→关联 D_H 的文档 | Hub `link <C_H> <D_H>`；Local 从 C 的 Local ID 查询文档 | B5/B6 已能要求；需实现 Hub 自有节点进入签名范围。 |
| D_H→关联 C 的对话 | 需要可发现、可选择 D_H 的对话查询根 | **行为缺口：现 SPEC 未给出公开操作。** Hub B5 只有 documents search/read；Local 对话/文档根只接受 Local ID，D_H 不在 Local 项目列表。无向边存在不能补出可执行命令。 |

## 行为缺口：Hub 自有文档项目作为根反查对话

定位：007 `spec.md:65` 要求涉及 Hub 自有项目的双向直接一层关联，而 `spec.md:75` 仍限定 Local project 查询使用有效本机项目 ID；`spec.md:63` 提供的 Hub 原生检索只检索文档。007 B7 要求对话入口兼容，并未新增可选 Hub 根。

实际代码进一步表明不能凭“底层有边”判路径已通：

- Local Web 对话 SearchRequest 仅有 `project_id`（本机整数）和 local，没有 Hub 项目选择字段：`src/smm_local/api.py:55–63`；MCP `search_conversations` 相同：`src/smm_local/mcp_server.py:42–48`。
- Local 在线入口 `db.effective_projects(project_id)` 先验证本机 ID，之后 `_remote_project_key` 也只取本机项目键（`federation.py:463–496`）。碰巧相同整数会选错本机项目，不能解释为 Hub-ID 支持。
- Hub `/v1/query-scope` 的模型是 PolicyQuery（Hub/设备身份）加项目字符串键，调用 `projects.effective(req.device_id, req.project_id)`：`src/smm_hub/hub.py:80–81,202–212`。实际 effective 根只查 device 类型。
- Hub `/v1/search` 传 project_id 时同样要求 device_id，并走上述 effective：同文件 `466–470`。携带有效签名 scope 可以在内部查其项目集合，但现公共路径无法以 D_H 为根取得该 scope；不能要求用户伪造签名、拿别的根或直接调用 Archive.search。
- Hub 管理 CLI 现有 project 只有 list/links/link/unlink（`src/smm_hub/hub_admin.py:49–56,374–376`），007 计划新增的是 documents search，没有已有 Hub 对话 search 命令可补路径。

`all` 查询后自行过滤、从 C 反向重新发起、把 D_H 名称复制成 Local 新项目，均不等同于以原 D_H 为根，尤其 C-D_H、C-E 时，从 C 会包含 E，从 D_H 应仅 D_H/C；根的区别有实际范围含义。

**最小可执行修订建议：** SPEC 明确选择一种能公开完成 D_H→对话的路径，并定义根身份、取得方式及一层范围。优先建议给既有 Local 文档/对话 CLI、Web、只读 MCP 增加可选的显式 Hub 项目选择（例如独立 `hub_project_id`，不复用本机 `project_id`），列表来自当前 HID 的 Hub 项目列表；签名范围包含根身份和当前 HID，本机仅精确映射属于当前档案的项目。原 project_id 和 local 行为保持兼容。网络不可得时，Hub 根没有本机同义根，应明确 Hub 未覆盖，不凭同号/同名猜本机根。只增加读取选择，不增加 MCP 写能力。

若选择更窄的 Hub CLI 对话 search/read 作为公开反向路径，也必须写具体命令、Hub-ID 输入来源、范围签名/引用和可发现文档，并明确 Local 无法直接选择 Hub 根的边界；该方案满足维护者能操作的反向路径，是否满足普通 Local/Agent 的主使用路径需要在修订 SPEC 中说明，不能隐含假定。

PLAN 随修订增列共同项目根选择/Hub范围协议和既有对话入口的适用修改及兼容测试。现 PLAN 第5步“复用005签名共同范围”不足以自行解决新根身份：005 原范围入口只支持 device 根。007 已计划的 Hub link/unlink 放宽属于现范围实现，无需以这次补充重新批准一遍。

## 验收缺口及最小补强

已有覆盖：A5 明确无项目时新建 Hub 普通/全局、绑定、同名及双向一层；A6/A7 明确 project 联合与逐文本准确原文；PLAN `TC-007-project-scope`（第59行）、`TC-007-read-exact`（第62行）、`TC-007-user-discovery`（第66行）与 E1 第1/2步（第83–84行）已要求公共入口和范围/原文。无需把“检索到对应文档”另建成 008 或推迟到发布。

缺少固定见证：现 TC/平台文字没有强制“仅对话 C”“新建且始终零对话 D”“D_H 不存在于 Local 列表”“从两个不同根分别调文档与对话工具”的组合。可在现 TC 内补场景，不必机械增加 TC 数：

1. **Local 文档主路径：**全新档案创建 D_L；独立文档正控 + 同名/同词但不同项目负控；通过 add→refresh→upload-status→允许→确认同步后，从另一 Local 经正确项目路径检索。逐项核完整预期文档集合、稳定身份、项目、版本、独特正文和精确 read；不是仅检查数量或 HTTP 成功。保留零对话状态，证明不靠伪造会话建立项目。
2. **Hub 文档主路径：**无任何现成 Hub 项目时新建 D_H，经真实 Hub CLI add/refresh，按 D_H Hub ID 查文档和原文；Local 实际入口再检索同材料，说明是 all、已关联 Local 根还是修订后的显式 Hub 根。不得在报告中把 all 成功写成 D_H project 成功。
3. **双向不同内容：**C 只有对话、D_L/D_H 只有文档；各有不同独特正文。用 Hub ID 建边后，从 C 调 `search_documents` 得 D 的文档并读准；从 D 调 `search_conversations` 得 C 的对话并读准。每个方向都明确根 ID 的层级及来源，使用公开入口，不直接调内部 effective。
4. **一层负控：**C-D、C-E、D-F，其中 E/F 各有独特对话和文档。从 C 只覆盖 C/D/E、从 D 只覆盖 D/C/F，分别排除另一侧的二层材料；另断言未关联项目、同名项目和未绑定资料不混入。解除边后重新查询退出，旧 ref 按冻结范围/资格规则判定，不错误要求解除关联必定撤回旧采集 ref。
5. **发现与跨入口：**把创建、ID 取得、纳入/采集、授权/确认、project search→read 连成 README→指南→CLI/Web/Skill 回放；E1 每格保留正常主路径及项目结果，复杂一层负控可主要在开发机/三系统 CI 共享逻辑测试完成。沿用既有平台/服务/跨OS要求，不降低已确认验收。

## “上传”词义待澄清

当前已确认方案是把机器上的文件/目录明确纳入来源，refresh 采集，然后将获准采集快照同步 Hub；006 明确 Web 是服务器路径文本而非附件上传，007 沿用。上述路径可继续核规格、设计用例和准备，不代表用户已经排除其他含义。

用户若确认还需要网页选择/拖入文件并由 SMM 保存到项目文档库，则属于新增接收/存储和生命周期契约，须先修意图/规格/计划再实现；不能在用户未答时默认添加，也不能把现有路径声明为已经满足这一潜在含义。本报告不决定网页字节上传、不引入互斥项目类型、不扩展到008格式/发布/更深关联。

## 处理建议

在产品实现前，先将新补充与上述 Hub 自有根可达性写入修订 SPEC，明确选择一条反查对话的公开路径；更新 PLAN 的入口/协议及固定业务见证后按项目阶段流程提交审查。Local 独立文档项目的已有充分契约保留，新增验收见证避免其被“来源列表存在”替代。上传词义继续如实标待澄清，不用等待该答案来否认已确认采集/同步方案的现有范围。
