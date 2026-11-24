# AT-SMM-007 当前候选设计与调试复审 v3

仅审本轮 current-debug-v3-handoff.json 指定的 15 目标、28 自动 TC。结论：26 passed，2 needs_revision（均为测试 implementation）。28 TC 本轮真实调试均 exit 0；绿灯不能填补下列独立断言缺口。没有据此判定正式执行、人工项、E1/E2 或 R007 交付。

依据为本 worktree 的 AGENTS.md、changes/007-hub-document-search/spec.md（SHA-256 590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6）、plan.md、验收技能 Reviewer/设计边界规则及定义 .acceptance/native-v1/AT-SMM-007/definitions/000007.json。定义原样 SHA-256 d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd 已独立重算，SPEC 来源摘要匹配。

SC6 design-sc6-f8-v1保留原两TC/两检查，新增无Hub配置检查与三公共入口×两根的6格；本轮已看到全部6格独立原件。SC8 design-sc8-final-v3将独立包 packages-2-build 与人工完整回归/三系统CI packages-2-gate分开，人工用户发现亦单列；本报告只认领两个自动TC负责检查。当前总36 TC/28自动/8人工，未把人工匹配当执行。

## 需修订项

1. **TC-007-library-update：implementation。** SPEC B2/B3/B8/A10、plan SC10及design-sc10-final-v2要求当前两份资料在允许/暂停状态逐份同步/保留。tests/test_hub_documents_contracts.py:1281未核初始Hub身份全集；:1286–1289只遍历实际命中并检查数量2。若漏第二资料并重复第一资料，两个命中都映射i=1、正文断言及len2均过，old字典还会将重复折叠，最终只拒绝第一ref。最小补初始与更新后Hub结果的两assets IDs全集、唯一数量及逐ID独立原文；保留现有CAS/同提交/中断/删除及两前状态。已有两份样本足够，不是新增等价样本要求。本轮数据确实正确，未据此声称产品缺陷。
2. **TC-007-listing-coverage：implementation。** SPEC B6默认本机响应保留及plan SC11完整本机名单，适用于现有无文档Existing before Hub和有文档Listing Local。tests/test_document_review_contracts.py:33只验list类型，:43只新p成员，在线API :45–46只coverage；:48–49又用未独立核实的默认输出作:59/:62断线expected。默认/在线/离线都漏Existing时可两边同错通过。最小从独立档案全项目取得预期并分别核默认MCP/API、在线include_hub及离线本机列表，不需新增项目。SC5另有全量检查，但其不同已登记混合准备状态不能替此首次列表只读前状态的独立观察。此项源guard、覆盖原因和无写副作用断言有效，未据此判当前产品失败。

## 逐项结论

| 场景 | TC | 设计/调试复审 | covers | 最早返修环节 |
|---|---|---|---|---|
| SC1 | TC-007-policy-choice | passed | policy-choice-1,policy-choice-2,policy-choice-3 | — |
| SC2 | TC-007-sync-boundaries | passed | sync-boundaries-3 | — |
| SC2 | TC-007-sync-publication | passed | sync-publication-1 | — |
| SC2 | TC-007-sync-retry | passed | sync-retry-2 | — |
| SC3 | TC-007-overlap-publication | passed | overlap-publication-2 | — |
| SC3 | TC-007-paused-lifecycle | passed | paused-lifecycle-1 | — |
| SC4 | TC-007-ordering-concurrency | passed | ordering-concurrency-2 | — |
| SC4 | TC-007-origin-identity | passed | origin-identity-1 | — |
| SC4 | TC-007-recovery-controls | passed | recovery-controls-3 | — |
| SC5 | TC-007-hub-native | passed | hub-native-1 | — |
| SC5 | TC-007-project-scope | passed | project-scope-2 | — |
| SC6 | TC-007-search-candidates | passed | search-candidates-1 | — |
| SC6 | TC-007-search-fallback | passed | search-fallback-2 | — |
| SC6 | TC-007-unconfigured-hub-root | passed | unconfigured-hub-root-3 | — |
| SC7 | TC-007-read-exact | passed | read-exact-1 | — |
| SC7 | TC-007-read-rejection | passed | read-rejection-2 | — |
| SC8 | TC-007-compatibility | passed | compatibility-1 | — |
| SC8 | TC-007-packages | passed | packages-2-build | — |
| SC10 | TC-007-library-ingest | passed | library-ingest-1 | — |
| SC10 | TC-007-library-update | needs_revision | — | implementation |
| SC10 | TC-007-project-ownership | passed | project-ownership-3 | — |
| SC11 | TC-007-listing-coverage | needs_revision | — | implementation |
| SC12 | TC-007-snippet-conflict | passed | snippet-conflict-1 | — |
| SC13 | TC-007-cli-scan-boundary | passed | cli-scan-boundary-1 | — |
| SC14 | TC-007-web-review-feedback | passed | web-review-feedback-1,web-review-feedback-2,web-review-feedback-3 | — |
| SC15 | TC-007-hub-retained-state | passed | hub-status-provenance-2 | — |
| SC15 | TC-007-hub-status-provenance | passed | hub-status-provenance-1 | — |
| SC16 | TC-007-folder-guidance | passed | folder-guidance-1 | — |

passed意见的covers均等于其debug.case_obligations全部分配；reason分别说明业务依据、自然语言设计、实际输入/断言、首目标或两边同错反例的首拦截、会改变预期的动作前状态及本次实际到达情况。两项需修订的大检查未认领完整covers。所有意见JSON只含对应目标的实际caseIDs。

## 原件及可见证据

- 独立重算15目标SHA、设计引用SHA、每份105项当前binding及全部登记artifact/双流SHA，均匹配。各目标source/实际冻结60份测试/工具/配置；每份冻结文件都匹配binding，各TC最新适用match.source的路径、SHA及首末行源码文字都与冻结候选一致。其余45产品文件为运行binding，当前文件SHA亦逐项匹配；未把未复制到source/的产品文件宣称已复制。
- SC2 gzip原件按lossless-evidence逐一解压重算内部原SHA全部匹配。实际边界2097152/2097153、请求16777216/16777217及9份合计18874368当前正文原件可复核；中断/恢复是真实PID 2909/2910，强制中断与正常清理区分。
- SC8当前本轮独立包附件package-probe-originals含18真实命令与36原双流，退出均0、命令流SHA逐一匹配。当前源码对应Local30/Hub31个模块/HTML、vendor转换shim均独立重算，并与installed-modules完整mapping一致；Hub hub_has_no_local=true。实际两端CLI原文不同且准确、Local MCP三文档工具存在。没有从包通过推断人工CI门禁。
- SC14四张本轮PNG全部实际打开：两端A成功/B严格UTF8失败/C成功与两份库条目；Hub管理未认证空壳；Local共享原文先实际本机、再实际Hub，原文/稳定原身份保持。实际解析local/hub两trace分别109/55 actions均无error；三个可定位read响应依次Hub自有、Local共享、Hub同版共享。
- SC15实际打开本轮Hub PNG，Status P来源/命中暂停保留、Q允许、Hub多/零绑定各不同；同轮20-action trace可见源行和项目命中断言。四身份逐项元信息、资格、采集接收窗口、源打开自检及共享V2独立原文均有断言。
- SC16两张本轮PNG及两个trace实际打开，另直接查看原trace目录单独画面（Local timestamp794.370，Hub836.248）。单目录未处理/创建端目录来源指引与混合valid成功均可见；56/55动作无error，原CDP target/items、目录枚举和服务器源打开探针正反自检已核。未产生解压文件或改原件。
- SC10 ownership竞态原件的实际路径是CLI先获保护、recover exit2（“此档案已有同步服务正在启动或运行”），随后重新取state恢复及旧ref失效。未将其描述为已实到“恢复先完成”分支。

浏览器使用真实Chrome加载实际HTML，HTTP由TestClient处理器通过route.fulfill完成。上述证据只证明本轮自动UI回归，不证明真实平台普通账号、E1网络/stdio、E2服务身份或跨机器。旧debug/正式/包v5没有替代本轮调试。

## 精确目标与意见路径

以下均从完整handoff读取并核对实际字节，不缩写摘要或推算路径。

| 场景 | target | target_path | target SHA-256 | caseIDs | review_file |
|---|---|---|---|---|---|
| SC1 | debug-sc1-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc1-f8-current-v3/result.json | 60ddb62f5f008c1f8593868701cbfa3aa9f2edd077c790878ac34127d1ba4c3c | TC-007-policy-choice | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc1-f8-current-v3.json |
| SC2 | debug-sc2-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc2-f8-current-v3/result.json | 4c419e8e40e7a858f9b12f16c960108c3c593383318925adfad67a6e4e2a0e15 | TC-007-sync-boundaries, TC-007-sync-publication, TC-007-sync-retry | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc2-f8-current-v3.json |
| SC3 | debug-sc3-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc3-f8-current-v3/result.json | bc52c46c98264f8fb9608fe6a3a6d38fce9fe26605aa7a0fce82718519604a8d | TC-007-overlap-publication, TC-007-paused-lifecycle | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc3-f8-current-v3.json |
| SC4 | debug-sc4-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc4-f8-current-v3/result.json | d052f88ecdf493f75928dc86092999d41bcf7cd5a03d30ae460b0d3655a675f5 | TC-007-ordering-concurrency, TC-007-origin-identity, TC-007-recovery-controls | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc4-f8-current-v3.json |
| SC5 | debug-sc5-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc5-f8-current-v3/result.json | 54a5391f159b61f6091296de070cf8f38db6d8c1afa13887557b43cf944a4887 | TC-007-hub-native, TC-007-project-scope | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc5-f8-current-v3.json |
| SC6 | debug-sc6-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc6-f8-current-v3/result.json | 54a7d37040cb57f8c5c2ef3889fa6b5ed478e734e1ac3abb499baafef8ba76fb | TC-007-search-candidates, TC-007-search-fallback, TC-007-unconfigured-hub-root | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc6-f8-current-v3.json |
| SC7 | debug-sc7-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc7-f8-current-v3/result.json | 93a1a938bf1f13e6925f5866df29c26525ec09e868c538a757b95c9a2ced72e9 | TC-007-read-exact, TC-007-read-rejection | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc7-f8-current-v3.json |
| SC8 | debug-sc8-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc8-f8-current-v3/result.json | a5847395f7d6eed485232627a48d8e83cc1210a35a00b520393c08679cb39a84 | TC-007-compatibility, TC-007-packages | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc8-f8-current-v3.json |
| SC10 | debug-sc10-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc10-f8-current-v3/result.json | 8875dd9e36ceb73a044358b26644af04a7c04d2a3c5a2eca81ac0e91173c7d78 | TC-007-library-ingest, TC-007-library-update, TC-007-project-ownership | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc10-f8-current-v3.json |
| SC11 | debug-sc11-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc11-f8-current-v3/result.json | 88e8cce743491a7bcb1bb2ba4b6fda513acbd333cc0bb6998510c5935841efa2 | TC-007-listing-coverage | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc11-f8-current-v3.json |
| SC12 | debug-sc12-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc12-f8-current-v3/result.json | e0765444d06448f3ab9369925aea9d30d8d7a8467600064bd0397d50cc466521 | TC-007-snippet-conflict | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc12-f8-current-v3.json |
| SC13 | debug-sc13-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc13-f8-current-v3/result.json | 9be9d4059890f13e74ee25d8e93189dd507f3b5aeb704e2906a923799fd046fb | TC-007-cli-scan-boundary | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc13-f8-current-v3.json |
| SC14 | debug-sc14-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc14-f8-current-v3/result.json | ec071604337a43bb38d605604ec4dc2af1765abdf5a5bad32525795ce4da93f6 | TC-007-web-review-feedback | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc14-f8-current-v3.json |
| SC15 | debug-sc15-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc15-f8-current-v3/result.json | cf7fca6d14cdf4d8f0dd621935e3fbfc9e5b7ade09473739c7f7ce3a4bddb21d | TC-007-hub-retained-state, TC-007-hub-status-provenance | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc15-f8-current-v3.json |
| SC16 | debug-sc16-f8-current-v3 | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/debug/debug-sc16-f8-current-v3/result.json | 3716d047b804072f37163ebe9a7250fb6d0945f366931f43b36bd9a3ca1599d8 | TC-007-folder-guidance | /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc16-f8-current-v3.json |

本轮逐目标JSON已分别写出并立即通知主Agent登记。只写hand-off指定15份意见和本报告，未修改产品/测试/调试原件，未执行产品、服务、ESXi、日常数据或GitHub写入。
