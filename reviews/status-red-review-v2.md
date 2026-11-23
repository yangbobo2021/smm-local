# AT-SMM-007 状态补充设计与红灯复审 v2

本轮独立审查三份目标：**两份 expected_failure，一份 needs_revision / implementation**。F5 文件元信息和 F7 两端目录指引已有可信业务红灯；F6 确认暂停后的来源缺状态也实际复现，但该 TC 的恢复状态断言仍有漏检，不能把首个真实失败升级为整个候选有效。没有判 R007、正式平台或交付通过。

## 依据、版本与保留范围

实际阅读 `/Users/boboyang/.agents/skills/app-delivery-acceptance-native/SKILL.md`、development / execution/reviewer / case-preparation/design / implementation；项目 `AGENTS.md`、007 intent/spec/plan、`changes/007-hub-document-search/reviews/project-library-authorization.md`、`reviews/pr39-review-v2.md` 和 `reviews/status-red-review-v1.md`。本轮对产品、测试和冻结原件只读，只写指定三份 JSON 与本报告；不登记、不发 GitHub 消息、不访问 ESXi、日常 Hub/VibeInsight 或用户日常资料，也未重跑业务。

工作根 `/private/tmp/smm-007`，实际 HEAD `c9ffae856160daf9685e81c71cca66887ebfec2f`。`git diff --name-only a44a363bb8a708396c643daeec331f6a83bc9aac -- src tests` 无已跟踪文件变化；本轮测试为新增冻结文件。三份收据每份 51 bindings / 45 product_bindings / 6 test_bindings 全部按当前字节复算匹配，artifacts 分别 39 / 42 / 43 项也全部匹配。没有以 HEAD 标签替代文件摘要。

当前定义 `000007.json` SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。逐对象核对 000006 的 14 场景及 requirements 全部原样保留，新版增加 SC15/16；本轮采用完整旧 31 TC 加三项后的 34 TC（27 自动 / 7 人工）范围，只复审本交接三项，不重新授予旧 31 项通过。SC15 两条判据分别源于 SPEC B2/B5 的列表状态与 B3/B6 的暂停/恢复/共享资格，SC16 源于 B8 目录指引和逐份真实报告、B1 不隐式扫描；没有发现场景自行添加产品承诺。

已实际读取旧 `design-sc15-v1/result.json` 和 v1 红灯冻结 `source/tests/test_document_status_contracts.py`，不是只按旧报告推测：旧同 TC 中第一检查 `hub-status-provenance-1` 留在 `TC-007-hub-status-provenance`，第二检查 `hub-status-provenance-2` 移入独立 `TC-007-hub-retained-state`；design-sc15-v2 分配正确，避免元信息首个失败遮蔽暂停状态。SC16 保持 `TC-007-folder-guidance` 与原检查 ID，并仍分别运行 Local/Hub。原 v1 报告、意见和失败未修改。

| 目标 | 实际目标 SHA | 独立结论 |
|---|---|---|
| red-007-hub-status-provenance-status-v2 | 2240cd20946350f2762add61e76f2ba68078c62a972411274ce9633bc21affb6 | expected_failure |
| red-007-hub-retained-state-status-v2 | 40201a6eb52cdfdd13fc16cfb8584f447169bcb8046ae00b04a97e86393a9d81 | needs_revision / implementation |
| red-007-folder-guidance-status-v2 | 9d1e75d76c5dc82d7c57e0b1dc70444c50676c1ef20def8b25a3c24f13c1e73a | expected_failure |

自然语言设计收据 SHA 分别 `abf2f098edce7214837dd69ed628b9e8c42d4595dc068d633c2bd0ed98c3eebb`（SC15）和 `a8b2f43e586e7d0f2284ea03c7feeafd6a165f0d2e6779db33cdc53032bda210`（SC16）；三个 match-v2 收据各只绑定自己的真实 TC。

## 元信息 TC

设计有效。`tests/test_document_status_contracts.py:26–149` 取得两个设备来源/项目、Hub 双绑定和 Hub 零绑定的独立预期；207–260 按原身份逐份核 SHA、长度、版本、资格、来源、项目及适用采集/接收时间，389 核全集与260唯一性。262–328 的 sources 检查新增全集/唯一性、独立项目、配置 revision、只读和无正文、准确原身份及适用时间，每个来源同时请求 HTTP 和真实 CLI files。只处理首个文件/来源、漏掉 Q 再重复其他行、两端共用同一错误目标，分别被215/216/389、260/265–282、287–290独立预期拦截；不能靠两个产品响应相等通过。329–384 已知样本正反、时区和真实 Python/CLI 打开源文件的自检均在本次首个业务失败前执行。原件 `00027-status-probe-selfcheck.json` 与 `00026-metadata-cli.json` 可核。未见未到达实现的确定测试故障；同条件再换名称属于可选补测。

本次 stdout 为 1 failed。389 调 verify，在211取 `origin` 报 KeyError；附件 `00028-hub-11.json` HTTP 200 和 `00029-metadata-cli.json` exit 0 都实际缺 origin/project_ids/received_at，源码仍直接返回006 files结构，属于 B5 缺失。两端已经取回，但 CLI 独立 verify、逐 sources、最终无副作用断言未到达；这些不能记实际通过。授予可信首个缺失的 expected_failure。

## 保留状态 TC

自然语言设计有效，且 v1 的命中漏集问题已修。416 初始全集/唯一性、441–457 暂停全集/数量/旧 ref/独立正文、483–497 恢复全集/数量/旧 ref/独立正文，能拦只首个目标正确、遗漏 Q 并重复 Hub 行、双方读取同一错误正文。共享段512核 p/q 的稳定 project_key 与允许/暂停状态，522逐项目核不同角色，538核允许资格推进后的独立正文，可拦把双方都视为暂停和冻结旧版本。

**阻塞一：恢复后的资格状态没有断言。** 475–497 只在479核 P 来源 retained_snapshot=False、483–484核所有命中此布尔=False，没有核来源 sync_state/sync_message 或命中 sync_states 恢复为允许。反例是：暂停前与确认暂停完全正确，恢复后全集、旧 ref、正文和 retained_snapshot=False 均正确，但 P 来源仍写 `sync_state=paused` / “暂停保留”，P 命中的 sync_states 也仍 paused。479–497 全过；505再次暂停后旧值重新正确，512–538仍全过。该错误违反 B2/B6 可见状态及本判据/设计明确的“允许/暂停/恢复”，改变的是已暂停再恢复的动作前状态，不是增加等价样本。最上游是 implementation，最少需按稳定项目/来源身份断言恢复后的允许资格，并核状态与保留标志一致，再在原产品重取红灯。

**阻塞二：旧初始来源状态检查的去向仍缺。** 继续读取原冻结 v1 发现其249–253明确逐源断言 `sync_state == (native if hub else allowed)` 与 retained_snapshot=False。v2 元信息的262–328已移除此状态检查；retained-state 的411–416只核初始命中身份，没有接回初始来源全体状态，特别是 Hub native 来源。旧分工中的可独立失败检查无依据漏列，按替换/拆分规则应恢复到保留状态 TC。这是对旧声明的原始位置核对，不是新增场景。发现时间在第二份 JSON 写出并通知之后，因此保留该 JSON 原字节，另即时通知主 Agent，并在本报告补充依据；既有结论仍为 needs_revision / implementation。

共享段还可把独立 origin/id 与原 source/project_key 固定下来作为身份检查强化；不靠此附加建议形成上述阻塞。

本次 stdout 为1 failed，在433取 sync_state 报 KeyError。`00031-api-015.json` 证明 P state=paused、generation=confirmed_generation=2、pending=false；`00032-hub-13.json` HTTP200只显示 ready/“同步投影只读”，缺暂停保留状态。首个真实产品缺失可信；Q 状态、暂停命中/read、Chrome、恢复及共享段均未到达。本候选因上述实际断言缺口不授予整 TC expected_failure。

## 目录指引 TC 与实际图像

设计有效。622–649每次重新滚动、取 box 并见证 target/items；599–618捕获阶段从真实 entry 原型包装目录/子 entry 读取并委托原 API。652–670 自检以 stopImmediatePropagation 阻止进入产品，实际枚举 body.txt 并捕获 createReader/readEntries；671清空后才放行产品。该自检没有算产品通过。server源读取守卫也实际自检后clear；697起取对应端完整文档/FTS/项目状态和 Hub 状态，修复v1仅比较Hub的问题。674–695正确/错误指引自检、706/732逐目录行指引及失败/未处理、735合法文件成功、737唯一库项、746目标ID和754独立原文、716/758目录审计都有实际代码。两端之一错误由参数化对应端拦截；仅纯目录正确而混合目录假成功先由732 guidance拦截；双方误取错误正文由746/754拦截；目录枚举后丢弃由716/758审计拦截。没有发现未到达路径的确定测试故障。若后续合法普通文件采用 entry.file API，可把审计限定目录后代，作为可选健壮性改进，不阻塞本轮。

实际打开本目标 `attachments/local-web-review.png` 和 `hub-web-review.png`：目录行都显示“example-folder：失败 · 无法读取所选文件”，该处没有目录来源或明确 refresh 指引。Local 下方已有“添加文档来源”区，Hub 页底已有 CLI 说明；这是既有替代发现路径，不能替代拖入目录当次的指引。

实际读取两份本次完整 trace ZIP 中 trace.trace：Local 190事件、Hub 211事件；vpug@56 / ejxz@161 是被截断的探针自检目录见证，其后 readEntries 返回 body.txt，audit 为 createReader/readEntries；放行后的 vpug@80 / ejxz@185 才是产品目录 drop，均 inside=true、isDirectory=true。唯一 after 错误分别 vpug@94 / ejxz@197，对应702提示断言。两端 stdout均在702失败，是 B8 业务缺失。703之后方向/无上传/完整状态/审计终验及混合批次/read均未到达，不作已执行通过。真实 Chrome 页面/JS经 route 转 TestClient，只证明局部交互，不证明 E1真实网络/TLS/平台身份。授予可信指引缺失 expected_failure。

## 独立文件交付

每份完成后已立即通知主 Agent 登记；没有等待整批。JSON仅含目标实际 TC，均省略covers。原文件及其SHA：

- `review-red-007-hub-status-provenance-status-v2.json`：`3bbb4388d623e3e7edc91327c88705021fdff585dc73a1403b8427e4d4e125cf`。
- `review-red-007-hub-retained-state-status-v2.json`：`a1c9692a693903717bf6d38e86cad418da09b4241430a5738022874f2cfef68d`。
- `review-red-007-folder-guidance-status-v2.json`：`8f26534a052434b72ff374e1d1624d5fb0b19dba2756afba1ca0924d43040cda`。

三文件位于 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/`。恢复状态 TC 修订后需新请求/新文件/新红灯复审；保留v1和v2意见，不改原件、不把未到达静态检查当运行证据。
