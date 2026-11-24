# PR #39 获准补证候选独立审查 v5

**结论：不合并，保持 Draft。** 当前存在已确认的测试实现故障，完整验收与最终候选门禁未满足；没有据本轮失败确认新的产品违约。当前完整 R007 独立判定为 [blocked](delivery-r007-approved-v1.md)，不能以旧 CI、局部正确原文或公开哈希完整性改判通过。

## 对象、方法与 PLAN

Reviewer：`/root/pr39_approved_review_v5`。先读项目 `AGENTS.md`、当前 PR Review Prompt 及007 Intent/SPEC/PLAN；范围为 base `83b50fcbbad1f29484aa54104ca0f9e75d0498e3` 到 **`ed56f94174ac7513ed52415607e823d26afa9d7e`** 的完整 PR。开始时 HEAD 为 `3eb918c06b873773560361a882b60b6aa986d471`，两测试、说明、索引与原生记录尚暂存；结束前已核其提交为 ed56f94。不是只审最后六行测试补丁。

自行执行 `git diff --quiet b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da -- src packaging scripts/build_packages.py README.md TRIAL_GUIDE.md skills/smm-search/SKILL.md`，退出0：产品、包映射及上述用户说明字节均未变化。因此 [完整审查 v4](pr39-review-v4.md) 的同字节产品核查和 F1–F8 关闭依据可以沿用；本轮另核实际入口、当前改动、关键断言、原始失败输出及三平台完整 MCP 响应，没有重审每份未变化历史附件，也没有把旧证据改称当前正式通过。

实现位置仍符合 PLAN 的采集/管理副本、Local 项目控制、Hub 发布/资格、联合查询及精确引用、创建端管理、独立包分工。本轮探针只补原 E1 stdio/重启义务，两自动断言仍属原 SC10/SC11；C1只修验收入口的数量与链接。PLAN 末段记有授权、实际失败及适用版本变化，未发现未说明的方案偏差、SPEC 减项或 AGENTS/CLAUDE 行为修改。**记录失败不等于完成 PLAN**：正式验收、三格完整 E1、E2及最终 head CI门仍有效。

本轮只执行文件/差异读取、JSON解析和纯证据完整性校验；没有运行 pytest/产品/平台/浏览器，未操作 GitHub、服务、ESXi或日常资料，未应用两个纠正草稿。最终 head CI由主 Agent另核，本报告不授予新执行授权。

## 受影响角色与实际入口

Intent 的目标是本机用户跨设备按项目读文档，以及 Hub 维护者管理来源、项目与状态；公共能力另服务只读 Agent及复跑维护者。下表是本轮沿当前可见文本/源码逐跳核对，**不是声称本轮浏览器完整路径已执行成功**。

| 角色、要做什么 | 主入口及当时可见信息、下一跳与输入取得 | 判断与完成边界 |
|---|---|---|
| 本机用户：建项目、纳入、检索、读原文 | README:33–59介绍格式、未发布包边界、默认不同步、创建端并链接指南 → TRIAL_GUIDE:84–100给双环境/独立DB与空Agent根 → Local Web主导航“文档”，`src/smm_local/static/index.html:57–65`有创建项目、项目选择、文件选择/拖入、外部来源、搜索及读取。路径属于服务电脑，来源ID来自sources，明确refresh后才查外部材料 | 局部输入与下一步充分，可发现并开始。当前完整人工复验止于测试helper，不能授完整 A8/A10路径通过 |
| 跨设备用户：取得连接、允许项目、理解范围和快照 | README007段 → 指南:118–144及既有configure-hub段：地址/凭据由维护者提供；sync-status取得稳定KEY/HID/generation → sync-policy → sync。CLI `src/smm_local/cli.py:145–165`及页面:61、180–186说明暂停保留、待确认、Hub目标、冻结提交值；Hub根从projects --hub/带来源选择器取得 | 未将数字ID、会话许可或仅连接当正文授权。精确ref/实际端说明可达；真实跨机及当前完整生命周期仍缺证 |
| Hub维护者：管理网页库或本端目录、恢复冲突 | README → 指南:102–116链接部署/TLS、纯文本hub-token；Hub根连接页说明取得凭据和刷新重选。认证后创建项目、选择/拖入、按项目search/read、更新移除。外部目录走同state-dir的project create/list → add → refresh → sources/files；恢复走指南:146–148的recovery-status/state/recover | `document_cli.py:7–40,43–90`对应命令与ID来源；Hub页:37–44明确投影只读。`document_api.py:56–86`没有远程add/refresh扫描入口。服务持久与清理的完整证据仍不足 |
| Agent：发现工具、只读检索、引用准确原文 | README Skill入口 → `skills/smm-search/SKILL.md:58–70`：先核实际schema/安装边界 → sources/projects(include_hub) → search_documents → read_document。说明互斥项目根、覆盖、精确引用、实际端及管理分离 | 用户可知不支持时如何判断；三工具只读路径保持。进程内测试或本轮局部stdio原件不能替代完整E1 |
| 交付维护者：复跑并查当前证据 | README:59“当前验证状态” → `scripts/acceptance/README.md:3–14`现写36项/28自动8人工并**直链007当前证据** → evidence README → 逐项索引/原件清单/独立意见。工具段仍列依赖、独立包、平台、隐私与trace条件，指南另可经PLAN绕行 | C1旧计数及缺直链的静态缺口已修；当前状态能直接找到。新人工导航阶段未到达，所以“文档已修”与“完整路径当前通过”分别认定 |

上述入口没有确认新的阻断信息缺失。已有实际画面/导航/CAS属于旧版本收据；本轮隐私四阶段有单独局部意见，均按其版本和范围认领，不拼成新的全路径成功。

## 当前发现与通过条件

### T1 [P1，测试实现故障] listing-coverage 准备失败，候选不能通过既定门禁

`tests/test_document_review_contracts.py:31`新增 `SELECT id,name,kind,stable_key FROM projects`。公开原输出 `evidence/public/approved-round-20261124/listing-debug.stdout` 的首错为 `sqlite3.OperationalError: no such column: stable_key`。`src/smm_local/core.py:206–208,590–597`显示该公开字段由`hub_local_project_keys.remote_key`装饰取得，并非projects列。失败发生在首次列表断言前，故不能判产品列表失败，也不能认新全集断言已执行。当前完整pytest/CI门不能借旧候选绿色成立。

[两测试准备复审](../changes/007-hub-document-search/reviews/approved-two-tests-design-v1.md)另指出来源对象仍每端只有一个适用目标，在线/离线来源预期部分取自未独立核全的默认响应，尚不能区分“每端只返回首来源”。这是既有“完整名单”检查的实现遗漏；**仅SQL故障已足够阻塞该项**，不需再扩样本证明当前产品有错。

建议在新轮获准后按真实schema取得独立项目预期，补原有三个来源观察面的最小独立全集/数量/唯一性与源打开守卫，保留原状态不变检查，再获准备/正式独立意见。无需新增TC、来源状态或等价第三目标。SQL/来源纠正草稿未应用，本轮不修不跑。

### T2 [P1，错误测试预期及缺证] E1与用户路径在内部ID比较提前停止

三平台 `evidence/public/approved-round-20261124/*-e1-failure.json`均定位 `hub_documents_platform.py:1753` 的 `actual["id"] == hit["id"]`。源码 `document_search.py:241–268`合并同origin/版本的两端命中时保留远端候选对象，`:325–332`沿当次bundle精确parts读首个有效端；因此combined命中的Hub内部ID与实际local读取的内部ID可以不同。SPEC B6/B7规定稳定origin、版本、摘要与精确来源，没有规定两档案内部ID相等。

本轮自行解析 Mac/Ubuntu/Windows 各自 `platform/mcp-5.json`及`mcp-7.json`的原始`content[0].text`：每格10个唯一origin命中和10个实际read，逐对完整origin、版本、双摘要、长度及正文均相符；各两份combined→local内部ID不同，且origin.document_id等于实际local ID。这与[本轮独立执行复审](approved-e1-failure-review-v1.md)逐独立原文结论一致。该局部正确性足以排除“ID不同就是误读”的推断；不证明循环后半及后续业务已执行。

`execute:2210`在`:2211–2212`两端Web前抛错，`:2227`生命周期、业务后重启Web/stdio均未到达；本轮无相应画面/trace/业务原件。新增两个重启ID比较位置也未被动态验证。用户发现wrapper同样在shared stdio停止，导航/Web/CAS未到达，四项独立结论均needs_revision/implementation、covers为空。单独隐私四阶段只支持凭据局部事实。

通过条件是获准后按完整origin/版本核身份，保留独立正文/码点/行号/ref路由断言，以冻结新runner取得三个完整E1和用户路径的实际后续证据与独立结论；不能仅删除身份检查或改产品迎合误期。origin纠正草稿尚未应用，本轮不追加执行。

### E1 [P1，必要服务证据不足] E2未证明网页资料停启持久及Windows完整清理

SPEC A9/E2及PLAN服务步骤仍要求Ubuntu实际user-systemd与Windows SCM/LocalService。旧服务的真实身份、网页上传/原文/更新删除、native外部采集资料重启回读及PID/端口清理可沿用为历史局部证据；[服务独立复审](services-manual-review-v1.md)仍缺**网页管理资料**停启后按原项目查询/沿旧有效ref读回。Windows另缺删除唯一任务服务/防火墙规则后“不存在”的实际查询；发出删除命令不等于确认不存在，也不能反推实际有残留。

通过条件限于补上述原有持久和后验清理原件。用户已选择“保留缺口，先完成其他验收”，故不应用服务草稿、不跑E2；停止补证没有豁免SPEC，当前不能合并。

### E2 [P1，获准资源缺口] 不同OS真实机器HTTPS仍未执行

SPEC:135、156与PLAN跨机器步骤要求独立于同机逻辑档案/服务的真实跨OS传输、远程网页上传、精确读取、版本及断开恢复。ESXi被禁止且无替代机器，当前资源项为insufficient_evidence。影响是A9无有效完整证据，不是已观察到传输产品失败。后续仅在获准替代资源存在时完成既定流程，本轮不访问被排除环境。

## SPEC逐项结论与当前证据边界

| 契约 | 本轮可确认的实现/证据 | 尚不能授予的结论 |
|---|---|---|
| B1–B2 / A1 授权、入口和状态 | 产品与v4同字节；默认off、独立文档许可、KEY/HID/G与旧页CAS实现未变，入口可达 | 旧正式与旧用户路径不自动绑定新测试/说明；本轮无全项passed |
| B3 / A3 暂停、撤回及更新 | 本轮library-update新增初始/更新后两文档独立ID全集、数量/唯一性，逐ID原文保留；允许/暂停两前状态均正式exit0且独立passed | 只认library-update-2，不能推到真实生命周期、E1/E2 |
| B4 / A2/A4 发布、身份与恢复 | 同字节实现及旧分项原据仍支持v4关闭边界；本轮MCP身份/版本局部一致 | 新绑定候选的其他正式项未重新完成；局部正确不等于全恢复/并发已验 |
| B5 / A5 Hub自有来源 | 当前CLI/API/网页仍区分本端显式采集和设备投影，状态及恢复说明可达 | 指定服务网页资料持久仍缺证 |
| B6 / A6 范围排序与列表 | F8的unavailable/reason修复保留，精确同源同版合并路径解释本轮ID差异 | listing准备故障、来源全集遗漏；不能称列表本轮passed或产品failed |
| B7 / A7/A8 精确原文、兼容与发现 | 当前三平台共30对MCP响应原origin/版本/正文相符；README/指南/CLI/Skill必要说明可达，C1静态修正 | 未完成当前全路径/完整正式兼容与最终head回归CI门 |
| B8 / A10 创建端网页库 | 产品未变；library更新/CAS/幂等/中断/删除的正式独立意见有效 | 本轮E1未到两端网页管理/伪造拒绝/纯文本DOM；旧画面不补新轮 |
| A9 E1/E2 | 新三格真实普通前景进程已运行并如实保留失败；服务及跨机缺口单列 | 必要三E1与E2未全通过，整项交付blocked |

当前[索引](../changes/007-hub-document-search/evidence/acceptance-index.json)为 **1 passed、4 needs_revision、30 not_executed、1 insufficient_evidence**。library是唯一当前正式passed；listing仍是未获准备放行、未正式执行的项，四个needs_revision为三E1和用户发现。旧26自动+2人工及包/完整回归/所记三系统CI留历史；测试或说明binding改变后的30个not_executed不是30项观测到产品回归，重新match也不是执行。当前新增SQL明确故障，旧绿色不能替代候选门禁。

实际运行纯校验 `.venv/bin/python scripts/acceptance/hub_documents_verify_evidence.py --original-root /private/tmp`，退出0：63公开文件、36TC、上述状态分布，`originals_checked=true`，`integrity_does_not_mean_delivery_passed=true`。它确认公开字节/原SHA/索引收据关联，不能证明缺失业务。F1–F8保持关闭；C1静态内容已修；本轮新增问题属于测试故障与未完成证据。只有修正候选、适用正式证据及所有必需平台/独立判定满足，且最终head CI实际通过，才能进入合并门。
