# SC9 complete28 人工准备独立复审

AT-SMM-005/R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；Reviewer /root/review_complete26_prep_c；2026-11-22T10:21:07.102087+00:00。

结论：共用自动准备有效，27测试实现错误已修；完整人工full2仍需补有据的E1成功零命中观察设计/原件，最早design。其余full1/3/4准备可执行；本人工项不能直接声称完整准备通过。没有产品缺陷结论。

## 当前审阅文件摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc9/request.json` SHA256 `dbbfec023e95401a5873c8ead02f11c1d4e790fbbdecfd4f595bdf3e8165f263`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc9/result.json` SHA256 `79fbc1cee80e11211e89d48c0ae82e255228c7af33c994966c04bf79dc6a7666`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete28-sc9/request.json` SHA256 `aea1d25a8a217c8c3392018a41bcb9a4db219047e722be27ab499f794b826708`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete28-sc9/result.json` SHA256 `4cde14087ff3d3c280d748ca313ae967326e0dabf2639c5ed720852748acf866`。
- `.acceptance-local/native-v1/AT-SMM-005/debug/debug-complete28-sc9/result.json` SHA256 `0b3fc6e5cb30538f8cb44ebe42e03a67c69c29e5f753e19cd33b2916ae2c85dd`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9.md` SHA256 `78e0b6f52a1e1d6ca909ee2cca66a3c2f8f5ffe0bf76b6478a2abef6ff4cb973`。

已实际读28交接/manifest、当前设计/匹配、修订真实源码与两个JSON原件；原26/27完整criteria反查和独立技能边界仍有效。所有criteria来自A9/B5-B6，没有新增产品字段要求。

## 逐人工check

TC-005-sc9-evidence仍full1/full2/full3/full4；auto fallback仍tdd-core，empty-coverage承接additional-empty-coverage。

- full1：原3E1 offline三入口A/A-new而无D/G、实际coverage/503原因/原文及PNG/trace仍可用，26已逐张打开必要画面；当前fallback28真实pass只支持其共用义务，平台事件按原时间d80等保留。
- full2共用语义：**现在具备有效自动准备**。28只把成功缺省原因字段用get读取，保留无原因/complete字典、实际/search调用及后续fault/explicit local全部检查。两个scope真实空结果附件均实际显示success=[]/complete+complete，failed=[]/complete+unavailable+具体原因，local=[]/complete+not_requested；27未到达部分现已全部到达。无需修改产品去增加SPEC未要求的null字段。
- full2平台边界：**仍需补设计/证据**。SPEC A9首段以“每个E1平台的CLI/MCP/Web”限定并在同段要求“本机/Hub成功零命中与不可用明确不同”；E1表要求各平台A9指定路径实际通过。当前人工action仍仅“核对三入口offline-all及重连恢复，显式本机范围独立不变”，新增auto是源TestClient、没有通过已安装CLI/真实stdio/各OS浏览器的零命中。manifest原13目录之前递归已核全部JSON没有空results搜索，当前manifest仍同13目录；两个新附件也没有E1入口原件。D4/E1明确实际入口不能由API单测替代。故新auto可证明共用语义，但不能冒充3OS三入口零命中状态。最低补法是每个E1三个实际入口各一个确定无命中的有效查询，留真实请求/coverage/无故障原因，Web保留关键空结果覆盖画面，再与已有真实不可用/显式本机原件区分；不用重跑已充分的停止/补传/重启或扩大系统组合。这是26/27意见已注明的平台边界，非因仅换等价ID新增样本。
- full3：可执行。继续按26MD与当前28完整JUnit具体case核test_partial_hub_failure_preserves_valid_local_snapshot、test_local_error_still_returns_readable_hub_candidates、test_incomplete_hub_candidate_is_excluded_without_losing_valid_peers_or_topping_up、5种invalid scope；快照后Hub故障/local故障/双故障/缺全文候选完整集合/coverage和出站数量各有独立断言，不缩成只认新2auto。
- full4：可执行。limit0/51不发Hub且ValueError，Web空query400及三OS三入口断线/恢复/原文原件继续可定位，28全套JUnit按具体声明核；不称非法字段全组合已实测。

## 版本、回归与下一步

当前debug28两TC全部bindings/artifacts SHA实算一致；PID52099/52100均exit0、分别1passed/2passed，empty两原始附件真实生成。产品ba8不变；原平台d80/f45/7c按前轮完整依赖闭包与scope11/15/reconcile21补证，不只比较不变Hub一个模块。原时间与本轮观察分开保留，不将历史或当前源TestClient改标平台执行。

28 full-pytest已结束exit1，stdout SHA0bf3d923304e80b45ef8aeb64aaa06d4d91159cd8419674675df6cd56dfef2aa、inputs SHA5d4733c45c4120f5651be10cfdd9f948edec505043f0face651cc9dd360a8290；逐case核新增empty all/project均passed，失败仅SC3引用三参数。共同回归不能总称成功，也不抹去本case有效结果。

边界反例：若Web只在results为空时不显示coverage/错报Hub未查，而CLI在该状态把空成功当故障，当前正命中平台截图+源API空结果可全部通过，却违反A9指定三入口该状态。因此平台补证不是同条件下换标识；应在自然设计落实已指定的实际观察面，再取得最小实际原件。自动passed只认分配的共用checks，人工full2平台部分和正式SC9仍保持未完成。
