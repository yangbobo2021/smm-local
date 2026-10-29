# SMM Local 第一版端到端验收

执行时间：2026-10-29T00:52:33.313123+00:00。
执行环境：隔离临时 Codex JSONL 样本与独立 SQLite 数据库；没有读取或修改用户真实对话。
结论：16/16 步通过。

| 步骤 | 操作 | 预期 | 实际 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 首次持久导入 | 3 段对话、6 条可见消息 | {"conversations": 3, "messages": 6} | 通过 |
| 2 | 重复同步幂等 | 新增消息 0 条 | 0 | 通过 |
| 3 | 追加记录增量同步 | 只新增 1 条消息 | 1 | 通过 |
| 4 | 项目关联只展开一层 | Alpha 查询包含 Alpha、Beta，不包含 Gamma | ["alpha-session", "beta-session"] | 通过 |
| 5 | 所有项目范围 | 3 段对话均可找到 | ["alpha-session", "beta-session", "gamma-session"] | 通过 |
| 6 | 当前对话默认排除 | 只剩 Beta | ["beta-session"] | 通过 |
| 7 | 当前对话显式纳入 | Alpha 与 Beta 均出现 | ["alpha-session", "beta-session"] | 通过 |
| 8 | 路径合并与子目录解析 | Beta 路径映射到 Alpha ID | 1 | 通过 |
| 9 | 取消关联 | Alpha 只包含自身 | [1] | 通过 |
| 10 | 合并同一项目 | Beta 路径与对话转到 Alpha，来源项目被删除 | {"source_removed": true, "path_project": 1} | 通过 |
| 11 | 删除来源后独立保留 | 原文 3 条仍可读取，搜索仍命中 | {"messages": 3, "source_exists": false} | 通过 |
| 12 | CLI 共用知识库 | 同一档案可搜且排除当前会话 | {"results": 2, "excluded": "alpha-session"} | 通过 |
| 13 | MCP 实际握手与工具调用 | 4 个只读工具可发现，自动排除当前会话 | {"tools": ["search_conversations", "read_conversation", "list_projects", "resolve_project"], "read_only": true, "excluded": "alpha-session"} | 通过 |
| 14 | Web 页面与 HTTP 检索 | 页面可加载、3 段对话可检索 | {"page_status": 200, "results": 3} | 通过 |
| 15 | Web 配置可保存 | 目录与间隔可回读 | {"codex_root": "/private/var/folders/jh/mt3s144j7wg98ww3zyqc1np00000gn/T/smm-acceptance-64uzl_gk/sessions", "sync_interval_seconds": 30} | 通过 |
| 16 | 同一 Skill 可安装到 Codex 和 Claude Code | 两个目录字节相同 | {"paths": ["home/.codex/skills/smm-search/SKILL.md", "home/.claude/skills/smm-search/SKILL.md"]} | 通过 |

## 审核边界

这组流程验证了机制连通性与持久性，不代表真实大库的导入耗时、召回准确率或所有历史会话格式均已覆盖。
真实本机导入及性能另行记录。
