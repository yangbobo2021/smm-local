# SMM Local 第一版交付与执行报告

执行日期：2026-10-29。首版用途：把本机 Codex 对话持续导入独立知识库，供 Codex、Claude Code 和用户在同一数据上按项目或全局检索。本文记录实际执行结果；[16 步隔离验收明细](first-version-e2e.md)和[机器可读记录](first-version-e2e.json)可逐项复核。

## 结果概览

依照“持久导入 → 项目归属与关联 → 检索接口 → Web UI”的依赖顺序实现，隔离端到端流程 **16/16 通过**，自动化测试 **5/5 通过**，SPEX 规约检查通过。本机服务已运行于 `http://127.0.0.1:8766`，并安装为 macOS 登录服务，按当前配置每 60 秒同步一次。

知识库把 Codex 来源中的**用户与助手可见文本消息**复制到独立 SQLite 数据库，建立整段对话的 FTS5/BM25 索引。源 JSONL 被删除后，已导入的这些消息和索引仍可读；隔离验收专门删除来源并再次搜索、读取，未删除用户真实历史来做测试。

## 按依赖顺序的执行证据

| 阶段 | 要求与实际动作 | 验收结果 |
| --- | --- | --- |
| 需求与规约 | 新建 Git 工作目录；用 SPEX 初始化 `specs/`，冻结 [IR-001](../specs/intents/001-first-local-version.md) 与四个行为规约包 | `spex lint: no problems found` |
| 持久导入 | Codex JSONL 适配器识别会话、可见消息、来源、顺序、时间和工作目录；用字节偏移增量同步，重复同步幂等 | 隔离样本首次 3 段/6 条；追加只增 1 条；重同步增 0 条；未写完行等待重试；删除来源后仍可读 3 条并搜索命中 |
| 项目归属与关联 | 以最近 Git 根目录或记录的工作目录建立项目；可手动改名、把父路径及子路径归并到项目、合并误拆项目、建立或取消双向一跳关联 | 隔离验收验证 Alpha → Beta → Gamma 时，查 Alpha 只扩到 Beta；取消关联和合并后再查；回归测试验证父目录映射对已有及未来子目录生效 |
| 检索接口 | 同一核心提供整段对话 BM25 排序、命中消息全文和位置、项目/全局范围、原文读取、当前 Codex 会话排除；CLI、MCP、HTTP 共用核心 | CLI 搜索命中隔离档案；真实 MCP stdio 握手发现 4 个工具并成功调用；HTTP 检索与原文读取通过 |
| Web UI | 展示同步状态、项目归属/关联/合并、范围检索、原文阅读和设置；手动触发同步 | 测试客户端验证页面与 API；本机浏览器实际打开 8766，检查状态、项目页、搜索和原文页 |
| 双 Agent Skill | 同一 [Skill 源文件](../skills/smm-search/SKILL.md)安装到 Codex 与 Claude Code；两端均注册 `smm-local` MCP，CLI 作为后备入口 | Skill validator 通过；两个安装副本 SHA-256 一致；`codex mcp get` 为 enabled，`claude mcp get` 为 Connected |
| 本机自动运行 | 本机 `launchd` 登录后启动 Web 服务，服务定期执行增量同步 | `launchctl` 显示 running；8766 仅监听 `127.0.0.1`；`/api/status` 返回最近同步结果 |

## 真实本机数据烟测

2026-10-29 的一次状态快照：扫描 `~/.codex/sessions` 中约 **9.7 GB** 的原始 JSONL，档案中记录 **3,446 个来源文件、3,431 段对话、20,133 条可见消息、589 个待整理的项目入口**，同步错误为 0。SQLite 数据库约 **493 MB**，`PRAGMA quick_check` 返回 `ok`。这些计数随后台同步继续变化。

在上述真实档案中，单次项目范围 `SMM` Top5 检索返回 1 段对话，耗时约 **98 ms**；单次全局 `KeySync 同步` Top5 返回 5 段，耗时约 **453 ms**。这是功能与响应时间烟测，不是稳定延迟分布，也不是召回准确率评估。

## 复核方式

在仓库目录运行：

```bash
.venv/bin/pytest -q
.venv/bin/python scripts/run_acceptance.py
node /path/to/@sublang/spex/dist/cli.js lint
.venv/bin/python /path/to/skill-creator/scripts/quick_validate.py skills/smm-search
python3 scripts/manage_service.py status
curl http://127.0.0.1:8766/api/status
```

端到端脚本只使用临时样本与临时数据库，并会重新生成两份验收记录。真实档案默认位于 `~/.local/share/smm-local/smm.sqlite3`，被 Git 忽略；报告中没有收录用户对话正文。

## 第一版边界与下一轮验证

- 只导入 Codex JSONL 中的用户和助手可见**文本**消息；工具调用、内部事件、图片和附件没有归档。其它 Agent 目前可检索同一档案，但其自身对话尚无导入适配器。
- 项目自动归属来自路径，真实档案形成了 589 个待确认入口；需要在 Web UI 中核对、合并和关联。项目过滤质量尚未用人工标注集评估。
- 当前 FTS5 分词与 BM25 排序是本版实现，不能把此前研究实验的 Top5/Top10 召回率直接套到本版。真实历史的检索质量、跨项目误归属和长对话结果展示仍需单独验收。
- Web 服务仅绑定本机回环地址，首版没有多用户身份与权限模型；适用于本机单用户，不适合直接暴露到网络。
