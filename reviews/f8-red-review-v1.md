# F8 新用例红灯与候选设计独立复审 v1

结论：**needs_revision，revision_target=implementation**。F8 是真实业务缺失，正式红灯有效地复现该缺失；候选实现仍遗漏其自然语言设计明确要求的显式 local 逐目标正文及准确引用检查，须在原产品上修订测试并重取红灯后再实现修复。本意见不判整条 R007、其他 TC 或平台验收通过。

独立 Reviewer：`/root/review_007_f8_red_v1`。项目：`/private/tmp/smm-007`，验收：`AT-SMM-007`。只读产品、测试、原始证据；只写本轮指定 JSON 与本报告。未运行 ESXi、服务、日常档案或 GitHub 写操作，未重新执行产品测试。按验收技能 TDD、Reviewer 与设计边界规则审阅。

## 目标与版本

- 需求：007 SPEC B6、A6；同时核对 B1/B7 对仅采集档案、准确引用的约定，以及 PLAN 原文/集合/状态独立预期约定。
- 设计：`design-sc6-f8-v1`，保留 `TC-007-search-candidates` / `TC-007-search-fallback` 的原检查，新增 `TC-007-unconfigured-hub-root`。
- 匹配：`match-sc6-f8-v1`；本轮仅复审新 TC。
- 红灯：`red-unconfigured-hub-root-f8-v1`，result SHA256 `cd6809af795739432edafcd2539cf3c59558ffc73d88853d923bd24eb7786571`。
- 定义：`.acceptance/native-v1/AT-SMM-007/definitions/000007.json`，SHA256 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。本次沿用定义，未修改 SPEC 或场景。
- 新测试冻结 SHA256：`97921e138890a9c70db941f069dbeeb0d2308e74739f46f1c9d28c8c791df72e`。原 `test_hub_documents_contracts.py` 冻结 SHA256 `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77`，当前匹配；全部产品/测试绑定和 51 份 artifacts 逐项重算无不一致。

正式意见文件：`.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-unconfigured-hub-root-f8-v1.json`，只包含新 TC，TDD covers 为 `[]`。已在完成该 JSON 后通知主 Agent 登记。

## 场景与设计

SPEC B6 要求 Hub 根不可解析或 Hub 不可用时“不把Hub数字ID当作本机ID…明确未覆盖且不返回猜测本机结果”，并区分合法零命中与不可用。既有 TC 覆盖已配置 Hub 的断线等状态；新增无 Hub 配置状态有明确依据。普通独立本机及显式 local 仍须保留本机语义。A6 要求“完整检查每个适用结果的身份、版本、来源”；本次自然语言又明确两份结果/引用与原语义保持。

新设计覆盖三个入口、两份独立本机资料和两个与本机数字 ID 碰撞的合法远端根，明确空结果/空有效范围、unavailable/原因及零网络/源打开和状态保持。场景与自然语言设计有效；缺口发生在实际断言，没有要求扩增等价样例。

## 必需返修

`tests/test_unconfigured_hub_documents.py:92–95` 只比较 `normal.results` 的两份正文；`:96–98` 只比较 `normal` 和 `explicit` 的 reference 数组。没有独立核显式 local 的每份正文，也没有核每份 reference 指向其对应的独立目标。

以下两种合理错误都违反已写设计，且在远端根按设计返回、无副作用的前提下可使当前全部断言通过：

1. `normal` 保持正确，`explicit` 第二目标正文改成另一正文，reference 数组不变。第一个漏过位置是第92行只检查 normal 正文；第96行不会检查 explicit 正文。
2. 两边都把第二目标 reference 改为第一目标 reference，保留 normal 两份正确正文。第96行仍相等，故仅首目标引用正确、第二目标被共同误指不会被拦截。

实际取本轮 `00005-unconfigured-cli.json` 与 `00006-unconfigured-cli.json` 原输出的内存副本，分别施加上述错误，走与第92–115行相同的结果断言，两反例均通过。仅将内存中的远端根响应设为设计已要求的 unavailable 和原因，以免已知 F8 遮蔽设计漏洞；这不是产品执行证据，不改原件、测试或产品。

最小返修是保留两个目标与原顺序比较，在 normal/explicit 两个观察面分别核独立夹具全集、每份正文与引用对应目标。逐引用读回并比对应独立原文可区分误指，但还需防漏掉/重复目标。继续保留既有网络、源打开和状态断言。原设计已足够，无需修改场景或新增样例数量门槛。

## 其他反例与守卫

- 只处理第一个远端根：root_position 两格分别在 CLI/API/MCP 查询，第二格第113行首先拦截非空结果/范围，第115行拦截未覆盖状态或原因错误。
- 借用同号本机结果：两个本机项目都有可命中的独立正文，第113行首先拦截泄露；不是空夹具导致的无效负控。
- 普通独立本机或显式 local 被误标 unavailable：第99–103行分别核两次响应的 not_requested / 无原因。
- 漏掉无配置前状态：第30行 `assert not federation.hub_config(local.db)` 独立确认；该条件不与既有已配置失联状态混同。
- 网络守卫先于查询安装，记录 federation._request 尝试并抛 AssertionError；第116行再核尝试列表为空。源打开守卫覆盖 builtins.open、io.open、os.open，同样先记录再拒绝。
- 第87/117行比较本机五张文档表及 FTS 完整行值。正式红灯在115行提前停止，116和117行没有执行，故本轮不能将其认领为已通过的无副作用证据。

## 正式红灯原件

本轮命令为 `.venv/bin/python -m pytest -q tests/test_unconfigured_hub_documents.py::test_unconfigured_hub_root`，进程退出1、stderr为空。六个参数格全部在第115行 `not_requested != unavailable` 失败；不是仅据“6 failed”总数判断。

原始 `unconfigured-root` 观察 `00008/00016/00021/00029/00037/00042` 分别对应两个根 × CLI/API/MCP，逐个都显示：`results=[]`、`effective_projects=[]`、`coverage.local=complete`、`coverage.hub=not_requested`、`fallback_reason=null`。CLI 原输出退出0，API返回200；对应正控先执行并到达远端根业务检查，无导入、协议解析或前置配置失败。

`src/smm_local/document_search.py:212–214` 设置 unavailable 与“未连接Hub，无法确定Hub根项目范围”，而第224–240行无配置返回再次覆盖成 not_requested / None，与 PR Review v3 的 F8 分析一致。草稿 v1 错误 `isNone` 导致的失败未进入正式冻结测试或原件，本意见没有采用草稿失败。

因此，现有产品缺陷已确认；但技能要求设计/实现不足时给 needs_revision，本轮不授 expected_failure。该结论只阻止以当前候选继续产品修复，不撤销已发现 F8，也不扩大为整需求或平台结果。
