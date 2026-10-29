# retrieval: 原文检索

## 意图

在明确范围内找出相关整段对话，并允许读取可信的原始消息。

## 外部行为

### retrieval-1

当用户发起非空查询时，系统应按 BM25 排序并返回匹配的整段对话身份、来源、项目、时间与命中消息位置。

### retrieval-2

当请求指定项目范围时，系统应只检索该项目及其直接关联项目 [[projects-3](projects.md#projects-3)]，并在结果中报告实际项目范围。

### retrieval-3

当请求指定全部项目范围时，系统应检索所有已导入项目，包括未归属项目。

### retrieval-4

当 Agent 提供当前来源会话 ID 时，系统应默认排除该会话，并允许明确覆盖该默认值。

### retrieval-5

当用户读取某会话或指定消息区间时，系统应从独立副本返回按顺序保存的完整消息 [[archive-1](archive.md#archive-1)]，即使源文件已删除 [[archive-4](archive.md#archive-4)]。

### retrieval-7

当命中的对话包含大量消息时，系统应兼顾消息的词面相关性和时间分布，返回带原始位置的完整消息及其相邻问答，避免只展示较早的相似讨论。

## 验证

### retrieval-6

隔离端到端流程应检查排序和命中位置 [[retrieval-1](#retrieval-1)]、项目与全局范围 [[retrieval-2](#retrieval-2)] [[retrieval-3](#retrieval-3)]、当前会话排除 [[retrieval-4](#retrieval-4)]、源删除后的原文读取 [[retrieval-5](#retrieval-5)]，以及长对话的跨时段证据展示 [[retrieval-7](#retrieval-7)]。
