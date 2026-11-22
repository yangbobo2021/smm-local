# SC7 人工准备独立复审

AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_b，2026-11-22T09:59:22.568119+00:00。本意见为准备阶段，未认领正式人工执行通过。

实际审阅design `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc7/request.json` SHA256 `16064152d1cd1c8beabfb0c9203cd1b60f575e79910ec8739472334c4cd39d4c`；match `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc7/result.json` SHA256 `8d7ba48af618ffa6814440304ab01b71cad2bccddce3b69a1d47f0020978e68d`；steps `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC7.md` SHA256 `a745550aa86cdf3feeaa9da641ff5af11af05a218b5275cea29de7306fa7a6b8`。人工TC-005-sc7-evidence分配complete-1/2/3/4/privacy。A7/B6/D3支持现有四条criteria，未增加产品承诺。

| 检查 | 可执行性与准备意见 |
|---|---|
| complete-1 | **needs_revision，revision_target design。** 离线audit与当前数学回归可照做且原件存在，但设计的独立数学预期只覆盖单查询词且df=M。SPEC D3明确“查询词项先去重”“含词项t的文档数为df”并“对查询中的每个词项…求和”。所有现有独立数学断言（test_combined_search.py:21–34的amber、:59–78的tailonly；audit.py的selective）均每个候选包含同一词。错误实现对任意term总令df=M可全部通过，缺少按不同df求每词贡献的必要判定条件；只比较两端同分更不能补。最早在自然设计增加多查询词/不同df（并可含重复query term）独立逐候选分数与顺序，再匹配/调试/复审。现有scene criteria“独立BM25预期”及D3已经承接，不必修改产品或先改scene。 |
| complete-2 | 原件准备有效。当前bm25专项保留原独立公式、同源同版本副本前后分数/消息数量及不同会话/轮次集合，新增v1/v2精确(canonical_id,version,text)独立集合。平台version-and-long-originals.json及retained-version-original.json是真实两个版本读取原件。须结合其引用读取验证，不能把纯数学候选的假reference字符串当真实读证据。 |
| complete-3 | 原件准备有效。当前long-message用2001/3-token独立公式分别断言两端完整分数，并准确读回2001-token本机全文；各main平台长消息原件含CLI/MCP/browser及reads。数学和读取各自有效，不能只用全文/预览分数相等。 |
| complete-4 | 原件准备有效，可进入核验。三E1 main的payloads/stopped-payloads及hub.log存在。已直接读取：禁传A追加/新会话完整合成标记不在停止区段；正常search仅query/current_source/current_session/include_current/limit/preview_chars/device_id/scope_reference字段；失败段分别3/5/11次offline info，不含正文候选。后续观察仍须逐载荷/日志搜索独有合成标记，核对失败发生在info之前所以没有发出search，而非仅数offline标签。 |
| privacy | 同complete-4共用原件，准备有效。步骤“Windows尚在重跑”为遗留说明，windows-client-run8本轮新离线audit receipt确已完成且原完整业务材料存在；不能据此残句假设缺Windows，也不能据audit passed自动认领。建议同步清理该残句（不改变判定）。 |

版本适用性：d80主流程、f45登录、7c Mac系统Hub分别保留原manifest/installed/service-events/业务时间。merge/federation/core的完整候选与排序调用闭包与最终ba8一致；references新范围标题变更不改变评分输入，但实际新范围读需scope11/15；api/cli/static仅reconcile变化不能替代查询原件；upload新目标校验和CAS由当前回归及reconcile21单独补。final-package-comparison21给7c→ba8完整Hub模块一致、Local仅upload改变，不能只比merge单模块。人工正式观察应绑定该闭包及补证。

探针：已读scripts/acceptance/selective_upload_audit.py和tests/test_selective_upload_audit.py。探针不导入产品ranker，以Counter/独立公式核对完整正文；正常fixture及五反例（missing_append、wrong_score、candidate_egress、false_complete、wrong_original）在当前full-pytest.xml逐case均通过。它的search字段白名单可拦候选额外字段，仍不代替本机独有正文逐值外发检查；七个新audit是原件离线核验，不是七次平台业务重跑。完整回归receipt在09:53:42Z完成exit0、输入/输出摘要一致。其数学输入仍不能补上述不同df缺口。

边界：只保留第一候选/轮次/版本由test_combined_search的独立session+canonical集合、test_upload_acceptance_boundaries:116-120精确v1/v2集合拦截；错误增加副本词频/权重由副本前后独立分数拦截。时间有效/相等时区/更新/空/缺失五种状态均预先构造，ties独立完整顺序拦截仅首目标正确。全文与预览同时截断会在2001/3-token独立公式拦截。不同df是上面明确遗漏的判定条件，而非随机换标识的可选补测。

结论：整场景人工准备**需修订complete-1设计后重审**；其余原件准备有效，未认领执行通过。JSON仅给真实auto分配项，各自保留有效/需修订结论，不把manual塞入debug。
