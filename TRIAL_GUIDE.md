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

`upload status` 显示当前地址/Hub 身份、设备、规则、本机序号、Hub 确认版本、已确认/未确认及在途消息。`needs_selection` 表示尚未选择；`pending` 表示本机已保存、Hub 尚未确认；`confirmed` 表示双方已确认；`conflict` 表示恢复或规则有差异，正文停止，需对账。停止在本机立即阻止新派发，已派发的在途请求需等 Hub 确认，不能当成已撤回。Hub 已确认限制后拒绝旧版本或无版本正文。

停止不会删除 Hub 旧副本；其他电脑的副本与 VibeInsight 同步不受影响。重新允许后按消息身份和内容版本核对回执，补齐旧历史、停传新会话和追加轮次，重复同步不增加副本。全局暂停仍可保存/确认规则和最小项目资料，不会自动恢复正文导入或上传。来源插件仍只归档本机，上传规则当前覆盖 Codex/Claude Code。

### 明确全局会话与归属

缺失工作目录的会话保持待定，不能自动当成全局项目。Web「项目」可建立唯一全局项目、查看归属预览并确认；CLI：

```sh
smm project ensure-global
smm search "该会话的关键词" --local
smm project assign-conversation <本机会话ID> --project-id <目标本机项目ID>
smm project assign-conversation <同一会话ID> --project-id <同一项目ID> --confirm <刚返回的confirmation>
```

会话 ID 来自仅本机搜索；目标 ID 来自 `projects` 或 `ensure-global`。先检查预览中实际会话和新增允许范围再提交；规则或归属变化后需重新预览。全局项目与普通项目不能合并，按 A 检索不会自动包含全局项目。人工归属在源文件重放后保留。Web 路径映射、项目合并若扩大上传范围，同样须确认绑定的预览；Hub 已有副本不会随本机改归属而撤回。

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

随后停止相应服务，恢复一致性备份集，保留输出 `do_not_restore` 中的保护与锁文件，不能用旧备份覆盖它们。数据库包括引用签名材料，配套 Hub 配置/凭据按输出的 `restore_files`/保留清单处理。自管 `serve-hub` 使用同一个实际状态目录。不能把运行中的 SQLite 主文件单独复制当成一致性备份；应停服务或使用 SQLite backup。

重启后先查看差异，查看本身不改变规则：

```sh
smm upload reconcile
smm upload reconcile --use hub
smm upload reconcile --use local --expected-hub-revision <刚查看的hub.revision>
```

`--use hub` 明确采用当前 Hub 规则；`--use local` 明确重新提交本机规则，必须带刚查看的版本，过期则重新查看，不能覆盖另一入口的新修改。Web 配置页也可查看并选择对账。恢复期间正文关闭；Hub 回到旧库会更换控制代次，原回执失效，明确对账后只补当前允许的缺失消息。手工连保护标记一起回滚不属于受支持恢复方式。
