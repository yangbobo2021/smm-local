# SC9 人工项准备独立复审

验收 AT-SMM-005；需求 R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_c；复审时间 2026-11-22T09:56:18.957094+00:00。

结论：needs_revision，最早修订阶段 design。这里只评价准备充分性，不是人工观察或正式业务通过。TC-005-sc9-evidence 分配 full1、full2、full3、full4。

## 实际审阅及摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc9/request.json` SHA256 `843b49c9759b0d7185a6719f0a375979b9482af62f7932876ed73c218bd49bf8`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc9/result.json` SHA256 `b682998caedec345610c5ad202cc0d387916601d7d7dda0de7d6318d3bbc48fd`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc9/request.json` SHA256 `0cca18641152a57c62998b2c4db318a78d3bdba09b2aef8ec2fb6dce7874ec2b`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc9/result.json` SHA256 `d3bb5e8fab42f5b3a30919f384901e1bec9598ceecc1214ed4bf0d2ba6a4fd8e`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9.md` SHA256 `dba685c74491639f286fece99e6f7605fc406d08ef7883942d6bb0d496dec528`。

已打开 AGENTS.md、确认 intent/spec/plan、PR Review Prompt、验收技能 design/implementation/reviewer/execution 约定。SC9 criteria 均可由 SPEC A9/B5–B6 推出，没有增加额外产品承诺。

## 逐检查准备判断

| 检查 | 准备判断 | 实际来源与边界 |
|---|---|---|
| full1 | 可执行，原件可用 | 三个 E1 主流程 mac-run8/linux-client-run8/windows-client-run8 的 offline-{cli,mcp}-search.json、offline-browser.json 均仅 local-A/local-A-new，coverage local=complete、hub=unavailable、effective_projects 只有A；对应 offline-search.png 已逐张打开，显示“本机已检索、Hub未查到该端、HTTP503”和两条A结果。offline/重新连接的浏览器trace、stdio命令及原文附件均存在，观察时须分别登记实际原件SHA。当前 fallback debug 只支撑本机共用 tdd-core。 |
| full2 | **需修订 design** | “成功零命中与未执行区分”见 SPEC A9、B6，现设计只有 expected 文字，没有成功零命中的前置数据、查询输入或核对动作。递归核对manifest列出的13个原件目录全部JSON，未找到 results=[] 的搜索；三个主流程与scope的全部入口均有命中。实际全套JUnit的相关test_combined_search/test_federation声明也没有成功零命中+coverage断言。错误实现若只在零候选时将成功端标为unavailable/not_requested，现有正命中/故障断言仍全过。最小补足：设计一个确定在两端均无命中的有效查询，断言实际完成端为complete、结果为空、没有故障原因，并与不可用/未请求端状态区别；A9要求的E1三入口观察也须有可定位原件，不能用expected自证。已有offline-all.json三平台CLI/MCP/Web确含A/D/G/U/U2/plugin完整集合，重连主流程确恢复combined，故这部分无需整个平台重跑。 |
| full3 | 可执行，须按下列当前case分配复核 | full-pytest.xml中test_partial_hub_failure_preserves_valid_local_snapshot、test_local_error_still_returns_readable_hub_candidates、test_incomplete_hub_candidate_is_excluded_without_losing_valid_peers_or_topping_up及5种test_invalid_scope_response_never_activates_local_links均实际passed。源码tests/test_combined_search.py:99–125比较A/B全集合、双端coverage和Hub完整原文，双失败raises；:187–202比较a/good完整集合、hub partial/candidate_failures、只有一次search，拦截坏候选泄漏、误丢好同伴、扩大召回。本项由人工原件核验引用这些41TC之外的真实回归，不能缩成只看fallback的debug。 |
| full4 | 可执行，参数部分不应夸大 | tests/test_combined_search.py:169–183实际limit0/51均ValueError，出站调用数量不变；tests/test_pipeline.py::test_web_api_uses_same_archive空query返回400，JUnit分别passed。平台断线/重连三入口及逐条读原文原件完整。主流程已检查独立正文，不靠CLI/MCP相等；范围扩大到D/G会先被完整session集合断言拦截。不同非法字段可另补，但不能声称已全组合实测。 |

## 版本与运行适用性

full-pytest-receipt.json显示2026-11-22T09:51:54.022374+00:00开始、09:53:42.149610结束、exit_code=0；stdout摘要b6499cb14c758394b549bc2bf0c9b57f508fc0a90b894f3a1d7c55a2685173d3已实算一致。inputs.json摘要2f79acd1d49efec1b4043a1616ed4d21b76499f695e4e9d5e646b1b4e2eec4d1与receipt一致，逐case读JUnit，未用234总数代替覆盖。debug-sc9的全部bindings/artifacts实算无差异，进程32869退出0、1passed。现有pair/夹具通过真实TestClient Hub及独立JSONL构造本机A/D，断言值来自夹具。

原业务d80主流程仍标d80；scope11是f45。当前federation/core/search_merge/MCP等查询闭包字节与其安装清单可比；references的d80标题变化由f45三客户端scope11及相关Hub scope11/15补，不能称d80已测新标题。后续f45→7c修改api/cli/upload/index，7c→ba8仅upload；须对diff确认CLI/API/Web修改限对账，上传初始化亦有当前断言/后续reconcile21。已读完整模块比较文件，不因Hub相等就宣布Local全相等。此处允许核验历史断线/查询事件的适用性，不将其改写成ba8平台重执行。

## 边界推演与下一步

A/D及两条A前置数据都被完整集合断言或实际JSON观察；只保留首条A会被平台期望两条A拦截，误用A/D同一目标会被独立会话名/正文拦截。快照后Hub失败不同于范围本身失败，已由独立A/B集合+coverage断言区分；两端同错不能通过独立正文期望。成功零命中是原文点名的不同前状态/结果，当前缺口不是等价标识补样本。应先修订full2自然设计、补相应原件/断言并刷新匹配及准备复审；其余人工检查可定位但本人工项整体现在不能进入声称完整通过的正式观察。
