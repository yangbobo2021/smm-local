# Canonical 候选回收：独立删除安全修订审查 v2

验收 ID：AT-SMM-008。结论：**v1 的 F1 误归属退役路径与 F2 新增 canonical GC 回放副作用，在 v2 对应代码路径中已阻断；本轮未发现新增的确定误删、身份误退休或写锁死锁问题。** 这是静态修订结论，不是 native green passed。多档案相同 submission_id 的真实分块及当前 commit 回放必要补测尚未执行，不能把该项标为实证通过；完整 GC / SC10 / R008 仍未关闭。

## 审查版本与行为依据

工作树 `{checkout}`，HEAD 仍为 `f1334a275e89c5079313eb7bdfc8436b62c422b7`。沿用上一轮已实际阅读的 AGENTS.md、008 intent/spec/plan、原生 Reviewer 判据及两端 v3 expected_failure 证据。本轮重新读取 `candidate-v2-fix.patch`、六文件当前 diff、v1 冻结源及 SHA 清单，并实际核当前源码与直接调用上下文。六份 v1 冻结源全部匹配其清单；v2 只进一步改变 snapshots / transfers / managed uploads，另外三文件与 v1 冻结源逐字相同。

| 当前文件 | SHA256 |
|---|---|
| src/smm_local/document_snapshots.py | 9c0404b342f5508a53092991bb4b918abcfaae3fe67f34ec637a8da61dadd6dc |
| src/smm_local/document_transfers.py | 7f3bd9271ab183140a6d9a9670f28bd743f11b671718ef4f873da11d78a7c86f |
| src/smm_local/managed_document_uploads.py | 8694ee21d4c7fea094f4fd829a32a54e90cfd0a7efa4659e06bda1c49cfc45b5 |
| src/smm_local/document_processing.py | 50a1acbd9431a3e24759e62ba11e64be2c3adb459e79568b4add9b1da88d1a1b |
| src/smm_local/document_protocol.py | ec92e229b688c19cfb8912593f63e4996d77ede8687fffec6db676e96af238b6 |
| src/smm_hub/processed_documents.py | 92f6defe477b4dc98a1683acf7c27d06b11616fa8de8b24de8799fcfee5bb8ea |

原始准则没有变化：B5 的当前合法候选、连续授权、不可复活 CID/AID、先拒绝再删除；B7 的档案/项目/提交绑定与原 UID 续传；B9 的未 commit 24 小时和已 commit 按资格保留；B6 的成套接收与重复回执幂等；A6 的独立档案身份、C1 的逐目标和独立真值，足以推出本轮修复目标。没有把“所有内部维护元数据永远不变”额外提升为 SPEC 新行为；F2 沿用已实证回归与上一轮的准确边界。

本轮未运行测试、native、构建、远程动作或其它业务操作，未修改产品、测试、既有报告和执行证据，没有提交 Git。只读源码、补丁及冻结材料，只写本报告；没有等待或评判正在串行执行的 v2 绿灯结果。

## F1：归属证明阻断另一档案相同 S 的误 fence

`document_snapshots.py:115–117` 在原 `BEGIN` 只读一致快照内直接读取 `settings['archive:identity']` 并 JSON 解码。它与 `references.material:14–18` 读取的持久身份采用同一表示；但回收器没有调用 material，因此不会触发其缺材料时的 `BEGIN IMMEDIATE`、建表、初始化身份或缓存写入，也没有引入 capacity.lock 内的 SQL 写事务。身份缺失时为 None，不猜测另一个身份，走保守保留。

`:128–129` 必须同时满足 purpose=`managed-original`、device_id=`managed`、binding.archive_id 与当前 SQL archive_id 相等，才拿当前库的 submission_id 查 receipt。三个值对应 `ManagedDocumentUploads.begin:102–103` 服务端固定创建的命名空间：purpose/device/archive 不是网页载荷可任意替换的字段。设备投影没有这个 managed purpose/device 组合；两个真正独立档案由各自 material 生成并持久保存不同 archive identity，不能因同父目录、同 S、同 SHA 或同项目序号跨过 archive 比较。

对 v1 的实际反例重新逐条件推演：A 的 S 已失效并在 aids/cids，B 仍有效、同 S、未满 24 小时且已有分块，A 新 admission 扫描全共享 root。B 的 purpose/device 虽相等，archive_id 与 A 不等，local_upload 为 false，receipt=None，obsolete 为 false；`:134` 把 B 每个 blob 纳入 protected，`:132–133` 不给 B UID 写 marker。下轮原 `reclaim_expired` 既无误造 marker，B 又未达到 TTL，故不清 B incoming。B 已 commit 当前回执也经过同一 false 分支受到保护，不依赖 canonical owners 来补救错误关联。

对 A 的真实失效正控：三个归属字段均真，当前库 S receipt 正确命中；只要该 receipt 的 CID 或 AID 已在退休集合，`:130–133` 仍先持久写 A UID marker，再允许后续物理清理。新条件没有把自身真实 obsolete 一起跳过。A 的当前 receipt 则 CID/AID 不退休，继续加入 protected；只有 capture 被较新合法采集替代、attempt 被较新重处理替代或最后连续授权失效等 B5 状态才进入 obsolete。

这足以在代码层阻断 v1 F1 所述“两个独立身份共享 root、相同 S”的路径。把同一 SQLite 备份复制为另一个路径并保留同 archive identity，是同一逻辑档案的副本，不能借本结论声称已经验证了任意复制库的分叉运行/恢复行为；本轮没有新增或执行此类场景。

## F2：既有 folder 返回先于新增 canonical GC，期限及异载荷拒绝保留

`document_transfers.py:193–202` 仍在同一个 capacity.lock 中操作。先执行原有 `reclaim_expired` 并核永久 marker；folder 存在时调用 `_load`，再完整比较 state.binding 与 state.blobs，最后 `_status` 返回，均发生在新增 `reclaim_candidates` 之前。因此 v1 pending/ready 当前 replay 不再触发 canonical CID/AID 退休或给旧 canonical receipt 新写 marker。只有没有既有 folder 的新 admission 才走 `:202` 的 canonical GC，随后按原路径检查共享长度预约、建 state、核总容量。

关键前状态逐项保留：

- 当前合法、已 commit：`_load` 不套未 commit TTL，binding/blobs 必须完全相等，返回相同 UID/已收块，不改 created_at、不重建预约、不重新消费容量。
- 当前合法、未 commit 且年龄不足 24 小时：同样读取现 state 返回，原分块及创建时间不重写；不会靠 begin 反复刷新 TTL。
- 已有 marker 或未 commit 达到 24 小时：仍由 reclaim_expired / `_load:135–154` 持久拒绝，不因提前返回而复活。
- UID 相同但 binding 或 blob SHA/长度改变：`:199–200` 在 canonical GC 前拒绝；管理入口还有 `_retry` 指纹校验，未放宽同提交异载荷。无 marker 的同 UID 异载荷也不能绕到新 admission。
- 管理 candidate 已被替代/移除：上层 `_check_current_upload` 的当前 receipt / CAS 检查仍先于 transfers.begin，未因 folder 存在就授权旧上传。

准确边界：**只有本次新增 canonical GC 被移至新 admission；原 TTL `reclaim_expired` 仍在既有 replay 前执行**，可能清理共享 root 中已经真实过期的其它未 commit 传输。这是原实现及 B9 授权的维护路径，不等于全目录所有字节对任何 replay 都永久不变。v1 两项实际失败是新增 retired/expired canonical 元数据副作用，代码原因已移走；是否两端既有 regression 同版重新通过，必须读后续正式执行与独立 Reviewer 结果，本报告不预判。

## 补充 AID 检查及其与现有保护的关系

`ManagedDocumentUploads._prior:68–70` 在 attempt/doc 存在性之后加 retired AID 拒绝，防旧 DB 恢复了相同 current/latest/receipt 时绕过永久 fence。它在返回 prior 之前执行，不会为旧回执新建 job、恢复 CID 或写正文；normal pending/ready/current AID 不在退休集合，不影响合法回放。后续原 current capture/latest attempt、项目成员和 authorized 检查均保留，CID 退休仍由 authorized 拦截。这是 B5/B7 旧身份不可复活约束的补齐。

`capture_metadata:225–229` 的无变化复用条件增加 `not retired(latest_attempt)`。正常持续授权、同原件/profile、current=published 且最新 AID 未退休时原复用路径保持；另一重叠来源失败也不会仅因此让有效 AID 退休。旧 DB 回退到已退休 latest AID 时不再返回 reused token，而在明确 refresh、source revision/refresh_id 校验和原件已保存的前提下生成新 CID/AID，既不复活旧身份，也不拒绝用户新的合法采集。原 published_capture/result 字段直到新成功发布才原子替换，旧历史 ledger 仍保护其完整原件/结果。

两检查都只读退休 JSON，不获取 capacity.lock、不新增长 SQL/控制锁。即使退休文件异常导致读取抛错，路径会保守失败，不会据未知状态删除正文。没有为了快速复用而绕过授权或处理发布 CAS。

## 其余安全结论的延续与未完成范围

本轮三文件修改没有改变 v1 的以下机制，已重新核直接调用：GC 的 SQL 一致快照在删除前关闭；capacity.lock 内不获取 Hub guard、不调用内容解析或 DB 写事务；capture/raw processing/result pins 覆盖 put→metadata、读取与 result→attempt；管理上传 raw pin 覆盖 commit→capture/job/receipt；Hub raw/results pin 覆盖 commit→stage，capacity 释放后才取短 guard/SQL 写事务。未发现新的反向锁嵌套或写锁环。

全部发布 ledger、current published fallback、仍连续授权的 current CID/latest attempt result、接收 stage、无 receipt committed transfer 及持久 pins 仍进入保护集合；exclusive owner 条件与 unknown/shared 字节保守策略不变。退休集合仍先于 UID marker 与 canonical unlink 持久化；恢复排除目录仍包含 reclamation 和 expired-transfers。项目暂停发送不进入本机采集授权判据；旧发布历史与当前候选的作用没有混为一谈。

目前必要实测边界明确如下：多档案同 S 的 B 未 commit 真实分块、B 已 commit 当前 receipt 回放，以及 A 自己真实失效的 marker/清理正控尚未执行。不能只验证两个返回集合相等：必须独立核各 archive_id/UID、B marker 不存在、B 已收源字节/created_at、按原 UID 续传并完成、A 的实际退休及准入回收；至少覆盖两个独立 B 目标来排除只保护首个 UID。此处只列验证义务，没有实现或运行新用例。

共享 SHA 最后 owner 释放、崩溃 pin 的安全回收、无用 stage/无 receipt committed transfer 的最后用途证明、未知旧字节、旧 DB 真恢复、多进程在途屏障和 Windows in-use 拒删，仍按 v1 报告与 implementation notes 属于保守多留或待验能力。容量 v3 红灯、v1 主项通过、以及正在运行的 v2 容量/回归都不能替代这些场景。本轮认可具体静态修订，不给 native passed、不把必要补测或完整 GC 标成已完成。
