<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# ZCode 与 SMM 兼容性试用

| 环境 | ZCode 实际运行路径 | SMM 验证结果 |
| --- | --- | --- |
| macOS | 已登录的 3.17.2 桌面端 | ZCode 成功调用 `smm-source-adapter` 和 `smm-search`。适配器通过固定验收入口注册。后台从真实 SQLite 会话库自动导入第三轮，六条原文与桌面记录一致。重同步新增零条。ZCode 通过搜索技能调用隔离测试库的 CLI 后读回原文。 |
| Windows 11 | 3.18.2 官方签名安装包，使用包内 ZCode 运行时 | GLM Coding Plan 接入后生成两段真实对话。本机通过固定验收入口注册适配器，首轮导入两条，后台下一轮自动追加两条，重跑新增零条，检索与原文读取逐条相符。 |
| Ubuntu | 3.18.2 官方 DEB 解包，使用包内 ZCode 运行时 | GLM Coding Plan 接入后生成两段真实对话。本机通过固定验收入口注册适配器，首轮导入两条，后台下一轮自动追加两条，重跑新增零条，检索与原文读取逐条相符。 |

Mac 读取真实 ZCode 进程写入的 SQLite 文件。远端从各自机器上的真实 ZCode 会话库提取隔离快照，并在当地运行 SMM 后台验证周期同步。另以实际 ZCode 会话库为来源验证后台可读性。
适配器按测试会话 ID 限定范围，过滤模型专用上下文、工具记录和思考分段，并等待助手消息完成。
远端使用官方包的命令行运行时生成对话，并由 SMM 验收脚本注册和验证后台同步。两台远端的 ZCode 桌面界面、由 Agent 自主生成适配器的流程，以及开机自启未在本次验证。
测试配置中的临时凭证已从两台远端测试目录移除。

原始对照及探针保存在工作区 `.acceptance-local/native-v1/AT-SMM-SOURCE-001/evidence/zcode/`。
