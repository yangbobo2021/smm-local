# v2 补充独立审查：数据库路径复用与 canonical owner 身份

AT-SMM-008，`{checkout}`，源码保持 v2 冻结。本轮结论：**存在 P1 合法 canonical 字节误删路径，应修订 owner 身份。** 这不是保守多留或尚未完成的回收能力。此前 v2 报告解决了 receipt 归属问题，本文件补充另一条不同的 owner 归属边界；不修改此前报告，也不授予 native / green passed。

本轮只读 CLI、Archive、Documents、Snapshots、references 及规格/指南相关入口，没有执行改名、创建测试档案、admission、测试、native、构建或远程操作；只写本文件。以下是源码条件推演，未称实际复现。

## 问题与实际可达链

`src/smm_local/document_snapshots.py:56–57` 的 `_gc_owner()` 仅为 `digest(['document-blob-owner-v1', 数据库绝对路径])`，没有绑定数据库内容中的 archive identity。`:138–147` 的 canonical 删除只要求 owners 恰好为 `[当前owner]`、blob 不在当前 protected、目标是普通文件，就执行 unlink。

具体选择 **CLI 路径来源的首次合法失败候选**，使它没有管理上传 transfer 这项额外用途保护：

1. A 位于 `shared/archive-a.sqlite3`，通过 CLI `documents add`、明确 `documents refresh` 纳入合法扫描 PDF，因缺 OCR 条件失败但完整 raw 已保存。入口 `cli.py:282–295` 直接构建 Documents 并调用 refresh；`documents.py:397–408` 先 capture，记录 captured_id，再处理；单文件处理失败时 `_publish:468–472` 只撤其它旧 capture 授权，保留本次已完整 captured_id。B5 明确该候选可只用保存字节重试。正常操作结束后 raw pin 已释放；没有 published ledger、Hub stage 或 raw-only managed transfer 的保护。
2. A 的 raw 写入通过 `Snapshots.capture:207–213` → `put:177–193`，在容量锁内登记 owner=`H(原路径)`。它是当前合法候选，数据库中 source 授权、current CID/latest AID 均有效；不需要持久进程存活。
3. 停止 A 的全部进程，保证 SQLite 一致集完整，再把数据库改名为同父目录的 `shared/archive-old.sqlite3`。不是丢弃活跃 WAL、损坏数据库或回滚退休标记。`.document-snapshots` 仍在同父目录，因此 A 的持久 raw 和 metadata 地址仍吻合。可以保持 A 暂不启动，或按新 `--db` 读取它；其逻辑 archive identity 和候选没有因为数据库文件名改变而被用户撤销。
4. 在原路径 `shared/archive-a.sqlite3` 新建独立档案 B，进行第一次普通合法新 admission，输入 SHA 与 A 不同。`Snapshots.__init__:24` 仍选同一个父目录 `.document-snapshots`；B 的 `_gc_owner()` 又得到 `H(原路径)`，与 A 旧登记完全一致，尽管 B 的真实 archive identity 不同。
5. B 的 `put:180` 或新 `BlobTransfers.begin:202` 调用 `reclaim_candidates`。`:97–120` 只读取 B 的 SQL publication/current/authorization/stage；B 不含 A 的 CID/AID 或 raw SHA，故 A 不进入 protected。A 没有 managed transfer，`:125–134` 的 v2 purpose/device/archive 修复无对象可保护；没有在途/崩溃 pin，`:135–137` 也无额外保护。
6. owners 中 A 的 raw 恰好为 `[H(原路径)]`，等于 B 当前 owner，`:141` 的跳过条件不成立，`:147` unlink A raw。后续 A 仍能从其 DB 得到合法 retry_target，但保存原件已缺失。B 的扫描甚至没有见到 A CID/AID，无法先把它们判为退休，违反 B5 先拒绝失效身份再回收无其它用途字节的次序和合法候选保留要求。

如果 A 恰为 managed upload，v2 对另一 archive transfer 的保护可能阻止删除；如果 A 尚有 pin 或已有发布历史，也可能幸存。但承诺适用于路径首次失败候选，不能以其它前状态存在额外保护排除这条反例。只用普通/全局、不同项目或另一个路径名做等价样例，也不会触发“旧 DB 路径被新逻辑档案占用”的 owner 碰撞。

## 现有入口和身份约定不能排除此动作

`cli.py:35` 提供自选 `--db`，`:182–186` 直接把该路径交给 Archive；`core.py:188–204` 创建父目录、打开/初始化该文件和 WAL，没有路径必须终身绑定同一 archive identity 的登记、独占占用墓碑或“同父目录只能一个 DB”的限制。`Documents.__init__:185–221` 创建文档表后构建 Snapshots，也没有对路径曾属于其它档案作校验。

真实档案身份另存于 `settings['archive:identity']`，`references.material:14–29` 从库内读取，缺失时生成 UUID；`references.decode:34–38` 用这个身份判断原文引用所属档案。它不是数据库文件名或 `_gc_owner` 路径 hash。指南明确可用独立 `--db`，备份/恢复要求保存数据库与持久目录一致集，但没有规定数据库文件名永不复用。此次同父目录一致改名不移动持久 root，也不覆盖保护目录；不能据既有恢复说明把 B 获准删除 A 字节当成用户授权。

即使把 A 改名操作另归为需谨慎的维护，B 在复用路径后也没有掌握 A 的当前用途，不应凭自身空库推导“独占且无最后用途”。因此问题是误删，而非对跨目录迁移能力的额外要求。

## 将 archive identity 纳入 owner 的适用修复与边界

把 owner 身份改为带版本的 `H(数据库绝对路径, archive:identity)`，保持当前路径隔离维度，能够覆盖本反例：A 原登记含 AID，B 原路径但 BID 不同，`owner_B != owner_A`，删除循环跳过 A 旧字节。A 改名后自己的 owner 也变了，所以原登记可能保守多留；这属于安全的回收能力边界，不能自动把旧路径的登记据新库认领。单纯用 archive identity 取代路径会引出同逻辑档案副本的用途边界，本建议是**在现有路径维度上加入持久身份**，不声称解决任意复制库分叉运行。

迁移必须保守：现有 path-only v1 owner 无法证明当时库内是哪份 identity，不应仅按当前路径批量转换成新 owner。保留旧标识为不能由新 owner 独占认领的记录，或显式按未知处理，宁可多留。尤其不能在 B 初始化时把旧 `[H(path)]` 改写成 `[H(path,BID)]`，那会重新制造本反例。只有有独立归属证据的迁移才能另行认领。

身份缺失时应保守未知：不能返回一个会被所有缺身份档案共用的“可删除 owner”，也不能把 None 登记为独占；缺失时跳过 owner 认领/删除，已有字节继续计费。GC 应只读当前 SQL identity，不在 capacity.lock 内调用可能初始化身份的 `material()`。

**仅“missing 时保守未知”还不足以维持新 CLI 候选的容量能力。** 目前 `Documents.__init__` 到 Snapshots 没有前置 material；`core.py` 不初始化 archive identity；CLI add/refresh 可以先于 files/search/managed begin 调用，而 files 在 `documents.py:300` 才调用 references.material。若首个 CLI refresh 创建 raw 时 identity 缺失，该 raw 会成为永久未知，之后即使合法替代也不能由本轮独占 canonical GC 释放，容易重现容量缺口。

因此，在 Snapshots 首次可能写入/认领 blob **之前**，用现有档案身份机制前置、幂等地初始化身份是合理方案，例如在 Snapshots 初始化阶段、取得 capacity.lock 前完成 `references.material(db)` 的短事务并读取已持久化身份。该调用不采集外部文件、不解析/OCR、不联网或授权上传；复用既有身份，不为已存在库轮换 identity。首次两个进程并发初始化仍须沿用 `BEGIN IMMEDIATE`、INSERT OR IGNORE、事务内重读的既有原子机制，不能各自缓存未真正落库的 UUID。

锁与恢复约束：初始化必须先退出自身 DB 写事务，再进入容量锁/正文 I/O；不要从 `_gc_owner`、`put` 或 collector 的容量锁内临时初始化。现有 Snapshots/Document 构造已经包含短 schema 写事务，前置身份应保持同一类短初始化边界；collector 仍使用同一 SQL 读快照，不增加 capacity→DB写→guard 的锁环。旧备份恢复应保留库内原 identity、当前 reclamation/expired-transfers fence；恢复成相同路径与相同逻辑身份时 owner 可相同，但当前退休集合仍禁止旧 CID/AID 复活。换成另一逻辑档案必须得到不同 owner；缺 identity 的旧库只能产生新逻辑身份或保守未知，不能据路径接管旧登记。

该分析说明建议能修复哪条静态路径，并没有实施或验证它。必要后续验证至少包括：首个 CLI 失败候选无需先 files/search 即可取得正确归属；同父目录停机一致改名 A 后，B 在旧路径新 admission 不能删 A 原字节，A 按原合法 CID 可读取/重试保存字节；B 自身真实 obsolete 候选仍可回收；legacy path-only / missing identity 保守保留；恢复 fence 与短锁顺序不变。真实输入/独立 SHA、CID/AID/archive identity 及物理文件需逐项核，两个产品返回相同不足以排除同错。以上均未在本轮运行。
