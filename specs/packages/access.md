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

### access-6

当 Agent 探查 MCP 检索工具时，系统应将只读取档案的工具声明为只读，以便调用方按实际行为处理审批。

### access-7

当用户在 Codex 或 Claude Code 中以自然语言请求同步维护时，通用 Skill 应引导 Agent 通过本机工具执行对应操作：

- 查看状态：汇报服务与暂停状态、各来源的导入情况、最近一次同步及错误 [[archive-17](archive.md#archive-17)]。
- 打开状态页：使用服务返回的本机地址打开状态页 [[access-2](#access-2)]。
- 立即同步：触发一次同步并汇报结果或仍在运行的状态 [[archive-16](archive.md#archive-16)]。
- 暂停同步：暂停自动同步 [[archive-14](archive.md#archive-14)]。
- 恢复同步：恢复自动同步 [[archive-15](archive.md#archive-15)]。

### access-8

当 Skill 为注册来源、历史检索、查看状态、打开状态页、立即同步或恢复同步请求本机服务时，系统应复用同一档案的已有服务，或在本机后台启动服务并等待就绪：

- 启动不可用时，报告原因，档案检索仍可读取已有索引 [[retrieval-1](retrieval.md#retrieval-1)]。
- 启动服务时遵守已保存的暂停设置 [[archive-14](archive.md#archive-14)]。
- Windows 后台启动等待同一档案服务的本机就绪响应，启动等待期限为 30 秒。
- 后台启动的服务应独立于请求启动的 Agent 进程运行。

### access-10

给定同一操作系统账户已安装 SMM，当已安装的 Agent 或本机登录服务访问档案时，系统应以用户级安装清单记录的档案路径为准 [[distribution-9](distribution.md#distribution-9)]，使检索、同步和暂停状态由同一个档案与服务提供 [[access-8](#access-8)] [[archive-14](archive.md#archive-14)]。

### access-12

如果当前 Agent 会话缺少 SMM MCP，当用户通过已安装的 Skill 请求同步或检索时，Skill 应通过随附脚本准备或定位本机组件 [[distribution-11](distribution.md#distribution-11)]，并在当前会话用 CLI 执行原请求 [[access-1](#access-1)]。

### access-15

当用户在 Web、CLI 或 Skill 管理来源时，各入口应使用同一后台调度 [[source-plugins-8](source-plugins.md#source-plugins-8)]。

### access-16

当用户打开本机导入页时，系统应按来源显示导入状态 [[source-plugins-7](source-plugins.md#source-plugins-7)]。

## 验证

### access-5

端到端验收应通过 CLI、MCP 与 HTTP 搜索同一会话以验证 [[access-1](#access-1)]，通过 Web 页面操作验证 [[access-2](#access-2)]，通过两个技能目录安装验证 [[access-3](#access-3)]，检查默认绑定地址 [[access-4](#access-4)]，并检查 MCP 工具只读标注 [[access-6](#access-6)]。

### access-9

在使用同一 Skill 与 MCP 的两个 Agent 接入路径执行同步维护时，验收应检查自然语言操作与工具的对应关系及页面地址 [[access-7](#access-7)]，并在服务关闭、运行、暂停、启动失败和 Windows 慢启动时核对后台启动、复用与失败反馈 [[access-8](#access-8)]。

### access-11

在同一账户的两个独立 Agent 进程使用不同会话环境变量时，验收应检查两者能看到相同的档案记录、暂停设置和状态页地址 [[access-10](#access-10)]。

### access-13

在只安装 Skill 的首个会话中，验收应只提出需要查阅旧对话的问题，并检查 Agent 通过随附脚本完成安装、检索和原文读取 [[access-12](#access-12)]。

### access-14

在已有档案且服务停止时，验收应只提出需要查阅旧对话的问题，并检查 Agent 在同一会话启动服务、读取原文，以及在自动同步已暂停的情况下不导入暂停期间新增的对话 [[access-8](#access-8)]。

### access-17

多来源端到端验收应核对 Web、CLI 和 Skill 的定向控制使用同一后台任务 [[access-15](#access-15)]，并核对状态页能区分零新增、从未成功、失败和停用 [[access-16](#access-16)]。
