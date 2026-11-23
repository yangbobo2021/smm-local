# PR #39 独立复审 v2

结论：**仍需修改，继续保持 Draft，不能认定交付通过或合并就绪。** 原 v1 的 F1–F4 在当前产品中已修复，且补充红灯、同测试绿灯和实际画面能支持相应局部结论。本轮另外确认三处已有规格的遗漏：Hub 文件列表缺少出处及接收元信息、远端结果不能区分暂停后保留的快照、文件夹拖入缺少目录来源指引。前两项影响状态解释，后一项影响错误后的操作引导；没有据此声称正文错误、匿名访问或撤回失败。必要正式验收和跨系统实机证据仍单独待补。

## 审查基线与方法

本轮独立上下文 Reviewer：`/root/pr39_review_v2`。实际读取本 worktree 的 `AGENTS.md`、`changes/_templates/pr-review.prompt.md`、007 全部 Intent/SPEC/PLAN、项目文档库授权原话、原 v1 审查、补红/绿审查及当前 diff。先核计划，再沿实际主入口回放角色，最后分别判断功能、发现路径和验收证据。没有因 E2 缺环境而跳过产品检查，也没有把与计划一致等同于需求完成。

实际 `gh pr view 39` 确认 PR 为 OPEN/DRAFT，base 为 `83b50fcbbad1f29484aa54104ca0f9e75d0498e3`，head 为 `f7bb5dcfd9fe6087c8d73fbd618524a949f0c039`。本轮 diff 是该 base 到该 head；产品代码提交为 `a44a363bb8a708396c643daeec331f6a83bc9aac`，后一个提交只补回收说明。没有修改产品、测试、冻结证据或 v1 报告，没有发 GitHub 评论，没有访问 ESXi、日常 Hub、VibeInsight 或真实用户资料。本轮只新增此报告和自己的私有合成复现原件。

## 已确认的新发现

### F5 [P2] Hub 的文件状态入口仍缺少原身份、项目和接收信息

性质：明确未满足 SPEC B5 的 `sources / files`“列出Hub自有及已接收来源/文件并区分身份、状态、资格、采集/接收时间”，也影响 B2 的远端来源状态解释。不是要求增加权限体系。

`src/smm_hub/document_cli.py:48–49` 和 `src/smm_hub/document_api.py:68–70` 直接返回 `documents.documents.files(...)`。该006结构在 `src/smm_local/documents.py:259–265` 只给本档案文档ID、source_id、路径、版本、资格及 captured_at，没有原设备/档案/文档身份、所属项目或 received_at。Hub 的 source 装饰在 `src/smm_hub/documents.py:163–192` 虽补了设备/档案/来源身份和项目，却没有采集/接收时间；接收来源的 finished_at 仍为 null。

独立合成反例同时创建一份设备同步文档和一份 Hub 上传文档，再调用认证 HTTP files/sources、真实 Hub CLI files 和 search。HTTP 与 CLI 文件行均缺上述字段，CLI exit 0；search 的同一设备文档却能返回正确 origin、project_ids 和 received_at，证明数据已经存在，只在文件状态入口遗漏。收到的 Hub 文件ID与原 document_id 也确实不同，不能把前者当作原身份。原件见 `/private/tmp/smm-007-pr39-review-v2/repro-files.{py,stdout,stderr}`。

影响限定：维护者沿指南 `documents sources` → `files --source-id ID` 核对混合资料库时，不能直接核实某份文件的原身份/项目及何时被 Hub 接收。已有 sources 可按 source_id 辅助辨认部分出处/项目，已知正文词时 search 可取得完整命中元信息；因此不称正常检索或读取被阻断，也不要求在列表返回正文。

建议和通过条件：在 Hub 层为 files 装饰出处、项目和适用采集/接收字段，CLI/HTTP共用；sources也提供适用采集/接收状态。以至少一份 Hub 自有及两份不同设备同名文档验证，每行可追溯准确原身份/项目/时间，保留 status/qualification，不能通过路径猜来源；列表仍只读、不打开源文件。

### F6 [P2] 确认暂停后，Hub 来源和命中仍与允许同步时完全相同

性质：B2 明确要求远端来源列表区分保留快照，B6 要求结果及覆盖区分“保留快照/未同步或错误”。本轮反例证明的是可见状态缺失，暂停保留正文的行为本身正确。

`src/smm_hub/documents.py:163–192` 只装饰 origin/read_only/message，未纳入该来源对应 `hub_document_controls.enabled`；search 的 `src/smm_hub/documents.py:705–748` 同样只装饰出处和泛称“Hub采集/接收版本”。两端页面的 provenance/来源渲染因此也没有可显示的暂停保留状态。

独立反例：设备项目发布一份独立正文后暂停并同步确认。原端 sync-status 为 `state=paused`、`enabled=false`、`generation=confirmed_generation=2`、`pending=false`；暂停前后的 Hub sources 数组、search.results 数组逐字段完全相同。来源仍显示 `ready` 和“同步投影只读”，命中没有暂停保留标记。原件 `/private/tmp/smm-007-pr39-review-v2/repro-retained.{py,stdout,stderr}` 保留两个真实状态及响应；不是只据字段名猜测。

影响限定：在另一设备查询或直接维护 Hub 的用户，无法在这条可达路径判断源项目已经停止继续上传，容易把保留副本当成仍在更新的同步源。原端 Local 的项目选择区及 sync-status 已正确显示暂停，是现有补救路径；采集/接收时间也可说明快照年龄，但不能表达已确认暂停。没有要求暂停创建冻结版本分支，仍应保留 B3 的共享文件可由另一连续获准来源推进的规则。

建议和通过条件：按来源/项目资格暴露允许、暂停保留及适用错误状态，在远端来源列表与命中/覆盖上可见。对允许→确认暂停→恢复允许验证状态变化及原文保持；共享文档同时有允许/暂停资格时保留各自状态，不能给整个文件错误加上单一冻结语义。显示只读元信息，不上传未获准文件名单。

### F7 [P3] 两端文件夹拖入只报读取失败，没有引导到明确目录来源

性质：B8“文件夹拖入提示使用明确目录来源”的局部提示遗漏。只影响错误后的引导，不构成目录被意外扫描或正文泄漏。

Local `src/smm_local/static/index.html:207`、Hub `src/smm_hub/static/index.html:70` 的 drop 处理只展开 `dataTransfer.files`，没有识别目录项。实际 Chrome 中通过 CDP 拖入本轮真实合成目录，浏览器见证 `webkitGetAsEntry().isDirectory=true`；两端最终只显示“example-folder：失败 · 无法读取所选文件”。本轮实际打开 `folder-local.png` 和 `folder-hub.png` 核实画面，均没有指向目录来源。

已有路径：Local 同一页下方有“添加文档来源”，指南说明绝对目录及明确 refresh；Hub 页底部也说明外部目录用 CLI。因此整体目录纳入功能可发现，问题限定为拖放失败处没有规格承诺的适用说明。建议在拖放时识别目录并明确未处理，Local 指向本机目录来源，Hub 指向维护者在 Hub 电脑执行的 CLI add/refresh；如实说明同批其他文件的处理结果。通过条件是实际目录拖入出现该指引、目录不被隐式扫描/上传，同批合法文件仍给真实逐份结果。

复现原件 `/private/tmp/smm-007-pr39-review-v2/repro-folder.{py,stdout,stderr}`、`folder-local.png`、`folder-hub.png`。本例运行实际 Chrome 页面/JS，HTTP由 Playwright route 转交真实 app TestClient；它证明此局部交互，**不是 E1 的实际网络/TLS或平台服务身份验收**。

## F1–F4 修复复核

| 原发现 | 当前代码与原件 | 本轮结论 |
|---|---|---|
| F1 HTTP使服务扫描外部路径 | Hub document_api已删除POST sources和refresh；仍保留CLI native add/refresh。SC13原件实际为两个HTTP add拒绝、两个单源及全部refresh拒绝、完整表状态不变/零源打开，以及两个真实CLI refresh后逐份原文正确 | 该缺口已修复；不把此TestClient结果当Windows服务权限证明 |
| F2 混合批次结果 | 两端循环内逐份catch，结束后刷新库并显示名称/结果。SC14原件及Mac v9两张mixed-batch PNG均可见A成功、B严格UTF-8失败、C成功，库行只有A/C且ID对应 | 该缺口已修复；不是要求一切失败都继续，也不把逐份成功展示扩大成整轮E1通过 |
| F3 Local到Hub管理入口 | Local第64行有无凭据管理链接及维护者凭据说明，sync-status只提供Hub地址。SC14真实点击到Hub空壳页，无Authorization；本轮实际打开empty-shell PNG | 该缺口已修复；文档和页面可达路径相互一致 |
| F4 实际读取端/出处 | Local provenance与阅读区显示archive_scope、原设备/档案和适用项目/采集接收。SC14真实native Hub、shared Local、沿同一个旧bundle在Local资格退出后Hub同版回退三个响应；本轮实际打开两张Local原文PNG及Mac v9联合read PNG | 该缺口已修复；三状态不是重搜或替换正文；F5/F6是另两个状态入口遗漏 |

实际重算 SC13/14 两份绿灯的所有 bindings/product_bindings/test_bindings/artifacts，分别为55/45/5/32及55/45/5/88，均与当前文件一致。业务stdout分别1 passed、2 passed，适用四文件回归均19 passed；两份trace分别607/284条记录，没有after动作错误。本轮阅读绑定测试及关键原响应/四张SC14 PNG，不只复述旧Reviewer结论。原红灯v3及绿灯v1报告保留，不覆盖旧意见。

SC11/12旧补充绿灯绑定的是先前产品，当前六个产品文件已变化，不能把其旧bindings称为当前同版。当前final-debug-v1 handoff已经存在：13次自动debug涵盖24个TC，其目标SHA和全部现有bindings/artifacts本轮实算均匹配，包括SC11/12/13/14。本轮只核真实性和适用版本，**没有代发这些debug的逐TC独立passed，也没有认定正式执行/需求判定完成**。

## 从真实主入口回放角色

下表分别引用当时可见的入口内容与下一跳。静态说明、已安装CLI实际帮助、既有实际业务/轨迹及本轮局部反例分别作为对应步骤依据，没有声称本轮重新完整执行所有操作。

| 角色及结果 | 入口发现与下一跳 | 前置输入、动作与确认 | 判断 |
|---|---|---|---|
| 本机用户：建立文档项目并读自己的资料 | README33–59行先介绍能力、支持格式、默认不同步、创建端管理和未发布边界，链接TRIAL_GUIDE84节；指南88–100行给双包独立安装、独立DB、空Agent根及Web入口 | Web主导航“文档”→新建项目→选择库项目→文件选择/拖放→批次报告/库行→按项目search→原文。目录路径旁明确“服务所在电脑”，保存pending后明确refresh；项目/来源ID由列表取得。Mac v9和SC14关键画面支持正常路径与混合批次 | 主路径充分；F7为目录拖入的局部引导缺口，不阻断已知目录来源操作 |
| 跨设备用户：独立选择项目同步并读取准确副本 | README56–59行→指南118–149行→documents父帮助/sync-status/sync-policy；本轮实际运行独立安装包的帮助，包含KEY/HID/G和暂停语义 | KEY/HID/G原样取最新状态；Web按钮闭包绑定当时值。选择先存本机、确认/待办另显示；Hub项目列表/选择器标来源，查询和原文不按另一端同号ID猜测；Local文档页可直接点无凭据Hub链接 | 发现、前置取得与正常完成路径可达。原端暂停状态清楚，但另一端结果的F6仍存在 |
| Hub维护者：管理Hub库/外部路径并核状态 | README55行及指南102–116行→Hub HTTPS根；匿名空壳说明凭据来源；Hub CLI父帮助暴露documents/project及state-dir | 实际选择凭据后新建Hub项目、选择/拖入、按项目search/read、更新/移除；设备投影显示只读。外部路径必须Hub本机CLI add后refresh，state-dir与服务一致；project list、sources取得ID | F1已修复；凭据前置可发现。沿sources→files核接收元信息有F5，确认暂停的Hub可见状态有F6 |
| Agent：以只读工具取文档证据 | README138–148行链接真实Skill；Skill58–74行先核安装schema/版本，再列出sources/projects→search→read及管理分离 | include_hub列表保留Local及coverage；两种项目ID互斥；local/fallback/精确reference/码点和快照边界明确，管理另走Web/CLI。当前MCP只读annotations与三个工具集合有兼容测试/包原件 | 工具发现和参数链充分；源列表也受F5/F6的实际元信息限制。没有把只读解释为禁止既有最小项目登记 |
| 维护/复跑者：独立验证并理解证据边界 | README59行→scripts/acceptance/README.md第3节→SPEC/PLAN/manual-cases；同一文档248–278行能找到workflow、模式、公钥取得与解密校验 | 当前入口给24自动/7人工、完整pytest、acceptance/Chrome条件、独立双包、隔离合成资料、私有原件/双SHA、不得使用ESXi。公钥证书Base64填workflow，私钥留本机；下载后核密文及解密原SHA | 能开始复跑，说明区分能力探测、同机服务与物理跨机器。候选证据页仍陈旧，见下文；完整trace实际回收不能由操作说明代替 |

局部文档准确性备注：`changes/007-hub-document-search/evidence/README.md:7,12,13,15` 仍写327/1、托管CI待提交执行、服务全部待验证及29项/22自动。当前定义000006和主维护入口已是31项/24自动，当前回归330/1，托管Mac/Ubuntu已实际执行。该页诚实声明未交付通过，故没有把旧导航误当虚报成功；但在下一次证据收口时应同步为绑定候选的真实状态，并链接本轮补红绿及后续正式索引，避免维护者漏掉SC13/14。通过条件是从可达证据页得到同一候选、完整数量及准确已执行/待执行边界；不要求伪造未完成平台。

## PLAN 与验收证据

当前实现位置与职责和PLAN基本一致：纯Documents/ManagedDocuments、共享协议与保护、Local同步/联合查询、Hub发布/API/CLI/Web、项目根与创建端边界、独立vendor包、CLI/MCP/后台接入及说明。PLAN末尾记录了无损gzip、包原stdout保留、列表/片段补测、SC13/14、隔离UTF-8探针、标准账户、真实服务及trace加密回收调整。没有看到未说明的范围扩展或AGENTS/CLAUDE行为修改；F5–F7是承诺的可见行为未完整落实，不能只靠PLAN符合消除。

本轮实际读取完整回归stdout/XML：330 passed、1 skipped，XML331项、0失败/0错误、1跳过。独立包result/commands为18条全部exit0；直接映射当前源码的Local30项、Hub14项SHA全部匹配，Mac v9实际安装Local30项/Hub31项也逐字节匹配安装文件。Hub vendor模块映射在包原清单中独立保存，Hub环境不依赖smm_local。包通过只证明对应构建/安装/命令。

Mac v9 result为passed，实际两端混合批次、联合原文PNG已打开；commands、source-open-audit、来源指纹、安装清单、生命周期和cleanup原件可核。源打开审计仅有explicit-refresh及合成conversation-import；cleanup记录8次任务服务进程退出及所有当前端口关闭。该轮为真实普通账户安装包HTTPS/浏览器/stdio候选流程；不冒称物理跨机器或本轮launchd，也不以result一个字段替代未逐条完成的正式人工记录。

| 验收 | 可支持的当前有限结论 | 必须保留的限制 |
|---|---|---|
| A1 | 默认off、独立选择、KEY/HID/G CAS及保存/确认分离有实现、测试与真实旧页材料 | 正式逐项执行及独立需求判定待完成 |
| A2 | 暂存/原子清单、长度/双SHA/16MiB与重试断言已纳入当前自动debug及回归 | 不由整套pytest替代每TC正式原件复审 |
| A3 | 暂停保留、发现失效撤回、共享连续资格/离线/重连有代码与当前调试支持 | F6缺远端保留状态；不称暂停等于撤回或永久冻结 |
| A4 | origin、单调控制/发布、保护/epoch及竞态修复有当前绑定和适用回归 | 本轮未确认新的数据完整性违例；不是证明不存在全部并发问题 |
| A5 | Hub项目/CLI采集及创建端隔离可用，远程外部扫描已禁 | F5；实际服务与物理跨机仍按各自证据判定 |
| A6 | 一层签名范围、限制候选重排、同版合并/异文排除和列表coverage有当前实现与debug | F6；F4显示已修复不代表全部状态已展示 |
| A7 | 逐引用/码点/版本资格校验及旧bundle同版回退有当前测试与SC14三个实际响应 | 没有把别端同名或新版本作回退；正式R007意见仍待 |
| A8 | 330/1、双包18命令/模块SHA、README→指南→CLI/Web/Skill/维护入口可复核 | 候选证据页需更新；最终head三系统CI未全结束 |
| A9 | 当前托管Mac/Ubuntu业务与Ubuntu实际user-systemd工作流已经成功 | Windows仍失败、SCM未到达；物理跨OS实机仍无获准环境；缺任一不判passed |
| A10 | 两端创建、正常上传/更新/删除/只读边界及F2修复有实际页面/请求依据 | F7；7项正式人工TC、完整平台独立意见及公开原件索引未完成 |

实际查询 run `45167073148`（product a44）已完成：macOS `document-installed` success；Ubuntu `document-installed`及“actual Ubuntu user-systemd Hub”步骤 success；Windows在前景安装包流程失败，SCM步骤skipped。另直接读取Windows回收的platform/failure.json：普通控制进程确为is_admin=false，停止在prepare/check_install读取wheel的PermissionError；cleanup为空任务服务且端口关闭。因此这次是环境准备失败，不能叫Windows产品业务已通过，也不能据此直接断言产品不兼容Windows。新ACL调整的就绪与未来复跑结果须另行记录。

查询时最终head的两个Test packages run `45167908741`、`45167900374` 均为Ubuntu success、macOS/Windows IN_PROGRESS。此为当时快照，后续结果不自动改变本报告。托管成功步骤也不等于完整原trace已在本机解密/核SHA/独立复审；本轮没有把公钥回收脚本或自检当作每个平台实际回收通过。

物理跨OS机器认证HTTPS仍无获准非ESXi环境。维持此必要证据待验证，不访问已禁资源，不建议缩减SPEC或用两个同机档案/托管能力探测替代。正式31项（24自动/7人工）的全项执行、独立需求判定和公开脱敏原件/SHA索引仍未完成。

## 建议的后续处理

先保留本轮三份独立反例和原 v1/F1–F4历史，围绕F5/F6/F7补可观察失败与修复，再重取适用自动/网页/独立包结果；不必扩大为额外权限或同步机制。同步候选证据导航，继续取得获准环境下的当前同版正式记录和最终CI。完成前维持Draft；缺证如实保留，不能把局部绿灯升级为交付passed。

本轮自己的复现目录含 `SHA256SUMS.json`。三份脚本只在TemporaryDirectory创建合成档案，结束清理TestClient与浏览器；各自原stdout/stderr与两张目录拖放PNG保留。原file反例脚本SHA为`1e269eb7ad13d49ed0533ca8abd2082004f413e8c166fc494222d4dcb9451420`，stdout为`05dfb29bc8a88d224cb513102581599ec617a983179b89d1e0e4fb1020f2aadd`；其余文件以该目录清单复算。
