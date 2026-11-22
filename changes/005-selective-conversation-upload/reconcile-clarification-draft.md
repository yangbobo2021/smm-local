# 对账输入补充（已确认）

维护者已于2026-11-22回复“采用建议，补入SPEC和PLAN”。本补充已纳入SPEC B1/A2/A11及PLAN第12节；以下保留确认时的具体方案。

独立审查实际复现：用户查看本机 none/代次1、Hub版本1后，另一入口保存 all/代次2，但Hub确认暂时失败，Hub仍版本1；旧页面或旧CLI命令只检查Hub版本1，于是实际重新提交 all，偏离用户所查看的 none。修复不改变四模式、上传默认或既有副本规则，补足B1“重新提交所显示的本机规则”的条件更新。

建议将SPEC B1的local重提命令改为：

```
smm upload reconcile --use local --expected-hub-revision <hub.revision> --expected-local-generation <local.generation>
```

两个值均从刚执行的 `smm upload reconcile` 输出取得；缺失或任一已过期时拒绝提交且不改变本机/Hub规则，提示重新查看。不能自动用提交时最新的本机规则替代旧页面展示值。

Web在查看差异时保留本机generation与Hub revision，采用Hub或重提本机均携带所展示版本；任一变化则要求重新查看。版本复核与本机条件保存使用同一个锁和数据库写边界，不能在校验后留出覆盖另一入口新规则的窗口。

CLI `--use hub` 沿用明确采用调用时Hub当前规则的用法；若提供 `--expected-local-generation` 则同样校验，否则绑定该次操作开始时读取的本机代次，保护调用期间的新保存。旧式 `--use local` 少本机代次参数会明确失败，不猜测用户同意了哪份本机规则。

PLAN补充验收：Hub版本不变但本机代次改变的旧CLI/Web请求均拒绝；本机保存发生于Hub读取期间也不能被覆盖；获取新差异后显式提交正常。检查拒绝前后本机规则/代次、Hub规则/版本及出站策略提交，新增正文不被过期确认解锁。同步更新帮助、Web提示、README链接的使用说明及恢复命令。
