# F8 同版绿灯独立复审 v1

结论：**passed，仅限 `TC-007-unconfigured-hub-root` 的本次 TDD 绿灯与附带回归。** 已确认的 F8 在当前两个字段修复后消除；原 v2 红灯、v1 不足意见及全部原件保留。本报告不认定 R007、E1/E2 或整体验收通过，现有平台协议及重启缺证、E1 额外轮待答复状态保持。

独立 Reviewer：`/root/review_007_f8_green_v1`；项目 `/private/tmp/smm-007`；验收 `AT-SMM-007`。实际读取 AGENTS、007 SPEC/PLAN、PR39 review-v3 F8、SC6 设计、v2 红灯意见及验收技能的 TDD/Reviewer 规则。产品、测试和原件只读，只写指定 JSON 与本报告；未重跑业务测试、操作服务、ESXi、日常档案或 GitHub。

## 目标及版本绑定

- 唯一目标：`green-unconfigured-hub-root-f8-v1`，result SHA256 `cecdbe1a152bbfe3cf8206490bdbc68cf65069a83e8c81e02c31c7b0122783e4`，与完整 handoff 相符。
- 定义 `.acceptance/native-v1/AT-SMM-007/definitions/000007.json`，SHA256 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。
- 设计 `design-sc6-f8-v1`，收据 SHA256 `e56194f73f06edfe6960f8493e05edb0a14fe7ea4ea46971136b1f01ec8c417c`；承接已登记 `review-red-unconfigured-hub-root-f8-v2` 的 expected_failure。
- 绿灯的 90 artifacts、100 bindings、45 产品及 5 测试绑定现场逐项重算均相符。`runtime-f8-green-v1` 的 100 bindings 与绿灯完全相同，2 smoke 原双流摘要正确，导入探测 exit0。
- 5 个测试绑定与 v2 红灯逐值一致，两个收据下的冻结测试源副本也逐字节一致。主测试 SHA256 `579020c02420f5612f23c70895dd6c44ca36fbdfa4dd8bc86300c85d0ae207f4`；原 `test_hub_documents_contracts.py` 仍为 `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77`。

意见 JSON 已先写并通知主 Agent 登记：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-unconfigured-hub-root-f8-v1.json`。仅含本 TC，`covers=[]`。

## 原始需求、断言与修复范围

SPEC B6 要求 Hub 根不可解析/Hub 不可用时不猜同号本机范围、明确未覆盖，并区分合法零命中与不可用。普通无 Hub 与显式 local 保留 006 语义。A6 要求逐适用结果核身份，B1/B7 要求只用采集档案、按搜索 reference 准确读取；本次无配置前状态、两个不同正文目标及逐引用验证有原始依据，未引入规格外行为。

相对 v2 红灯，45 个产品绑定只有 `src/smm_local/document_search.py` 改变：旧 SHA256 `4f3e58f93f0681ba2739b805a5f66dc080ab64e7dd3fe91440054986a4737c85`，新 SHA256 `79eb9dd928a45e75aecbaf190aef8c7a4d522020cd797bb5d44e9837efc31360`。实际读取 Git HEAD 对应旧摘要原文并作 diff，仅 standalone 早退的两值变化：`coverage.hub` 从固定 not_requested 改用已计算的 hub_coverage，fallback_reason 从固定 None 改用 reason。

无配置显式 Hub 根的 `options.exact_project_ids=[]` 没有改变，212–214 行已算出的 unavailable/原因经早退保留。正常与 explicitLocal 仍由初值 not_requested/None 返回；224 行早退位置不变，006 词法排序不进入联合候选重排。

`tests/test_unconfigured_hub_documents.py:25–33` 以各自文件路径核独立创建 ID、独立字面正文及没有 Hub 配置。97–105 行对 normal/explicit 分别核数量、完整 ID 集、各份正文，并真实提交每个 hit.reference 读取，核 ID/正文/[start,end)；`Fixture.read:95–97` 不用 ID 绕过引用。106–113 行核顺序引用及正常 not_requested/无原因。123–127 行核空范围、不可用与原因、无网络/源打开和完整文档状态保持。

推演反例的第一拦截：只首目标在98行，重复首目标冒充全集在99行，任一观察面的第二正文错在102行，两边第二 reference 同错指向第一份在104行。只第一 Hub 根正确时第二参数格仍在123/125行拦截。与已配置断线旧 TC 并存，未以一个动作前状态替代另一个；新增等价标识样例不是本次阻断。

## 六格实际执行与副作用

红绿命令逐项相同：

```text
/private/tmp/smm-007/.venv/bin/python -m pytest -q tests/test_unconfigured_hub_documents.py::test_unconfigured_hub_root
```

本次执行 receipt 为 exit0，原 `run.stdout` 为 `6 passed, 1 warning in 1.14s`，stderr 为空。目标目录均位于 `.acceptance-local/native-v1/AT-SMM-007/tdd-green/green-unconfigured-hub-root-f8-v1/`。

| 原始根响应附件 | 公共入口 | 同号本机项目 | 逐个核实的结果 |
|---|---|---:|---|
| 00014-unconfigured-root.json | CLI | 1 | 空结果/空有效范围，local complete，hub unavailable，原因保留 |
| 00028-unconfigured-root.json | API | 1 | 同上 |
| 00039-unconfigured-root.json | MCP | 1 | 同上 |
| 00053-unconfigured-root.json | CLI | 2 | 同上 |
| 00067-unconfigured-root.json | API | 2 | 同上 |
| 00078-unconfigured-root.json | MCP | 2 | 同上 |

每份明确原因为 `未连接Hub，无法确定Hub根项目范围`，`results`、`effective_projects`、`effective_project_ids` 都为空。每格分别从两个 files 原件核独立路径/ID，四个实际 HTTP read 原件共24份逐个为200，ID 对应各份独立正文 `needle local private 0/1`，范围均 `[0,22)`；每个 normal/explicit 观察面都各读两份。

CLI/API 普通和 explicitLocal 原查询均核两份完整 ID/正文、not_requested/None，以及两边 reference 顺序。MCP 普通查询通过真实 `server.call_tool`，测试并未另导出这两次查询本体；其执行由同版逐项断言、实际六格全通过、对应四份真实 HTTP read 原件共同支持。根 MCP 响应有单独原件；这些是进程内公共工具测试，不能作为真实 stdio 平台验收。

原红灯在125行停止，本次六格全通过使126/127行均实际完成：`_request` 记录并拒绝守卫、两份源文件 builtins/io/os.open 守卫均零尝试；操作前后 `document_state` 的 document_sources、document_source_projects、documents、document_memberships、document_meta 和 FTS 完整行值相同。没有把仅安装守卫等同于后置断言已通过。

## 附带回归与独立包补证

本次回归 receipt 的 argv 与 request 相同：三个既有文件 `test_document_search.py`、`test_document_sync_recovery_scope.py`、`test_document_review_contracts.py`，以及原 `test_search_fallback`、`test_search_candidates`。原 regression.stdout 为 `14 passed, 1 warning in 4.26s`，stderr 空，exit0；原双流 SHA 与目标绑定一致。它验证既有词法/准确读取、范围恢复和联合候选/回退；不将此14项称为完整 pytest 或三系统门禁。

只读补核 `/private/tmp/smm-007-installed-candidate-v5`：18个真实 build/独立环境安装/入口命令均 exit0，commands 与 result 一致，36份原双流 SHA 全相符。两份 wheel 整体 SHA 匹配。按 build_packages 的 vendor 规则重算当前源码，Local30、Hub31个模块/HTML分别与 wheel 内容、独立安装文件、installed-modules 输出逐项一致；Hub `_archive` 的共享复制和 shim 替换也实际重算。

当前 document_search.py 的新 SHA 与两个字段已进入 Local wheel 和安装；Hub wheel 不含 smm_local 命名空间，独立安装探针实际检查 `find_spec('smm_local') is None`。Hub31模块与其映射源码保持相符。Local wheel SHA 为 `6b4f21c082db98ca2aeaf1c69a3a1884ec7c31ce7b003f42d73c75ff1897db3c`，Hub wheel SHA 为 `f5b984b661616c5677feda9c8265c0eecd952a349cd0ff505a4bcb42c6cf7bd2`。

本报告只提供 F8 同版 TDD 绿灯及明确列出的回归/包补证。平台协议/重启缺证、物理跨机器与服务 E2、E1额外轮待答复仍按既有记录处理，不由本次两个字段修复或包探针冒认完成。
