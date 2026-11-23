# AT-SMM-007 状态补充设计与红灯复审 v1

本轮只审 SC15/SC16 新增两项候选，结论均为 **needs_revision**。原始输出确证 F5 文件元信息缺失及 F7 两端目录拖入指引缺失；当前候选存在独立判定串联与实际断言漏检，不能把真实的首项失败升级为整 TC 有效红灯。F6 暂停保留状态在本次 SC15 运行未到达，不予实际失败认领。未判 R007 或整个交付通过。

## 范围及原件

实际打开 AGENTS.md、changes/007-hub-document-search/intent.md、spec.md、plan.md、该变更 reviews/project-library-authorization.md、根 reviews/pr39-review-v2.md，以及指定技能及 development / reviewer / design / implementation 参考。补充授权文件实际位于变更目录的 reviews 下。

采用 definitions/000007.json，SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。程序逐对象核对 000006 的全部 14 场景及需求均原样保留，新版增加 SC15/16；本轮没有重新评旧 31 TC。两条新场景判据均能从已确认 B1–B8 推出，没有发现需退回 scene 的新增行为。

按 handoff 核对两目标 result 原字节 SHA：

| 场景 / TC | 目标 SHA | 结论 |
|---|---|---|
| SC15 / TC-007-hub-status-provenance | ba32cd179d9e0293b6e645eb94b109b8cf1f3dfadf08e987ffac8adba216189a | needs_revision / design |
| SC16 / TC-007-folder-guidance | 75083a5613263c0f9ebf31b280a22df81518698f700429f519fbe84535c2eb4e | needs_revision / implementation |

两目标分别 51/45/6/37 和 51/45/6/41 个 bindings/product_bindings/test_bindings/artifacts 全部复算匹配。复审读取时工作树 HEAD 已为 `12100dd2b1e15015bca61a738125079a34af8760`，产品绑定仍逐字匹配所交接候选；不以 HEAD 标签代替文件摘要。

## SC15

设计把独立的列表元信息与暂停保留可见状态串入同 TC。stdout 在 tests/test_document_status_contracts.py:234 调用 verify、181 取 origin 时停止；HTTP 200 原件 00026-hub-11.json 及 CLI exit 0 的 00027-metadata-cli.json 均实际缺 origin、project_ids、received_at，产品 files 入口仍直返 006 结构。因此 F5 真实存在，但 sources、暂停/恢复、共享及 Chrome 都未执行。

最上游需拆分独立设计/运行，保留旧 ID 检查去向。另外补 sources 每行独立项目/适用资格及无正文断言；现有 235–291 可放过所有 sources 误写首个项目。暂停/恢复需核完整身份集与唯一性：323–335 可放过漏掉 Q 并重复 Hub 自有行的结果，后续网页只查 P，恢复时回到正常亦可全过。此为不同动作前状态下的真实漏检，不是增加等价样本。files 已有逐行 SHA/项目独立期望和全集/唯一性，能拦只首个 files 正确或两端 files 共同写错的反例。

新 verify/moment/CLI 审计等需有已知正负样本自检；runtime smoke 只证明 Chrome/Playwright 可用。

## SC16

实际打开本次 local-web-review.png、hub-web-review.png：两端上传结果均为“example-folder：失败 · 无法读取所选文件”，该结果处没有明确目录来源指引。下方另有来源/CLI说明，只能支持既有替代发现路径。两参数都实际到 464 提示断言失败；465 后的方向指引、无上传/状态、混合上传/read 均未到达。

实际读两份本次 trace（155/179 事件），唯一 after 错误均为该提示断言，nlol@56 / ohsm@137 原值均见 isDirectory=true。使用真实 Chrome、页面 JS 及 TestClient 路由；不是 E1 网络/TLS/平台身份验收。

实现需补混合批次目录行结果与创建端指引：505 只核名字，507 只核合法文件成功，目录被假报成功仍能通过其后库/原文断言。第二次 CDP drop 必须重新取得 box 并见证本次目标；结果列表在 drop 前，首轮填充会改变布局，当前复用首轮前位置的未执行路径存在测试故障风险。禁止隐式扫描需有目录读取审计，仅读库/无上传/原文件未改不能排除“读取后丢弃”。Local 状态基线必须针对 Local；w.snapshot 当前只读 Hub DB。补新探针正负自检，并在原产品版本重取红灯。

只把其他端做错会由参数化执行与各端提示断言拦截；合法文件误取另一原文会由目标 ID 和独立正文预期拦截。额外同条件文件名属于可选补测。

## 独立意见

每份意见完成即写唯一文件并通知主 Agent，再处理下一项。JSON 仅含相应实际 TC，均未填 covers；没有登记工具、GitHub或外部服务操作，没有修改产品/测试/冻结证据。

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-hub-status-provenance-status-v1.json`：SHA `c3417ee6684269412987a08ed558a7566d91fcb0c205a61e70753af75edc572f`。
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-folder-guidance-status-v1.json`：SHA `75e0144211fe261637dfde3881c47ba14e3e63162146bbd3009ab8e373e00c74`。

本轮只读已有合成材料，不访问 ESXi、日常 Hub/VibeInsight、真实用户资料，不重跑业务或修改原始尝试。
