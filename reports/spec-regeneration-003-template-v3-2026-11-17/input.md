# 规格起草资料

## 任务

根据单独提供的正式 SPEC 模板、已确认意图、补充决定及项目资料，重新起草供维护者审阅的规格。
直接输出规格正文，以提供的资料为准。不要执行测试或修改文件；必要信息缺失时标明待确认。
不要将设计说明或已有使用说明当作已执行的验收结果。

## 已确认意图

# 意图：在汇总端同步 VibeInsight 对话，并按关联项目检索

## 现有问题

用户在 SMM 中按当前项目检索历史时，汇总端可以提供多台设备上传的对话。VibeInsight 另行收集的对话缺少自动进入 SMM 汇总端的入口。即使两边的对话在讨论同一件事，用户仍需要另外去 VibeInsight 查找。

与当前项目相关的对话可能归在另一台电脑上传的项目中，也可能归在一个或多个 VibeInsight 项目中。项目名称、路径和仓库划分可能不同。用户需要在汇总端明确指定哪些项目要一起检索。

## 受影响的用户

已接入 SMM 汇总端，希望检索当前项目及其他电脑或 VibeInsight 上相关项目的用户。还包括负责配置来源、同步范围和项目关联的汇总端维护者。

## 期望结果

- 汇总端自动从 VibeInsight 拉取配置范围内的历史对话，随后持续同步新增或更新的对话。用户在现有 SMM 检索入口即可搜索已同步的对话，并打开命中消息的原文。
- 汇总端维护者可以建立、查看和调整项目关联。电脑上传的项目可以关联另一台电脑上传的项目，也可以关联一个或多个 VibeInsight 项目。
- 例如，电脑甲上传项目 A，电脑乙上传项目 B，汇总端从 VibeInsight 同步项目 C、D。在汇总端把 A 分别与 B、C、D 关联后，本机按 A 检索时，会在 A 原有的检索范围上加入 B、C、D 中已归档的对话。解除 A 与 C 的关联后，A 的关联检索范围只包含 B、D。
- 检索结果显示命中对话的来源和所属项目，并提供原始会话和消息位置。

## 范围与约束

- 汇总端中的项目有两类来源：各台电脑上传的对话，以及汇总端从 VibeInsight 拉取的对话。本地使用者通过 SMM 现有检索入口访问。
- 项目关联在汇总端统一配置，用于扩展检索范围。以已保存的直接关联为准，各来源的对话保留原项目归属。
- 首版沿用汇总端当前的单用户访问模式。汇总端只从 VibeInsight 同步获准纳入的项目。

## 待确认问题

无。

## 已确认的补充决定

以下整理自维护者已确认的需求及设计，保留本次交付范围，不是旧验收条目的复制：

- Hub 维护者通过 Hub CLI 配置 VibeInsight 连接、只读凭据、同步周期，并查看最近成功时间、失败原因和脱敏状态。
- 验证连接及所需读取权限成功后才替换有效配置。凭据跨服务重启保留，重启无需重新输入；更换同一来源的凭据沿用进度。
- 拉取连接可读取的全部项目，不设项目同步名单或按项目移出等额外操作。首次发现项目即使历史早于已有进度也补齐。
- 支持新会话与旧会话新追加的轮次，原汇总会话标识及来源顺序保持；重复事件按来源会话及消息标识去重。
- 失败时此前归档继续可检索读取，报告失败，恢复后重试未提交记录。进度不越过未成功归档数据。
- 项目关联存于 Hub，设备—设备、设备—VibeInsight 两类关系均支持。双向、仅直接一层、重复建立只有一条；解除不删除归档，解除后的对话仍可全局查找。
- 项目列表区分来源、电脑、稳定项目身份及同名项目。本机端补传项目归属与稳定身份，包括无新增消息的旧历史归属补传。
- 设备项目改显示名保留身份及关联。VibeInsight 仓库主机、端口、路径的组合身份变化形成新项目，由维护者重新关联；旧归档与旧关联保留，新项目同步后全局可查。
- 本机 CLI/MCP 的在线项目查询携带当前项目身份，范围和结果标明汇总端及生效项目；全局检索覆盖两类来源。
- 命中提供来源、所属项目、原会话和消息位置；CLI/MCP 可沿用 Hub 与消息引用精确读回原文，旧引用继续可用。
- Hub 不可用时按现有行为回退本机所有项目并返回回退原因；显式本机查询沿用本机项目关系。旧客户端无项目范围的请求仍全局检索。
- 首版沿用单用户模式。没有新增事件的历史消息原地改写不负责发现，保留已归档的旧内容。
- 本机 Web 的功能扩展不在本次范围；它管理本机档案/关联，在线 Hub 检索的关联由 Hub CLI 统一管理。

## 已确认的设计资料

- 来源通过 Hub 服务调用外部 PostgreSQL 客户端 `psql`，读取 VibeInsight `fact_events` 事件；仅执行只读查询。
- 连接地址、周期、启用状态存配置；秘密值存 Hub 服务状态目录的专用凭据文件，以操作系统权限限制访问。运行账号读取，命令输出、日志和对话数据库不含秘密原值。
- 进度保存在 Hub 数据库。每轮先固定上界，按批次归档；归档和进度一同提交，重启从已提交位置继续。
- `created_at` 与事件 `id` 组成续跑位置，同时间按 `id` 区分；每轮回看近期记录以覆盖常见延迟提交，重复读取按来源标识去重。
- 本机端、Hub 独立打包；本机 CLI/MCP 共享归档与检索逻辑，连接 Hub 后上传项目归属并在线检索。具体实施、机器、命令和测试步骤后续由 PLAN 落实。


## 现有项目资料摘录

### 模块职责

来源 `d2dee18fcc050dcf20bd4108429975477399db8d:AGENTS.md`；下列为原文及行号，不是测试结果：

```text
3: ## 模块与关系
4: 
5: - **本机端**（`src/smm_local/`）导入各来源的对话，负责本机归档、项目关联和检索。
6:   CLI、MCP 和 Web UI 共用本机档案及检索逻辑。配置汇总服务后，本机端向 Hub 上传
7:   可汇总的记录，并通过 Hub 执行跨设备检索。
8: - **多机汇总端**（`src/smm_hub/`）接收多台设备上传的记录，提供跨设备检索。
9:   Hub 不可用时，本机端可回退到本机档案。
10: - **检索技能**（`skills/smm-search/`）指导 Agent 通过本机端的 MCP 或 CLI
11:   搜索历史对话、读取原文和维护同步。
12: - **来源适配技能**（`skills/smm-source-adapter/`）指导当前 Agent 为自身实现本机来源插件，
13:   使 SMM 本机端能够导入该 Agent 的对话记录。
14: 
15: ## 开发流程
16: 
17: 本项目采用 Anthropic 的 AI-native SDLC 实践。每项变更在
```

### 本机端安装与使用

来源 `d2dee18fcc050dcf20bd4108429975477399db8d:TRIAL_GUIDE.md`；下列为原文及行号，不是测试结果：

```text
9: ### 升级本机端
10: 
11: 通过搜索 Skill 安装过旧版时，更新整个 `smm-search` Skill 文件夹，并在 `~/.local/share/smm-local/install.json` 中找到 `package_environment`。用该环境的 Python 执行下面三条命令。macOS 和 Linux 的解释器位于环境下的 `bin/python`，Windows 位于 `Scripts/python.exe`。
12: 
13: ```text
14: <安装环境的 Python> -m smm_local.cli stop-on-demand
15: <安装环境的 Python> -m pip install --upgrade smm-local==0.3.0
16: <安装环境的 Python> -m smm_local.installation install
17: ```
18: 
19: 升级沿用安装清单中的档案路径。升级后新开 Agent 会话，查看 SMM 同步状态。从源码安装的用户可从新版本源码重新运行 `scripts/install.py`。
20: 
21: ## 2. 在 Agent 中管理同步
22: 
23: 安装完成后，在新的 Codex 或 Claude Code 会话中直接说：
24: 
25: - 「查看 SMM 同步状态」看来源计数、上次同步和导入错误。
26: - 「打开 SMM 状态页」打开本机页面。
27: - 「现在同步一次我的对话」立即导入；初次同步可能需要一段时间。
28: - 「暂停自动同步」或「恢复自动同步」管理后台导入。暂停后仍可查已有档案、查看状态页或明确同步一次；服务或电脑重启后暂停设置仍有效。
29: 
30: 如果服务还没运行，Agent 会在需要时启动它。macOS 默认也会在登录后启动服务。
31: 
32: Codex 默认读取 `~/.codex/sessions`，Claude Code 默认读取 `~/.claude/projects`。若历史放在别处，到 Web「配置」设置实际目录，再点「立即同步」。同一个系统账户下，两个 Agent 共用一个同步服务和一个档案，默认位于 `~/.local/share/smm-local/smm.sqlite3`。在任一 Agent 中暂停或恢复，另一边会看到同一个状态。
```

### Hub 部署与服务运行方式

来源 `d2dee18fcc050dcf20bd4108429975477399db8d:TRIAL_GUIDE.md`；下列为原文及行号，不是测试结果：

```text
56: ## 多台电脑共用汇总档案
57: 
58: 汇总端通过下面的包管理流程部署，也可在自行管理进程时运行 `smm-hub serve-hub`。汇总端使用独立数据库，远程连接使用 HTTPS。连接凭证允许上传和搜索汇总档案，应发给有权访问这些对话的使用者。
59: 
60: 在每台电脑上安装新版 Skill。将管理员提供的凭证文件存到该账户的 `~/.local/share/smm-local/hub-token`，或在配置时告诉 Agent 文件路径。然后说「把这台电脑叫出差笔记本，汇总地址是 https://smm.example.net:8770」。汇总电脑若也要上传自己的本机对话，同样配置一次。
61: 
62: 连不上汇总电脑时，Skill 会说明当前只搜本机，范围包含本机已导入的所有 Agent。网络恢复后，后台会补传未确认的记录，搜索重新覆盖汇总档案。引用会注明来源电脑、Agent、原始会话 ID 和消息位置。
63: 
64: ### 通过包管理器部署汇总端
65: 
66: 管理员通过 uv 从 PyPI 安装独立的 `smm-hub` 包。
67: 
68: ```sh
69: uv tool install smm-hub==0.3.0
70: smm-hub hub setup
71: ```
72: 
73: 向导询问客户端可访问的 HTTPS 地址、证书和私钥，例如 `https://hub.example.net:8770`。在 Linux 用户服务下使用 1024 以上的监听端口。它会复制 TLS 文件、生成连接凭证、准备数据库、注册系统服务并检查 HTTPS。私有 CA 可通过 `--ca-file` 提供，并应配置到客户端 Python 的信任链。指定全部参数可无交互部署。Windows 需要以管理员身份运行终端，并将 uv 工具环境和基础 Python 安装在 LocalService 可读取和执行的目录（例如管理员管理的 ProgramData 下），macOS 在注册系统级 launchd 服务时会请求 sudo，Linux 使用可在启动时运行的 systemd 用户服务。
74: 
75: ```sh
76: smm-hub hub status
77: smm-hub hub disable
78: smm-hub hub enable
79: smm-hub hub upgrade
80: ```
81: 
82: 升级命令调用 uv 并保留地址、凭证和数据库，升级前保存 SQLite 备份。保留包索引中的旧版本，以便升级失败时恢复。启用中的服务在升级后会重新启动并检查 HTTPS。使用自定义 uv 安装环境时，从同一个账户和环境运行升级。使用 `--version` 可显式切换包索引中的发行版本。Windows 向导为监听端口配置仅限本地子网的入站防火墙规则。
83: 
84: 已通过旧版 `smm-local` 部署汇总端时，先记下原来的数据目录和启停状态，安装 `smm-hub`，然后用旧命令停用旧服务。在原数据目录运行 `smm-hub hub --state-dir <原数据目录> enable` 接管原服务。原服务需要保持停用时，直接保留停用状态，日后再用新命令启用。两套命令使用同一份汇总端状态文件和数据库。
```

### 既有服务的身份与启动配置

来源 `d2dee18fcc050dcf20bd4108429975477399db8d:src/smm_hub/hub_os.py`；下列为原文及行号，不是测试结果：

```python
39:     def preflight(self):
40:         if sys.platform == "darwin":
41:             # Authenticate on the terminal before commands whose output is captured.
42:             if not subprocess.run(["sudo", "-v"]).returncode == 0:
43:                 raise RuntimeError("注册 macOS 汇总服务需要管理员权限")
44:         elif sys.platform == "linux":
45:             import pwd
46:             import os
47:             self.user = pwd.getpwuid(os.getuid()).pw_name
48:             command("systemctl", "--user", "show-environment")
49:             result = command("loginctl", "show-user", self.user, "-p", "Linger", "--value")
50:             if result.stdout.strip() != "yes":
51:                 command("loginctl", "enable-linger", self.user)
52:         elif sys.platform == "win32":
53:             import ctypes
54:             if not ctypes.windll.shell32.IsUserAnAdmin():
55:                 raise RuntimeError("请在管理员终端中配置 Windows 汇总服务")
56:         else:
57:             raise RuntimeError("汇总服务管理支持 Linux、Windows 和 macOS")
58: 
59:     def protect_state(self):
60:         if sys.platform == "win32":
61:             # The archive and private key are readable only by administrators and the service account.
62:             command("icacls.exe", str(self.root), "/inheritance:r", "/grant:r",
63:                     "*S-1-5-32-544:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-19:(OI)(CI)M")
64: 
65:     def new_runtime_directory(self):
66:         import os
67: 
80:         if sys.platform == "linux":
81:             directory = Path.home() / ".config/systemd/user"
82:             directory.mkdir(parents=True, exist_ok=True)
83:             executable = " ".join(map(systemd_arg, self.args))
84:             (directory / self.unit).write_text(
85:                 "[Unit]\nDescription=SMM aggregation server\n"
86:                 f"[Service]\nExecStart={executable}\nRestart=on-failure\nRestartSec=2s\nUMask=0077\n"
87:                 "[Install]\nWantedBy=default.target\n", encoding="utf-8")
88:             command("systemctl", "--user", "daemon-reload")
89:             command("systemctl", "--user", "enable", self.unit)
90:         elif sys.platform == "darwin":
91:             import os
92:             import pwd
93:             user = pwd.getpwuid(os.getuid()).pw_name
94:             if not os.getuid():
95:                 raise ValueError("请以普通管理员账户运行 smm-hub，SMM 会单独请求 sudo")
96:             data = {"Label": self.launch_label, "ProgramArguments": self.args, "UserName": user,
97:                     "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False},
98:                     "StandardErrorPath": str(self.root / "launchd-error.log")}
99:             with tempfile.NamedTemporaryFile() as file:
100:                 file.write(plistlib.dumps(data))
101:                 file.flush()
102:                 command("sudo", "install", "-o", "root", "-g", "wheel", "-m", "644", file.name, str(self.plist))
107:     def install_windows(self, config):
108:         runtime = Path(config.get("python", sys.executable))
109:         site = runtime.parent.parent / "Lib" / "site-packages"
110:         base = config.get("base_python") or str(Path(sys.base_prefix) / "python.exe")
111:         # The SCM starts the actual interpreter directly. The venv redirector
112:         # spawns a separate process before the service can register.
113:         worker = ("import sys; "
114:                   f"sys.path.insert(0, {str(site)!r}); "
115:                   "from smm_hub.windows_service import boot; boot()")
116:         image = subprocess.list2cmdline([base, "-I", "-S", "-c", worker, self.name, str(self.root)])
117:         present = command("sc.exe", "query", self.name, check=False).returncode == 0
118:         action = "config" if present else "create"
119:         command("sc.exe", action, self.name, "binPath=", image, "start=", "auto",
120:                 "obj=", r"NT AUTHORITY\LocalService", "DisplayName=", "SMM aggregation server")
121:         command("sc.exe", "failure", self.name, "reset=", "86400", "actions=", "restart/3000/restart/5000")
122:         command("netsh.exe", "advfirewall", "firewall", "delete", "rule", f"name={self.name}", check=False)
123:         command("netsh.exe", "advfirewall", "firewall", "add", "rule", f"name={self.name}",
124:                 "dir=in", "action=allow", "protocol=TCP", f"localport={config['port']}",
125:                 "remoteip=localsubnet", "profile=any")
126: 
```

### 当前来源配置和关联入口

来源 `cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd:TRIAL_GUIDE.md`；下列为原文及行号，不是测试结果：

```text
88: ### 从 VibeInsight 同步对话
89: 
90: 先用上一节的 `smm-hub hub setup` 配置汇总服务。在运行汇总服务的电脑上安装 PostgreSQL 客户端 `psql`，让运行汇总服务的系统账户可执行它。用 VibeInsight 数据库的只读账户配置连接。管理命令会验证读取权限，并提示输入密码。若服务环境找不到客户端，可用 `--psql` 指定绝对路径。
91: 
92: 向 VibeInsight 数据库维护者取得 PostgreSQL 主机、端口、数据库名及只读账户，确认该账户可以读取的项目均获准归档到本 Hub。当前适配器读取 `fact_events` 的 `id`、`created_at`、`user_id`、`platform_code`、`session_id`、`trace_id`、`event_type`、`event_timestamp`、`message`、`repo_hostname`、`repo_port`、`repo_path` 字段。数据库维护者需确认部署使用这套事件结构，并授予所需读取权限。连接密码在命令提示中输入。
93: 
94: ```sh
95: smm-hub hub vibeinsight configure --host db.example.net --port 5432 --database vibeinsight --user reader
96: smm-hub hub vibeinsight status
97: ```
98: 
99: 如果使用自定义状态目录，在 `hub` 后加 `--state-dir <状态目录>`。同步周期默认 300 秒，可用 `--interval` 调整。启用同步后，汇总服务拉取连接可读的全部项目，随后同步新会话及旧会话追加的轮次。服务重启会读取已保存的凭据和进度继续。状态命令显示最近成功时间和失败原因。源端原地改写历史消息而未产生新事件时，汇总档案保留已导入的原内容。
100: 
101: ### 管理汇总端的项目关联
102: 
103: 本机客户端至少完成一次与汇总端的同步后，运行 `smm-hub hub project list` 查看项目 ID、来源和设备名称。用以下命令管理关系，示例中的 `1` 和 `2` 换成汇总端给出的项目 ID。
104: 
105: ```sh
106: smm-hub hub project links
107: smm-hub hub project link 1 2
108: smm-hub hub project unlink 1 2
109: ```
110: 
111: 在 Agent 中要求按当前项目搜索时，CLI 和 MCP 会查询汇总端保存的当前项目及直接关联项目。关系双向生效。命中 VibeInsight 对话时，可以用同一个读取入口取得原文和源事件位置。需扩大范围时，明确要求搜索所有项目。汇总端断开时，CLI 和 MCP 回退到本机所有项目，并返回回退原因。
112: 
113: ### 项目改名与仓库身份变化
114: 
115: 设备项目修改显示名后，Hub 沿用原项目身份及关联。VibeInsight 项目以仓库主机、端口和路径的组合标识身份，该标识变化时会发现一个新项目。旧项目的归档及关联继续保留，已同步的新项目对话可通过全局检索找到。
116: 
117: 仓库身份变化后，维护者用 `smm-hub hub project list` 找到新仓库项目和相关设备项目，再用 `smm-hub hub project link <设备项目ID> <新仓库项目ID>` 建立关系，并按当前项目检索确认新对话已纳入。需要移除旧项目的关联时，用 `project unlink` 解除该关系，旧对话仍可全局检索。
```

