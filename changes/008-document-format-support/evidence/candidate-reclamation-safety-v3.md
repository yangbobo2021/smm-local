# Canonical owner v3：独立静态修订审查

AT-SMM-008，工作树 `{checkout}`，HEAD `f1334a275e89c5079313eb7bdfc8436b62c422b7`。结论：**刚确认的数据库改名后原路径复用 P1，在 v3 对应代码路径中已有效阻断；本轮范围未发现新的确定误删或锁次序问题。** 这是静态安全修订意见，不是 native green passed，也不代表真实多档案、数据库改名或恢复已经实测通过。

本轮实际读取 `candidate-v3-owner-fix.patch`、完整 `candidate-v3.patch`、`candidate-v3-source-sha256.json`、当前 Snapshots、references、SQLite connection 退出实现与直接调用上下文。清单内六文件 SHA256 全部匹配当前源码；相对 v2 只有 document_snapshots.py 的 owner 修订，当前该文件 SHA256 为 `5b87230f9367d1f892a6a9a9b12235cb05c41c766ffedba3549d69a3dcc3fbb9`，另五文件与 v2 已核值相同。

沿用已阅读的 AGENTS.md、008 intent/spec/plan：B5 的合法失败候选保留、先拒绝失效身份再回收无其它用途字节，B9 的容量准入与不挤掉当前候选，独立档案身份和恢复 fence，足以推出本修订要求，没有新增产品行为。未运行测试/native/构建/远程或数据库/进程操作，未改源码、测试、既有证据或报告，只写本文件。正在执行的 v3 Local/Hub 主项和回归不由本报告判定。

## 身份初始化先于正文容量锁，CLI 首次失败不再因缺身份变成未知 owner

`document_snapshots.py:25–33` 的 schema context 已结束，`:36–37` 才导入并调用 `references.material(db)`；SQLite `_ClosingConnection.__exit__`（core.py:180–185）在提交/回滚后关闭连接。因此没有把 material 的初始化写事务嵌入尚未退出的 schema 事务。

构造器在任何 capture / put / transfer body admission 之前执行，且自身没有取得 capacity.lock。`material:13–29` 对已存在 identity 和 secret 只读复用；缺材料时用独立短 `BEGIN IMMEDIATE`、INSERT OR IGNORE、事务内重读取得真正持久身份。并发首次初始化不会把未写入的另一个 UUID 当成实际 identity 缓存；现存库不会因为每次构造 Snapshots 被轮换身份。

CLI `documents add/refresh` 先构建 Documents，再构建 Snapshots；现在即使用户从未 files/search，也先取得持久 archive identity，再写首个 raw。合法首次缺 OCR 失败之后，该 raw 可以登记当前 v2 owner；后续自身真实替代/最后授权失效仍有独占回收路径。不会因为只有 managed begin 预先调用 material，而把路径来源首个候选永远当未知字节多留。

该初始化只处理既有档案身份材料，不读取源文件、不解析/OCR、不创建上传授权。material 的初始化事务结束后才可能进入 pin/put 的容量锁与正文 I/O，没有新增 capacity→SQL写→guard 反向嵌套。

## owner 绑定路径与持久档案身份，并与用途快照一致

`_gc_owner:60–65` 不调用 material；有传入 c 时只执行一条 SELECT、JSON 解码及 digest。未传 c 时仅开短连接做相同只读查询。hash 输入现在是 `document-blob-owner-v2` tag、库内持久 archive identity、数据库 resolve 绝对路径，保留了原来的不同数据库路径隔离维度。

collector 在 `:106–130` 的原 `BEGIN` 一致读快照内，`:126 owner=self._gc_owner(c)` 使用同一个连接取得 owner；与 current/authorizations/publication/receipts/stages 看到的是同一 DB 状态。不是关闭用途快照后再从另一时点读取 owner，也没有在 capacity.lock 内临时补建 identity。SQL 读事务仍在持久退休和物理 unlink 前结束。

`_own_blob:72–73` 的独立 owner 读取发生在已存在的容量锁内，但它只是短 SQL 读，不初始化、不持锁等待 guard 或解析任务。没有因本修订新增 DB 写锁环。正常身份持久稳定；本报告不把运行中外部替换数据库或删除 identity 当成已支持、已验证的并发流程。

## 对路径复用反例逐分支核对

设 A 首次合法失败候选无 transfer/stage/残留 pin，owner 记录为 `H(v2,AID,shared/archive-a.sqlite3)`。停进程、保持 SQLite 一致集后把 A 改名为 archive-old.sqlite3，B 在原路径创建独立身份 BID：

1. B 的 constructor 先持久初始化 BID；collector 的 owner 为 `H(v2,BID,原路径)`，与旧 AID 输入不同。
2. B 的用途快照确实仍不知道 A 的 CID/SHA，但删除循环 `:151` 会因 `values != [owner_B]` 跳过 A raw，而不再只因原路径相同宣称独占。无需 managed transfer 或 pin 补救。
3. A 从新路径重新打开，其当前 owner 因路径变化也不等于旧登记；旧字节保守多留。若 A 再 put 相同 blob，`_own_blob` 追加新 owner，不抹去旧 owner，仍不能被另一库当作自身独占删除。这里解决的是安全，不宣称已经实现改名后旧 owner 的最终释放。
4. B 自己在新版本新建 blob 时 owners 为其真实单 owner；合法 current/授权或 pin 仍保护，真正 obsolete 后才允许删除，修订并未把全部新 canonical 一律保留。

因此，v2 报告中“B 继承原 path hash，误把 A 字节判为 B 独占无引用”的具体必要条件被移除。不同 SHA、两个或更多其它档案仍分别经过相同 identity 比较/owner 精确集合条件，不是只保护某个首目标的标识特判；但这仍是代码推演，没有实际改名或新建测试档案。

## missing 与 legacy 的保守边界

`_gc_owner:64` 在 settings 没有 identity 行时返回 None；`_own_blob:73` 不登记 None；collector `:151` 显式在 owner=None 时跳过全部 canonical unlink。不会把所有缺身份库压成一个共同“独占未知 owner”。若此前未登记的既存 blob 被观察，原 `:71` 仍不凭本次存在就认领。正常构造会前置初始化；即使之后身份行异常缺失，上述路径也选择多留，不靠路径认领。

旧 path-only v1 digest 与新 tag/identity/path digest 不相同；补丁没有批量迁移、删除或替换旧 owners 记录。`_own_blob` 遇已存在 legacy key 时可能追加本库新 owner，但保留旧值，形成多 owner，故 collector 精确 `[当前owner]` 条件不成立。不能把这种追加误写为已成功认领 legacy 独占，也不能把保守占空间称为新的误删缺陷。

对于 legacy 未知字节、旧路径 owner 和共享 SHA 的最后 owner 释放，回收能力仍未完成；不能据容量新库主项成功认领旧档案迁移回收已经通过。没有 identity 行与格式损坏/任意外部篡改不是同一状态；本报告只对代码明确处理的缺行作上述结论，不扩展到未经定义的损坏库容错。

## 恢复、既有 fence 与执行边界

正常数据库改名保留库内 identity，不依赖原文件名生成新 identity。旧备份恢复到同路径、同逻辑身份可能得到相同 owner，但已退休 CID/AID 仍由当前持久 retired.json 拒绝，未被本修订撤销。换成独立新库得到不同 identity，不能接管该路径旧 owner；缺身份旧库初始化也不转换历史登记。`DocumentGuard.prepare_restore` 的 reclamation / expired-transfers 排除项不变，必须继续保留当前 fence，不能用旧备份覆盖。

v2 已核的跨档案同 S receipt 归属、既有 folder 回放早于新增 canonical GC、retired AID 拒绝、当前连续授权、历史发布 ledger、raw/results pins、接收 stage 和短 guard 保护都未在本次补丁中改动。原先“先持久退休再物理删除”的顺序不变。

**动态缺口仍独立存在：** 本轮未实测 A 停机改名/B 复用旧路径、CLI 首个失败候选无需 files/search 的归属、多档案同 S 真实分块/当前 commit 回放、missing/legacy 保守与旧 DB 真恢复，以及并发/Windows 拒删。应以独立 raw SHA、archive identity、CID/AID、物理文件和后续合法 retry/准入核对，不能只比较两个产品返回相等。上述缺口不因本次静态修订认可而标为已完成。

既有 watchdog `matching→cmdline→AccessDenied` 的实际异常、共享 stderr 诊断和持续不可读清理风险，已在 `safety-supervisor-failure-v2.md` 归因，本轮监督产品代码未改；不能称已修复，也不能把容量测试的权限负控称为假错。原 v2 Hub 执行失败不被新的 owner 修订追认。本报告只确认 owner P1 对应静态路径修订有效，不登记 native green，不判完整 GC/SC10/R008通过。
