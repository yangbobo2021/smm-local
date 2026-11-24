# 获准额外一轮两项测试的独立设计、实现与调试复审

项目：`/private/tmp/smm-007`；验收：`AT-SMM-007`。本轮仅审交接 `work/approved-tests-v1-handoff.json` 指定的两个 debug 收据，不修改产品/测试、不运行测试、不操作 E1/E2、ESXi 或 GitHub。

| 场景 / TC | 独立结论 | 覆盖认领 | 最上游修订阶段 |
|---|---|---|---|
| SC10 / TC-007-library-update | passed | library-update-2 | 无 |
| SC11 / TC-007-listing-coverage | needs_revision；本轮为测试故障，非产品缺陷 | 空；业务检查未到达 | implementation |

## 核对材料与版本

实际阅读项目 AGENTS.md、007 intent/spec/plan、acceptance/manual-cases.md、技能 references/case-preparation/design.md 与 execution/reviewer.md；需求原文优先于既有测试范围。实际核当前 definitions/000007.json（SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`）SC10/SC11、两个 approved-v1 match、各自所指 design-sc10-final-v2 / design-sc11-final-v2、冻结实际测试及辅助断言、debug stdout/stderr 和业务附件。

两份目标 result.json 字节 SHA 均与交接一致：library `08385d4b2451fde47c3c23b9799c24e2bdf58cfea52671de190dce8cd2871188`；listing `6ce054cf3b18a43ead1c4c02b4a50d45ba1c3461a0d44dc72619dc09a9ea4f3a`。两项各105份绑定以及318/115份原件的当前文件逐SHA匹配，未发现版本错配。哈希核对只证明审查对象一致，不代替业务判断。

## SC10：场景、设计和实现均可承接本TC义务

`library-update-2` 来自 SPEC B8第118/120行的创建端更新、CAS、幂等、中断、删除/重放及B3的项目同步状态，判据无额外产品要求。自然语言设计明确两端、两份不同正文、另一项目同名负控，以及允许/暂停之前已发布材料，能承接分配义务。

`tests/test_hub_documents_contracts.py:1219-1275` 在两个创建端分别遍历两份独立回执，逐目标核身份/显示名/归属/存储位置/换版与原字节；核重试幂等、异载荷拒绝且完整数据库/管理副本不变；分别只让内容版本或来源revision过期；核相同字节有效ref连续及真实replace后中断保完整版本；逐份删除、旧ref拒绝、独立同名负控不变和移除后重放拒绝。

本轮补丁 `1281-1289` 在允许和暂停两种动作前状态分别核初始及动作后独立原始DocID全集、数量及唯一性，`1291-1292` 按该ID核每份独立原文，`1296-1297` 核删除后的空查询及所有旧ref拒绝。

| 有依据的错误反例 | 实际第一个拦截位置 |
|---|---|
| 创建端仅更新第一份，第二份不更新或存错原字节 | 第二轮1228或1230；若只返回正文错，则1233调用 helper:140 |
| 初始或动作后仅第一份、第二份缺失或重复第一份 | 初始1283；动作后1289 |
| 保留两个正确origin ID，两条ref共同误指第一份 | 第二份1292，经 helper:140与独立original 2 / replacement 2比较失败 |
| 允许时仍旧正文，或暂停时却发送新正文 | 各状态1292，经helper:140失败 |
| 删除漏第二份 | 1296的空查询断言；旧ref仍可读则1297拒绝断言失败 |
| 拒绝操作写坏其他已有材料 | 1232/1236/1246/1267/1275的完整状态比较 |

实际原 stdout 为1 passed；附件中Local/Hub两份独立replacement原文、单字段CAS拒绝、中断拒绝和移除/重放拒绝均存在。`00161/00166` 是允许状态双目标原文→新正文，`00188/00195` 是暂停前双目标→保旧，`00168/00170` 和 `00197/00199` 逐ref实际读回各自正文；`00176/00205` 为空且四份初始旧ref全部400。分配检查全部到达，认可该候选进入后续正式执行；本意见不是正式执行结果。

## SC11：准备SQL错误，业务未执行

场景 `listing-coverage-1` 来自 SPEC B6第79行与B7第95行。自然语言设计已要求默认/显式联合/离线时的完整两端列表、覆盖原因和不扫描/同步；其action夹带另一TC的异文候选文字，不作为本TC覆盖。

原 stdout 的首个错误是 `tests/test_document_review_contracts.py:31`：

```
SELECT id,name,kind,stable_key FROM projects
sqlite3.OperationalError: no such column: stable_key
```

`src/smm_local/core.py:206-208` 的projects表不含此列；公开 `stable_key` 在 `590-597` 从 `hub_local_project_keys.remote_key` 装饰生成。这是测试准备独立预期集合时查询了不存在的数据库列。不是产品列表请求失败，不应登记product_defect或业务预期红灯。附件仅六份add/refresh/info/create/upload准备响应，尚无`listing-mcp`或`listing-side-effects`，第41行以后均无本次动态证据。

静态核新项目全集逻辑：`34-37` 核独立档案集合、数量和每个项目字段，能在首次42行调用时拦截遗漏夹具中已有`Existing before Hub`的首目标实现；两列表/API共同漏同项目仍分别被52/53/56/57拦，离线保留列表共同漏项目被73/77拦。不能用当前退出失败反推这些断言已经执行。

另有来源实现覆盖缺口：16/18行每端只准备一个来源，41/48行只核ID集合、49行只核包含Hub来源、50行只核kind集合，58/72行还复用默认来源输出。原文对适用来源列表作同一承诺，若每端只返回首个来源、其他适用来源漏失，当前单来源输入没有可核的第二适用目标；多个观察面同漏来源仍不能被这些来源断言区分。应把设计中的完整名单要求落实为独立来源预期及各状态完整性/唯一性断言。此为已有设计的实现落实缺口，不要求无依据扩展业务状态，也不要求无限增加等价样本。

来源缺口的阻塞依据需精确限定：SC11原句是“本机默认来源/项目列表保持兼容；明确include_hub时返回两端列表及各自覆盖状态”，直接来源为SPEC B7第95行“list_document_sources默认保留本机列表……include_hub=true取得……两端来源”，PLAN第76行再要求“完整本机名单仍保留”，第48行要求“各适用目标……分别断言，不以只检查第一个文件……代替独立预期”。名单承诺适用于已明确纳入的每个来源，不只当前首条。

这里不是在已区分来源完整性错误后再增加同条件ID：本轮新断言区分的是**项目列表**漏掉旧项目；**来源列表**仍是独立的被承诺对象，Local与Hub各仅一个来源，尚未区分“正常返回全部来源”和“该端永远只返回首来源”。两端分别只有一条不等于同一端有两条；项目多条也不能证明来源多条。因此第一次为每个受检来源列表提供第二个有效来源，是区分尚未覆盖的首目标截断错误所需的最小检查。该错误违反上述原文，现有来源集合、成员和回退相等断言可以全过；无需看到产品分支或实际产品失败才指出这一验证遗漏。已能在同一观察面证明两个目标均正确后，再换ID、添第三个同类来源属于可选，不继续阻塞。也不据此强制新增pending/failed/重叠/设备投影等新来源状态或类型；那些均须另有行为差异依据。

本项最小必要修订范围为：(1)纠正独立预期集合所用SQL，使其符合实际projects与hub_projects关联结构，保留与公开列表对应的独立项目身份/集合检查；(2)在当前已有默认MCP、在线include_hub、离线include_hub三个来源观察面，使每端准备的两个同类适用来源都接受独立身份全集及数量/唯一性检查，沿用完整独立预期而非只比较两响应；(3)保留原无扫描/同步及状态不变检查，并使源打开守卫涵盖本次准备的源路径。无需另加业务状态、接口、TC或更多等价ID。主Agent所示未应用SQL草稿`/private/tmp/smm-007-listing-schema-correction-draft.patch`仅属于第(1)项；这里只核其拟修范围，不把草稿当作已应用或已验证结果。

因此为 `needs_revision / implementation`，covers为空。**本轮SQL测试故障本身已足够得出该结论**；来源遗漏是同一实现复审的静态覆盖边界，不是额外产品缺陷。本次不修复或重跑；本轮失败及原件应保留，不把测试故障升级成产品失败。任何后续修订/执行仍由主Agent按本轮授权用尽的事实处理，不由本意见授予执行授权。

## 已交付原样意见

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-library-update-approved-v1.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-listing-coverage-approved-v1.json`

每份只含目标实际TC，已分别写好后立即通知主Agent登记；登记状态由主Agent读取工具收据决定。
