# AT-SMM-007 当前版本正式执行独立复审 v2

本轮完整 handoff 的 26 份 singleton execute、26 个 TC 已逐份独立复审，结论为 **26 passed**，认领 30 个实际分配检查。26 次外层执行含 33 个 pytest 参数实例；兼容项内层另有 42 个指定旧回归通过。该结论只适用于本轮范围，不等于 28 自动项、36 TC 或 R007 整体交付通过。

- 项目：`/private/tmp/smm-007`；验收：`AT-SMM-007`。
- Reviewer：`/root/review_007_current_formal_v2`。
- handoff：`/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/work/current-formal-v2-handoff.json`；SHA-256 `87d68bccda03e53c18661094aa26c6423023cd8142f517944288f1963ffef08f`。
- 定义：`d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`；候选标识：`b7ed5d7 F8 source`。
- 实际产品 `src/smm_local/document_search.py` SHA-256：`79eb9dd928a45e75aecbaf190aef8c7a4d522020cd797bb5d44e9837efc31360`。

复审以 AGENTS、007 SPEC/PLAN、验收技能 execution/reviewer 规则、实际实现和本轮原件为依据。逐目标重新计算 target_path 原字节 SHA；105 项当前运行 bindings 与已审 design_review 所引用运行绑定/实现摘要逐字对应，case_design 摘要、definitions、case_obligations 和设计分配一致。本轮累计 5723 个 artifact 清单引用全部摘要匹配；sync-boundaries 的 2742 份和 library-ingest 的 494 份 gzip 均完整解压，原字节长度/SHA 与 lossless manifest 一致，共 3236 份原始 JSON。

逐项核实 actual argv、cwd、证据环境路径、起止、exit、进程元数据、stdout/stderr 和附件。所有外层 exit0、stderr 空且 stdout 无 skip；结合无早退顺序断言、各参数和末端业务原件确认本次实际到达，未借 debug 日志替代正式证据。coverage=off 只表示未采集代码行覆盖，不是业务覆盖率数值。

| 场景 | TC | 结论 | 本次 covers | 原样独立意见 |
|---|---|---|---|---|
| SC1 | `TC-007-policy-choice` | passed | `policy-choice-1`, `policy-choice-2`, `policy-choice-3` | [review-execute-policy-choice-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-policy-choice-f8-v2.json) |
| SC2 | `TC-007-sync-boundaries` | passed | `sync-boundaries-3` | [review-execute-sync-boundaries-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-sync-boundaries-f8-v2.json) |
| SC2 | `TC-007-sync-publication` | passed | `sync-publication-1` | [review-execute-sync-publication-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-sync-publication-f8-v2.json) |
| SC2 | `TC-007-sync-retry` | passed | `sync-retry-2` | [review-execute-sync-retry-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-sync-retry-f8-v2.json) |
| SC3 | `TC-007-overlap-publication` | passed | `overlap-publication-2` | [review-execute-overlap-publication-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-overlap-publication-f8-v2.json) |
| SC3 | `TC-007-paused-lifecycle` | passed | `paused-lifecycle-1` | [review-execute-paused-lifecycle-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-paused-lifecycle-f8-v2.json) |
| SC4 | `TC-007-ordering-concurrency` | passed | `ordering-concurrency-2` | [review-execute-ordering-concurrency-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-ordering-concurrency-f8-v2.json) |
| SC4 | `TC-007-origin-identity` | passed | `origin-identity-1` | [review-execute-origin-identity-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-origin-identity-f8-v2.json) |
| SC4 | `TC-007-recovery-controls` | passed | `recovery-controls-3` | [review-execute-recovery-controls-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-recovery-controls-f8-v2.json) |
| SC5 | `TC-007-hub-native` | passed | `hub-native-1` | [review-execute-hub-native-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-hub-native-f8-v2.json) |
| SC5 | `TC-007-project-scope` | passed | `project-scope-2` | [review-execute-project-scope-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-project-scope-f8-v2.json) |
| SC6 | `TC-007-search-candidates` | passed | `search-candidates-1` | [review-execute-search-candidates-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-search-candidates-f8-v2.json) |
| SC6 | `TC-007-search-fallback` | passed | `search-fallback-2` | [review-execute-search-fallback-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-search-fallback-f8-v2.json) |
| SC6 | `TC-007-unconfigured-hub-root` | passed | `unconfigured-hub-root-3` | [review-execute-unconfigured-hub-root-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-unconfigured-hub-root-f8-v2.json) |
| SC7 | `TC-007-read-exact` | passed | `read-exact-1` | [review-execute-read-exact-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-read-exact-f8-v2.json) |
| SC7 | `TC-007-read-rejection` | passed | `read-rejection-2` | [review-execute-read-rejection-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-read-rejection-f8-v2.json) |
| SC8 | `TC-007-compatibility` | passed | `compatibility-1` | [review-execute-compatibility-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-compatibility-f8-v2.json) |
| SC8 | `TC-007-packages` | passed | `packages-2-build` | [review-execute-packages-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-packages-f8-v2.json) |
| SC10 | `TC-007-library-ingest` | passed | `library-ingest-1` | [review-execute-library-ingest-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-library-ingest-f8-v2.json) |
| SC10 | `TC-007-project-ownership` | passed | `project-ownership-3` | [review-execute-project-ownership-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-project-ownership-f8-v2.json) |
| SC12 | `TC-007-snippet-conflict` | passed | `snippet-conflict-1` | [review-execute-snippet-conflict-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-snippet-conflict-f8-v2.json) |
| SC13 | `TC-007-cli-scan-boundary` | passed | `cli-scan-boundary-1` | [review-execute-cli-scan-boundary-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-cli-scan-boundary-f8-v2.json) |
| SC14 | `TC-007-web-review-feedback` | passed | `web-review-feedback-1`, `web-review-feedback-2`, `web-review-feedback-3` | [review-execute-web-review-feedback-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-web-review-feedback-f8-v2.json) |
| SC15 | `TC-007-hub-retained-state` | passed | `hub-status-provenance-2` | [review-execute-hub-retained-state-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-hub-retained-state-f8-v2.json) |
| SC15 | `TC-007-hub-status-provenance` | passed | `hub-status-provenance-1` | [review-execute-hub-status-provenance-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-hub-status-provenance-f8-v2.json) |
| SC16 | `TC-007-folder-guidance` | passed | `folder-guidance-1` | [review-execute-folder-guidance-f8-v2](/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-folder-guidance-f8-v2.json) |

本轮关键证据与边界：

- 未配置 Hub 根：CLI/API/MCP 各两个合法同号 Local 负控，共六格原件均空结果/空有效项目、hub unavailable 和明确原因；normal/explicitLocal 各自两个独立 ID/正文及合计 24 次精确 ref 读回、原覆盖、无网络/源打开和状态守卫均完成。
- SC14：实际打开本轮四张 PNG，包括两端批次、Hub 空壳和本机原提供端；读取 local/hub trace（109/55 actions）及其原 resources，三次读取端为 Hub native、Local shared、Hub shared，逐文件批次与重放的 ID/原文正确。
- SC15：实际打开 retained-state 的本轮 Hub PNG；20 actions trace 与原 search resource 确认暂停保留可见，四个原身份在允许/暂停/恢复阶段均按独立预期核验，最后共享 V2 可由暂停资格准确读取。metadata TC 独立核 HTTP/CLI 全集及无正文/源打开守卫，不借另项图证明自身检查。
- SC16：实际打开本轮两端 PNG 和 zip 内目录单独帧（Local timestamp 818.695，Hub 841.04），并读 56/55 actions trace、network resources 和四份 guidance 原 JSON；目录不枚举/不上传，混合 valid 唯一保存且独立原文正确。只在内存解压图片，没有新增或改写证据。
- project-ownership 本轮 CLI 竞态实际为旧 context 的 CLI 成功、并发 recover 因同 state-dir admin.lock 被拒绝；这证明本次管理员互斥路径，不声称本次命中 stale-epoch CLI 拒绝。源码持锁后取 context、guard 内再核 context；HTTP 各旧 HID/epoch/稳定项目拒绝与正常正控另有本轮实际证据。
- hub-native-1 按已审 action 认 Hub 原生 CLI 和导入来源误 refresh/remove；完整跨端添加/更新/删除/绑定边界由本轮 project-ownership 独立承接。检查文字涉及的跨验证项分工不能用于把单项扩大为整场景通过。
- SC8 本轮仅 compatibility-1 和 packages-2-build；独立包 18 条真实命令/双流、Local 30/Hub 31 模块源码→wheel→安装断言及当前源码映射已核。完整回归/三系统 CI 门禁、用户发现均为其他人工验证项，不从本轮两项推出。

TC-007-library-update 与 TC-007-listing-coverage 不在本轮 26 目标中；没有为其写正式意见或扩大为 28 自动项通过。E1/E2、额外补强轮、需求级结论和合并门禁不在本轮判定范围。没有运行产品、服务、Windows/ESXi、日常来源或 GitHub 写操作；只写指定逐目标意见与本报告。
