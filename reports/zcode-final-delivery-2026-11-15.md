<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# ZCode 三平台最终版交付验收

执行日期为 2026-11-15。三台机器安装同一份 SMM Local 0.2.0 验收 wheel，SHA-256 为 `ac3970af76a4fb6a68d9a7c37f71f99984c851eb592f16aa3b6a41ac5067e950`。覆盖用户指定的现场生成、首次注册、进程退出重开、定时导入和原文检索。三平台指定链路均通过。Ubuntu 覆盖官方 app-server，桌面端验收覆盖 macOS 和 Windows。行为依据见 [来源适配与验收规约](https://github.com/yangbobo2021/smm-local/blob/90824f3410428c8fd3024a082d18c184b9b3490f/specs/packages/source-plugins.md#source-plugins-13) 和 [后台服务就绪规约](https://github.com/yangbobo2021/smm-local/blob/90824f3410428c8fd3024a082d18c184b9b3490f/specs/packages/access.md#access-8)。

| 系统和 ZCode 入口 | 现场适配与注册 | 退出重开后仍就绪的 SMM | 后台归档及 ZCode 读回 |
| --- | --- | --- | --- |
| macOS 15.3.1，桌面 3.17.2 | ZCode 修正读取范围后，在新档案中首次注册版本 1 | PID `9152`，端口 `64272` | 档案 2，回复位置 7，`ZCODEFINAL-MAC-REOPEN-6159-REPLY` |
| Windows 11，桌面 3.18.2 | ZCode 修正系统事件过滤和流式回复游标后，在新档案中首次注册版本 1 | PID `9828`，端口 `55284` | 档案 3，回复位置 7，`ZCODEFINAL-WIN-REOPEN-6295-REPLY` |
| Ubuntu 22.04.5 LTS，官方 3.18.2 包内 app-server | ZCode 现场生成，经样本验收后首次注册版本 1 | PID `22983`，端口 `38075` | 档案 3，回复位置 9，`ZCODEFINAL-LINUX-REOPEN-6379-REPLY` |

## 验收方法

每台机器从空的候选目录和新档案开始。使用独立核对过的真实 ZCode SQLite 前后快照。ZCode 调用 `smm-source-adapter`，编写 Python 脚本与清单，执行随 Skill 提供的 `accept.py validate` 和 `register`。成功版本三个摘要各不相同，每个平台的首次与追加检查各为 2 条。注册返回的 `service_url` 与真实就绪接口相符。

macOS 通过应用退出，Windows 通过系统托盘退出。观察窗口确认桌面 ZCode 进程消失后再重开。Ubuntu 结束官方包内的 app-server 后启动新的 app-server 进程，未覆盖 Ubuntu 桌面界面。三台均先确认新对话标识在源库及 SMM 档案中不存在。重开后发送对话，由只读观察器核查自动归档的两条记录，逐条比对源库的角色、位置和正文。之后才从 ZCode 发起单独的关键词搜索，记录 `smm-search`、本机 `search` 和 `read` 的执行结果。整个流程没有手动同步。验收完成后停止了本轮启动的隔离服务，保留测试档案和证据。

## 执行偏差与范围

- macOS 首版候选通过固定脚本，却把实际读取范围扩大到了 15 个会话。隔离档案一度写入 244 条消息。发现后停止该隔离服务并清理隔离档案副本。ZCode 把自己生成的清单复制到新候选目录，重写脚本以限制来源，并在另一个空档案完成闭环。此次发现表明当前验收脚本会核对快照的精确输出，但无法仅凭快照证明实际来源的授权范围。
- Windows 的首次注册授权请求被取消，随后 ZCode 在另一段桌面任务注册同一份已验证候选。该候选的服务就绪及保活通过，但把对话前的系统时间线记录误判成未完成回复，导致第一段新对话漏导。修正过滤后的第一轮复测又发现，助手回复在正文为空时就被游标越过，写完后仍使用同一行。ZCode 据此继续修正并用新档案复跑。独立回放确认空回复等待完成，完成后适配器对同一行只输出一次，下次轮询无重复。真实新对话的归档另由后台批次记录确认。首次注册返回就绪地址，托盘退出后原服务保持在线。重开桌面客户端时需要重新登录测试账号。
- Ubuntu 的模型配置曾影响启动，恢复后使用同一适配会话续接。记录显示适配进程 PID 21738 完全退出，随后新建对话用 PID 23144，检索用 PID 23507。服务启动时间和首次注册响应均早于适配进程退出，退出后的三次进程快照显示同一就绪服务。适配进程退出前的服务状态由注册响应和启动时间交叉核对。三平台均观测到提问和回复进入两个不同的后台批次。
- 闭环使用受控测试会话。候选经过范围核对和单次执行授权，macOS 与 Windows 均在给出实测诊断后由 ZCode 修正。三平台全程使用同一份 SMM 构建。
- macOS 本轮真实快照只有一个种子会话。多会话、重复文本、变更后的无效候选拒绝等补充覆盖来自同版插件集成测试。
- 原生工具已有活动验收 `AT-SMM-MULTI-DEVICE-001`，本轮在 `AT-SMM-SOURCE-001` 目录留存证据和独立复审意见。

## 证据

本机证据位于 [final-2026-11-15](../.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/zcode/final-2026-11-15/)，包括 `adapt.json`、服务进程快照、`import.json`、`search.json`、后台服务日志及导入批次。独立复审逐项核对了三平台的注册、进程退出、后台导入和原文读回。详见 [独立复审记录](../.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/zcode/final-2026-11-15/independent-review.md)。

同版 macOS 测试为 32 项通过，1 项 Windows 专用用例跳过。Windows 的慢启动等待和无关端口拒绝两项回归通过。`spex lint` 为零错误，保留两条既有警告。
