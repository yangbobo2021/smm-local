# SC11 恢复清单 runtime lease v2 独立红灯审查

结论：`expected_failure`。新用例和保留的旧恢复集用例足以证明公开恢复清单遗漏运行租约排除；本轮不是准备故障或测试错误。仅针对 `TC-008-snapshot-restore-set`，不等于 SC11 或 R008 整体验收。

## 审查目标与版本

- 目标操作：`tdd-red`。
- 目标：`red-completion-sc11-runtime-lease-v2`。
- 定义：`definitions/000003.json`，SHA-256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。
- red result SHA-256：`fe4f60b575de7be4542d0b264f1de8f9bb321542f2815f4801edc1d50d3fe0d9`。
- 设计：`design-completion-sc11-runtime-lease-v2`，SHA-256 `b435de2ea017f2086136fc50d78b8253b5908c9e2452ad1addcf7f28499e2d64`。
- match/runtime 使用同名 v2。唯一实际红灯 TC 身份保持；match 中其他既有最低安装用例未被本次红灯认领。
- HEAD：`3042dfa9dd8d2b2ad91773ff3395836e1dab1391`。工作区已有其他在做变更，本审查没有修改它们。

## 原始依据与设计充分性

实际读取 AGENTS、008 intent/spec/plan、007 spec、TRIAL_GUIDE，以及 app-delivery-acceptance-native 的 reviewer、development 和 design 规则。008 B4/B5/B8及边界保留已采集字节、结果和归档恢复保护；指南146、377要求一致的数据库/管理副本/持久快照集，并排除任务目录、运行锁。007恢复冲突要求停止正文且不得自动重授权。

`ProcessingService` 在 `services/` 仅创建按数据库路径摘要命名的 json 运行登记和内核 lock。`_coordinate` 在整个运行期持有该锁；`control_lock` 在 Windows 使用 `msvcrt.locking`，在 POSIX 使用 flock。它们不属于持久原件、处理结果或续传数据。将整个 services 排除有依据，不需要改变任何 durable 字节承诺。

指南也明确“随后停止相应服务”。保持真实前景 Hub 运行并复制是定位公开清单遗漏的组件探针；并不证明支持运行中恢复数据库，也不改变用户恢复流程。SQLite使用 backup，不把活动主库单文件直接复制当一致备份。

自然设计完整保留原三分支、普通/全局两项目和旧布局，新增真实运行租约。其范围明确不认 E/H 标准用户。设计文字称CLI配置Hub，但实际配置由 `configure_hub` 公共函数完成，此沿用旧项已披露范围，不影响 prepare-restore 公开CLI结果。

## 红灯原件核对

总驱动退出1。Mac原始stdout和JUnit：1失败5通过，30.61秒。新增项实际在第43行因复制集合含 json 和 lock 失败；`Mac/00007-restore-live-processing-lease.json` 记录真实 running 及 services_excluded=false。公开 prepare-restore 成功，但do_not_restore遗漏services。

Windows实际win32/Python3.14.10；SSH组件身份is_admin=true。stdout/JUnit为2失败4通过，87.66秒。新项第36行真实复制发生PermissionError errno13，`verified/attachments/00008-restore-live-lease-copy-failure.json`直接记录锁路径。旧Hub整份恢复在第124行同类PermissionError；两个Local与两旧布局通过。旧Hub日志未打印出源路径，不能声称旧trace直接指出锁；同轮隔离项、清单、归档半复制成员和内核锁代码共同支持归因。Windows半复制的目标lock存在但为空，不代表复制成功。

`document_protocol.py:175–176` 的排除集合只有 tasks、capacity.lock、upload-queue.lock、expired-transfers、reclamation，遗漏services；第179行将整个快照根加入restore_files。公开清单与源码一致，未靠测试特判构造失败。product绑定SHA仍为 `ec92e229b688c19cfb8912593f63e4996d77ede8687fffec6db676e96af238b6`。

## 摘要、源码与归档

独立读取并重算全部605 artifacts、88 bindings、1 product_binding和24 test_bindings，没有不一致。冻结source中的24测试和驱动文件逐字节与绑定相同。runtime记录就绪；实际远端输入及before/after清单229文件相同，未用本机版本替代远端证明。

Mac-scratch-original.tar.gz 305、Windows input.tar.gz 231、output.tar.gz 430普通成员全部实际读取。Windows430输出成员逐字与verified一致，远端传输长度1096264及SHA `0ff70d3cf15838636eb29e5e16729ed4e20e151e2e9f6697ba223f2343f2fb92`一致。

两个平台各3个pytest current symlink只作为原tar/链接元信息保留，未跟随、未重建。v1采证阻塞不追认为本次业务结果；v2持久scratch及原tar正确保留了这些成员。未读取或导出private.pem。

## 持久数据与原分支

原测试每分支两项目各DOCX/XLSX成功及扫描PDF无OCR失败，共6原件、4结果。身份、状态、源raw SHA、项目以及原件下载均有逐项断言。同步表未初始化的私人Local与已初始化Local分别执行，Hub单独执行，两旧布局无快照目录也分别执行。

Mac三分支完整到达复制、当前guard保留、SQLite完整性、所列元数据和冲突状态。Windows两个Local同样到达；Hub在复制中失败，后半125–137行未到达。独立从归档重算六分支60 durable blob摘要；五个完成分支50个复制blob与动作前原件完全一致。恢复库仅在内存副本将WAL读模式字节切为普通模式后deserialize，完整性与所列元数据一致；没有改写证据数据库。初次内存直接deserialize因WAL模式报unable to open database file，该只读审查方式问题经内存模式处理解决，不是产品额外失败。

transfers本轮为空，没有已有.documents管理副本实体，不认这些样本已实测。旧测试对这些目录具有泛化复制能力并不等同真实对象验收。

## 边界反例与首个拦截位置

1. 只处理首份/首个项目，遗漏第二项目或失败候选：旧测试66–81行核完整六项身份及独立raw，93–96行核6raw/4results和独立SHA全集；清单遗漏在102–107行失败。
2. 清单包括根但错误排除某个持久blob，或复制错对象：127行逐字与冻结动作前字节比较，131行元数据比较，不靠两产品结果相同放行。
3. 只排lock而把旧running登记复制：新项43行copied必须空、44行要求整个services被排除；只排json仍会在Windows36行、POSIX43行失败。
4. 排services同时误排raw/results：旧完成分支127行失败。三个动作前状态都保留，不能被另一个状态成功掩盖。
5. 同一结果误指向首文档：每项目查询的唯一ID、源文件身份和下载对独立raw比较先行拦截。

新项44–45本次均未到达，不宣称已经通过。28行保留当前快照根覆盖结构检查，不将其外推为新的服务恢复保证。追加等价标识的样本属于可选补测，现有样本足以区分本次有依据的错误。

## 历史交叉核对

实际打开0320622源CI run46107496051 Windows authenticated-triage的5个及authenticated-details的283个选定原件，长度和SHA均符合inspection。原JUnit确有同名Hub124行PermissionError，两个Local通过；该CI结果明确标准用户非Administrators。这里依赖已有认证选定原件，未重新解密整份官方artifact，不认完整CI回收或全平台通过。

另打开restore-runtime-remote-a589867deda4420eb82c9e0604ac7b96的真实Windows初次复现stdout/JUnit/result及全部输入230、输出31普通归档成员；传输摘要一致，同为新增项复制锁失败。该早先组件也是管理员，不能替代E/H普通身份。

## 判定范围

准予本冻结v2记录expected_failure。TDD意见省略covers；仅一实际TC。尚无本修补绿灯；完整兼容、真实停服/重启恢复、持久传输实例、受管服务、E/H/X及最终需求判断继续保留。未修改产品/测试/旧记录，未合并PR43。
