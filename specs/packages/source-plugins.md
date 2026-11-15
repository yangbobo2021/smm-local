<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# source-plugins: 本机对话来源插件

## 意图

让用户通过适配 Skill 接入能持续读取的本机对话来源，由 SMM 后台持续同步 [[archive-6](archive.md#archive-6)]。

## 外部行为

### source-plugins-1

当用户通过适配 Skill 接入新来源时，Skill 应使用 SMM 已安装的 Python 和随附验收入口生成并验证标准库 Python 插件。

### source-plugins-2

当用户验收候选插件时，SMM 应通过生产执行器验证角色、原文、会话及消息身份、顺序、来源位置、重复读取和追加续读，其中预期记录取自独立核对的样本。

### source-plugins-3

当用户注册本机插件时，SMM 应仅保存与本机来源配置、接口版本和已验证脚本摘要一致的版本。

### source-plugins-4

当后台调用插件时，SMM 应以现有 Python 在独立进程运行已注册的版本，并在出现超时、异常退出、输出超限或非法记录时记录单来源失败 [[archive-17](archive.md#archive-17)]。

### source-plugins-5

当 SMM 接收一批有效的新增对话时，SMM 应在同一事务内提交档案记录、索引及来源进度 [[archive-2](archive.md#archive-2)] [[archive-3](archive.md#archive-3)]。

### source-plugins-6

当用户停用来源时，SMM 应停止接受该来源的新导入并保留已归档内容 [[retrieval-5](retrieval.md#retrieval-5)]。

### source-plugins-7

当用户查看来源状态时，SMM 应按来源显示身份、启停、配置的来源路径、最近结果、最近成功时间及归档数量 [[archive-17](archive.md#archive-17)]。

### source-plugins-8

当用户指定来源立即同步时，SMM 应通过后台调度执行该来源或复用包含该来源的进行中同步 [[archive-16](archive.md#archive-16)]。

### source-plugins-9

当用户回退插件时，SMM 应恢复前一已验收版本并重置读取进度，保留档案供去重重放 [[archive-3](archive.md#archive-3)]。

### source-plugins-10

给定本机插件来源，当用户读取已归档消息时，SMM 应提供该消息的实际来源位置、插件版本和导入批次。

### source-plugins-11

给定来源已停用，当用户清理指定插件导入批次时，SMM 应删除该批次新增的消息、更新索引并重置来源读取进度。

### source-plugins-12

给定已安装适配 Skill，当用户接入本机来源时，Skill 应引导其从后台自动同步结果中检索并读回新增对话 [[retrieval-5](retrieval.md#retrieval-5)]。

### source-plugins-15

当验收入口在使用样本或实际来源的路径时失败，SMM 应报告失败阶段、对应的路径及其类型和失败原因 [[source-plugins-2](#source-plugins-2)]。

### source-plugins-17

当首次注册启用本机来源插件时，SMM 应返回后台同步服务的就绪地址或启动诊断 [[access-8](access.md#access-8)]。

### source-plugins-18

当验收候选插件时，SMM 应按独立提供的授权范围核对实际来源返回的记录，并在发现越界时拒绝注册且报告越界身份。

### source-plugins-19

当后台运行已保存授权范围的插件版本时，SMM 应按同一范围拒绝包含越界记录的整批结果 [[source-plugins-5](#source-plugins-5)] [[source-plugins-18](#source-plugins-18)]。

### source-plugins-20

当验收 ZCode SQLite 适配器时，SMM 应运行随版本提供的固定样本以核对系统事件过滤、空回复等待及原行完成后的续读去重。

## 验证

### source-plugins-13

隔离端到端验收应通过适配 Skill 接入新增来源 [[source-plugins-1](#source-plugins-1)]，对照来源预期验证首次、重复和续读 [[source-plugins-2](#source-plugins-2)]，拒绝变更后未验收的版本 [[source-plugins-3](#source-plugins-3)]，核对首次注册返回的就绪地址 [[source-plugins-17](#source-plugins-17)]，并在完全退出并重开 Agent 后通过同一服务的后台同步检索新增对话 [[source-plugins-12](#source-plugins-12)]。

### source-plugins-14

故障与维护验收应验证插件故障仅影响本来源 [[source-plugins-4](#source-plugins-4)]、失败后保持读取进度且重试无重复 [[source-plugins-5](#source-plugins-5)]、停用后可检索原文 [[source-plugins-6](#source-plugins-6)]、按来源报告状态 [[source-plugins-7](#source-plugins-7)]、并发复用同一同步 [[source-plugins-8](#source-plugins-8)]、版本回退 [[source-plugins-9](#source-plugins-9)]、追溯导入版本与批次 [[source-plugins-10](#source-plugins-10)]、清理后重放 [[source-plugins-11](#source-plugins-11)]。

### source-plugins-16

验收入口测试应使用文件和目录样本，验证失败报告能区分首次读取、追加读取及实际来源 [[source-plugins-15](#source-plugins-15)]。

### source-plugins-21

来源授权验收应以局部授权和实际库内的混合会话检验注册拒绝及运行期批次拒绝 [[source-plugins-18](#source-plugins-18)] [[source-plugins-19](#source-plugins-19)]。

### source-plugins-22

ZCode 固定样本验收应覆盖前置内部事件、原行空回复、重复轮询、原行写完以及完成后重放 [[source-plugins-20](#source-plugins-20)]。
