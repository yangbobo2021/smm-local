# archive: 对话档案

## 意图

将本机可读取的 Codex 与 Claude Code 对话保存为不依赖源文件的知识库记录。

## 外部行为

### archive-1

当同步本机 Codex JSONL 会话时，系统应保存用户和 Agent 可见文本、消息顺序、来源会话 ID、来源路径、时间与工作目录。

### archive-2

当已有会话追加完整记录并再次同步时，系统应只加入尚未导入的消息。

### archive-3

当相同来源被重复同步时，系统应避免重复会话和消息。

### archive-4

当已导入来源文件被删除时，系统应保留已导入对话和索引。

### archive-5

当来源文件出现无效或未写完的 JSONL 行时，系统应记录错误并保留已成功导入的数据，以便后续重试。

### archive-6

当服务运行时，系统应周期性同步已配置且可读取的来源并提供手动立即同步入口。

### archive-9

当用户安装本机登录服务时，系统应在登录后自动启动本地服务并继续周期性同步 [[archive-6](#archive-6)]。

### archive-10

当同步本机 Claude Code JSONL 会话时，系统应把可见用户与助手文本、来源会话 ID、工作目录、时间和顺序保存到同一档案，并标明 Claude Code 来源。

### archive-11

当来源记录包含工具结果、思考、压缩摘要或内部注入上下文时，系统应跳过这些内容，不把它们作为可检索的人机对话 [[archive-10](#archive-10)]。

### archive-12

当某个 Agent 的来源目录不存在时，系统应继续处理其他可用来源并报告该来源不可用，而非中断整个同步。

## 验证

### archive-7

在隔离端到端流程中，首次、追加和重复同步应分别验证 [[archive-1](#archive-1)]、[[archive-2](#archive-2)] 与 [[archive-3](#archive-3)]。

### archive-8

在删除来源文件后重新检索、注入未完成行后重试、运行服务和手动同步、安装登录服务时，应分别验证 [[archive-4](#archive-4)]、[[archive-5](#archive-5)]、[[archive-6](#archive-6)] 与 [[archive-9](#archive-9)]。

### archive-13

在隔离样本中同时导入两种 Agent 对话、工具结果和不存在的来源目录时，应分别验证 [[archive-10](#archive-10)]、[[archive-11](#archive-11)] 与 [[archive-12](#archive-12)]。
