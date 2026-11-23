# AT-SMM-007 两项补充绿灯独立复审 v1

独立 Reviewer：`/root/review_007_gap_green_v1`。依据 `work/gap-green-v1-handoff.json`，仅复核原 SPEC B6/B7 的 SC11、SC12 两项修复的同测试绿灯。**两项均为 passed；没有判定 R007 或整体交付通过。** 已知 `reviews/pr39-review-v1.md` 四项缺陷仍保留，正式同版全范围及必要平台证据也不能由本轮替代。

## 基线与证据真实性

实际读取交付验收技能、development、Reviewer规范、项目 AGENTS/CLAUDE、SPEC、PLAN、定义000005、两份自然设计、完整冻结测试和公共夹具、原红灯日志/原生意见与登记结果、当前相关产品源码，以及本轮两份绿灯完整 stdout/stderr、附件和006适用回归原件。没有执行业务测试、修改产品、冻结测试或原证据，只写本轮两份意见和本报告。

- 当前 HEAD 为 `de41d7e77fc207f4850fc35a2968dedd6f10ad5a`。两份绿灯各45项 product_bindings 全部实算匹配当前文件，并逐项与 HEAD 原文件字节摘要一致。各54项总 bindings 全部实算一致。
- 定义000005实算 SHA 为 `176e4c3412612ac48b72d65458d81bd67b66246fa28877e3166ba39f20814419`，SPEC 为 `590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`，两份设计摘要与引用一致。SC11来源为B6/B7列表及只读约定；SC12来源为冲突排除、覆盖及准确原文，未新增产品行为。
- 两项 red/green 的完整5份冻结测试/夹具副本与当前文件逐字节相同；完整 cases（包含完整 source 文本）、command 数组以及实际 execution argv 均相同。主测试 SHA 为 `060f6b0bf82b5e16854d240c06a945e3717b4bc0e5e57b81efdfca0747aa244a`。
- 原红灯分别18/17项 artifacts 全部实算一致；其 result SHA 与已登记独立 expected_failure 目标相同，分别真实失败于列表第36行与异文第98行。保留原失败和前轮需修订历史。
- 当前绿灯列表33项、片段26项 artifacts 全部实算一致。两份业务原 stdout 均为 `1 passed`、execution exit=0、stderr空。对应函数没有 skip 或提前退出，结合原始附件确认所有循环和终态断言已实际完成。
- 每份绿灯均附006适用四文件回归：`test_document_compatibility.py`、`test_document_lifecycle.py`、`test_document_search.py`、`test_document_sync_recovery_scope.py`。两份原 stdout 均为 `19 passed, 1 warning`，exit=0、stderr空，四文件当前摘要匹配绑定。该套件结果不替代各用例正式记录。

| 场景 / 实际TC | green result SHA-256 | 有限结论 |
|---|---|---|
| SC11 / TC-007-listing-coverage | `cddb4cc50a5a377b583f119c16a01ea1b1814bb82947a4ca9fbbe6eb1254c6b2` | passed |
| SC12 / TC-007-snippet-conflict | `68ba289e16cac02a861f50db4961744f462e5fa81c2b09ee2fb84de87d3be6a1` | passed |

工作树另有包探针 `scripts/acceptance/hub_documents_packages.py` 修改及本轮外新文件；它不在两份绿灯实际读取/绑定范围。本结论没有把该未审工具变化或另四项缺口纳入通过。

## SC11：两端列表、离线保留与只读终态

SPEC B6:79、87与B7:95支撑本项。完整实际函数见 `tests/test_document_review_contracts.py:14–75`。

原件00007/00008及00012–00014证明MCP来源、MCP项目与API项目默认仍是本机数组；00009/00010/00011分别证明明确include_hub的三入口返回两端列表和 complete/complete、fallback_reason=null。来源和项目采用实际独立夹具身份，Hub来源顶层id与origin.kind正确。00015/00016/00017是故障注入后的 complete/unavailable、Hub空与 `listing offline witness`；本机来源、MCP项目、API项目各自完整等于对应默认结果（第59/62行），并非仅验证非空。00018–00020证明恢复在线后再次访问全部三入口。

第29行在首次调用前保存本机settings、上传/文档全表及Hub项目/文档快照，记录全段路由marker；31行源读取guard持续到最后在线API。63/64/69/70/71/72/73行完整完成：离线无成功Hub请求、前后Hub快照不变、本机策略与文档状态不变、源打开零次，全程只允许 `/info`、`/projects`、`/documents/sources`。00021末尾见证明确两边状态不变、source_open_attempts=[]，全部12个请求路由仅上述列表路由。

推演首次在线API先同步再正确返回，第72行最初Hub基线或第73行全段路由会失败；只持久更改本机上传许可会被local_state完整比较拦截；打开当前来源会记录attempts并在第71行失败。本轮上述断言均实际到达，通过依据不再停留在红灯后的静态可执行性。产品 `document_sync.py:674–693` 保留Local列表并隔离Hub失败，MCP/API调用点与实测响应相符。既有project-scope完整项目集合断言仍保留于主测试780–788行；本补项没有替代或删减它们。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-listing-coverage-review-v5-a.json`，写完后已立即通知根Agent登记。

## SC12：同窗与部分重叠异文排除、正常精确合并

SPEC B6:85、87及B7:91、93支撑本项。完整实际函数见 `tests/test_document_review_contracts.py:79–105`。

00005证明正常发布，00006证明独立本机原文 `conflictnonce actual local original`、version1、[0,35)。86–92行由真实Hub响应deepcopy后仅改正文，同窗为35个x，部分重叠把start改为5并生成30个x，保持origin/version/双摘要/text_length与精确引用。

00007/00008(equal-window)与00010/00011(partial-overlap)均保留一条本机可信正文，archive_scope=local、单一本机origin_reference且reference与00006完全相同；Hub coverage=partial，candidate_failures为明确“同一身份和版本的文档片段冲突，排除远端候选”。因此不是被错误形状或摘要检查提前排除。00009/00012按保留引用真实read，均准确原文[0,35)、LF起止行1、实际读取端local。96–101行在两个循环都实际完成；只修同窗、漏partial/错误、混入远端引用会分别被98/99/100行拦截，两次read用独立original_text而非搜索两边互比。

102行恢复循环前保存的真实request；00013正常返回combined及local/hub两个精确origin_references、complete/complete且无候选错误，00014按实际bundle读取准确原文。103–105行实际完成，可以拦截一律丢弃Hub的错误修法。产品 `document_search.py:251–259` 按绝对码点交集比较重叠正文，在bundle和覆盖旧候选前continue，正常分支260–266行仍合并双引用，与原件相符。既有摘要冲突889–893行及正常候选/去重838–866行仍保留。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-snippet-conflict-review-v5-a.json`，写完后已立即通知根Agent登记。

## 结论边界

本轮是两项冻结补充用例的同测试绿灯与回归独立复核，covers按TDD规范省略。TestClient和响应正文故障注入不等于真实TLS、跨OS、Web UI或服务身份实测。PR39四项其他已确认缺陷（远程外部来源扫描、混合批次逐文件结果、Local至Hub创建端入口、UI实际读取端/出处）与必要正式平台缺证继续保留。不得从这两项passed推定R007、全部29验证项或整体交付passed。
