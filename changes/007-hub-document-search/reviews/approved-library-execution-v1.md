# 已授权 library-update 正式执行独立复审 v1

结论：**passed**，仅 `TC-007-library-update` / SC10 的 `library-update-2`。没有将本结论扩展为整个 SC10、E1/E2 或整项交付通过。

- 项目：`/private/tmp/smm-007`；验收：`AT-SMM-007`。
- Reviewer：`/root/approved_library_execution_v1`；准备 Reviewer 为另一上下文 `/root/approved_two_tests_design_v1`。
- 目标：`.acceptance-local/native-v1/AT-SMM-007/execute/execute-library-update-approved-v1/result.json`。
- 目标原始字节 SHA-256：`1d493010be647ebf32a91128f42315f3f755e6e0cec52e9797d315a1d079e8da`。
- 当前定义摘要：`d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。
- 原样可登记意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-execute-library-update-approved-v1.json`。

已实际阅读 AGENTS、007 intent/spec/plan、独立 Reviewer 规则、`design-sc10-final-v2`、`review-debug-library-update-approved-v1`、当次正式执行收据、当前断言与相同版本源码副本、原始 stdout/stderr/process 以及全部业务附件。需求依据为 SPEC B8 的更新/删除契约和 B3 的暂停/撤回契约。复审保持产品和测试只读，没有运行测试，没有操作 E1/E2、ESXi 或 GitHub。

## 版本与原件

逐字节计算并核对交接目标 SHA、105 项 bindings 和 213 项 artifacts，均匹配。213 项包含 209 份业务附件、stdout、stderr、process 和执行请求。execute 本身没有单独的 source 目录；其 105 项 bindings 和用例 implementation 摘要均与 debug 完全相同，debug/source 中全部 105 份副本也逐字节匹配当前文件及执行绑定。设计记录摘要和准备复审所指 debug 目标摘要也一致。

正式命令只选择 `tests/test_hub_documents_contracts.py::test_library_update`。原始 stdout 为 `1 passed, 1 warning in 2.66s`，stderr 为空。警告为 TestClient 的 httpx 弃用提示，不影响业务断言。本结论以实际断言和下面的原始业务结果为依据。

## 实际覆盖

`tests/test_hub_documents_contracts.py:1219–1275` 对 Local 与 Hub 各两份正文不同的同名资料逐一执行；另一个项目中同名资料作为负控。

| 检查 | 断言与本次原始证据 |
|---|---|
| 保身份、显示名、归属、存储位置，换版、准确正文与旧 ref | 1228–1234 独立核上传回执 ID、v1→v2、原路径/名称/项目及磁盘原字节，正文由独立 replacement 1/2 字符串确定；Local 上传附件 00003/00004，Hub 00061/00063，四份对应 read 均正确，旧 ref 均 400。 |
| submission 幂等及异载荷拒绝 | 1231–1232 同请求重试返回相同确认；改字节重用 ID 返回 400，并比较文档库和管理副本状态。四份均到达。 |
| 两个 CAS 字段独立失效 | 1235–1246 在版本过期而 revision 当前、revision 过期而版本当前两种情况下分别拒绝，状态/磁盘比较不变；1265–1267 对删除同样逐字段核验。 |
| 相同字节连续 | 1248–1249 保持 v2 和原路径，用更新前当前 ref 仍读到完整独立正文。 |
| 中断保护 | 1254–1263 在实际 `os.replace` 完成后注入 OSError，断言注入确实命中、磁盘回到完整旧原字节且原 ref 仍准确。附件 00021/00043/00092/00130 为 400 中断结果；随后 00022/00044/00094/00132 都读回对应完整 replacement 1/2。此处是文件替换后的注入异常，不冒称实际杀进程断电。 |
| 删除、负控、上传重放 | 1268–1275 删除后退出查询且旧 ref 拒绝，另一项目同名负控仍读 `needle untouched`；Local 00055、Hub 00153 的已删除上传重放都返回 400，状态不变。 |

四份实际文档 ID 分别为 Local `112c8c1d3d1f46a7bf6600a597193edd` / `268fc05302a54bb2a46db76ccabadfba`，Hub `f51ff2d955104e59b2053e2020fa7c22` / `618988a811604f238eb9a6d6647ad86a`。复审逐目标核了上传、更新和 read 的身份、独立正文及对应引用，未以两响应一致代替目标正确。

`1277–1297` 的允许/暂停两状态都先明确允许并发布两份资料，再作暂停决定。1283 用独立上传回执的 ID 集、数量和唯一性核初始全集；1289 再核更新后的全集；1291–1292 按 `origin.document_id` 选出独立预期，逐 ref 读正文。仅首份正确、第二份重复或两份共同误指首份，都会在全集或第二份独立正文处失败。

| 动作前状态 | 本次正式证据 |
|---|---|
| 允许已有两份 | 00155/00156 给出两个独立本机 ID；00161/00166 均完整唯一对应二者。00168/00170 请求使用对应搜索 ref，逐份读到 replacement 2/1，均 v2。删除后 00176 空结果，00178/00180 两个旧 ref 均 400。 |
| 暂停已有两份 | 00182/00183 给出另外两个独立 ID；00188/00195 均完整唯一对应二者，暂停后仍 v1。00197/00199 按对应 ref 逐份读 original 2/1；没有把允许时应有的新正文错当暂停预期。删除后 00205 空结果，00207/00209 两个旧 ref 均 400。 |

所有分配检查本次均实际到达。未发现本范围内的证据缺失、测试故障或产品失败。`covers` 严格只有 `library-update-2`；真实浏览器交互、实际系统进程生命周期、服务身份和跨机器传输不在这份自动收据中认领。
