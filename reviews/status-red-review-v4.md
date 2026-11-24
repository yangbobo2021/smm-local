# AT-SMM-007 状态补充设计与红灯复审 v4

结论：三份目标均为 **expected_failure**。SC15 元信息和 SC16 目录指引继续是可信业务红灯；SC15 保留状态 v3 指出的两项实现漏检已补，本版也可作为有效红灯。没有判定 R007、E1/E2 或整个交付通过，红灯后未到达的路径没有记作实测通过。

## 范围与版本

根 `/private/tmp/smm-007`，Reviewer `/root/review_007_status_red_v4`。本轮实际阅读 `app-delivery-acceptance-native/SKILL.md`、development、execution/reviewer、case-preparation/design、implementation；项目原始 `AGENTS.md`、007 intent/spec/plan、变更目录的 `reviews/project-library-authorization.md`、根 `reviews/pr39-review-v2.md` 及 status-red-review-v1/v2/v3。补充授权文件位于变更目录，PR及旧状态审查位于根 reviews。未访问 GitHub、ESXi、日常 Hub/VibeInsight 或真实用户资料。

采用 `definitions/000007.json`，SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。逐对象比较 000006 的 requirements 和14个旧场景均原样保留，仅新增 SC15/16。范围沿用旧31项加本批3项，共34 TC（27自动/7人工）；本轮仅独立判断交接的3项，不重新授予旧31项结论。

当前 HEAD `48bc7f37cc44e4c7f2055e92a917c6e44192b4f8`。`git diff --name-only a44a363bb8a708396c643daeec331f6a83bc9aac -- src tests` 无已跟踪差异，产品仍为未修复的 a44；新增测试实际 SHA `81e29a9751c1b2e3f6793ea2b70ba14e285ae0c72ab27488e1db1f02f69d0d00`。未应用外部修复补丁。三目标每份51 bindings / 45 product_bindings / 6 test_bindings，以及39/38/43 artifacts，均按当前原字节重算匹配。metadata/folder函数AST与v3相同；三份重新取证绑定同一完整测试文件。

| 目标 | result.json SHA | 结论 |
|---|---|---|
| red-007-hub-status-provenance-status-v4 | 97140558b23a921148b96c665757750ab36baffe5781f2b88825f6693af96c7d | expected_failure |
| red-007-hub-retained-state-status-v4 | 54623682d8cabc6f191bec3cf6642317759d02b69b2807e2987d1d8524dd0c89 | expected_failure |
| red-007-folder-guidance-status-v4 | 9588a687e72dfecce716941f06ecc7790a878d845fdd12d035bb89e7145293fc | expected_failure |

SC15 v4自然语言设计SHA为 `e9d890e5b0205a5990e4493b88f99ea57995e36250cc75c643207057079b3117`，SC16 v4为 `5a56fa9003773eb5f5efedd3c44a55cf3e14c6fd10e7ecdd94df75383e223128`。三个match-v4各只声明交接的实际TC，并引用相应设计。SC15来自B2/B3/B5/B6，SC16来自B1/B8及创建端管理约定，未发现场景额外增加产品承诺。

实际读 `case-design/design-sc15-v1/result.json` 及v1红灯冻结测试：`hub-status-provenance-1` 留在原TC；第二检查移入独立 `TC-007-hub-retained-state`。旧测试249–253的初始native/allowed与retained=false由本版418–477承接，暂停及恢复分别487、541重复全集检查；独立检查没有因拆分消失。旧意见和失败保持不变。

## 元信息

场景、自然语言设计及实现有效。`tests/test_document_status_contracts.py:207–260` 按独立原身份核files的SHA、长度、版本、资格、来源原身份、项目和适用时间，260核唯一性、389核全集。262–328逐sources核身份全集、唯一性、项目、revision、只读、无正文及采集/接收时间，逐来源请求HTTP和真实CLI files。

若只首个目标正确，其余目标出错，逐行215–225以及389全集首先拦截；漏Q而重复其他行由260及265–282拦截。HTTP/CLI双方误用同一个错误目标或项目，独立expected的215–216、287–290先拒绝，不能以两个错误结果一致通过。设备/Hub自有、零/多绑定已覆盖会改变预期的条件；同条件换名称是可选样本。329–384已知正确及错误元信息、时区、Python/CLI真实源打开审计自检已执行，附件00027-status-probe-selfcheck.json及00026-metadata-cli.json可核。

本次stdout为1 failed：389调用verify在211读取origin报KeyError。00028-hub-11.json为HTTP200，00029-metadata-cli.json为exit0，两份四行文件结果实际缺origin/project_ids/received_at。`src/smm_hub/document_api.py:68–70`、`document_cli.py:48–49`仍直接返回006 files，是B5明确可见行为缺失。CLI响应已经取回，但其独立verify、sources逐行和最终副作用检查未到达，未认领通过。静查未到达代码未见确定测试错误。

## 保留状态

场景、自然语言设计及实现有效。v3两处漏检已修：418–454按独立expected取得kind、完整origin和原项目集合；476/487/541在初始、确认暂停、恢复三个时点核全来源数量及唯一全集。source_id全集加数量可拒绝遗漏后重复，完整origin不再由产品kind推期望。暂停期间也核两个Hub自有来源及其native状态。

反例逐断言推演：

- 仅首个来源正确、Q在恢复时误标Hub/native，最早448完整origin拒绝；保持origin但state错由449拒绝，错项目由454拒绝。
- 仅P暂停来源正确，暂停时漏掉任一native来源，由419–422拒绝；native误标暂停/保留由449–453拒绝。
- 仅首个命中正确，Q遗漏并重复P，由457–461数量及已知身份全集拒绝；Q/native状态错由468–474拒绝。该helper在477/503/547三个时点实际被调用，暂停不是仅单独挑出P/Q检查。
- 两结果误用同一目标/正文，416和457–461核独立身份全集，520、560–561核逐身份旧精确引用和独立正文，不能只靠两边相等通过。
- 共享文件的暂停/允许资格分别由574–590按稳定project_key核，600–603核允许资格推进后暂停项目可读独立新正文，避免把暂停误作冻结分支。

已覆盖的行为差异是device/native、零/多项目、允许/确认暂停/恢复及共享资格；无依据仅改同条件标识为可选。对未到达实现静查未见确定测试错误。

本Reviewer额外在内存用AST抽取实际 `assert_allowed_sources` / `assert_allowed_hits`，仅装入独立人工四来源夹具（两个device、一个双绑定native、一个零绑定native）。初始/暂停/恢复三正例均通过；Q改Hub/native、暂停缺native、native误标暂停、Q错项目、Q命中错状态、遗漏Q重复P六个负例均拒绝。命令为系统python3执行AST helper隔离脚本，无产品操作、无原件改写；实际输出为六行REJECTED和 `Known independent 4-source initial/pause/resume positives and 6 negatives passed; no product execution.`。该自检支持断言有效性，不代替本次未到达的产品业务。

原stdout为1 failed：476调用初始来源断言，在449读取sync_state报KeyError。00028-hub-13.json为HTTP200，四来源实际无sync_state/retained_snapshot/sync_message；产品 `documents.py:163–192` 只装饰origin/read_only/message。是可信B2/B6可见状态缺失。416初始命中全集及首来源448 origin已经执行；477初始命中状态、478后暂停/网页/恢复/共享均未到达。没有挪用旧版暂停原件称为本轮实测暂停，也没有授予这些路径通过。

## 目录指引与本轮原图

场景、设计及实现有效。687–715每次drag重新定位并核target/items；663–684捕获真实目录entry、委托原API审计枚举。717–736阻止产品收到自检drop，显式读取body.txt，看到createReader/readEntries后清审计再放行；638–642服务器子文件打开负控、739–760指引正反样本已执行，00012/00026-folder-probe-selfcheck.json可核。

只Local正确而Hub错由两端参数各自767/771拦截。纯目录正确而混合目录假成功由795–797逐目录行拒绝；双方误用同一错误文件/正文由801–819库身份和独立正文拒绝。776–781对应端完整document_snapshot及Hub状态、781/820–824枚举/服务器读取审计和836原指纹覆盖隐式采集及读取后丢弃。未到达代码静查未见确定测试故障。再换同条件名字是可选样本；普通FileEntry.file包装可影响未来不同上传实现，属可选健壮性检查，不据此阻塞当前路径。

已实际打开本次 `attachments/local-web-review.png`、`hub-web-review.png`。两端上传结果都显示“example-folder：失败 · 无法读取所选文件”，该处没有目录来源及适用创建端指引。Local下方添加来源表单、Hub页底CLI说明是其他位置的发现路径，不能替代当次目录提示。

实际打开两份trace ZIP、读取trace.trace：Local191事件、Hub212事件。bjbj@56/hfpn@161是自检目录；显式枚举body.txt并返回createReader/readEntries；清审计后bjbj@80/hfpn@185是产品drop，均inside=true/isDirectory=true。唯一after错误bjbj@94/hfpn@197对应767目录提示断言。stdout两参数均在767失败，是B8可信业务缺失。768之后方向/逐行断言、无上传/完整状态/终验审计、混合批次/read均未到达，未算实际通过；自检读取目录不当作产品扫描。

本次是实际Chrome页面/JS，网络请求经Playwright route转交真实TestClient，支撑此局部交互。不是E1真实网络/TLS/平台身份或E2服务实测。

## 意见交付及边界

三份独立JSON逐目标完成后立即通知主Agent登记，没有代为登记，没有等待整批后才交。每份仅含相应目标实际TC，均省略covers：

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-hub-status-provenance-status-v4.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-hub-retained-state-status-v4.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-folder-guidance-status-v4.json`

本轮只写以上三JSON和本报告。未修改产品、测试、冻结原件或旧意见，未执行GitHub、ESXi、日常服务、登记或产品业务重跑。只做只读材料核对及内存helper正反自检。后续产品实现和同测试绿灯、正式平台及需求判定须另取相应原件和独立意见。
