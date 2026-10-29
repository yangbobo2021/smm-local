# SMM Local 同事试用指南

SMM 在本机保存 Codex 与 Claude Code 的可见对话文本，提供项目范围 BM25 搜索。首次导入后，源 Agent 删除会话不会删除 SMM 档案。SMM 没有云端服务；Agent 读取的片段仍可能进入该 Agent 所配置的模型服务，请遵守公司的数据使用规则。

## 1. 安装

适用 macOS，需 Python 3.11+、网络可安装 Python 依赖，以及已安装 Codex CLI 或 Claude Code CLI。把发行包解压到**打算长期保留的位置**，在该目录执行：

```bash
python3 scripts/install.py
```

安装器建立 `.venv`、用户级 Skill 和 MCP，启动仅监听 `127.0.0.1:8766` 的服务。它只配置已安装的 Agent。若移动发行目录，请在新位置再次执行同一命令。不会自动删除旧档案。

## 2. 确认能用

```bash
~/.local/bin/smm doctor
~/.local/bin/smm sync
```

`doctor` 中 `ready` 应为 `true`，至少一个 `sources` 为 `true`，已安装 Agent 的 `mcp` 和 `skills` 为 `true`，`service_ok` 为 `true`。这只确认本机接线正常；`model_auth_checked=false` 表示还需用一次真实新会话确认 Agent 自己的模型登录。打开 <http://127.0.0.1:8766>，查看来源计数、项目和导入错误。首次导入可能需要一些时间；只有本机已有的对话会出现。

Codex 默认读取 `~/.codex/sessions`，Claude Code 默认读取 `~/.claude/projects`。若历史放在别处，到 Web「配置」设置实际目录，再点「立即同步」。只使用一种 Agent 也可以。数据库位于 `~/.local/share/smm-local/smm.sqlite3`；请按公司敏感信息规则保护这份本机文件。

## 3. 实际提问

在新的 Codex 或 Claude Code 会话中问一个**必须依靠旧对话**才能回答的问题，例如：“我以前对某项目的上线回滚提出过什么要求？请查原始对话并引用来源会话和消息位置。”Agent 应调用 `smm-local` 的检索及读取工具，答案应能在 Web「检索测试」中复核。首次尝试可明确说“请使用 SMM 搜索过去对话”，再试不点名工具的自然提问。

项目检索默认只包含当前项目及直接关联项目。跨项目提问时，让 Agent 使用全局范围；也可以在 Web「项目」中建立关联。检索结果保留来源、时间和命中位置；命中一段对话不等于其中每句都是事实，须读原文核对。

## 4. 遇到问题

- `sources` 都为 `false`：检查对应 Agent 的会话目录；使用 Web 配置实际位置。
- 首次安装依赖下载很慢：按公司规定配置可用的 Python 包镜像（`PIP_INDEX_URL`），再运行同一安装命令；已保存的档案不会丢失。
- Claude Code 报 401 或未登录：先独立运行 `claude -p '回复 READY'` 确认自己的模型服务可用；这一步与 SMM MCP 接入是两项检查。
- `mcp` 为 `false`：在发行目录重新运行安装命令，然后新开 Agent 会话。
- `service_ok` 为 `false`：查看 `~/.local/share/smm-local/logs/stderr.log`，或手动运行 `~/.local/bin/smm serve`。
- 搜不到预期对话：先确认导入计数和项目范围，再用显著的项目名、人物名或事件词重试。
- Agent 给出没有原文支持的回答：要求它提供来源会话和位置，在 Web 读取原文；请把问题、实际结果与期望来源反馈给试用负责人。

## 5. 结束试用

在发行目录执行 `python3 scripts/uninstall.py` 停用服务并移除由 SMM 安装的 Skill 与 MCP；这**不会删除数据库**。需要删除历史档案时，再由本人手工删除 `~/.local/share/smm-local/smm.sqlite3` 及同目录的 `-wal`、`-shm` 文件。

请在试用反馈中记录：安装是否独立完成、一次自己的历史问题是否找对原文、一次跨 Agent 搜索是否找对、哪一步费时或困惑。不要把私人对话原文发到公共 issue。
