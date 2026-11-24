# PR #39 独立审查 v4

结论：**继续保持 Draft，当前不具备交付通过或合并条件。F8 已关闭；本轮未确认新的产品失败。** 当前仍有两项自动断言不足、三格 E1、两项服务 E2 和真实跨机器 E2 缺证。新增一项较小的维护入口文字/导航问题，不能将其夸大为普通用户无法使用。

## 范围、版本与方法

独立新上下文 Reviewer：`/root/pr39_review_v4`。首先读取 `AGENTS.md` 和 `changes/_templates/pr-review.prompt.md`，按 Prompt 对照 Intent/SPEC/PLAN，回放实际用户、Agent 调用方、Hub 管理者和交付维护者路径，再核规格与证据。范围为 base `83b50fcbbad1f29484aa54104ca0f9e75d0498e3` 到当前 HEAD **`b2784d89504ecc68848c9ae1900298a7655be7b4`** 的完整 PR diff，涵盖产品、测试、打包、使用说明、工作流、验收工具和版本化证据，未将审查缩成 F8 两字段增量。

产品候选仍是 `b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da`；b2784d8 是后续证据、计划记录与完整性校验提交。实际核读 Local 文档库/同步/联合查询/协议、Hub 接收与管理、公共 CLI/API/MCP、两端 HTML、共享包映射及受影响测试；以当前正式/设计/人工独立意见和对应索引核验其适用边界。纯完整性校验、原 JSON/XML 解析和已保存图片查看不属于新的产品执行。本轮仅写本报告，没有修改产品/测试/SPEC、执行产品或平台测试、启动服务、操作 GitHub，亦未访问被排除的 ESXi 或日常资料。

## PLAN 核对

主要实现与 PLAN:15–30 的职责划分一致：纯采集库保持独立；`managed_documents.py` 管理本端字节副本、版本 CAS、submission 和移除墓碑；Local 独立项目选择/保护/任务；Hub 有正文暂存、完整清单原子发布、连续资格和 epoch 恢复；联合查询仅本机重排返回片段并按精确引用读取；两端创建端管理由后端执行；Hub vendoring 和自己的 HTML 进入独立包。`project_control.py` 没有新增改动，现有合并来源迁移及按当前项目重算同步的路径保留。AGENTS/CLAUDE 未被本 PR 修改。

PLAN 后段已说明测试无损 gzip、包原输出保存、SC11–16、真实 Windows 标准身份/SCM、CMS trace 回收、F8 的新增前状态及当前 36 TC、两自动项未放行和平台未完成；没有发现以执行注释偷偷减少 SPEC 的情况。PLAN 早段保留 35 项等历史数量，末尾明确新增过程和现数，不能把早期数字作为当前通过项数。

**仍未完成的 PLAN 步骤不能由记录缺口代替。** PLAN:102 的各入口原文、:105 的停启后 CLI/MCP/Hub/Web 读取、:111–114 的跨机器与服务持久条件、:128 的最终证据提交 CI、:131 的全部必测通过门禁仍有效。用户选择保留服务缺口、暂不使用 ESXi、暂无替代机器，以及额外轮待答复，均没有改变 SPEC A9。现有结论支持继续其他获准工作，不支持合并。

## F1–F8 的关闭核对

| 发现 | 当前实现及证据 | 判断 |
|---|---|---|
| F1 远程请求导致 Hub 扫描外部路径 | `document_api.py:49–65` 只公开来源列表/set/remove，无 HTTP add/refresh；`document_cli.py:53–76` 保留维护者本端明确采集。SC13 当前正式通过 | 关闭 |
| F2 批次错误掩盖后续/逐份结果 | Local `static/index.html:191–205`、Hub `static/index.html:43–50` 逐文件捕获并报告、刷新成功项；SC14 当前双端真实浏览器意见有效 | 关闭 |
| F3 Local 到 Hub 管理跳转 | Local `static/index.html:65,178–180` 有无凭据链接及维护者凭据来源；当前公开 Local 全页 PNG 实际可见该链接，Hub 刷新 PNG 是空壳 | 关闭 |
| F4 实际读取端/出处显示 | `document_search.py:313–354` 返回实际端；两端 `documentProvenance` 显示原身份，Local read 区明确实际端，SC7/14 原件支持同版精确回退 | 关闭 |
| F5 files/sources 元信息 | Hub `documents.py:171–247,272–297` 装饰来源身份、项目、采集/接收时间与快照状态，SC15 当前正式意见逐身份检查 | 关闭 |
| F6 暂停保留状态 | Hub `documents.py:227–268` 按控制状态表达暂停/保留/共享推进，页面显示资格状态；当前 retained-state 正式通过 | 关闭 |
| F7 文件夹拖入指引 | 两端 drop 处理分别说明服务电脑目录/Hub CLI及本机同步路径，不枚举目录；SC16 当前双端正式证据 | 关闭 |
| F8 无配置的显式 Hub 根误报正常空结果 | 下述两字段、六格正负控与当前正式执行共同支持 | 关闭 |

F8 实际产品修复位于 `src/smm_local/document_search.py:236,238`：早退保留已计算的 `hub_coverage` 和 `reason`。`:121–122` 的空精确本机范围、`:212–214` 的 unavailable/原因和 `:224` 的原早退位置保持；普通无连接/显式 local 仍保留原词法排序，不进入联合重排。

已自行核 `tests/test_unconfigured_hub_documents.py`：:18–20 是 CLI/API/MCP × 两个合法正整数根的六格；:25–33 按各自路径取得两份独立 ID/字面正文且确认无配置；:97–105 对 normal、explicit 两观察面分别核完整 ID/数量/正文，再实际提交每个 reference 核 ID/正文/范围；:106–113 核原顺序与正常覆盖；:123–127 核空范围、unavailable/原因、无网络/源打开及完整状态保持。只返回首份、重复首份、第二正文错误、两边第二引用同错指向首份分别会被 :98/:99/:102/:104 拦截，不再沿用红灯 v1 的正控漏洞。

本轮还独立解析公开 `evidence/public/current/f8/{cli,api,mcp}-root-{1,2}.json` 六份实际响应：全部空结果/空有效项目，hub=unavailable，原因均为“未连接Hub，无法确定Hub根项目范围”。红灯 v2、同测试六格绿灯、14 项相关回归及正式 `execute-unconfigured-hub-root-f8-v2` 的意见/版本分开保存。该关闭仅处理原 B6/A6 缺陷，不推出 E1/E2 或全需求通过。

## 从真实主入口回放各角色

Intent 受影响者是跨设备查项目资料的本机使用者与管理 Hub 内容/项目/状态的维护者；实际接口还服务只读 Agent 和复跑维护者。

| 角色与目标 | 起点、当时可见内容及逐步下一跳 | 判断 |
|---|---|---|
| 本机用户：建项目、纳入、命中并读原文 | README:33–59 介绍格式/预览包边界/默认不同步/创建端并链接指南 → TRIAL_GUIDE:84–100 给双包隔离环境、DB/空 Agent 根和本机 Web 文档页 → 页面主导航“文档”、创建项目、项目选择、选择/拖入、逐份结果、检索和读取按钮。外部路径/来源 ID/明确 refresh 在指南:70–78 及表单就地说明 | 必要输入有取得方式。当前公开 Local 全页图可见两份不同文档、逐份成功、对应项目查询及纯文本原文；正常路径可开始与确认 |
| 跨设备用户：连接、明确允许、解释范围/快照 | README:55–59 → 指南:102、118–144 → 既有连接段:240 的 `configure-hub 地址 本机名称 --token-file 路径`；地址/凭据由维护者提供，TLS/信任见部署段:155–170。sync-status 取得稳定 KEY/HID/G → sync-policy → sync。页面显示本机选择、Hub确认、待办与共享暂停边界；查询有本机/Hub根及 local 选择 | 配置操作不是只给一个裸内部路径。当前用户发现两条真实旧页 CAS 与隐私意见通过；正常授权/失败解释可达，F8已关闭。真实跨机器结果仍缺证 |
| Hub 管理者：取得凭据、管理库与外部来源 | README:55 → 指南:102 的 HTTPS地址/纯文本 hub-token 与部署链接；Hub根空壳本身说明从维护者取得文件、仅内存/刷新重选 → 认证后新建项目/选择/拖入/search/read/更新移除。外部目录沿指南:104–116 的同 state-dir project create/list → add → refresh → sources/files → search/read | Hub ID、来源 ID及路径所属电脑明确。后台服务不取得远程扫描入口；投影只读、关联不转移管理权。恢复可由指南:146–148 到 recovery-status/state/recover。指定服务完整持久仍缺证 |
| Agent：发现可用能力、只读搜索、按引用取证 | README:27–32 的 Skill入口 → Skill:58–70 先查真实 schema/版本，再 sources/projects(include_hub) → search_documents → read_document；MCP schema 的三个文档工具与 include_hub/local/hub_project_id 对应 | 安装边界、两端覆盖、互斥根、一层范围和精确 ref 可发现。进程内 MCP 正式项与真实 stdio 用户发现应分别认领，不能以其替代平台 E1 |
| 复跑/交付维护者：独立包、条件、当前原件 | README:59 → scripts/acceptance/README:3–14 的007段，提供 pytest/acceptance依赖、独立包/平台/隐私/工具自检、ESXi限制；尾部:250–280 给workflow模式与trace公钥/解密。TRIAL_GUIDE:150 → PLAN:122 明示公开 evidence 路径 → evidence README/索引/清单/完整性命令 | 复跑条件有可用路径。直接“当前验证状态”导航的小缺口见 C1；不能说证据不存在或整体不可操作 |

页面观察来自已保存图/请求及当前源文件，本轮未重新开浏览器实跑。当前 `TC-007-user-discovery` 的独立意见认领本轮 v5 包、真实 stdio、两端按项目原文、两条旧页 CAS 与隐私四阶段；这些局部观察充分，仍不能补出停启后 Web/stdio 或服务动作。

## 当前审查发现

### E1 [P1，证据不足] 两项自动检查不能排除目标漏失，尚无当前正式通过

`tests/test_hub_documents_contracts.py:1281` 初始 Hub 命中直接折叠为字典，:1286–1289 更新后只遍历实际结果并验 len=2。第二份漏失且第一份重复时，两次正文断言可都正确，旧字典又只剩首份。因此 A3/A10 的允许/暂停前已有两份资料的完整身份集合没有被独立保证。当前样本正确不等于产品已经失败，也不能补出缺少的断言。

`tests/test_document_review_contracts.py:33` 默认项目只验 list，:43 只验新 p 成员，:45–46 在线 API 只验 coverage，:48–49 把未核全的默认输出作 :59/:62 离线预期。已有无文档项目 Existing before Hub 若在三个观察面共同漏失，可两边同错通过；影响 B6/A6/A8 的默认本机列表保留。SC5 另一混合前状态的完整检查有效，但不是该只读列表前状态的独立预期。

建议和通过条件限定为：现有两份 assets 的初始/更新结果各自验 ID 全集与唯一性并逐 ID 读独立正文；现有档案全部项目的独立 expected 分别用于默认/在线/断线的各公共列表。保留既有断言，无需新增等价样本。`current-design-review-v3.md:11–12` 已判这两项 needs_revision，`acceptance-index.json` 当前均 not_executed；额外轮等待维护者决定，本轮不应用草稿、不补跑。影响是无法授予完整验收，不是已确认数据丢失。

### E2 [P1，证据不足] 三格 E1 的已写 stdio 原文和停启入口尚未完成

SPEC:154 和 PLAN:102、105 已明确要求。平台源码 `hub_documents_platform.py:1716–1731` 只对 A/B 四份调用 read_document；:1732–1744 对含私有和 Hub D/E 的全集仅 search。`:2133–2150` 顺序是 stdio、两端 Web、最后 lifecycle；`:2052–2078` 重启后的有效原文检查走 CLI，没有后续 Web/stdio。已读取 Mac 自身五组 mcp 原 JSON，记录分工确实是 sources/projects/search、四份 read、all search、对话 search/read，与缺口一致，不从摘要状态倒推。

旧三平台身份、独立包、CLI/Web、已执行的 stdio 与生命周期原件仍有效；当前 F8 产品模块已换字节，索引正确将旧三格标 current_bindings=false/current not_executed。不能把旧 exit0、当前用户发现、进程内 MCP 或三系统 pytest 等同完整当前 E1。适度补证是获准额外轮后对既有独立正文调用真实 stdio read，并按已写停启步骤读有效 ref/内容，保留新原件及独立复审；不是要求每入口重复每种生命周期状态。本轮等待决定，不能据此要求访问被禁环境。

### E3 [P1，证据不足] 两服务 E2 缺网页资料停启持久；Windows清理只证明已执行部分

SPEC:156、PLAN:112–114 要求服务网页副本、项目原文和实际停启持久。共用 lifecycle `hub_documents_platform.py:2052–2078` 只从 native 外部 D/E 项回读；服务独立报告 `services-manual-review-v1.md` 的 Windows/Ubuntu缺口段对应实际重启后没有保留的网页 dropped 文档按新建项目搜索及原有效 ref 读取。真实 user-systemd UID1001/SCM LocalService S-1-5-19、普通 Local拒读HubDB、此前两份网页原文/更新删除以及 native 停启读取仍是有效局部证据。

Windows `hub_documents_scm_platform.py:418–436` 发 sc delete/netsh delete，但不核 netsh 返回，也没有服务/规则不存在的后验查询。failures=[] 和 PID/端口退出不能证明全部配置已删除；同样不能因此断言真实残留存在。

必要通过条件为同版服务停启后按原网页项目核保留文档与旧有效 ref，并保存 Windows 唯一任务服务/规则不存在的实际查询。维护者已明确“保留缺口，先完成其他验收”，本轮尊重此决定，不应用补证草稿、不重跑、不把停止补证解释为豁免。当前两TC not_executed，历史独立意见为不足。

### E4 [P1，缺获准资源] 真实跨 OS 不同机器 HTTPS 没有业务证据

SPEC:135、156 和 PLAN:111 明确另需物理跨机器。PLAN:143–145 与证据 README:16 记录用户排除 ESXi 且暂无替代机器；当前 `TC-007-e2-cross-machine` 是 resource 观察/insufficient_evidence，没有实际同步、远程网页上传、另一端精确读取、断开/恢复原件。同宿主逻辑档案、普通 CI 或各自服务不能替代。

影响是 A9 无法通过，不是观测到传输错误。后续仅在用户提供获准机器后补既定流程；此时保持 blocked/Draft，不应索取或自行使用已禁资源。

### C1 [P3，文档发现难度] “当前验证状态”直达段仍是旧计数/未来索引说明

README:59 将“当前验证状态”链接到 `scripts/acceptance/README.md#007-项目文档库与hub同步`。实际目的段 :5 仍写“27自动TC、8人工”和“最终公开索引会…”，没有链接已经存在的007 evidence README；相邻006段 :18 则直接链接自己的当前证据。维护者按这条承诺的状态入口只能先看到方法与过时35项数量，需自行继续追踪。

已有可用绕行明确存在：TRIAL_GUIDE:150 的 PLAN链接 → PLAN:122 明示 `changes/007-hub-document-search/evidence/README.md` 路径 → 当前28 passed/7 not_executed/1 insufficient与逐项原件。因此不能说证据整体不可找到、普通使用被阻断，亦不新增产品阻断。建议只在该007段补当前 evidence链接、将当前数量写36（28自动/8人工），保留历史记录。通过条件是 README 的“当前验证状态”下一跳可直接到现有索引，数字与索引一致；这是 B7/A8 维护入口准确性的小修，不要求重设计导航。该文件是当前用户发现收据的四份文档绑定之一；本轮保留缺口并在 PR 列明，没有修改后继续冒称原路径收据仍为当前。后续修订须相应更新路径证据适用性。

## 逐条规格与现有证据

| SPEC | 已可复核部分 | 限定结论/缺口 |
|---|---|---|
| B1 / A1 授权格式 | policy-choice、ingest/ownership及兼容正式项；项目默认off、独立对话许可、受控采集、无隐式源打开 | 自动分项有依据；全部实机仍受 A9限制 |
| B2 / A1 状态选择 | 当前 KEY/HID/G、CAS与控制/竞态；用户发现两条真实旧页原payload/完整状态 | 通过分项有效，不以普通新页代旧页；本轮无新产品失败 |
| B3 / A3 生命周期 | paused-lifecycle、overlap-publication、retained-state正式项及精确旧ref拒绝 | 库更新两份完整身份尚缺断言，E1/E2停启缺证另列 |
| B4 / A2/A4 发布/身份/恢复 | publication/retry/boundaries/origin/ordering/recovery当前正式项；完整清单/摘要/回执/保护/范围不变 | 已执行自动分项通过；实际服务/跨机不能由共同实现替代 |
| B5 / A5 原生来源/项目 | hub-native/project-scope/cli-scan-boundary/provenance当前项，CLI显式采集与投影拒绝 | 用户和维护入口可达；服务网页持久仍不足 |
| B6 / A6 范围排序 | candidates/fallback/F8/snippet当前正式项；两端limit、冻结一层、不同版本与精确引用 | F8关闭；listing-coverage完整列表断言仍不足 |
| B7 / A7/A8 读取兼容/说明 | read-exact/read-rejection/compatibility、v5双包与用户发现；本机旧ref及同版回退 | 正常发现/操作有依据；C1小缺口，真实 stdio/停启矩阵未完成 |
| B8 / A10 网页库与归属 | 双端 ingest/ownership、SC14/16、当前用户发现的选择/拖入、逐项目/ID/read、纯文本及凭据隐私 | 可认相应分项；library-update和实际服务/平台完整条件未满足 |
| A8 完整回归/包/CI | 当前本机341=340pass+1skip；三系统所记 b7ed CI成功，v5 Local30/Hub31映射和独立安装意见 | 只认所记产品。CI五浏览器格因无Playwright跳过，本机与正式浏览器另证；最终PR head CI由主Agent另核 |
| A9 E1/E2 | 大量旧版有效局部原件保留并标版本，真实服务身份有依据 | 六必要平台项未完整；当前整体不通过，不能改为已交付 |

本轮独立重解析四份公开当前 JUnit：每份341项，本机1skip，Mac/Ubuntu各6skip，Windows5skip，均零failure/error；与当前门禁独立报告一致。未查询 GitHub 实时状态，不能将保存的 b7ed CI 宣称为 b2784d8 或本报告提交后最终 HEAD 的通过。

公开校验命令 `.venv/bin/python scripts/acceptance/hub_documents_verify_evidence.py --original-root /private/tmp` 实际退出0：`integrity=passed, public_files=57, case_count=36, passed=28, not_executed=7, insufficient_evidence=1, integrity_does_not_mean_delivery_passed=true`。六份F8原反馈、四份JUnit和两张当前公开PNG另实际打开/解析。完整性只确认字节/索引关联，不替代每份原件业务断言；索引清楚区分当前/历史、26自动正式通过+2人工通过，未把28自动debug exit0说成正式passed。

`reviews/delivery-r007-v2.md` 的完整需求独立结论为 blocked，与上述逐项核查一致。本轮关闭 F8，保留 F1–F7关闭；两自动项和六平台项均按缺证处理，不编造成当前产品失败。只有既定必要项取得有效当前证据与独立结论、最终 HEAD CI实际通过，才可进入 PLAN 的交付/合并门；本报告不授予需求 passed、不合并或发布，也不要求无授权追加复测。
