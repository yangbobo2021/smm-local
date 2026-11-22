# [P2] 目录尾部 ** 未实现零目录段，合法排除仍纳入直接文件

独立 PR Reviewer：`/root/review_006_pr_final`。审查头 `4c706b304e904b126ea3103523069b265d101b31`，base `f797fe843430b48faf379cd76b4ae18fd52f5c64`。本项由审查者在全新临时目录真实运行产品后端发现，没有修改产品、测试或原生 AT 判定。最终 PR 审查尚未通过。

**性质与范围：明确违反既有 SPEC B2/A2；不是新增需求。** B2 规定 `**` 匹配零个或多个目录段，尾 `/` 排除对应目录及全部后代。因此 `cache/**/` 中 `**` 取零段时须匹配 `cache` 目录，从而排除其中直接文件与后代。当前 `src/smm_local/documents.py:85`–`90` 固定前一段的 `/`、将末尾 `**` 编译为 `.*`，得到 `^cache/.*$`，不能匹配遍历时目录本身的相对路径 `cache`。`_scan` 第286行又只允许尾 `/` 模式匹配目录，结果为：`cache/sub` 被排除，但 `cache/direct.txt` 不匹配目录条件，仍被采集和检索。

受影响者是使用 CLI/Web 合法递归目录排除的普通用户和依赖其纳入范围的 Agent。`cache/` 是现有可用替代，且显式纳入、检索、读取的基础路径仍可用；本发现不声称整个文档功能不可操作。实际影响是用户配置中本应被排除的直接文件仍进入本机采集快照，故不能以现有 SC2 passed 证明完整 B2/A2。

真实执行使用 `.venv/bin/python`，从仓库根运行如下产品调用（夹具只在 `TemporaryDirectory`，档案位于该目录）：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from smm_local.core import Archive
from smm_local.documents import Documents, _glob
with TemporaryDirectory(prefix='smm006-glob-review-') as temp:
    p = Path(temp).resolve()
    (p/'docs'/'cache'/'sub').mkdir(parents=True)
    for name, text in [('cache/direct.txt', 'needle direct'),
                       ('cache/sub/nested.txt', 'needle nested'),
                       ('visible.txt', 'needle control')]:
        (p/'docs'/name).write_text(text)
    d = Documents(Archive(p/'archive.sqlite3'))
    s = d.add(str(p/'docs'), exclude=['cache/**/'])
    d.refresh(s['id'])
    print(bool(_glob('cache/**/').fullmatch('cache')))
    print([Path(h['path']).relative_to(p/'docs').as_posix()
           for h in d.search('needle', limit=50)['results']])
```

真实输出：

```text
False
['cache/direct.txt', 'visible.txt']
```

独立预期为仅 `['visible.txt']`。完整 source/refresh/search 响应、规范夹具路径与实际观察起止保存在 `work/pr-review-v2/glob-trailing-recursive.json`，原 SHA-256 为 `aba525c7925296dd5ac8621b1946b3de194149cbb5c9e71225c692539000ea88`；其中 `expected_paths` 与 `actual_paths` 分列，未把错误结果登记为通过。此前一次观察仅因打印时 `/var` 与 `/private/var` 的相对路径比较触发审查脚本异常，第二次使用 `resolve()` 完整记录；这不改变产品实际纳入直接文件的复现。

适度修复与通过条件：实现末尾 `**` 的零/多目录段语义，补真实扫描级用例覆盖 `cache/**/`、`**/cache/**/` 的根/嵌套位置及多级目录，并保留目录外正控及相似名目录正控；以旧产品取得真实断言红灯，再以修复产品取得绿灯与当前有效验收证据。普通 `*` 不跨路径段、既有 `**/private.txt` 与尾 `/` 行为应继续通过。未要求改变 SPEC 或扩大纳入范围；修复前不应授予整体验收或合并结论。
