<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# federation: 多机对话汇总

## 意图

让用户在任一设备检索已同步的对话，并在汇总服务不可用时继续检索本机档案。

## 外部行为

### federation-1

当用户通过 Skill 提供汇总电脑的连接地址和本机名称时，系统应为该系统账户保存共享配置 [[access-10](access.md#access-10)]，保留稳定的设备 ID，并报告连接状态。

### federation-2

当用户运行汇总服务时，服务应只向持有连接凭证的客户端提供上传、搜索和读取，远程连接应使用 HTTPS。

### federation-3

给定已配置汇总且自动同步未暂停，当本机后台服务完成一次导入 [[archive-6](archive.md#archive-6)] 时，系统应向汇总库发送尚未确认的对话消息，并在后续同步轮次重试未确认的记录。

### federation-4

当汇总服务接收记录时，系统应按 Agent 类型与原始会话 ID 合并会话，并按消息标识和原文去重，同时保留每条消息对应的设备 ID、电脑名称和原始消息位置。

### federation-5

给定已配置汇总，当用户通过 Skill 搜索历史时，系统应根据可用性自动选择检索范围：

- 汇总服务可用时搜索整个汇总档案 [[retrieval-1](retrieval.md#retrieval-1)]，各设备的本机项目 ID 不通用。
- 汇总服务不可用时搜索本机所有项目与 Agent 的档案 [[retrieval-3](retrieval.md#retrieval-3)]，并标明仅搜索本机。

### federation-6

当用户查看命中或读取其原文时，系统应返回实际来源的电脑名称、Agent 类型、原始会话 ID 和消息位置 [[retrieval-5](retrieval.md#retrieval-5)]，并按命中所属档案读取证据。

### federation-8

当管理员部署 Linux、Windows 或 macOS 汇总端时，系统应提供通过公开 Python 包索引安装的独立汇总端包和跨平台管理入口。

### federation-9

当管理员完成汇总端配置向导时，系统应按指定 HTTPS 地址配置并启动汇总服务 [[federation-2](#federation-2)]，准备独立数据库和连接凭证，并显示客户端接入信息。

### federation-10

当管理员启用或停用汇总端时，系统应由操作系统服务管理器保存该状态，并在系统重启后按该状态运行。

### federation-11

当管理员查看汇总端状态时，系统应报告已保存的启停状态、服务的可用性与连接地址。

### federation-12

当管理员通过包管理器升级汇总端时，系统应保留数据库、地址、连接凭证和启停状态，并检查已启用服务升级后的可用性。

## 验证

### federation-7

在两个独立客户端与一个汇总服务上，验收应通过 Skill 配置连接 [[federation-1](#federation-1)]，验证未授权连接被拒绝 [[federation-2](#federation-2)]，断线期间能搜索本机并在重连后恢复汇总检索 [[federation-5](#federation-5)]，补传与重试不增加重复记录 [[federation-3](#federation-3)] [[federation-4](#federation-4)]，且搜索和原文可追溯实际设备与消息位置 [[federation-6](#federation-6)]。


### federation-13

在 Linux、Windows 和 macOS 上，验收应从包源安装并配置汇总端 [[federation-8](#federation-8)] [[federation-9](#federation-9)]，从另一台电脑通过 Skill 接入并查询 [[federation-1](#federation-1)] [[federation-5](#federation-5)]，重启后核对启停状态和服务可用性 [[federation-10](#federation-10)] [[federation-11](#federation-11)]，并升级后使用原地址和凭证读取已有会话 [[federation-12](#federation-12)]。
