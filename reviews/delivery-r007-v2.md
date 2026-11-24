# R007 当前完整需求独立交付判定 v2

结论：**blocked**。当前版本尚有必测证据和测试断言缺口；没有独立确认当前产品仍违反必测判据。历史 F8 产品失败已取得有效修复闭环，不把它延续为当前失败。此结论只针对完整 R007，不是沿用旧 35 TC 的交付判断。

## 身份、范围与规则

- 项目：`/private/tmp/smm-007`；验收：`AT-SMM-007`；独立 Reviewer：`/root/delivery_007_judgment_v2`。
- 范围：完整且仅 `R007`，16 场景、36 TC（28 自动、8 人工）。SC6 新增“未配置 Hub”的动作前状态，未删除旧检查。
- 定义：`.acceptance/native-v1/AT-SMM-007/definitions/000007.json`，实际重算 SHA-256 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。
- 当前 SPEC SHA-256：`590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`。
- 产品候选：`b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da`；实际 `src/smm_local/document_search.py` SHA-256 `79eb9dd928a45e75aecbaf190aef8c7a4d522020cd797bb5d44e9837efc31360`。
- 结果快照：`.acceptance-local/native-v1/AT-SMM-007/work/delivery-r007-v2-view.json`，本次读回 SHA-256 `ac7ddd60e07df908b4f3fecd0eb8535f3b894ef11461393f36d10fc0fcae6be8`。

已阅读 AGENTS、007 intent/spec/plan、`reviews/authorization.md`、`reviews/project-library-authorization.md`，以及验收 Skill 的执行、结果与 Reviewer 需求级规则。规则要求全部必测有有效证据才可 passed；当前正式必测产品失败才判 failed；尚未确认失败而必要条件不能排除时判 blocked。SPEC A9 原文要求 E1 三格及 E2 当前同版独立包与业务通过，明确“缺任一必需环境不判需求passed”。PLAN 亦不允许因缺环境缩减 SPEC。

原授权仅 007、隔离合成材料，不发布、不升级日常安装、不连接真实用户文档/日常 Hub/VibeInsight。后续停止补跑与禁止 ESXi 的约束有效，但没有变更已确认的验收范围。

## 当前正式证据核对

独立读取 28 份当前正式 execute/manual 收据，逐份核定义摘要；逐字节重算其 **2,883 项 bindings、5,840 项 artifacts 引用，共 5,950 个唯一文件，未发现不一致**。这证明本次引用的证据绑定完整；业务执行覆盖继续按对应独立执行意见和实际分配认领，不能由文件完整性自动推出需求通过。

当前结果为 **28 passed、7 not_executed、1 insufficient_evidence**。28 passed 仅由 **26 自动项 + `TC-007-user-discovery` + `TC-007-regression-ci`** 组成，不是 28 自动通过。SC9、SC10、SC11 为 `not_fully_validated`，其余 13 场景为 passed。以下均按当前结果，不把历史旧版本绿灯套到新候选。

| 场景 | 已有当前实测与独立执行意见 | 当前范围结论 |
|---|---|---|
| SC1 | policy-choice；默认关闭、项目授权、稳定 KEY/HID/G、共享资格与持久选择；真实旧页由用户发现另证 | passed |
| SC2 | sync-publication / retry / boundaries；完整发布、暂存、重试和真实边界 | passed |
| SC3 | paused-lifecycle / overlap-publication；暂停、失效撤回及重叠来源 | passed |
| SC4 | origin-identity / ordering-concurrency / recovery-controls；身份、并发顺序和保护/恢复 | passed |
| SC5 | hub-native / project-scope；原生采集及直接一层项目范围 | passed |
| SC6 | search-candidates / fallback / unconfigured-hub-root；召回排序、已配置故障及无配置状态 | passed |
| SC7 | read-exact / read-rejection；准确引用及拒绝边界 | passed |
| SC8 | compatibility / packages / user-discovery / regression-ci；按四项各自分配 | passed |
| SC9 | 旧 E1/E2 局部原件仍保留；当前五完整平台/服务项未执行，跨机一项证据不足 | 未完整验证 |
| SC10 | library-ingest / project-ownership 当前正式通过；library-update 准备需修订，当前未正式执行 | 未完整验证 |
| SC11 | listing-coverage 准备需修订，当前未正式执行 | 未完整验证 |
| SC12 | snippet-conflict | passed |
| SC13 | cli-scan-boundary | passed |
| SC14 | web-review-feedback | passed |
| SC15 | hub-retained-state / hub-status-provenance | passed |
| SC16 | folder-guidance | passed |

当前正式复审入口为 `reviews/current-formal-review-v2.md`、`reviews/current-user-discovery-review-v4.md`、`reviews/current-regression-ci-review-v2.md`。它们分别只认各自的检查，不替代完整实际平台。

独立解析当前四份 JUnit 原件，核得：本机完整回归 341 项 = 340 通过、1 跳过；三系统所记 CI 各 341 项，macOS/Ubuntu 为 335 通过、6 跳过，Windows 为 336 通过、5 跳过；均零 failure/error。相关 SHA 与门禁独立报告一致。五浏览器格在 CI 因无 Playwright 跳过，Unix 另跳 Windows 专属项；本机对应浏览器格实际通过。完整回归和普通 CI 仍不能替代 E1/E2 的真实入口、指定服务身份和跨机器条件。门禁通过只适用于所记候选及同树 PR merge checkout；后续最终 PR head 仍须完成其适用门禁。

当前包分项与独立报告记录 v5 的 18 命令、Local 30 / Hub 31 模块源码→wheel→安装摘要一致、Hub 无 Local 发行包依赖。包正确不等于三平台完整业务已跑完。

## F8 已关闭，不作为当前失败

独立查阅红灯 v2、绿灯、当前正式意见，旧失败 `expected_failure` → 同测试绿灯 `passed` → 当前正式 CLI/API/MCP × 两根六格 `passed`。当前六格检查分配为 `unconfigured-hub-root-3`。两个独立本机文档及普通/显式 local 的正确结果、引用原文仍有各自独立断言。

实际 `document_search.py:121` 在显式 Hub 根时设置空精确范围；`:212` 起在无 Hub 配置状态记录 unavailable 与原因；`:233–238` 的早退结果保留 `hub_coverage` 与 `reason`。旧 245c236 到 b7ed 的该产品文件 diff 确为这两个返回值变化。当前实现和正式六格支持此状态下不猜同号本机范围，普通本机行为保持。

门禁收据 `product_version` 尾句 `product245c236 bytes unchanged` 是过时说明，不能覆盖实际进程、当前绑定和 CI head；原收据保留，独立门禁报告及公开索引已明确更正。本次使用实际候选与字节摘要。没有把旧失败、测试准备错误或跳过扩成当前产品失败。

## 阻塞一：两项自动检查尚未完成当前正式验收

`reviews/current-design-review-v3.md` 对 28 自动 TC 为 26 passed、2 implementation needs_revision。它们虽然调试 exit 0，仍未被放行正式执行。

1. **`TC-007-library-update` / `library-update-2`。** SPEC B2/B3/B8/A10 及设计要求两份资料在允许/暂停前状态逐份同步或保留。`tests/test_hub_documents_contracts.py:1281–1289` 初始 Hub 命中直接变成按 ID 的字典，更新后只遍历实际命中并验数量 2。假设第二份漏失而首份重复两次，每次正文与首份相符、len 仍为 2，旧字典还折叠重复，现有断言可能全过。因而不能排除部分资料丢失；应独立核初始与更新后的两份文档身份全集、唯一性及各自原文。当前实际数据正确属于局部观察，不等于断言已保证全集。
2. **`TC-007-listing-coverage` / `listing-coverage-1`。** SPEC B6 默认本机列表承诺适用于已有无文档项目与新增有文档项目。`tests/test_document_review_contracts.py:33–62` 默认仅验 list 类型，在线主要验新增 p 成员或 coverage，离线预期又取自未独立核全的默认响应。若 Existing before Hub 在默认、在线和离线都漏失，可两边同错通过；不能排除正常无文档项目在列表消失。应从独立档案全项目取得 expected，再分别核各公共列表。不同准备前状态的 SC5 不能代替本项。

两项是测试实现缺口，尚无产品失败实测。完整 pytest 通过不会增加其中缺失的断言。额外修订轮待维护者决定，本次没有修改测试或继续运行。

## 阻塞二：三平台 E1 的入口与停启证据

SPEC A9/E1 及 PLAN E1 第 2、5 步明确要求真实 CLI/Web/stdio 与新进程读取。当前 `e1-macos-1`、`e1-linux-2`、`e1-windows-3` 无有效完整当前证据，旧运行随产品换版留作历史，当前 v5 尚未完整重跑。

独立读 `reviews/macos-protocol-recheck-v4.md`、`reviews/e1-ci-manual-review-v1.md` 和冻结 `work/runner-snapshots/mac-v16/hub_documents_platform.py:1719` 起：stdio 对 A/B 四份资料 read；私有/Hub 自有在 all 搜索集合中，但未调用 read_document。`:2133` 起顺序为 stdio → 两端 Web → lifecycle；生命周期停启后有 CLI/API 原文，缺新进程 Web/stdio 原文。两个前景平台专项原件复审也指出同样漏项。

这不是额外要求“每入口×每生命周期状态”。实际遗漏的是 PLAN 已明写的入口与停启动作。入口路由/stdio 序列化、新进程连接及引用状态可能改变结果；旧正确 search 片段、其他入口 read 或当前用户发现分项均不能排除。Mac 历史完整 passed 已被补审纠正，已有普通身份、CLI/Web、已调用 stdio 及生命周期局部仍保留。额外 E1 轮待答复，本次不补跑。

## 阻塞三：实际服务 E2 的网页持久与清理证据

`reviews/services-manual-review-v1.md` 旧执行有真实 Ubuntu user-systemd 与 Windows SCM LocalService 身份、网页两份正文及更新/删除、外部 native 采集、普通 Local 获准同步和 PID/端口清理。它们不当作当前 v5 完整验收。

独立检查冻结 `work/runner-snapshots/service-465d27e/hub_documents_platform.py:1666–1744`，停启后遍历的是 native `d_entries + e_entries`；没有剩余网页文档在原新建项目下的查询与旧有效 ref 读取。网页管理副本、来源资格与服务账户文件访问在重启时可能不同于外部采集缓存，native 成功不能推出网页持久成功。

Windows 旧清理证据还缺删服务与防火墙规则后“不存在”的实际查询；发出 delete、进程/监听关闭不等于服务与规则均不存在。这是清理证据不足，未确认清理失败。对应 `e2-linux-service-5`、`e2-windows-service-6` 当前未执行。

用户已明确选择“保留缺口，先完成其他验收”，因此不应用补证草稿、不再重跑；停止动作的授权没有豁免 SPEC。

## 阻塞四：不同 OS、不同机器的 E2 未执行

直接读取 `work/manual-evidence/cross-machine-resource-v1/resource-observation.json`：实际业务 `not executed`；用户禁止家庭 ESXi Windows/Linux，替代资源回答“暂时没有，先继续本机与 CI”，被排除主机未访问。

因此 `e2-cross-machine-4` 只有资源不足观察，没有不同 OS 两台真实机器的认证 HTTPS、远程 Hub 浏览器新建上传更新、另一端项目检索/精确原文、换版与断线恢复及通道清理。物理网络/TLS、远程浏览器来源和机器身份可能改变结果；同机逻辑档案、同宿主普通 Local + SCM/systemd 或普通 CI 均不能排除。资源不足不代表产品失败，仍触发 A9 的交付阻塞。

## 实测、推论与交付边界

本次直接实证为当前记录/字节绑定、测试源码与冻结脚本结构、四份 JUnit 计数、资源原观察及已登记独立意见；未重新运行产品、测试、浏览器或服务。当前 26 自动和 2 人工的已验证分配保持有效。

未通过的两项自动断言和平台条件描述的是会改变结果的可行情况，属于缺测试/缺证据，不能当作已经观察的产品缺陷。共同 Python/SQLite 实现、普通回归或当前正确样本不足以排除这些差异，尤其 SPEC 明确要求实际平台。不能据此推论全 R007 passed，也没有依据判当前 failed。

公开 `evidence/README.md`、`acceptance-index.json`、`public-manifest.json` 区分当前与历史，当前清单实际为 57 文件，定义/候选身份一致；本次核对了其元数据与当前计数，没有把公开摘要或 integrity passed 当成交付通过。

唯一原生意见已先写入并立即通知主 Agent 登记：

`/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/delivery-r007-v2.json`

JSON 严格仅 `status` 与 `reason`，状态 `blocked`。本报告为需求级理由补充，不代替主 Agent 的 delivery-judge 原生登记。本次只写该 JSON 与本报告，未修改其他文件，未执行服务、ESXi、日常 Hub 或 GitHub 写入。
