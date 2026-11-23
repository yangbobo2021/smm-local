# AT-SMM-007 新增缺口红灯独立复审 v2

独立 Reviewer：`/root/review_007_gap_red_v2`。只读核查 `work/review-gap-red-v4-handoff.json` 的两个目标；逐份意见已写入交接指定文件并立即通知根 Agent，由根登记。本轮结论：SC11 `needs_revision / implementation`，SC12 `expected_failure`。

## 基线与证据

实际读取验收技能、development、reviewer及设计边界约定，项目AGENTS/CLAUDE、SPEC B6/B7原文、定义000005、两个自然设计与match-v3、完整新增测试与辅助夹具、相关产品实现及原始stdout/附件。未执行业务测试、修改产品或冻结测试。

定义000005实算SHA为 `176e4c3412612ac48b72d65458d81bd67b66246fa28877e3166ba39f20814419`；与000004比较，需求及原十个场景逐项相同，只新增SC11/SC12。当前SPEC SHA为 `590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`，符合需求记录。两个设计结果摘要匹配目标引用。当前冻结测试SHA为 `195ae0f439817a3abb1e8eed9aa8e3137fd467699ef13c1035a962c3a948a709`。

两目标全部artifacts、bindings逐文件重算一致：列表18项artifacts/50项bindings，片段17项artifacts/50项bindings。两份stderr为空，stdout均实际exit=1，失败发生在业务契约处；没有仅因进程非零判预期失败。

| 场景/用例 | 目标result.json SHA-256 | 意见 |
|---|---|---|
| SC11 / TC-007-listing-coverage | `e6fb629052c9fd88b3c27d9e77b4365e65c17d5353ae25687b7911f172e7f64c` | needs_revision / implementation |
| SC12 / TC-007-snippet-conflict | `03b2bc4e9d1677f42d130332550337bb1871142e69feb99078f282f940a996aa` | expected_failure |

## SC11：真实列表缺失保留，副作用观察仍需前移

SPEC B6第79、87行及B7第95行支撑默认兼容、双端覆盖、离线保留本机和只读约束；场景与自然设计的业务预期有依据。实际00009-listing-mcp.json以include_hub=true调用，却仍收到本机数组，stdout在测试第31行访问coverage时TypeError。mcp_server.py:71–73未支持include_hub，故首个失败是产品真实缺失。

前轮确定错误已修复：第35行读取来源顶层id，符合HubDocuments.sources契约；第42–44行分别取得MCP/API默认完整名单，第54、57行逐完整结果比较离线返回，能拦截非空但残缺名单。第52–57行同时核两端覆盖、空Hub和原因。旧project-scope第780–788行继续核API/MCP完整项目ID名单。源打开guard覆盖全段并保留最终原文件检查。

仍有两个具体漏观测，不能冻结后直接授整项expected_failure：

- 第45–46行才保存Hub快照和请求marker，已晚于第27–44行所有首次在线列表。第61–64行仅重新调用两个MCP，不含在线API。若API第40行先同步正文再给正确名单和coverage，快照会把同步结果当作基线，离线正常回退、后续MCP保持只读即可全过。这违反场景已写“不隐式扫描或同步”；移动已有观察范围即可拦截，无需添加等价样例。
- B7明确禁止只读工具“隐式选择上传”。若工具只改本机许可而尚未外发，Hub snapshot、网络route及源打开guard均不观察本机local_document_sync的enabled/generation，当前断言仍可全过。应在任何列表前记录本机选择，操作后核其保持；无需约束所有内部元数据完全不变。

最早修订环节为implementation：把副作用观察起点移到所有列表之前，覆盖API/MCP在线及离线，核本机上传选择和Hub状态，之后在未改产品上重新取红灯。本次第32–66行均未实际执行，静态核查不认领其通过。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-listing-coverage-review-v4.json`。

## SC12：同窗冲突被合并的可信预期失败

SPEC B6第85–87行规定同身份版本的冲突片段/摘要不得混合，应报告候选错误及覆盖；B7规定精确引用读取。设计、匹配和完整测试符合这些条款。既有test_hub_documents_contracts.py:889–893摘要冲突检查仍保留，本TC补正文冲突。

00005-api-005证明正常发布，00006-api-006提供本机独立原文 `conflictnonce actual local original`、version1及[0,35)。注入只改真实Hub响应的text，保留origin/version/双摘要/长度/精确引用。00007-api-007及00008-snippet-conflict实际返回35个x、combined、两引用、Hub complete和空candidate_failures，stdout第89行准确拦截。document_search.py:169–195只校验形状和元信息，第239–257行未比重叠正文即覆盖为Hub候选，与证据相符。

已逐项核对首失败后可执行路径：第90行partial及候选错误、第91行单引用、第92行按独立原文/范围/LF公式准确read；第二轮[5,35)的30个x形状合法，第89行可拦截仅修同窗；第93行恢复真实request，第94–96行要求正常combined、双引用及独立原文，拦截一律排除Hub。未见后续字段或夹具错误。等价文件/ID增样属于可选补测。

本次仅实际到达equal-window第89行。partial诊断、单引用、read、partial-overlap及恢复正常合并均未到达；expected_failure只认可真实红灯及可执行设计，不认领后续执行通过，必须由同版绿灯实际跑完并独立复审。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-snippet-conflict-review-v4.json`。

本轮仅写两份本轮意见与本报告，没有认领完整007、平台、人工或后续绿灯通过。
