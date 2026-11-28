# PR #43 处理版本隔离补充意见

范围：只读核查 `6c65bc9295d49ff8ff13a6cfe07277b0504d7209` 的 `src/smm_local/document_search.py`，并实际打开冻结 SPEC B5/B6/B8、原生 SC9 scope criterion、引用编码/读取及端点版本校验。该模块现盘 SHA256 为 `216bbc5c1b6a0f8b32096c72b009d4803d2462bb6a30011c62ed6ae95dd36fa9`，与6c65原字节相同。涉及其他模块时以 `git show 6c65bc9:<path>` 为基准，不认领新的五文件 finalization patch。

结论：**确认一个 P1 级引用/结果隔离缺口。不同 processing_version 的合法候选可能被误合并；同时，同V/P但不同结果摘要的候选也可能被误当作同一副本。** 这是静态确定的分支及纯函数级检查，未运行真实同步/检索/读取实验，不是已观测的用户资料损坏。

## 首个具体位置和实际分支

首个缺口在 `src/smm_local/document_search.py:21–25`：`_identity()` 只取 `(device_id, archive_id, document_id, version)`，没有 processing_version。后续 `:241–268` 的合并分支没有补上此条件：

1. `:242` 按“全部 Local候选，然后全部Hub候选”的顺序处理。
2. `:243–245` 用上述身份键命中已有Local候选。
3. `:246–252` 只比较 `sha256`、`text_sha256`、`text_length`。即使两端 P/result_sha 不同，这三项仍相同就不会报冲突。
4. `:253–261` 仅比较重叠文字片段。正文不变时此处也不拦截。
5. `:262–267` 创建 `parts=[old.reference, hit.reference]` 的bundle，并将两端 origin_references 合在一起。
6. `:268` 把整个Hub `hit` 存回同一key。显示用的 processing_version/profile/result_sha/coverage/locations/table_context等因此来自后处理的Hub候选，而不是两个处理版本的并列结果。

`search` 的前置Hub候选检查 `:165–178` 也只验证V/rawSHA/textSHA/length等与Hub外层引用相符，没有要求它与Local处理版本相等；它不能补救合并条件。此处的缺失不需要伪造Hub响应：两个端点都可分别返回自己合法的当前快照。

本次只用内存字典，将实际源码 `_identity` 函数通过AST单独编译后调用，未导入/实例化Archive、连接数据库或启动服务。输入为同 origin、V=1、同原SHA/文本SHA/长度/片段，Local P=2/resultSHA=A、Hub P=1/resultSHA=B。实际输出：

```text
key_equal = True
guard_digest_conflict = False
overlap_conflict = False
processing_pair = (2, 1)
result_pair_differs = True
```

其中 identity 相等是当前不可变纯函数的直接结果；两个guard布尔值是对源码已有比较字段的内存核对。没有调用真实 `search()`、签发bundle或模拟网络成功来冒充集成证据。

## 可到达的用户路径和影响

正常场景是：本机资料V1/P1已同步到Hub；用户暂停项目文档同步（B6明确保留Hub旧快照），然后在创建端对同一保存原件用新配置/profile显式重处理，成功得到V1/P2。Word正文不依赖OCR语言配置，完全可能原SHA、规范正文SHA和长度都不变，但profile及完整结果SHA改变。B5明确允许并要求这种只推进处理版本的发布。用户随后用默认联合检索查询该正文词，两端旧/新快照均可独立有效。

在上述合法双候选前提下，当前分支会把两份结果压成一条 combined，并显示Hub的P1/结果元数据；原本应显示的本机P2独立条目消失。这不是“旧Hub必须先接收新版本”的要求，暂停和待同步状态本来就允许两端暂时不同。

更关键的是bundle的读顺序：

- `src/smm_local/references.py:85–88` 只按输入顺序去除重复引用字符串并签名，没有验证parts为相同处理快照。
- `document_search.py:327–334` 顺序遍历parts，**直接返回第一个成功读取结果**。本场景先读Local P2，且未与展示用的Hub P1/resultSHA比较。
- 因此用户点击上面展示P1的同一引用，可以得到P2的正文读取响应、profile/coverage/定位或 original-info。正文在该示例中相同，不代表引用所声明的处理版本也相同。若处理结构/覆盖不同，不能保证沿Hub候选展示的table_context得到同一处理结果；不声称本次已经实跑出错误表格。
- Local part后来失效时，`:332` 捕获其错误再读Hub P1。同一个外层bundle可以先返回P2，再退回P1，而不是只在同一处理快照的等价副本间回退。这个推演基于明确的读取顺序；没有运行服务或伪造过期响应。

显式 `--local` 不进入联合候选合并；直接Hub入口也只读Hub自己的精确引用。这两条是现有可用绕行路径，不能使默认联合路径满足规格。

## 现有检查为何没有阻断

单端检查确实存在，不能误说所有版本核验都缺失：

- `src/smm_local/documents.py:525–528` 将P/resultSHA/rawSHA写入新格式搜索引用；`:577–579` 读取时核对该端当前P、结果及原件摘要。
- Hub外层引用 `src/smm_hub/documents.py:849–854` 带P/resultSHA，`read():930–933` 进入上述内层读取；每个part的旧处理版本会在自己的端点被拒绝。
- Hub接收发布 `documents.py:677–681` 拒绝同V的旧P以及同V/P异resultSHA覆盖其当前快照。这防止接收覆盖，并不要求仍保留P1的Hub与已到P2的Local在搜索时同步同版。

这些检查验证“这个part是否属于它自己那端的当前快照”，不会验证“bundle内所有part是否等于外层搜索展示的处理快照”。Local P2和Hub P1都各自合法，首part自然通过。问题发生在联合合并，而不是靠伪造签名绕过端点校验。

同一根因还有另一分支：若同origin/V/P却 resultSHA 不同，但raw/textSHA/长度及重叠文字相同，当前 `:246–261` 仍全部放行并bundle。规格要求把这种情况列为冲突、反映覆盖；不能只把resultSHA塞进唯一键后作为两个合法版本并列。

## 规格依据及适度处理建议

- B5要求处理版本单调、配置/profile或结果/覆盖变化推进P，引用绑定内容/处理版本及原件/结果摘要。
- B6把同一清单中的原身份、V/P、profile及摘要绑定成套，暂停保留Hub旧快照；它没有授权查询层跨处理快照混合。
- B8直接规定“合并副本时还须相同processing_version及结果/原件摘要”“同原件不同处理版本明确分开”；相同身份/V/P但异结果摘要应按冲突反映覆盖。
- `.acceptance/native-v1/AT-SMM-008/definitions/000001.json` 的SC9第一条scope criterion明确“同源同处理版本去重、不同处理版本不混”。这属于已确认范围，**不是新增建议性要求**。

建议按内容身份及处理版本分组，并在同一V/P组内检查原件/完整结果摘要一致后才合并；异P保留独立候选，同V/P异摘要明确冲突。bundle的构造/回退也应保证只能在同一成套处理快照间选择，不能通过固定选择Local或Hub掩盖问题。旧TXT/Markdown缺少P的既有行为需保持兼容，不能无条件要求它们提供新格式字段。

可验证通过条件：用两个端点各自合法、同原身份/V且正文不变的P1/P2候选，默认联合查询在limit足够时返回两条且分别标明端点/P/resultSHA；各条text/table/original-info都只能沿自己处理快照读取，某一端失效后不能回退到另一P。相同P/相同双摘要能合并并保留现有同版回退；相同P/不同resultSHA必须报冲突和覆盖不足。补真实同原件重处理、暂停/待同步与恢复后各自旧引用的集成证据，再判断交付通过；本补充不提供或伪造该实测。

旧 `independent-review-v2.md` 保持原字节，SHA256仍为 `91cfd5c6efdcd43a05284d2c04f8ac36e235a99be792cf937d189d6299bdfbeb`。本次只新增本补充意见，不改源、不运行产品/验收/保留测试、不写远端、不重评新五文件。
