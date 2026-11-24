# AT-SMM-007 SC8 最终设计与调试独立复审 v3

结论：本轮两个自动 TC 均 **passed**，分别只认领 `compatibility-1` 与 `packages-2-build`。原包用例分配缺口已通过设计拆分关闭；新增完整回归/三系统 CI 门禁的设计及人工步骤承接充分，但本轮未执行该人工项。用户发现人工项亦未执行。本报告不是正式执行、R007 或整体交付通过结论。

Reviewer：`/root/review_007_sc8_final_v3`。工作根 `/private/tmp/smm-007`。实际读取验收 SKILL 及 design、implementation、reviewer 规则、AGENTS、007 intent/spec/plan、`reviews/final-design-review-v2.md`、原 v2 设计及唯一意见、v3 设计/匹配/运行准备/调试原件。本轮仅核验已有材料，未重跑产品、访问 GitHub/ESXi/日常系统或登记意见；只写本轮唯一 JSON 和本报告。唯一 JSON 完成后已立即通知主 Agent 登记。

## 冻结范围与版本

交接为 `.acceptance-local/native-v1/AT-SMM-007/work/sc8-final-v3-handoff.json`。实际目标为 `debug-sc8-final-v3`，operation `debug`，`result.json` SHA-256：`fb8b796bc345eb08cec0d5222e1138db060f3460164f3daf7da770a4f6a4532c`。定义 `definitions/000007.json` SHA-256：`d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。

实际设计 `design-sc8-final-v3` SHA-256：`e5edf2b6015282f3f1925d51c47aece8014947d384acf4009b0c234978c2c944`；实际有效匹配是 `match-sc8-final-v3-a`，不是先前被阻塞的 `match-sc8-final-v3`。后者因 inspected files 缺来源被工具拒绝，历史保留，不作为已匹配依据。有效匹配四项 source 的完整 SHA、first/last/text 均与当前源逐字相符；debug 只执行 compatibility/packages 两项。JSON 恰含两项，covers 与目标 case_obligations 全等，不含两个 manual。

当前 104 项 bindings 全部重算匹配；目标 144 项 artifacts 全部存在且重算相符，包含两 TC 原始 stdout/stderr/process、附件、源码副本及请求。实际产品源仍为 `245c236ddc41057cd78694902283574d1175e309` 对应内容；HEAD `873b500dcd93062eaa0cdab6c7c332c3fc6bd080` 相对它仅 CI 导出 helper、其自检与文档/报告差异，src、tests、本次 build/packages/checks 探针无差异。未使用的 `hub_documents_ci.py` 不要求绑定到这两个 TC runtime；本次判断以实际 bindings 为准，不能因此把这次调试说成 CI helper 的验收。

## 从原始依据核对拆分

SPEC A8 原文要求：“Local/Hub分别构建安装、Hub不依赖Local发行包；完整pytest及三系统CI通过。”PLAN“执行记录、公开证据与回归”另要求完整 pytest 原输出/JUnit、双包构建独立安装，以及对最终产品与最终证据提交实际通过的三系统 CI。B7 保留旧参数/响应、旧引用、上传选择、Vibe 协议及 MCP 只读；B1 禁止隐式扫描和执行嵌入内容。

原 `design-sc8-final-v2/result.json` 的 packages-2 实际整句为“Local和Hub独立构建安装，全模块源码/wheel/安装摘要一致；Hub无Local发行包或客户端依赖，完整回归及三系统CI通过。”但其自然动作、匹配 source `test_hub_documents_contracts.py:1125–1134` 与子探针只做包构建/安装/入口。反例是两包全正确而完整 pytest 的其他测试失败、任一系统 CI 失败或最终 head 未通过：原 TC 仍可通过。因此旧 `review-debug-sc8-final-v2.json` 的 `needs_revision` / `revision_target: design` 成立，必须保留；那不是产品失败，也不能靠另一份回归日志自动补成旧分配已覆盖。

v3 的去向如下：

| 原义务 | v3 验证项 | 本轮状态 |
|---|---|---|
| 独立构建/安装、完整模块源→wheel→安装摘要、Hub 无 Local 依赖 | 原 TC-007-packages，packages-2-build | 设计/实现与本次调试通过 |
| 完整回归及三系统 CI | 新 manual TC-007-regression-ci，packages-2-gate | 设计/人工步骤充分；仅匹配，未执行 |
| 旧对话/许可/暂停/ref/Vibe、MCP 只读 | 原 TC-007-compatibility，compatibility-1 | 与 v2 自然设计逐字相同；本次调试通过 |
| 入口发现、旧网页 CAS、凭据/重载及纯文本不执行 | 原 TC-007-user-discovery，user-discovery-3 | 与 v2 自然设计逐字相同；仅匹配，未执行 |

新 gate 精确匹配 `changes/007-hub-document-search/acceptance/ci-gate.md:1–11`。它要求当前候选完整 pytest 真实 argv、退出、双流及独立 JUnit 总数/失败/错误/skip 对账；macOS/Ubuntu/Windows 各实际 job 与每个测试、双包构建、分环境安装步骤和 JUnit 原件；候选 head、产品/测试/工作流字节、run/head 链接及原/公开 SHA；最终 PR head 另核三系统通过。未完成、缺原件或版本不符不能判通过，并明确不能替代 E1/E2 身份、服务和物理跨 OS HTTPS。这完整承接原句，没有增加产品需求，也没有放松最终 head 要求。原 34 TC 身份保留，仅新增一个 manual，清单成为 35 项（27 自动、8 人工）。本轮不判断任何 gate 的实际执行或 CI 当前状态。

## 兼容项的实际依据

`test_compatibility:1067–1121` 用真实 Codex/Claude 两条不同旧会话原文和非空 Vibe 夹具。005 none/only/all × 文档动作前全局暂停 False/True 的每格，先保存两端完整 legacy 表和设置，实际文档 refresh/read/remove 后在 1097–1098 全量比较；1096 核正文未外发。旧会话原 ref 分别在 1099–1100 对独立字面原文判定。

独立无 Hub 档案调用真实三文档 MCP 工具，1104 核精确工具集合，1105–1106 核每个只读/非破坏注解；1109 网络 guard、1110 源打开 guard，1111–1116 核 API/MCP 检索/read 的独立原文、正确列表、完整文档状态/设置及零源打开。CLI 及旧 005/upload/Vibe 回归确实作为子 pytest 执行，非仅 import。

本次 `00029-legacy-dialogue-policy-vibeinsight-regression.json` 保留真实六文件 argv、exit 0、完整 stdout 的 **42 passed** 及空 stderr。外层精确选择器原 stdout 为 **1 passed**，exit 0，37 份附件均核 SHA。没有把这 42 项子回归说成完整 pytest。

反例逐一走断言：只保留 Codex 而破坏 Claude，在 1100 Claude 独立预期首次失败；两 ref 共同返回同错正文也在 1100 失败；某一个 none/only/all 或暂停前置态错误，1097–1098 在对应格失败；API 和 MCP 同错正文被 `assert_text` 的独立原文拦截；只读操作造成状态/设置变更、扫描或联网分别由 1116、源 guard、1109 拦截。已覆盖会改变预期的这些状态后，另换同条件的名称/ID 属可选样本，不是有依据的阻塞缺口。

## 包项的实际依据

`test_packages:1125–1134` 实际调用 `hub_documents_packages.py:23–92`，不运行整套 pytest 或 CI。18 条命令为 build；Local venv/install/installed-modules/project-create/add/refresh/search/read/MCP；Hub venv/install/installed-modules/project-create/add/refresh/search/read。每条完整 argv、exit 0 和 stdout/stderr 原件均已读并重算两流 SHA，与 commands/result 一致。

探针清除 PYTHONPATH/VIRTUAL_ENV，独立工作目录、独立新 venv、实际隔离解释器 `-I -X utf8`。分别构造 Local 30 / Hub 31 个模块和 HTML 的完整独立源码映射，Hub 共享源码按其发行命名空间映射而不是比较两个产品结果。Reviewer 另从当前源重新计算整份两 role 映射，全部等于 expected.json、result 及实际 installed-modules stdout 的映射。wheel 54–56 检查完整成员集合与每份源码字节；65–66 对安装文件逐份核 SHA；67 实际要求 Hub 环境 `find_spec('smm_local') is None`。两端实际 site_root 均位于各自不同新 venv。

本次 wheel SHA：Local `75355e31030ebf1079dce574f48077e7e63cc52cdb2f3c5386eda3a850c3f716`；Hub `36db2a568c7b5a18906f849aa93b510aec667476d39530a39c133d4fdf962d98`。这两值来自本次探针原件，不移用旧版包。

Local/Hub 分别创建项目及纳入各自 `source 中文.txt`，输入是 `packageprobe local😀\nindependent local` 与 `packageprobe hub😀\nindependent hub`。75 核 pending，按明确来源 refresh，再按实际项目搜索并读取本次 hit 的 ref；80 核精确独立原文与 version=1。Local 再核 MCP 文档工具精确集合。实际两原文、来源及文档身份不同，没有把两包共用一个产品结果当预期。

反例逐一走断言：仅首模块正确其余错误，最早在 54 的完整集合或 56 对应模块字节失败；仅首包正确，第二 role 同样独立核验；wheel 正确而安装目录错在 66 失败；两包共同错误不能满足独立源码映射，误取同一目录也不能同时满足不同角色命名空间、实际 `find_spec` 与独立 site_root；Hub 误依赖客户端在 67 及其实际 CLI 业务失败；两端同错正文在 80 各自独立字面预期失败。新环境确保既有安装不能掩盖漏包，pending/refresh 是本包入口明确操作。更换同条件等价文件或增加同类模块样本没有额外原始行为依据，不作为阻塞项。

`package-probe-originals` 原封保存 commands.json、result.json、两 expected.json 和 18 条命令的全部 36 份 stdout/stderr。`conftest.py:49–68` 在 pytest 临时目录清理前 copyfile 逐字复制完整双流，不截断、不改返回、不只复制单 result。旧绿灯缺包原件问题已经关闭。本次包成功仍仅支持 packages-2-build。

运行准备 `runtime-final-v2/smoke.stdout` 的原 SHA 已核，完整输出保留当前 `hub_documents_checks.py` 30 个独立自检结果：双目标正文/范围/行号/版本/摘要/项目/来源/资格/身份、漏项/重复、实际活 PID/监听拒绝及退出后接受，另有 9 项适用回归 passed；其辅助源码绑定与本次一致。自检只支持探针可信性，不代产品平台通过。

## 交付边界

本轮唯一意见是 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc8-final-v3.json`，恰含目标两 TC，均完整认领各自当前 case_obligations。没有将旧 packages-2 的整句转记通过，没有覆盖旧 JSON/失败/意见，没有给 TC-007-regression-ci、TC-007-user-discovery、E1/E2 或整体交付授通过。后续人工执行、正式执行及需求级判定仍须各有同版原件和独立复审。
