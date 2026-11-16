# SPEC 生成输入：来源管理命令帮助

## 生成指令

从一个新会话开始。使用本文件中的已确认意图、项目资料和单独提供的待测 SPEC 模板，
起草供维护者审阅的 `spec.md`。直接输出规格正文。以这里固定的资料为准。

## 已确认意图

```markdown
# 意图：让来源管理命令的用途一目了然

## 现有问题

`smm source --help` 只列出子命令名。用户在终端里无法直接判断每条命令的作用，
尤其难以分清停用来源、回退适配器和删除导入批次。

## 受影响的用户

通过终端接入或维护本机对话来源的 SMM 用户。

## 期望结果

用户只看 `smm source --help` 就能找到要用的命令，理解停用、回退和清理各自会改变什么。
`smm source --help` 和 `smm source purge-batch --help` 都提示用户，
清理批次前须先停用对应的插件来源。

## 范围与约束

本次范围限于 `smm source` 的 CLI 帮助文案。沿用现有命令名、参数和操作行为。

## 待确认问题

无。
```

## 项目资料

以下是实施试点前的仓库状态，固定于提交 `5ce7e15204440ff605d0c7f40576fad9de9fd19e`。
可查阅 [原始意图](https://github.com/yangbobo2021/smm-local/blob/5ce7e15204440ff605d0c7f40576fad9de9fd19e/changes/001-clarify-source-cli-help/intent.md)、
[CLI 定义](https://github.com/yangbobo2021/smm-local/blob/5ce7e15204440ff605d0c7f40576fad9de9fd19e/src/smm_local/cli.py)、
[来源注册和批次处理](https://github.com/yangbobo2021/smm-local/blob/5ce7e15204440ff605d0c7f40576fad9de9fd19e/src/smm_local/importers/registry.py)及
[来源操作说明](https://github.com/yangbobo2021/smm-local/blob/5ce7e15204440ff605d0c7f40576fad9de9fd19e/skills/smm-source-adapter/protocol.md#L25)。

现有项目提供的 CLI 用途说明采用简体中文。`smm source --help` 当前只列出以下子命令名。
`smm source purge-batch --help` 当前显示两个位置参数 `source_id` 和 `batch`。

| 现有子命令 | 行为 |
|---|---|
| `list` | 返回以来源 ID 为键的本机来源状态对象。 |
| `validate` | 使用来源清单和测试样本验收候选适配器。 |
| `register` | 使用来源清单和测试样本验收候选适配器，验收通过后注册来源。 |
| `enable` | 启用指定来源的导入。 |
| `disable` | 停用指定来源的导入，保留已导入记录。 |
| `rollback` | 将指定插件来源的适配器切回上一版。 |
| `batches` | 接收一个来源 ID，返回该插件来源的导入批次列表。每条批次记录的 `id` 是批次 ID。 |
| `purge-batch` | 接收来源 ID 和整数批次 ID，从 SMM 本机档案删除该批次已导入的记录。对应插件来源仍启用时拒绝清理。 |

`validate` 和 `register` 接收位置参数 `manifest` 及必填选项 `--fixture`。
`enable`、`disable`、`rollback`、`batches` 和 `purge-batch` 接收位置参数 `source_id`。
`purge-batch` 还接收整数位置参数 `batch`。

CLI 在创建档案对象和执行子命令前解析命令行。
两条帮助命令都会打印帮助并以状态码 `0` 退出，不写入档案。
