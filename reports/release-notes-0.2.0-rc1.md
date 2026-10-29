# SMM Local 0.2.0-rc1 同事试用候选版

在 macOS 本地持久导入 Codex 与 Claude Code 的可见对话，按项目及其直接关联项目搜索原文。两种 Agent 共用同一份档案、MCP 工具和 Skill；另提供 CLI、Web 页面、诊断与卸载脚本。源 Agent 删除会话后，已导入的副本仍保留。

下载 `smm-local-0.2.0-rc1.tar.gz`，解压到准备长期保留的位置，运行 `python3 scripts/install.py`。按 [试用指南](https://github.com/yangbobo2021/smm-local/blob/v0.2.0-rc1/TRIAL_GUIDE.md)检查 `~/.local/bin/smm doctor` 并完成一次真实历史问题。首次安装要从 Python 包源下载依赖，网络慢时可按公司规定配置 `PIP_INDEX_URL`。

验收：9 项自动测试通过；隔离环境的安装、重装、迁移和保留数据库卸载通过；Codex 新会话 3 题最终答案与原文一致。事后审计发现其中 2 题的检索结果受先前测试答案污染，故不能把 3/3 当作独立检索成功率。Claude Code 的 MCP 已连接且对话导入通过，但本机模型鉴权/服务不可用，真实新会话回答尚未验收。此版供有限试用，不代表长期使用价值或普遍检索准确率已经验证。详见[更新后的交付报告](https://github.com/yangbobo2021/smm-local/blob/main/reports/coworker-delivery-report.md)与[污染审计](https://github.com/yangbobo2021/smm-local/blob/main/reports/coworker-agent-audit-001.md)。

发行包只含代码与说明，不含历史对话、数据库和密钥。知识库位于使用者本机 `~/.local/share/smm-local/smm.sqlite3`。
