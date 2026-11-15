<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai> -->

# 本机来源插件协议 v1

清单必须包含 `version: 1`、`id`、`name`、`root` 和 `script`。路径相对于清单所在目录或为绝对路径。为每个来源账户选一个稳定的小写 ASCII ID，可包含数字及连字符。脚本是单个 `.py` 文件，仅使用标准库。注册将保存文件快照，因此编辑候选文件后需要重新验收并注册。

脚本从标准输入读取一份 JSON。字段为 `version`、`root`、`cursor`、`limit` 和 `scope`（旧注册版本发来的请求可能省略）。初次 `cursor` 为 null，后续为上次提交的字符串。程序向标准输出写一份 UTF-8 JSON，字段为 `messages`（数组）、`cursor`（字符串或 null）和 `more`（布尔值）。有消息或尚有可处理的积压时必须推进进度。SMM 每轮处理一批。遇到会造成漏读的格式变化时以非零退出，让 SMM 保留之前的进度。

每条消息包含 `session_id`、`message_id`、`position`（非负整数）、`role`（user 或 assistant）、`text`（可见原文）、`origin`（相对来源目录的路径，单文件来源为其文件名）。`timestamp`（ISO 8601 字符串）和 `cwd`（本机绝对路径）可省略。使用上游稳定 ID，保持相同会话中同一消息的身份、位置和正文稳定。对于追加写入的日志，可以在确认轮转方式后使用字节位置。在 SQLite 中用只读连接。跳过内部提示、思考、工具结果、压缩摘要及尚未提交的消息。插件通过标准输出交付归一化数据，SMM 保存档案和进度。

验收样本 JSON 包含 `before` 和 `after` 两个独立快照路径、`expected_before` 和 `expected_added` 两组按实际返回顺序排列的标准消息，以及独立授权的 `scope`。快照路径相对于验收 JSON。两个快照保留相同的相对来源路径及记录身份。预期正文从原 Agent 界面或独立核对的原始记录取得。注册时 SMM 会重新验收，然后保存通过的脚本和授权范围。

| scope | 授权内容 |
| --- | --- |
| `{"kind":"all"}` | 用户明确授权整个来源路径 |
| `{"kind":"sessions","session_ids":["id"]}` | 用户授权的固定会话 ID |
| `{"kind":"zcode","session_ids":["id"],"first_user_prefix":"项目标记 "}` | ZCode SQLite 单文件中指定 ID，及首条可见用户原文以指定前缀开头的会话 |
| `{"kind":"zcode","all_sessions":true}` | 用户明确授权整个 ZCode SQLite 文件，仍运行 ZCode 固定样本 |

根据请求中的 `scope` 做过滤。ZCode 中按会话的原始插入顺序找到首条可见用户消息，按 `part.sequence` 拼接尚未标记为内部或合成的文本片段，再做区分大小写的前缀匹配。后续用户消息含前缀不改变授权。核对会话范围时要能读取游标之前的首条消息。SMM 独立查验实际来源的输出，如果越界，就报告会话与消息 ID，拒绝注册或拒绝运行中的整批结果。受限的实际来源探测需要在验收批次预算内到达末尾。授权检查约束提交给档案的消息，脚本自身在本机账户权限下运行。

SMM 将每个快照的实际路径直接作为 `root`，不会把文件路径改成其父目录。验收失败时，先查看报错中的阶段（`before`、`after` 或 `live`）、路径和类型；如果实际来源是目录、快照是文件，适配器要能处理两种输入，再重新验收。

`smm source list` 查看状态。用 `smm source disable <ID>` 停用，`smm source enable <ID>` 恢复，`smm source rollback <ID>` 切回上一版。用 `smm source batches <ID>` 查已导入批次。只有用户要求纠正已导入的内容且来源已停用时，才使用 `smm source purge-batch <ID> <批次>` 删除明确的批次。恢复前修正导致误读的规则。

ZCode 的隐藏、仅模型可见、系统时间线及工具记录要先过滤。可见助手回复可能先有空行，再在同一行补写原文和完成标记。助手未完成时保留该行的续读能力，即使正文为空。仅遇到未完成行且没有可处理消息时，可保留游标并返回 `more: false`，由下一轮后台同步重试。已完成但没有可见正文的行可跳过。固定样本依次指向首次、空回复、同一行完成三个独立快照，中间及完成后均重复读取。用 `samples-zcode <新目录>` 查看随验收器发布的输入和独立预期。适配器正常处理请求传入的范围和数据库结构。
