# Canonical 候选回收：独立删除安全审查 v1

验收 ID：AT-SMM-008。结论：**needs_revision（产品删除安全）**。发现一条可使另一独立档案的合法上传身份被永久作废、已接收分块随后被删除的实际路径。其余下述范围未发现新的确定误删或写锁死锁路径，但本次静态审查不构成绿灯通过，也不关闭完整 GC / SC10 / R008。

## 范围与证据边界

工作树 `{checkout}`，HEAD `f1334a275e89c5079313eb7bdfc8436b62c422b7`，审查六个未提交产品文件及其直接调用上下文。实际阅读了 AGENTS.md、008 intent/spec/plan、`implementation-notes-v1.md`、两端 `review-gc-capacity-{local,hub}-red-v3/result.json`，以及 snapshots / processing / transfers / managed uploads / Hub processed receiver / protocol 和来源刷新、资料管理、恢复、锁实现。

本轮仅读取已有文件与执行日志，没有运行测试、native、构建或远程动作，没有修改产品、测试或既有证据，没有登记 native 或提交 Git。只写本报告。参考了原生交付验收技能的 reviewer 判据要求；本报告不是正式 native green Reviewer 回执。

首次读取 `green-sc10-canonical-capacity-local-v1` 时顶层结果尚未产生；随后按主 Agent 的完成通知重新只读日志和收据：主项 stdout 为 `1 passed, 1 warning in 131.48s`；配套回归为 `2 failed, 7 passed, 2 skipped, 1 warning in 140.41s`，exit_code=1。最终顶层 `result.json` 为 `status: blocked`，reason 为 `the original test or project regression did not pass`。这里只记录观察事实，未据主项通过判绿灯 passed，也未把本机结果代替 Hub。两项回归失败另见 F2。

审查时六文件 SHA256：

| 文件 | SHA256 |
|---|---|
| src/smm_local/document_snapshots.py | ea099fa6b9a8fa9125eceed3deae5d4c07eb41b1d3c39774ad3703e5e3b19f84 |
| src/smm_local/document_processing.py | 50a1acbd9431a3e24759e62ba11e64be2c3adb459e79568b4add9b1da88d1a1b |
| src/smm_local/document_transfers.py | 397d7cbc3c123c14183d9e98523b252123040f19bc2cb439ba38c23da895cd27 |
| src/smm_local/managed_document_uploads.py | ac7dfbef07b06afebade7033bd786bc2c90a490b6d2134a0a5d8b59a781c12e0 |
| src/smm_local/document_protocol.py | ec92e229b688c19cfb8912593f63e4996d77ede8687fffec6db676e96af238b6 |
| src/smm_hub/processed_documents.py | 92f6defe477b4dc98a1683acf7c27d06b11616fa8de8b24de8799fcfee5bb8ea |

## 先核原始判据

SPEC B5 要求最新合法候选不静默过期，合法替代/移除/最后连续授权失效后，先拒绝失效 CID/AID 与资格，再回收无其它用途的字节；另一连续来源仍有效时不得取消当前候选。B7 要求上传身份绑定当前项目、档案上下文与内容，支持续传，旧提交不得复活已移除资料。B9 要求未 commit 传输 24 小时可回收，已 commit 候选按 B5 而非 TTL 保留，256MiB 接受前预留且不挤掉当前可重试候选。B6 要求接收阶段及回执保护成套保存和控制身份；A6 明确两本机档案身份独立；C1 要求逐适用目标及独立真值，不以两个产品集合相等代替正确性。PLAN 修改职责另明确“额度预留和孤立文件回收不撤掉合法引用”、字节锁不跨解析/网络/查询，保留归档恢复保护。

因此，拒绝旧身份、独立档案不串退役、连续授权与当前候选保留、在途写入保护及永久恢复 fence，均能由既有契约推出，不是本轮新增产品行为。当前容量子例只解决已知独占 canonical 候选，不足以宣称整个 GC 完成；未知/共享/崩溃 pin 保守保留是本候选明确边界。

## F1 — P1：跨档案 receipt 关联缺少 archive_id，可误退休合法 UID 并回收其 incoming

位置：`src/smm_local/document_snapshots.py:115`、`:123–130`，根因是共享目录扫描和仅当前数据库 receipt 集合的关联范围不同。

实际前提与动作链：

1. 两个合法独立档案 A、B 使用同一父目录下不同数据库文件，例如 `archive-a.sqlite3` 与 `archive-b.sqlite3`。`Snapshots.__init__:24` 把二者都映射到父目录 `.document-snapshots`；产品没有要求两个 DB 必须处于不同父目录。`--db` 支持独立档案，且 PLAN 已明确记录同父目录不同 DB 共享队列锁的既有边界，不能假定这类档案不存在。
2. 两档案分别合法使用相同 `submission_id=S`。该值只由 `ManagedDocuments._submission:86–90` 检查非空字符串和长度，`document_library_submissions:70–71` 的唯一性限于各自数据库，没有全机唯一约束。`ManagedDocumentUploads.begin:102–103` 正确绑定各自 `archive_id=material(db)[0]`；`BlobTransfers.begin:191` 的 UID 摘要包含 archive_id，所以 A、B 此时有两个合法独立 UID，不能把它们当同一提交。
3. A 的 S 上传曾 commit 并得到 receipt；随后 A 合法替代/移除其候选，使 receipt 所指 CID/AID 在 A 的扫描中属于 `cids/aids`。B 的 S 上传仍有效、尚未 commit、未满 24 小时，已有一个或多个真实分块，也可采用与 A 不同 SHA，避免共享正文干扰判断。
4. A 的下一次普通 `put` 或 `transfers.begin` 在容量锁内触发 `reclaim_candidates`。`:115` 只从 **A 的数据库**建立 `receipts[submission_id]`。`:123` 调用 `_states(self)`，而 `_states`（transfers.py:30–55）遍历 **共享 root 的全部传输**，包含 B 的 UID。
5. 对 B 的 state，`:125` 只检查 purpose 与 submission_id，取到 A 的 S receipt；没有核 binding.archive_id、归属库或与 receipt 的完整绑定。`:126` 因 A 的 CID/AID 已退休而为真，`:128–129` 给 **B 的 UID**持久写入 `expired-transfers/<B-UID>`，也不把 B 的 blob 加入 protected。
6. B 的后续 binding/part/commit 经过 `BlobTransfers._load:135–137`，立即按过期拒绝，即使 B 原项目、CAS、候选状态和真实年龄都没变化。下一次 admission 的 `reclaim_expired:71–89` 认该 marker 为过期；若无其它 live transfer 共用 B 的 SHA，就 unlink B 的 `.incoming-<sha>`，释放 B 的预约与已收字节。此处不查 canonical owners，故多 owner 保守策略无法拦住。

这不是“尚未实现共享根回收”的保守多留问题，而是对另一个合法档案作了错误的失效判定并实施破坏。持久 fence 的先后顺序虽然正确，但被 fence 的目标错误，恢复排除 marker 后身份还会持续失效。仅同库双目标、不同项目、不同 SHA 或不同状态的容量用例无法触发这一关联范围差异；必须存在第二独立 DB 与相同 submission_id。

修复方向：先证明传输 binding 属于当前数据库的档案，再使用当前库 receipt 推导 obsolete；无法证明归属的传输保持 live/protected。不要只比较 S，也不要把所有同父目录档案的全量状态据 A 的 receipt 作废。修复后的有界验证应保留 A 的真实退休正控，分别核 B 未 commit 已收分块、B 已 commit 当前 receipt 可回放两种状态；让 A 的 admission 实际触发回收，独立核 B-UID 没有 marker、B 已收分块字节和年龄不变、B 能按原 UID 续传/commit。至少两个独立 B 目标可区分只照顾首 UID；用不同 SHA 与源字节核验，不能只比较两个产品返回集合。

## F2 — 已实证回归未通过：合法 replay 的 begin 先执行 GC，改变永久元数据

这项是本轮同版执行中的实际失败，与 F1 的静态多档案路径分别保存。`regression.stdout` 两个失败均在 `test_document_formats_update_replay_c1.py:127` 的 pending replay 内，最终由 `:91 assert state(server)==before` 拦截。日志显示 SQL tables 部分一致，`saved_bytes` 不同：出现 `expired-transfers/<uid>`，`reclamation/retired.json` 摘要改变。`state` 的原始定义（`test_document_formats_update_replay.py:27–37`）扫描真实 document SQL 表和 `.document-snapshots` 下除锁文件外的所有文件摘要，所以这不是界面或内部 ID 误比。

可达调用顺序与失败一致：当前 V2 已合法 commit、pending worker 被真实 gate 挡住，V1 已发布仍可读；`replay:80–91` 冻结状态后依次 begin / 重复同块 / 异块拒绝 / 重复 commit。`ManagedDocumentUploads.begin:104–107` 已先确认该提交是当前 receipt；但 `BlobTransfers.begin:193–202` 在检查既有 folder 并返回已存状态前，先调用 `reclaim_expired` 和新增 `reclaim_candidates`。GC 将 V1 的旧 CID/AID 退休，并给对应旧 UID 标 marker，从而使“只回放当前提交”的请求产生新的永久退休副作用。重复 part 本身不触发 GC，重复 commit 的短 pin 正常删除不留文件；新增副作用最早位于 begin 的提前 GC。

SPEC B6/B7 规定重复回执/提交幂等、当前身份可续传；既有 PLAN 的 managed-update-replay 已验证 pending/ready 现身份回放与完整保存状态不变。本轮保持了现有测试字节，故这是实际回归未通过的修订依据，不能忽略后把容量主项叫 formal green passed。修复可在容量锁内先验证并返回匹配的既有 transfer，只有真正新 admission 再执行 GC 与预约；仍需保留过期身份拒绝和异 binding/异 payload 拒绝，不能直接把所有旧 folder 当成功。

同时准确限制这项证据：B5 本身允许退休确实已失效的旧身份，所示日志没有证明被退休 V1 仍是合法可重试候选，也没有证明旧发布 canonical 字节被删除。因此 F2 不能冒称“合法原件误删”的实证；“所有内部 GC 元数据在成功 replay 时必须逐字不变”比单纯业务幂等更严格。保留既有回归并采用上述无新增准入时不做全局 GC 的修复能同时满足当前测试和业务契约；若选择改变该既有观察边界，须先明确论证并独立复审，不能仅删除断言来清红灯。

## 其余删除安全与锁顺序核对

### CID/AID 的退休及持续授权

`reclaim_candidates:97–118` 用一次 `BEGIN` 的 SQL 一致快照读取 publication ledger、current/published、captures、attempts、authorizations 和 stages。当前 CID 只有同时命中 document current、未退休、至少一个 active 且 revision 与 source 相符的授权才存活；对所有 capture 行循环，不按首目标或 source status 简单判断。`authorized:198–200` 采用 EXISTS，另一来源失败不会取消仍有连续授权的 CID；`Documents.refresh:424–428` 的正常 refreshing 不改变 revision，故刷新期间原有授权仍能保护当前候选。真正 set/remove/明确缺失等授权撤销路径与 B5 相符。

退休集合 `:121–122` 先通过 fsync/replace 的 `atomic_json` 持久写入；随后才处理 UID marker 与 canonical unlink。创建端 `authorized`、process 入口、publish、retry_target 均检查相应退休状态；旧 DB 把旧 current/latest 恢复回来后不能仅靠旧 SQL 行重新得到处理或发布资格。历史已发布内容不靠 CID 可重试资格维持物理保留。未发现同一正常创建流程中把已退休旧 CID 重新变成合法 current 的入口；新合法采集生成新 CID/AID。

### canonical 所有权、共享 SHA 与未知文件

`_own_blob:58–65` 在容量锁内注册数据库绝对路径 owner；既存未知 blob 不因本次观察就推断独占。新建 blob 先替换到 canonical 再原子登记 owner；在两者之间崩溃，缺 owner 文件保守留下。已登记同 SHA 被另一库 put/commit 时追加 owner，删除循环 `:135–137` 仅接受精确 `[当前owner]`。因此正常经这些写入入口登记的另一档案相同 SHA，不会被当前库无引用推导为可删；两库登记后即使其中一方退休，仍保守多留。未知 `.pending`、`.incoming` 或非 owners 项不进入 canonical 删除循环。

这项安全性质不等于能够回收共享 SHA 的最后用途：没有 owner 释放与全库用途证明，所以已多 owner 字节会持续占空间。该缺口属于回收能力未实现。不要用它掩盖 F1，F1 在 UID/incoming 分支绕过 owners。

### put→metadata / processing→attempt / commit→receipt-stage

`capture:203–209` 在 put 之前建 raw pin，覆盖 put 后、等待创建端 guard 及 metadata 事务完成前的窗口。处理入口 `document_processing.py:10–11` 的 raw pin 覆盖 worker 读取；`:34–38` 的 result pin 先于 put，直到 attempt 的 result_sha 更新事务退出。旧任务在 pin 存续时被替代，可以退休其身份，但不会删其正在使用的正文；任务之后仍必须过 publish CAS 和退休检查。

`ManagedDocumentUploads.commit:117–119` 的 raw pin 覆盖 transfers.commit 到管理副本替换、capture/job/receipt 同事务完成；`ProcessedDocuments.commit:77–79` 同时 pin raw/results，覆盖 transfers.commit 到短 guard+SQL stage 事务完成。尚无 receipt 的 committed transfer 不按 TTL 过期，扫描会把它当其它用途保护；已保存 Hub stage 的两个摘要也进入 protected。正常异常退出释放 pin 后，仍由 SQL 当前候选 / transfer / stage 等用途决定存活；进程崩溃残留 pin 保守留下。

### SQL、capacity.lock 与 Hub guard

容量锁内 GC 只有短 SQL 读快照，没有调用 Hub guard 或 DB 写事务；读事务在持久退休及物理删除之前退出。Archive 初始化 WAL；普通 DB 写路径没有在持有写事务时再进入这些 pin / put。process 的 raw pin 创建已释放 capacity 后才 `BEGIN IMMEDIATE`，result pin 同理；pin finally 发生在内层 DB/guard context 退出后。

Hub begin 是 guard→capacity→SQL读；Hub commit 新 wrapper 先短 binding/短 pin 并释放 capacity，再进入 `_commit` 的 guard+SQL阶段，未形成 capacity→guard 的反向嵌套。路径 capture 的 pin 也不持 capacity 等待 mutation_context。已读直接调用中未发现新增写锁死锁环；这是静态路径结论，没有运行跨进程并发或 Windows 锁测试。

### 历史发布、未知崩溃用途与恢复 fence

publication ledger 的全部历史 raw/results 与 current published fallback 在 `:98–101` 进入保护集合，因此旧 ready/partial 发布字节不会因新失败候选或授权撤销转成可回收 canonical。当前合法候选不靠 TTL 存活；配置变化也不直接取消其原件。暂停发送控制不参与 authorized 判定，符合 B5。

`DocumentGuard.prepare_restore:174–176` 在既有过期 marker 排除之外加上 `reclamation`，配合 `atomic_json` 的文件 fsync、POSIX 父目录 fsync，保留当前退休集合、owners 与 pin，避免旧备份覆盖 fence。按既有受支持恢复流程停止服务并遵守 do_not_restore 时，未发现 DB 单独回退复活已删旧 CID/AID 的新路径。实际旧 DB 恢复、跨进程恢复、Windows durable/reject-delete 尚无本轮执行证据，不据此认验收通过。

## 容量子例能证明与不能证明的边界

现容量测试 `test_document_formats_candidate_gc.py:234–271` 真正建立普通/全局×none/ready/partial×两份共 12 个独立目标，`:278–310` 逐个替代、触发准入和移除，不能仅首目标正确就通过。`:186–188` 对每个当前候选检查身份/状态及独立原字节；旧发布不仅前后产品结果相等，`:193–194` 有源定义全文 oracle，原件 `:209` 对源字节，表格另经 Creator.read 的独立真值核验。仅两边重复/误用同一目标并不能普遍逃过这些检查。

但它是单个 client.db 的档案，所有传输完成（`:164–167`），submission_id 用独立 uuid；因此 F1 的“第二 DB、相同 S、仍有效未 commit 分块”动作前状态没有进入，现断言即使全通过也排除不了 F1。它也没有证明共享根最后 owner 释放、无用 results 的所有状态、在途屏障、未知文件/崩溃 pin 回收、stage 失效回收或恢复全矩阵。两端 v3 expected_failure 仅证明原产品独占 obsolete canonical 未释放容量，不能当这些缺口已取得红绿灯。

保守多留的 shared owners、无 receipt committed transfer、全部 Hub stages、崩溃 pins、未知旧 canonical 和 Windows PermissionError 后仍计费的文件，按本候选实现说明继续保留。它们可能阻止新准入，属于未完成的回收场景与必要验收，不应改称“删除安全失败”；F1 则已经有可达的身份及字节误回收推演，应先修产品再以新增对应状态和同版容量证据复核。
