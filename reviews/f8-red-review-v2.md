# F8 新用例红灯与候选设计独立复审 v2

结论：**expected_failure**。SC6 新增无 Hub 配置的动作前状态有 B6/A6 原始依据，设计与 v2 实现有效；v1 两处正控缺口已补齐。正式六格都在覆盖状态业务断言失败，确认现有 F8 缺失。此结论仅适用于 `TC-007-unconfigured-hub-root`，不代表其他用例、R007、平台或整体验收通过。

独立 Reviewer：`/root/review_007_f8_red_v2`；项目 `/private/tmp/smm-007`；验收 `AT-SMM-007`。实际打开 AGENTS、007 SPEC/PLAN、PR39 review-v3 F8，以及验收技能的 TDD、Reviewer、设计边界规则。产品、测试及原件只读，仅写本轮指定 JSON 与本报告；未执行产品测试、Windows/ESXi/服务、日常档案或 GitHub 写操作。

## 目标与完整性

- 唯一目标：`red-unconfigured-hub-root-f8-v2`，result SHA256 `2868eadb9964f6385be7408beddcb87e2bec443133a24a224398831ddb7cc3c9`。
- 定义：`.acceptance/native-v1/AT-SMM-007/definitions/000007.json`，SHA256 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`；仍为 16 场景，SPEC 当前字节与 SC6 冻结来源摘要一致。
- 设计 `design-sc6-f8-v1`；匹配 `match-sc6-f8-v2`。与 `design-sc6-final-v2` 逐值比较，原 `TC-007-search-candidates`、`TC-007-search-fallback` 及旧 obligations 全保留。本轮只判新 TC，未重新判旧项。
- v2 新测试 SHA256 `579020c02420f5612f23c70895dd6c44ca36fbdfa4dd8bc86300c85d0ae207f4`；原 `test_hub_documents_contracts.py` 冻结 SHA256 `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77` 未变。
- 45 产品绑定、5 测试绑定及 87 artifacts 现场逐项重算均一致；v2 产品绑定与 v1 完全相同，尚未修复产品。

意见文件：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-unconfigured-hub-root-f8-v2.json`。只含唯一 TC，TDD `covers=[]`；JSON 先写并通知主 Agent 后写本报告。辅助函数位置为 `tests/document_helpers.py:95–97`。

## 场景与设计

SPEC B6 要求 Hub 根无法解析/Hub 不可用时不把数字 ID 当作本机 ID、不猜范围、明确未覆盖，并区分正常零命中与不可用。普通无 Hub 查询及显式 local 保持 006 语义。B1 要求检索/读取只使用采集档案，B7 要求按搜索 reference 准确读回。A6 的逐适用结果身份检查及 PLAN 的独立夹具预期支撑本次两个不同目标与逐引用核查。

原 TC 的已配置 Hub 断线与本 TC 的没有连接配置，是会改变产品早退分支及预期说明的不同动作前状态。新 TC 覆盖 CLI/API/MCP、两个合法正整数 Hub 根及同号本机负控，普通/显式 local 正控、范围为空、不可用与原因、网络/源打开守卫及完整文档状态保持。场景未增加规格外行为，设计未漏掉本轮有依据的业务差异。不以继续增加相同条件的等价标识作为阻断。

## 实现与反例核查

`tests/test_unconfigured_hub_documents.py:25–31` 分别创建两份独立正文，用各自文件路径核 files 响应身份，建立 ID→独立字面正文预期；第33行独立核无 Hub 配置。第97–105行对 normal 和 explicit 两个观察面分别核结果数量、ID 全集、每份正文，并通过该搜索结果的 reference 实际 HTTP read，核该 ID、正文及 `[0,len(original))`。`Fixture.read` 第95–97行实际提交 `hit.reference`，没有以 hit.id 绕开引用。第106–108行仍保留两边引用顺序比较，第109–113行分别核 `not_requested` 且无原因。

按实际断言推演，并用本轮 CLI 原件的内存副本执行第96–113行原 AST，得到以下首拦截位置。正常见证先通过；不修改测试、产品或原件，不将内存断言验证冒称新的产品业务运行。

| 合理错误 | 首个拦截位置 | 原因 |
|---|---|---|
| 只返回首个本机目标 | 第98行 | 数量小于独立预期全集 |
| 重复首个目标冒充两个 | 第99行 | ID 集合缺第二份独立创建身份 |
| 保留第二目标身份但正文错 | 第102行 | 每份正文与独立预期不等 |
| explicit 第二份正文错 | 第102行 explicit 循环 | 已分别核两个观察面，v1 漏洞关闭 |
| 两边第二份 reference 均误用第一份 | 第104行 | 真正 read 返回第一份 ID/正文，不等第二目标，v1 两边同错漏洞关闭 |
| 只第一个远端根正确 | 第二根参数格第123或125行 | 泄露结果/范围先由123拦，错误状态/无原因由125拦 |

第33行确认没有配置，不会误将已有已配置断线的状态当新覆盖。normal/explicit 若误报不可用或原因，第111–112行拦截。两个同号本机项目都有真实可检索正文，负控不依赖空档案。

网络 `_request` 守卫在第36–40行记录并拒绝；源打开守卫在第93行安装，覆盖两份原文件的 builtins.open、io.open、os.open。第126行核两类尝试为空。第91/127行通过 `document_state` 比较五张本机文档表及 FTS 的完整行值。

## 原始红灯及到达边界

正式命令 `.venv/bin/python -m pytest -q tests/test_unconfigured_hub_documents.py::test_unconfigured_hub_root`，退出1，stderr 空。`run.stdout` 中 `[0-cli]`、`[0-api]`、`[0-mcp]`、`[1-cli]`、`[1-api]`、`[1-mcp]` 六格均先完成正控与逐引用读取，后在第125行发生 `not_requested != unavailable` 业务失败；不是依“6 failed”总数推断。

原件 `00014/00028/00039/00053/00067/00078-unconfigured-root.json` 逐个显示 `results=[]`、`effective_projects=[]`、`coverage.local=complete`、`coverage.hub=not_requested`、`fallback_reason=null`。CLI 原响应退出0、API 请求200；六格各4份 read 原件（共24份）均200，分别对应两份独立 ID、不同正文及 0..22 范围。MCP 查询经真实 `server.call_tool`，正常正控的执行由后续到达的业务断言及逐引用 read 原件共同支持，不冒称本轮实际 stdio 平台验收。

源码 `src/smm_local/document_search.py:212–214` 先设“未连接Hub，无法确定Hub根项目范围”及 unavailable，第224–240行无配置早退又覆盖成 not_requested/None，与 F8 完全一致。没有导入、环境、配置夹具或协议错误，故授予预期失败。

红灯在第125行停止，第126行最终零尝试断言及第127行完整状态比较未执行；本轮不能认领这两项已通过。守卫本身已在操作前安装且运行期间未异常，是已到达的有限证据。后续修复应沿冻结测试与命令获取同版绿灯并完成这些后置检查。v1 needs_revision 报告、意见和原件保持，不被 v2 覆写。
