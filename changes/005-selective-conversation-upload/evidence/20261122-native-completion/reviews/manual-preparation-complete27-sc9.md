# SC9 complete27 人工准备独立复审

AT-SMM-005/R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；Reviewer /root/review_complete26_prep_c；2026-11-22T10:08:38.107051+00:00。

结论：needs_revision，implementation。自然设计补上了成功零命中，但新增自动断言遇测试错误提前退出，人工full2不能引用为完整通过；其余分项保留可观察准备。没有产品缺陷结论。

## 本轮审阅文件摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc9/request.json` SHA256 `dbbfec023e95401a5873c8ead02f11c1d4e790fbbdecfd4f595bdf3e8165f263`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc9/result.json` SHA256 `79fbc1cee80e11211e89d48c0ae82e255228c7af33c994966c04bf79dc6a7666`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc9/request.json` SHA256 `f7732c12a637cf261a626e2af128c82606f39a0a80c2ec8efb7ee27e686a2fde`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc9/result.json` SHA256 `79f5226389e6d5f44473b88ab79c050f20bc724db3d39af72270e5adb5bd2511`。
- `.acceptance-local/native-v1/AT-SMM-005/debug/debug-complete27-sc9/result.json` SHA256 `b809f0706a4abb29547c44eab98375d8d54462a68c160fc64cd43d1f68376540`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9.md` SHA256 `932903424de78d706bcc80be4c9fc3f5223ede544b6af19f171097c13eeae6f5`。

本轮实际读取complete27交接、manifest、PLAN12.4、当前设计/匹配与全部debug源/输出；沿用已实际读过的确认SPEC A9/B5–B6、AGENTS及技能边界标准。原26准备意见是历史独立意见，未改写。

## TC与逐check

TC-005-sc9-evidence仍分配full1/full2/full3/full4；新增TC-005-empty-coverage分配additional-empty-coverage，原fallback仍tdd-core。场景原文没有被改成“必须成功含某null字段”。

- full1：准备可执行。原13目录中三E1主流程offline三入口只A/A-new、排除D/G、coverage complete/unavailable、HTTP503，原PNG/trace/CLI/MCP原文仍有效；之前逐张看过的三个offline-search.png未改，可在本轮正式核验逐附件绑定。fallback27真实通过只支撑tdd-core。
- full2：需修订implementation。补充步骤已明确引用empty-coverage27的两scope和三种查询状态；实际两个参数成功空列表与complete/complete已达，success强制索引fallback_reason引发KeyError。SPEC只需无失败原因；combined正常返回没有该键，不能据此称产品故障。失败注入、显式本机、真实Hub搜索调用检查、evidence写入均位于首错之后未到达，无附件，不能人工依据设计expected补成通过。保留已达结果并修最小断言后重新debug/复审；实际E1三入口零命中可在范围对应的真实观察中按A9取得，不能从正命中截图推为实测。
- full3：准备可执行；继续按26MD的41TC之外当前完整回归映射：test_partial_hub_failure_preserves_valid_local_snapshot、test_local_error_still_returns_readable_hub_candidates、test_incomplete_hub_candidate_is_excluded_without_losing_valid_peers_or_topping_up、5种invalid scope原实际JUnit。新测试失败不推翻这些独立证据，也不能替代新增状态。
- full4：准备可执行；参数边界仍由limit0/51出站不变/ValueError与Web空query400回归，三E1断线/重连/逐条原文照原件定位。未新增未经原文要求的非法字段全组合。

## 版本与边界

产品仍ba8；原d80/f45主流程、scope11/15和reconcile21版本适用性仍按manual-preparation-complete26-sc9.md已核依赖闭包与完整模块比较，不因单Hub模块相等宣称Local相等。当前27bindings/artifacts全部SHA实算一致；debug27结果保留原失败，非把26全套234通过改标27。原26 full pytest receipt输入/完成状态仍可用于其未改声明，新增当前失败优先单列。

边界推演：原A/D完整集合拦截首目标丢失或范围互错；新增all/project确实先遇成功零命中，故26缺失前状态在设计中已补。但错误实现仅在失败/显式本机空结果时混淆coverage的反例仍可能落在未到达部分，不能通过首个成功空结果推断整个检查有效。先修implementation，不退回scene，不授product_defect。正式人工full2应待新版完整到达及独立准备放行再做。
