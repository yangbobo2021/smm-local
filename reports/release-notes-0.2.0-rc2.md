# SMM Local 0.2.0-rc2 同事试用候选版

此版默认将搜索卡片中的每条命中消息缩为最多 600 字，并保留消息位置；Agent 可按需读取该轮完整原文。Codex 与 Claude Code 的对话仍导入同一份本地档案，支持项目范围检索。下载 `smm-local-0.2.0-rc2.tar.gz`，解压到打算长期保留的位置，运行 `python3 scripts/install.py`。详见[试用指南](https://github.com/yangbobo2021/smm-local/blob/v0.2.0-rc2/TRIAL_GUIDE.md)。

发行包 SHA-256：`597fac7f0f2ca07eb902f543c6e15b30549884f3a6a7f4123f4ddfc3fb38d775`。隔离安装的九项检查及 12 项自动测试均通过。一道当前工作中的历史图谱问题在直接查原始文件与 SMM 两组都得到有据答案，SMM 确实调用了检索及完整读取；这道题不证明 SMM 在效率上优于直接查文件。Claude Code MCP 已接通，但本机模型调用超时，尚未完成真实回答验收。详见[执行报告](https://github.com/yangbobo2021/smm-local/blob/v0.2.0-rc2/reports/rc2-trial-report.md)。

发行包不含历史对话、数据库或密钥。该版本供有限试用，正式多使用者验收仍待完成。
