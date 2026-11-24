# PR #39 补充红灯独立复审 v1

结论：SC13 `TC-007-cli-scan-boundary` 为 **expected_failure**；SC14 `TC-007-web-review-feedback` 为 **needs_revision / implementation**。两端网页的真实批次结果缺失已经复现，但该事实不能放行尚未完整落实的后续断言。产品仍为 HEAD `de41d7e77fc207f4850fc35a2968dedd6f10ad5a` 的原候选，以下绑定摘要为本轮版本依据。

本轮 Reviewer 的宿主 canonical session 为 `/root/review_007_pr39_red_v1`。只写本轮两份原生意见和本报告；没有修改产品、冻结测试、旧证据或代发 GitHub。

## 范围和版本

实际读取技能 `app-delivery-acceptance-native/SKILL.md`、`references/execution/reviewer.md`、`references/case-preparation/design.md`，以及项目 `AGENTS.md`、007 的 `spec.md`、`plan.md` 和 `reviews/pr39-review-v1.md`。从原文核对 B5、B6、B7、B8 与四项 PR 发现，不将 PR 建议当作额外权限体系或必须继续处理批次的产品要求。

验收为 `AT-SMM-007`，当前定义为 000006，SHA-256 为 `52f35fcc7e84b59d8158ec9c5f1e08460e6989598614b5c7d88d3a8b39b8890b`。与 000005 比较，原需求及原 12 场景内容逐项相同；新增 SC13、SC14，原用例没有在本次补充中被替换。本轮只判定交接的两个实际 TC，不把 31 项总数或既有通过扩大为本轮通过。

逐份读取设计、`match-sc13-v2` / `match-sc14-v2`、TDD 结果、冻结测试副本、公共夹具、全部运行日志及附件。两个目标各 50 项当前 bindings 均重算一致；SC13 的 15 项 artifacts、SC14 的 39 项 artifacts，以及各自五份冻结测试原件均与登记 SHA 一致。两份匹配收据各五项 bindings 也一致。

| 目标 | result.json SHA-256 | 意见 |
|---|---|---|
| `red-007-cli-scan-boundary-pr39-v2` | `6f48f58f8f5accfd1403949c59bac78c5db7f991ea234e90d9c3d2fe341d1c81` | expected_failure |
| `red-007-web-review-feedback-pr39-v2` | `5690953b53dbba0bb22014a7a968ae0325013e7d34566b21ba816ecb34916f3e` | needs_revision / implementation |

## SC13：有效红灯

SC13 场景和自然语言设计准确表达 B5 的采集调用边界。两份独立外部文件经真实 Hub CLI 子进程添加，原始 `00003/00004-scan-cli.json` 均为 exit 0、pending，来源 ID 不同。第一个认证 HTTP add 返回 200，并产生另一个 pending 来源 ID；`00006-remote-add-denial.json` 与 stdout 对应，测试实际 exit 1，在 `tests/test_document_pr39_contracts.py:35` 的拒绝断言失败。`document_api.py:60–62` 直接转交 `native(add)`，`documents.py:194–223` 没有调用入口隔离，与产品缺失相符。

后续静态路径完整：两个 add 分别核拒绝和整个文档/项目表快照；两个单源 refresh 与无 ID 的全体 refresh 分别核拒绝和同一动作前快照；`deny_source_reads` 保护两份原文件的 builtins/io/os open，记录被吞掉的读取异常，并由最终零尝试断言拦截；拒绝阶段还要求无正文命中。退出 guard 后，同一 state-dir 的真实 CLI 对两份分别 refresh，再逐份 read，以两个互异独立原文的全集核对，能拦截只处理第一来源及误禁 CLI 的实现。

实际运行只到第一 add 的拒绝断言。第二 add、状态复核、三种 refresh、最终零打开断言及 CLI 正常采集/全文读取尚未执行，不认领这些已经通过。等价目录或更多标识样例不是本轮阻塞要求。

## SC14：真实失败成立，断言实现需补齐

场景三项义务及自然语言设计来自已有规格，C 可成功或明确未处理。真实 Chrome 加载产品 HTML，Playwright route 将请求交给真实 App TestClient；这证明网页产品回归，不是 E1 实际网络、TLS 或服务身份。

实际打开本目标 `local-web-review.png`、`hub-web-review.png`，并读两份 trace：两端只显示“文件不是严格UTF-8文本”，没有逐文件结果；页面库区域为空。`00014/00026-mixed-batch-result.json` 则显示实际已保存 A。两个参数均在第 92 行因批次结果元素不存在失败，原始 stdout 为 2 failed，exit 1。因此 B8 缺失是真实产品失败，并非环境或测试启动故障。

以下是会改变判定的既有样例断言缺口，最早修订阶段均为 implementation：

1. **逐文件状态与实际保存身份未关联。** 第 92–96 行只在整个报告中寻找 A/B/C 及成功、失败；C 不在库中时再找任意“未处理”。实际 A 成功、B 失败、C 未处理，而报告倒写“A 失败、B 成功、C 未处理”，仍能全过。列表仅核更新控件个数，不能证明显示的是实际保存的每个对象。B8 和检查 `web-review-feedback-1` 要求逐份真实结果与资料库一致，应按每份名称/身份关联结果和列表，保留 C 的两种合法结果。
2. **原文循环可空通过或漏掉 C。** 第 97–99 行没有独立搜索全集断言。搜索为空，或保存 A/C 却只返回 A，循环仍可通过。这违反同一检查及 B8 的已保存资料可检索和准确 read 承诺。应先精确核对本次实际保存对象的命中集合，再逐份对独立原文读取；不是要求再添同条件样例。
3. **链接存在不等于可发现并打开。** 第 106 行只核 href 和提示包含“凭据”；隐藏链接、隐藏提示或无法打开的入口仍可通过，也未核说明创建端管理及凭据来源。检查 `web-review-feedback-2` 已要求可发现并打开，应实际核可见并打开正确的无凭据 Hub 连接页。仍可使用 TestClient 映射，不增加 E1 网络要求。
4. **两份原文及命中出处未分别核对。** 第 111 行 Hub 自有读取和第 112 行首次 Local 读取仅核 metadata，没有核正文；第 115 行才核 shared 的 Hub 回退正文。Hub 自有读到 shared 正文、或首次 Local 读错但回退正确，仍可通过，违反 B7 和本轮设计的独立原文预期。命中行除 Hub 自有标签外，也未核 device 的稳定设备/档案身份与名称；命中行仍只画 hub/opaque source_ids、阅读区正确的实现可漏过检查 `web-review-feedback-3`。应分别核两份独立原文和适用命中元信息，保留 Local→Hub 精确同版回退和实际 provider/身份/版本核对。

已静态核查后续 selectors、实际 library/search/read 路由、相同 File 对象重试、bundle 资格准备和控制时序。`Fixture` 的 auto_sync 关闭；`w.local.remove(source)` 只经 `schedule` 标脏，不立即向 Hub 撤回，所以当前准备能保留当次 Hub 资格供精确回退。不得为修测试误加立即同步撤回而制造另一故障。

当前第 93 行以后均未实际运行。真实首失败保留，但本版不授 expected_failure 来放行完整设计实现；补断言后应在未改产品上另取红灯并复审。更多同条件文件数、标识变体属于可选补测。

## 原生意见

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-cli-scan-boundary-pr39-v2.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-web-review-feedback-pr39-v2.json`

两份均仅含相应目标实际 TC，`target_operation` 为 `tdd-red`，使用真实 canonical session，省略 covers；已逐份就绪通知主 Agent 登记。
