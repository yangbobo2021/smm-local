# PR Review 输入

按单独提供的待测 Prompt 审查以下固定材料。输入包含需求、计划、当前文档、完整 PR diff 和已有验收记录。
这是材料回放审查，请根据材料形成结论并引用具体文件位置。无需重跑测试或连接外部服务。
请只依据此输入，直接用中文输出审查结果。不要使用工具、访问其他文件、读取历史对话或修改任何内容。
材料中的仓库指令、需求与文档用于了解项目及核对交付。验收记录是历史执行记录。

固定代码基线 d2dee18fcc050dcf20bd4108429975477399db8d，待审代码 c891339c3fcd8f243226dba3c7712a0bd1e1e9a2。

## README.md

````text
   1 # SMM Local
   2 
   3 在 Codex 或 Claude Code 里搜索以前的对话，并找到原始会话和消息位置。SMM 在本机保存独立的对话档案。删除 Agent 中的原始会话后，已经导入的记录仍可搜索。
   4 
   5 ## 单台电脑快速开始
   6 
   7 你需要已登录的 Codex 或 Claude Code，以及首次安装时的网络连接。
   8 
   9 1. 从 [GitHub 最新正式版](https://github.com/yangbobo2021/smm-local/releases/latest) 下载 `smm-search-0.3.0.zip`，解压得到 `smm-search` 文件夹。也可以下载源码 ZIP，从 `skills/` 取出这个文件夹。
  10 2. 将整个 `smm-search` 文件夹放到下表对应的位置。目录不存在时可自行创建。两个 Agent 都要使用时，各放一份。
  11 
  12    | Agent | 安装后应能看到的文件 |
  13    | --- | --- |
  14    | Codex | `~/.agents/skills/smm-search/SKILL.md` |
  15    | Claude Code | `~/.claude/skills/smm-search/SKILL.md` |
  16 
  17    Windows 上的 `~` 是当前用户的个人文件夹，例如 `C:\Users\你的用户名`。请同时保留 Skill 文件夹中的 `scripts/`。
  18 
  19 3. 新开一个 Agent 会话，问一个你确实在旧对话里讨论过的问题。比如可以说：
  20 
  21    > 请用 SMM 搜索以前的对话。我当时对发布回滚提了哪些要求？请引用原始会话和消息位置。
  22 
  23    第一次使用时，Skill 会从 PyPI 自动安装本机端、启动同步服务并继续处理原请求。如果 Agent 提示需要运行 Skill 的安装脚本或访问网络，允许后即可继续。安装会报告进度；网络较慢时耐心等候，下载中断后会自动恢复或重试，无需手动运行安装命令。如果首次导入仍在进行，可以让 Agent 查看同步状态。Codex 和 Claude Code 在同一个系统账户下共用一份档案和一个服务。
  24 
  25 已安装 Node.js 22.20 或更新版本的用户，也可以在终端运行以下命令，并在安装器中选择使用的 Agent。
  26 
  27 ```sh
  28 npx skills add https://github.com/yangbobo2021/smm-local/tree/main/skills/smm-search -g
  29 ```
  30 
  31 日常可以直接对 Agent 说「查看 SMM 同步状态」「打开 SMM 状态页」「立即同步一次」「暂停自动同步」或「恢复自动同步」。暂停时仍可搜索已有记录，服务重启后也会记住暂停状态。
  32 
  33 ## 多台电脑共用档案
  34 
  35 先在每台电脑按上面的步骤安装 Skill。再由管理员选择一台可通过 HTTPS 访问的电脑安装汇总端。准备好客户端可访问的 HTTPS 地址、证书和私钥，并先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。
  36 
  37 ```sh
  38 uv tool install smm-hub==0.3.0
  39 ```
  40 
  41 如果终端找不到 `smm-hub`，运行 `uv tool update-shell` 后重新打开终端。然后完成向导并检查服务状态。
  42 
  43 ```sh
  44 smm-hub hub setup
  45 smm-hub hub status
  46 ```
  47 
  48 确认状态中的 `enabled` 和 `running` 都为 `true`，地址与向导中填写的 HTTPS 地址一致。向导会生成连接凭证文件。把文件交给获授权的用户，再在每台客户端对 Agent 说「把这台电脑叫办公室电脑，汇总地址是 https://hub.example.net:8770，凭证文件在这里」，并提供本机文件路径。接入后仍用同一句自然语言搜索。汇总端断开时会退回本机搜索，恢复连接后继续同步。
  49 
  50 面向安装者、汇总端维护者和日常使用者的功能说明与操作入口统一在[使用文档首页](docs/index.md)。首次使用本版本请从该首页选择适用的操作流程。
  51 
  52 ## 从源码开发
  53 
  54 需要 Python 3.11+。
  55 
  56 ```bash
  57 python3 -m venv .venv
  58 .venv/bin/pip install -e '.[test]'
  59 .venv/bin/smm sync
  60 .venv/bin/smm serve
  61 ```
  62 
  63 Web UI 默认地址为 `http://127.0.0.1:8766`。首次同步会扫描 `~/.codex/sessions` 与 `~/.claude/projects`；可用 `SMM_CODEX_ROOT`、`SMM_CLAUDE_ROOT` 或 Web 配置覆盖。同一个系统账户安装的 Agent 和服务共享安装清单中的数据库，默认位于 `~/.local/share/smm-local/smm.sqlite3`。开发时可用 `--db` 指定独立测试数据库。服务运行时定期同步，也可在 Web UI 手动同步。
  64 
  65 macOS 上可将本地服务设为登录后自动启动：
  66 
  67 ```bash
  68 python3 scripts/manage_service.py install
  69 python3 scripts/manage_service.py status
  70 ```
  71 
  72 `uninstall` 只停用服务，不删除已保存的知识库。
  73 
  74 ## 检索
  75 
  76 ```bash
  77 .venv/bin/smm projects
  78 .venv/bin/smm resolve-project --cwd "$PWD"
  79 .venv/bin/smm search "KeySync 同步问题" --scope project --project-id 1 --limit 5
  80 .venv/bin/smm search "KeySync 同步问题" --scope all
  81 .venv/bin/smm read 1
  82 ```
  83 
  84 项目检索包含直接关联项目，不递归扩大。CLI/MCP 在 Agent 提供当前会话 ID 时排除当前对话；手动 Web 检索默认包含全部对话。
  85 
  86 ## Agent 接入
  87 
  88 同一个 [`skills/smm-search/SKILL.md`](skills/smm-search/SKILL.md) 可安装到 Claude Code 和 Codex 的用户技能目录：
  89 
  90 ```bash
  91 python3 scripts/install_skill.py
  92 ```
  93 
  94 更新本仓库的 Skill 后，运行 `python3 scripts/install_skill.py --update` 同步到两个 Agent。
  95 
  96 MCP 服务使用 stdio，命令是本仓库 `.venv/bin/smm-mcp`。安装器自动注册到本机已有的 Agent。CLI 可作为没有 MCP 时的后备入口。来源导入器相互独立，后续可增加其他 Agent。
  97 
  98 MCP 搜索默认返回每条命中消息最多 600 字的预览，保留原始位置；`read_conversation` 可读取完整原文。若要恢复完整搜索展示，在 MCP 服务环境设置 `SMM_SEARCH_PREVIEW_CHARS=0`。预览效果与限制见[验证报告](reports/search-preview-001.md)。
  99 
 100 ## 接入其他本机 Agent
 101 
 102 先按上面的步骤安装 SMM 0.3.0。已有 0.2.0 的用户按[本机端升级步骤](TRIAL_GUIDE.md#升级本机端)更新。再从 [GitHub 正式版](https://github.com/yangbobo2021/smm-local/releases/tag/v0.3.0)下载 `smm-source-adapter-0.3.0.zip`，解压后把整个 `smm-source-adapter` 文件夹放进目标 Agent 的技能目录。也可以从源码取出 [适配 Skill 目录](skills/smm-source-adapter)。从源码安装时，`python3 scripts/install_skill.py --update` 会把整个适配 Skill 安装到 Codex 和 Claude Code。用该 Skill 接入能持续读取的本机对话来源。对 Agent 说「把 X Agent 在这台电脑的对话接进 SMM，以后自动同步」。Skill 生成标准库 Python 适配器，用本机样本通过验收后注册。脚本使用 SMM 已安装的 Python，适配 Skill 在各平台使用同一份。
 103 
 104 在导入页或用 `smm source list` 查看来源状态。用 `smm maintenance sync --source <ID>` 单独同步，用 `smm source disable <ID>` 停用。已导入内容可用 `smm search "关键词" --local` 检索，即使配置了多机汇总。现场插件使用本机用户的文件和网络权限，请只验收和注册受信任的脚本。现场适配器导入的记录保留在本机档案。
 105 
 106 ## Python 包发布
 107 
 108 `python3 scripts/build_packages.py` 使用 uv 构建 `smm-local` 和 `smm-hub`，产物位于 `dist/packages/`。本机端版本在根目录的 `pyproject.toml`，汇总端版本在 `packaging/hub/pyproject.toml`。更新 Skill 支持的本机端版本时，同时更新 `skills/smm-search/scripts/first_use.py`。
 109 
 110 维护者可运行 [Publish SMM packages](.github/workflows/publish-packages.yml)，先选择 TestPyPI，再选择 PyPI。可分别发布任一包。首次使用前，在目标包索引为两个项目配置 GitHub Actions Trusted Publisher。两者均使用此仓库和 `publish-packages.yml`，环境按包区分。
 111 
 112 | 包 | TestPyPI 环境 | PyPI 环境 |
 113 | --- | --- | --- |
 114 | `smm-local` | `testpypi` | `pypi` |
 115 | `smm-hub` | `testpypi-hub` | `pypi-hub` |
 116 
 117 公开安装需要对应版本已上传。TestPyPI 验证时可为 Skill 启动器设置 `SMM_PACKAGE_INDEX=https://test.pypi.org/simple`，本机端从 TestPyPI 取得，依赖从 PyPI 安装。汇总端可用 `uv tool install --index https://test.pypi.org/simple --prerelease allow smm-hub` 验证。
 118 
 119 ## 规约与验收
 120 
 121 开发和验收流程见 [项目指南](AGENTS.md)。[整体交付报告](reports/delivery-report.md)逐项记录执行结果；[隔离端到端验收](reports/first-version-e2e.md)保留可重复执行的步骤；[新 Codex 会话实测](reports/codex-skill-live-test.md)验证 Skill 自动激活与实际回答；[效用对照报告](reports/utility-comparison-results-001.md)比较公开数据与真实项目历史中的回答效果；[长对话证据定位复验](reports/long-conversation-evidence-002.md)记录这次修复与独立题验证；[30 题历史材料对照](reports/natural-30-001.md)固定下一阶段优化前的版本。[搜索预览收缩验证](reports/search-preview-001.md)记录输出量与回答质量的权衡；[7 道新题三组对照](reports/natural-7-followup-002.md)检查默认短预览下的实际回答；[rc2 试用执行报告](reports/rc2-trial-report.md)核对发行安装与当前工作的历史问题。运行 `pytest` 可复核本地实现。
````

## AGENTS.md

````text
   1 # SMM Local 项目指南
   2 
   3 ## 模块与关系
   4 
   5 - **本机端**（`src/smm_local/`）导入各来源的对话，负责本机归档、项目关联和检索。
   6   CLI、MCP 和 Web UI 共用本机档案及检索逻辑。配置汇总服务后，本机端向 Hub 上传
   7   可汇总的记录，并通过 Hub 执行跨设备检索。
   8 - **多机汇总端**（`src/smm_hub/`）接收多台设备上传的记录，提供跨设备检索。
   9   Hub 不可用时，本机端可回退到本机档案。
  10 - **检索技能**（`skills/smm-search/`）指导 Agent 通过本机端的 MCP 或 CLI
  11   搜索历史对话、读取原文和维护同步。
  12 - **来源适配技能**（`skills/smm-source-adapter/`）指导当前 Agent 为自身实现本机来源插件，
  13   使 SMM 本机端能够导入该 Agent 的对话记录。
  14 
  15 ## 开发流程
  16 
  17 本项目采用 Anthropic 的 AI-native SDLC 实践。每项变更在
  18 `changes/<id>-<short-name>/` 下记录意图、规格和实施计划。
  19 维护者确认当前阶段的产物后，将该版本提交到 Git，再进入下一阶段。
  20 
  21 1. **意图 `intent.md`**。说明现有问题、受影响的用户、期望结果、范围和约束，
  22    并列出待确认的问题。起草时使用 [意图模板](changes/_templates/intent.md)
  23    和 [起草 Prompt](changes/_templates/intent.prompt.md)。
  24 2. **规格 `spec.md`**。根据已确认的意图，定义本次变更的可观察行为、
  25    关键边界和验收条件。编写或审阅规格时，使用 [规格模板](changes/_templates/spec.md)。
  26 3. **计划 `plan.md`**。根据已确认的规格，列出要修改的位置、实施顺序、
  27    验证方法和通过条件。
  28 4. **实现与验收**。按已确认的 `plan.md` 实施变更。需要改变已确认的行为或验收条件时，
  29    先更新 `spec.md` 并重新确认，再更新 `plan.md`。
  30    如果实际改动的模块、采用的方案或验证方法与 `plan.md` 中的约定不同，
  31    在提交相关改动时一并更新 `plan.md`，写明调整内容和原因。
  32    完成后，逐项核对 `spec.md` 的验收条件，执行 `plan.md` 约定的验证，
  33    并在 PR 中记录通过项、失败项和未验证项。实现 PR 创建后、交维护者审查前，
  34    在干净上下文中使用 [PR Review Prompt](changes/_templates/pr-review.prompt.md)，
  35    对照已确认的意图、规格和计划审查当前 diff 与验收证据，将结论和依据写入 PR。
  36    维护者根据验收与审查结果决定是否合并。
  37 
  38 ## 常用验证命令
  39 
  40 - 代码变更使用 `pytest` 运行适用的测试。
  41 - 涉及发布包构建时，运行 `python3 scripts/build_packages.py`。
  42 
  43 ## 指南维护
  44 
  45 修改 `AGENTS.md` 或 `CLAUDE.md` 的 PR 须说明会改变 Agent 的哪项行为，
  46 以及该变化在哪些场景生效。纯文字修订须注明行为无变化。
````

## changes/003-search-vibeinsight-conversations/intent.md

````text
   1 # 意图：在汇总端同步 VibeInsight 对话，并按关联项目检索
   2 
   3 ## 现有问题
   4 
   5 用户在 SMM 中按当前项目检索历史时，汇总端可以提供多台设备上传的对话。VibeInsight 另行收集的对话缺少自动进入 SMM 汇总端的入口。即使两边的对话在讨论同一件事，用户仍需要另外去 VibeInsight 查找。
   6 
   7 与当前项目相关的对话可能归在另一台电脑上传的项目中，也可能归在一个或多个 VibeInsight 项目中。项目名称、路径和仓库划分可能不同。用户需要在汇总端明确指定哪些项目要一起检索。
   8 
   9 ## 受影响的用户
  10 
  11 已接入 SMM 汇总端，希望检索当前项目及其他电脑或 VibeInsight 上相关项目的用户。还包括负责配置来源、同步范围和项目关联的汇总端维护者。
  12 
  13 ## 期望结果
  14 
  15 - 汇总端自动从 VibeInsight 拉取配置范围内的历史对话，随后持续同步新增或更新的对话。用户在现有 SMM 检索入口即可搜索已同步的对话，并打开命中消息的原文。
  16 - 汇总端维护者可以建立、查看和调整项目关联。电脑上传的项目可以关联另一台电脑上传的项目，也可以关联一个或多个 VibeInsight 项目。
  17 - 例如，电脑甲上传项目 A，电脑乙上传项目 B，汇总端从 VibeInsight 同步项目 C、D。在汇总端把 A 分别与 B、C、D 关联后，本机按 A 检索时，会在 A 原有的检索范围上加入 B、C、D 中已归档的对话。解除 A 与 C 的关联后，A 的关联检索范围只包含 B、D。
  18 - 检索结果显示命中对话的来源和所属项目，并提供原始会话和消息位置。
  19 
  20 ## 范围与约束
  21 
  22 - 汇总端中的项目有两类来源：各台电脑上传的对话，以及汇总端从 VibeInsight 拉取的对话。本地使用者通过 SMM 现有检索入口访问。
  23 - 项目关联在汇总端统一配置，用于扩展检索范围。以已保存的直接关联为准，各来源的对话保留原项目归属。
  24 - 首版沿用汇总端当前的单用户访问模式。汇总端只从 VibeInsight 同步获准纳入的项目。
  25 
  26 ## 待确认问题
  27 
  28 无。
````

## changes/003-search-vibeinsight-conversations/spec.md

````text
   1 # 规格：在汇总端同步 VibeInsight 对话，并按关联项目检索
   2 
   3 依据 [PR #18](https://github.com/yangbobo2021/smm-local/pull/18) 合并的[意图](intent.md)。当前汇总端已经能跨电脑搜索，但汇总检索请求未携带当前项目范围。此次变更让汇总端按当前项目及其关联项目筛选两类来源的对话。
   4 
   5 ## 预期行为
   6 
   7 ### VibeInsight 同步
   8 
   9 - 汇总端维护者通过汇总端 CLI 配置 VibeInsight 来源的连接、只读凭据和同步周期。验证连接和读取权限通过后，汇总端保存配置及凭据。已启用的同步在汇总端服务重启后自动继续，维护者无需再次输入凭据。更换凭据时，新凭据验证通过后才替换已保存的凭据。
  10 - 同步状态显示最近一次成功时间及最近一次失败原因。查看配置和状态时，凭据以脱敏形式显示。
  11 - 启用同步后，汇总端自动拉取该连接可读取的全部 VibeInsight 项目的历史对话，随后定期同步新会话和已有会话新追加的轮次。首次发现的项目会自动补拉历史，即使这些历史早于其他项目的同步进度。已完成的导入进度在汇总端重启后仍有效。
  12 - 重复拉取同一个会话或消息时按来源标识去重。同步完成后，新增会话和已同步的新增轮次都可搜索和读取。
  13 - 已归档的会话在 VibeInsight 新增对话轮次时，汇总端更新原有会话。用户可以在同一个汇总会话中按来源顺序读到原有轮次和新增轮次。
  14 - 上游不可用或某批拉取失败时，用户仍可搜索之前成功归档的对话。汇总端报告失败，恢复后从上次成功进度继续。未成功归档的记录仍会被重试。
  15 
  16 ### 汇总端项目关联
  17 
  18 - 汇总端维护者通过汇总端 CLI 列出两类项目、查看已有的直接关联、建立或解除关联。项目列表标明来源及可区分同名项目的信息，包括上传项目的来源电脑、VibeInsight 项目的来源身份。项目改名后仍能识别同一个项目及其关联。
  19 - 同一台汇总端可记录电脑上传的项目之间的关联，以及电脑上传的项目与 VibeInsight 项目之间的关联。一个项目可以直接关联多个项目，关联双向生效。重复建立同一条关联时，关联列表只有一条。两台电脑连接同一汇总端后，使用汇总端保存的关联。
  20 - 本机同步项目归属后，汇总端可以识别检索请求中的当前项目，并区分不同电脑上传的同名项目。功能上线前已上传的历史在设备补齐对应的项目归属后，也能出现在项目检索中。
  21 
  22 ### 搜索与读取
  23 
  24 - 在 CLI 或 MCP 发起汇总端项目检索时，结果标明由汇总端执行以及实际检索的项目。按项目 A 检索时，候选范围为 A 及其在汇总端直接关联的项目。例如 A 关联 B、C，B 另关联 D，从 A 检索纳入 A、B、C。解除 A 与 C 的关联后，从 A 检索的范围为 A、B。
  25 - 全局汇总检索涵盖两类来源中可供检索的对话。命中项标明来源、所属项目、原始会话标识和消息位置，并可通过现有读取入口打开该条消息的原文。
  26 - 汇总端不可用时，CLI 和 MCP 沿用现有回退行为，搜索本机所有项目，并返回本机来源和回退原因。显式选择本机检索时按本机档案和本机项目关系执行。
  27 
  28 ## 边界与约束
  29 
  30 - 访问沿用汇总端现有的单用户模式。汇总端使用只读凭据拉取 VibeInsight，对话保存于汇总档案。
  31 - 首版的增量依据是 VibeInsight 新写入的对话事件。若 VibeInsight 原地改写历史消息，且未写入新增事件，首版不负责发现该改写或刷新汇总档案中的对应消息。已归档的历史仍可按原内容检索和读取。
  32 - 项目关联影响项目检索范围。解除关联后，对话仍归属原项目，并可在相应的项目范围或全局范围中找到。
  33 - 项目身份以可持续标识为准。同名项目可分别配置关联。尚缺项目归属的历史记录可通过全局检索找到，待设备补齐项目归属后进入相应的项目范围。
  34 - 旧客户端发出的无项目范围请求沿用全局检索行为。
  35 
  36 ## 设计决策
  37 
  38 - **凭据保存在汇总端。** 沿用汇总端现有的独立凭据文件方式。连接地址、同步周期和启用状态保存在配置中，秘密值写入汇总服务状态目录内的专用凭据文件，由操作系统文件权限限制访问。汇总服务以自己的运行账号读取该文件，命令输出、日志和对话数据库不保存凭据原值。
  39 - **同步进度保存在汇总数据库。** 每个 VibeInsight 来源持久记录已成功归档的上游位置。一次同步先确定本轮上界，再分批按新增事件识别新会话和已有会话的新增轮次。归档结果和对应的进度一起提交。重启时读取已提交的位置继续，失败的批次会重新处理。更换同一来源的凭据沿用该来源的进度。
  40 - **PostgreSQL 事件流的续跑依据。** 可沿用 Living KB 的服务器入库时间 `created_at` 和事件 `id` 作为组合位置。同一时间的多个事件通过 `id` 区分。每轮回看最近一段入库记录，覆盖常见的延迟提交。重复读取时按来源会话和消息标识去重。
  41 
  42 ## 验收条件
  43 
  44 1. **自动拉取全部可读取项目。** 配置一个可读取两个项目的 VibeInsight 连接并启用同步。两项目的历史均可从 SMM 搜到并读回原文。随后让该连接可以读取第三个项目，该项目早于已保存同步进度的历史也会自动导入。查看配置和状态，确认看不到凭据原值。
  45 2. **凭据持久和旧会话续写。** 配置并成功同步一段有 3 轮的会话后停止汇总端。在停机期间向该会话追加 2 轮，并创建另一段新会话。重启服务，无需再次输入凭据即可自动同步。原会话仍使用同一个汇总会话标识，按来源顺序读回全部 5 轮，两轮新增内容均可检索。新会话可独立搜索。再次同步后，原会话仍为 5 轮。尝试用无效凭据替换时，原配置仍可继续使用。
  46 3. **跨设备和跨来源关联。** 电脑甲上传 A，电脑乙上传 B，VibeInsight 提供 C、D。建立 A 与 B、A 与 C、B 与 D 的关联。每个项目都包含同一关键词及独有证据。电脑甲按 A 发起汇总检索，范围为 A、B、C。电脑乙按 B 检索，范围为 B、A、D。解除 A 与 C 的关联后，按 A 只覆盖 A、B，全局仍能找到 C。
  47 4. **同名、改名和已有历史。** 两台电脑上传同名项目，只选择其中一个建立关联。按关联起点检索能区分两套对话。目标项目改名后关联有效。升级前已上传的对话在设备补齐项目归属后可按项目找到，在此之前可通过全局检索找到。
  48 5. **检索入口与引用可追溯。** 从 CLI 和 MCP 分别发起同一项目的汇总端检索，核对实际项目范围一致。对设备上传记录和 VibeInsight 记录各核对一条命中，确认来源、所属项目、会话标识和消息位置齐备，按命中引用读回的原文一致。
  49 6. **回退和兼容。** 停止汇总端后，CLI 和 MCP 的项目检索按现有方式搜索本机所有项目，响应标明本机来源和回退原因。旧客户端的全局请求仍能搜索汇总档案。
  50 7. **失败批次与重读去重。** 让一批记录在归档完成前失败，查看错误状态并确认之前成功归档的对话仍可读取。恢复后，失败批次中的记录最终都可检索，包括回看时间内延迟提交的事件。重复执行同步后，每个来源会话仍只有一个有效版本。
````

## changes/003-search-vibeinsight-conversations/plan.md

````text
   1 # 实施计划：汇总端同步 VibeInsight 对话及关联项目检索
   2 
   3 依据 [PR #19](https://github.com/yangbobo2021/smm-local/pull/19) 合并的[规格](spec.md)。
   4 
   5 ## 修改位置
   6 
   7 | 模块 | 拟修改内容 |
   8 | --- | --- |
   9 | `src/smm_hub/hub.py`、`src/smm_hub/projects.py` 和共享档案查询 | 增量扩展汇总数据库，保存项目身份、会话归属、项目关联、VibeInsight 来源和同步进度。复用现有对话索引及原文读取，加上项目范围过滤和来源信息。 |
  10 | `src/smm_hub/hub_admin.py`、`src/smm_hub/vibeinsight.py`、`src/smm_hub/vibeinsight_settings.py` | 提供来源配置、同步状态和项目管理命令。复用服务状态目录和凭据文件机制。随 Hub 进程启动、停止同步任务。将读取上游的代码与同步、归档逻辑分开，以便在测试里替换上游读取。 |
  11 | `src/smm_local/federation.py`、`src/smm_local/core.py` | 上传设备上的项目身份及会话归属，把已有历史的归属补传到新 Hub，在线检索时传递当前项目。CLI 复用现有入口。更新 MCP 工具说明及 Skill 指引。 |
  12 | `tests/test_federation.py`、拟新增的 `tests/test_vibeinsight_sync.py` | 用固定事件夹具和可控制的来源读取实现覆盖初次拉取、重启、失败恢复和双客户端行为。真实 PostgreSQL 查询验证单独运行。 |
  13 | `TRIAL_GUIDE.md` | 记录 Hub CLI 配置、项目管理、实际使用的上游连接依赖、支持的增量类型和断线时的检索行为。 |
  14 
  15 ## 实施顺序
  16 
  17 1. **先建立基线和测试夹具。** 固定一个合并规格时的 Hub 和客户端版本。用该版本生成一份已有设备、对话、原文引用和上传进度的汇总档案副本。准备两套隔离客户端和贴近 VibeInsight 事件字段的合成数据，能控制项目何时可见、事件何时追加以及哪一批失败。为各项目准备共同关键词和各自唯一的文本。
  18 2. **扩展汇总存储和兼容协议。** 在副本上验证可重复执行的数据库迁移。设备项目以设备和稳定的本地项目标识识别，VibeInsight 项目以来源和上游项目标识识别。用独立的归属关系保存同一段去重会话在不同设备上的项目归属。保留已有会话与消息标识，以及旧客户端上传和全局搜索所需的协议字段。通过 Hub 能力标记让新客户端判断何时可以发送项目元数据和项目范围。
  19 3. **补齐设备归属并接通关联检索。** 给项目元数据和会话归属使用独立的补传进度，覆盖升级前已上传的对话，以及没有新增消息的项目改名。增加 Hub CLI 的项目列表、关联查询、建立和解除操作。将双向关联存为一条关系。Hub 按消息的来源项目建立检索索引，先按当前项目及直接关联过滤候选，再排序和截取结果。去重后的会话可以保留多套项目归属，消息命中和引用以各自来源为准。CLI 和 MCP 用返回的汇总会话与消息引用读取原文。沿用当前的断线回退行为。
  20 4. **接通 VibeInsight 配置和首次拉取。** 复用 Living KB 对 `fact_events` 的只读查询口径。运行时连接使用 `psql`，复用既有查询口径并保持两个 Python 包的依赖独立。把连接、查询执行和结果解析集中在读取上游的代码里，便于独立验证或替换。staging 验证中，按项目分页重复扫描历史导致上游查询超时。改用固定上界的只读 PostgreSQL COPY 流，Hub 仍按项目分批提交。长流按输出空闲时间检测卡住，停服可中断读取。本轮发现的项目固定，随后新可见的项目在下一轮补齐历史。配置来源时验证服务账号可连接并读取源数据，再发布新配置和受限凭据文件。验证失败时保留上一次有效配置。启用后自动发现连接可读取的项目，按有界批次拉取历史，并保存项目归属和来源位置。仓库标识以 VibeInsight 提供的 Git 仓库身份为准，同一会话的各轮可归属不同仓库。
  21 5. **实现增量续跑并接入 Hub 生命周期。** 每轮固定上游位置上界。用 `created_at + id` 比较位置，在上次成功位置附近回查近期事件。按新事件识别新会话和已有会话新增的轮次，按来源身份去重并维持原有归档标识。将同一批的对话、索引和对应进度一起提交，恢复时重试未提交的批次。为新发现的项目安排独立的历史补拉，避免被已有来源进度跳过。绑定 Hub 启停，保存最近成功时间和脱敏后的错误，通过测试确认同步失败期间已有对话仍可检索。
  22 6. **验证常规回归和发行包入口。** 用可控来源逐项执行验收，检查两个 wheel 的独立安装及启动。初次接通上游时单独验证 PostgreSQL 查询。更新使用指南，记录验证结果。
  23 
  24 ## 验证方法与通过条件
  25 
  26 常规 `pytest` 和未来默认 CI 用固定夹具替换 VibeInsight 的读取端。Hub 启动、状态和凭据落盘、SQLite 归档与进度提交、CLI/MCP 检索及读取使用实际实现。测试用新进程和同一状态目录验证重启，用可控事件批次和故障验证恢复。默认回归所需的服务和数据都由测试在本机创建。
  27 
  28 | SPEC 验收项 | 怎么验证 | 通过条件 |
  29 | --- | --- | --- |
  30 | 1. 自动拉取全部可读取项目 | 在来源夹具里准备三个项目的历史，配置为起初仅返回两个项目。从 Hub 管理 CLI 配置并启用，等两个项目同步后，再让夹具返回第三个项目。第三个项目的测试事件全部早于已保存的位置。用各项目的唯一文本搜索并读取命中原文，同时核对配置显示、状态输出和日志。 | 开始时两个项目的历史都可查，新可见项目不经单独配置即自动补齐较早历史。测试密码原值未出现在输出、日志或对话数据库中。 |
  31 | 2. 凭据持久与旧会话续写 | 导入三轮后记录汇总会话标识、消息顺序及同步位置，停止 Hub 进程。停机期间追加两轮并写入一段新会话。使用同一状态目录启动新进程，不传数据库密码。同步完成后再运行一轮，并尝试用错误密码替换凭据。 | 启动后自动续跑。原会话标识相同，原有三轮和新增两轮按顺序读回，两轮新内容和新会话均可搜索。重复同步仍只有五轮。错误凭据被拒绝，原配置仍能同步。 |
  32 | 3. 跨设备和跨来源关联 | 客户端甲上传 A，客户端乙上传 B，Hub 从来源夹具拉取 VibeInsight 项目 C 和 D。经 Hub CLI 建立 A–B、A–C、B–D，再重复建立一次 A–B。分别从两套客户端按项目搜索，解除 A–C 后重查 A 及全局。 | A 的有效范围及命中仅为 A、B、C，B 的为 B、A、D。关联列表中 A–B 只有一条。解除后 A 的范围是 A、B，全局仍可查到 C 的原文。 |
  33 | 4. 同名、改名和已有历史 | 用第 1 步的旧版档案升级。两台设备的同名项目各含独有文本，只关联其中一个。让设备在没有新增对话时完成项目归属补传，并改名后重查。升级和补传前后都读取同一条旧引用。 | 同名项目可区分，按关联起点只命中选中的项目。改名后关联仍有效。缺少归属的历史在补传前可通过全局找到，补传后按项目可查。旧引用可读，原会话和设备来源未重复。 |
  34 | 5. 检索入口与引用可追溯 | 用 CLI 和真实 stdio MCP 客户端执行同一项目查询，分别选一条设备上传消息和 VibeInsight 消息，使用每条结果返回的引用进行精确原文读取，与源夹具逐条比对。 | 两个入口都标明汇总端和相同的有效项目集合。每条结果包含正确的来源、项目、原始会话标识及消息位置，读取的角色、正文及顺序与来源一致。 |
  35 | 6. 回退和兼容 | 先用旧版客户端向新版 Hub 上传并执行全局搜索和读取。再停止新版 Hub，在本机两个不同项目放入共同关键词，分别用 CLI、MCP 按一个项目搜索。 | 旧客户端的上传、全局搜索和读取可用。断线查询沿用本机全局回退，两个本机项目都可命中，响应包含本机来源及回退原因。 |
  36 | 7. 失败批次与重读去重 | 在写入某一批时注入可恢复故障，并读取该批前已保存的同步位置及已有对话。恢复后让 Hub 自动重试。再写入一条在本轮回查范围内、入库位置早于当前进度的延迟事件，执行重读。 | 失败批次未造成部分提交或越过尚未归档的记录，状态可见且已有对话可读。恢复后失败批次和延迟事件都能搜到。重复拉取后，同一来源会话和消息各保留一份。 |
  37 
  38 另做一条范围回归。在夹具里原地改写一条已归档的历史消息，保持事件 ID 和入库位置，随后向同一会话追加一轮。验证新增轮次可查，旧消息仍读回原先归档的内容。
  39 
  40 ### PostgreSQL 查询验证（单独运行）
  41 
  42 在隔离 PostgreSQL 中用少量合成事件执行实际 COPY 流和分页对照查询，核对只读账号能查询、项目和会话标识正确、时间与事件 ID 边界正确分页，以及追加轮次和窗口内延迟事件能够被选中。初次接通上游和以后修改查询或连接方式时执行，可由开发者本机按需运行。默认 CI 无需安装 `psql`、启动 PostgreSQL 或连接 VibeInsight。后续如需自动化，可独立配置带临时 PostgreSQL 的 CI 任务。
  43 
  44 staging 首次流式拉取达到单次查询时间上限后，从已提交的项目进度续跑。将各项目的回看窗口下界传给上游 COPY 查询，使已推进的项目无需重新传输窗口前的历史，尚无进度的项目继续读取可见历史。验证续跑能保留已归档内容并完成整轮。
  45 
  46 ### 回归与构建命令
  47 
  48 先运行 `pytest -q tests/test_federation.py tests/test_vibeinsight_sync.py tests/test_cli_help.py tests/test_service_startup.py`，再运行 `pytest -q`。运行 `python3 scripts/build_packages.py`，将两个 wheel 分别装到干净环境，验证 Hub 能读取配置并运行同步，本机端能通过 CLI 和 MCP 查询。用发行版 Hub 执行首次 PostgreSQL 查询验证，检查连接依赖和服务账号环境。
  49 
  50 实现 PR 按上述 7 项逐条记录通过、失败或未验证，并附脱敏的 CLI/MCP 响应、同步进度对比、测试和构建结果。交维护者审查前，在干净上下文按仓库的 [PR Review Prompt](../_templates/pr-review.prompt.md) 审查实现与验收证据，将结论写入实现 PR。
````

## TRIAL_GUIDE.md

````text
   1 # SMM Local 同事试用指南
   2 
   3 SMM 在本机保存 Codex 与 Claude Code 的可见对话文本，提供项目范围 BM25 搜索。首次导入后，源 Agent 删除会话不会删除 SMM 档案。SMM 没有云端服务；Agent 读取的片段仍可能进入该 Agent 所配置的模型服务，请遵守公司的数据使用规则。
   4 
   5 ## 1. 安装
   6 
   7 按 [README 的快速开始](README.md#单台电脑快速开始)安装 `smm-search`。首次使用需要网络和 Agent 的本机执行权限。Skill 会使用已有的 Python，或自动准备用户级 Python。
   8 
   9 ### 升级本机端
  10 
  11 通过搜索 Skill 安装过旧版时，更新整个 `smm-search` Skill 文件夹，并在 `~/.local/share/smm-local/install.json` 中找到 `package_environment`。用该环境的 Python 执行下面三条命令。macOS 和 Linux 的解释器位于环境下的 `bin/python`，Windows 位于 `Scripts/python.exe`。
  12 
  13 ```text
  14 <安装环境的 Python> -m smm_local.cli stop-on-demand
  15 <安装环境的 Python> -m pip install --upgrade smm-local==0.3.0
  16 <安装环境的 Python> -m smm_local.installation install
  17 ```
  18 
  19 升级沿用安装清单中的档案路径。升级后新开 Agent 会话，查看 SMM 同步状态。从源码安装的用户可从新版本源码重新运行 `scripts/install.py`。
  20 
  21 ## 2. 在 Agent 中管理同步
  22 
  23 安装完成后，在新的 Codex 或 Claude Code 会话中直接说：
  24 
  25 - 「查看 SMM 同步状态」看来源计数、上次同步和导入错误。
  26 - 「打开 SMM 状态页」打开本机页面。
  27 - 「现在同步一次我的对话」立即导入；初次同步可能需要一段时间。
  28 - 「暂停自动同步」或「恢复自动同步」管理后台导入。暂停后仍可查已有档案、查看状态页或明确同步一次；服务或电脑重启后暂停设置仍有效。
  29 
  30 如果服务还没运行，Agent 会在需要时启动它。macOS 默认也会在登录后启动服务。
  31 
  32 Codex 默认读取 `~/.codex/sessions`，Claude Code 默认读取 `~/.claude/projects`。若历史放在别处，到 Web「配置」设置实际目录，再点「立即同步」。同一个系统账户下，两个 Agent 共用一个同步服务和一个档案，默认位于 `~/.local/share/smm-local/smm.sqlite3`。在任一 Agent 中暂停或恢复，另一边会看到同一个状态。
  33 
  34 ## 3. 实际提问
  35 
  36 在新的 Codex 或 Claude Code 会话中问一个**必须依靠旧对话**才能回答的问题，例如：“我以前对某项目的上线回滚提出过什么要求？请查原始对话并引用来源会话和消息位置。”Agent 应调用 `smm-local` 的检索及读取工具，答案应能在 Web「检索测试」中复核。首次尝试可明确说“请使用 SMM 搜索过去对话”，再试不点名工具的自然提问。
  37 
  38 项目检索默认只包含当前项目及直接关联项目。跨项目提问时，让 Agent 使用全局范围；也可以在 Web「项目」中建立关联。检索结果保留来源、时间和命中位置；每条命中消息默认只预览前 600 字，较长消息会标明省略。需要依据后半段内容作答时，让 Agent 调用 `read_conversation` 读取该轮完整原文。命中一段对话不等于其中每句都是事实，须读原文核对。
  39 
  40 ## 4. 遇到问题
  41 
  42 - 两个来源都显示不可用：让 Agent 打开状态页，在「配置」中检查会话目录。
  43 - 首次安装依赖下载失败：让 Agent 查看具体错误，恢复网络后在会话里重试原请求。
  44 - Claude Code 报 401 或未登录：先检查 Claude Code 自己的模型登录。
  45 - Agent 找不到 SMM：检查 Skill 文件夹是否完整放在所用 Agent 的技能目录，随后新开会话。
  46 - 服务启动失败：让 Agent 检查返回的日志路径并说明实际原因。
  47 - 搜不到预期对话：先确认导入计数和项目范围，再用显著的项目名、人物名或事件词重试。
  48 - Agent 给出没有原文支持的回答：要求它提供来源会话和位置，在 Web 读取原文；请把问题、实际结果与期望来源反馈给试用负责人。
  49 
  50 ## 5. 结束试用
  51 
  52 先从各 Agent 的 Skill 目录移除自己放入的 `smm-search` 文件夹。若也要卸载本机组件，可请 Agent 读取 `~/.local/share/smm-local/install.json`，用其中 `package_environment` 指向的 Python 运行 `-m smm_local.installation uninstall`。从源码安装的旧版仍可从 `project_root` 运行 `scripts/uninstall.py`，以停用服务并移除 MCP 注册。卸载会保留数据库。
  53 
  54 请在试用反馈中记录：安装是否独立完成、一次自己的历史问题是否找对原文、一次跨 Agent 搜索是否找对、哪一步费时或困惑。不要把私人对话原文发到公共 issue。
  55 
  56 ## 多台电脑共用汇总档案
  57 
  58 汇总端通过下面的包管理流程部署，也可在自行管理进程时运行 `smm-hub serve-hub`。汇总端使用独立数据库，远程连接使用 HTTPS。连接凭证允许上传和搜索汇总档案，应发给有权访问这些对话的使用者。
  59 
  60 在每台电脑上安装新版 Skill。将管理员提供的凭证文件存到该账户的 `~/.local/share/smm-local/hub-token`，或在配置时告诉 Agent 文件路径。然后说「把这台电脑叫出差笔记本，汇总地址是 https://smm.example.net:8770」。汇总电脑若也要上传自己的本机对话，同样配置一次。
  61 
  62 连不上汇总电脑时，Skill 会说明当前只搜本机，范围包含本机已导入的所有 Agent。网络恢复后，后台会补传未确认的记录，搜索重新覆盖汇总档案。引用会注明来源电脑、Agent、原始会话 ID 和消息位置。
  63 
  64 ### 通过包管理器部署汇总端
  65 
  66 管理员通过 uv 从 PyPI 安装独立的 `smm-hub` 包。
  67 
  68 ```sh
  69 uv tool install smm-hub==0.3.0
  70 smm-hub hub setup
  71 ```
  72 
  73 向导询问客户端可访问的 HTTPS 地址、证书和私钥，例如 `https://hub.example.net:8770`。在 Linux 用户服务下使用 1024 以上的监听端口。它会复制 TLS 文件、生成连接凭证、准备数据库、注册系统服务并检查 HTTPS。私有 CA 可通过 `--ca-file` 提供，并应配置到客户端 Python 的信任链。指定全部参数可无交互部署。Windows 需要以管理员身份运行终端，并将 uv 工具环境和基础 Python 安装在 LocalService 可读取和执行的目录（例如管理员管理的 ProgramData 下），macOS 在注册系统级 launchd 服务时会请求 sudo，Linux 使用可在启动时运行的 systemd 用户服务。
  74 
  75 ```sh
  76 smm-hub hub status
  77 smm-hub hub disable
  78 smm-hub hub enable
  79 smm-hub hub upgrade
  80 ```
  81 
  82 升级命令调用 uv 并保留地址、凭证和数据库，升级前保存 SQLite 备份。保留包索引中的旧版本，以便升级失败时恢复。启用中的服务在升级后会重新启动并检查 HTTPS。使用自定义 uv 安装环境时，从同一个账户和环境运行升级。使用 `--version` 可显式切换包索引中的发行版本。Windows 向导为监听端口配置仅限本地子网的入站防火墙规则。
  83 
  84 已通过旧版 `smm-local` 部署汇总端时，先记下原来的数据目录和启停状态，安装 `smm-hub`，然后用旧命令停用旧服务。在原数据目录运行 `smm-hub hub --state-dir <原数据目录> enable` 接管原服务。原服务需要保持停用时，直接保留停用状态，日后再用新命令启用。两套命令使用同一份汇总端状态文件和数据库。
  85 
  86 ### 从 VibeInsight 同步对话
  87 
  88 先用上一节的 `smm-hub hub setup` 配置汇总服务。在运行汇总服务的电脑上安装 PostgreSQL 客户端 `psql`，让运行汇总服务的系统账户可执行它。用 VibeInsight 数据库的只读账户配置连接。管理命令会验证读取权限，并提示输入密码。若服务环境找不到客户端，可用 `--psql` 指定绝对路径。
  89 
  90 ```sh
  91 smm-hub hub vibeinsight configure --host db.example.net --port 5432 --database vibeinsight --user reader
  92 smm-hub hub vibeinsight status
  93 ```
  94 
  95 如果使用自定义状态目录，在 `hub` 后加 `--state-dir <状态目录>`。同步周期默认 300 秒，可用 `--interval` 调整。启用同步后，汇总服务拉取连接可读的全部项目，随后同步新会话及旧会话追加的轮次。服务重启会读取已保存的凭据和进度继续。状态命令显示最近成功时间和失败原因。源端原地改写历史消息而未产生新事件时，汇总档案保留已导入的原内容。
  96 
  97 ### 管理汇总端的项目关联
  98 
  99 本机客户端至少完成一次与汇总端的同步后，运行 `smm-hub hub project list` 查看项目 ID、来源和设备名称。用以下命令管理关系，示例中的 `1` 和 `2` 换成汇总端给出的项目 ID。
 100 
 101 ```sh
 102 smm-hub hub project links
 103 smm-hub hub project link 1 2
 104 smm-hub hub project unlink 1 2
 105 ```
 106 
 107 在 Agent 中要求按当前项目搜索时，CLI 和 MCP 会查询汇总端保存的当前项目及直接关联项目。关系双向生效。命中 VibeInsight 对话时，可以用同一个读取入口取得原文和源事件位置。需扩大范围时，明确要求搜索所有项目。汇总端断开时，CLI 和 MCP 回退到本机所有项目，并返回回退原因。
````

## skills/smm-search/SKILL.md

````text
   1 ---
   2 name: smm-search
   3 description: Search archived Agent conversations, manage SMM sync, or configure a multi-computer archive hub. Use for prior project decisions, fixes and preferences, or to check, sync, pause or resume the archive. Do not use for information only in the current chat.
   4 ---
   5 
   6 # SMM conversation archive
   7 
   8 Use the `smm-local` MCP tools when `configure_hub` is available. If this session has an older MCP or no MCP, use the Skill's first-use launcher for the entire request, including search and evidence reads. Use the scripts next to this `SKILL.md`, with paths resolved relative to this Skill directory:
   9 
  10 - macOS and Linux: `sh "<skill-directory>/scripts/first_use.sh" <arguments>`
  11 - Windows: invoke `"<skill-directory>\scripts\first_use.ps1"` with `&` in PowerShell, followed by the arguments.
  12 
  13 The launcher installs the supported SMM Local package from the Python package index on first use or finds the existing installation for this OS account. It reports stages and download progress, and handles interrupted downloads and installation retries. Tell the user that first use is installing and relay progress when the install is still running. If the shell moves the command to a background task, keep following that same task and its output until it finishes. Do not launch another copy or treat a still-running command as a failure. Then continue the original request through the launcher even when the newly registered MCP tools are not visible yet. Do not ask the user to install Python, run an SMM command, or restart the Agent to complete the first request. If the launcher ultimately fails, explain the specific error.
  14 
  15 ## Maintain conversation sync
  16 
  17 Call `manage_sync` with the action that matches the user's request:
  18 
  19 | Request | Action | What to report |
  20 | --- | --- | --- |
  21 | 查看同步状态 / check sync status | `status` | Service and pause state, source availability and counts, last completed sync and errors. Use `sync.last_result.finished_at` for the last completed sync if available. |
  22 | 打开状态页 / open the status page | `open` | Confirm if `opened` is true. Otherwise give the returned `url` as a clickable link. |
  23 | 立即同步 / sync now | `sync` | Report new conversations and messages and any errors in `result`. If `running` is true, say it is still running and use `status` to check progress. |
  24 | 暂停同步 / pause automatic sync | `pause` | Confirm the saved pause. An in-flight sync can finish. Explicit one-off sync and searches are still available. |
  25 | 恢复同步 / resume automatic sync | `resume` | Confirm the change and whether sync is in progress. |
  26 
  27 For a specific source, find its ID in status and pass `source` with status or sync. To enable or disable it, call `set_source_enabled` with the ID, or pass `source enable|disable <ID>` to the launcher. The source state and global pause are independent. To add a new source, use `smm-source-adapter`.
  28 
  29 For maintenance requests, the management tool result is sufficient. Zero archived conversations can be a valid status; report what SMM sees and ask before investigating unrelated directories or configuration.
  30 
  31 If MCP or this tool is unavailable, pass `maintenance <action> [--source ID]` to the launcher. Use an argument vector or quote paths for the current shell.
  32 
  33 The local tool starts the service when needed and reuses it if running. Only use `resume` when the user asks to resume automatic sync. Treat a failed tool response as a failure, not as confirmation.
  34 
  35 ## Search archived conversations
  36 
  37 Before searching, call `manage_sync(action="status")` (or `maintenance status` through the launcher) to ensure the local service is available. If startup fails, still search existing archives and mention that they may be out of date. If automatic sync is enabled and the first import has not finished or the user needs very recent history, use `sync` and check its result before relying on the search. If the import is still running, report that results may be incomplete.
  38 
  39 1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. When the search runs on a configured SMM Hub, project links come from the Hub and may include other devices or VibeInsight. Use the returned effective scope and fallback reason when reporting which archive was searched. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
  40 2. Search with a few distinctive terms from the user's question. Adjust terms and search again if the results contain plausible leads but not the needed evidence. Do not infer that no information exists from a project-scoped miss alone.
  41 3. Examine the source, project, time, and matched message positions. Search previews may be abbreviated; use `read_conversation` with the conversation ID and relevant positions to inspect complete messages before answering. Distinguish the archived user's statement from an assistant's proposal or speculation.
  42 4. Cite the computer name, Agent type, original source conversation ID and original message position. For a hub result, use that message's `origins` and `source_position`. Pass the exact returned `hub_id` to `read_conversation` or launcher `read --hub-id`. Read the entire conversation, or pass the returned `hub_message_id` (launcher `--hub-message-id`) for an exact message. If reading remote evidence fails, search again and report the actual scope; never use the same numeric ID against another archive.
  43 
  44 When the user requests this computer or a local plugin source, pass `local=true` to MCP or `--local` to the launcher.
  45 
  46 If `archive_scope` is `hub`, search covered all devices in the hub. Local project IDs do not filter the hub. If `archive_scope` is `local` and `fallback_reason` is present, tell the user that the hub was unavailable and this search covered only this computer. An empty hub result is not a connection failure.
  47 
  48 MCP tools: `list_projects`, `resolve_project`, `search_conversations`, `read_conversation`.
  49 
  50 Launcher arguments: `projects`, `resolve-project --cwd "$PWD"`, `search "terms" --scope project --project-id ID`, `read ID --start POSITION --end POSITION`.
  51 
  52 The MCP/CLI adapter excludes the current conversation by default when `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or `CLAUDE_SESSION_ID` is available. Set `include_current=true` only when earlier content from this same conversation is needed. If the Agent does not expose its session ID, pass `current_session_id` explicitly when known.
  53 
  54 ## Configure the aggregation computer
  55 
  56 When the user asks to link this computer to an aggregation computer, take the address and this computer's name from their request. Call `configure_hub(address, device_name)`, or pass `configure-hub <address> <device_name>` to the launcher. If the user supplies a credential file path, include `token_file` or `--token-file <path>`. If the result says `needs_token`, ask for the path to the credential file provided by the hub administrator. Do not read its contents into the conversation.
  57 
  58 Report whether the configuration was saved and the hub is reachable. When reachable, SMM starts the first upload if automatic sync is enabled. The background service retries pending records after reconnecting. A saved but offline hub still allows local search.
````

## docs/index.md

````text
   1 # SMM 使用文档
   2 
   3 这是 SMM 面向安装者、汇总端维护者和日常使用者的使用文档首页。
   4 
   5 - 单台电脑安装及日常使用见[快速开始](../README.md#单台电脑快速开始)。
   6 - 多台电脑共用档案见[部署汇总端](../TRIAL_GUIDE.md#通过包管理器部署汇总端)。
   7 - 汇总端支持自动同步 VibeInsight 的历史对话、新会话与旧会话追加的轮次。维护者按[从 VibeInsight 同步对话](../TRIAL_GUIDE.md#从-vibeinsight-同步对话)准备只读数据库账户、安装 PostgreSQL 客户端、配置连接并查看状态。
   8 - 维护者可把不同电脑上传的项目和 VibeInsight 项目建立双向直接关联。按[管理汇总端的项目关联](../TRIAL_GUIDE.md#管理汇总端的项目关联)设置后，用户继续在 Agent 中按当前项目搜索，并读取命中原文。
````

## PR diff

````diff
diff --git a/TRIAL_GUIDE.md b/TRIAL_GUIDE.md
index c7286c4..e42c262 100644
--- a/TRIAL_GUIDE.md
+++ b/TRIAL_GUIDE.md
@@ -82,3 +82,26 @@ smm-hub hub upgrade
 升级命令调用 uv 并保留地址、凭证和数据库，升级前保存 SQLite 备份。保留包索引中的旧版本，以便升级失败时恢复。启用中的服务在升级后会重新启动并检查 HTTPS。使用自定义 uv 安装环境时，从同一个账户和环境运行升级。使用 `--version` 可显式切换包索引中的发行版本。Windows 向导为监听端口配置仅限本地子网的入站防火墙规则。
 
 已通过旧版 `smm-local` 部署汇总端时，先记下原来的数据目录和启停状态，安装 `smm-hub`，然后用旧命令停用旧服务。在原数据目录运行 `smm-hub hub --state-dir <原数据目录> enable` 接管原服务。原服务需要保持停用时，直接保留停用状态，日后再用新命令启用。两套命令使用同一份汇总端状态文件和数据库。
+
+### 从 VibeInsight 同步对话
+
+先用上一节的 `smm-hub hub setup` 配置汇总服务。在运行汇总服务的电脑上安装 PostgreSQL 客户端 `psql`，让运行汇总服务的系统账户可执行它。用 VibeInsight 数据库的只读账户配置连接。管理命令会验证读取权限，并提示输入密码。若服务环境找不到客户端，可用 `--psql` 指定绝对路径。
+
+```sh
+smm-hub hub vibeinsight configure --host db.example.net --port 5432 --database vibeinsight --user reader
+smm-hub hub vibeinsight status
+```
+
+如果使用自定义状态目录，在 `hub` 后加 `--state-dir <状态目录>`。同步周期默认 300 秒，可用 `--interval` 调整。启用同步后，汇总服务拉取连接可读的全部项目，随后同步新会话及旧会话追加的轮次。服务重启会读取已保存的凭据和进度继续。状态命令显示最近成功时间和失败原因。源端原地改写历史消息而未产生新事件时，汇总档案保留已导入的原内容。
+
+### 管理汇总端的项目关联
+
+本机客户端至少完成一次与汇总端的同步后，运行 `smm-hub hub project list` 查看项目 ID、来源和设备名称。用以下命令管理关系，示例中的 `1` 和 `2` 换成汇总端给出的项目 ID。
+
+```sh
+smm-hub hub project links
+smm-hub hub project link 1 2
+smm-hub hub project unlink 1 2
+```
+
+在 Agent 中要求按当前项目搜索时，CLI 和 MCP 会查询汇总端保存的当前项目及直接关联项目。关系双向生效。命中 VibeInsight 对话时，可以用同一个读取入口取得原文和源事件位置。需扩大范围时，明确要求搜索所有项目。汇总端断开时，CLI 和 MCP 回退到本机所有项目，并返回回退原因。
diff --git a/changes/003-search-vibeinsight-conversations/plan.md b/changes/003-search-vibeinsight-conversations/plan.md
index 419750f..34c7926 100644
--- a/changes/003-search-vibeinsight-conversations/plan.md
+++ b/changes/003-search-vibeinsight-conversations/plan.md
@@ -6,9 +6,9 @@
 
 | 模块 | 拟修改内容 |
 | --- | --- |
-| `src/smm_hub/hub.py` 与 Hub 存储代码 | 增量扩展汇总数据库，保存项目身份、会话归属、项目关联、VibeInsight 来源和同步进度。复用现有对话索引及原文读取，加上项目范围过滤和来源信息。 |
-| `src/smm_hub/hub_admin.py`、`src/smm_hub/cli.py` 和新增的 Hub 同步代码 | 提供来源配置、同步状态和项目管理命令。复用服务状态目录和凭据文件机制。随 Hub 进程启动、停止同步任务。将读取上游的代码与同步、归档逻辑分开，以便在测试里替换上游读取。 |
-| `src/smm_local/federation.py`、`src/smm_local/core.py` | 上传设备上的项目身份及会话归属，把已有历史的归属补传到新 Hub，在线检索时传递当前项目。CLI 和 MCP 通过现有公共入口消费结果，更新相应帮助、工具说明及 Skill 指引。 |
+| `src/smm_hub/hub.py`、`src/smm_hub/projects.py` 和共享档案查询 | 增量扩展汇总数据库，保存项目身份、会话归属、项目关联、VibeInsight 来源和同步进度。复用现有对话索引及原文读取，加上项目范围过滤和来源信息。 |
+| `src/smm_hub/hub_admin.py`、`src/smm_hub/vibeinsight.py`、`src/smm_hub/vibeinsight_settings.py` | 提供来源配置、同步状态和项目管理命令。复用服务状态目录和凭据文件机制。随 Hub 进程启动、停止同步任务。将读取上游的代码与同步、归档逻辑分开，以便在测试里替换上游读取。 |
+| `src/smm_local/federation.py`、`src/smm_local/core.py` | 上传设备上的项目身份及会话归属，把已有历史的归属补传到新 Hub，在线检索时传递当前项目。CLI 复用现有入口。更新 MCP 工具说明及 Skill 指引。 |
 | `tests/test_federation.py`、拟新增的 `tests/test_vibeinsight_sync.py` | 用固定事件夹具和可控制的来源读取实现覆盖初次拉取、重启、失败恢复和双客户端行为。真实 PostgreSQL 查询验证单独运行。 |
 | `TRIAL_GUIDE.md` | 记录 Hub CLI 配置、项目管理、实际使用的上游连接依赖、支持的增量类型和断线时的检索行为。 |
 
@@ -16,8 +16,8 @@
 
 1. **先建立基线和测试夹具。** 固定一个合并规格时的 Hub 和客户端版本。用该版本生成一份已有设备、对话、原文引用和上传进度的汇总档案副本。准备两套隔离客户端和贴近 VibeInsight 事件字段的合成数据，能控制项目何时可见、事件何时追加以及哪一批失败。为各项目准备共同关键词和各自唯一的文本。
 2. **扩展汇总存储和兼容协议。** 在副本上验证可重复执行的数据库迁移。设备项目以设备和稳定的本地项目标识识别，VibeInsight 项目以来源和上游项目标识识别。用独立的归属关系保存同一段去重会话在不同设备上的项目归属。保留已有会话与消息标识，以及旧客户端上传和全局搜索所需的协议字段。通过 Hub 能力标记让新客户端判断何时可以发送项目元数据和项目范围。
-3. **补齐设备归属并接通关联检索。** 给项目元数据和会话归属使用独立的补传进度，覆盖升级前已上传的对话，以及没有新增消息的项目改名。增加 Hub CLI 的项目列表、关联查询、建立和解除操作。将双向关联存为一条关系。Hub 先按当前项目及直接关联过滤候选，再做查询排序和结果截取。CLI 和 MCP 用返回的汇总会话与消息引用读取原文。沿用当前的断线回退行为。
-4. **接通 VibeInsight 配置和首次拉取。** 复用 Living KB 对 `fact_events` 的只读查询口径。运行时连接暂建议用 `psql`，也可用仅由 Hub 安装的 Python PostgreSQL 驱动。把连接、查询执行和结果解析集中在读取上游的代码里，便于独立验证或替换。配置来源时验证服务账号可连接并读取源数据，再发布新配置和受限凭据文件。验证失败时保留上一次有效配置。启用后自动发现连接可读取的项目，按有界批次拉取历史，并保存项目归属和来源位置。
+3. **补齐设备归属并接通关联检索。** 给项目元数据和会话归属使用独立的补传进度，覆盖升级前已上传的对话，以及没有新增消息的项目改名。增加 Hub CLI 的项目列表、关联查询、建立和解除操作。将双向关联存为一条关系。Hub 按消息的来源项目建立检索索引，先按当前项目及直接关联过滤候选，再排序和截取结果。去重后的会话可以保留多套项目归属，消息命中和引用以各自来源为准。CLI 和 MCP 用返回的汇总会话与消息引用读取原文。沿用当前的断线回退行为。
+4. **接通 VibeInsight 配置和首次拉取。** 复用 Living KB 对 `fact_events` 的只读查询口径。运行时连接使用 `psql`，复用既有查询口径并保持两个 Python 包的依赖独立。把连接、查询执行和结果解析集中在读取上游的代码里，便于独立验证或替换。staging 验证中，按项目分页重复扫描历史导致上游查询超时。改用固定上界的只读 PostgreSQL COPY 流，Hub 仍按项目分批提交。长流按输出空闲时间检测卡住，停服可中断读取。本轮发现的项目固定，随后新可见的项目在下一轮补齐历史。配置来源时验证服务账号可连接并读取源数据，再发布新配置和受限凭据文件。验证失败时保留上一次有效配置。启用后自动发现连接可读取的项目，按有界批次拉取历史，并保存项目归属和来源位置。仓库标识以 VibeInsight 提供的 Git 仓库身份为准，同一会话的各轮可归属不同仓库。
 5. **实现增量续跑并接入 Hub 生命周期。** 每轮固定上游位置上界。用 `created_at + id` 比较位置，在上次成功位置附近回查近期事件。按新事件识别新会话和已有会话新增的轮次，按来源身份去重并维持原有归档标识。将同一批的对话、索引和对应进度一起提交，恢复时重试未提交的批次。为新发现的项目安排独立的历史补拉，避免被已有来源进度跳过。绑定 Hub 启停，保存最近成功时间和脱敏后的错误，通过测试确认同步失败期间已有对话仍可检索。
 6. **验证常规回归和发行包入口。** 用可控来源逐项执行验收，检查两个 wheel 的独立安装及启动。初次接通上游时单独验证 PostgreSQL 查询。更新使用指南，记录验证结果。
 
@@ -39,7 +39,9 @@
 
 ### PostgreSQL 查询验证（单独运行）
 
-在隔离 PostgreSQL 中用少量合成事件执行实际读取代码，核对只读账号能查询、项目和会话标识正确、时间与事件 ID 边界正确分页，以及追加轮次和窗口内延迟事件能够被选中。初次接通上游和以后修改查询或连接方式时执行，可由开发者本机按需运行。默认 CI 无需安装 `psql`、启动 PostgreSQL 或连接 VibeInsight。后续如需自动化，可独立配置带临时 PostgreSQL 的 CI 任务。
+在隔离 PostgreSQL 中用少量合成事件执行实际 COPY 流和分页对照查询，核对只读账号能查询、项目和会话标识正确、时间与事件 ID 边界正确分页，以及追加轮次和窗口内延迟事件能够被选中。初次接通上游和以后修改查询或连接方式时执行，可由开发者本机按需运行。默认 CI 无需安装 `psql`、启动 PostgreSQL 或连接 VibeInsight。后续如需自动化，可独立配置带临时 PostgreSQL 的 CI 任务。
+
+staging 首次流式拉取达到单次查询时间上限后，从已提交的项目进度续跑。将各项目的回看窗口下界传给上游 COPY 查询，使已推进的项目无需重新传输窗口前的历史，尚无进度的项目继续读取可见历史。验证续跑能保留已归档内容并完成整轮。
 
 ### 回归与构建命令
 
diff --git a/skills/smm-search/SKILL.md b/skills/smm-search/SKILL.md
index 4141e74..340083c 100644
--- a/skills/smm-search/SKILL.md
+++ b/skills/smm-search/SKILL.md
@@ -36,7 +36,7 @@ The local tool starts the service when needed and reuses it if running. Only use
 
 Before searching, call `manage_sync(action="status")` (or `maintenance status` through the launcher) to ensure the local service is available. If startup fails, still search existing archives and mention that they may be out of date. If automatic sync is enabled and the first import has not finished or the user needs very recent history, use `sync` and check its result before relying on the search. If the import is still running, report that results may be incomplete.
 
-1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
+1. Determine scope. For work tied to a project, call `resolve_project` with the current working directory, then search with `scope="project"` and that `project_id`. This includes directly linked projects. When the search runs on a configured SMM Hub, project links come from the Hub and may include other devices or VibeInsight. Use the returned effective scope and fallback reason when reporting which archive was searched. Use `scope="all"` when the user asks across projects, the project cannot be resolved, or a focused search misses relevant history. State the scope when it matters to the answer.
 2. Search with a few distinctive terms from the user's question. Adjust terms and search again if the results contain plausible leads but not the needed evidence. Do not infer that no information exists from a project-scoped miss alone.
 3. Examine the source, project, time, and matched message positions. Search previews may be abbreviated; use `read_conversation` with the conversation ID and relevant positions to inspect complete messages before answering. Distinguish the archived user's statement from an assistant's proposal or speculation.
 4. Cite the computer name, Agent type, original source conversation ID and original message position. For a hub result, use that message's `origins` and `source_position`. Pass the exact returned `hub_id` to `read_conversation` or launcher `read --hub-id`. Read the entire conversation, or pass the returned `hub_message_id` (launcher `--hub-message-id`) for an exact message. If reading remote evidence fails, search again and report the actual scope; never use the same numeric ID against another archive.
diff --git a/src/smm_hub/_archive.py b/src/smm_hub/_archive.py
index b7a6aca..914d5f6 100644
--- a/src/smm_hub/_archive.py
+++ b/src/smm_hub/_archive.py
@@ -2,5 +2,5 @@
 # SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
 """Expose the shared archive API for development from a source checkout."""
 
-from smm_local.core import Archive, shared_db_path
+from smm_local.core import Archive, shared_db_path, tokens
 from smm_local.support import NoRedirect, _service_lock, hub_url
diff --git a/src/smm_hub/hub.py b/src/smm_hub/hub.py
index 4fc1eee..3fe64ca 100644
--- a/src/smm_hub/hub.py
+++ b/src/smm_hub/hub.py
@@ -16,6 +16,8 @@ from fastapi import Depends, FastAPI, Header, HTTPException
 from pydantic import BaseModel, Field
 
 from ._archive import Archive
+from .projects import HubProjects
+from .vibeinsight import SOURCE as VIBEINSIGHT
 
 
 class Record(BaseModel):
@@ -45,6 +47,27 @@ class Search(BaseModel):
     include_current: bool = False
     limit: int = Field(default=5, ge=1, le=50)
     preview_chars: int = 600
+    device_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
+    project_id: int | str | None = None
+
+
+class DeviceProject(BaseModel):
+    id: int | str
+    name: str = Field(min_length=1)
+
+
+class Membership(BaseModel):
+    source: Literal["codex", "claude-code"]
+    source_session_id: str
+    project_id: int | str | None
+
+
+class ProjectMetadata(BaseModel):
+    hub_id: str
+    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")
+    device_name: str = Field(min_length=1, max_length=120)
+    projects: list[DeviceProject] = Field(max_length=100)
+    memberships: list[Membership] = Field(max_length=100)
 
 
 class Read(BaseModel):
@@ -91,20 +114,11 @@ def order_messages(con, conversation_id: int) -> None:
                     enumerate(ordered, 1))
 
 
-def create_hub(db: Archive, token: str) -> FastAPI:
+def create_hub(db: Archive, token: str, *, lifespan=None) -> FastAPI:
     if not token.isascii() or len(token) < 32 or any(not 33 <= ord(char) <= 126 for char in token):
         raise ValueError("汇总服务需要至少 32 字符的连接凭证")
+    projects = HubProjects(db)
     with db.connect() as con:
-        con.executescript("""
-            CREATE TABLE IF NOT EXISTS hub_devices (id TEXT PRIMARY KEY, name TEXT NOT NULL);
-            CREATE TABLE IF NOT EXISTS hub_origins (
-                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
-                device_id TEXT NOT NULL REFERENCES hub_devices(id),
-                source_position INTEGER NOT NULL,
-                source_order INTEGER NOT NULL,
-                PRIMARY KEY (message_id, device_id, source_position)
-            );
-        """)
         con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('hub_identity',?)",
                     (json.dumps(uuid4().hex),))
         hub_id = json.loads(con.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()[0])
@@ -114,7 +128,7 @@ def create_hub(db: Archive, token: str) -> FastAPI:
             raise HTTPException(401, "需要有效的汇总服务凭证")
 
     app = FastAPI(title="SMM Hub", docs_url=None, redoc_url=None, openapi_url=None,
-                  dependencies=[Depends(authorize)])
+                  dependencies=[Depends(authorize)], lifespan=lifespan)
 
     def require_hub(expected: str) -> None:
         if expected != hub_id:
@@ -122,7 +136,7 @@ def create_hub(db: Archive, token: str) -> FastAPI:
 
     @app.get("/v1/info")
     def info():
-        return {"protocol": 1, "hub_id": hub_id}
+        return {"protocol": 1, "hub_id": hub_id, "capabilities": ["projects"]}
 
     @app.post("/v1/upload")
     def upload(batch: Upload):
@@ -172,19 +186,84 @@ def create_hub(db: Archive, token: str) -> FastAPI:
             for conversation_id in changed:
                 order_messages(con, conversation_id)
                 db._reindex(con, conversation_id)
+                projects.reindex(con, conversation_id)
         return {"accepted": len(batch.records)}
 
-    def add_origins(conversation: dict, message_field: str) -> dict:
+    @app.post("/v1/project-metadata")
+    def project_metadata(batch: ProjectMetadata):
+        require_hub(batch.hub_id)
+        with db.connect() as con:
+            con.execute("BEGIN IMMEDIATE")
+            con.execute("""
+                INSERT INTO hub_devices(id,name) VALUES(?,?)
+                ON CONFLICT(id) DO UPDATE SET name=excluded.name
+            """, (batch.device_id, batch.device_name))
+            for project in batch.projects:
+                projects.upsert(con, "device", batch.device_id, str(project.id), project.name)
+            for item in batch.memberships:
+                row = con.execute("""
+                    SELECT c.id FROM conversations c WHERE c.source=? AND c.source_session_id=?
+                    AND EXISTS (
+                        SELECT 1 FROM messages m JOIN hub_origins o ON o.message_id=m.id
+                        WHERE m.conversation_id=c.id AND o.device_id=?
+                    )
+                """, (item.source, item.source_session_id, batch.device_id)).fetchone()
+                if row is None:
+                    raise HTTPException(409, "设备需先上传会话")
+                project_id = None
+                if item.project_id is not None:
+                    project = con.execute("""
+                        SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?
+                    """, (batch.device_id, str(item.project_id))).fetchone()
+                    if project is None:
+                        raise HTTPException(409, "设备需先上传项目")
+                    project_id = project[0]
+                projects.assign(con, row[0], "device", batch.device_id, project_id)
+                projects.reindex(con, row[0])
+        return {"projects": len(batch.projects), "memberships": len(batch.memberships)}
+
+    def add_projects(conversation: dict, within: tuple[int, ...] | None = None,
+                     messages: tuple[int, ...] | None = None) -> None:
+        assigned = projects.memberships(conversation["id"], within, messages)
+        conversation["projects"] = assigned
+        if assigned:
+            conversation["project_id"] = assigned[0]["id"]
+            conversation["project_name"] = assigned[0]["name"]
+
+    def add_origins(conversation: dict, message_field: str, within: tuple[int, ...] | None = None) -> dict:
+        if conversation["source"] == VIBEINSIGHT:
+            source_id, _, platform, original_session = json.loads(conversation["source_session_id"])
+            conversation["source_session_id"] = original_session
+            origin = {"source": VIBEINSIGHT, "source_id": source_id, "platform": platform}
+            with db.connect() as con:
+                for message in conversation[message_field]:
+                    message_id = message.pop("_message_id")
+                    event = con.execute("""
+                        SELECT v.event_id,v.project_id,p.name FROM hub_vibeinsight_messages v
+                        JOIN projects p ON p.id=v.project_id WHERE v.id=?
+                    """, (message_id,)).fetchone()
+                    message["hub_message_id"] = message_id
+                    message["origins"] = [{**origin, "source_position": message["position"],
+                                           "source_event_id": event[0], "project_id": event[1],
+                                           "project_name": event[2]}]
+            conversation["origins"] = [origin]
+            return conversation
         devices = {}
         with db.connect() as con:
             for message in conversation[message_field]:
                 message_id = message.pop("_message_id")
                 message["hub_message_id"] = message_id
                 origins = [dict(row) for row in con.execute("""
-                    SELECT d.id AS device_id, d.name AS device_name, o.source_position
+                    SELECT d.id AS device_id, d.name AS device_name,o.source_position,
+                           pm.project_id,p.name AS project_name
                     FROM hub_origins o JOIN hub_devices d ON d.id=o.device_id
+                    LEFT JOIN hub_project_memberships pm ON pm.kind='device' AND pm.owner=d.id
+                        AND pm.conversation_id=?
+                    LEFT JOIN projects p ON p.id=pm.project_id
                     WHERE o.message_id=? ORDER BY d.name,d.id,o.source_position
-                """, (message_id,))]
+                """, (conversation["id"], message_id))]
+                if within is not None:
+                    origins = [origin for origin in origins if origin["project_id"] in within]
                 message["origins"] = origins
                 for origin in origins:
                     devices[origin["device_id"]] = {
@@ -196,11 +275,24 @@ def create_hub(db: Archive, token: str) -> FastAPI:
     @app.post("/v1/search")
     def search(req: Search):
         try:
-            result = db.search(**req.model_dump(), include_message_ids=True)
+            effective = None
+            ids = None
+            if req.project_id is not None:
+                if req.device_id is None:
+                    raise ValueError("项目检索需要设备标识")
+                effective = projects.effective(req.device_id, str(req.project_id))
+                ids = tuple(project["id"] for project in effective)
+            result = db.search(**req.model_dump(exclude={"project_id", "device_id"}),
+                               include_message_ids=True, hub_project_ids=ids)
         except ValueError as exc:
             raise HTTPException(400, str(exc)) from exc
+        if effective is not None:
+            result.update(scope="project", effective_projects=effective)
         for hit in result["results"]:
-            add_origins(hit, "matched_messages")
+            matched = hit["matched_messages"]
+            anchors = tuple(item["_message_id"] for item in matched if item.pop("_query_match", False))
+            add_projects(hit, ids, anchors or tuple(item["_message_id"] for item in matched))
+            add_origins(hit, "matched_messages", ids)
         return {**result, "hub_id": hub_id}
 
     @app.post("/v1/read")
@@ -211,6 +303,9 @@ def create_hub(db: Archive, token: str) -> FastAPI:
                              include_message_ids=True, message_id=req.message_id)
         except ValueError as exc:
             raise HTTPException(404, str(exc)) from exc
+        # A single-message citation carries the actual project of that message
+        # even when the conversation has been seen in several projects.
+        add_projects(result, messages=(req.message_id,) if req.message_id is not None else None)
         return add_origins(result, "messages")
 
     return app
diff --git a/src/smm_hub/hub_admin.py b/src/smm_hub/hub_admin.py
index be352f2..b6ce8f8 100644
--- a/src/smm_hub/hub_admin.py
+++ b/src/smm_hub/hub_admin.py
@@ -46,6 +46,25 @@ def add_arguments(commands) -> None:
     upgrade.add_argument("--index", help="Python 包索引")
     upgrade.add_argument("--prerelease", action="store_true")
     upgrade.add_argument("--version", help="切换到指定的发行版本")
+    projects = actions.add_parser("project", help="管理汇总项目及直接关联")
+    project_actions = projects.add_subparsers(dest="project_action", required=True)
+    project_actions.add_parser("list", help="列出设备和 VibeInsight 项目")
+    project_actions.add_parser("links", help="列出双向项目关联")
+    for operation, help_text in (("link", "关联两个项目"), ("unlink", "解除项目关联")):
+        relation = project_actions.add_parser(operation, help=help_text)
+        relation.add_argument("one", type=int)
+        relation.add_argument("other", type=int)
+    vibeinsight = actions.add_parser("vibeinsight", help="配置 VibeInsight 只读同步")
+    vibeinsight_actions = vibeinsight.add_subparsers(dest="vibeinsight_action", required=True)
+    configure = vibeinsight_actions.add_parser("configure", help="验证并保存连接，启用同步")
+    configure.add_argument("--host", required=True)
+    configure.add_argument("--port", type=int, default=5432)
+    configure.add_argument("--database", required=True)
+    configure.add_argument("--user", required=True)
+    configure.add_argument("--interval", type=int, default=300, help="同步周期，单位为秒")
+    configure.add_argument("--psql", default="psql", help="PostgreSQL 客户端的路径")
+    configure.add_argument("--password-file", type=Path, help="从凭据文件读取密码，否则交互输入")
+    vibeinsight_actions.add_parser("status", help="查看同步状态")
     actions.add_parser("run", help=argparse.SUPPRESS)
 
 
@@ -331,14 +350,46 @@ class Hub:
             with closing(sqlite3.connect(self.database)) as target:
                 source.backup(target)
 
+    def project(self, args):
+        from .projects import HubProjects
+
+        projects = HubProjects(Archive(self.database))
+        if args.project_action in ("list", "links"):
+            return getattr(projects, args.project_action)()
+        projects.link(args.one, args.other, linked=args.project_action == "link")
+        return projects.links()
+
+    def vibeinsight(self, args):
+        from getpass import getpass
+
+        from .vibeinsight_settings import Connection, VibeInsightSettings
+
+        settings = VibeInsightSettings(self.root, Archive(self.database))
+        if args.vibeinsight_action == "status":
+            return settings.status()
+        self.service.protect_state()
+        if args.password_file:
+            password = args.password_file.expanduser().read_text(encoding="utf-8").rstrip("\r\n")
+        elif sys.stdin.isatty():
+            password = getpass("VibeInsight 数据库密码：")
+        else:
+            raise ValueError("请在交互终端输入密码，或传入 --password-file")
+        return settings.configure(
+            Connection(args.host, args.port, args.database, args.user, args.interval, args.psql),
+            password,
+        )
+
     def server(self):
         import uvicorn
 
         from .hub import create_hub
+        from .vibeinsight_settings import VibeInsightSettings
 
         cfg = self.config()
         token = self.token.read_text(encoding="ascii").strip()
-        return uvicorn.Server(uvicorn.Config(create_hub(Archive(self.database), token),
+        archive = Archive(self.database)
+        sync = VibeInsightSettings(self.root, archive)
+        return uvicorn.Server(uvicorn.Config(create_hub(archive, token, lifespan=sync.lifespan),
             host=cfg["bind"], port=cfg["port"], ssl_certfile=str(self.certificate),
             ssl_keyfile=str(self.key)))
 
@@ -359,6 +410,6 @@ def dispatch(args: argparse.Namespace):
         return getattr(hub, action)()
     hub.root.mkdir(mode=0o700, parents=True, exist_ok=True)
     with _service_lock(hub.root / "admin.lock"):
-        if action in ("setup", "upgrade"):
+        if action in ("setup", "upgrade", "project", "vibeinsight"):
             return getattr(hub, action)(args)
         return getattr(hub, action)()
diff --git a/src/smm_hub/projects.py b/src/smm_hub/projects.py
new file mode 100644
index 0000000..7a3406d
--- /dev/null
+++ b/src/smm_hub/projects.py
@@ -0,0 +1,165 @@
+# SPDX-License-Identifier: Apache-2.0
+"""Project identity and membership in the aggregation archive."""
+
+from __future__ import annotations
+
+from collections import defaultdict
+
+from ._archive import Archive, tokens
+
+
+class HubProjects:
+    def __init__(self, db: Archive):
+        self.db = db
+        with db.connect() as con:
+            con.executescript("""
+                CREATE TABLE IF NOT EXISTS hub_devices (id TEXT PRIMARY KEY, name TEXT NOT NULL);
+                CREATE TABLE IF NOT EXISTS hub_origins (
+                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
+                    device_id TEXT NOT NULL REFERENCES hub_devices(id),
+                    source_position INTEGER NOT NULL,
+                    source_order INTEGER NOT NULL,
+                    PRIMARY KEY (message_id,device_id,source_position)
+                );
+                CREATE TABLE IF NOT EXISTS hub_projects (
+                    id INTEGER PRIMARY KEY REFERENCES projects(id),
+                    kind TEXT NOT NULL,
+                    owner TEXT NOT NULL,
+                    source_key TEXT NOT NULL,
+                    UNIQUE(kind,owner,source_key)
+                );
+                CREATE TABLE IF NOT EXISTS hub_project_memberships (
+                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
+                    kind TEXT NOT NULL,
+                    owner TEXT NOT NULL,
+                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
+                    PRIMARY KEY(conversation_id,kind,owner,project_id)
+                );
+                CREATE INDEX IF NOT EXISTS hub_membership_by_project
+                  ON hub_project_memberships(project_id,conversation_id);
+                CREATE TABLE IF NOT EXISTS hub_vibeinsight_messages (
+                    id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
+                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
+                    event_id TEXT NOT NULL, trace_key TEXT NOT NULL
+                );
+                CREATE TABLE IF NOT EXISTS hub_project_documents (
+                    id INTEGER PRIMARY KEY,
+                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
+                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
+                    UNIQUE(conversation_id,project_id)
+                );
+                CREATE INDEX IF NOT EXISTS hub_documents_by_project ON hub_project_documents(project_id,id);
+                CREATE VIRTUAL TABLE IF NOT EXISTS hub_project_fts USING fts5(terms, tokenize='unicode61');
+                CREATE VIEW IF NOT EXISTS hub_project_messages AS
+                    SELECT DISTINCT m.id AS message_id, m.conversation_id, pm.project_id
+                    FROM hub_project_memberships pm JOIN messages m ON m.conversation_id=pm.conversation_id
+                    JOIN hub_origins o ON o.message_id=m.id AND o.device_id=pm.owner
+                    WHERE pm.kind='device'
+                    UNION ALL
+                    SELECT m.id,m.conversation_id,v.project_id FROM hub_vibeinsight_messages v
+                    JOIN messages m ON m.id=v.id;
+            """)
+
+    @staticmethod
+    def upsert(con, kind: str, owner: str, key: str, name: str) -> int:
+        row = con.execute(
+            "SELECT id FROM hub_projects WHERE kind=? AND owner=? AND source_key=?",
+            (kind, owner, key),
+        ).fetchone()
+        if row is not None:
+            con.execute("UPDATE projects SET name=? WHERE id=? AND name<>?", (name, row[0], name))
+            return row[0]
+        project = con.execute("INSERT INTO projects(name) VALUES(?) RETURNING id", (name,)).fetchone()[0]
+        con.execute("INSERT INTO hub_projects(id,kind,owner,source_key) VALUES(?,?,?,?)",
+                    (project, kind, owner, key))
+        return project
+
+    @staticmethod
+    def assign(con, conversation: int, kind: str, owner: str, project: int | None) -> None:
+        if kind == "device":
+            con.execute("""
+                DELETE FROM hub_project_memberships WHERE conversation_id=? AND kind=? AND owner=?
+                  AND project_id IS NOT ?
+            """, (conversation, kind, owner, project))
+        if project is not None:
+            con.execute("""
+                INSERT OR IGNORE INTO hub_project_memberships(conversation_id,kind,owner,project_id)
+                VALUES(?,?,?,?)
+            """, (conversation, kind, owner, project))
+
+    @staticmethod
+    def reindex(con, conversation: int) -> None:
+        con.execute("""
+            DELETE FROM hub_project_fts WHERE rowid IN (
+              SELECT id FROM hub_project_documents WHERE conversation_id=?
+            )
+        """, (conversation,))
+        con.execute("DELETE FROM hub_project_documents WHERE conversation_id=?", (conversation,))
+        by_project = defaultdict(list)
+        for project, body in con.execute("""
+            SELECT pm.project_id,m.text FROM hub_project_messages pm JOIN messages m ON m.id=pm.message_id
+            WHERE pm.conversation_id=? ORDER BY m.position,m.id
+        """, (conversation,)):
+            by_project[project].append(body)
+        for project, bodies in by_project.items():
+            document = con.execute("""
+                INSERT INTO hub_project_documents(conversation_id,project_id) VALUES(?,?) RETURNING id
+            """, (conversation, project)).fetchone()[0]
+            terms = " ".join(tokens("\n".join(bodies)))
+            con.execute("INSERT INTO hub_project_fts(rowid,terms) VALUES(?,?)", (document, terms))
+
+    def list(self) -> list[dict]:
+        with self.db.connect() as con:
+            return self._list(con)
+
+    @staticmethod
+    def _list(con, ids: tuple[int, ...] | None = None) -> list[dict]:
+        query = """
+            SELECT p.id,p.name,h.kind AS source,h.owner,h.source_key,d.name AS device_name
+            FROM hub_projects h JOIN projects p ON p.id=h.id
+            LEFT JOIN hub_devices d ON h.kind='device' AND h.owner=d.id
+        """
+        if ids is not None:
+            query += " WHERE h.id IN (" + ",".join("?" for _ in ids) + ")"
+        return [dict(row) for row in con.execute(query + " ORDER BY p.id", ids or ())]
+
+    def memberships(self, conversation: int, within: tuple[int, ...] | None = None,
+                    messages: tuple[int, ...] | None = None) -> list[dict]:
+        with self.db.connect() as con:
+            if messages:
+                placeholders = ",".join("?" for _ in messages)
+                query = (f"SELECT DISTINCT project_id FROM hub_project_messages "
+                         f"WHERE conversation_id=? AND message_id IN ({placeholders})")
+                args = (conversation, *messages)
+            else:
+                query = "SELECT DISTINCT project_id FROM hub_project_memberships WHERE conversation_id=?"
+                args = (conversation,)
+            ids = tuple(row[0] for row in con.execute(query, args) if within is None or row[0] in within)
+            return self._list(con, ids) if ids else []
+
+    def effective(self, device: str, key: str) -> list[dict]:
+        with self.db.connect() as con:
+            row = con.execute(
+                "SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?",
+                (device, key),
+            ).fetchone()
+        if row is None:
+            return []
+        ids = tuple(self.db.effective_projects(row[0]))
+        with self.db.connect() as con:
+            return self._list(con, ids)
+
+    def links(self) -> list[dict]:
+        with self.db.connect() as con:
+            return [dict(row) for row in con.execute("SELECT a,b FROM project_links ORDER BY a,b")]
+
+    def link(self, one: int, other: int, *, linked: bool = True) -> None:
+        with self.db.connect() as con:
+            kinds = [row[0] for row in con.execute(
+                "SELECT kind FROM hub_projects WHERE id IN (?,?)", (one, other)
+            )]
+        if len(kinds) != 2:
+            raise ValueError("请选择两个不同的汇总项目")
+        if "device" not in kinds:
+            raise ValueError("关联至少需要一个设备项目")
+        self.db.link_projects(one, other, linked)
diff --git a/src/smm_hub/vibeinsight.py b/src/smm_hub/vibeinsight.py
new file mode 100644
index 0000000..192cccf
--- /dev/null
+++ b/src/smm_hub/vibeinsight.py
@@ -0,0 +1,421 @@
+# SPDX-License-Identifier: Apache-2.0
+"""Read-only VibeInsight ingestion with durable archive checkpoints."""
+
+from __future__ import annotations
+
+import base64
+import json
+import os
+import sqlite3
+import subprocess
+import tempfile
+import time
+from collections import defaultdict
+from contextlib import closing
+from datetime import UTC, datetime, timedelta
+from threading import Event, Thread
+from typing import Protocol
+
+from ._archive import Archive
+from .projects import HubProjects
+
+Position = tuple[str, str]
+SOURCE = "vibeinsight"
+OVERLAP = timedelta(hours=24)
+BATCH_SIZE = 500
+
+
+class Source(Protocol):
+    def validate(self) -> None: ...
+    def projects(self, through: Position | None = None) -> list[str]: ...
+    def upper(self) -> Position | None: ...
+    def page(self, project: str, after: Position | None, through: Position, limit: int) -> list[dict]: ...
+
+
+def _literal(value: str) -> str:
+    return "'" + value.replace("'", "''") + "'"
+
+
+def _position_sql(position: Position) -> str:
+    timestamp, identifier = position
+    return f"({_literal(timestamp)}::timestamp, {_literal(identifier)})"
+
+
+def event_position(row: dict) -> Position:
+    return row["created_at"], row["id"]
+
+
+class PostgresSource:
+    UNASSIGNED = "(无仓库)"
+    PROMPT = "event_type='trace.started' AND NULLIF(btrim(message),'') IS NOT NULL"
+
+    @classmethod
+    def _repo(cls, alias: str = "") -> str:
+        return f"""CASE WHEN NULLIF(btrim({alias}repo_path), '') IS NULL THEN '{cls.UNASSIGNED}'
+                   ELSE COALESCE(NULLIF(lower(btrim({alias}repo_hostname)), ''), '(本机)')
+                      || COALESCE(':' || {alias}repo_port::text,'')
+                      || '/' || trim(both '/' from btrim({alias}repo_path)) END"""
+
+    def __init__(self, config: dict, password: str):
+        self.config = config
+        self.password = password
+
+    def _command(self) -> tuple[list[str], dict[str, str]]:
+        config = self.config
+        env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
+        env.update(PGPASSWORD=self.password, PGCONNECT_TIMEOUT="5")
+        args = [config["psql"], "--no-psqlrc", "--no-password", "--quiet", "--tuples-only",
+                "--no-align", "--set=ON_ERROR_STOP=1", f"--host={config['host']}",
+                f"--port={config['port']}", f"--dbname={config['database']}", f"--username={config['user']}"]
+        return args, env
+
+    @staticmethod
+    def _transaction(sql: str, timeout: str) -> str:
+        return (f"BEGIN READ ONLY; SET LOCAL statement_timeout='{timeout}'; "
+                "SET LOCAL standard_conforming_strings=on; " + sql + "; COMMIT;")
+
+    def _error(self, code: int, stderr: str) -> RuntimeError:
+        lines = [line for line in stderr.splitlines() if line.strip()]
+        reason = lines[0] if lines else f"退出码 {code}"
+        if self.password:
+            reason = reason.replace(self.password, "***")
+        return RuntimeError(f"VibeInsight 查询失败：{reason[:400]}")
+
+    def _query(self, sql: str) -> list:
+        args, env = self._command()
+        transaction = self._transaction(sql, "25s")
+        try:
+            result = subprocess.run(args, input=transaction, capture_output=True, text=True,
+                                    encoding="utf-8", errors="replace", env=env, timeout=30)
+        except subprocess.TimeoutExpired as exc:
+            raise RuntimeError("VibeInsight 查询超时") from exc
+        except OSError as exc:
+            raise RuntimeError("无法启动 PostgreSQL 客户端 psql") from exc
+        if result.returncode:
+            raise self._error(result.returncode, result.stderr)
+        return [json.loads(line) for line in result.stdout.split("\n") if line.strip()]
+
+    def validate(self) -> None:
+        # PostgreSQL checks privileges on every referenced column even with LIMIT 0.
+        self._query("""
+            SELECT row_to_json(probe) FROM (
+                SELECT id,created_at,user_id,platform_code,session_id,trace_id,event_type,
+                       event_timestamp,message,repo_hostname,repo_port,repo_path FROM fact_events LIMIT 0
+            ) probe
+        """)
+
+    def projects(self, through: Position | None = None) -> list[str]:
+        bound = "" if through is None else f" AND (created_at,id)<={_position_sql(through)}"
+        return self._query(f"""
+            SELECT to_json(project) FROM (
+                SELECT DISTINCT {self._repo()} AS project FROM fact_events
+                WHERE event_type IN ('trace.started','trace.completed')
+                  AND (NULLIF(btrim(message),'') IS NOT NULL OR NULLIF(btrim(repo_path),'') IS NOT NULL) {bound}
+                UNION SELECT '{self.UNASSIGNED}'
+            ) projects ORDER BY project
+        """)
+
+    def upper(self) -> Position | None:
+        bounds = self._query("""
+            SELECT json_build_array(created_at,id) FROM fact_events ORDER BY created_at DESC,id DESC LIMIT 1
+        """)
+        return tuple(bounds[0]) if bounds else None
+
+    def _events_sql(self, after: Position | None, through: Position) -> tuple[str, str]:
+        lower = "" if after is None else f"AND (e.created_at,e.id)>{_position_sql(after)}"
+        upper = _position_sql(through)
+        # A trace's prompt supplies its project. If no matching prompt has
+        # usable project metadata, retain the known reply or session project.
+        common = f"""
+            WITH prompts AS MATERIALIZED (
+                SELECT user_id,platform_code,session_id,{self._repo()} AS project
+                FROM fact_events WHERE {self.PROMPT} AND (created_at,id)<={upper}
+            ), sessions AS (
+                SELECT user_id,platform_code,session_id,
+                    CASE WHEN COUNT(DISTINCT project)=1 THEN MIN(project) END AS sole_project
+                FROM prompts GROUP BY user_id,platform_code,session_id
+            ), trace_projects AS (
+                SELECT DISTINCT ON (user_id,platform_code,session_id,COALESCE(trace_id,id))
+                       user_id,platform_code,session_id,COALESCE(trace_id,id) AS trace_key,
+                       {self._repo()} AS project
+                FROM fact_events
+                WHERE (created_at,id)<={upper} AND NULLIF(btrim(repo_path),'') IS NOT NULL
+                  AND event_type IN ('trace.started','trace.completed')
+                ORDER BY user_id,platform_code,session_id,COALESCE(trace_id,id),
+                         (event_type<>'trace.started'),event_timestamp,id
+            ), events AS (
+                SELECT e.id,e.created_at,e.user_id,e.platform_code,e.session_id,e.trace_id,
+                       e.event_type,e.event_timestamp,e.message,
+                       COALESCE(t.project,NULLIF({self._repo("e.")},'{self.UNASSIGNED}'),
+                                s.sole_project,'{self.UNASSIGNED}') AS project
+                FROM fact_events e JOIN sessions s
+                    ON e.session_id=s.session_id AND e.platform_code=s.platform_code
+                       AND e.user_id IS NOT DISTINCT FROM s.user_id
+                LEFT JOIN trace_projects t ON t.session_id=e.session_id AND t.platform_code=e.platform_code
+                    AND t.user_id IS NOT DISTINCT FROM e.user_id AND t.trace_key=COALESCE(e.trace_id,e.id)
+                WHERE (e.created_at,e.id)<={upper} {lower}
+                  AND e.event_type IN ('trace.started','trace.completed')
+                  AND NULLIF(btrim(e.message),'') IS NOT NULL
+            )
+        """
+        return common, "ORDER BY created_at,id"
+
+    def page(self, project: str, after: Position | None, through: Position, limit: int) -> list[dict]:
+        common, order = self._events_sql(after, through)
+        return self._query(f"""
+            {common}
+            SELECT to_jsonb(events)-'project' FROM events WHERE project={_literal(project)}
+            {order} LIMIT {int(limit)}
+        """)
+
+    def stream(self, after: Position | None, through: Position, *,
+               project_bounds: dict[str, Position] | None = None, stopped=lambda: False):
+        common, _ = self._events_sql(after, through)
+        bounds = json.dumps([
+            {"project": project, "created_at": position[0], "id": position[1]}
+            for project, position in (project_bounds or {}).items()
+        ])
+        sql = f"""
+            COPY (
+                {common}
+                SELECT replace(encode(convert_to(row_to_json(events)::text,'UTF8'),'base64'),
+                               E'\\n','') FROM events
+                LEFT JOIN jsonb_to_recordset({_literal(bounds)}::jsonb)
+                    AS checkpoint(project text, created_at timestamp, id text)
+                    ON checkpoint.project=events.project
+                WHERE checkpoint.project IS NULL
+                    OR (events.created_at,events.id)>(checkpoint.created_at,checkpoint.id)
+                ORDER BY events.created_at,events.id
+            ) TO STDOUT
+        """
+        args, env = self._command()
+        # The client stops a stalled stream sooner; bound server work even if
+        # a disconnected backend cannot immediately observe its closed socket.
+        transaction = self._transaction(sql, "4h").encode("utf-8")
+        with tempfile.TemporaryFile() as contents, tempfile.TemporaryFile() as errors:
+            contents.write(transaction)
+            contents.seek(0)
+            with subprocess.Popen(args, stdin=contents, stdout=subprocess.PIPE, stderr=errors, env=env) as process:
+                assert process.stdout is not None
+                finished = Event()
+                last_output = time.monotonic()
+
+                def interrupt():
+                    while not finished.wait(0.25):
+                        if stopped() or time.monotonic() - last_output >= 300:
+                            if process.poll() is None:
+                                process.kill()
+                            return
+
+                watcher = Thread(target=interrupt, daemon=True)
+                watcher.start()
+                try:
+                    for line in process.stdout:
+                        last_output = time.monotonic()
+                        if stopped():
+                            return
+                        if line.strip():
+                            yield json.loads(base64.b64decode(line))
+                    code = process.wait()
+                    if code != 0 and not stopped():
+                        errors.seek(0)
+                        raise self._error(code, errors.read().decode("utf-8", errors="replace"))
+                finally:
+                    finished.set()
+                    watcher.join()
+                    if process.poll() is None:
+                        process.kill()
+
+
+
+class VibeInsightSync:
+    def __init__(self, db: Archive, source_id: str, *, batch_size: int = BATCH_SIZE):
+        self.db = db
+        self.source_id = source_id
+        self.batch_size = batch_size
+        self.projects = HubProjects(db)
+        with db.connect() as con:
+            con.executescript("""
+                CREATE TABLE IF NOT EXISTS hub_vibeinsight_cursors (
+                    source_id TEXT NOT NULL, project TEXT NOT NULL, timestamp TEXT NOT NULL,
+                    event_id TEXT NOT NULL, PRIMARY KEY(source_id,project)
+                );
+            """)
+
+    def run(self, source: Source, *, stopped=lambda: False) -> None:
+        try:
+            end = source.upper()
+            if end is not None:
+                projects = source.projects(end)
+                if callable(stream := getattr(source, "stream", None)):
+                    self._sync_stream(stream, projects, end, stopped)
+                else:
+                    for project in projects:
+                        if stopped():
+                            return
+                        self._sync_project(source, project, end, stopped)
+        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
+            record_failure(self.db, exc)
+            raise
+        if not stopped():
+            self.db._save_settings({"vibeinsight_last_success": datetime.now(UTC).isoformat(),
+                                    "vibeinsight_error": None})
+
+    def _sync_stream(self, stream, projects: list[str], end: Position, stopped) -> None:
+        with self.db.connect() as con:
+            checkpoints = {row[0]: (row[1], row[2]) for row in con.execute("""
+                SELECT project,timestamp,event_id FROM hub_vibeinsight_cursors WHERE source_id=?
+            """, (self.source_id,))}
+        lower_bounds = {
+            project: ((datetime.fromisoformat(checkpoints[project][0]) - OVERLAP).isoformat(), "")
+            for project in projects if project in checkpoints
+        }
+        after = min(lower_bounds.values()) if lower_bounds and len(lower_bounds) == len(projects) else None
+        known_projects = set(projects)
+        queued: dict[str, list[dict]] = defaultdict(list)
+        size = 0
+
+        def flush():
+            for project, rows in queued.items():
+                self._commit(project, rows, event_position(rows[-1]))
+            queued.clear()
+
+        if not projects or stopped():
+            return
+        previous = after
+        with closing(stream(after, end, project_bounds=lower_bounds, stopped=stopped)) as rows:
+            for row in rows:
+                if stopped():
+                    return
+                position = event_position(row)
+                if position > end or (previous is not None and position <= previous):
+                    raise RuntimeError("VibeInsight 返回了无效的流式同步位置")
+                previous = position
+                project = row["project"]
+                # Discovery and COPY are separate snapshots. A later-visible
+                # project needs its history before it can have a checkpoint.
+                if project not in known_projects:
+                    continue
+                if project in lower_bounds and position <= lower_bounds[project]:
+                    continue
+                queued[project].append(row)
+                size += 1
+                if size == self.batch_size:
+                    flush()
+                    size = 0
+        if not stopped():
+            flush()
+            for project in projects:
+                self._commit(project, [], end)
+
+    def _sync_project(self, source: Source, project: str, end: Position, stopped) -> None:
+        with self.db.connect() as con:
+            saved = con.execute("""
+                SELECT timestamp,event_id FROM hub_vibeinsight_cursors WHERE source_id=? AND project=?
+            """, (self.source_id, project)).fetchone()
+        committed = tuple(saved) if saved else None
+        after = ((datetime.fromisoformat(committed[0]) - OVERLAP).isoformat(), "") if committed else None
+        while not stopped():
+            rows = source.page(project, after, end, self.batch_size)
+            if stopped():
+                return
+            next_position = event_position(rows[-1]) if rows else end
+            if next_position > end or (rows and after is not None and next_position <= after):
+                raise RuntimeError("VibeInsight 返回了无效的分页位置")
+            complete = len(rows) < self.batch_size or next_position == end
+            processed = end if complete else next_position
+            checkpoint = max(committed, processed) if committed else processed
+            self._commit(project, rows, checkpoint)
+            if complete:
+                return
+            committed, after = checkpoint, next_position
+
+    def _commit(self, project: str, rows: list[dict], cursor: Position) -> None:
+        with self.db.connect() as con:
+            con.execute("BEGIN IMMEDIATE")
+            changed: set[int] = set()
+            if rows:
+                project_id = self.projects.upsert(con, SOURCE, self.source_id, project, project)
+                for row in rows:
+                    conversation = self._archive(con, row, project_id)
+                    if conversation is not None:
+                        changed.add(conversation)
+            for conversation in changed:
+                ordering = con.execute("""
+                    SELECT id FROM (
+                        SELECT m.id,m.role,m.timestamp,v.trace_key,v.event_id,
+                          MIN(CASE WHEN m.role='user' THEN m.timestamp END)
+                            OVER (PARTITION BY v.trace_key) AS prompt_time,
+                          MIN(m.timestamp) OVER (PARTITION BY v.trace_key) AS first_event
+                        FROM messages m JOIN hub_vibeinsight_messages v ON m.id=v.id
+                        WHERE m.conversation_id=?
+                    )
+                    ORDER BY COALESCE(prompt_time,first_event),trace_key,
+                             CASE role WHEN 'user' THEN 0 ELSE 1 END,timestamp,event_id
+                """, (conversation,)).fetchall()
+                con.executemany("UPDATE messages SET position=? WHERE id=?",
+                                ((number, row[0]) for number, row in enumerate(ordering, 1)))
+                self.db._reindex(con, conversation)
+                self.projects.reindex(con, conversation)
+            con.execute("""
+                INSERT INTO hub_vibeinsight_cursors(source_id,project,timestamp,event_id)
+                VALUES(?,?,?,?) ON CONFLICT(source_id,project) DO UPDATE
+                SET timestamp=excluded.timestamp,event_id=excluded.event_id
+                WHERE (excluded.timestamp,excluded.event_id)>(timestamp,event_id)
+            """, (self.source_id, project, *cursor))
+
+    def _archive(self, con, row: dict, project_id: int) -> int | None:
+        role = {"trace.started": "user", "trace.completed": "assistant"}.get(row["event_type"])
+        if role is None or not (row["message"] or "").strip():
+            return None
+        identifier = json.dumps([self.source_id, row["user_id"], row["platform_code"], row["session_id"]],
+                                ensure_ascii=False, separators=(",", ":"))
+        timestamp = row["event_timestamp"]
+        con.execute("""
+            INSERT OR IGNORE INTO conversations(source,source_session_id,source_path,started_at,updated_at)
+            VALUES(?,?,?,?,?)
+        """, (SOURCE, identifier, "", timestamp, timestamp))
+        conversation = con.execute("SELECT id FROM conversations WHERE source=? AND source_session_id=?",
+                                   (SOURCE, identifier)).fetchone()[0]
+        trace_key = row["trace_id"] or row["id"]
+        source_key = json.dumps([trace_key, role], ensure_ascii=False)
+        saved = con.execute("""
+            INSERT INTO messages(conversation_id,source_key,position,role,text,timestamp) VALUES(?,?,0,?,?,?)
+            ON CONFLICT(conversation_id,source_key) DO NOTHING RETURNING id
+        """, (conversation, source_key, role, row["message"], timestamp)).fetchone()
+        if saved is None:
+            return self._reassign_provenance(con, conversation, source_key, row["id"], project_id)
+        self.projects.assign(con, conversation, SOURCE, self.source_id, project_id)
+        con.execute("""
+            INSERT INTO hub_vibeinsight_messages(id,project_id,event_id,trace_key) VALUES(?,?,?,?)
+        """, (saved[0], project_id, row["id"], trace_key))
+        con.execute("""
+            UPDATE conversations SET started_at=MIN(started_at,?),updated_at=MAX(updated_at,?) WHERE id=?
+        """, (timestamp, timestamp, conversation))
+        return conversation
+
+    def _reassign_provenance(self, con, conversation: int, key: str, event: str, project: int) -> int | None:
+        previous = con.execute("""
+            SELECT v.id,v.project_id FROM messages m JOIN hub_vibeinsight_messages v ON v.id=m.id
+            WHERE m.conversation_id=? AND m.source_key=? AND v.event_id=? AND v.project_id<>?
+        """, (conversation, key, event, project)).fetchone()
+        if previous is None:
+            return None
+        con.execute("UPDATE hub_vibeinsight_messages SET project_id=? WHERE id=?", (project, previous[0]))
+        self.projects.assign(con, conversation, SOURCE, self.source_id, project)
+        con.execute("""
+            DELETE FROM hub_project_memberships
+            WHERE conversation_id=? AND kind=? AND owner=? AND project_id=?
+              AND NOT EXISTS(SELECT 1 FROM hub_project_messages existing
+                             WHERE existing.conversation_id=hub_project_memberships.conversation_id
+                               AND existing.project_id=hub_project_memberships.project_id)
+        """, (conversation, SOURCE, self.source_id, previous[1]))
+        return conversation
+
+
+def record_failure(archive: Archive, error: Exception) -> None:
+    reason = str(error)[:500]
+    archive._save_settings({
+        "vibeinsight_error": reason,
+        "vibeinsight_last_failure": {"at": datetime.now(UTC).isoformat(), "reason": reason},
+    })
diff --git a/src/smm_hub/vibeinsight_settings.py b/src/smm_hub/vibeinsight_settings.py
new file mode 100644
index 0000000..2c23408
--- /dev/null
+++ b/src/smm_hub/vibeinsight_settings.py
@@ -0,0 +1,123 @@
+# SPDX-License-Identifier: Apache-2.0
+"""Persist the VibeInsight connection and run sync for a managed Hub."""
+
+from __future__ import annotations
+
+import asyncio
+import json
+import shutil
+import sqlite3
+import threading
+import time
+from contextlib import asynccontextmanager
+from dataclasses import dataclass
+from pathlib import Path
+from uuid import uuid4
+
+from ._archive import Archive
+from .vibeinsight import PostgresSource, VibeInsightSync, record_failure
+
+
+@dataclass(frozen=True)
+class Connection:
+    host: str
+    port: int
+    database: str
+    user: str
+    interval: int
+    psql: str
+
+    def __post_init__(self):
+        if not self.host.strip() or not self.user.strip() or not self.database.strip():
+            raise ValueError("VibeInsight 连接需要主机、数据库和用户名")
+        if "=" in self.database or "://" in self.database:
+            raise ValueError("数据库参数应为数据库名")
+        if not 1 <= self.port <= 65535 or self.interval < 1:
+            raise ValueError("数据库端口或同步周期无效")
+
+
+class VibeInsightSettings:
+    def __init__(self, root: Path, archive: Archive, *, source_factory=PostgresSource):
+        self.root = root
+        self.archive = archive
+        self.profile = root / "vibeinsight.json"
+        self.source_factory = source_factory
+
+    def load(self) -> dict:
+        try:
+            return json.loads(self.profile.read_text(encoding="utf-8"))
+        except FileNotFoundError:
+            return {}
+
+    def configure(self, connection: Connection, password: str) -> dict:
+        from .hub_admin import write_file
+
+        binary = shutil.which(connection.psql)
+        if binary is None and self.source_factory is PostgresSource:
+            raise ValueError("找不到 psql，请安装 PostgreSQL 客户端或指定 --psql")
+        if not password:
+            raise ValueError("VibeInsight 数据库密码不能为空")
+        prior = self.load()
+        config = {**vars(connection), "psql": str(Path(binary).resolve()) if binary else connection.psql}
+        self.source_factory(config, password).validate()
+        config["credential_file"] = f"vibeinsight-credential-{uuid4().hex}"
+        credential = self.root / config["credential_file"]
+        write_file(credential, password.encode("utf-8"))
+        try:
+            write_file(self.profile, json.dumps(config, ensure_ascii=False).encode("utf-8"))
+        except OSError:
+            credential.unlink(missing_ok=True)
+            raise
+        if prior:
+            old_file = self.root / Path(prior["credential_file"]).name
+            old_file.unlink(missing_ok=True)
+        return self.status()
+
+    def status(self) -> dict:
+        config = self.load()
+        with self.archive.connect() as con:
+            results = {row[0]: json.loads(row[1]) for row in con.execute("""
+                SELECT key,value FROM settings WHERE key IN ('vibeinsight_last_success','vibeinsight_error','vibeinsight_last_failure')
+            """)}
+        return {
+            "enabled": bool(config),
+            **{key: config[key] for key in ("host", "port", "database", "user", "interval") if key in config},
+            "credential_saved": bool(config and (self.root / Path(config["credential_file"]).name).is_file()),
+            "last_success": results.get("vibeinsight_last_success"),
+            "last_error": results.get("vibeinsight_error"),
+            "last_failure": results.get("vibeinsight_last_failure"),
+        }
+
+    def sync(self, config: dict, stopped) -> None:
+        path = self.root / Path(config["credential_file"]).name
+        try:
+            password = path.read_text(encoding="utf-8")
+        except OSError as exc:
+            raise RuntimeError("无法读取已保存的 VibeInsight 凭据") from exc
+        source_id = json.dumps([config["host"], config["port"], config["database"]])
+        VibeInsightSync(self.archive, source_id).run(self.source_factory(config, password), stopped=stopped)
+
+    def _serve(self, stopped: threading.Event) -> None:
+        previous = {}
+        due = 0.0
+        while not stopped.is_set():
+            try:
+                config = self.load()
+                if config and (config != previous or time.monotonic() >= due):
+                    previous = config
+                    due = time.monotonic() + config["interval"]
+                    self.sync(config, stopped.is_set)
+                    due = time.monotonic() + config["interval"]
+            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
+                record_failure(self.archive, exc)
+            stopped.wait(0.25)
+
+    @asynccontextmanager
+    async def lifespan(self, app):
+        stopped = threading.Event()
+        task = asyncio.create_task(asyncio.to_thread(self._serve, stopped))
+        try:
+            yield
+        finally:
+            stopped.set()
+            await task
diff --git a/src/smm_local/core.py b/src/smm_local/core.py
index 989371f..a736bb8 100644
--- a/src/smm_local/core.py
+++ b/src/smm_local/core.py
@@ -653,7 +653,7 @@ class Archive:
                     return dict(row)
         return None
 
-    def search(self, query: str, *, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, preview_chars: int = 0, include_message_ids: bool = False) -> dict[str, Any]:
+    def search(self, query: str, *, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, preview_chars: int = 0, include_message_ids: bool = False, hub_project_ids: tuple[int, ...] | None = None) -> dict[str, Any]:
         query_terms = list(dict.fromkeys(tokens(query)))
         if not query_terms:
             raise ValueError("查询词不能为空")
@@ -669,8 +669,29 @@ class Archive:
                 raise ValueError("项目范围必须指定 project_id")
             project_ids = self.effective_projects(project_id)
         match = " OR ".join('"'+term.replace('"','')+'"' for term in query_terms)
-        sql = "SELECT c.id,c.source,c.source_session_id,c.title,c.started_at,c.updated_at,c.project_id,p.name AS project_name,bm25(conversation_fts) AS rank_score FROM conversation_fts JOIN conversations c ON c.id=conversation_fts.rowid LEFT JOIN projects p ON p.id=c.project_id WHERE conversation_fts MATCH ?"
+        columns = ("c.id,c.source,c.source_session_id,c.title,c.started_at,c.updated_at,c.project_id,"
+                   "p.name AS project_name")
         args: list[Any] = [match]
+        if hub_project_ids:
+            placeholders = ",".join("?" for _ in hub_project_ids)
+            sql = f"""
+                WITH matched AS MATERIALIZED (
+                    SELECT d.conversation_id,bm25(hub_project_fts) AS score FROM hub_project_fts
+                    JOIN hub_project_documents d ON d.id=hub_project_fts.rowid
+                    WHERE hub_project_fts MATCH ? AND d.project_id IN ({placeholders})
+                ), ranked AS (
+                    SELECT conversation_id,MIN(score) AS rank_score FROM matched GROUP BY conversation_id
+                )
+                SELECT {columns},r.rank_score FROM ranked r JOIN conversations c ON c.id=r.conversation_id
+                LEFT JOIN projects p ON p.id=c.project_id WHERE 1
+            """
+            args.extend(hub_project_ids)
+        else:
+            sql = (f"SELECT {columns},bm25(conversation_fts) AS rank_score FROM conversation_fts "
+                   "JOIN conversations c ON c.id=conversation_fts.rowid "
+                   "LEFT JOIN projects p ON p.id=c.project_id WHERE conversation_fts MATCH ?")
+            if hub_project_ids == ():
+                sql += " AND 0"
         if project_ids is not None:
             sql += " AND c.project_id IN (" + ",".join("?" for _ in project_ids) + ")"
             args.extend(project_ids)
@@ -688,11 +709,27 @@ class Archive:
             results = []
             for index,row in enumerate(rows, 1):
                 fields = "id AS _message_id,position,role,text" if include_message_ids else "position,role,text"
-                messages = con.execute(f"SELECT {fields} FROM messages WHERE conversation_id=? ORDER BY position,id", (row["id"],)).fetchall()
+                message_sql = f"SELECT {fields} FROM messages WHERE conversation_id=?"
+                message_args = (row["id"],)
+                if hub_project_ids:
+                    message_sql += (
+                        " AND id IN (SELECT message_id FROM hub_project_messages WHERE conversation_id=? "
+                        f"AND project_id IN ({placeholders}))"
+                    )
+                    message_args = (row["id"], row["id"], *hub_project_ids)
+                messages = con.execute(message_sql + " ORDER BY position,id", message_args).fetchall()
                 item = dict(row)
+                if hub_project_ids:
+                    item["title"] = next(
+                        (message["text"].strip().splitlines()[0][:120] for message in messages
+                         if message["role"] == "user" and message["text"].strip()), "(无用户消息)"
+                    )
                 item["rank"] = index
                 item["bm25_score"] = -item.pop("rank_score")
                 matched = select_matched_messages(messages, query_terms)
+                if include_message_ids:
+                    for message in matched:
+                        message["_query_match"] = not set(query_terms).isdisjoint(tokens(message["text"]))
                 item["matched_messages"] = [compact_message(m, query_terms, preview_chars) for m in matched] if preview_chars else matched
                 results.append(item)
             effective = [] if project_ids is None else [dict(r) for r in con.execute("SELECT id,name FROM projects WHERE id IN ("+",".join("?" for _ in project_ids)+") ORDER BY id", project_ids)]
diff --git a/src/smm_local/federation.py b/src/smm_local/federation.py
index 6fbead4..211b755 100644
--- a/src/smm_local/federation.py
+++ b/src/smm_local/federation.py
@@ -50,11 +50,15 @@ def _request(config: dict, route: str, payload: dict | None = None) -> dict:
         raise HubUnavailable("无法连接汇总服务") from exc
 
 
-def _hub_identity(config: dict) -> str:
+def _hub_info(config: dict) -> dict:
     response = _request(config, "/info")
     if response.get("protocol") != 1 or not response.get("hub_id"):
         raise HubUnavailable("该地址没有可用的 SMM 汇总服务")
-    return response["hub_id"]
+    return response
+
+
+def _hub_identity(config: dict) -> str:
+    return _hub_info(config)["hub_id"]
 
 
 def configure_hub(db: Archive, address: str, device_name: str, token_file: str | None = None) -> dict:
@@ -116,7 +120,8 @@ def push_pending(db: Archive) -> dict | None:
     config = hub_config(db)
     if not config:
         return None
-    hub_id = _hub_identity(config)
+    info = _hub_info(config)
+    hub_id = info["hub_id"]
     key = f"hub_cursor:{hub_id}:{config['device_id']}"
     with db.connect() as con:
         saved = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
@@ -147,7 +152,8 @@ def push_pending(db: Archive) -> dict | None:
         if not rows:
             if sent == 0:
                 _register_device(config, hub_id)
-            return {"uploaded": sent, "pending": False}
+            pending = "projects" in info.get("capabilities", ()) and _push_projects(db, config, hub_id, cursor)
+            return {"uploaded": sent, "pending": pending}
         response = _request(config, "/upload", {
             "hub_id": hub_id, "device_id": config["device_id"],
             "device_name": config["device_name"], "records": rows,
@@ -161,9 +167,87 @@ def push_pending(db: Archive) -> dict | None:
                 ON CONFLICT(key) DO UPDATE SET value=MAX(CAST(settings.value AS INTEGER), CAST(excluded.value AS INTEGER))
             """, (key, str(cursor)))
         sent += len(rows)
+    if "projects" in info.get("capabilities", ()):
+        _push_projects(db, config, hub_id, cursor)
     return {"uploaded": sent, "pending": True}
 
 
+def _project_keys(con) -> None:
+    con.execute("""
+        CREATE TABLE IF NOT EXISTS hub_local_project_keys (
+            id INTEGER PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
+            remote_key TEXT NOT NULL UNIQUE
+        )
+    """)
+    con.execute("""
+        INSERT INTO hub_local_project_keys(id,remote_key)
+        SELECT id,lower(hex(randomblob(16))) FROM projects
+        WHERE id NOT IN (SELECT id FROM hub_local_project_keys)
+    """)
+
+
+def _push_projects(db: Archive, config: dict, hub_id: str, cursor: int) -> bool:
+    device = config["device_id"]
+    with db.connect() as con:
+        con.execute("BEGIN IMMEDIATE")
+        _project_keys(con)
+        con.execute("""
+            CREATE TABLE IF NOT EXISTS hub_metadata_uploads (
+                hub_id TEXT NOT NULL, device_id TEXT NOT NULL, kind TEXT NOT NULL,
+                local_key TEXT NOT NULL, value TEXT NOT NULL,
+                PRIMARY KEY(hub_id,device_id,kind,local_key)
+            )
+        """)
+    for _ in range(25):
+        if db.get_settings()["sync_paused"] or hub_config(db) != config:
+            return True
+        with db.connect() as con:
+            names = list(con.execute("""
+                SELECT k.remote_key,p.name FROM projects p JOIN hub_local_project_keys k ON k.id=p.id
+                LEFT JOIN hub_metadata_uploads a ON a.hub_id=? AND a.device_id=? AND a.kind='project'
+                  AND a.local_key=k.remote_key
+                WHERE a.value IS NOT p.name ORDER BY p.id LIMIT ?
+            """, (hub_id, device, BATCH_SIZE)))
+            memberships = [] if names else list(con.execute("""
+                SELECT c.source,c.source_session_id,k.remote_key FROM conversations c
+                LEFT JOIN hub_local_project_keys k ON k.id=c.project_id
+                LEFT JOIN hub_metadata_uploads a ON a.hub_id=? AND a.device_id=? AND a.kind='membership'
+                  AND a.local_key=c.source || ':' || c.source_session_id
+                WHERE a.value IS NOT COALESCE(k.remote_key,'')
+                  AND c.source IN ('codex','claude-code')
+                  AND EXISTS(SELECT 1 FROM messages m WHERE m.conversation_id=c.id AND m.id<=?)
+                ORDER BY c.id LIMIT ?
+            """, (hub_id, device, cursor, BATCH_SIZE)))
+        if not names and not memberships:
+            return False
+        response = _request(config, "/project-metadata", {
+            "hub_id": hub_id, "device_id": device, "device_name": config["device_name"],
+            "projects": [{"id": key, "name": name} for key, name in names],
+            "memberships": [{"source": source, "source_session_id": session, "project_id": key}
+                            for source, session, key in memberships],
+        })
+        if response.get("projects") != len(names) or response.get("memberships") != len(memberships):
+            raise HubUnavailable("汇总服务未确认整批项目资料")
+        with db.connect() as con:
+            con.executemany("""
+                INSERT INTO hub_metadata_uploads(hub_id,device_id,kind,local_key,value) VALUES(?,?,?,?,?)
+                ON CONFLICT(hub_id,device_id,kind,local_key) DO UPDATE SET value=excluded.value
+            """, [(hub_id, device, "project", key, name) for key, name in names] +
+                 [(hub_id, device, "membership", f"{source}:{session}", key or "")
+                  for source, session, key in memberships])
+    return True
+
+
+def _remote_project_key(db: Archive, project_id: int) -> str:
+    with db.connect() as con:
+        con.execute("BEGIN IMMEDIATE")
+        _project_keys(con)
+        row = con.execute("SELECT remote_key FROM hub_local_project_keys WHERE id=?", (project_id,)).fetchone()
+        if row is None:
+            raise ValueError("项目不存在")
+        return row[0]
+
+
 def _local_origin(config: dict) -> dict:
     return {"device_name": config.get("device_name") or socket.gethostname(),
             "device_id": config.get("device_id")}
@@ -183,11 +267,18 @@ def search_archive(db: Archive, query: str, *, local: bool = False, **options) -
         try:
             source = options.get("current_source")
             hub_source = source if source in {None, "codex", "claude-code"} else None
-            result = _request(config, "/search", {
+            payload = {
                 "query": query, "current_session_id": options.get("current_session_id") if source == hub_source else None,
                 "current_source": hub_source, "include_current": options.get("include_current", False),
                 "limit": options.get("limit", 5), "preview_chars": options.get("preview_chars", 0),
-            })
+            }
+            if options.get("scope") == "project":
+                if options.get("project_id") is None:
+                    raise ValueError("项目范围必须指定 project_id")
+                if "projects" in _hub_info(config).get("capabilities", ()):
+                    payload.update(device_id=config["device_id"],
+                                   project_id=_remote_project_key(db, options["project_id"]))
+            result = _request(config, "/search", payload)
             if not isinstance(result.get("results"), list) or not result.get("hub_id"):
                 raise HubUnavailable("汇总服务返回了无效搜索结果")
             return {**result, "archive_scope": "hub", "requested_scope": options.get("scope", "all")}
diff --git a/src/smm_local/mcp_server.py b/src/smm_local/mcp_server.py
index 3a140fd..978adcb 100644
--- a/src/smm_local/mcp_server.py
+++ b/src/smm_local/mcp_server.py
@@ -38,7 +38,7 @@ def create_mcp(archive: Archive | None = None) -> FastMCP:
 
     @server.tool(annotations=readonly)
     def search_conversations(query: str, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, local: bool = False) -> str:
-        """Search archived conversations with 600-character message previews and original positions by default. read_conversation returns full evidence. scope=project includes direct links; pass current_session_id to exclude the active conversation by default."""
+        """Search archived conversations with 600-character message previews and original positions by default. read_conversation returns full evidence. scope=project includes direct links in the archive being searched; pass current_session_id to exclude the active conversation by default."""
         current_id = current_session_id or os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
         source = current_source or ("codex" if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID") else "claude-code" if os.environ.get("CLAUDE_SESSION_ID") else None)
         size = int(os.environ.get("SMM_SEARCH_PREVIEW_CHARS", "600"))
diff --git a/tests/test_federation.py b/tests/test_federation.py
index 4182002..542555b 100644
--- a/tests/test_federation.py
+++ b/tests/test_federation.py
@@ -203,3 +203,79 @@ def test_federation_offline_recovery_dedup_and_provenance(tmp_path, monkeypatch)
         if hub.poll() is None:
             hub.terminate()
             hub.wait(timeout=10)
+
+
+def test_project_links_filter_before_ranking_and_follow_only_one_hop(tmp_path):
+    from fastapi.testclient import TestClient
+    from smm_hub.hub import create_hub
+
+    token = "t" * 40
+    with TestClient(create_hub(Archive(tmp_path / "hub.sqlite3"), token),
+                    headers={"Authorization": "Bearer " + token}) as hub:
+        info = hub.get("/v1/info").json()
+        assert "projects" in info.get("capabilities", [])
+        for index, label in enumerate(("alpha", "bravo", "charlie", "delta"), 1):
+            payload = {
+                "hub_id": info["hub_id"], "device_id": f"{index:032x}", "device_name": label,
+                "records": [{"source": "codex", "source_session_id": label, "started_at": None,
+                             "source_key": label, "position": 0, "source_order": 1, "timestamp": None,
+                             "role": "user", "text": f"asteroid {label}"}],
+            }
+            assert hub.post("/v1/upload", json=payload).status_code == 200
+            assert hub.post("/v1/project-metadata", json={
+                **{k: payload[k] for k in ("hub_id", "device_id", "device_name")},
+                "projects": [{"id": 1, "name": "Same name"}],
+                "memberships": [{"source": "codex", "source_session_id": label, "project_id": 1}],
+            }).status_code == 200
+
+        from smm_hub.projects import HubProjects
+
+        manager = HubProjects(Archive(tmp_path / "hub.sqlite3"))
+        projects = {p["device_name"]: p["id"] for p in manager.list()}
+        a, b, c, d = (projects[label] for label in ("alpha", "bravo", "charlie", "delta"))
+        for one, other in [(a, b), (b, a), (a, c), (b, d)]:
+            manager.link(one, other)
+        assert len(manager.links()) == 3
+
+        def check(label, expected):
+            result = hub.post("/v1/search", json={
+                "query": "asteroid", "device_id": f"{label:032x}", "project_id": 1, "limit": len(expected),
+            })
+            assert result.status_code == 200, result.text
+            data = result.json()
+            assert {p["id"] for p in data["effective_projects"]} == expected
+            assert {hit["project_id"] for hit in data["results"]} == expected
+
+        check(1, {a, b, c})
+        check(2, {a, b, d})
+        manager.link(c, a, linked=False)
+        check(1, {a, b})
+        assert len(hub.post("/v1/search", json={"query": "asteroid"}).json()["results"]) == 4
+
+
+def test_project_request_reports_actual_scope_before_any_links(tmp_path):
+    from fastapi.testclient import TestClient
+    from smm_hub.hub import create_hub
+
+    token = "s" * 40
+    device = "0" * 32
+    with TestClient(create_hub(Archive(tmp_path / "hub.sqlite3"), token),
+                    headers={"Authorization": "Bearer " + token}) as hub:
+        info = hub.get("/v1/info").json()
+        if "projects" in info.get("capabilities", []):
+            result = hub.post("/v1/project-metadata", json={
+                "hub_id": info["hub_id"], "device_id": device, "device_name": "Laptop",
+                "projects": [{"id": 1, "name": "Empty"}], "memberships": [],
+            })
+            assert result.status_code == 200
+        result = hub.post("/v1/search", json={"query": "evidence", "device_id": device, "project_id": 1})
+        assert result.status_code == 200
+        assert result.json()["scope"] == "project"
+        assert [p["name"] for p in result.json()["effective_projects"]] == ["Empty"]
+
+
+def test_vibeinsight_configuration_has_managed_hub_entry_point():
+    command = [sys.executable, "-m", "smm_hub.cli", "hub", "vibeinsight", "--help"]
+    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
+    assert result.returncode == 0, result.stderr
+    assert "configure" in result.stdout and "status" in result.stdout
diff --git a/tests/test_vibeinsight_sync.py b/tests/test_vibeinsight_sync.py
new file mode 100644
index 0000000..06e9b6f
--- /dev/null
+++ b/tests/test_vibeinsight_sync.py
@@ -0,0 +1,650 @@
+"""Synthetic source fixtures for Hub synchronization through its normal archive."""
+from pathlib import Path
+
+import pytest
+
+from smm_local.core import Archive
+
+
+def event(number, session, role, project="git.example/team/alpha", *, trace=None, created=None, text=None):
+    return {
+        "id": f"event-{number:04d}", "user_id": "owner", "platform_code": "codex",
+        "session_id": session, "trace_id": trace or f"trace-{number // 2}",
+        "event_type": {"user": "trace.started", "assistant": "trace.completed"}[role],
+        "message": text or f"evidence {session} {number}", "project": project,
+        "event_timestamp": f"2026-09-14T00:{number:02d}:00",
+        "created_at": created or f"2026-09-14T00:{number:02d}:00",
+    }
+
+
+def position(row):
+    return row["created_at"], row["id"]
+
+
+class FixtureSource:
+    def __init__(self, rows, projects):
+        self.rows = rows
+        self.visible = projects
+        self.fail = False
+
+    def validate(self):
+        return None
+
+    def projects(self, through=None):
+        return self.visible
+
+    def upper(self):
+        return max((position(row) for row in self.rows if row["project"] in self.visible), default=None)
+
+    def page(self, project, after, through, limit):
+        if self.fail:
+            raise RuntimeError("fixture connection unavailable")
+        return sorted((row for row in self.rows if row["project"] == project
+                       and (after is None or position(row) > after) and position(row) <= through),
+                      key=position)[:limit]
+
+
+def synchronizer(path: Path):
+    from smm_hub.vibeinsight import VibeInsightSync
+
+    return VibeInsightSync(Archive(path), "fixture", batch_size=2)
+
+
+def test_all_visible_projects_and_historical_discovery(tmp_path):
+    alpha, beta, gamma = ("git.example/team/" + name for name in ("alpha", "beta", "gamma"))
+    source = FixtureSource(
+        [event(8, "alpha", "user", alpha), event(9, "beta", "user", beta),
+         event(1, "gamma", "user", gamma)],
+        [alpha, beta],
+    )
+    database = tmp_path / "hub.sqlite3"
+    run = synchronizer(database)
+    run.run(source)
+    hits = Archive(database).search("evidence")["results"]
+    assert len(hits) == 2
+    assert {Archive(database).read(hit["id"])["messages"][0]["text"] for hit in hits} == {
+        "evidence alpha 8", "evidence beta 9",
+    }
+    source.visible.append(gamma)
+    run.run(source)
+    hits = Archive(database).search("evidence")["results"]
+    assert {Archive(database).read(hit["id"])["messages"][0]["text"] for hit in hits} == {
+        "evidence alpha 8", "evidence beta 9", "evidence gamma 1",
+    }
+
+
+def test_resume_appends_to_same_conversation_in_source_order(tmp_path):
+    alpha = "git.example/team/alpha"
+    rows = [event(n, "old", "user" if n % 2 == 0 else "assistant") for n in range(6)]
+    source = FixtureSource(rows, [alpha])
+    database = tmp_path / "hub.sqlite3"
+    synchronizer(database).run(source)
+    store = Archive(database)
+    original, = store.search("evidence")["results"]
+    before = store.read(original["id"])["messages"]
+    rows.extend([event(n, "old", "user" if n % 2 == 0 else "assistant") for n in range(6, 10)])
+    rows.append(event(12, "new", "user"))
+    resumed = synchronizer(database)
+    resumed.run(source)
+    resumed.run(source)
+    assert len(store.search("evidence")["results"]) == 2
+    assert store.search("old")["results"][0]["id"] == original["id"]
+    after = store.read(original["id"])["messages"]
+    assert after[:6] == before
+    assert [(msg["role"], msg["text"]) for msg in after] == [
+        ("user" if n % 2 == 0 else "assistant", f"evidence old {n}") for n in range(10)
+    ]
+
+
+def test_failed_batch_retries_and_late_event_is_read_once(tmp_path):
+    alpha = "git.example/team/alpha"
+    rows = [event(0, "old", "user"), event(1, "old", "assistant")]
+    source = FixtureSource(rows, [alpha])
+    database = tmp_path / "hub.sqlite3"
+    sync = synchronizer(database)
+    sync.run(source)
+    store = Archive(database)
+    hit, = store.search("evidence")["results"]
+    source.fail = True
+    rows.extend([event(2, "old", "user"), event(4, "other", "user")])
+    with pytest.raises(RuntimeError, match="fixture connection unavailable"):
+        sync.run(source)
+    assert len(store.read(hit["id"])["messages"]) == 2
+    source.fail = False
+    sync.run(source)
+    rows.append(event(3, "old", "assistant"))
+    rows[1]["message"] = "in-place historical edit"
+    synchronizer(database).run(source)
+    synchronizer(database).run(source)
+    assert [msg["text"] for msg in store.read(hit["id"])["messages"]] == [
+        f"evidence old {n}" for n in range(4)
+    ]
+
+
+def fixture_source(config, password):
+    import json
+    if password != "synthetic-reader-password":
+        raise RuntimeError("fixture authentication rejected")
+    raw = json.loads(Path(config["host"]).read_text(encoding="utf-8"))
+    result = FixtureSource(raw["rows"], raw["projects"])
+    result.fail = raw["fail"]
+    return result
+
+
+def run_test_entry():
+    import functools
+    import sys
+
+    from smm_hub import vibeinsight_settings
+
+    settings = functools.partial(vibeinsight_settings.VibeInsightSettings, source_factory=fixture_source)
+    if sys.argv[1] == "serve":
+        import uvicorn
+        from smm_hub.hub import create_hub
+
+        state, port = Path(sys.argv[2]), int(sys.argv[3])
+        archive = Archive(state / "smm-hub.sqlite3")
+        app = create_hub(archive, "h" * 40, lifespan=settings(state, archive).lifespan)
+        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
+    else:
+        from smm_hub.cli import main
+
+        vibeinsight_settings.VibeInsightSettings = settings
+        main()
+
+
+def test_managed_hub_credential_restart_and_mixed_project_search(tmp_path, monkeypatch):
+    import asyncio
+    import json
+    import os
+    import socket
+    import subprocess
+    import sys
+    from urllib.error import URLError
+    from urllib.request import Request, urlopen
+
+    from mcp import ClientSession, StdioServerParameters
+    from mcp.client.stdio import stdio_client
+
+    from smm_local.federation import configure_hub, push_pending
+    from test_federation import cli, eventually, record_codex
+
+    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
+    launcher = [sys.executable, "-c",
+                f"import runpy; runpy.run_path({str(__file__)!r})['run_test_entry']()"]
+    state = tmp_path / "hub"
+    state.mkdir()
+    data = tmp_path / "fixture.json"
+    password = tmp_path / "password"
+    password.write_text("synthetic-reader-password", encoding="utf-8")
+    token = tmp_path / "hub-token"
+    token.write_text("h" * 40, encoding="ascii")
+    alpha, beta, gamma = ("git.example/team/" + name for name in ["alpha", "beta", "gamma"])
+    rows = [event(n, "vibe-A", "user" if n % 2 == 0 else "assistant", alpha)
+            for n in range(10, 16)]
+    rows.extend([event(16, "vibe-B", "user", beta), event(1, "vibe-C", "user", gamma)])
+
+    def write_source(projects, *, fail=False):
+        temporary = data.with_suffix(".tmp")
+        temporary.write_text(json.dumps({"rows": rows, "projects": projects, "fail": fail}), encoding="utf-8")
+        temporary.replace(data)
+
+    def admin(*args, expected=0):
+        result = subprocess.run(launcher + ["hub", "--state-dir", str(state), *args],
+                                capture_output=True, text=True, timeout=10)
+        assert result.returncode == expected, result.stderr
+        assert "synthetic-reader-password" not in result.stdout + result.stderr
+        return json.loads(result.stdout) if expected == 0 else result.stderr
+
+    with socket.socket() as sock:
+        sock.bind(("127.0.0.1", 0))
+        port = sock.getsockname()[1]
+    address = f"http://127.0.0.1:{port}"
+
+    def hub_call(route, payload=None):
+        request = Request(address + "/v1/" + route,
+                          data=json.dumps(payload).encode() if payload is not None else None,
+                          headers={"Content-Type":"application/json", "Authorization":"Bearer " + "h" * 40})
+        try:
+            with urlopen(request, timeout=2) as response:
+                return json.load(response)
+        except URLError:
+            return None
+
+    def start():
+        service = subprocess.Popen(launcher + ["serve", str(state), str(port)])
+        try:
+            eventually(lambda: hub_call("info"))
+        except BaseException:
+            stop(service)
+            raise
+        return service
+
+    def stop(process):
+        if process.poll() is None:
+            process.terminate()
+        try:
+            process.wait(timeout=10)
+        except subprocess.TimeoutExpired:
+            process.kill()
+            process.wait(timeout=10)
+
+    def query(word="evidence"):
+        result = hub_call("search", {"query": word, "limit": 20})
+        return result["results"] if result else []
+
+    write_source([alpha, beta])
+    config = ["vibeinsight", "configure", "--host", str(data), "--database", "fixture", "--user", "reader",
+              "--interval", "1", "--password-file", str(password)]
+    assert admin(*config)["credential_saved"]
+    stored_profile = (state / "vibeinsight.json").read_bytes()
+    assert b"synthetic-reader-password" not in stored_profile
+    password.write_text("wrong-password", encoding="utf-8")
+    assert "fixture authentication rejected" in admin(*config, expected=2)
+    assert (state / "vibeinsight.json").read_bytes() == stored_profile
+    password.unlink()
+    service = start()
+
+    async def mcp(db, tool, arguments):
+        params = StdioServerParameters(command=sys.executable,
+                                       args=["-m", "smm_local.mcp_server", "--db", str(db.db_path)],
+                                       env=dict(os.environ))
+        async with stdio_client(params) as (reader, writer):
+            async with ClientSession(reader, writer) as endpoint:
+                await endpoint.initialize()
+                reply = await endpoint.call_tool(tool, arguments)
+                assert not reply.isError
+                return json.loads(reply.content[0].text)
+
+    try:
+        initially = eventually(lambda: hits if len(hits := query()) == 2 else None)
+        assert {hit["source_session_id"] for hit in initially} == {"vibe-A", "vibe-B"}
+        a = next(hit for hit in initially if hit["source_session_id"] == "vibe-A")
+        assert admin("vibeinsight", "status")["last_success"]
+        hub_id = hub_call("info")["hub_id"]
+        write_source([alpha, beta, gamma])
+        eventually(lambda: any(hit["source_session_id"] == "vibe-C" for hit in query()))
+        stop(service)
+
+        rows.extend(event(n, "vibe-A", "user" if n % 2 == 0 else "assistant", alpha) for n in range(20, 24))
+        rows.append(event(24, "independent", "user", beta))
+        write_source([alpha, beta, gamma])
+        service = start()
+        eventually(lambda: query("independent"))
+        later = hub_call("read", {"hub_id": hub_id, "conversation_id": a["id"]})
+        assert later["source_session_id"] == "vibe-A"
+        assert [item["text"] for item in later["messages"]] == [
+            f"evidence vibe-A {n}" for n in [10, 11, 12, 13, 14, 15, 20, 21, 22, 23]
+        ]
+        assert [item["origins"][0]["source_event_id"] for item in later["messages"]][-2:] == [
+            "event-0022", "event-0023"
+        ]
+        assert admin("vibeinsight", "status")["credential_saved"]
+        write_source([alpha, beta, gamma], fail=True)
+        eventually(lambda: admin("vibeinsight", "status")["last_error"])
+        assert query("independent")
+        write_source([alpha, beta, gamma])
+        recovered = eventually(lambda: status if not (status := admin("vibeinsight", "status"))["last_error"] else None)
+        assert "fixture connection unavailable" in recovered["last_failure"]["reason"]
+
+        clients = []
+        for name in ("device-a", "device-b"):
+            working = tmp_path / name / "work" / "duplicate-name"
+            sessions = tmp_path / name / "sessions"
+            working.mkdir(parents=True)
+            sessions.mkdir()
+            # Original project is determined by cwd, while the file resides in the import root.
+            record_codex(sessions, name, [(0, name, f"evidence from {name}")])
+            history = sessions / f"{name}.jsonl"
+            history.write_text(history.read_text().replace(str(sessions), str(working)), encoding="utf-8")
+            archive = Archive(tmp_path / name / "local.sqlite3")
+            archive.set_settings(codex_root=str(sessions))
+            archive.sync_codex()
+            assert configure_hub(archive, address, name, str(token))["connected"]
+            clients.append((archive, archive.resolve_project(str(working))["id"]))
+        client_a, project_a = clients[0]
+        client_b, project_b = clients[1]
+
+        # Reproduce an old upload with its message cursor independently of project metadata.
+        legacy = {
+            "hub_id": hub_id, "device_name": "device-a",
+            "device_id": json.loads(client_a.db_path.with_suffix(".sqlite3.hub.json").read_text())["device_id"],
+            "records": [{"source":"codex","source_session_id":"device-a","started_at":None,
+                         "source_key":"device-a","position":0,"role":"user",
+                         "text":"evidence from device-a","timestamp":None,"source_order":1}],
+        }
+        assert hub_call("upload", legacy)["accepted"] == 1
+        with client_a.connect() as con:
+            message_id = con.execute("SELECT MAX(id) FROM messages").fetchone()[0]
+            con.execute("INSERT INTO settings(key,value) VALUES(?,?)",
+                        (f"hub_cursor:{hub_id}:{legacy['device_id']}", str(message_id)))
+        historical = next(hit for hit in query() if hit["source_session_id"] == "device-a")
+        assert historical["project_id"] is None
+        assert push_pending(client_a)["uploaded"] == 0
+        assert push_pending(client_b)["uploaded"] == 1
+
+        names = admin("project", "list")
+        device_a, device_b = [next(p for p in names if p["device_name"] == name) for name in ("device-a", "device-b")]
+        vibe_a, vibe_b = [next(p for p in names if p["source_key"] == name) for name in (alpha, beta)]
+        assert device_a["name"] == device_b["name"] == "duplicate-name"
+        for one, other in [(device_a, device_b), (device_a, vibe_a), (device_b, vibe_b), (device_b, device_a)]:
+            links = admin("project", "link", str(one["id"]), str(other["id"]))
+        assert len(links) == 3
+        client_b.rename_project(project_b, "renamed")
+        assert push_pending(client_b)["uploaded"] == 0
+
+        def scope(archive, project):
+            return cli(archive.db_path, "search", "evidence", "--scope", "project",
+                       "--project-id", str(project), "--limit", "20")
+
+        scoped = scope(client_a, project_a)
+        scoped_b = scope(client_b, project_b)
+        assert {hit["source_session_id"] for hit in scoped["results"]} == {"device-a", "device-b", "vibe-A"}
+        assert {p["name"] for p in scoped["effective_projects"]} >= {"duplicate-name", "renamed"}
+        assert {hit["source_session_id"] for hit in scoped_b["results"]} == {
+            "device-a", "device-b", "vibe-B", "independent"
+        }
+        via_mcp = asyncio.run(mcp(client_a, "search_conversations", {
+            "query":"evidence", "scope":"project", "project_id":project_a, "limit":20,
+        }))
+        assert via_mcp["effective_projects"] == scoped["effective_projects"]
+        for session in ("device-a", "vibe-A"):
+            hit = next(row for row in via_mcp["results"] if row["source_session_id"] == session)
+            message = hit["matched_messages"][0]
+            exact = asyncio.run(mcp(client_a, "read_conversation", {
+                "conversation_id":hit["id"], "hub_id":hub_id, "hub_message_id":message["hub_message_id"],
+            }))
+            assert exact["messages"][0]["position"] == message["position"]
+            assert exact["messages"][0]["text"] == message["preview"]
+            assert exact["project_name"] == hit["project_name"]
+        original = hub_call("read", {"hub_id":hub_id,"conversation_id":historical["id"]})
+        assert [msg["text"] for msg in original["messages"]] == ["evidence from device-a"]
+        admin("project", "unlink", str(vibe_a["id"]), str(device_a["id"]))
+        assert {hit["source_session_id"] for hit in scope(client_a, project_a)["results"]} == {"device-a", "device-b"}
+        assert "vibe-A" in {hit["source_session_id"] for hit in query()}
+
+        stop(service)
+        other = tmp_path / "different-project"
+        other.mkdir()
+        sessions = tmp_path / "device-a" / "sessions"
+        record_codex(sessions, "offline-local", [(0, "new", "evidence only in another local project")])
+        history = sessions / "offline-local.jsonl"
+        history.write_text(history.read_text().replace(str(sessions), str(other)), encoding="utf-8")
+        client_a.sync_codex()
+        offline = scope(client_a, project_a)
+        assert offline["scope"] == "all" and offline["archive_scope"] == "local" and offline["fallback_reason"]
+        offline_mcp = asyncio.run(mcp(client_a, "search_conversations", {
+            "query":"evidence", "scope":"project", "project_id":project_a,
+        }))
+        assert offline_mcp["scope"] == "all" and offline_mcp["fallback_reason"]
+        for result in (offline, offline_mcp):
+            assert {hit["source_session_id"] for hit in result["results"]} == {"device-a", "offline-local"}
+    finally:
+        stop(service)
+
+
+def test_archive_and_cursor_rollback_together(tmp_path, monkeypatch):
+    rows = [event(0, "baseline", "user"), event(1, "baseline", "assistant")]
+    source = FixtureSource(rows, ["git.example/team/alpha"])
+    database = tmp_path / "hub.sqlite3"
+    sync = synchronizer(database)
+    sync.run(source)
+
+    def cursor():
+        with sync.db.connect() as connection:
+            return tuple(connection.execute(
+                "SELECT timestamp,event_id FROM hub_vibeinsight_cursors"
+            ).fetchone())
+
+    committed = cursor()
+    # An exact timestamp tie straddles the two-record page boundary.
+    rows.extend([
+        event(2, "batch", "user", created="2026-09-14T00:01:00"),
+        event(3, "batch", "assistant", created="2026-09-14T00:01:00"),
+    ])
+    original = sync._archive
+
+    def fail_after_first_write(connection, row, project):
+        inserted = original(connection, row, project)
+        if row["id"] == "event-0003":
+            raise RuntimeError("rollback this page")
+        return inserted
+
+    with monkeypatch.context() as changes:
+        changes.setattr(sync, "_archive", fail_after_first_write)
+        with pytest.raises(RuntimeError, match="rollback this page"):
+            sync.run(source)
+    assert cursor() == committed
+    assert sync.db.search("batch")["results"] == []
+    assert sync.db.search("baseline")["results"]
+    sync.run(source)
+    sync.run(source)
+    result, = sync.db.search("batch")["results"]
+    assert [item["text"] for item in sync.db.read(result["id"])["messages"]] == [
+        "evidence batch 2", "evidence batch 3",
+    ]
+
+def test_delayed_reply_keeps_source_turns_grouped(tmp_path):
+    directory = tmp_path / "hub.sqlite3"
+    rows = [
+        event(0, "grouped", "user", trace="first"),
+        event(1, "grouped", "user", trace="second"),
+        event(2, "grouped", "assistant", trace="second"),
+        event(3, "grouped", "assistant", trace="first"),
+    ]
+    sync = synchronizer(directory)
+    sync.run(FixtureSource(rows, ["git.example/team/alpha"]))
+    hit, = sync.db.search("grouped")["results"]
+    assert [m["text"] for m in sync.db.read(hit["id"])["messages"]] == [
+        f"evidence grouped {n}" for n in (0, 3, 1, 2)
+    ]
+
+
+def test_scoped_shared_conversations_keep_only_matching_project_messages(tmp_path):
+    from fastapi.testclient import TestClient
+    from smm_hub.hub import create_hub
+    from smm_hub.projects import HubProjects
+
+    archive = Archive(tmp_path / "hub.sqlite3")
+    token = "x" * 40
+    device_a, device_b = "a" * 32, "b" * 32
+    with TestClient(create_hub(archive, token), headers={"Authorization": "Bearer " + token}) as hub:
+        hub_id = hub.get("/v1/info").json()["hub_id"]
+        for device, project, word in [(device_a, "Alpha", "quasar"), (device_b, "Bravo", "orion")]:
+            address = {"device_id": device, "device_name": project, "hub_id": hub_id}
+            upload = hub.post("/v1/upload", json={**address, "records": [
+                {"source":"codex", "source_session_id":"same-archive", "started_at":None,
+                 "source_key":word, "position":1, "source_order":1, "timestamp":None,
+                 "role":"user", "text":f"common {word}"}
+            ]})
+            assert upload.status_code == 200
+            metadata = hub.post("/v1/project-metadata", json={**address, "projects":[{"id":1,"name":project}],
+                "memberships":[{"source":"codex","source_session_id":"same-archive","project_id":1}]})
+            assert metadata.status_code == 200
+
+        def scoped(word):
+            return hub.post("/v1/search", json={
+                "query": word, "device_id": device_a, "project_id": 1, "preview_chars": 0,
+            }).json()["results"]
+
+        assert scoped("orion") == []
+        hit, = scoped("common")
+        assert [message["text"] for message in hit["matched_messages"]] == ["common quasar"]
+        assert hit["matched_messages"][0]["origins"][0]["project_name"] == "Alpha"
+
+        first, second = HubProjects(archive).list()
+        projects = FixtureSource([
+            event(0, "cross-repo", "user", "alpha-repo", text="nebula alphaonly"),
+            event(1, "cross-repo", "assistant", "alpha-repo", text="nebula firstreply"),
+            event(2, "cross-repo", "user", "beta-repo", text="nebula betaonly"),
+            event(3, "cross-repo", "assistant", "beta-repo", text="nebula secondreply"),
+        ], ["alpha-repo", "beta-repo"])
+        synchronizer(archive.db_path).run(projects)
+        global_hit, = hub.post("/v1/search", json={"query":"nebula"}).json()["results"]
+        assert {p["name"] for p in global_hit["projects"]} == {"alpha-repo", "beta-repo"}
+        project_ids = {p["name"]: p["id"] for p in HubProjects(archive).list()}
+        manager = HubProjects(archive)
+        manager.link(first["id"], project_ids["beta-repo"])
+        manager.link(second["id"], project_ids["alpha-repo"])
+        assert scoped("alphaonly") == []
+        beta, = scoped("nebula")
+        assert beta["id"] == global_hit["id"] and beta["project_name"] == "beta-repo"
+        assert [msg["text"] for msg in beta["matched_messages"]] == [
+            "nebula betaonly", "nebula secondreply",
+        ]
+        message_id = beta["matched_messages"][1]["hub_message_id"]
+        exact = hub.post("/v1/read", json={"hub_id":hub_id,"conversation_id":beta["id"],
+                                          "message_id":message_id}).json()
+        assert exact["project_name"] == "beta-repo"
+        assert exact["messages"][0]["origins"][0]["source_event_id"] == "event-0003"
+        manager.link(first["id"], second["id"])
+        both_projects, = scoped("orion")
+        assert both_projects["project_name"] == "Bravo"
+        assert {p["name"] for p in both_projects["projects"]} == {"Bravo"}
+
+        for device, name, role, body in [
+            (device_a, "Alpha", "user", "background from Alpha"),
+            (device_b, "Bravo", "assistant", "long response " * 60 + " 猫"),
+        ]:
+            address = {"device_id": device, "device_name": name, "hub_id": hub_id}
+            upload = hub.post("/v1/upload", json={**address, "records": [
+                {"source":"codex", "source_session_id":"preview-shared", "started_at":None,
+                 "source_key":role, "position":1, "source_order":1, "timestamp":None,
+                 "role":role, "text":body}
+            ]})
+            assert upload.status_code == 200
+            metadata = hub.post("/v1/project-metadata", json={**address, "projects":[],
+                "memberships":[{"source":"codex","source_session_id":"preview-shared","project_id":1}]})
+            assert metadata.status_code == 200
+        result = hub.post("/v1/search", json={"query":"猫", "device_id":device_a, "project_id":1}).json()
+        exact_hit, = result["results"]
+        assert "猫" not in exact_hit["matched_messages"][-1]["preview"]
+        assert exact_hit["project_name"] == "Bravo"
+        assert "_query_match" not in exact_hit["matched_messages"][-1]
+
+
+def test_late_repository_attribution_moves_provenance_without_editing_body(tmp_path):
+    rows = [
+        event(0, "late-project", "user", "alpha", trace="started"),
+        event(1, "late-project", "assistant", "alpha", trace="late"),
+    ]
+    source = FixtureSource(rows, ["alpha"])
+    sync = synchronizer(tmp_path / "archive.sqlite3")
+    sync.run(source)
+    rows.append(event(2, "late-project", "user", "beta", trace="late"))
+    source.visible.append("beta")
+    rows[1].update(project="beta", message="an upstream in-place edit")
+    sync.run(source)
+    hit, = sync.db.search("late-project")["results"]
+    messages = sync.db.read(hit["id"])["messages"]
+    assert [message["text"] for message in messages] == [
+        "evidence late-project 0", "evidence late-project 2", "evidence late-project 1",
+    ]
+    with sync.db.connect() as connection:
+        repo = connection.execute("""
+            SELECT p.name FROM hub_vibeinsight_messages v JOIN projects p ON p.id=v.project_id
+            WHERE v.event_id='event-0001'
+        """).fetchone()
+        assert repo[0] == "beta"
+
+
+def test_streamed_sync_checkpoints_partial_batch_and_discovers_older_projects(tmp_path):
+    class StreamSource(FixtureSource):
+        lower_bounds = None
+        visible_only_during_stream = ()
+
+        def page(self, *args):
+            raise AssertionError("streaming source must avoid repeated project queries")
+
+        def stream(self, after, through, *, project_bounds, stopped=lambda: False):
+            self.lower_bounds = after
+            self.project_bounds = project_bounds
+            projects = set(self.visible) | set(self.visible_only_during_stream)
+            visible = sorted((row for row in self.rows if row["project"] in projects
+                              and (after is None or position(row) > after)
+                              and (row["project"] not in project_bounds
+                                   or position(row) > project_bounds[row["project"]])
+                              and position(row) <= through), key=position)
+            for i, row in enumerate(visible):
+                if self.fail and i == 3:
+                    raise RuntimeError("stream interrupted")
+                yield row
+
+    alpha, beta, gamma = "alpha", "beta", "gamma"
+    rows = [
+        event(4, "shared", "user", alpha, trace="t1"),
+        event(5, "other", "user", beta),
+        event(6, "shared", "assistant", alpha, trace="t1"),
+        event(7, "shared", "user", alpha, trace="t2"),
+        event(1, "older-history", "user", gamma),
+    ]
+    source = StreamSource(rows, [alpha, beta])
+    database = tmp_path / "hub.sqlite3"
+    source.fail = True
+    sync = synchronizer(database)
+    with pytest.raises(RuntimeError, match="stream interrupted"):
+        sync.run(source)
+    with sync.db.connect() as connection:
+        counts = connection.execute("SELECT count(*) FROM messages").fetchone()[0]
+        assert counts == 2
+        saved = dict(connection.execute("SELECT project,event_id FROM hub_vibeinsight_cursors"))
+        assert saved == {"alpha":"event-0004", "beta":"event-0005"}
+    shared, = sync.db.search("shared")["results"]
+    source.fail = False
+    source.visible.append(gamma)
+    resumed = synchronizer(database)
+    resumed.run(source)
+    assert source.lower_bounds is None
+    assert set(source.project_bounds) == {alpha, beta}
+    assert resumed.db.search("older-history")["results"]
+    assert resumed.db.search("shared")["results"][0]["id"] == shared["id"]
+    assert [message["text"] for message in resumed.db.read(shared["id"])["messages"]] == [
+        "evidence shared 4", "evidence shared 6", "evidence shared 7",
+    ]
+    resumed.run(source)
+    assert source.lower_bounds is not None
+    with resumed.db.connect() as connection:
+        assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 5
+
+    # Discovery and streaming have separate upstream snapshots.
+    rows.extend((
+        event(8, "between-snapshots", "user", "delta", created="2026-09-14T00:06:00"),
+        event(9, "project-backfill", "user", "delta", created="2026-09-10T00:00:00"),
+    ))
+    source.visible_only_during_stream = ("delta",)
+    resumed.run(source)
+    with resumed.db.connect() as connection:
+        assert connection.execute("SELECT 1 FROM hub_vibeinsight_cursors WHERE project='delta'").fetchone() is None
+    source.visible.append("delta")
+    resumed.run(source)
+    assert source.lower_bounds is None
+    assert resumed.db.search("project-backfill")["results"]
+
+
+def test_stop_cancels_postgres_stream_while_stdout_is_blocked(tmp_path, monkeypatch):
+    import os
+    import sys
+    import time
+    from threading import Event, Thread
+
+    from smm_hub.vibeinsight import PostgresSource
+
+    started = tmp_path / "child-started"
+    child = "from pathlib import Path; import sys,time; Path(sys.argv[1]).touch(); time.sleep(30)"
+    source = PostgresSource({}, "fixture")
+    monkeypatch.setattr(source, "_command", lambda: ([sys.executable, "-c", child, str(started)], dict(os.environ)))
+    stopped = Event()
+
+    def stop_after_launch():
+        deadline = time.monotonic() + 4
+        while not started.exists() and time.monotonic() < deadline:
+            time.sleep(0.02)
+        stopped.set()
+
+    watchdog = Thread(target=stop_after_launch)
+    watchdog.start()
+    begin = time.monotonic()
+    assert list(source.stream(None, ("2026-09-14T00:00:00", "001"), stopped=stopped.is_set)) == []
+    watchdog.join()
+    assert started.exists()
+    assert time.monotonic() - begin < 5

--- a/README.md
+++ b/README.md
@@ -47,7 +47,7 @@
 
 确认状态中的 `enabled` 和 `running` 都为 `true`，地址与向导中填写的 HTTPS 地址一致。向导会生成连接凭证文件。把文件交给获授权的用户，再在每台客户端对 Agent 说「把这台电脑叫办公室电脑，汇总地址是 https://hub.example.net:8770，凭证文件在这里」，并提供本机文件路径。接入后仍用同一句自然语言搜索。汇总端断开时会退回本机搜索，恢复连接后继续同步。
 
-证书信任、各平台服务配置、升级和卸载见[安装与使用指南](TRIAL_GUIDE.md)。
+面向安装者、汇总端维护者和日常使用者的功能说明与操作入口统一在[使用文档首页](docs/index.md)。首次使用本版本请从该首页选择适用的操作流程。
 
 ## 从源码开发
 

--- /dev/null
+++ b/docs/index.md
@@ -0,0 +1,8 @@
+# SMM 使用文档
+
+这是 SMM 面向安装者、汇总端维护者和日常使用者的使用文档首页。
+
+- 单台电脑安装及日常使用见[快速开始](../README.md#单台电脑快速开始)。
+- 多台电脑共用档案见[部署汇总端](../TRIAL_GUIDE.md#通过包管理器部署汇总端)。
+- 汇总端支持自动同步 VibeInsight 的历史对话、新会话与旧会话追加的轮次。维护者按[从 VibeInsight 同步对话](../TRIAL_GUIDE.md#从-vibeinsight-同步对话)准备只读数据库账户、安装 PostgreSQL 客户端、配置连接并查看状态。
+- 维护者可把不同电脑上传的项目和 VibeInsight 项目建立双向直接关联。按[管理汇总端的项目关联](../TRIAL_GUIDE.md#管理汇总端的项目关联)设置后，用户继续在 Agent 中按当前项目搜索，并读取命中原文。

````

# 固定验收记录

以下为本轮评估开始时读取的 PR #21 正文节选。保留验收结果，省略既有审查结论和早期失败记录。

## 变更

依据已确认的意图 #18、规格 #19 和计划 #20，Hub 通过只读连接同步 VibeInsight 可读取的全部项目，CLI 和 MCP 按当前项目及 Hub 中的直接关联查找并读取原文。现有设备历史可补传项目归属。同步凭据与进度跨重启保留。实现选用 `psql`，常规测试用可控上游夹具。

## 验收

验收 ID `AT-SMM-VIBEINSIGHT-003`，验证提交 `963a8f7`。

### 验收环境与真实服务器覆盖

| 环境 | 状态 | 证据范围 |
| --- | --- | --- |
| 本机隔离 PostgreSQL 14，使用合成 `fact_events` | 已验证 | 独立安装的 Hub wheel 走实际 `psql` 查询、只读账号和 SCRAM 认证，并验证本机 HTTPS、CLI 和 MCP。 |
| 真实 VibeInsight staging | **完整只读同步通过** | 独立 Hub 从空档案开始，上游超时后从持久化检查点续跑并完成整轮同步。CLI/MCP 均搜到并读回同一条消息，与 staging 原始事件核对一致。见完整复跑回执。 |
| 真实 VibeInsight 生产 | 未执行 | 本次补验只连接 staging。 |
| 生产规模吞吐、Windows 服务和 ACL | 未验证 | 本次验证使用本机合成样本。 |

下面七项结论适用于本机夹具和隔离 PostgreSQL 环境。

| SPEC | 结果及证据 |
| --- | --- |
| 1. 自动拉取全部可读取项目 | 通过。夹具覆盖初次导入和可见性变化。隔离 PostgreSQL 的行可见性探针确认较早的第三个项目自动补齐。独立检查验证配置输出、Hub 日志和 SQLite 数据库中无合成密码。 |
| 2. 凭据持久与旧会话续写 | 通过。新进程沿用同一个状态目录，原会话从 3 轮补到 5 轮且保留标识。本机隔离 PostgreSQL 的 SCRAM 拒绝错误密码，权限不足的替换账户也被拒绝，原凭据继续可用。 |
| 3. 跨设备和跨来源关联 | 通过。双端检索验证双向直接关联、重复建立、解除后的项目范围及全局检索。共享会话与跨仓库会话按消息所属项目过滤。 |
| 4. 同名、改名和已有历史 | 通过。基线 `d2dee18` 的 Hub 创建档案后原地升级，补传项目归属后同名项目可分别搜索，旧对话和旧消息引用保留。设备项目改显示名后关联有效。 |
| 5. 检索入口与引用可追溯 | 通过。CLI 和真实 stdio MCP 项目范围一致，两类来源的原文与返回引用可对照。另验证长预览中的一字命中仍归到实际来源项目。 |
| 6. 回退和兼容 | 通过。实际旧客户端上传、全局搜索、读取兼容。断线后 CLI/MCP 回退本机全局并给出原因。 |
| 7. 失败批次与重读去重 | 通过。注入归档中途失败，核对内容与进度一同回滚。本机隔离 PostgreSQL 验证时间相同的事件按 ID 分页、窗口内迟到回复和归属修正。旧消息原地改写保留已归档正文。 |

- 早期提交 `963a8f7` 的全量 pytest（Python 3.14）：61 通过，1 个 Windows 专用测试跳过。Python 3.12 定向复审通过。
- `python3 scripts/build_packages.py` 通过。两个 wheel 分别安装到干净环境，用独立 Hub wheel 跑隔离 PostgreSQL 14 与 HTTPS 服务，再用 Local wheel 验证 CLI 和 MCP。
- `git diff --check origin/main...HEAD` 通过。
- VibeInsight 仓库路径变化按新来源身份处理，设备项目显示名变更已验证。

### 本机执行日志摘录

```text
PASS: SQL page boundary with equal created_at, mixed-repository and unpaired trace attribution, and unsafe credential replacement refusal.
PASS: PostgreSQL SCRAM credentials and late repository provenance without changing the archived message.
PASS: independently installed Hub wheel with PostgreSQL 14 and managed HTTPS lifecycle.
PASS: read-only source, later-visible older history, same-timestamp restart, late completion, original edit preserved, original event reference.
PASS: independently installed Local wheel used CLI and stdio MCP to query Hub.
PASS: actual client from baseline d2dee18 uploaded, searched and read via the new Hub.
PASS: real prior Hub archive migrated in place; distinct scope, identities and old message references verified.
61 passed, 1 skipped in 98.98s (0:01:38)
```

### 真实 staging 完整只读复跑 · 通过

北京时间 2026-11-16T18:06:16+08:00 从空档案启动，2026-11-16T22:10:06+08:00 从检查点续跑，2026-11-16T22:21:19+08:00 结束。Hub 记录整轮成功时间为 `2026-11-16T14:21:17.093536+00:00`。

- 两段均使用独立安装的 Hub wheel 和同一份逻辑档案，通过实际部署的 VibeInsight staging 读取。首次提交 `85280fb` 在四小时查询上限处中断，已保存 **111,587 条消息**。提交 `c891339` 从持久化检查点续跑，新增 **1,669 条消息**并记录整轮成功。最终归档 **142 个项目、20,325 个会话、113,256 条消息**，持久化项目检查点 143 个。
- 按授权使用现有凭据。上游连接默认事务为只读，Hub 的每次 `psql` 调用均检查 `BEGIN READ ONLY`。两段共放行 11 次，拒绝 0 次。探针额外核对和原文比对在只读事务内完成。服务端没有写入或造数据；临时 Hub 已停止。客户端报告 staging 连接未启用 PostgreSQL TLS 或 GSSAPI 加密。
- 样本在独立安装的本机端 CLI 和 stdio MCP 都命中，精确读回的来源会话、源事件、消息位置与角色一致。正文和 staging 原始事件逐字相同。公开回执只保留比较结果。
- 初次实跑在逐项目分页处反复超时。修复后以固定上界的只读 PostgreSQL COPY 流传输，Hub 仍分项目提交内容和进度。首次完整流式查询达到时限后，将每个项目的回看窗口下界加入 COPY 查询，避免续跑时重新传输窗口前的历史。独立复审覆盖停服取消读取、读取中断续跑以及新可见项目的较早历史。复审在隔离 PostgreSQL 14 中核对了实际 COPY 输出，确认各项目的检查点和回看窗口生效，窗口内延迟事件仍能进入档案。普通回归 63 项通过、1 项 Windows 用例跳过。独立 wheel 的隔离 PostgreSQL、旧版客户端和旧档案升级验证通过。

```text
hub_sync_cycle_completed=true
resumed_from_saved_archive=true
sample=staging-message-01 source=vibeinsight role=assistant
cli_search=hit mcp_search=hit
same_source_event_and_session=true
same_cli_mcp_message_position=true
staging_cli_mcp_body_equal=true
upstream_default_transaction_read_only=true
server_writes=false
isolated_hub_stopped=true
```

