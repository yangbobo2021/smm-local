# SMM Local 同事试用指南

SMM 在本机保存 Codex 与 Claude Code 的可见对话文本，提供项目范围 BM25 搜索。首次导入后，源 Agent 删除会话不会删除 SMM 档案。SMM 没有云端服务；Agent 读取的片段仍可能进入该 Agent 所配置的模型服务，请遵守公司的数据使用规则。

## 1. 安装

按 [README 的快速开始](README.md#单台电脑快速开始)安装 `smm-search`。首次使用需要网络和 Agent 的本机执行权限。Skill 会使用已有的 Python，或自动准备用户级 Python。

## 2. 在 Agent 中管理同步

安装完成后，在新的 Codex 或 Claude Code 会话中直接说：

- 「查看 SMM 同步状态」看来源计数、上次同步和导入错误。
- 「打开 SMM 状态页」打开本机页面。
- 「现在同步一次我的对话」立即导入；初次同步可能需要一段时间。
- 「暂停自动同步」或「恢复自动同步」管理后台导入。暂停后仍可查已有档案、查看状态页或明确同步一次；服务或电脑重启后暂停设置仍有效。

如果服务还没运行，Agent 会在需要时启动它。macOS 默认也会在登录后启动服务。

Codex 默认读取 `~/.codex/sessions`，Claude Code 默认读取 `~/.claude/projects`。若历史放在别处，到 Web「配置」设置实际目录，再点「立即同步」。同一个系统账户下，两个 Agent 共用一个同步服务和一个档案，默认位于 `~/.local/share/smm-local/smm.sqlite3`。在任一 Agent 中暂停或恢复，另一边会看到同一个状态。

## 3. 实际提问

在新的 Codex 或 Claude Code 会话中问一个**必须依靠旧对话**才能回答的问题，例如：“我以前对某项目的上线回滚提出过什么要求？请查原始对话并引用来源会话和消息位置。”Agent 应调用 `smm-local` 的检索及读取工具，答案应能在 Web「检索测试」中复核。首次尝试可明确说“请使用 SMM 搜索过去对话”，再试不点名工具的自然提问。

项目检索默认只包含当前项目及直接关联项目。跨项目提问时，让 Agent 使用全局范围；也可以在 Web「项目」中建立关联。检索结果保留来源、时间和命中位置；每条命中消息默认只预览前 600 字，较长消息会标明省略。需要依据后半段内容作答时，让 Agent 调用 `read_conversation` 读取该轮完整原文。命中一段对话不等于其中每句都是事实，须读原文核对。

## 4. 遇到问题

- 两个来源都显示不可用：让 Agent 打开状态页，在「配置」中检查会话目录。
- 首次安装依赖下载失败：让 Agent 查看具体错误，恢复网络后在会话里重试原请求。
- Claude Code 报 401 或未登录：先检查 Claude Code 自己的模型登录。
- Agent 找不到 SMM：检查 Skill 文件夹是否完整放在所用 Agent 的技能目录，随后新开会话。
- 服务启动失败：让 Agent 检查返回的日志路径并说明实际原因。
- 搜不到预期对话：先确认导入计数和项目范围，再用显著的项目名、人物名或事件词重试。
- Agent 给出没有原文支持的回答：要求它提供来源会话和位置，在 Web 读取原文；请把问题、实际结果与期望来源反馈给试用负责人。

## 5. 结束试用

先从各 Agent 的 Skill 目录移除自己放入的 `smm-search` 文件夹。若也要卸载本机组件，可请 Agent 读取 `~/.local/share/smm-local/install.json`，用其中 `package_environment` 指向的 Python 运行 `-m smm_local.installation uninstall`。从源码安装的旧版仍可从 `project_root` 运行 `scripts/uninstall.py`，以停用服务并移除 MCP 注册。卸载会保留数据库。

请在试用反馈中记录：安装是否独立完成、一次自己的历史问题是否找对原文、一次跨 Agent 搜索是否找对、哪一步费时或困惑。不要把私人对话原文发到公共 issue。

## 多台电脑共用汇总档案

汇总端通过下面的包管理流程部署，也可在自行管理进程时运行 `smm-hub serve-hub`。汇总端使用独立数据库，远程连接使用 HTTPS。连接凭证允许上传和搜索汇总档案，应发给有权访问这些对话的使用者。

在每台电脑上安装新版 Skill。将管理员提供的凭证文件存到该账户的 `~/.local/share/smm-local/hub-token`，或在配置时告诉 Agent 文件路径。然后说「把这台电脑叫出差笔记本，汇总地址是 https://smm.example.net:8770」。汇总电脑若也要上传自己的本机对话，同样配置一次。

连不上汇总电脑时，Skill 会说明当前只搜本机，范围包含本机已导入的所有 Agent。网络恢复后，后台会补传未确认的记录，搜索重新覆盖汇总档案。引用会注明来源电脑、Agent、原始会话 ID 和消息位置。

### 通过包管理器部署汇总端

管理员通过 uv 从 PyPI 安装独立的 `smm-hub` 包。命令固定到当前试用候选版。

```sh
uv tool install smm-hub==0.2.0rc16
smm-hub hub setup
```

向导询问客户端可访问的 HTTPS 地址、证书和私钥，例如 `https://hub.example.net:8770`。在 Linux 用户服务下使用 1024 以上的监听端口。它会复制 TLS 文件、生成连接凭证、准备数据库、注册系统服务并检查 HTTPS。私有 CA 可通过 `--ca-file` 提供，并应配置到客户端 Python 的信任链。指定全部参数可无交互部署。Windows 需要以管理员身份运行终端，并将 uv 工具环境和基础 Python 安装在 LocalService 可读取和执行的目录（例如管理员管理的 ProgramData 下），macOS 在注册系统级 launchd 服务时会请求 sudo，Linux 使用可在启动时运行的 systemd 用户服务。

```sh
smm-hub hub status
smm-hub hub disable
smm-hub hub enable
smm-hub hub upgrade --prerelease
```

升级命令调用 uv 并保留地址、凭证和数据库，升级前保存 SQLite 备份。保留包索引中的旧版本，以便升级失败时恢复。启用中的服务在升级后会重新启动并检查 HTTPS。使用自定义 uv 安装环境时，从同一个账户和环境运行升级。使用 `--version` 可显式切换包索引中的发行版本。Windows 向导为监听端口配置仅限本地子网的入站防火墙规则。

已通过旧版 `smm-local` 部署汇总端时，先记下原来的数据目录和启停状态，安装 `smm-hub`，然后用旧命令停用旧服务。在原数据目录运行 `smm-hub hub --state-dir <原数据目录> enable` 接管原服务。原服务需要保持停用时，直接保留停用状态，日后再用新命令启用。两套命令使用同一份汇总端状态文件和数据库。
