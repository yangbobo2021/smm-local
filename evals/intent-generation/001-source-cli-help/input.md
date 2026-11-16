# Intent 生成输入：看不懂来源管理子命令

## 任务

根据以下反馈和项目资料，起草一份供维护者确认的 `intent.md`。
直接输出意图正文。

## 初始反馈

运行 `smm source --help`，只看到一串命令名，看不出各命令分别做什么。

## 项目资料

以下是试点实施前的状态，资料来源固定于提交 `5ce7e15`。

`smm source --help` 的子命令列表如下，各自没有用途说明。

```text
{list,validate,register,enable,disable,rollback,batches,purge-batch}
```

`smm source purge-batch --help` 的输出如下。

```text
usage: smm source purge-batch [-h] source_id batch

positional arguments:
  source_id
  batch

options:
  -h, --help  show this help message and exit
```

现有操作说明记录了这些行为：

- `list` 查看来源状态，返回结果以来源 ID 为键。
- `disable` 停用一个来源的导入，已导入记录保留。
- `rollback` 将指定插件来源的适配器切回上一版。
- `batches` 使用来源 ID 查询该插件来源的导入批次，批次记录含 `id`。
- `purge-batch` 从本机档案删除指定批次已导入的记录。对应来源仍启用时，命令拒绝清理。
