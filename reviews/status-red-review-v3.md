# AT-SMM-007 状态补充设计与红灯复审 v3

结论：三份目标中 **两份 expected_failure，一份 needs_revision / implementation**。列表元信息与两端目录指引是可信业务红灯。保留状态 TC 已补 v2 的直接缺项，但来源状态还存在独立期望及暂停时全集漏检，不能授予整 TC 有效红灯。没有判 R007、E1/E2 或整个交付通过。

## 依据、版本及范围

工作根 `/private/tmp/smm-007`，实际 Reviewer `/root/review_007_status_red_v3`。实际打开技能 `app-delivery-acceptance-native/SKILL.md` 及 development、execution/reviewer、case-preparation/design、implementation；原始依据包括本根 AGENTS.md、007 intent/spec/plan、变更目录 `reviews/project-library-authorization.md`、根 `reviews/pr39-review-v2.md`、`status-red-review-v1.md`、`status-red-review-v2.md`。没有以主 Agent 口头判断代替原件。

采用 `definitions/000007.json`，SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`；逐对象核 000006 的 requirements 和 14 个旧场景均不变，新增 SC15/16。范围为保留旧 31 项后的 34 TC（27 自动/7 人工），本轮仅审交接三 TC，未重新授予旧 31 项结论。

实际 HEAD `c9ffae856160daf9685e81c71cca66887ebfec2f`；`git diff --name-only a44a363bb8a708396c643daeec331f6a83bc9aac -- src tests` 无已跟踪变更，产品仍是 a44 未修状态。当前新增测试 SHA `f7088a2a7ada95fa73e84fd31f070899c1e4c3b0642bda14f7c348cce494f7a9`。三目标每份 51 bindings / 45 product_bindings / 6 test_bindings 均按当前文件复算匹配，artifacts 分别 39 / 38 / 43 项全匹配；不以 HEAD 代替字节版本。

| 目标 | 实际目标 SHA | 结论 |
|---|---|---|
| red-007-hub-status-provenance-status-v3 | 63b6cf5d0d773c8af6b2690d3bce9bc6078907e803a6b876b391c7790545a578 | expected_failure |
| red-007-hub-retained-state-status-v3 | 11f3e347886ab8cf73c1a85bf98a98ce2bcc4c12f925e9bdc6056c0ff1741a08 | needs_revision / implementation |
| red-007-folder-guidance-status-v3 | 40c7d576d843fe301da1d6d42d2f0292e91a07460bcf3cce748e1919dc3a29e3 | expected_failure |

自然语言设计实际 SHA：SC15 v3 `dbe229c3bc74789c9b655752e271dcbf29c05432c9d42b9d75bfea2a975b7809`、SC16 v3 `e8c873d9c7c9230d64da0839bbe85c57b729843cf8fc5363909e3bf1e3489aef`。三个 match-v3 各只绑定自己的 TC，均引用对应 v3 设计。SC15 两判据来自 B2/B5 和 B3/B6，SC16 来自 B8/B1；没有发现判据扩充产品承诺。

实际读旧 `design-sc15-v1/result.json` 及旧 v1 冻结测试：第一检查 `hub-status-provenance-1` 留给同 ID 元信息 TC；第二检查 `hub-status-provenance-2` 独立迁入 `TC-007-hub-retained-state`。旧 v1 第249–253行的初始 native/allowed 与 retained=false 在本版418–449接回保留状态 TC；恢复511/517也新增检查，原缺项去向可追溯。旧记录及本次真实失败保留。

## 元信息 TC

场景、设计与实现有效。`tests/test_document_status_contracts.py:207–260` 逐身份核 files 的独立项目、SHA、长度、版本、资格、来源原身份与采集/接收时间，260核唯一性、389核全集；262–328逐来源核来源全集/唯一性、项目、revision、只读、无正文及时间，并读取真实 HTTP/CLI 全部及逐源 files。

只首个目标正确时，215–225逐行及389全集首先拦截；漏另一目标而重复首行由260拦截。HTTP/CLI双方共用同一错误目标或项目时，独立 expected 的215–216及287–290会拒绝，不能靠两响应相等通过。零/多项目绑定有独立期望；未见遗漏会改变预期的其他前状态，同条件换名称属于可选样本。

329–384正反自检已执行，`00027-status-probe-selfcheck.json` 与 `00026-metadata-cli.json`证实已知正确元信息通过、错误SHA/项目/资格/时间/重复及Python/CLI真实源打开被拦截。原stdout为1 failed：389调用verify，在211取origin时报KeyError。`00028-hub-11.json` HTTP200、`00029-metadata-cli.json` exit0 均实际缺origin/project_ids/received_at；`src/smm_hub/document_api.py:68–70` 和 `document_cli.py:48–49`仍直返006 files，属于B5可观察缺失。

CLI响应已取回，但其独立verify、sources逐行及最终副作用检查未到达，不作通过认领。静查未到达实现未见确定测试故障。授予本TC的 expected_failure。

## 保留状态 TC

场景和设计有效，v2所指直接漏项已补，但实现仍需修订。

1. **来源预期依赖产品返回种类。** 418–429核source_id全集后，用 `source["origin"]["kind"]` 自行决定allowed/native，没有按独立expected定位来源种类及原身份。反例：初始、暂停和全部命中/read正确；恢复后仅Q来源保留正确source_id，却把origin.kind改hub并标native、retained=false、消息无暂停。511调用仍通过，513只看P，517–532仅看命中，后续共享段也不再看Q来源，因此全TC仍可通过。这违反B2/B5及恢复允许的既定承诺；改变的是恢复后来源的业务状态，不是增加等价标识。实际以AST抽取当前assert_allowed_sources执行已知四来源正例通过，再把第二个已知device改成hub/native，实际仍通过。最少应从独立expected按source_id取得种类/完整origin和预期状态。
2. **暂停时来源全集及native状态遗漏。** 458–472只找P/Q两行。仅在P确认暂停期间漏掉两个Hub native来源，或把它们误标paused/retained=true，只要P/Q与所有hits/read正确，458–507可全过；恢复时返回正常又可过511以后。B5的来源列表及B2/B6状态承诺适用于这些现存目标，设计已写逐身份全集/唯一性。应在暂停阶段也逐来源核全集、唯一性及独立状态。这与第一问题同属 implementation。

现有命中检查已能拦只首个目标正确或遗漏Q重复其他行：416、432–446、474–478及521–524核独立身份全集与数量，443–446独立核允许/native及source_id。暂停每命中旧ref/正文在485–490核对；恢复529–531保旧ref/独立正文。共享547按稳定project_key区别P暂停/Q允许，557–560逐项目核状态与原文，570–573核允许资格推进后P可读新版本；双方都误读同一旧正文被独立预期拦截。

本次stdout为1 failed：448调用初始来源断言，425取sync_state报KeyError。`00028-hub-13.json` HTTP200所有来源确缺状态字段；Hub sources产品只装饰origin/read_only/message。首个业务缺失可信，但新增初始检查令本次暂停动作尚未执行；449初始命中、450后暂停/网页/恢复/共享全部未到达。不能挪用v2暂停原件称本轮已执行，亦不能把首个可信红灯升级为候选有效。静查未见其他确定运行错误；因以上两处漏检判 needs_revision / implementation。

## 目录指引 TC 与本次图像

设计与实现有效。657–685每次drag重新滚动/定位、核本次target/items；633–651捕获阶段从真实entry原型包装目录/子entry API并委托原行为。687–705自检使用stopImmediatePropagation阻止产品收到自检drop，实际枚举body.txt、捕获createReader/readEntries；706清空审计后才放行产品。608–612的服务器源读取守卫也已实际自检，`00012`/`00026-folder-probe-selfcheck.json`与本次trace可核。709–730正反指引样本通过。

741/767逐目录行拒绝假成功并核适用创建端/明确刷新指引；732开始比较对应端完整文档/FTS/项目状态及Hub状态；751/790–794的审计可拦枚举后丢弃。只有Local正确而Hub错误由Hub参数737/741拦截；仅纯目录正确、混合目录假成功由767拦截；双方误用同一错误文件由772/781库身份及789独立正文拦截。额外同条件文件名可选；未到达代码静查未见确定测试故障。审计包装普通FileEntry.file可能影响未来其他合法上传实现，属可选健壮性改进，不据此阻塞当前路径。

已实际打开本次 `attachments/local-web-review.png` 与 `hub-web-review.png`：两端目录行均为“example-folder：失败 · 无法读取所选文件”，该处没有目录来源/适用创建端指引。Local下方来源表单、Hub页底CLI说明是其他位置的替代发现路径，不能替代规格要求的当次目录拖入提示。

实际读取本次两份trace ZIP的trace.trace：Local191事件、Hub212事件。exnw@56 / dtye@161是被阻止的自检目录，其后实际读到body.txt与createReader/readEntries审计；706重置后exnw@80 / dtye@185才是产品drop，均inside=true/isDirectory=true。唯一after错误exnw@94 / dtye@197对应737目录提示断言。stdout两参数均在737失败，属于B8业务缺失，授予 expected_failure。738之后方向、无上传/状态/审计终验、混合批次与read未执行；自检枚举不计产品扫描。Chrome真实页面/JS经route转真实TestClient，只证明局部反例，不是E1真实网络/TLS/平台身份证据。

## 独立文件与边界

每份完成即写唯一意见文件并通知主Agent登记，未等待整批；JSON仅含该目标实际TC，均省略covers：

- `review-red-007-hub-status-provenance-status-v3.json`：SHA `344620a49c9b542c99378f23031c228398385f94da059a2187d1bc005cf48373`。
- `review-red-007-hub-retained-state-status-v3.json`：SHA `c1e499d81b65cf12b72a3d754cceda50e6fbeb527b2768dcc8fc5e611360d54a`。
- `review-red-007-folder-guidance-status-v3.json`：SHA `729f06463833a9498ad4cfa6c676345e9a82fde41f856ea69fe659ab3775652c`。

三文件位于 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/`。本轮对产品、测试和旧证据只读，只新增指定三JSON及本报告；未访问ESXi、日常Hub/VibeInsight或真实用户资料，不发GitHub消息，不运行登记工具，不重跑产品业务。仅额外在内存对实际断言helper做已知正反样本复核；没有据它冒称产品执行或完整验收。
