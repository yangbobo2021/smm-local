# access: 本地使用入口

## 意图

让用户与不同 Agent 使用同一知识库，并能检查处理状态。

## 外部行为

### access-1

当用户启动 CLI、MCP 或 Web 服务时，各入口应调用同一份档案、项目和检索逻辑 [[retrieval-1](retrieval.md#retrieval-1)]。

### access-2

当用户打开本地 Web UI 时，页面应展示同步状态、项目映射与关联、查询测试、会话原文和可修改配置。

### access-3

当 Agent 使用仓库提供的通用 Skill 时，Skill 应说明范围选择、排除当前会话、搜索与读取方法，并能在 Claude Code 和 Codex 的技能目录中被发现。

### access-4

当用户启动 Web 服务时，默认监听地址应仅允许本机访问。

## 验证

### access-5

端到端验收应通过 CLI、MCP 与 HTTP 搜索同一会话以验证 [[access-1](#access-1)]，通过 Web 页面操作验证 [[access-2](#access-2)]，通过两个技能目录安装验证 [[access-3](#access-3)]，并检查默认绑定地址 [[access-4](#access-4)]。
