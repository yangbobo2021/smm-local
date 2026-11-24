# AT-SMM-007 状态补充同测试绿灯复审 v1

结论：交接的 SC15/SC16 三 TC、四个 pytest 参数执行均为 **passed**，支持 F5–F7 这三个局部修复。各自四文件回归均为 19 passed。该结论不等于 34 TC 正式验收、R007 需求判定、E1/E2 平台或整体交付通过。

## 范围、依据及版本

独立 Reviewer `/root/review_007_status_green_v1`；根 `/private/tmp/smm-007`。实际读取交付验收技能 SKILL.md、development、execution/reviewer，项目 AGENTS、007 intent/spec/plan、`changes/007-hub-document-search/reviews/project-library-authorization.md`、根 `reviews/pr39-review-v2.md` 和 `reviews/status-red-review-v4.md`。本轮仅只读产品、测试和证据，只写交接的三个唯一 JSON 及此报告；没有执行登记、产品业务重跑、ESXi、日常服务或 GitHub 操作。

意图规定结果应解释来源、项目、版本、停止同步和保留副本；B2/B5 明确 Hub sources/files 的身份、项目资格及采集/接收信息，B3 规定暂停保留连续资格、共享文件仍能由另一允许资格推进当前版本，B6 要求结果/coverage 区分保留快照，B8 要求文件夹拖入引导明确目录来源及逐份真实结果。用户的创建端管理原话进一步决定 Local 和 Hub 应给出不同的目录纳入路径。SC15/16 及自然语言设计未据此增加新授权体系或冻结分支。

定义 `000007.json` 实算 SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。SC15/SC16 的 design-sc15-v4 / design-sc16-v4 摘要分别实算为 `e9d890e5b0205a5990e4493b88f99ea57995e36250cc75c643207057079b3117` / `5a56fa9003773eb5f5efedd3c44a55cf3e14c6fd10e7ecdd94df75383e223128`。第一检查分配给 metadata TC，第二检查独立 retained TC；目录 TC 两端参数覆盖同一个实际身份。

本轮按交接目标的当前完整文件 SHA 判适用性，未因产品修改尚未提交而推断失效。测试 SHA `81e29a9751c1b2e3f6793ea2b70ba14e285ae0c72ab27488e1db1f02f69d0d00`；三目标的 cases、test_bindings 与获准额外一轮的 v4 红灯逐对象完全相同，包含相同测试源选段、公共夹具和原 command。三个已登记 tdd-red review 的 judgments 都为 expected_failure，其保存的 reviewer.txt 与原 review-inbox JSON 逐字节相同。旧意见与原始失败未被替换。

| 当前 tdd-green 目标 | result.json SHA | 当前 bindings / product / test / artifacts | 原始业务 stdout | 原始回归 stdout |
|---|---|---|---|---|
| green-007-hub-status-provenance-status-v4-a | `4bb7a8b6b803b9cb78c9cda957440e7947a0485bdac06661808c84d1cf5dc639` | 56 / 45 / 6 / 76 | 1 passed | 19 passed |
| green-007-hub-retained-state-status-v4-a | `ad634ea1bf95d54b593fd375e242e377798fc350bd834ff0945766d0d5e7c150` | 56 / 45 / 6 / 101 | 1 passed | 19 passed |
| green-007-folder-guidance-status-v4-a | `5835b759af672d0eac03ab1858c589faab6409c51fc289292cd1391f49f14b01` | 56 / 45 / 6 / 61 | 2 passed | 19 passed |

上述每项 bindings、product_bindings、test_bindings 和 artifacts 全部对实际文件逐字节重算，无缺件或 SHA 不符；不只核结果字段。业务和回归的 process/输出原件均已检查，exit0、stderr 空。各回归 argv 精确包含 test_document_compatibility.py、test_document_lifecycle.py、test_document_search.py、test_document_sync_recovery_scope.py。

当前六个相关产品文件 SHA：

- `src/smm_hub/documents.py`：`7f2ff0fca5566eadc8366b54201a10794bc3b5dcf2b6368ef7b4012511e3d9d5`
- `src/smm_hub/document_api.py`：`4534d9960696958c35117ce264329cd7bdeb3c4c2a05fb78bb9e1e3e97ed3667`
- `src/smm_hub/document_cli.py`：`946ad71a44995239656578f09ff917a37525ddf2273b36290ea461244a0a24c3`
- `src/smm_hub/static/index.html`：`7ad6ce7a1161a8811284540984eeb956d7c706d4b54117bb30df38c95203c23a`
- `src/smm_local/document_search.py`：`4f3e58f93f0681ba2739b805a5f66dc080ab64e7dd3fe91440054986a4737c85`
- `src/smm_local/static/index.html`：`7197d7f6bd3ab27522d7860ce98a3ce473ef77190cb5340bf262e5177fd36932`

## F5：列表元信息

先从 design-sc15-v4 的 hub-status-provenance-1 反查 `tests/test_document_status_contracts.py:153–396`。四个独立目标涵盖两个设备项目来源、Hub 双项目绑定和 Hub 零绑定。207–260 按独立原身份核 SHA、长度、版本、资格、来源及项目，核适用采集/接收时间和全集唯一性；262–328 核所有来源的 origin、project_ids、status、revision、read_only、无正文及适用时间，并逐源请求 HTTP 与真实 CLI files。若只有首个正确，其余错误，独立 expected 与全集/唯一性最早拒绝；HTTP/CLI 同时误取错误项目或同一个目标也不能靠二者相等通过。329–384 的正确/错误元信息、时区、真实 Python/CLI 源打开正反自检有实际原件。

证据根为 `.acceptance-local/native-v1/AT-SMM-007/tdd-green/green-007-hub-status-provenance-status-v4-a/TC-007-hub-status-provenance/attachments/`。`00027-status-probe-selfcheck.json`、`00026-metadata-cli.json` 支持自检；实际读取 `00028-hub-11.json` / `00029-metadata-cli.json` 四行文件，含准确 origin/source_origin、项目、status/qualification、captured_at/received_at；`00034-hub-16.json` / `00035-metadata-cli.json` 四来源区分设备、自有、多/零绑定，后续 `00036–00063` 是每个来源对应 HTTP/CLI files。测试已到达末尾零源读取和完整 snapshot 不变断言，旧红灯后未到达的 sources 检查本轮确已执行。

产品 API/CLI files 共用 `HubDocuments.files`；sources/files 从既有档案装饰出处和当前文件采集/接收时间，资格保留，不返回正文、不扫描。sources 默认取得短 control_lock，已在锁内的 files/native/search/read 传 locked=True，避免非重入锁递归。没有变更数据库 schema、正文或引用格式。

## F6：确认暂停、恢复及共享当前版本

design-sc15-v4 的 hub-status-provenance-2 对应 `tests/test_document_status_contracts.py:398–603`。初始/确认暂停/恢复三阶段独立 expected 覆盖四来源/四命中，419–474 核 origin、项目、完整身份数量与状态。只 P 正确、Q 错 kind/项目/状态、暂停漏 native 或重复 P 代 Q 都会失败；520、560–561 逐身份用旧精确引用和独立正文核暂停/恢复，未以两边响应相等替代预期。574–603 分项目核共享资格，核允许资格推进后的当前新文本。

证据根为同 tdd-green 下 `green-007-hub-retained-state-status-v4-a/TC-007-hub-retained-state/attachments/`。`00032-api-015.json` 的 P 实际 paused，generation=confirmed_generation=2；`00033-hub-14.json` 中 P paused/retained，Q allowed，两个 Hub native 仍在。`00035-hub-16.json` 的 results/coverage 具有对应状态，`00037/39/41/43` read 正文正确。恢复实际到达 `00052-hub-25.json` / `00054-hub-27.json`，全部返回相应 allowed/native 和 retained=false，`00056/58/60/62` 保留旧引用的准确原文。

共享 `00072-hub-39.json` 的同文件两个 project_key 分别 paused/allowed；`00074/78` 限定项目分别返回对应资格，`00076/80` 读回独立旧文本。最后 `00084-hub-49.json` 与 `00086-hub-51.json` 实际在暂停项目读到 version2 及 `sharedstatusnonce advanced through allowed project`，暂停资格仍有效。该关键路径本次已经到达，不再引用红灯前静态代码冒充运行。

实际打开 `hub-web-review.png`：Status P 为只读投影，received-one 命中及 coverage 写明暂停后保留，来源行说明“保留仍有效的资格，共享文件可由其他允许来源更新”；Q 仍允许，两 Hub 来源说明自有。实际读完整 `hub-web-review-trace.zip/trace.trace`，121事件、无 after 错误；nshk@28 是来源文字，@44/@46 是命中文字，@48 是截图。实际打开 ZIP 内 `screencast/page@c4af8024957cc0425349f953dbbd06d1-1795438575389.jpeg` 核同次画面。

Hub sources/_snapshot_metadata/search/read 共用逐资格 state/origin/project 数据，保持文件级版本；search coverage 装饰相应来源。Local 联合查询保留远端 hit 元信息和 coverage.hub_sources，Local/Hub 两 HTML 均渲染命中/read/coverage 分支。这部分 Local 保留 UI 和 conflict 状态是当前代码核对，本 TC 真实保留状态网页仅执行 Hub，未把这两个未实测差异扩大为 passed。

## F7：真实目录及混合批次，两端分别核对

design-sc16-v4 的 folder-guidance-1 对应 `tests/test_document_status_contracts.py:624–836`。源打开负控在638–642，663–684委托原浏览器目录 API 观察枚举，687–715每次重新定位、滚动和读取 bounding box，核真实 drop target/items；717–736 的自检 drop 会被捕获阶段 stopImmediatePropagation 拦截，显式枚举得到 body.txt 后清审计再解除 selfcheck，不能把该枚举误当产品扫描。739–760 对指引正反样本检查，之后每个真实单目录/混合目录均逐行验证。只有 Local 正确会使 Hub 参数失败；混合目录假成功被 guidance 拦截；双方误取同一文件被库 ID/精确ref及独立正文拒绝。

证据根为同 tdd-green 下 `green-007-folder-guidance-status-v4-a/TC-007-folder-guidance/attachments/`。实际读取 `00012/00033-folder-probe-selfcheck.json`、`00017/00037-actual-folder-guidance.json`、`00023/00044-actual-mixed-folder-guidance.json`，并逐当前代码核证据产生前断言。纯目录没有上传 POST，目标端所有 document 相关表/项目完整 snapshot 及 Hub snapshot 不变；混合时库只含 valid.txt、read 精确等于独立 `mixedfoldernonce independent valid`。目录枚举审计、服务子文件读取审计始终空，只有一个合法文件来源；末尾子文件字节和mtime相同。两端都实际到达这些末尾检查。

实际打开 `local-web-review.png`：example-folder 未处理，指向“添加文档来源”、本机 SMM 服务所在电脑的目录和明确刷新；valid.txt 成功，其文档 ID 与库行一致。`hub-web-review.png`：example-folder 未处理，明确 Hub 电脑由维护者经 Hub CLI 添加目录/refresh；若在浏览器用户电脑则到本机 SMM 添加目录来源再按项目同步；valid.txt 成功且库 ID 一致。它们是混合批次当次逐份结果，不是页脚说明替代错误处引导。

两 ZIP 的 trace.trace 实际读取为 Local270/Hub287事件，均无 after 错误。Local tdjv@56/58/60 和 Hub jspm@213/215/217 是自检真实目录、body.txt 枚举及createReader/readEntries；@64/@221 清零放行。业务 @80/@237 单目录和 @120/@275 混合的 inside=true、真实 isDirectory 及文件名均已核；@102/@144/@257/@297 审计为 []。三次独立 waitForSelector（Local @42/46、@66/70、@106/110；Hub @199/203、@223/227、@261/265）和源码定位步骤对应，未复用过时坐标。

实际打开 ZIP 内关键图：

- Local `screencast/page@813d46bfc55b305d27f6b96883abecb1-1795438586929.jpeg`：纯目录0成功/1未处理，指向本机来源及刷新；`…-1795438587186.jpeg`：混合valid成功并显示同一来源/库行。
- Hub `screencast/page@39b92936aa35a71a4671d68a83dc55d2-1795438588323.jpeg`：纯目录未处理及适用Hub电脑/CLI或本机来源指引；`…-1795438588473.jpeg`：混合valid成功，目录仍未处理。

当前两个 drop 处理只读取 entry.isDirectory 识别目录并生成指引，不调用目录枚举；其他 file 进入原逐份保存流程。实际 Chrome + Playwright route 转交真实 TestClient 支持局部交互与档案行为，不能用作真实网络/TLS、平台身份、服务或跨机器验收。

## 原样独立意见与限制

每完成一份即写唯一文件并通知主 Agent 登记，未等待整批后交。三个 JSON 仅包含对应的实际 TC，省略 covers；reason 区分已到达检查及证据边界：

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-hub-status-provenance-status-v4-a.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-hub-retained-state-status-v4-a.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-folder-guidance-status-v4-a.json`

本轮分配的三个 TC 所有适用断言实际到达；没有将红灯未到达路径、设计文字或 observation 的布尔结果单独当通过依据。完整回归附加材料 `/private/tmp/smm-007-status-fixed-regression.stdout` 已结束，原文为334 passed/1 skipped；XML335项、0 failure/0 error/1 skip，二者一致。仅有限核对附加输出，没有由该套件摘要逐项授予其他TC正式passed。

局部绿灯不解决仍需当前同版正式记录、平台实机/完整trace、需求独立判定和公开证据收口的剩余义务，不支持宣布交付通过或合并就绪。
