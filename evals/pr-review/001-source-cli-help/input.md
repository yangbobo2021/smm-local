# PR Review 输入：来源管理命令帮助

与单独提供的待测 Prompt 一起交给独立 Reviewer。根据以下材料和原始验收记录回放，
说明哪些结果可复核。材料对应 PR #7 的首次提交。

- Base `5ce7e15204440ff605d0c7f40576fad9de9fd19e`
- Head `cae2b86349abd4ddf1879c3282211d2315713c5a`

## Intent

````markdown
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
````

## SPEC

````markdown
# 规格：说明来源管理子命令的用途

依据 [已确认的意图](intent.md)。

## 预期行为

运行 `smm source --help` 时，帮助页为现有 8 个子命令各提供一句用途说明。
说明应表达下表中的含义，措辞可等义调整。

| 子命令 | 用途说明应表达的含义 |
|---|---|
| `list` | 列出本机对话来源及其状态。 |
| `validate` | 验收候选来源适配器。 |
| `register` | 验收并注册来源适配器。 |
| `enable` | 启用指定来源的导入。 |
| `disable` | 停用指定来源的导入，保留已导入的记录。 |
| `rollback` | 将指定插件来源的适配器切回上一版。 |
| `batches` | 查看指定插件来源的导入批次。 |
| `purge-batch` | 从 SMM 本机档案删除指定批次已导入的记录。 |

`smm source --help` 和 `smm source purge-batch --help` 都应明确提示，
清理批次前须先停用该批次所属的插件来源。

## 边界与约束

改动范围限于 `smm source` 的帮助文案。沿用现有子命令名、参数和操作行为。
查看帮助时只显示说明并退出。

## 验收条件

1. `smm source --help` 正常退出，列出全部 8 个现有子命令。
   逐项核对，每条说明均准确表达表中的用途。
2. `smm source --help` 明确提示清理批次前须停用对应的插件来源。
3. `smm source purge-batch --help` 正常退出，仍显示来源 ID 和批次 ID 两个位置参数，
   并明确提示同一停用前置条件。
````

## PLAN

````markdown
# 计划：完善来源管理命令的帮助

依据 [已确认的规格](spec.md)。

## 修改位置

- `src/smm_local/cli.py`。在 `smm source` 的参数解析定义中，为现有 8 个子命令补充用途说明，并在两处帮助显示清理批次的前置条件。
- `tests/test_cli_help.py`。新增 CLI 帮助回归测试，覆盖两处入口。现有来源插件测试继续验证实际操作行为。

## 实施顺序

1. 按规格中的表格，为 8 个子命令设置 `argparse` 的 `help` 文案，让用途说明出现在 `smm source --help` 的列表中。
2. 将「清理批次前须先停用对应的插件来源」同时用于总帮助中 `purge-batch` 的条目和该子命令自己的 `description`。两处复用同一句提示，现有命令名、参数定义和执行逻辑保持原样。
3. 通过 CLI 的 `main()` 入口测试两条帮助命令，捕获标准输出和退出码。使用临时数据库路径，确认查看帮助后该路径没有创建数据库。

## 验证方法与通过条件

| 规格验收项 | 验证方法 | 通过条件 |
|---|---|---|
| 总帮助的用途说明 | 运行 `smm source --help`，逐条对照规格表 | 退出码为 `0`，8 个子命令均有说明，且每条说明准确表达对应操作 |
| 总帮助的停用提示 | 查看总帮助中的 `purge-batch` 条目 | 明确说明须先停用该批次所属的插件来源 |
| 子命令帮助的参数与提示 | 运行 `smm source purge-batch --help` | 退出码为 `0`，仍显示 `source_id` 和 `batch` 两个位置参数，并显示同一停用提示 |

运行 `pytest -q tests/test_cli_help.py tests/test_source_plugins.py`。
两组测试均应通过，并在实现 PR 中记录上述三项验收结果。
````

## PR diff

````diff
diff --git a/src/smm_local/cli.py b/src/smm_local/cli.py
index beffc0f..a72a864 100644
--- a/src/smm_local/cli.py
+++ b/src/smm_local/cli.py
@@ -50,16 +50,26 @@ def main() -> None:
     maintenance.add_argument("--source")
     source = sub.add_parser("source", help="验收、注册或管理本机来源")
     actions = source.add_subparsers(dest="source_action", required=True)
-    actions.add_parser("list")
-    for action in ("validate", "register"):
-        candidate = actions.add_parser(action)
+    actions.add_parser("list", help="列出本机对话来源及其状态")
+    for action, help_text in (
+        ("validate", "验收候选来源适配器"),
+        ("register", "验收并注册来源适配器"),
+    ):
+        candidate = actions.add_parser(action, help=help_text)
         candidate.add_argument("manifest", type=Path)
         candidate.add_argument("--fixture", type=Path, required=True)
-    for action in ("enable", "disable", "rollback", "batches", "purge-batch"):
-        control = actions.add_parser(action)
+    for action, help_text in (
+        ("enable", "启用指定来源的导入"),
+        ("disable", "停用指定来源的导入，保留已导入的记录"),
+        ("rollback", "将指定插件来源的适配器切回上一版"),
+        ("batches", "查看指定插件来源的导入批次"),
+    ):
+        control = actions.add_parser(action, help=help_text)
         control.add_argument("source_id")
-        if action == "purge-batch":
-            control.add_argument("batch", type=int)
+    purge_help = "从本机档案删除指定批次已导入的记录。清理批次前须先停用对应的插件来源"
+    purge = actions.add_parser("purge-batch", help=purge_help, description=purge_help)
+    purge.add_argument("source_id")
+    purge.add_argument("batch", type=int)
     sub.add_parser("stop-on-demand", help="停止按需启动的后台服务")
     configure = sub.add_parser("configure-hub", help="配置汇总电脑和本机名称")
     configure.add_argument("address")
diff --git a/tests/test_cli_help.py b/tests/test_cli_help.py
new file mode 100644
index 0000000..fd0db11
--- /dev/null
+++ b/tests/test_cli_help.py
@@ -0,0 +1,49 @@
+# SPDX-License-Identifier: Apache-2.0
+# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
+
+import sys
+
+import pytest
+
+from smm_local.cli import main
+
+
+@pytest.mark.parametrize(
+    ("args", "expected_text"),
+    [
+        pytest.param(
+            ["source", "--help"],
+            (
+                "list 列出本机对话来源及其状态",
+                "validate 验收候选来源适配器",
+                "register 验收并注册来源适配器",
+                "enable 启用指定来源的导入",
+                "disable 停用指定来源的导入，保留已导入的记录",
+                "rollback 将指定插件来源的适配器切回上一版",
+                "batches 查看指定插件来源的导入批次",
+                "purge-batch 从本机档案删除指定批次已导入的记录。"
+                "清理批次前须先停用对应的插件来源",
+            ),
+            id="source",
+        ),
+        pytest.param(
+            ["source", "purge-batch", "--help"],
+            ("source_id batch", "清理批次前须先停用对应的插件来源"),
+            id="purge-batch",
+        ),
+    ],
+)
+def test_source_help(args, expected_text, monkeypatch, capsys, tmp_path):
+    database = tmp_path / "archive.sqlite3"
+    monkeypatch.setattr(sys, "argv", ["smm", "--db", str(database), *args])
+
+    with pytest.raises(SystemExit) as exc_info:
+        main()
+
+    assert exc_info.value.code == 0
+    output = capsys.readouterr()
+    assert not output.err
+    assert not database.exists()
+    help_text = "".join(output.out.split())
+    for expected in expected_text:
+        assert "".join(expected.split()) in help_text
````

## 原始 PR 正文与验收证据

````markdown
## 变更

为 `smm source --help` 的 8 个子命令补充用途，并让清理批次的停用提示同时显示在总帮助和 `purge-batch` 的帮助中。新增 CLI 回归测试，验证帮助输出和查看帮助时不会创建档案。

## 验收结果
| 规格验收项 | 结果 |
|---|---|
| 总帮助为现有 8 个子命令分别说明用途 | 通过，逐条对照规格并核对实际 CLI 输出 |
| 总帮助提示清理前须停用对应插件来源 | 通过，提示显示在 `purge-batch` 条目 |
| `purge-batch --help` 保留两个位置参数并显示同一提示 | 通过，仍显示 `source_id` 和 `batch` |

本次规格的三项验收均已验证并通过。`pytest -q tests/test_cli_help.py tests/test_source_plugins.py` 为 19 项通过。两项新增回归测试在原实现上均复现了帮助缺失。`git diff --check` 通过。


## 验收证据

以下输出在 PR 提交 `cae2b86` 的源码上采集。两条帮助命令的退出码均为 `0`。

### 总帮助 · 规格验收项 1、2

```text
$ smm source --help
usage: smm source [-h]
                  {list,validate,register,enable,disable,rollback,batches,purge-batch} ...

positional arguments:
  {list,validate,register,enable,disable,rollback,batches,purge-batch}
    list                列出本机对话来源及其状态
    validate            验收候选来源适配器
    register            验收并注册来源适配器
    enable              启用指定来源的导入
    disable             停用指定来源的导入，保留已导入的记录
    rollback            将指定插件来源的适配器切回上一版
    batches             查看指定插件来源的导入批次
    purge-batch         从本机档案删除指定批次已导入的记录。清理批次前须先停用对应的插件来源

options:
  -h, --help            show this help message and exit
```

### 清理批次的帮助 · 规格验收项 3

```text
$ smm source purge-batch --help
usage: smm source purge-batch [-h] source_id batch

从本机档案删除指定批次已导入的记录。清理批次前须先停用对应的插件来源

positional arguments:
  source_id
  batch

options:
  -h, --help  show this help message and exit
```

### 自动化测试

```text
$ pytest -q tests/test_cli_help.py tests/test_source_plugins.py
19 passed in 52.41s
```

新增的两项 CLI 测试同时确认查看帮助不会创建测试数据库。
````
