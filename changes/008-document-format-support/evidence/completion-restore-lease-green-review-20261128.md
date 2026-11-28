# SC11 runtime lease 恢复清单绿灯独立审查

结论：passed。仅针对 AT-SMM-008 / SC11 / TC-008-snapshot-restore-set 的本次 tdd-green，不表示 SC11、R008、完整 C1 或 E/H/X 通过。审查只读产品、测试及旧记录，只写本意见文件与 review-inbox。未读 private key、未改运行结果、未合并 PR43。

## 目标与冻结版本

- target_operation：tdd-green。
- target：green-completion-sc11-runtime-lease-v1。
- result SHA-256：2107bb813eb8bca4e40aaf7210eb88a03505366f0b96c1d436a6017904d8e13f。
- definitions/000003 SHA-256：16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633。
- design-completion-sc11-runtime-lease-v2 SHA：b435de2ea017f2086136fc50d78b8253b5908c9e2452ad1addcf7f28499e2d64。
- match-completion-sc11-runtime-lease-v2 SHA：2342f71bb302a6fa069d182c7a355a7f3f9eb6b238cee4dc50ff9ba4af7db0e2。
- 有效 red v2 SHA：fe4f60b575de7be4542d0b264f1de8f9bb321542f2815f4801edc1d50d3fe0d9；其独立 expected_failure 登记 review result SHA b016fa0fdfeb0b048c07599ec27b4833ef607ccd4a1b056bdbb2c303a5b5ff54。
- green document_protocol.py SHA：afe2b1015443955495ac6a7c8ce7b171b1a5078fa711935a32ab3e35f9fba53f；red 为 ec92e229b688c19cfb8912593f63e4996d77ede8687fffec6db676e96af238b6。

## 原始依据与修复合理性

实际打开 worktree AGENTS、008 intent/spec/plan、007 恢复约定、TRIAL_GUIDE 146/370–377、native skill 及 reviewer/development 规则。008 保留归档恢复保护；指南要求数据库、已有管理副本和持久原件/结果/传输状态为一致集，运行锁、任务目录和当前保护记录不能随旧备份恢复。指南仍要求随后停止服务；本组件使用保持运行的 Hub 定位清单问题，不产生运行中恢复数据库的支持承诺。

产品唯一差异在 DocumentGuard.prepare_restore:176 的固定排除元组增加 services。把当前文件该一项去掉后，完整原字节 SHA 精确等于 red product binding，排除集合其他项和 restore_files 未改。ProcessingService.__init__ 在 services 仅建立按 DB 路径摘要命名的 .lock 和 .json 登记；_coordinate 持有 control_lock 后写 running，整个服务生命周期持锁，停止写 stopped。待办处理 payload/state 在 SQLite hub_document_processing_jobs；原件、结果、传输在并列的 raw/results/transfers，因此排除 services 不会排掉持久任务或内容。没有改变身份、解析/OCR、300 秒、1GiB、256MiB、授权或恢复 guard。

## 红绿测试与实际结果

24 test_bindings 在 red/green 完全相同；green/source 内全部 24 文件逐字匹配。两驱动和运行命令保持。red 原始 Mac.stdout 实际 1 failed/5 passed、30.61 秒，在新测试43行发现 copied 包含 json/lock；Windows 原 run.stdout 实际 2 failed/4 passed、87.66 秒，新测试36行和旧 Hub restore_set:124 均 PermissionError，新隔离项原 JSON 明确指向活 .lock。已打开 red 独审详细报告及登记。

green 原 Mac.stdout 为 6 passed、28.75 秒，mac-junit 为6项、0失败、0跳过、28.750秒。Windows 原 run.stdout 为6 passed、90.82秒，原 JUnit 为6项、0失败、0跳过、90.613秒；两个计时观察面有正常开销差别，不混写。两平台运行租约原 JSON 均 status=running、services_excluded=true。新增项43–45行实际全到达：copied必须为空、目录整体排除、全部 json/lock都由公开排除清单覆盖。没有测试硬编码跳锁路径，也不以停服务消除活锁后再证明清单正确。

原三分支 local-private / local-sync / hub 均在两平台完整通过；每分支普通/全局两个项目，各 DOCX/XLSX成功和扫描PDF无OCR失败，共6 raw、4 results。两个 legacy 布局分别通过，未创造不存在的快照目录。每个平台4个 Server停止原件均 exit0、forced=false，实际身份包含 launcher/serving PID、ctime、argv/exe 和归属成员；Server 最后核已登记树退出并检查监听口不可达。Windows result.actual_platform=win32，Python3.14.10，is_admin=true，仅原生文件锁组件，不认标准账户 E/H 或受管服务。

## 摘要与原始归档核验

独立读取并重算全部608 artifacts、94 bindings、24 test_bindings、1 product_binding，全部符合记录。94 bindings相对red的共同路径只有 document_protocol.py 改变，另6个绑定是本次相关回归的源/helper新增绑定。实际读取271份附件JSON。回归额外6文件未复制进 source 快照，但有执行记录的SHA绑定且当前原文件已逐个重算，不称其存在 source 副本。

Mac scratch 原 tar 的301普通成员全部读取，86目录、3个current符号链接仅保留原tar/元信息，未跟随/重建。SHA 965f53a91e218498a6ef69a978aaf7d7d99fbc803dca06bc783df12ce4114af7。

Windows input tar231普通成员全部读取，input-manifest229文件逐项核验；output tar430普通成员全部读取并逐字与 verified目录相同，88目录、3个current链接仅元信息。output长度1094800与原transfer一致，SHA 9ccf8b17b536674ca5dcce20744d84df3f7ea1dffbf360c92154ee01d592c8ef。before/after源码清单均等于输入229文件；动态启动 document_formats_restart_server.py 在red输入/green输入/当前源码也逐字相同，SHA08be26fa4abc0e3eb220dd8b15cb94ff486977c7f02fe7b7f955283aca4a13c8。字体本机与远端同为2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b。create/upload/business/download/download-receipt的原命令及stdout/stderr、远端源码/结果和JUnit均保留且已打开。

## 持久数据与保护边界独立复算

从两个原tar直接读取六分支全部60个 durable blob，逐个核源SHA/长度及恢复副本原字节一致，不只相信 all_durable_exact 摘要。源原件集合与独立输入/公开下载、捕获记录SHA有逐份断言。各恢复库只在内存副本将WAL读模式头字节转为普通模式再deserialize，六份 integrity_check=ok，所列 documents/captures/state/attempts/authorizations 及适用 library/local_document_sync 元数据全部与动作前记录一致；未写归档DB。

各保留的当前 post-prepare guard 在tar内恢复副本重新核SHA；公开恢复状态两Local为conflict，Hub为conflict并提示恢复，不能凭备份重新开正文。local-private动作前无同步表、local-sync有同步表，分别实际核验。

本次 transfers为空、没有已有.documents实体，不能声称这两种持久实例已恢复实测。新增修复不改变它们的清单覆盖/复制分支，且与 services路径不重叠；这不扩大本次单项结论。

## 相关回归

已核原 regression.stdout、stderr、process记录及green result绑定：candidate_recovery + document_sync_recovery_scope 实际18 passed、1 skipped、17.86秒、exit0，stderr空。源码检查覆盖shared last-use、真实pin owner退出、旧/未知归属、复用DB路径、拒删计费、POSIX真实任务树清理、复制档案歧义以及恢复选择不能重授权其他Hub、项目重用和暂停/guard中断stage。唯一跳过是非Windows上的实际Windows Job分支；不把该跳过认通过，也不把Mac回归变成Windows回归。该套件只作附加回归证据，未产生各TC正式执行收据。

## 反例与结论边界

- 只排lock而恢复旧running JSON：新项43行copied必须为空会拦截；44行又要求整个services目录覆盖。
- 只排JSON而留锁：POSIX43行copied非空，Windows36行真实复制失败；不能用内核差异掩盖。
- 加services同时误排raw/results：原恢复项127行逐全部durable byte比较会拦截；元数据在131行另核。
- 只正确首文档/首项目或漏失败PDF：66–81行完整ID集合/状态/每份原SHA与公开原件、93–96行6raw/4results和捕获集合、102–107行每持久路径覆盖会拦截。
- 偷复用旧guard或重新授权：129行当前guard SHA、133–137行恢复阻断状态分别拦截。

自然设计与用例实现对本次有依据的行为差异充分。全部green主检查有本次实证，补充回归实际通过；按native TDD规则，review JSON省略covers，检查分配仍为snapshot-restore-set，实际断言在上述依据中说明。完整兼容、持久传输实例、真实停服恢复生命周期、普通账户安装、受管服务与E/H/X以及另一个目录正在运行的安装版full3都不在此次结论范围。提交本修复时应按AGENTS把实施调整及验证边界同步到plan；本意见不替主Agent修改计划或提交。
