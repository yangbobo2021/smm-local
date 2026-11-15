# SMM Local

在 Codex 或 Claude Code 里搜索以前的对话，并找到原始会话和消息位置。SMM 在本机保存独立的对话档案。删除 Agent 中的原始会话后，已经导入的记录仍可搜索。

## 单台电脑快速开始

你需要已登录的 Codex 或 Claude Code，以及首次安装时的网络连接。

1. 从 [GitHub 最新正式版](https://github.com/yangbobo2021/smm-local/releases/latest) 下载 `smm-search-0.3.0.zip`，解压得到 `smm-search` 文件夹。也可以下载源码 ZIP，从 `skills/` 取出这个文件夹。
2. 将整个 `smm-search` 文件夹放到下表对应的位置。目录不存在时可自行创建。两个 Agent 都要使用时，各放一份。

   | Agent | 安装后应能看到的文件 |
   | --- | --- |
   | Codex | `~/.agents/skills/smm-search/SKILL.md` |
   | Claude Code | `~/.claude/skills/smm-search/SKILL.md` |

   Windows 上的 `~` 是当前用户的个人文件夹，例如 `C:\Users\你的用户名`。请同时保留 Skill 文件夹中的 `scripts/`。

3. 新开一个 Agent 会话，问一个你确实在旧对话里讨论过的问题。比如可以说：

   > 请用 SMM 搜索以前的对话。我当时对发布回滚提了哪些要求？请引用原始会话和消息位置。

   第一次使用时，Skill 会从 PyPI 自动安装本机端、启动同步服务并继续处理原请求。如果 Agent 提示需要运行 Skill 的安装脚本或访问网络，允许后即可继续。安装会报告进度；网络较慢时耐心等候，下载中断后会自动恢复或重试，无需手动运行安装命令。如果首次导入仍在进行，可以让 Agent 查看同步状态。Codex 和 Claude Code 在同一个系统账户下共用一份档案和一个服务。

已安装 Node.js 22.20 或更新版本的用户，也可以在终端运行以下命令，并在安装器中选择使用的 Agent。

```sh
npx skills add https://github.com/yangbobo2021/smm-local/tree/main/skills/smm-search -g
```

日常可以直接对 Agent 说「查看 SMM 同步状态」「打开 SMM 状态页」「立即同步一次」「暂停自动同步」或「恢复自动同步」。暂停时仍可搜索已有记录，服务重启后也会记住暂停状态。

## 多台电脑共用档案

先在每台电脑按上面的步骤安装 Skill。再由管理员选择一台可通过 HTTPS 访问的电脑安装汇总端。准备好客户端可访问的 HTTPS 地址、证书和私钥，并先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)。

```sh
uv tool install smm-hub==0.3.0
```

如果终端找不到 `smm-hub`，运行 `uv tool update-shell` 后重新打开终端。然后完成向导并检查服务状态。

```sh
smm-hub hub setup
smm-hub hub status
```

确认状态中的 `enabled` 和 `running` 都为 `true`，地址与向导中填写的 HTTPS 地址一致。向导会生成连接凭证文件。把文件交给获授权的用户，再在每台客户端对 Agent 说「把这台电脑叫办公室电脑，汇总地址是 https://hub.example.net:8770，凭证文件在这里」，并提供本机文件路径。接入后仍用同一句自然语言搜索。汇总端断开时会退回本机搜索，恢复连接后继续同步。

证书信任、各平台服务配置、升级和卸载见[安装与使用指南](TRIAL_GUIDE.md)。

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

## 接入其他本机 Agent

先按上面的步骤安装 SMM 0.3.0。已有 0.2.0 的用户按[本机端升级步骤](TRIAL_GUIDE.md#升级本机端)更新。再从 [GitHub 正式版](https://github.com/yangbobo2021/smm-local/releases/tag/v0.3.0)下载 `smm-source-adapter-0.3.0.zip`，解压后把整个 `smm-source-adapter` 文件夹放进目标 Agent 的技能目录。也可以从源码取出 [适配 Skill 目录](skills/smm-source-adapter)。从源码安装时，`python3 scripts/install_skill.py --update` 会把整个适配 Skill 安装到 Codex 和 Claude Code。用该 Skill 接入能持续读取的本机对话来源。对 Agent 说「把 X Agent 在这台电脑的对话接进 SMM，以后自动同步」。Skill 生成标准库 Python 适配器，用本机样本通过验收后注册。脚本使用 SMM 已安装的 Python，适配 Skill 在各平台使用同一份。

在导入页或用 `smm source list` 查看来源状态。用 `smm maintenance sync --source <ID>` 单独同步，用 `smm source disable <ID>` 停用。已导入内容可用 `smm search "关键词" --local` 检索，即使配置了多机汇总。现场插件使用本机用户的文件和网络权限，请只验收和注册受信任的脚本。现场适配器导入的记录保留在本机档案。

## Python 包发布

`python3 scripts/build_packages.py` 使用 uv 构建 `smm-local` 和 `smm-hub`，产物位于 `dist/packages/`。本机端版本在根目录的 `pyproject.toml`，汇总端版本在 `packaging/hub/pyproject.toml`。更新 Skill 支持的本机端版本时，同时更新 `skills/smm-search/scripts/first_use.py`。

维护者可运行 [Publish SMM packages](.github/workflows/publish-packages.yml)，先选择 TestPyPI，再选择 PyPI。可分别发布任一包。首次使用前，在目标包索引为两个项目配置 GitHub Actions Trusted Publisher。两者均使用此仓库和 `publish-packages.yml`，环境按包区分。

| 包 | TestPyPI 环境 | PyPI 环境 |
| --- | --- | --- |
| `smm-local` | `testpypi` | `pypi` |
| `smm-hub` | `testpypi-hub` | `pypi-hub` |

公开安装需要对应版本已上传。TestPyPI 验证时可为 Skill 启动器设置 `SMM_PACKAGE_INDEX=https://test.pypi.org/simple`，本机端从 TestPyPI 取得，依赖从 PyPI 安装。汇总端可用 `uv tool install --index https://test.pypi.org/simple --prerelease allow smm-hub` 验证。

## 规约与验收

SPEX 初始化的 [`specs/`](specs/map.md) 是需求和验证的事实来源。[整体交付报告](reports/delivery-report.md)逐项记录执行结果；[隔离端到端验收](reports/first-version-e2e.md)保留可重复执行的步骤；[新 Codex 会话实测](reports/codex-skill-live-test.md)验证 Skill 自动激活与实际回答；[效用对照报告](reports/utility-comparison-results-001.md)比较公开数据与真实项目历史中的回答效果；[长对话证据定位复验](reports/long-conversation-evidence-002.md)记录这次修复与独立题验证；[30 题历史材料对照](reports/natural-30-001.md)固定下一阶段优化前的版本。[搜索预览收缩验证](reports/search-preview-001.md)记录输出量与回答质量的权衡；[7 道新题三组对照](reports/natural-7-followup-002.md)检查默认短预览下的实际回答；[rc2 试用执行报告](reports/rc2-trial-report.md)核对发行安装与当前工作的历史问题。运行 `pytest` 和 `spex lint` 可复核本地实现。
