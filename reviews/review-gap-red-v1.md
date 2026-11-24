# AT-SMM-007 新增缺口红灯独立复审 v1

独立 Reviewer：`/root/review_007_gap_red_v1`。采用 `work/review-gap-red-v2-handoff.json` 两个目标；逐项意见已分别写入交接指定 review-inbox 并通知主 Agent，本 Reviewer 不代登记。结论为列表测试 `needs_revision`、片段冲突 `expected_failure`，不是两个测试全部通过。

## 基线、版本与证据核验

实际读取验收技能 SKILL、development、reviewer、自然设计边界检查，以及项目 AGENTS/CLAUDE、SPEC B6/B7原文、当前定义、两个自然设计/匹配收据、冻结测试与辅助夹具、相关真实产品源码和两次原始stdout/附件。参考 `reviews/green-review-v3.md` 的最早设计遗漏说明，重新从原文和断言判断。

定义000005实算SHA为 `176e4c3412612ac48b72d65458d81bd67b66246fa28877e3166ba39f20814419`；旧000004的十个场景对象逐一与000005相同，新增SC11/SC12，不以新增场景替换旧检查。交接所述总范围29项，本轮只复审新增两个TC。

两个目标全部artifacts和bindings逐文件重算一致；产品及测试当前文件均匹配红灯绑定。主测试 `tests/test_document_review_contracts.py` SHA为 `2d43c4e30e94b18b665ff688a62b2c4be8071322dbbf82038c467d1cac6ea8fd`。两个原stderr为空，stdout各为1 failed，均实际exit=1；不把该退出码本身当业务证据。

| 场景/实际用例 | 目标result.json SHA-256 | 意见 |
|---|---|---|
| SC11 / TC-007-listing-coverage | `4a3d3ab03a5f845ed804f94de8706772adb3ee820463e9d069fbc14626a40206` | needs_revision / implementation |
| SC12 / TC-007-snippet-conflict | `f283aace062a948f2920191b75b917f5f19fe42e15ee54300c94a253146b97d3` | expected_failure |

## SC11：首个产品红灯可信，后续测试必须修订

SPEC B6第79行及B7第95行要求默认本机兼容、明确include_hub返回两端及覆盖；只读工具不隐式选择上传/扫描/同步正文。design-sc11-v1的预期可从这些条文推出。当前真实MCP请求include_hub=true仍返回本机来源数组，附件00009-listing-mcp.json与stdout第31行的TypeError一致；mcp_server.py:71–73确实缺少include_hub参数。不是环境或夹具未建立。

继续检查首个失败之后发现确定测试错误：第35行读Hub来源行顶层source_id，而HubDocuments.sources在src/smm_hub/documents.py:163–192返回顶层id、origin.source_id。修复产品列表契约后这里会KeyError；不能冻结这版测试直接进入实现，也不能把首个失败授为整项expected_failure。

另有已写设计预期未被实际断言充分落实：第48/51行断网分支只检查local非空，错误或残缺的非空名单仍可通过，应核对本次正确来源/完整本机项目集合；第26/53行只保护单源正文打开，没有检测隐式同步正文/改变上传选择的副作用，且当前来源项目同步默认关闭。旧test_project_scope:780–788保留了API/MCP在线项目名单及默认名单检查，故这些旧检查仍有去向；本新增用例第39–40行只核API coverage，不能单独支撑名单完整性。

以上最早需修订测试实现以落实已写设计预期。保留当前真实业务缺失及证据，在产品未修改时修正字段和护栏后另取红灯。项目列表/API、断网两个MCP/API及最终无源读取断言在本次都未到达。

意见原件：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-listing-coverage-review-v2.json`。

## SC12：同窗异文被错误合并的真实预期失败

SPEC B6第85–87行要求相同身份版本的不一致片段/摘要不混合，并作为候选错误反映覆盖。自然设计对应正常同步、只改远端候选正文且保持摘要、同窗/部分重叠，以及恢复后的正常合并。旧test_hub_documents_contracts.py:889–893摘要冲突检查仍保留；本TC补其没有覆盖的正文差异，不替代旧TC。

实际原件00005-api-005确有发布，00006-api-006的Local hit为独立原文 `conflictnonce actual local original`、version1、[0,35)。00007-api-007及00008-snippet-conflict中同origin/version/双SHA的正文变为35个x，却成为combined并保留两个origin_references，Hub coverage仍complete、candidate_failures为空。stdout在第77行失败，符合真实产品缺失。源码document_search.py:169–185验证形状与签名路由元信息，239–257只核摘要后就合并覆盖，没有比较重叠正文，与原件相符。

第一个失败后逐条静态核对：第二轮把start改为5、text改成30个x，仍是与Local [0,35)重叠且长度合法的候选；只修同窗而漏掉该状态会在第77行再次失败。保本机但漏partial/候选错误会被第78行拦截，错误保留远端资格会被第79行拦截，第80行用独立original_text及码点/行号公式验证读取。第81行恢复保存的真实request，不存在递归补丁；第82–84行要求正常combined、两引用及独立原文read，能拦截“一律丢弃Hub”的假修复。未见这些路径的静态字段或夹具错误。

本次实际仅运行equal-window到第77行；partial-overlap、partial诊断/单引用/read、恢复后的正常合并都未到达。expected_failure认可真实红灯和可执行测试设计，不授这些后续路径执行通过，须由同版绿灯真实跑完后独立复审。

意见原件：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-snippet-conflict-review-v2.json`。

本轮没有执行业务测试、修改产品或修改冻结测试，仅写本轮两个意见JSON和本报告。没有认领平台、人工、完整007交付或旧绿灯范围之外的通过。
