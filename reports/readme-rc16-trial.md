# 0.2.0rc16 README 试用记录

按 README 的快速开始和汇总端安装步骤试跑。测试在 macOS 临时用户目录中进行，使用模拟对话和正式 PyPI 上的 `0.2.0rc16`。本机服务使用临时端口，关闭登录自启。Skill ZIP 由仓库中的 `scripts/build_release.py --skill` 生成。

| 项目 | 实测结果 |
| --- | --- |
| 发行 ZIP | 解压后包含 `SKILL.md` 和三个启动脚本。分别放入 Codex 与 Claude Code 的用户技能目录。 |
| GitHub 获取 | 有仓库权限时，源码 ZIP 中的 Skill 文件与发行 ZIP 一致，README 的 `npx skills` 命令也能安装到 Codex 用户目录。匿名访问仓库及其发布页返回 404。 |
| Codex 首次提问 | 在全新会话中发送 README 示例。Codex 自动识别 Skill，从 PyPI 安装本机端，启动服务并搜索，随后读取原文并在回答中引用测试会话 ID 与消息位置。 |
| Claude Code 首次提问 | 隔离会话在登录环节停止。直接运行同一目录下的 Skill 启动器，可以从 PyPI 安装本机端并命中测试对话。 |
| 汇总端安装 | 通过 README 的 uv 命令安装指定版本。使用 `uv tool update-shell` 后，新终端可发现 `smm-hub`。配置向导及状态命令的帮助可运行。 |
| 项目回归 | 20 项测试通过。 |

独立复核确认了匿名下载入口缺失，以及汇总端检查的实际范围。正式发布前仍需提供可匿名下载的 Skill ZIP，补测已登录的 Claude Code 会话，并在具备 TLS 证书与服务管理权限的汇总机器上完成向导和跨机接入。
