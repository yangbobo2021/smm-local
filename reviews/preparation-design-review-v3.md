# AT-SMM-007 准备阶段独立复审 v3

本轮20项准备证据可接受：19项新增能力取得可信 `expected_failure`，既有兼容基线1项 `passed`。未发现本轮范围内需要继续阻塞的场景、自然设计或实现缺口。此结论只允许进入产品实现，不是007产品交付通过。

## 本轮实际核对

项目为 `/private/tmp/smm-007`，产品HEAD为 `83b50fcbbad1f29484aa54104ca0f9e75d0498e3`，尚无007产品实现。实际阅读AGENTS.md、007 intent/spec/plan及项目文档库授权原话，技能SKILL/development/reviewer/design/implementation规则，并核000004全部场景判据。采用定义摘要 `0203f41968d96272ce5bd204e8e6cbbd273fc6d9c7441f27f9fa517b206481b3` 已按原文件字节重算一致。

实际核对自然设计design-sc1..10-v4（SC8为v5）、match-sc1..10-v4、runtime-red-v3；逐项打开当前冻结测试、helper、包及探针源码、原始stdout/stderr和附件。20个目标result的SHA均与唯一handoff相符；其所有artifacts原件摘要、所有bindings与当前文件实算一致，无跨版证据。测试文件SHA为 `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77`。

以AST实际选段核对前轮冻结源码与当前源码，确认恰8个test声明改变；其余12个test声明及w夹具字节相同。相同声明亦重新阅读本轮源码及原始运行证据，没有以旧passed替代新核对。20份意见均仅包含各目标真实TC；TDD不认领covers，兼容基线仅认领其全部分配 `compatibility-1`。

## 八项修订的实质

| 用例 | 原始依据与本轮实际检查 |
|---|---|
| sync-publication | B4/A2。150–192两来源各两份独立正文/身份/元数据；从已发布V1真实引用派生有效签名future，186发布前拒绝，192同一引用发布后成功，排除坏内层引用的假拒绝。 |
| sync-boundaries | B1/B4/B5/A2。296–318旧目录计费不变而9成员各推进2MiB，完整9ID/逐全文窗口证明不按旧预算截断；319–345真实Hub CLI分别核16MiB/超限及1000/1001候选。 |
| paused-lifecycle | B3/A3。active与paused前已有效分别做413–426单文件不可读→partial→同字节恢复，独立兄弟持续可读、失效成员旧ref拒绝，未用整源失败代替partial。 |
| ordering-concurrency | B4/A4。真实publish接受后延迟ack；553使较新pause真正网络未确认，580–583释放旧ack前后及重启仍保新pending，独立事务与控制在release前完成。 |
| recovery-controls | B4/B5/A4。633–638真实授权V1发布正控与预暂存V2，故障后663拒绝发布；Local645–650健康离线诊断及真实待发V2，故障后禁正文，显式选择恢复。 |
| search-candidates | B6/A6。两端长原文>2000，841–844实际片段逐原件/端点/有界校验，846–855只以正常返回片段计算独立BM25，864–865核全部排序和分数。 |
| search-fallback | B6/A6。932本机exact IDs精确P/Q，933仅一次query-scope，934/935两端共用该签名范围，962区分unsupported/unavailable；另核冻结/拒绝及同号ID负控。 |
| library-update | B8/A10。1264–1267两创建端每份资料的DELETE分别只令version或revision过期，其余当前有效，拒绝且完整DB/管理副本不变，1268当前值删除成功。 |

逐项意见分别写出原始判据依据、首目标正确/其它目标错误、单一适用动作前状态错误、两结果同错的拦截位置。现有输入已区分有依据的行为差异；相同条件下换等价ID/日期/数额属于可选补测，不继续以等价样本数量阻塞。

## 原始执行与限制

19份红灯均实际退出1。首失败分别是已确认公共能力缺失：sync-status/library 404、认证info缺document_epoch、显式local被API/CLI拒绝、Hub CLI无project create、默认查询仍local_documents。未以导入不存在模块、环境失败或测试语法错误作为红灯。每份意见注明实际首失败与未到达部分；未到达的设计/断言经源码复核可信，仍不算产品执行通过。

兼容基线原始run.stdout为1 passed、进程exit0；附件00029的旧005/upload/Vibe/help回归为42 passed。compatibility-1分配的检查全部实际到达。完整pytest、最终三系统CI、双包全部成功和新007产品行为不由该基线认领。

7人工项的设计和可执行步骤已匹配；本轮未实际操作浏览器或正式执行人工项，不授任何人工passed。user-discovery明确两条真实旧页提交、Hub凭据内存/认证头与reload、纯文本不执行的画面/轨迹/请求证据；E1/E2保持当前SPEC完整要求。未访问家庭ESXi或任何远程测试机。历史控制器/浏览器/探针自检只证明准备，不是Windows/Linux产品平台通过。无替代实机时相关E1/E2保持待验证，不能据本报告合并交付。

## 逐目标意见

| TC | 本轮目标 | 结论 | 原样意见 |
|---|---|---|---|
| TC-007-hub-native | red-007-hub-native-v3 | expected_failure | [review-red-007-hub-native-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-hub-native-v3.json) |
| TC-007-library-ingest | red-007-library-ingest-v3 | expected_failure | [review-red-007-library-ingest-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-library-ingest-v3.json) |
| TC-007-library-update | red-007-library-update-v3 | expected_failure | [review-red-007-library-update-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-library-update-v3.json) |
| TC-007-ordering-concurrency | red-007-ordering-concurrency-v3 | expected_failure | [review-red-007-ordering-concurrency-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-ordering-concurrency-v3.json) |
| TC-007-origin-identity | red-007-origin-identity-v3 | expected_failure | [review-red-007-origin-identity-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-origin-identity-v3.json) |
| TC-007-overlap-publication | red-007-overlap-publication-v3 | expected_failure | [review-red-007-overlap-publication-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-overlap-publication-v3.json) |
| TC-007-packages | red-007-packages-v3 | expected_failure | [review-red-007-packages-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-packages-v3.json) |
| TC-007-paused-lifecycle | red-007-paused-lifecycle-v3 | expected_failure | [review-red-007-paused-lifecycle-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-paused-lifecycle-v3.json) |
| TC-007-policy-choice | red-007-policy-choice-v3 | expected_failure | [review-red-007-policy-choice-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-policy-choice-v3.json) |
| TC-007-project-ownership | red-007-project-ownership-v3 | expected_failure | [review-red-007-project-ownership-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-project-ownership-v3.json) |
| TC-007-project-scope | red-007-project-scope-v3 | expected_failure | [review-red-007-project-scope-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-project-scope-v3.json) |
| TC-007-read-exact | red-007-read-exact-v3 | expected_failure | [review-red-007-read-exact-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-read-exact-v3.json) |
| TC-007-read-rejection | red-007-read-rejection-v3 | expected_failure | [review-red-007-read-rejection-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-read-rejection-v3.json) |
| TC-007-recovery-controls | red-007-recovery-controls-v3 | expected_failure | [review-red-007-recovery-controls-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-recovery-controls-v3.json) |
| TC-007-search-candidates | red-007-search-candidates-v3 | expected_failure | [review-red-007-search-candidates-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-search-candidates-v3.json) |
| TC-007-search-fallback | red-007-search-fallback-v3 | expected_failure | [review-red-007-search-fallback-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-search-fallback-v3.json) |
| TC-007-sync-boundaries | red-007-sync-boundaries-v3 | expected_failure | [review-red-007-sync-boundaries-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-sync-boundaries-v3.json) |
| TC-007-sync-publication | red-007-sync-publication-v3 | expected_failure | [review-red-007-sync-publication-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-sync-publication-v3.json) |
| TC-007-sync-retry | red-007-sync-retry-v3 | expected_failure | [review-red-007-sync-retry-v3.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-sync-retry-v3.json) |
| TC-007-compatibility | baseline-007-compatibility-v4 | passed | [review-baseline-007-compatibility-v4.json](..//private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-baseline-007-compatibility-v4.json) |
