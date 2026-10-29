# SMM Local

本地 Codex 与 Claude Code 对话档案与项目范围检索。导入后保存独立副本：删除 Agent 源会话不会删除知识库中的记录。

同事试用请从 [安装与使用指南](TRIAL_GUIDE.md) 开始。`python3 scripts/install.py` 完成用户级 Skill/MCP 注册与本机服务，`~/.local/bin/smm doctor` 检查实际状态。

## 安装与启动

需要 Python 3.11+。

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/smm sync
.venv/bin/smm serve
```

Web UI 默认地址为 `http://127.0.0.1:8766`。首次同步会扫描 `~/.codex/sessions` 与 `~/.claude/projects`；可用 `SMM_CODEX_ROOT`、`SMM_CLAUDE_ROOT` 或 Web 配置覆盖。数据库默认保存在 `~/.local/share/smm-local/smm.sqlite3`，可用 `SMM_DB` 覆盖。服务运行时定期同步，也可在 Web UI 手动同步。

macOS 上可将本地服务设为登录后自动启动：

```bash
python3 scripts/manage_service.py install
python3 scripts/manage_service.py status
```

`uninstall` 只停用服务，不删除已保存的知识库。

## 检索

```bash
.venv/bin/smm projects
.venv/bin/smm resolve-project --cwd "$PWD"
.venv/bin/smm search "KeySync 同步问题" --scope project --project-id 1 --limit 5
.venv/bin/smm search "KeySync 同步问题" --scope all
.venv/bin/smm read 1
```

项目检索包含直接关联项目，不递归扩大。CLI/MCP 在 Agent 提供当前会话 ID 时排除当前对话；手动 Web 检索默认包含全部对话。

## Agent 接入

同一个 [`skills/smm-search/SKILL.md`](skills/smm-search/SKILL.md) 可安装到 Claude Code 和 Codex 的用户技能目录：

```bash
python3 scripts/install_skill.py
```

更新本仓库的 Skill 后，运行 `python3 scripts/install_skill.py --update` 同步到两个 Agent。

MCP 服务使用 stdio，命令是本仓库 `.venv/bin/smm-mcp`。安装器自动注册到本机已有的 Agent。CLI 可作为没有 MCP 时的后备入口。来源导入器相互独立，后续可增加其他 Agent。

MCP 搜索默认返回每条命中消息最多 600 字的预览，保留原始位置；`read_conversation` 可读取完整原文。若要恢复完整搜索展示，在 MCP 服务环境设置 `SMM_SEARCH_PREVIEW_CHARS=0`。预览效果与限制见[验证报告](reports/search-preview-001.md)。

## 规约与验收

SPEX 初始化的 [`specs/`](specs/map.md) 是需求和验证的事实来源。[整体交付报告](reports/delivery-report.md)逐项记录执行结果；[隔离端到端验收](reports/first-version-e2e.md)保留可重复执行的步骤；[新 Codex 会话实测](reports/codex-skill-live-test.md)验证 Skill 自动激活与实际回答；[效用对照报告](reports/utility-comparison-results-001.md)比较公开数据与真实项目历史中的回答效果；[长对话证据定位复验](reports/long-conversation-evidence-002.md)记录这次修复与独立题验证；[30 题历史材料对照](reports/natural-30-001.md)固定下一阶段优化前的版本。[搜索预览收缩验证](reports/search-preview-001.md)记录输出量与回答质量的权衡；[7 道新题三组对照](reports/natural-7-followup-002.md)检查默认短预览下的实际回答。运行 `pytest` 和 `spex lint` 可复核本地实现。
