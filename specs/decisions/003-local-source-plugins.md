<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# DR-003: 现场生成的本机来源插件

## 状态

已接受。

## 背景

不同 Agent 的本机对话结构各异，SMM 团队无法逐一维护全部来源。

## 决策

现场 Agent 生成 Python 插件，由 SMM 用已安装的解释器在独立进程调度。
SMM 负责验收、归档、索引、进度及生命周期，插件负责读取与转换来源。
本机用户启用受信任脚本，执行进程使用该用户的权限。
试用版中现场插件的记录仅进入本机档案。

## 影响

适配 Skill 和插件协议在系统之间通用。
进程边界提供故障隔离，文件与网络权限取决于操作系统账户。
内置来源保持现有会话身份并使用同一个来源调度入口。
