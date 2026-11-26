# SMM Local 同事试用指南

SMM 在本机保存 Codex 与 Claude Code 的可见对话文本，提供项目范围 BM25 搜索。首次导入后，源 Agent 删除会话不会删除 SMM 档案。SMM 没有云端服务；Agent 读取的片段仍可能进入该 Agent 所配置的模型服务，请遵守公司的数据使用规则。

## 1. 安装

按 [README 的快速开始](README.md#单台电脑快速开始)安装 `smm-search`。首次使用需要网络和 Agent 的本机执行权限。Skill 会使用已有的 Python，或自动准备用户级 Python。

### 升级本机端

通过搜索 Skill 安装过旧版时，更新整个 `smm-search` Skill 文件夹，并在 `~/.local/share/smm-local/install.json` 中找到 `package_environment`。用该环境的 Python 执行下面三条命令。macOS 和 Linux 的解释器位于环境下的 `bin/python`，Windows 位于 `Scripts/python.exe`。

```text
<安装环境的 Python> -m smm_local.cli stop-on-demand
<安装环境的 Python> -m pip install --upgrade smm-local==0.4.0
<安装环境的 Python> -m smm_local.installation install
```

升级沿用安装清单中的档案路径。升级后新开 Agent 会话，查看 SMM 同步状态。从源码安装的用户可从新版本源码重新运行 `scripts/install.py`。

## 2. 在 Agent 中管理同步

安装完成后，在新的 Codex 或 Claude Code 会话中直接说：

- 「查看 SMM 同步状态」看来源计数、上次同步和导入错误。
- 「打开 SMM 状态页」打开本机页面。
- 「现在同步一次我的对话」立即导入；初次同步可能需要一段时间。
- 「暂停自动同步」或「恢复自动同步」管理后台导入。暂停后仍可查已有档案、查看状态页或明确同步一次；服务或电脑重启后暂停设置仍有效。

如果服务还没运行，Agent 会在需要时启动它。macOS 默认也会在登录后启动服务。

Codex 默认读取 `~/.codex/sessions`，Claude Code 默认读取 `~/.claude/projects`。若历史放在别处，到 Web「配置」设置实际目录，再点「立即同步」。同一个系统账户下，两个 Agent 共用一个同步服务和一个档案，默认位于 `~/.local/share/smm-local/smm.sqlite3`。在任一 Agent 中暂停或恢复，另一边会看到同一个状态。

## 3. 实际提问

在新的 Codex 或 Claude Code 会话中问一个**必须依靠旧对话**才能回答的问题，例如：“我以前对某项目的上线回滚提出过什么要求？请查原始对话并引用来源会话和消息位置。”Agent 应调用 `smm-local` 的检索及读取工具。本机档案的答案可在 Web「检索测试」中复核；汇总端结果由 Agent 保留搜索返回的汇总端和消息引用，通过同一读取工具打开原文。包含 005 的版本中，Web「检索测试」默认联合检索，可明确选择仅本机；0.4.0 的 Web 只查本机。首次尝试可明确说“请使用 SMM 搜索过去对话”，再试不点名工具的自然提问。

项目检索默认只包含当前项目及直接关联项目。跨项目提问时，让 Agent 使用全局范围。本机项目关联可在 Web「项目」中配置；连接 Hub 后，CLI/MCP 的在线检索使用 Hub 保存的关联，由汇总端维护者统一配置。[管理汇总端的项目关联](#管理汇总端的项目关联)

检索结果保留来源、时间和命中位置；每条命中消息默认只预览前 600 字，较长消息会标明省略。需要依据后半段内容作答时，让 Agent 调用 `read_conversation` 读取该轮完整原文。命中一段对话不等于其中每句都是事实，须读原文核对。

## 4. 遇到问题

- 两个来源都显示不可用：让 Agent 打开状态页，在「配置」中检查会话目录。
- 首次安装依赖下载失败：让 Agent 查看具体错误，恢复网络后在会话里重试原请求。
- Claude Code 报 401 或未登录：先检查 Claude Code 自己的模型登录。
- Agent 找不到 SMM：检查 Skill 文件夹是否完整放在所用 Agent 的技能目录，随后新开会话。
- 服务启动失败：让 Agent 检查返回的日志路径并说明实际原因。
- 搜不到预期对话：先确认导入计数和项目范围，再用显著的项目名、人物名或事件词重试。
- Agent 给出没有原文支持的回答：要求它提供来源会话和位置。本机结果可在 Web 读取原文；汇总端结果让 Agent 使用搜索返回的汇总端和消息引用读取原文。请把问题、实际结果与期望来源反馈给试用负责人。

## 5. 结束试用

先从各 Agent 的 Skill 目录移除自己放入的 `smm-search` 文件夹。若也要卸载本机组件，可请 Agent 读取 `~/.local/share/smm-local/install.json`，用其中 `package_environment` 指向的 Python 运行 `-m smm_local.installation uninstall`。从源码安装的旧版仍可从 `project_root` 运行 `scripts/uninstall.py`，以停用服务并移除 MCP 注册。卸载会保留数据库。

请在试用反馈中记录：安装是否独立完成、一次自己的历史问题是否找对原文、一次跨 Agent 搜索是否找对、哪一步费时或困惑。不要把私人对话原文发到公共 issue。

## 本机文档检索（006，尚未发布）

当前 README 快速安装的 0.4.0 和 Skill 首次安装器不含 006，重复安装同版本不会得到文档功能。预览可按 README 从源码安装，或在源码根目录运行 `python3 scripts/build_packages.py`，将 `dist/packages/smm_local-0.4.0-py3-none-any.whl` 安装到**独立新环境**。两个构建包仍使用未发布阶段版本字符串，以实际源码/wheel字节区分；不要覆盖日常安装。需要 Python 3.11+ 和 uv。

```text
uv venv .document-preview
uv pip install --python <新环境的Python> dist/packages/smm_local-0.4.0-py3-none-any.whl
<新环境的Python> -m smm_local.cli --db <独立档案的绝对路径> documents --help
```

macOS/Linux 的解释器是 `.document-preview/bin/python`，Windows 是 `.document-preview\Scripts\python.exe`。以下用 `smm` 表示该环境的入口；需要隔离时，**每条命令**均在子命令之前加 `--db <同一个独立档案>`，MCP 用同环境 `smm-mcp --db <同一档案>`。仅本机文档不需要 Hub，也不需要管理员权限；含007时默认联合查询，明确`--local`保留006范围。Web 沿用本机服务；新档案默认仍配置 Agent 对话来源，若只演示合成文档，可将 `SMM_CODEX_ROOT` 与 `SMM_CLAUDE_ROOT` 指向事先创建的空目录后再启动服务。

1. 打开本机 Web 主导航“文档”。“创建普通本机项目”返回项目 #ID；已有项目也可在“项目”页或 `smm projects` 取得。全局项目通过“项目”页或 `smm project ensure-global` 创建，它与普通项目同级，不自动包含在 A 项目检索中。
2. 添加 **SMM 服务所在电脑**上当前账户可读的绝对文件或目录路径，不能填写浏览器另一台电脑的路径。来源支持 `.md`、`.markdown`、`.txt`（扩展名不区分大小写），严格 UTF-8，允许 BOM；006/007不含 Word、Excel、PDF；包含008的构建见下方新格式章节，图片仍不支持。来源可绑定零个、一或多个现有本机项目；零绑定只参加“全部文档”，共享资料不创建项目关联。CLI 可用 `smm documents add <绝对路径> --project-id ID --project-id ID`。
3. 保存后为 `pending`，尚未读取正文。点击该来源“刷新”或运行 `smm documents refresh --source-id <来源ID>`；省略 ID 逐来源刷新全部。来源 ID 从页面或 `smm documents sources` 取得。目录默认递归，`--no-recursive` 只看根直接文件。默认排除隐藏及 `.git/.hg/.svn/node_modules/.venv/venv/build/dist` 目录，不跟随链接/junction；可将实际文件或实际子目录另加为来源。
4. 自定义 `--exclude` 可重复，使用相对根的 POSIX 路径，大小写敏感：`*` 单段、`?` 单字符、`**` 零或多层目录，末尾 `/` 排目录及后代；例如 `--exclude '**/private.txt' --exclude 'cache/'`。禁止绝对路径、`..`、反斜杠。Web“编辑配置”与 `smm documents set <来源ID>` 都是**完整替换**：未选项目/未给名单即清空，未给 `--no-recursive` 即递归；根路径不变，配置版本递增，旧来源资格立即退出，刷新后按新配置生效。
5. 查看来源 `ready`、`partial`、`failed` 和“文件状态”，CLI 为 `smm documents files --source-id <ID>`。每文件原字节最多 2MiB，每来源最多 1000 个受支持候选及 16MiB 累计（过大文件不计累计，坏编码/NUL/后续不可读仍计）。逐文件错误只让该文件失败；来源枚举或总预算超限整轮失败且旧材料不可查。修正路径/权限/编码或缩小明确纳入范围，再刷新；不要将零命中当作全部已查。`refreshing` 在进程中断后也可通过下一次明确刷新恢复。
6. 在“检索采集文档”选择全部或本机项目；CLI 为 `smm documents search "查询词" --scope project --project-id ID --limit 5`，数量 1–50。只按正文召回。006独立版本及显式`--local`展开本机双向直接一层；包含007并连接Hub时按下一节共同范围执行。有效零命中与未刷新/部分失败分开展示覆盖状态。
7. 点“读取原文”，或原样将命中的 `reference` 传给 `smm documents read --reference <引用>`。默认读最多 2000 码点的命中窗口；`--start 0 --end 100` 按整个规范化文本的 Unicode 码点 `[0,100)` 扩读，一次最多 16000 字符，不是字节或 UTF-16。仅去 BOM 并将 CRLF/CR 转 LF，其他字符不改；原始字节 SHA-256、采集时间和版本均可核对。内容纯文本显示，不执行其中 Markdown/HTML/脚本。
8. 修改/删除文件后，刷新前仍读取明确标记的上次快照；再次刷新才发现变化。内容新版本、失败/缺失、来源配置或资格变化后，失效引用明确拒绝；重新搜索取得新引用。即使改回旧字节或修复后同配置重新纳入，旧失效引用不会复活。首版不提供历史版本读取。无变化刷新、同档案服务/CLI/MCP重启保留版本和连续有效引用，不自动扫描文档。
9. Web“移除来源”或 `smm documents remove <来源ID>` 不改原文件。独占材料立即退出检索/读取；其他有效重叠来源可保留唯一文件级当前快照及项目资格，移除最后采集来源也不回退旧正文。最后来源退出后清理可用正文/索引，不承诺物理介质安全擦除。

Agent 使用三个只读 MCP 工具 `list_document_sources` → `search_documents` → `read_document(reference=...)`；来源管理通过 CLI/Web。先核覆盖，正文需读回再引用规范路径、采集版本/时间、字符/行号。对话仍用原对话工具，不能将两种引用混用。仅本机文档不调用Hub；007联合查询与按项目明确允许的同步使用Hub，均不调用外部模型。Agent自己读取的片段会随其正常上下文流转。

维护者的源码回归、双包独立安装与三系统真实入口复跑前提见[验收探针](scripts/acceptance/README.md#006-本机文档可选实际包验证)。

## 项目文档库与 Hub 同步（007，尚未发布）

本节需要同时含007的 Local 和 Hub；公开0.4.0包及首次安装器尚不包含。两个源码构建包仍用0.4.0阶段版本号，必须以当前提交/模块及wheel摘要区分，重复安装同名公开包不会获得新功能。不覆盖日常实例或拿真实资料验收。

先在源码根构建，再分别安装到两个全新环境。以下解释器路径为macOS/Linux，Windows替换为对应环境下的`Scripts/python.exe`。uv不在PATH时传`--uv <实际uv绝对路径>`。

```text
python3 scripts/build_packages.py
uv venv .preview-local
uv venv .preview-hub
uv pip install --python .preview-local/bin/python dist/packages/smm_local-0.4.0-py3-none-any.whl
uv pip install --python .preview-hub/bin/python dist/packages/smm_hub-0.4.0-py3-none-any.whl
```

下文`smm`、`smm-hub`指各独立环境的真实入口，不是已安装的日常命令。每条Local命令都可在子命令前加`--db <同一个独立数据库绝对路径>`；Hub所有管理命令都使用同一个`hub --state-dir <绝对目录>`。本机Web沿该独立档案启动`serve`；只演示文档时先将`SMM_CODEX_ROOT`、`SMM_CLAUDE_ROOT`指向任务空目录，避免导入日常对话。

**本机创建和管理。** 打开本机Web「文档」，先创建项目。文档项目与对话项目是同一种项目，允许同名、以ID及稳定键区分。选择“上传到本机项目文档库”中的项目，再选择或拖入`.md/.markdown/.txt`。保存即采集SMM专用副本，可立即按项目搜索并点击“读取原文”；外部原文件不会被改写。项目库各文档可选择新文件更新内容，保留ID/显示名/归属；移除退出搜索和读取，副本可以保留。目录/外部文件沿上一节`documents add/set/refresh`，只在明确refresh时读取。

**Hub创建和管理。** 维护者先按[汇总安装](#通过包管理器部署汇总端)准备HTTPS/TLS和连接凭据。独立预览也可用`serve-hub --state-dir <目录> --token-file <现有凭据文件> --tls-cert <证书> --tls-key <私钥> --host <地址> --port <端口>`；非回环必须TLS。直接在浏览器打开该Hub HTTPS根地址，选择维护者交付的纯文本`hub-token`文件认证。凭据仅放内存和同源认证头，不放URL、浏览器存储或Cookie；页面刷新后须重新选择。新建Hub项目后选择/拖入文件，可搜索、按原文引用读取、更新和移除。远程浏览器上传的是文件字节，无需在Hub机器预先准备同名路径。设备/VibeInsight项目为只读投影，没有普通管理资格；本机网页也不代理管理Hub项目。

Hub机器已有文件/目录则由维护者在Hub本机执行：

```text
smm-hub hub --state-dir <目录> project create "共享资料"
smm-hub hub --state-dir <目录> project list
smm-hub hub --state-dir <目录> documents add <Hub机器绝对路径> --project-id <Hub自有ID>
smm-hub hub --state-dir <目录> documents refresh --source-id <add返回的id>
smm-hub hub --state-dir <目录> documents sources
smm-hub hub --state-dir <目录> documents search "独特正文词" --scope project --project-id <Hub项目ID>
smm-hub hub --state-dir <目录> documents read --reference <本次reference>
```

`project ensure-global`创建/取得Hub自有全局项目。`documents set SOURCE --project-id ID [--exclude 模式] [--no-recursive]`完整替换为pending，随后明确refresh；省略列表清空，省略no-recursive恢复递归。`files [--source-id ID]`查看采集状态；`remove SOURCE`退出资格，不删除原文件。零绑定只参加all，多绑定不制造关联。设备来源拒绝Hub refresh/set/remove，不能尝试访问设备路径。网页库文件名只作显示，实际副本位于当前档案旁的隐藏`.documents/UUID/`目录，不允许客户端指定存储路径；相同名字/内容的不同上传是独立身份。

**选择本机项目同步。** 先沿既有`configure-hub`连接验证Hub，新旧项目的文档均默认不上传，允许对话上传、项目关联或来源新增都不代表授权。Web「项目文档同步选择」逐项目操作，或从刚显示的状态逐字取得以下三个值：

```text
smm documents sync-status
smm documents sync-policy <project_key> --enabled yes --expected-hub-id <hub_id> --expected-generation <generation>
smm documents sync
smm documents sources --hub
```

KEY是稳定本机项目键，HID是目标Hub身份，generation是本机保存代次，均不是项目数字ID；过期/错Hub/已删除KEY拒绝，重新查看后再决定。离线仍可保存已验证目标的选择，明确显示待确认；未知Hub不能授权正文。允许后同步该项目成功采集的当前及未来文档；新来源须明确采集。`sync --project-key KEY`只重试指定项目，手动不导入对话、不refresh、不修改全局暂停。正常重启沿用选择及任务。项目显示名修改保留选择；合并后目标保持自身选择，不继承原项目允许，新建/ID复用默认关闭。

`--enabled no`是暂停：停止新正文/新名单，保留Hub已有连续资格；源移除/配置变化、refresh发现删除/不可读/失败仍安排撤回。离线撤回未确认时Hub可能仍返回旧快照，不称远端已删除。后台周期会重试档案任务；全局自动暂停只停止后台正文，仍重试已知控制/撤回；手动documents sync仍可执行。重新允许补当前有效全量，旧失效资格不复活。共享文件只给允许项目新资格；曾允许后暂停的项目，若其资格仍连续，可随另一个获准来源推进到同一文件级新版本，暂停不建立冻结分支。

**按项目检索与原文。** 两端各正常返回limit（1–50）个、每份最多2000码点的片段，随后在本机对最多2limit片段做BM25，按稳定身份打破同分，最终返回limit。未上传本机结果参与排序，候选正文/摘要/文件名单不会为重排外发。相同设备/档案/文件/内容版本且双摘要一致才合并，保留两端精确引用；不同设备或版本分别保留。文档与对话共用Hub双向直接一层关联：A关联B、B关联C时从A只查A+B。

```text
smm projects --hub
smm documents search "正文词" --scope project --project-id <本机根ID>
smm documents search "正文词" --scope project --hub-project-id <Hub根ID>
smm documents search "正文词" --scope project --project-id <本机根ID> --local
smm documents read --reference <本次返回的reference> --start 0 --end 100
smm search "对话词" --scope project --hub-project-id <Hub根ID>
```

`project-id`与`hub-project-id`互斥。Web可选档案范围、项目端及对应项目。MCP `list_projects(include_hub=true)`返回local/hub和逐端coverage/失败原因，默认仍是本机数组；`list_document_sources(include_hub=true)`返回两端来源及coverage，Hub不可用仍返回本机及原因，默认本机。`search_documents(...,local=true)`明确仅本机；`hub_project_id`选择Hub根，读取仍用`read_document(reference=...)`。三个文档工具仍只读，管理需Web/CLI。

线上本机项目根只使用Hub的一层范围并映射自己稳定项目键；仅本机使用本机关联。范围无法确认时只查所请求本机根；Hub根不可得不猜同号/同名本机项目。已取得合法共同范围后仅查询断线，可保留该范围的本机结果；签名/身份被拒绝则不保留。覆盖区分已查完零条、部分、不可用与旧能力不支持。本机失败仍可返回可用Hub结果，并明确缺失端。引用绑定身份/内容版本/当次连续资格，不能把对话引用、另一端数字ID或新资格代替原引用；合并引用只可回退到当次同版本另一端。Unicode码点和LF行号规则沿006。

**保护冲突与恢复。** 文档保护记录是数据库旁的`<数据库名>.documents-guard.json`及锁文件，不是005的upload guard。备份数据库、已有管理原始副本`.documents`及`.document-snapshots`内的持久原件、处理结果和传输状态为一致集；按输出的`do_not_restore`排除快照目录内的`tasks`、`capacity.lock`和`upload-queue.lock`等运行状态，并保留当前`expired-transfers`过期上传身份保护目录，保留既有Hub连接/TLS/凭据；恢复时不能把旧保护文件覆盖当前保护边界。已有`upload prepare-restore`/`hub prepare-restore`输出包含适用文档保护排除项及副本目录，文档正文会停止；Hub还拒绝文档搜索/read。

Hub维护者查看`hub documents recovery-status`的冲突、影响及不透明state，再执行`hub documents recover --expected-state <刚查看state>`。过期state拒绝；成功建立新document_epoch，使全部旧Hub文档引用/资格永久失效并丢弃暂存，自有来源保留pending。随后自有来源明确refresh，本机项目从sync-status取得KEY/HID/generation重新明确允许。Local保护失配也须对需要的项目重新显式选择，其余旧选择不会自动恢复；若本机版本回退仍冲突，应由维护者明确处理Hub恢复，不能猜版本或覆写新正文。此流程不改变005对话恢复约定或日常对话数据。

维护者的[007复跑入口](scripts/acceptance/README.md#007-项目文档库与hub同步)和[已确认平台要求](changes/007-hub-document-search/plan.md)列明自动用例、实际Web/CLI/stdio、服务身份、证据及尚未覆盖项；普通单测通过不等于所有平台交付通过。


## Word、Excel、PDF（008，开发中，尚未发布）

需要包含008的同一次源码构建，公开0.4.0及首次安装器不含本功能。两个预览wheel仍使用0.4.0版本字符串，按提交与wheel摘要区分。使用独立环境、独立档案及Hub状态目录，勿覆盖日常实例。文档解析依赖是可选项；只接收本机已处理结果的Hub不需要安装它们或OCR。

### 安装创建端处理依赖

在源码根目录运行python3 scripts/build_packages.py后，分别建立Local和Hub环境。用实际环境Python安装本轮wheel及documents依赖，例如：

~~~text
uv venv <Local环境>
uv pip install --python <Local环境Python> "<绝对路径>/dist/packages/smm_local-0.4.0-py3-none-any.whl[documents]"
uv venv <Hub环境>
uv pip install --python <Hub环境Python> "<绝对路径>/dist/packages/smm_hub-0.4.0-py3-none-any.whl[documents]"
~~~

macOS/Linux环境Python在bin/python，Windows在Scripts/python.exe。下面smm/smm-hub均指对应独立环境的入口；Local所有命令在子命令前加--db <独立档案>。Hub沿用实际服务状态目录，不能配置一个与服务无关的新默认档案。仅接收结果的Hub安装本次基础wheel，不加[documents]。

DOCX、XLSX与有完整文字层的PDF可直接解析，不要求OCR。扫描页或原生页眉加扫描正文的PDF需要在创建端预先部署本地Tesseract 5及eng、chi_sim语言数据。部署好完整可执行程序及其运行依赖后，用绝对路径配置；SMM不会在处理或启动时联网下载组件。

~~~text
smm --db <独立档案> documents processing-status
smm --db <独立档案> documents processing-configure --expected-revision <刚看到的revision> --ocr-executable <Tesseract可执行文件绝对路径> --ocr-data-dir <语言数据目录绝对路径> --languages eng+chi_sim
smm --db <独立档案> documents processing-status --check
~~~

Hub创建端把命令前缀换为smm-hub hub --state-dir <实际Hub状态目录> documents。配置持久保存，服务重启使用同一档案配置；状态中的最近探测身份应与实际运行任务的账户/服务身份分别核对。过期revision拒绝；配置变更不自动重做已有资料。OCR程序/数据路径只能在所在端CLI配置，网页/API不能指定处理命令。

### 按项目纳入、检索并核对原件

两端的文档与对话共用项目。外部路径沿用documents add/set后明确refresh；网页可在本端项目选择或拖入.docx/.xlsx/.pdf，也可保留旧文本格式。新建同名上传仍是独立资料；更新已有新格式资料须保持格式相同，跨格式改为新纳入。文件不会改写外部源；网页原件和处理结果保存到创建端。

在对应项目的资料行点击“更新文档”并选择同格式新文件；文档身份、原显示名、项目归属和管理存储位置保留，所选文件名可以不同。收到原件后仍须等待本端处理终态，成功换版后重新检索取得新引用；partial/failed按详情处理。“移除文档”撤回检索和原文资格，不作为文件系统擦除承诺。旧页面版本过期时，先重新查看资料库，不覆盖另一入口的新状态。

~~~text
smm --db <独立档案> project create "产品资料"
smm --db <独立档案> projects
smm --db <独立档案> documents add <所在机器文件或目录绝对路径> --project-id <本机项目ID>
smm --db <独立档案> documents refresh --source-id <add返回的来源ID>
smm --db <独立档案> documents files --source-id <来源ID>
smm --db <独立档案> documents search "文档中的独特词" --scope project --project-id <本机项目ID>
smm --db <独立档案> documents read --reference <本次reference>
smm --db <独立档案> documents read --reference <同一reference> --view original-info
smm --db <独立档案> documents read --reference <同一reference> --original-output <尚不存在的输出文件绝对路径>
~~~

Hub使用自己的项目ID及上述Hub前缀；本机检索Hub自有资料仍只有查询/读取权限。查询不重新打开源文件、不解析、不OCR。默认read是提取文本的命中窗口，Unicode码点范围与LF行号沿用旧行为；这不是DOCX/XLSX/PDF原字节。original-info给原SHA、字节数、来源及可用性，original-output下载准确原字节且拒绝覆盖，与start/end或表格参数互斥。无正文命中的合法空白文档可从files/library的original_reference读回原件。

表格命中包含table_context，全文读取列出tables。使用同一引用和返回的table_id：

~~~text
smm --db <独立档案> documents read --reference <reference> --view table --table-id <table_id> --row-start 1 --row-end 4 --column-start 1 --column-end 3
~~~

CLI/API 行列从1开始，终点不含；示例取前三行、前两列。返回表头上下文、单元格、合并跨度及原位置，不猜字段含义。正文/OCR/表格纯文本显示。Agent使用list_document_sources、search_documents、read_document，只能读取text/table/original-info；不通过MCP返回base64大原件，也不新增管理或OCR工具。原件交对应CLI或认证HTTP下载。

### 处理状态、失败重试与同步责任

网页中，在项目范围检索后点击“读取原文”，可查看内容版本、处理版本、格式、处理状态与原字节 SHA；展开“提取覆盖与当前文字位置”查看支持范围和当前文字对应的部件、工作表单元格或 PDF 页区域。选择命中表格并点击“读取命中默认窗口”，再按需指定行列；网页行列从 1 开始，结束行/列**包含在范围内**，与上述 CLI/API 的右端不含不同。点击单元格可看源位置及适用的隐藏表/行/列属性。窗口与必要表头合计超额时会报错，保留上一次已读取的表格。

点击“查看采集原件信息”核对保存字节，再用“下载采集原件”下载；合法空白文档没有正文命中，直接从对应项目的资料列表下载。旧 TXT/Markdown 若未保存原件，会显示未保存且不提供可用下载入口，仍可读取其已采集文本。Hub 原件下载沿用当前网页认证，请勿把凭据放到 URL。

已接收、正在处理、ready、partial、failed、空内容成功有不同含义。空内容成功只用于完成支持范围检查的真实空白。Word/Excel没有提取到支持文字、同时存在图片等未支持对象时显示failed；有可用文字时仍可检索该文字，并在coverage中列明排除项。partial保留支持范围内已完成的内容，同时列明具体缺页/区域/表格；failed不能解释成已完整搜索且没有内容。OCR文字明确标识识别结果可能有误，首版质量范围为清晰水平简体中文/英文印刷字。PDF优先直接解析已有可用文字，不为完整原生页重复OCR；强承诺表格为单页、水平文字、完整矩形网格且无跨行列合并的原生或清晰扫描表格。

files/library同时展示published_snapshot、latest_attempt、retry_target。首次失败时published为空，V/P均0；网页替换失败保留旧发布，同时显示新失败CID。恢复组件/配置后，从当前retry_target原样取得值，仅在创建端明确重处理：

~~~text
smm --db <独立档案> documents reprocess --document-id <ID> --capture-id <CID> --expected-attempt-id <AID> --expected-version <V> --expected-processing-version <P>
~~~

不从旧搜索结果猜CID或版本。新候选失败时只重试新CID；已失效CID/AID或采集授权拒绝。重试读取保存字节，不依赖重新打开源文件；来源被移除、后续刷新确认缺失等授权失效不能用旧缓存复活。成功才成套发布新原件、文本、表格、覆盖和定位；新版本发布后旧引用拒绝，重新检索取得新引用。不提供历史全文入口。

本机项目文档同步仍默认关闭，沿用007按项目选择。允许后上传准确原件及本机已处理结果，Hub直接建索引，不重解析、不OCR。Hub自有项目的处理在Hub完成。项目创建端始终负责添加、删除、更新和重新处理，关联项目不授予另一端管理权。原件上限20MiB，新增格式通过分块上传；资源超限或缺组件要按错误处理，不能把半成品显示为成功。

同档案未发布暂存总量为256MiB。未提交的上传自创建满24小时后过期；再次接收新内容时释放其预约及没有活跃上传共用的分块。旧上传身份继续明确报过期，须用新的提交身份重新传输。已提交且仍有资格的失败候选、等待任务和已发布原件不按此期限删除，不能通过淘汰它们为新上传腾出容量。

首版不支持图片文件、.doc/.xls/.docm/.xlsm、宏执行、公式重算或密码文件解密，不调用外部模型。Excel含隐藏/veryHidden区域；公式和文件缓存值分别展示，无缓存标missing，已有缓存新鲜度unknown。DOCX不保证稳定排版页码；图片、图表、SmartArt等不做语义理解。具体支持/限制见[008规格](changes/008-document-format-support/spec.md)，验收范围见[实施计划](changes/008-document-format-support/plan.md)与[脱敏证据](changes/008-document-format-support/evidence/)。普通CI通过不等于各OS/原生服务全部验收完成。


## 多台电脑共用汇总档案

汇总端通过下面的包管理流程部署，也可在自行管理进程时运行 `smm-hub serve-hub`。汇总端使用独立数据库，远程连接使用 HTTPS。连接凭证允许上传和搜索汇总档案，应发给有权访问这些对话的使用者。

在每台电脑上安装新版 Skill。将管理员提供的凭证文件存到该账户的 `~/.local/share/smm-local/hub-token`，或在配置时告诉 Agent 文件路径。然后说「把这台电脑叫出差笔记本，汇总地址是 https://smm.example.net:8770」。汇总电脑若也要上传自己的本机对话，同样配置一次。

包含 005 的版本连不上汇总电脑时，Skill 会说明实际覆盖范围：按 A 项目查询只查本机 A；全项目查询才查本机全部。网络恢复后，后台会补传未确认的记录，搜索重新覆盖汇总档案。引用会注明来源电脑、Agent、原始会话 ID 和消息位置。

### 通过包管理器部署汇总端

管理员通过 uv 从 PyPI 安装独立的 `smm-hub` 包。

```sh
uv tool install smm-hub==0.4.0
smm-hub hub setup
```

向导询问客户端可访问的 HTTPS 地址、证书和私钥，例如 `https://hub.example.net:8770`。在 Linux 用户服务下使用 1024 以上的监听端口。它会复制 TLS 文件、生成连接凭证、准备数据库、注册系统服务并检查 HTTPS。私有 CA 可通过 `--ca-file` 提供，并应配置到客户端 Python 的信任链。指定全部参数可无交互部署。Windows 需要以管理员身份运行终端，并将 uv 工具环境和基础 Python 安装在 LocalService 可读取和执行的目录（例如管理员管理的 ProgramData 下），macOS 在注册系统级 launchd 服务时会请求 sudo，Linux 使用可在启动时运行的 systemd 用户服务。

```sh
smm-hub hub status
smm-hub hub disable
smm-hub hub enable
smm-hub hub upgrade
```

升级命令调用 uv 并保留地址、凭证和数据库，升级前保存 SQLite 备份。保留包索引中的旧版本，以便升级失败时恢复。启用中的服务在升级后会重新启动并检查 HTTPS。使用自定义 uv 安装环境时，从同一个账户和环境运行升级。使用 `--version` 可显式切换包索引中的发行版本。Windows 向导为监听端口配置仅限本地子网的入站防火墙规则。

已通过旧版 `smm-local` 部署汇总端时，先记下原来的数据目录和启停状态，安装 `smm-hub`，然后用旧命令停用旧服务。在原数据目录运行 `smm-hub hub --state-dir <原数据目录> enable` 接管原服务。原服务需要保持停用时，直接保留停用状态，日后再用新命令启用。两套命令使用同一份汇总端状态文件和数据库。

### 从 VibeInsight 同步对话

先用上一节的 `smm-hub hub setup` 配置汇总服务。在运行汇总服务的电脑上安装 PostgreSQL 客户端 `psql`，让运行汇总服务的系统账户可执行它。用 VibeInsight 数据库的只读账户配置连接。管理命令会验证读取权限，并提示输入密码。若服务环境找不到客户端，可用 `--psql` 指定绝对路径。

向 VibeInsight 数据库维护者取得 PostgreSQL 主机、端口、数据库名及只读账户，确认该账户可以读取的项目均获准归档到本 Hub。当前适配器读取 `fact_events` 的 `id`、`created_at`、`user_id`、`platform_code`、`session_id`、`trace_id`、`event_type`、`event_timestamp`、`message`、`repo_hostname`、`repo_port`、`repo_path` 字段。数据库维护者需确认部署使用这套事件结构，并授予所需读取权限。连接密码在命令提示中输入。

```sh
smm-hub hub vibeinsight configure --host db.example.net --port 5432 --database vibeinsight --user reader
smm-hub hub vibeinsight status
```

如果使用自定义状态目录，在 `hub` 后加 `--state-dir <状态目录>`，并与服务实际使用的目录保持一致。同步周期默认 300 秒，`--interval` 为不小于 1 的整数秒；它表示轮次调度间隔，不承诺整轮导入在该时间内完成。非法值或连接验证失败不会替换有效配置。

配置成功后，汇总服务自动拉取连接可读的全部项目，随后同步新会话及旧会话追加的轮次。服务重启会读取已保存的凭据和进度继续。状态命令显示最近成功时间和失败原因。每个项目从已提交位置向前回查 24 小时并去重；窗口外的迟到事件不保证发现。停服超过一天仍从持久位置继续，新发现项目会补齐更早的历史。源端原地改写历史消息而未产生新事件时，汇总档案保留已导入的原内容。

仅更换同一数据库目标的账号或密码会保留进度。数据库主机、端口或库名的配置组合变化时按不同来源导入，原归档保留；连接目标的别名不会自动合并。这与下文项目的仓库身份是两套标识。

终端配置成功后，还应在实际服务中检查 `vibeinsight status` 的最近成功时间，并通过检索和读取原文确认结果。macOS 的 launchd、Linux 的 systemd 用户服务以及 Windows 的 LocalService 可能有不同的 PATH 和文件访问权限。Windows 上 Python、psql 及其动态库需对 LocalService 可读可执行，专用凭据文件则限制为服务账户和管理员可读。出现依赖、权限或连接错误时，既有归档仍可检索；修复后服务自动重试。

### 自行管理 Hub 进程

自行管理进程时无需执行 `hub setup` 注册系统服务。准备独立状态目录、至少 32 字符的 ASCII Token 文件，以及客户端可访问的 HTTPS 地址、证书和私钥；Token 文件的原值由获授权客户端使用。按上一节取得数据库连接信息，然后在交互终端配置来源，密码由提示输入：

```sh
smm-hub hub --state-dir /path/to/hub-state vibeinsight configure --host db.example.net --database vibeinsight --user reader --psql /path/to/psql
smm-hub serve-hub --state-dir /path/to/hub-state --host 0.0.0.0 --port 8770 --token-file /path/to/hub-token --tls-cert /path/to/cert.pem --tls-key /path/to/key.pem
```

把示例路径换成运行账户可访问的本机路径；Windows 可使用带引号的绝对路径。`serve-hub --state-dir` 读取同目录的来源配置/凭据，并使用其中的 `smm-hub.sqlite3`。启动后自动同步，停止后用相同命令和目录重新启动，无需重输数据库密码。查看状态或管理项目时，仍使用 `hub --state-dir <同目录> ...`。

若同时提供顶层 `--db`，它必须指向该目录中的同一档案，否则启动被拒绝。使用不同服务管理方式时先停旧进程，避免两个进程并用同一档案和端口。旧的无 `--state-dir` 启动方式保留独立归档/检索行为；要读取保存的 VibeInsight 配置，需显式指定目录。

### 管理汇总端的项目关联

本机客户端至少完成一次与汇总端的项目登记后（005 不要求上传正文），运行 `smm-hub hub project list` 查看项目 ID、来源和设备名称。用以下命令管理关系，示例中的 `1` 和 `2` 换成汇总端给出的项目 ID。

```sh
smm-hub hub project links
smm-hub hub project link 1 2
smm-hub hub project unlink 1 2
```

在 Agent 中要求按当前项目搜索时，CLI 和 MCP 会查询汇总端保存的当前项目及直接关联项目。关系双向生效。命中 VibeInsight 对话时，可以用同一个读取入口取得原文和源事件位置。需扩大范围时，明确要求搜索所有项目。包含 005 的版本在汇总端断开时，项目查询只回退到本机所请求项目，并返回原因；全项目查询回退到本机全部。

### 项目改名与仓库身份变化

设备项目修改显示名后，Hub 沿用原项目身份及关联。VibeInsight 项目以仓库主机、端口和路径的组合标识身份，该标识变化时会发现一个新项目。旧项目的归档及关联继续保留，已同步的新项目对话可通过全局检索找到。

仓库身份变化后，维护者用 `smm-hub hub project list` 找到新仓库项目和相关设备项目，再用 `smm-hub hub project link <设备项目ID> <新仓库项目ID>` 建立关系，并按当前项目检索确认新对话已纳入。需要移除旧项目的关联时，用 `project unlink` 解除该关系，旧对话仍可全局检索。


## 项目上传与联合检索（005，尚未发布）

本节需要同时使用包含 005 的 Local 和 Hub。0.4.0 正式包不支持上传规则和新引用，更新 Skill 不等于更新运行组件。预览可按 README 建立独立源码开发环境，再运行 `python3 scripts/build_packages.py` 构建两个 wheel。用 `uv venv <任务环境>` 建环境，`uv pip install --python <环境中的Python> <本次wheel实际路径>` 安装；分别为 Local、Hub 建环境，不覆盖日常安装。macOS/Linux 的 Python 位于 `bin/python`，Windows 位于 `Scripts/python.exe`；CLI 同目录为 `smm`/`smm.exe` 或 `smm-hub`/`smm-hub.exe`。下文 `smm`、`smm-hub` 均指这些实际入口，`--db <独立档案>` 加在子命令之前。正式发布后才可按该发布版本替换包管理器命令中的版本号。

### 先取得项目，再选择上传范围

`configure-hub <地址> <本机名称> --token-file <文件路径>` 保存目标。新目标先只查询，自动登记设备与项目名称/类型/稳定键，不上传未允许会话的 ID、标题、路径、摘要或正文。查看 Web：`smm maintenance open`，进入「配置」的上传范围；命令行可运行：

```sh
smm projects
smm upload status
smm upload set --mode all
smm upload set --mode only --project-id 1 --project-id 2
smm upload set --mode except --project-id 2
smm upload set --mode none
```

这些是四个可替代的设置例子，请选择所需的一条。数字用 `smm projects` 返回的本机 ID 替换，可重复 `--project-id`；`only` 空名单不上传，`except` 空名单允许全部；`all/none` 不接受名单。每次保存完整替换规则。名称修改不改变稳定身份或名单。Hub 管理员运行 `smm-hub hub project list` 得到另一套 Hub ID，用于 Hub 关联命令。

`upload status` 显示当前地址/Hub 身份、设备、规则、本机序号、Hub 确认版本、已确认/未确认及在途消息。`needs_selection` 表示尚未选择；`pending` 表示本机已保存、Hub 尚未确认；`confirmed` 表示双方已确认；`conflict` 表示恢复或规则有差异，正文停止，需对账。传输进度由 `transfer_state` 单独显示暂停、待规则/对账、失败、在途待核实、正在补齐或已补齐；`allowed_pending_messages` 只统计当前允许范围内待确认的正文、项目归属或来源顺序，`transfer_problem` 保留最近同步失败，健康同步后清除。`last_transfer_attempt/last_transfer_success` 是最近传输轮次时间，不等同于规则确认时间。停止在本机立即阻止新派发，已派发的在途请求需等 Hub 确认，不能当成已撤回。Hub 已确认限制后拒绝旧版本或无版本正文。

停止不会删除 Hub 旧副本；其他电脑的副本与 VibeInsight 同步不受影响。重新允许后按消息身份和内容版本核对回执，补齐旧历史、停传新会话和追加轮次，重复同步不增加副本。全局暂停仍可保存/确认规则和最小项目资料，不会自动恢复正文导入或上传。来源插件仍只归档本机，上传规则当前覆盖 Codex/Claude Code。

### 明确全局会话与归属

缺失工作目录的会话保持待定，不能自动当成全局项目。Web「项目」可建立唯一全局项目、查看归属预览并确认；CLI：

```sh
smm project ensure-global
smm search "该会话的关键词" --local
smm project assign-conversation <本机会话ID> --project-id <目标本机项目ID>
smm project assign-conversation <同一会话ID> --project-id <同一项目ID> --confirm <刚返回的confirmation>
```

会话 ID 来自仅本机搜索；目标 ID 来自 `projects` 或 `ensure-global`。先检查预览中实际会话和新增允许范围再提交；规则或归属变化后需重新预览。全局项目与普通项目不能合并，按 A 检索不会自动包含全局项目。人工归属在源文件重放后保留。Web 路径映射、项目合并若扩大上传范围，同样须确认绑定的预览；Hub 已有副本不会随本机改归属而撤回。已上传会话从 A 改归属到 B 后，只有 B 获准上传，后续同步才为 Hub 已保存的同版本消息增加 B 归属；A 归属和旧引用保留，正文不重复保存。B 禁止上传时不发送这段会话的新归属或指纹。归属确认丢失会保持待确认并重试。

### 搜索与读取

```sh
smm search "关键词" --scope project --project-id <本机项目ID> --limit 5
smm search "关键词" --local --scope project --project-id <本机项目ID>
smm read --reference <某条结果的reference>
```

MCP 使用 `search_conversations`、`read_conversation(reference=...)`；Web 在「检索测试」选择默认联合或仅本机，沿具体结果的原文按钮读取。三者共用同一逻辑。配置 Hub 后，默认两端各按同一个 N 正常返回候选（1–50），在本机按完整命中消息重新计算 BM25，先归并可证明同源同版本的副本，再排序，最终最多 N 条。不同版本/轮次保留。不为排序发送本机候选正文；预览长度不影响得分或完整原文。

在线按 A 项目查 Hub 的直接一层 A/B/V，同时查询本机属于该共同集合的内容，包括未上传内容；本机自己的 A/D 关联只在显式仅本机时使用。Hub 范围解析失败只查本机 A；已有合法快照后 Hub 查询失败可保留该快照内的本机结果，说明缺失端点。全项目失败回退本机全部；本机失败而 Hub 可用则返回 Hub 并说明本机缺失；双方都失败报错。零命中不表示连接失败。

顶层 `archive_scope=combined` 不决定单条档案。每条引用绑定实际档案、消息及版本，只读检索时允许的消息集合；可用 `--start/--end` 进一步缩小，不能扩大到范围外内容。多来源组合引用可整体读取，指定区间时先选择其 `origin_references` 中一个来源。远端不可用不会读本机同号 ID。旧 `read ID`、`--hub-id`、`--hub-message-id` 继续可用；不要把联合结果的本机 ID 与顶层 Hub ID 拼接。原文改变或引用损坏时重新检索。

### 升级兼容与恢复备份

有可验证同 Hub 已上传状态的旧设备升级时保留全部允许；新接入或实际 Hub 身份变化需重新选择。只换地址/凭据且仍是同一个 Hub，不重置规则。新 Local 连接旧 Hub 可查询可核验的全项目候选，但不上传正文；按项目只回退本机所请求项目，明确提示能力不足。旧 Local 对尚未迁移设备仍可写；该设备一旦采用新策略，旧写被拒绝，旧读仍可用。

恢复前先运行该 Hub 原服务配置下的 `smm-hub hub status`（自定义状态目录时沿用原 `--state-dir`），从输出 `database` 的父目录确认实际 Hub 状态目录，并核对与待恢复服务相同。再用实际档案/状态目录输出清单并写入恢复保护：

```sh
smm --db <本机档案> upload prepare-restore
smm-hub hub --state-dir <实际Hub状态目录> prepare-restore
```

随后停止相应服务及采集、上传、同步任务，恢复一致性备份集。`do_not_restore`列出的当前保护记录不得用旧备份覆盖；其中任务临时目录和运行锁也不从备份恢复。文档持久目录包括已有`.documents`和`.document-snapshots`，不能只恢复数据库或只复制管理原件。数据库包括引用签名材料，配套 Hub 配置/凭据按输出的 `restore_files`/保留清单处理。自管 `serve-hub` 使用同一个实际状态目录。不能把运行中的 SQLite 主文件单独复制当成一致性备份；应停服务或使用 SQLite backup。

重启后先查看差异，查看本身不改变规则：

```sh
smm upload reconcile
smm upload reconcile --use hub
smm upload reconcile --use local --expected-hub-revision <刚查看的hub.revision> --expected-local-generation <刚查看的local.generation>
```

`--use local` 明确重新提交刚显示的本机规则，必须同时带刚查看差异输出中的 `hub.revision` 与 `local.generation`；少一个、任一已过期或调用期间本机规则又有修改，都拒绝且不覆盖当前规则，需重新查看。不能自动改用另一入口后来保存的本机规则。`--use hub` 明确采用调用时 Hub 当前规则，仍保护调用期间的本机新保存；也可提供 `--expected-local-generation` 绑定刚查看的本机代次。Web 两种对账按钮均绑定页面所显示的两端版本，过期需重新查看。恢复期间正文关闭；Hub 回到旧库会更换控制代次，原回执失效，明确对账后只补当前允许的缺失消息。手工连保护标记一起回滚不属于受支持恢复方式。
