# AT-SMM-007 新增缺口红灯独立复审 v3

独立 Reviewer：`/root/review_007_gap_red_v3`。按 `work/review-gap-red-v5-handoff.json` 只读复核两个目标，逐份原生意见写入指定 review-inbox 后立即通知根 Agent 登记。两项均为 `expected_failure`；这不表示后续未到达断言已执行通过，也不表示完整007交付通过。

## 基线、版本与真实证据

实际读取交付验收技能、development、Reviewer及自然设计边界检查，项目AGENTS/CLAUDE、SPEC B6/B7、PLAN、定义000004/000005、design-sc11/sc12-v1、match-sc11/sc12-v4、冻结测试和辅助夹具、相关产品代码、前两轮意见及本轮两份stdout/原始附件。没有执行业务测试、修改产品或冻结测试。

定义000005实算SHA为 `176e4c3412612ac48b72d65458d81bd67b66246fa28877e3166ba39f20814419`，需求与原十个场景逐项等于000004，仅增加SC11/SC12。SPEC实算SHA为 `590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`，符合冻结来源。两个设计结果摘要符合红灯目标引用。冻结主测试SHA为 `060f6b0bf82b5e16854d240c06a945e3717b4bc0e5e57b81efdfca0747aa244a`。

两目标全部artifacts/bindings逐文件实算一致：列表18/50，片段17/50；stderr均为空，stdout均为真实exit=1。独立判断依据具体业务失败与原件，不以退出码直接推定预期失败。

| 场景 / 实际TC | 目标result.json SHA-256 | 意见 |
|---|---|---|
| SC11 / TC-007-listing-coverage | `4e7369581f1bc31b1e5ba2d9f05c4eb113d46287f3777abcfac532b9d25f3731` | expected_failure |
| SC12 / TC-007-snippet-conflict | `f560acf1a3255518d343cebbd3ffa66c838f42c272346303f2a9659f0e8904c9` | expected_failure |

## SC11：前轮副作用缺口已落实，产品红灯可信

SPEC B6第79、87行与B7第95行支撑默认兼容、两端名单/覆盖、离线保留及只读约束。场景与自然设计预期有依据，未增加行为。原件00007/00008证明默认MCP本机数组，00009明确请求include_hub=true却仍返回本机来源数组；stdout在测试第36行访问coverage发生TypeError。mcp_server.py:71–73只有hub参数并返回单端数组，确为SPEC已有契约缺失。

已核对修订后的实际断言：

- 第40行按Hub来源顶层id核身份，符合HubDocuments.sources:163–192。
- 第47–49行分别保存MCP默认来源、MCP默认项目、API默认项目，第59/62行完整比较断网返回，能拦截非空但缺失/错误名单。第57–62行另检查两端覆盖、空Hub及缺失原因。旧project-scope:780–788仍对API/MCP项目完整集合提供独立预期，本补项未替代该检查。
- 第25–29行在首次列表调用前读取settings、local_upload*、upload_message*、local_document*、document*全部SQL行、Hub文档/项目快照及网络marker。第31行source-open guard一直覆盖到第68行最后在线API。第71–73行核零打开、本机相关状态及Hub完整快照不变，并核首次至最后调用的Hub路由只能为/info、/projects、/documents/sources。第67–70行同时重试在线MCP和API。

按原文推演前轮漏过的反例：若第45行API首次在线列表先同步正文，再返回正确名单和coverage，即使第50行局部快照把结果当成基线，最初基线的第72行或全段路由第73行仍会失败；如果工具只在本机保存上传许可而不外发，第72行local_state完整比较会失败；若隐式打开当前源文件，guard保留attempts，第71行失败。上述是已有动作/数据上的必要观察，现已落实。默认关闭状态覆盖隐式开启授权；额外更换等价文件或ID属于可选补测，未发现有原文依据、会改变本补项预期且现有断言仍放过的阻塞分支。

本次实际只运行到第36行；第37–75行的项目/API双端列表、离线比较和副作用终态未到达。静态可执行性结论不能代替同版绿灯实际运行。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-listing-coverage-review-v5.json`。

## SC12：异文误合并红灯可信，冲突和正常反例齐备

SPEC B6:85、87及B7:91、93规定冲突不混合、覆盖报错及精确读取。场景/设计未增加行为；既有search-candidates:889–893摘要冲突检查及838–866正常候选完整身份/去重检查仍保留。

原件00005-api-005显示published=1；00006-api-006中可信本机正文为独立字符串 `conflictnonce actual local original`，version1、[0,35)。注入只改真实Hub响应正文，保持origin/version/双摘要/text_length/精确引用。00007-api-007及00008-snippet-conflict返回35个x、combined、双引用，Hub覆盖complete且candidate_failures为空；stdout在测试第98行失败。document_search.py:169–195只校验形状及元信息，239–257核摘要后直接合并并以Hub候选覆盖，未比重叠正文，和真实原件相符。

继续静态核查：若只修完整同窗，第二轮[5,35)的30个x仍与本机[0,35)重叠且异文，会被第98行拦截；只保本机但漏partial/候选错误由第99行拦截；错误保留远端引用由第100行拦截。第101行真实read并按独立原文、码点范围、LF行号核对，防止两边同错。第102行恢复循环前保存的真实request，不递归；第103–105行要求正常combined、双精确来源且read准确原文，能拦截一律丢弃Hub或错误拒绝正常候选。未发现后续字段、范围或夹具错误。额外等价文件/ID样例为可选。

本次仅实际到equal-window第98行。partial诊断、单引用、read、partial-overlap及恢复正常合并均未到达；本轮不认领这些路径执行通过，须同版绿灯实际完成并独立复审。

原生意见：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-snippet-conflict-review-v5.json`。

本轮只写上述两份原生JSON及本报告，保留前轮需修订与原始失败历史。没有认领平台、人工、全量回归或最终需求通过。
