# PR #39 恢复候选独立审查 v6

**结论：blocked，继续保持 Draft，不具备合并或交付通过条件。** 本轮未确认新的产品违约或用户入口阻断；SQL/四来源守卫及三处origin纠正合理，当前完整回归、所记候选三系统CI和恢复的E1局部原件有效。逐项正式结果/独立意见链与可读完整轨迹缺失，两个指定服务和真实跨机器义务仍未满足。源码、功能回归、用户可发现、正式交付分别判定，不重建33项通过。

## 范围与方法

本次 Reviewer 为 `/root/pr39_recovery_review_v6`，在新上下文实际打开 `AGENTS.md`、`changes/_templates/pr-review.prompt.md` 和 007 的 Intent/SPEC/PLAN。范围为 base `83b50fcbbad1f29484aa54104ca0f9e75d0498e3` 至候选 `5083227897ab9612390a4cbc4997df961dff96d7` 的完整 PR，包括产品、测试、打包、工作流、说明、历史审查和证据；另审本次未提交的恢复增补。不是只审最新 SQL 或三行身份断言。

本轮自行核改动清单、主要源码和公共入口、当前测试断言与恢复材料；同字节的完整产品审查可参考 [v4](pr39-review-v4.md) 和 [v5](pr39-approved-review-v5.md)，但不把其中旧执行或旧独立身份冒认为本次观察。实际 `git diff --quiet b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da 5083227 -- src packaging scripts/build_packages.py README.md TRIAL_GUIDE.md skills/smm-search/SKILL.md` 退出 0，确认这些字节一致。

本轮只读仓库和任务恢复材料、解析 JSON/XML；不执行产品或测试、不启动服务、不访问 GitHub 修改接口、不操作家庭 ESXi、日常 SMM/Hub/VibeInsight 或用户资料；只写本报告。

## PLAN 与当前实现

实现职责与 PLAN 修改位置一致：纯采集库保留 006 扫描与资格逻辑；`managed_documents.py` 保存 SMM 副本、submission、版本 CAS 和移除墓碑；`document_sync.py` 独立控制稳定项目键/HID/generation、正文与控制、持久待办和回执；Hub 独立暂存/原子清单发布、连续资格和 epoch 恢复；联合查询仅在本机重排两端有界片段、沿精确引用读取。后端区分创建端，Hub 远程 API 没有外部路径 add/refresh 路由，CLI 保留本端明确采集。Hub vendor 纯模块并打入自身 HTML，不引入 Local 发行包依赖。

当前源码另核原F1–F8实际修复位置：Hub `document_api.py` 仅有来源set/remove，没有远程扫描；两端网页逐文件捕获失败并继续后续项；Local的Hub管理链接不携带凭据；联合read返回实际端、页面显示原设备/档案/文档；Hub `sources/files` 在同一控制锁中装饰项目、身份、采集/接收时间与暂停资格；两端目录拖入不枚举并给适用创建端指引；无配置显式Hub根在 `document_search.py:212–238` 保留空精确本机范围、unavailable与原因。`test_unconfigured_hub_documents.py` 的两根×CLI/API/MCP六格分别核两独立正文/各ref读取、空Hub范围与无网络/无源打开/状态不变。没有发现这些已修路径在当前候选重新引入旧问题；不据此冒称旧正式证据已恢复。

本轮纠正属于 PLAN 原 SC11 完整名单与 E1 读取义务。末段记录原错误、授权范围、四路径守卫修订及 E1 专用模式；未发现以 PLAN 说明降低 SPEC，亦未修改 AGENTS/CLAUDE。正式逐项验收、E1/E2、最终候选 CI 和独立需求判定仍是门禁，记录未完成不能代替完成。

### SQL、全集与四路径守卫

`tests/test_document_review_contracts.py:32–35` 从真实表结构构造预期：Local 读 `projects(id,name,kind)`，Hub 读 `projects JOIN hub_projects` 并将 `h.kind` 映射为接口 `source`。这与 `core.py` 的项目表、稳定键装饰和 `HubProjects._list` 对应，已消除 v5 的不存在列错误。预期在首次列表前从准备档案独立取得，涵盖已有无文档项目，不再以接口响应作为唯一预期。

`:36–43` 同时核长度、ID 集合及逐项目字段；两端各两来源分别由准备回执构造独立 ID 集合。默认 MCP、在线 MCP/include_hub、Web 项目列表和离线返回分别核全集；长度加集合能拒绝漏第二项、重复第一项和错误 ID，离线名单另先核其基准。`:46` 守卫覆盖 `path,path2,native.path,native2.path`，`:94–96` 核无源打开、两端完整相关状态不变和仅只读路由。守卫实际包装 `builtins.open/io.open/os.open`；读取 SQLite 构造预期没有打开这些源副本。此为静态认可，不生成缺失的调试/正式收据。

`test_hub_documents_contracts.py` 的 library-update 在允许/暂停两前状态中，初始与更新后均核两份独立 origin document ID 全集、数量与唯一性，再按独立正文逐份读取。v4 的两自动断言遗漏在当前代码中已补齐；当前正式执行与独立意见是否可复核另见证据部分。

### 三处 origin 更正

`hub_documents_platform.py:1753,1796,1836` 改核完整 `origin` 与 `version`，没有只删除身份检查；相邻 `exact_read` 仍核独立原字节规范化后的全文、码点与行号，此前 `document_set` 核 search 全集、双摘要与长度，重启 stdio 用原有效 reference，Web 实际点相应结果的读取按钮并核 DOM 文本。

这符合 B6/B7 的身份契约：`document_search.py:241–268` 合并同源同版时保留远端候选对象，`:325–332` 的 bundle 可先读本机精确 part；Hub 内部行 ID 与 Local 行 ID 可以不同，完整 origin/版本才是跨档案身份。三处纠正没有更改产品、来源资格或 E1 必需步骤。旧内部 ID 失败不是已确认误读；代码正确也不等于后续 E1 已实际执行。

## 从主入口回放用户路径

Intent 影响跨电脑检索项目文档的本机使用者和 Hub 维护者；公共接口还服务只读 Agent 与复跑维护者。以下是本轮静态逐跳回放，不称为新浏览器实跑。

| 角色与结果 | 实际入口、当时信息与下一跳 | 判断及边界 |
|---|---|---|
| 本机用户建立项目、纳入、命中并读原文 | README:33–59 介绍受支持格式、预览包边界、默认不同步与创建端 → TRIAL_GUIDE:84–100 给独立双环境、档案及空 Agent 根 → Local Web 主导航“文档”，页面:57–65 依次可新建、选项目、选择/拖入、查看逐份结果、按项目 search/read；外部目录由指南:70–78 和就地表单说明路径属于服务电脑、ID 从来源列表取得、先明确 refresh | 必要信息与操作可发现，可开始并确认正常结果；静态路径不授当前完整人工项通过 |
| 跨设备用户明确允许与解释结果 | README 007 段 → 指南:118–144 → 既有 configure-hub/TLS 段取得维护者地址/凭据；sync-status 取得 KEY/HID/generation → sync-policy → sync。Local 页面:181–186 显示目标、选择/确认/待办并冻结提交值；projects --hub/带端选择器取得 Hub 根 | 许可独立于对话；暂停保留、撤回待确认、共享推进及精确引用说明可达。真实物理跨机结果仍单列缺证 |
| Hub 维护者管理库/来源及恢复 | README:55 → 指南:102–116 链接 TLS/凭据取得；Hub 根匿名空壳本身说明向维护者取得文件、仅内存及刷新重选 → 认证后项目/上传/更新/删除/search/read。外部路径由同 state-dir CLI 的 project create/list→add→refresh→sources/files→search/read；指南:146–148 给 recovery-status/state/recover | HID/epoch/稳定项目状态来自认证信息和列表；投影只读、目录所属电脑及恢复影响明确。指定服务持久证据未由该说明完成 |
| Agent 只读检索与准确引用 | README Skill 安装入口 → Skill:58–70 先核实际 schema/安装版本 → sources/projects(include_hub) → search_documents → read_document。说明 local/Hub 根互斥、一层范围、覆盖及实际读取端 | 三文档工具保持只读，不隐式扫描或授权。进程内 MCP 或局部 stdio 正确不代替完整实机 E1 |
| 交付维护者复跑和复核状态 | README:59“当前验证状态” → scripts/acceptance/README:3–14 现写36项/28自动8人工，直链证据 README，给独立包、依赖、平台、隐私和专用 E1 模式 → 证据导航顶部明确旧索引为历史、直链恢复README → 本轮CI/E1选件、独立意见及blocked登记 | 原 C1 的旧数量与缺直链静态问题已修；本轮主入口已能找到真实恢复状态，未让纠正前SQL失败/旧统计冒充当前状态。静态导航修正不替代完整用户发现人工执行 |

未确认新的产品入口阻断或必要输入缺失。F1–F8 同字节关闭依据仍成立；C1 静态修正与当前完整用户发现执行是两个判断。

## 恢复证据核对

### 常规 CI 与本机回归

实际读本机 `exit.json`：候选 5083227、隔离恢复目录、完整 argv/起止/退出0；JUnit 实数341，340通过、1非Windows平台限定跳过、无 failure/error，与原 stdout 一致。原退出记录未列执行前全源码摘要；执行后101份 src/tests SHA 及无差异检查只按事后测量认领，不倒填成执行前快照。

独立解析恢复的 [CI run45298310517](https://github.com/yangbobo2021/smm-local/actions/runs/45298310517) 元数据/jobs：head 为5083227，三系统 pytest、双包构建、分环境安装步骤均 success；实际 checkout `4f4385709ace965a3b1b1953d1d266ac8e51ee88`，保存的 API 提交及 job 日志对应，树 SHA 与508相同。三份 JUnit 各341项、零 failure/error；macOS/Ubuntu各335通过6跳过，Windows336通过5跳过。五个浏览器参数因普通 test extra 缺 Playwright 跳过，另一个是非Windows不适用的启动等待项；不把普通 CI 说成全部网页/实机覆盖。

四份公开 JUnit 与私有原件自行解析比较，仅去 hostname 属性即 XML 完全一致，原SHA亦核一致。当前产品/测试回归与所记候选普通CI有证据；本报告及恢复说明后续若提交新 head，仍需单独核该最终 head CI，不能把508的运行自动改称新提交已通过。

### 三平台 E1 可读原件

三份 E1 ZIP 已恢复，自行对照 GitHub artifact 元数据核长度、外层SHA及ZIP CRC；再核每件内层 `sha256.json`：Mac115、Ubuntu115、Windows116件均一致。该完整性结论只针对已恢复字节。

[run45297175901](https://github.com/yangbobo2021/smm-local/actions/runs/45297175901) head为8210b25，三job的前景业务步骤 success，两种实际服务步骤均 skipped。8210至508只增列表测试的一行四路径守卫，产品和E1 runner未变。三份 `runner-bindings.json` 的三个SHA均实核等当前；各 `packages/result.json` 的Local30/Hub31映射与当前源码逐件相等（Hub vendor shim按构建替换规则核），且等平台 `*-installation.json` 的实际安装映射。Mac控制器UID501、Windows `is_admin=false` 等身份原件可读；这只是各自托管机的普通前景流程，不是物理跨机器或SCM。

本轮自行解析各OS原 `mcp-5.json`/`mcp-7.json`：10个唯一完整origin/version，逐份 read 与固定合成原件全文、原字节SHA、规范化SHA、长度、码点及LF行号一致；重启stdio各6份、重启Web的Local6份/Hub3份也逐份按独立固定原文核对。不能继续沿用v5“尚未到重启”的旧动态结论：这些新轮原件确实存在。各OS的8个越端伪造管理操作及完整前后状态、两端literal各4阶段与两目标全集、生命周期、源打开审计和清理原件均已可读，清理显示任务进程/端口退出。

另实际打开Mac `restart-web-a.png`/`restart-web-hub.png`、Ubuntu `web-a-mixed-batch.png`、Windows `web-hub-literal-original.png`：可见重启后的结果/实际原文、逐文件成功失败、纯文本显示的script/img内容、创建端与Hub管理入口；与相应JSON一致。本次未逐图重新观察全部动作。九份CMS仅核密文字节及其清单，私钥已丢失，**没有解密或打开原trace**，因此不冒称完整浏览器轨迹已复核。

## 当前审查发现

### E1 [P1，证据缺失] 逐项正式收据与独立意见不能从索引/摘要重建

恢复README明确原临时树和未提交材料缺失，原因未确认；当前Git保留521件JSON实际为7份定义、1份manifest和513份尝试索引，索引指向的私有result尚不可读。原生登记前完整视图能识别定义v7，但16个scenes的cases/history均空、R007为pending_delivery_review；本次新需求独立意见随后真实登记为blocked，见下节。这里的0有效执行说明恢复链断开，不能推断此前没有执行，也不是回归测试失败。

上一轮摘要的“33 passed / 2 not_executed / 1 insufficient_evidence”及四份新独立意见/97件公开选件未恢复，不能据摘要新造通过收据或套用旧Reviewer身份。列表SQL/四源和origin纠正的静态合理性、本机340+1及E1可读业务局部有效，均不能补出这些缺失的逐项正式结果及独立判定；用户发现完整当前路径的单独原件/意见也未恢复。对维护者的实际影响是无法逐TC追溯本候选正式验收，不能认需求passed或合并。

通过条件限于找回真实原件及原独立意见，或在已有授权边界允许时另取明确标新的适用执行与独立判定；不得改写索引冒充原收据。保留新旧身份、失败历史、绑定和时间；本报告不要求未经授权追加轮次。E1的CMS私钥缺失使完整轨迹当前不可打开，须如实保留边界，不能用hash或job success反推浏览器全部动作通过。

### E2 [P1，必要服务证据不足] 用户保留的两服务缺口仍阻塞A9

SPEC:151,156及PLAN服务步骤要求实际Ubuntu user-systemd/Windows SCM LocalService，且网页管理资料停启后仍按原项目命中、沿旧有效ref读取。旧 [services-manual-review-v1](services-manual-review-v1.md) 记录两服务尚缺该网页资料持久证据；Windows还缺唯一任务服务/防火墙规则删除后“不存在”的查询。`hub_documents_scm_platform.py:418–436` 仅发删除命令，netsh返回未核、无后验查询，不能把failures=[]或PID退出当全部配置已删除，也不能反推实际存在残留。

用户明确“保留缺口，先完成其他验收”，本轮不执行服务，E1专用模式也明确跳过它们。旧真实身份、先前网页管理及外部采集原文重启局部证据保留历史；不能因此宣布两服务完整通过。影响是A9与服务持久门禁未满足，未确认新的产品失败。通过条件仍是原网页项目/旧有效ref停启实证及Windows任务配置不存在的实际后验查询；用户停止补证不是SPEC豁免。

### E3 [P1，获准资源缺口] 不同OS真实机器HTTPS尚无实证

SPEC:135,156要求至少一组不同OS不同物理机器的获准正文同步、远程浏览器上传、另一端精确读取、版本更新与断开恢复。当前无获准替代机器，家庭ESXi已排除；各托管job的同机逻辑档案与前景Hub不能替代这组网络/身份边界。影响是A9不能通过，并非观察到跨机产品故障。后续仅在用户给出获准资源时完成既定步骤，本轮不访问禁用环境、不要求以额外机器声明替代业务原件。

## SPEC逐项判断

| 条件 | 当前可确认部分 | 不能推出的结论 |
|---|---|---|
| A1 / B1–B2 | 独立项目默认off、KEY/HID/generation CAS、对话许可分离、状态及旧页保护实现保留；完整回归通过 | 正式逐项收据及当前用户发现人工原件缺失，不能授全项正式通过 |
| A2 / B4 | 暂存/完整清单事务、摘要/长度及幂等实现与对应测试未退化，当前回归零失败 | 普通CI不替代实机/E2或逐项正式判定 |
| A3 / B3 | 暂停/撤回/重叠资格及双资料更新断言保留；新E1生命周期原件可读 | 两服务网页资料持久缺证，不能完整交付 |
| A4 / B4–B5 | 身份/代次/保护恢复与无网络持锁路径当前已核，恢复专门回归仍在 | 不以静态实现或旧正式意见补缺失的新收据 |
| A5 / B5 | Hub本端CLI明确采集，设备投影管理拒绝，项目/来源/文件元数据实现和E1包流程可复核 | E2指定服务完整持久仍不足 |
| A6 / B6 | 有界候选本机BM25、一层精确范围、Hub根失败不猜本机；F8保留覆盖/原因；列表独立全集已补 | 当前正式列表准备/执行意见未恢复；不能再称当前SQL仍失败，也不能称已正式passed |
| A7 / B7 | 精确引用路由、实际读取端与同版part回退保留；三E1原MCP/重启全文可逐份复核 | CMS轨迹未打开、其他正式read负控收据缺失，局部正确不授完整需求passed |
| A8 / B7 | 主使用/维护入口、包边界与必要输入可达；Local/Hub映射各30/31、当前本机完整回归及所记508三系统普通CI有效 | 当前完整用户发现独立收据缺失；后续证据提交head仍须CI实核 |
| A9 | 三前景E1 job成功且大量业务原件已恢复，界定为普通身份同宿主逻辑设备 | 完整独立平台判定链缺失、CMS不可读、两个服务及真实跨机义务未满足 |
| A10 / B8 | 创建端后端边界、上传/更新/移除、越端8请求前后状态、纯文本及逐文件反馈实现和新E1局部原件支持 | 完整人工路径及指定服务持久/原生正式判定仍不能授通过 |

## 冻结恢复增补与新独立判定

收到冻结通知后实读恢复README、主证据导航和PLAN末段；未提交增补如实解释材料缺失、有效回归/E1局部、CMS不可读和E2停止边界。README主入口已经标“历史快照”并直链恢复状态，没有让旧索引的1 passed/4 needs_revision或摘要33 passed冒称当前。PLAN将恢复方法与正式/CI后续门禁一并写明，未改行为或验收条件。

自行对冻结 `recovery-20261124/manifest.json` **32件**逐一重算长度和SHA，全部一致；三份restart派生摘要逐字段等私有原JSON、源SHA亦等，六张公开PNG字节等对应原件。四份JUnit仅去hostname的转换另已核。新 `delivery-r007-reviewer.json` 与登记artifacts SHA相符；`delivery-r007-registration.json` 字节等实际原生delivery-judge的result，judgment为blocked，Reviewer身份为本轮真实 `/root/delivery_007_recovery_v1`。登记前完整view的pending与登记后full view/summary的blocked分别核到，后view SHA与摘要一致；没有把登记前状态误当当前。17个截图checkpoint标明当前恢复态，实际打开两张公开需求/SC9图可见blocked/尚未完成验收，未回填历史画面。

已读 [R007恢复独立报告](delivery-r007-recovery-v1.md)，其完整需求blocked与本次PR审查一致：未确认有效当前必测产品失败，证据不完整，不能passed。完整性32件通过只确认冻结选件的可追溯字节，不代替36TC正式执行或完整浏览器轨迹。

最终PR head在提交本报告/恢复说明后仍须取得实际CI结果；等待新head门禁不是产品失败，也不能被旧508的CI替代。必要服务与跨机器缺口及当前正式证据链完整之前，保持Draft、不合并、不发布、不升级；本报告没有执行或授权额外平台轮次。
