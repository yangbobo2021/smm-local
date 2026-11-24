# PR #39 独立审查 v1

结论：**需要修改，当前不能交付通过或合并**。发现四处有实际影响的已确认规格缺口：远程接口可让 Hub 服务扫描外部路径、混合批次上传缺少逐文件结果、Local Web 缺少去 Hub 创建端管理的入口、Local Web 丢失原文实际读取端及必要出处。候选完整回归和独立包结果支持已执行功能，但不能消除这些遗漏，也不能替代尚未取得的正式同版验收和 E2 证据。

## 审查范围与方法

本轮是独立新上下文审查。实际读取 `AGENTS.md`、`changes/_templates/pr-review.prompt.md`、007 的完整 intent/spec/plan、`changes/007-hub-document-search/reviews/project-library-authorization.md` 原话，以及修改的产品、测试、说明和既有审查。按 Prompt 先比 PLAN，再回放使用角色入口，最后对照 SPEC 与证据；不因一项平台缺证停止其他审查。

实际 `gh pr view 39` 确认 PR 为 OPEN/DRAFT，base main 为 `83b50fcbbad1f29484aa54104ca0f9e75d0498e3`（PLAN #38 merge），head 为 `de41d7e77fc207f4850fc35a2968dedd6f10ad5a`。审查 diff 正是 `83b50fc..de41d7e`，工作树 HEAD 相同。报告只适用于该候选，不自动认可后续修复。未修改产品、测试、已有证据或报告；未代发 GitHub 评论，未访问 ESXi、日常档案、日常 Hub 或 VibeInsight。

为验证两个具体反例，使用全新合成临时档案运行当前 app；原始反例脚本和输出单独保存在 `/private/tmp/smm-007-pr39-review-v1/`。浏览器反例实际运行 Chrome 157.0.8103.50，页面请求经 Playwright route 转交真实 app 的 TestClient，**不是实际网络 E1、TLS 或普通服务身份验收**。反例只证明对应产品行为。

## 已确认发现

### F1 [P1] 远程文档接口绕过 Hub 外部来源仅由 CLI 账户采集的边界

性质：明确违反 SPEC B5 第69行及“边界与约束”的服务身份约定，不是新增成员权限建议。

`src/smm_hub/document_api.py:60–62` 把远程 `POST /v1/documents/sources` 直接交给 `documents.native("add")`；第72–75行把远程 refresh 直接交给同一管理对象。`src/smm_hub/documents.py:194–223` 没有调用入口限制，`native("refresh")` 在服务进程中调用 `Documents.refresh`。持有既有 token 的远程调用方只需从 `/v1/info` 取得 HID/epoch，就可添加其指定的 Hub 绝对文件/目录，再令 Hub 服务账户读取。`source_id` 省略时还会刷新全部 Hub 自有来源。这与网页字节上传到专用副本库是不同能力。

实际反例：合成 `server-secret.txt` 从未经 CLI refresh；认证 HTTP add/refresh/search 依次返回 `[200,200,200]`，状态 `pending→ready`，搜索返回 `needle service-account external source`。服务具有额外外部路径读取权限时，远程调用者可利用该权限采集资料；即使当前同 UID 前景进程，这也已违反承诺的调用边界。不是匿名访问漏洞，认证本身正常。

建议：远程原生来源接口不得执行外部 add/refresh 采集；保留必要的已采集来源配置/撤回及管理副本操作。若保留 refresh API，须明确拒绝外部路径来源并避免无 ID 刷新它们。通过条件：认证 HTTP 对合成外部来源 add/refresh 不能读取或发布正文；CLI 显式 refresh 仍可采集；Web 字节上传/更新仍可用，服务启动、查询与同步仍不打开外部文件。

### F2 [P2] 两端多文件上传遇到单份错误后，不报告已保存和未处理的文件

性质：明确违反 B8“逐份报告成功/失败”，影响普通网页用户确认真实纳入范围；没有声称当前页面会假报全成功。

Local `src/smm_local/static/index.html:196` 与 Hub `src/smm_hub/static/index.html:47` 把整个 for 循环包在一个 try/catch 中；第一份失败就退出循环，失败分支也不 reload 已经成功保存的资料。当前没有逐文件状态/文件名。

实际 Chrome 回放：依次选择有效 `A.txt`、严格 UTF-8 无效的 `B.txt`（字节 FF）、有效 `C.txt`。两端的真实库都只有 `A.txt`；notice 都只有“文件不是严格UTF-8文本”；页面资料库仍为空。A 已成功但不可见，C 没有尝试，用户无法从这次结果判断哪些文件已进入哪个项目。普通“查看项目文档库”可恢复查看 A，是已有补救路径。

建议：逐文件捕获并报告文件名及成功/拒绝/未处理状态，始终刷新已成功项；可继续处理其他文件，或明确说明余项停止。通过条件：相同三文件批次两端均显示 A 的真实成功、B 的具体错误及 C 的真实处理结果，列表与实际库一致；重复/重试不意外新增 A。

### F3 [P2] 从 Local Web 查到 Hub 项目后，没有去创建端管理的入口

性质：B6 第79行、B8 直接要求的入口缺失；影响限定为发现和跳转，不阻断已知 Hub 地址的用户。

Local Web 的项目端选择器只标“Hub 项目（只读）”（第64行），`refreshHubRoots` 第175–177行填项目选项，但没有管理提示或链接；整个 Local HTML 没有到配置 Hub 的链接。配置页第270行只把 `hub_address` 写进 `textContent`。用户沿“文档→Hub 项目→查到资料”能读文档，却不能在当前路径知道到哪里添加/更新/删除 Hub 项目资料。

已有可用路径：README 第53–61行及 TRIAL_GUIDE 第102行明确介绍浏览器直接打开 Hub HTTPS 地址、向维护者取得 token 文件；用户可离开页面回指南，或从配置页复制地址。故问题是局部路径缺失，不是整体功能不可发现。

建议：在文档页/Hub 根选择处提供已配置 Hub 的无凭据链接，并说明创建端管理和凭据文件来源；不能导出 Local 保存的 token。通过条件：已连接用户从 Local 文档入口可到正确 Hub 空壳页，地址无 token，刷新后仍须由用户选文件认证。

### F4 [P2] Local Web 没有显示实际原文读取端，出处不足以区分 Hub 自有与设备副本

性质：明确缺少 B6 第87行及 B7 第91行要求的可见信息；API 路由本身不因此判错。

`src/smm_local/document_search.py:308–354` 正确在 Local/Hub 读取结果上返回 `archive_scope`，bundle 也按当次同版精确 ref 回退。但 Local `static/index.html:156` 的阅读区忽略该字段，只显示名称/路径、版本/采集时间、SHA 和范围。搜索行第160行只显示 `local/hub/combined` 和不透明 `source_ids`，没有 Hub 自有/哪台设备的稳定身份及项目/接收信息。两端相同原路径的同版副本或 bundle 回退时，用户无法判断这次实际由哪一端提供原文；不透明来源 ID 不能替代出处解释。

已实际打开当前包流程的 `/private/tmp/smm-007-macos-e1-v8/web-local-joint-read.png`：Hub 自有 two.md 的阅读区确实没有实际端；搜索列表的远端设备和 Hub 自有命中均显示 `hub`。本轮没有把该画面说成 bundle 故障回退实测，回退影响依据上述渲染代码和 API 分支静态确定。

建议：阅读区显示响应的实际 Local/Hub 端、原档案/设备身份及适用接收状态；命中行区分 Hub 自有与设备及项目。通过条件：同名跨设备资料可辨，合并命中先在本机读、再使本机当次资格失效而从 Hub 同版回退时，正文仍正确且阅读区随实际端变化。不要为展示而重新读取别的版本或改权限边界。

## 反例原件及复跑

稳定脚本：`/private/tmp/smm-007-pr39-review-v1/repro.py`。从候选根执行：

```text
.venv/bin/python /private/tmp/smm-007-pr39-review-v1/repro.py
```

Chrome 默认 `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`，可用 `CHROME_BINARY` 指定现有可执行文件。脚本只创建并自动清理自己的临时档案，不启动后台产品服务。原输出 `/private/tmp/smm-007-pr39-review-v1/repro.stdout`，原 stderr `/private/tmp/smm-007-pr39-review-v1/repro.stderr`，本轮实际退出0。stdout逐行保留远端扫描和两个混合批次的真实观察；这是发现的见证脚本，不是把错误行为当需求 passed 的验收断言。

| 文件 | SHA-256 |
|---|---|
| repro.py | `5cafe4e36be940986176f19809582dabaabced2e0504dfe983aa93cbe2ed5aec` |
| repro.stdout | `6e426d93a62534643083ede1136fa3619225175d2af3d038dc4abeee43154ddf` |
| repro.stderr | `066cc191f6664c38c128f04db050a826a638f88d970c0cc6a5e9f42eac02928c` |

## 按真实主入口回放各角色

| 角色/目标 | 起点及当时可见内容 | 后续可达步骤、输入和确认 | 判断 |
|---|---|---|---|
| 本机使用者：新建项目并查到自己的文档 | README 第33–61行先介绍006/007，明确公开0.4.0不支持，并链接指南/独立包；不是从未发布命令直接要求普通安装用户尝试 | 指南第88–100行给独立包、独立DB、空Agent来源和serve；Web主导航“文档”可见创建本机项目、选择/拖放、目录纳入。CLI第133–164行能找到create、来源项目ID、pending→refresh、search→reference→read。页面成功后可查看资料版本/按项目搜索 | 单份正常路径清晰，格式/位置及采集区别充分；混合批次确认有F2。 |
| 跨设备使用者：决定同步并查原文 | README 007独立小节明确默认关闭和创建端；指南第118–144行介绍configure-hub、KEY/HID/G取值及精确引用 | Local“项目文档同步选择”显示目标Hub、稳定KEY、G、本机状态和Hub确认；网页闭包第183–185行绑定当时值。CLI sync-policy帮助虽简短，但父层及指南提供取值；选择后保存和Hub确认分开。项目选择器可切Hub根，独立MCP列表有两端coverage | 当前代码与旧页拒绝材料支持CAS。读原文数据路由可用，但Local呈现有F3/F4。 |
| Hub维护者：创建Hub资料库/维护文件目录 | README 007提示HTTPS地址与token文件；指南第102–116行分别说明网页字节和Hub本机路径 | Hub根匿名只给连接页，文件来源及内存认证可见；认证后项目create、选择/拖放、按项目搜索/read、更新/移除。Hub CLI父层 documents、project list/create、state-dir共用说明可达；来源ID来自sources/add。设备投影后端 `_own_source/_own_project` 拒绝普通管理 | 正常创建端路径可达。服务不得读外部路径的边界被F1绕过；网页批次有F2。 |
| Agent：只读文档证据 | README“Agent接入”第140行链接真实Skill；Skill第58–70行先核安装版本，再列sources/projects→search→read | Skill明确include_hub、scope两种ID、local、覆盖/fallback、严格UTF8、reference/码点及三只读文档工具；MCP schema与include_hub修复相符；管理另走Web/CLI，不推断上传授权 | 发现及参数链完整。搜索可能进行已有最小项目登记，未见私有候选外发；不把只读声明扩大成零元数据写承诺。 |
| 维护/复跑者：取得适用依赖、隔离运行并核证据 | README007末尾→scripts/acceptance/README.md007→SPEC/PLAN及manual-cases | 文档说明包、控制环境/浏览器、合成档案、私有原件、双SHA及禁用ESXi；源码开发给test extra。平台脚本与CI document-installed可找到。evidence/README明确候选而非通过 | 维护路径存在；正式公开逐项证据仍缺，见下节。验收README第5行仍写20自动/7人工，已落后定义/PLAN的22自动/7人工；第7行只给旧主文件命令，会遗漏SC11/12，建议同时列补充文件或完整pytest，防维护者局部复跑漏掉已知契约。此陈旧导航没有阻止完整pytest实际运行。 |

实际打开了上述 `web-local-joint-read.png` 及 `/private/tmp/smm-007-user-paths-debug-v2/same-hub-old-generation.png`，后者清楚显示“本机文档选择已变化，请重新查看generation”以及旧页的稳定KEY/HID/G。截图仅作为相应局部界面观察，不能承担未显示步骤或整条生命周期的通过判定。

## PLAN符合性和验证差异

产品模块与计划的职责划分基本一致：纯Documents扩展、ManagedDocuments、独立协议/同步/联合搜索、Hub API/CLI/Web、vendor独立包及CLI/MCP/后台接入。改动没有触碰AGENTS/CLAUDE。PLAN第128–158行记录证据无损gzip、包原件持久化、真实HTTP数组兼容、补充控制竞态回归、SC11/12新增、CI标准账户与禁用ESXi，未发现把这些调整伪装成已确认行为改变。006隔离测试仅将旧默认查询明确为local=True，保留旧零网络守卫，符合007新默认联合契约。

F1不是PLAN已说明的合理技术调整：计划与SPEC都承诺Hub外部来源由CLI账户refresh，新增远程扫描入口扩大了实际能力。F2/F3/F4也不是计划允许删除的用户可见义务。需返修及补反例，不宜只通过修改指南描述当前行为消除差异。

当前证据与正式交付有明确差别：本轮实际读取候选完整pytest stdout/XML，328测试、0失败/0错误/1跳过，stdout为327 passed/1 skipped；检查独立包result/18命令导航及macOS安装清单，其可直接映射当前src的模块SHA无差异。macOS及旧页两个调试目录result均为passed，cleanup记录任务PID已退出/端口关闭。但这些仍是候选调试原件，不能重新命名为原生需求passed。原生定义000005、旧27项及新增SC11/12、历史红绿审查/包insufficient_evidence均须保留。此报告没有发出原生逐TC独立passed意见。

| SPEC验收 | 当前可支持的结论 | 本轮限制/缺口 |
|---|---|---|
| A1 授权入口 | 代码/测试覆盖默认off、独立项目控制、稳定key/HID/G、暂停及恢复保护；旧页画面与原请求材料可复核 | 最终同版逐TC正式记录/意见尚待；不由一次完整回归替代 |
| A2 完整发布 | stage/publish事务、双摘要/长度、16MiB边界、完整清单、单调序列和回执逻辑与自动断言相符 | 本轮未重审每份原生边界JSON为需求passed |
| A3 生命周期 | 代码分离连续资格/文件版，暂停控制只保留已知成员，撤回任务持久；已有active/paused/overlap/离线测试及候选Mac流程 | 必需平台尚未完整正式复审；不把暂停称为永久冻结版 |
| A4 顺序/身份 | 独立origin、CAS、控制/发布序列、guard/epoch及4个补充竞态回归有明确实现 | 本轮未发现新的已确认并发违例；不是证明不存在其他竞态 |
| A5 Hub自有 | 创建端检查、CLI state-dir和来源/项目管理可用，设备路径不送扫描器 | F1违反扫描调用账户边界；服务身份业务证据仍缺 |
| A6 联合范围排序 | 按签名一层范围精确映射，2limit候选BM25重排；SC11/12修复能在代码/327测试结果中定位 | F3/F4；最终正式SC11/12绿灯仍待；同号/同名不替代身份 |
| A7 准确原文 | 引用封装/当次资格、Unicode范围和实际端返回有实现/测试依据 | F4是实际端展示缺口，不声称读到错误文本 |
| A8 兼容与发现 | 完整pytest327/1、独立两包18命令与模块SHA、指南/Skill正常路径有依据 | F2–F4及复跑导航陈旧；最终三系统CI/公开SHA原件索引仍待 |
| A9 实际平台 | Mac候选包CLI/Web/stdio材料存在、来源指纹/进程清理可检查 | E1其余两平台当前未获同版完整独立正式意见；跨OS真实机器、Ubuntu user-systemd、Windows SCM/LocalService业务证据未取得。能力探测/前景Hub不能替代；不得使用已禁ESXi |
| A10 网页库 | 两端单份纳入/更新/删除、类型/路径/CAS/创建端隔离已实现并有现有自动/候选浏览器材料 | F2明确违反批次结果契约；其他必要真实浏览器/平台证据待正式登记 |

审查时 `gh pr view` 返回的本候选 Test packages 三系统检查仍为 IN_PROGRESS（两组run）；不把进行中视作通过，也不据未来结果预判。evidence/README第12–15行仍明确托管CI/E2及正式公开索引待补，这种候选状态描述是诚实的。根据PLAN第122行，缺任何必要当前同版TC/平台及独立需求意见均不能给交付通过。

## 处理建议与复审通过条件

先保留本候选和反例，围绕F1–F4补明确失败见证、修产品并重验受影响测试/包/网页；特别保持远程字节管理与外部路径CLI采集的边界。更新维护复跑入口的22自动项，避免遗漏SC11/12。之后取得新候选同版正式逐项记录、适用回归与最终CI，继续落实获准非ESXi环境的E2；没有环境时如实保留缺证，不降低SPEC或要求启用禁用资源。

本轮没有提出需要扩展项目类型、权限体系或额外管理流程的SPEC外阻断建议。F1–F4均来自已确认行为；平台/正式证据问题单独列为证据不足。修复完成应使用新版本审查，保留本轮结论，不覆盖旧意见成passed。
