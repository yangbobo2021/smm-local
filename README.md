# SMM Local

本地 Codex 与 Claude Code 对话档案与项目范围检索。导入后保存独立副本：删除 Agent 源会话不会删除知识库中的记录。

普通用户只需从 GitHub 安装 `smm-search` Skill。首次在 Codex 或 Claude Code 中使用时，Skill 从 Python 包索引安装 `smm-local` 并执行原请求。多台电脑需要汇总时，管理员另外安装 `smm-hub`。见[安装与使用指南](TRIAL_GUIDE.md)。

## 从源码开发

需要 Python 3.11+。

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/smm sync
.venv/bin/smm serve
```

Web UI 默认地址为 `http://127.0.0.1:8766`。首次同步会扫描 `~/.codex/sessions` 与 `~/.claude/projects`；可用 `SMM_CODEX_ROOT`、`SMM_CLAUDE_ROOT` 或 Web 配置覆盖。同一个系统账户安装的 Agent 和服务共享安装清单中的数据库，默认位于 `~/.local/share/smm-local/smm.sqlite3`。开发时可用 `--db` 指定独立测试数据库。服务运行时定期同步，也可在 Web UI 手动同步。

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

## Python 包发布

`python3 scripts/build_packages.py` 使用 uv 构建 `smm-local` 和 `smm-hub`，产物位于 `dist/packages/`。本机端版本在根目录的 `pyproject.toml`，汇总端版本在 `packaging/hub/pyproject.toml`。更新 Skill 支持的本机端版本时，同时更新 `skills/smm-search/scripts/first_use.py`。

维护者可运行 [Publish SMM packages](.github/workflows/publish-packages.yml)，先选择 TestPyPI，再选择 PyPI。可分别发布任一包。首次使用前，在目标包索引为两个项目配置 GitHub Actions Trusted Publisher。两者均使用此仓库和 `publish-packages.yml`，环境按包区分。

| 包 | TestPyPI 环境 | PyPI 环境 |
| --- | --- | --- |
| `smm-local` | `testpypi` | `pypi` |
| `smm-hub` | `testpypi-hub` | `pypi-hub` |

公开安装需要对应版本已上传。TestPyPI 验证时可为 Skill 启动器设置 `SMM_PACKAGE_INDEX=https://test.pypi.org/simple`，本机端从 TestPyPI 取得，依赖从 PyPI 安装。汇总端可用 `uv tool install --index https://test.pypi.org/simple --prerelease allow smm-hub` 验证。私有 GitHub 仓库的 Skill 安装仍需仓库读取权限。

## 规约与验收

SPEX 初始化的 [`specs/`](specs/map.md) 是需求和验证的事实来源。[整体交付报告](reports/delivery-report.md)逐项记录执行结果；[隔离端到端验收](reports/first-version-e2e.md)保留可重复执行的步骤；[新 Codex 会话实测](reports/codex-skill-live-test.md)验证 Skill 自动激活与实际回答；[效用对照报告](reports/utility-comparison-results-001.md)比较公开数据与真实项目历史中的回答效果；[长对话证据定位复验](reports/long-conversation-evidence-002.md)记录这次修复与独立题验证；[30 题历史材料对照](reports/natural-30-001.md)固定下一阶段优化前的版本。[搜索预览收缩验证](reports/search-preview-001.md)记录输出量与回答质量的权衡；[7 道新题三组对照](reports/natural-7-followup-002.md)检查默认短预览下的实际回答；[rc2 试用执行报告](reports/rc2-trial-report.md)核对发行安装与当前工作的历史问题。运行 `pytest` 和 `spex lint` 可复核本地实现。
