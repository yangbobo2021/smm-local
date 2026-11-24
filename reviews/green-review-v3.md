# AT-SMM-007 独立绿灯与回归复审 v3

本轮20份逐TC意见已完成并逐份通知登记：18份TDD绿灯 `passed`、既有兼容debug基线1份 `passed`、包验证绿灯1份 `insufficient_evidence`。未发现已执行断言的产品失败；不能据此给007整体交付绿灯。除包原件缺失外，完整规格核对发现两类明确的实现/覆盖缺口，见下文。7人工项与最终三系统CI仍不能认领通过。

## 独立范围及版本

本轮独立Reviewer只读项目、源码及原始证据，未修改产品、测试、历史证据，未执行任何业务测试，未访问ESXi或远程机器。只写本轮20意见JSON与本报告。实际读取AGENTS.md、007 intent/spec/plan、project-library-authorization原话、验收技能SKILL.md及development/reviewer规则、自然设计SC1–10 v4（SC8 v5）、原红灯/准备v3意见、当前断言与实现。采用交接green-review-v3-handoff.json指定的20个目标，定义000004字节SHA实算为 `0203f41968d96272ce5bd204e8e6cbbd273fc6d9c7441f27f9fa517b206481b3`。

逐文件重算20个目标result SHA、全部artifacts和当时当前bindings，均相符；19份红灯/绿灯test_bindings和cases完全相同，主测试SHA `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77`。检查基线83b50fc以来tracked diff，并实际读取未跟踪的新document_protocol/document_sync/document_search/managed_documents、Hub documents/API/CLI/Web等文件，不把git diff遗漏的新模块当作无变更。结论适用于交接冻结版；主Agent在20份意见登记后告知新增包证据留存钩子，后续修改不在本轮原收据绑定内，必须重取同版证据，不能把本轮结论自动移用。

## 阻止最终交付的发现

### 1. 包构建/独立安装原件未持久化（本轮包TC：insufficient_evidence）

PLAN第68行要求“原命令/退出/摘要为证，不只记构建成功”。tests/test_hub_documents_contracts.py:1125–1134确实执行包脚本且断言结果；hub_documents_packages.py:23–95确实写出18个真实命令的stdout/stderr、commands.json、result.json、两wheel摘要、源码/wheel/安装全模块摘要，并使用隔离venv与 `-I`、清PYTHONPATH，检查Hub没有smm_local。然而这些文件只写在pytest tmp_path，observe仅保存子脚本exit0与status/commands18摘要。

当前目标唯一附件00001-current-independent-packages.json指向 `/private/var/folders/jh/mt3s144j7wg98ww3zyqc1np00000gn/T/pytest-of-boboyang/pytest-1187/test_packages0/packages`；独立实际检查该目录已不存在。故本次pytest/脚本返回成功可信，未确认产品失败，但无法独立读回计划要求的原始两包构建安装日志和完整摘要。保留本目标及意见，补持久化原件后另取同版执行并重审。不能用回归总passed代替。

### 2. 联合列表契约未按SPEC实现，准备设计遗漏覆盖状态

SPEC B7第95行明确 `list_document_sources(include_hub=true)` 返回带覆盖状态的两端来源。冻结src/smm_local/mcp_server.py:71–73只有 `hub: bool=False`，hub=true只返回Hub数组；没有include_hub参数，也没有两端合并响应/覆盖。技能和指南改用hub=true不能替代已确认SPEC；主Agent确认没有改该SPEC的授权。

同类问题见SPEC B6第79行：`list_projects(include_hub=true)` 要返回两端及各自覆盖。冻结MCP/API只有 `{local, hub}`，hub_projects在远端失败时抛出，不能保留本机列表并说明Hub未覆盖。test_project_scope:779–788只核两端ID集合和默认旧数组，未核覆盖/单端故障；test_compatibility只负责三只读工具及默认行为，不能支撑新增列表契约。最早是场景/自然设计未完整承接B6/B7列表范围，随后实现和断言也遗漏；需按原SPEC补设计、真实红灯、实现和新证据。此为静态逐接口核对的确定差异，未冒称已实测失败；本轮已执行的compatibility-1等分配检查passed保持其原含义，不等于B6/B7需求已全覆盖。

### 3. 同身份同版本的冲突片段仍会合并（静态确定实现缺口）

SPEC B6第85行明确不混合“不一致片段/摘要”的相同身份版本候选，并反映候选错误覆盖。冻结document_search.py:169–185只核签名路由元信息、摘要字段和片段类型/长度/端点；239–260在同origin/version去重时只比较sha256、text_sha256、text_length，未比较相同或重叠范围的正文。

可复核推演：对已有效的共享同版命中，仅把远端text改成相同长度的异文，保持origin/version/双SHA/长度/start/end及原签名ref。上述验证全部成立，去重会bundle并以远端候选替换可信Local，错误片段参与BM25，Hub覆盖仍为complete。tests/test_hub_documents_contracts.py:889–893仅注入text_sha256冲突，不能拦截此独立的片段冲突。最早自然设计需明确摘要和片段分别受控的负控，随后补真实反例并修复重叠片段比较与partial诊断。本Reviewer没有运行该反例，因此不把推论伪装为本轮日志中的失败；它仍是必须解决的SPEC实现差异，逐TC执行通过不能消除它。

## 已核实的同版执行依据

19份TDD目标都实际TC exit0/1 passed，且各自回归原进程exit0/19 passed，argv覆盖006 lifecycle/search/compatibility与新增4个恢复/在途回归。完整原始work/smm-007-regression-third.stdout及同名XML为325 passed/1 skipped；XML唯一skip是Windows专属 `tests.test_service_startup.test_windows_waits_for_a_slow_background_service`，不是跳过007业务。兼容debug另保留旧005/upload/isolation/Vibe/help真实子pytest argv/exit0/42 passed原stdout。

原红灯均为需求缺失而非环境错误：sync-status/library404、info缺epoch、local参数拒绝、Hub CLI缺project create、默认仍local_documents。绿灯测试/命令保持原字节，当前原日志表明后续断言实际到达。逐TC意见引用具体源码行号、原件和边界，TDD意见省略covers；debug只认领compatibility-1。

源码与实际断言相互支持的范围包括：项目默认off/独立授权与稳定key/CAS；两来源多文件stage与完整原子发布、真实kill/restart及丢ack重试；active/paused前已有资料的失效撤回、partial单成员与兄弟连续资格；共享文件级当前版本、独立origin；网络等待不持本机SQL/控制锁、旧ack不清新pending；保护回退与显式恢复；Hub路径CLI原端管理；双向项目一层公共查询；正常有界片段BM25、异版/异设备区别和隐私；精确Unicode原文窗口、旧资格不复活；两端项目库更新/删除CAS、故障回滚与创建端写隔离。上述通过范围不包括前述未被断言拦截的列表与片段冲突缺口。

### 无损gzip

实际逐份读取两个lossless-evidence.json，并对每份gzip重算压缩SHA/长度、解压后重算原SHA/长度及JSON解析：library-ingest 494份、13,348,805原字节；sync-boundaries 2742份、30,268,110原字节全部一致。冻结conftest.py只在sessionfinish且>8MiB时封装，包含解压逐字节断言，不改变业务输入、测试断言、stdout或退出码；没有截取大正文。2MiB全文及9成员所有16000窗口含尾部都能完整还原。首轮green-boundaries-v1业务通过但超工具25MiB而blocked原件、v2旧候选均保留，未用来替代当前结论。

### 补充反例及旧回归适配

实际读supplementary-fences的4例源码、原失败和修后stdout。跨Hub保护恢复原1失败、删除/数字ID复用竞态原1失败、stage后pause/guard原2失败；修后对应2 passed及含其他相关项的7 passed原件。当前各绿灯回归包含完整4例：只修所选key、所有其他Hub目标blocked；SQL写选择内重核稳定project_key/CAS；每body及publish前重核配置/guard/选择/dirty代次；全部成员stage完成后才加入不确定manifest账本。这些代码与真实前后结果一致，网络不在锁/事务内。外部qualification见证stdout另实际通过：原端资格数回到同1仍建立新Hub连续资格，旧ref拒绝，以及bool引用字段拒绝；这是附加见证，不是新增第28TC。

006 test_document_compatibility只把旧默认查询改为显式local=True，符合已确认007 B6默认联合的新契约。原socket/open、无网络计数、完整两端状态与对话策略守卫保留，没有删掉旧义务。默认联合另由SC6验证。辅助deny_source_reads仅加强Windows normcase及读取次数观察。

## 人工及平台状态

7人工项仍未执行：user-discovery及E1三平台、E2跨机器/Linux user-systemd/Windows SCM LocalService。真实网页旧页面CAS、凭据只在内存/Authorization且reload重新选择、纯文本不执行、文件选择/拖放及各平台完整生命周期仍需其实际画面/轨迹/请求和独立意见。源码网页审查、本机局部调试、探针自检、环境能力探测、逻辑双档案、325单测均不能代替这些义务。最终三系统CI/当前包的正式平台证据也不能由本轮推成通过。维护者禁止使用家庭ESXi继续有效。

## 逐目标意见

| 目标 | 实际TC | 结论 | 原样意见 |
|---|---|---|---|
| green-007-hub-native-v3 | TC-007-hub-native | passed | [review-green-007-hub-native-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-hub-native-v3.json) |
| green-007-library-ingest-v3 | TC-007-library-ingest | passed | [review-green-007-library-ingest-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-library-ingest-v3.json) |
| green-007-library-update-v3 | TC-007-library-update | passed | [review-green-007-library-update-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-library-update-v3.json) |
| green-007-ordering-concurrency-v3 | TC-007-ordering-concurrency | passed | [review-green-007-ordering-concurrency-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-ordering-concurrency-v3.json) |
| green-007-origin-identity-v3 | TC-007-origin-identity | passed | [review-green-007-origin-identity-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-origin-identity-v3.json) |
| green-007-overlap-publication-v3 | TC-007-overlap-publication | passed | [review-green-007-overlap-publication-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-overlap-publication-v3.json) |
| green-007-packages-v3 | TC-007-packages | insufficient_evidence | [review-green-007-packages-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-packages-v3.json) |
| green-007-paused-lifecycle-v3 | TC-007-paused-lifecycle | passed | [review-green-007-paused-lifecycle-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-paused-lifecycle-v3.json) |
| green-007-policy-choice-v3 | TC-007-policy-choice | passed | [review-green-007-policy-choice-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-policy-choice-v3.json) |
| green-007-project-ownership-v3 | TC-007-project-ownership | passed | [review-green-007-project-ownership-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-project-ownership-v3.json) |
| green-007-project-scope-v3 | TC-007-project-scope | passed | [review-green-007-project-scope-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-project-scope-v3.json) |
| green-007-read-exact-v3 | TC-007-read-exact | passed | [review-green-007-read-exact-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-read-exact-v3.json) |
| green-007-read-rejection-v3 | TC-007-read-rejection | passed | [review-green-007-read-rejection-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-read-rejection-v3.json) |
| green-007-recovery-controls-v3 | TC-007-recovery-controls | passed | [review-green-007-recovery-controls-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-recovery-controls-v3.json) |
| green-007-search-candidates-v3 | TC-007-search-candidates | passed | [review-green-007-search-candidates-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-search-candidates-v3.json) |
| green-007-search-fallback-v3 | TC-007-search-fallback | passed | [review-green-007-search-fallback-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-search-fallback-v3.json) |
| green-007-sync-boundaries-v3 | TC-007-sync-boundaries | passed | [review-green-007-sync-boundaries-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-sync-boundaries-v3.json) |
| green-007-sync-publication-v3 | TC-007-sync-publication | passed | [review-green-007-sync-publication-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-sync-publication-v3.json) |
| green-007-sync-retry-v3 | TC-007-sync-retry | passed | [review-green-007-sync-retry-v3.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-sync-retry-v3.json) |
| baseline-007-compatibility-final-v1 | TC-007-compatibility | passed | [review-baseline-007-compatibility-final-v1.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-baseline-007-compatibility-final-v1.json) |

后续应保留全部本轮收据与原样意见，补列表/冲突片段的设计和红灯、修复产品及包证据持久化后，使用新请求ID取得当前完整绑定的绿灯/回归并交新上下文独立复审。本轮不批准007整体交付或合并。
