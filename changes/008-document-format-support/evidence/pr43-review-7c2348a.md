# PR #43 检查点独立审查：7c2348a

结论：**needs_revision；SC1/R008 未完成。** 本次队列补丁的单档案限定效果有可信的 Mac 与 Windows 组件证据；此前队列锁超时/上传准备断连不能继续笼统列为这些已测流程仍失败。补丁新增的同父目录多 SQLite 档案丢唤醒静态风险仍成立，原生绿灯复审仍是 `needs_revision / design`。维护者保留该缺口不构成 SPEC 豁免。旧 F1/F2/F4/F5 与完整平台验收缺口仍在；没有发现另一项有充分依据的新产品回归。

## 审查范围与方法

实际 HEAD 为 `7c2348a8b1dfa9550ce024d1cc42b25eaaaa3fb3`。全 PR 基线为 `d8894d429ebe0915e377513a637b5dfc0fc7ea1a`；本次主要审查 `12e5128952ae2929b6c920158022f7d973213f76..HEAD` 的 17 个文件，以旧全 PR 意见 `changes/008-document-format-support/evidence/pr43-review-abf46ca.md` 和上一检查点 `pr43-review-12e5128.md` 为既有依据。不是重新审遍整个 PR，也不是全 PR 重新验收。

已读取项目 AGENTS.md、PR Review Prompt、008 intent/spec/plan 的约束与相关实施记录，核对当前增量、冻结队列测试、原生红绿结果/独立意见、公开证据及其私有原件。当前 SPEC SHA256 为 `e6ba46812b4083b20820278005bb3cb0d32764372d8c8ef8e23b2e638ddfea28`，与冻结 R008 定义引用一致。未运行 pytest、native、构建、业务客户端或远程命令；仅用标准库只读解析、摘要、ZIP/tar/XML/AST及 Git 对照。只新增本文，不修改产品、测试、已有意见，不向 PR 写入或合并。

## 当前问题

### N2 · P1 · 共用锁的另一档案被当作本档案消费者，可能丢失唯一唤醒

性质：**有源码依据的静态产品风险，尚未实测复现；已有原生复审的设计缺口。** 不是将未来拟议用例当作本轮失败，也不是新需求或可由“只测单档案”豁免的条件。

位置：`src/smm_local/managed_document_uploads.py:183–206`，`document_snapshots.py:23–24`，`api.py:282,411–414`；入口依据为 SPEC B4 的 `smm --db <档案>`、B9:131 的每档案任务契约，以及 README:123 的独立数据库用法。`Archive` 接受用户指定 SQLite 路径，没有同父目录只能有一个档案的约束。

`Snapshots.root` 是数据库父目录下的 `.document-snapshots`，故 `D/a.sqlite3` 与 `D/b.sqlite3` 共用 `upload-queue.lock`；两者待办却在各自数据库中。本补丁 `timeout=0` 争锁失败即返回（189–195），持有者 `_drain_pending`（205–206）和解锁后复查（199–200）都只查自己的数据库。A 档案持锁时，B 档案真实提交 pending 后唯一后台 kick 可直接返回；A 完成后只检查 A，不能保证 B 再有消费者。没有第三次上传、重启或额外 kick 时，B 的合法 pending 可能一直无法变成可检索资料。解锁后同库重查只解决同一数据库空队尾窗口。

影响对象是使用明确独立档案的 Local 用户，影响上传完成而非只有发现难度，关联 B1/B4/B9、A1/A7/A10。现有四参数各只使用一个 Creator/database，Local 与 Hub fixture 又在不同父目录，因而本风险可与全部现有断言通过同时成立。没有证据声称所有用户必现、数据损坏或已经实测永久 pending。

处理边界：维护者已明确保留 SHA256 `d48d3264294bee9e344ff476b5b9f914c107e4593b0a831f47c7282f0c66a655` 的 `cross-archive-proposal.md` 所述缺口，不新增其 TC、不应用进一步补丁、不专跑。本轮遵守该决定。未来若重新纳入，适度通过条件是实际同父目录双档案受控争用、第二档案真实持久提交、释放后不靠额外 kick/重启救场，两库各自完成并按独立身份/真值读取；不要求固定锁算法。当前不能关闭此项或把队列 TC/SC1 标为完整 passed。

### 既有问题的当前定位

| 项目 | 本次源码核对与结论 |
|---|---|
| 旧 F1 / P1：失效已 commit 未发布 canonical 字节缺 GC | `document_snapshots.py:50–79` 仍累计 raw/results 并仅排除曾发布 ledger；未见最后用途/活跃分配感知回收。本增量未修改该路径。仍保留；不是已修的未 commit incoming TTL 预约问题。 |
| 旧 F2 / P1：路径 refresh 发布拒绝缺失败终态 | `documents.py:428–433` 置 refreshing 后只包扫描，`459` 发布可抛错，`482` 来源终态不执行；managed 的 fail_current 不覆盖这条路径。仍保留；未专跑保留取消条件，也不声称新结果已错误发布。 |
| 旧 F4 / P2：路径 Web 文件状态缺候选/重试值 | `static/index.html:141` 仍只输出 path/status/version/error；API/CLI files 可取得详细字段。因此是局部信息不足与误读风险，非所有入口阻断。仍保留。 |
| 旧 F5 / P2：活跃服务 CLI 内容任务未交接 | `hub_admin.py:435–445` 直接分派，HubDocuments 的 refresh/reprocess 仍可在 CLI 流程处理；PLAN:75 要求交同 state 服务 worker。仍属已说明但未完成的实施方案，前景成功不替代实际服务身份。 |
| 上一检查点 N1：队列锁超时/Windows 上传准备断连 | 忙锁不再等待默认五秒后抛出，真实协调器取得锁后的 RuntimeError 继续传播；单档案两窗口 Mac 实测及所选 Windows TCP 上传/远端读取流程已通过。**限定缓解成立**，不能继续把该次旧失败称为当前同流程仍失败；也不能扩为所有队列调度已正确，N2 仍在。 |
| 已关闭项 | 合并表头 F3、纯 Hub original 路由、处理版本隔离及 managed/缓存重试 CAS 收尾的既有限定结论保留；本增量未改这些模块。没有重新核全部历史业务原件，不重新授予整域通过。 |

## 计划、设计与实现一致性

本增量唯一产品文件是 `managed_document_uploads.py`。旧受锁 `while` 消费体与新 `_drain_pending` 的 AST 逐项一致；新增行为是非阻塞取锁、取得协调权前后区别 RuntimeError，以及释放锁后查询本库 pending。没有新 schema、CLI 参数或处理结果替身。PLAN:311 记录方法、两次测试修订、红绿/Windows/构建范围及保留的跨档案风险，没有未说明的新实现偏差；但该记录不能把尚未满足的规格改成已完成。

冻结 `tests/test_document_formats_upload_queue.py` 覆盖 Local/Hub × processing/empty_handoff。第二份真实 commit 返回后只读 pending、SHA/CID 发事件，再启动独立 Timer；不再要求第二个 TestClient 后台 Future 先返回或第二 kick 必须进入 OS 锁。最终核两份独立 ID、V/P、SHA、CID/AID、检索/正文/全表/原件、两行 done，并要求真实协调器数据库 RuntimeError 可见。6.5 秒是测试释放控制，不是产品 SLA；当前短时绿灯不证明 Timer 回调曾触发。

SC1 冻结判据还包含两端路径/选择拖入、默认关闭、投影管理拒绝、旧页/身份/epoch及配置边界。本 TC 仅承担 creator-upload-queue 子域，独立意见 `covers=[]`，不能由四参数推广 SC1。未跟踪的 path-refresh case-design 还没有本轮产品/测试执行，不计当前交付。三份未跟踪 Python 草稿及其历史 `.py.txt` 不计正式可执行测试或当前通过绑定。

## 本轮实际证据复核

以下区分完整性复核与业务语义复核，不能把“全部摘要一致”写成“全部业务逐份重验”。

1. **Mac 原生链完整性**：逐份重新计算 red v1/v2/v3 的全部 80/80/80 个 artifacts（354,680 / 355,312 / 356,092 字节），以及 green v1 的 183 个 artifacts（763,892 字节），无缺失/不符。green 的 94 bindings 全与盘上相符，62 product 与 22 test bindings 又逐项与 HEAD Git 字节相符。可信 red-v3 与 green 测试绑定完全相同，产品只队列模块变化。green result SHA 为 `ea28814aa1a3bc8572289a9929ee8a73d4cfe7e62fecd20bf7d305881d8a8d58`，red-v3 为 `fea7a654f22ed760db1556b7fdc50b1b006aea9a5f2cb092187837d1682d4149`。
2. **执行和独立判定**：实读 red-v3 原 stdout 四分支在第二后台调用的 RuntimeError 断言失败，4 failed / 23.22s；green 主项 4 passed / 4.29s，相关回归 8 passed / 119.50s，execution 均 exit0。回归实际选择 remote_original、uploads、update_replay_c1、transfer_expiry，不能把 update_replay_c1 混成保留的 upload_restart_c1。四份 review result/其列明 artifacts 摘要及 target 对应正确：前两红 `needs_revision`（分别 implementation/design），第三红 `expected_failure`，绿 `needs_revision/design`。绿 review SHA `a1258ee7cea80ca50cca296f2aff9df9615a1588e43e685d51e048f67031020b`，未被 Windows 补充改判。
3. **本轮 Mac/Windows 队列语义核对**：分别打开全部四份 handoff 与四份 complete：两窗口、两端齐全，异常均 None，空队尾前 pending=0，每项两独立 ID 均 done/error=null。分别八份输入与保存下载按实际 SHA/字节对应；全部 Office ZIP CRC/XML 可打开。本轮没有重新对所有管理响应的每个正文词、表格格值/跨度和 profile 全字段逐份建立独立预期；这些完整业务核对依据两份已有独立意见及已到达的冻结测试断言，不能冒称由本检查点重新全核。
4. **Windows 传输/源码链**：只读 controller.py/run_remote.py、preflight/remote/transport/transfer、result/stdout/JUnit。六阶段均 exit0，各 stdout/stderr 摘要吻合；实际 preflight admin=true，Python 3.14.10/win32，选择仅四队列参数与纯远端原件项。tar 恰 274 成员，全部与回传 manifest、当前本地源码及 HEAD Git 字节一致；tar SHA `2180303e19587a55a8082bdd4f1c5dab257e22f8cbdf34dc8d5b797da5261c73`。不是 wheel 安装业务或官方 CI。
5. **Windows 回收完整性**：`evidence.zip` 长度 3,483,660、SHA `9ef7d483a16580c741dbf2754c138343ceef6ff523c64f80ac73dc4b99573b6b`；CRC 正常，1,508 成员。opened/sha256.json 的 1,507 项逐份长度/SHA及 ZIP/解包字节全部一致。JUnit tests=5、failures/errors/skipped=0，suite 367.870s；stdout 为 5 passed / 389.54s，两计时面分别保留。result exit0、未超时、cleanup_errors=[]。这不是重新执行或证明完整清理 H5。
6. **Windows 远端语义复核限度**：本轮解析全部 72 个 verified-download 事件，确为 24 独立 key 各 cli-search/http-search/stdio-reference 三次，48 个 stdio 调用记录存在，24 个 wrong-Hub 事件均4xx。没有重新逐份重建 24 目标全部 origin/profile、正文/表格真值、CLI/HTTP 元数据与观察器日志基线；其更完整反查引用既有 private 独审及公开脱敏副本。原意见 SHA `8702ea2424eb8de615ea7e48a1e670352781325a8dcd5f1cb21a1341cb217489`、公开副本 SHA `bb3e037ab253448f349eb66fbfa7374a882be6378449d3503d2ec984a175bc08` 已核。该意见明确 72 是循环次数、24 是不同原件，也未把 stdio 元信息当直接文件字节。
7. **已保存构建**：只读打开两 wheel，复算长度/SHA/CRC；Local 46、Hub 47 个声明源码成员逐字匹配当前源码（Hub `_archive` 映射对应 Local 源）。两包包含队列 SHA `2cf2ea859f3c8b1d3bba9eb924434d73f28bcffd6be14faf6c00dfe014a05303`。Local wheel SHA `afde4615d9d78543f48256c1b1016473a759990ba2040eedc9138bf05872e6ae`，Hub `0a213c453f43a8a5e52bda0a40609f8258a65a5ab8edfd6841481a32a052fc8c`。只认构建/成员字节，不认本轮安装后业务。

公开 upload-queue-development.json、PLAN:311 与独立意见边界一致。pending-verification 的新 queue_fix_checkpoint 明确 native needs_revision、Windows 组件通过和完整未完成；其旧 windows_upload_queue_defect 子键仍写 fix pending、remote_query_routing_fix 的旧 other_findings 还列已关闭表头，属于历史状态未显式标历史的索引陈旧，建议以后整理为历史/当前分明，非新增产品阻断。本次未取得/核验 7c2348a 的最终三 OS 普通 CI，不用 abf46ca 的旧 CI 或 Windows 补充替代。

## Intent 角色与用户入口回放

本表沿当前可见文档/源码静态回放，没有重新操作 CLI/浏览器。队列修复没有新增用户操作或参数。

| 角色与目标 | 主入口、可见下一跳与值来源 | 当前判断 |
|---|---|---|
| Local 使用者纳入格式、检索核原件 | README:61–67 明示开发中/格式/创建端 → 008指南153–180 同构建独立 wheel、材料入口、绝对 OCR 路径、status revision/check → 184–208 明确上传或 add/refresh，ID取返回/列表，ref/table_id取搜索/正文，原件下载 | 能发现并开始操作；单档案队列改善真实完成路径。N2、路径 F2/F4及 E1不足仍限制整体完成。 |
| Web 使用者选择/拖入并判断结果 | README:65 → 指南184–186、212–218 的接收/处理/发布、库详情与下载 → 当前两端项目资料库和 reader | 说明区分收到和可检索，库详情有当前尝试；本轮四项为 ASGI，Windows远端项含 TCP，但不是拖入/真实浏览器全验。路径“文件状态”仍 F4。 |
| Hub维护者准备创建端/服务 | README Hub与008入口 → 指南168/180 使用实际 state-dir、所在端配置及执行身份 → status/check与认证管理入口 | 参数含义和取得方式可达；CLI任务交接 F5仍未完成，SSH管理员 check/源码成功不能代表 LocalService 或普通客户端。 |
| Agent/同步资料使用者读取依据 | README Agent接入 → skills/smm-search/SKILL.md:58–72 实际能力/项目选择 → exact reference → text/table/original-info，再交 CLI/认证 API下载 | 支持范围、只读边界、表格参数和引用来源可见；Windows所选 stdio引用交接有补证，不能扩成全部查询/正文表格矩阵。 |
| 维护者复跑和判交付 | README:67 SPEC/PLAN/证据 → scripts/acceptance/README:3–32 普通回归、OCR材料、组件/安装/E/H/X及回收入口 → pending索引 | 有可达复跑路径，明确无一命令代整体验收；上列旧索引子键建议标历史。 |

## SPEC 逐项检查点判断

| 条件 | 本次增量支持与仍未满足的部分 |
|---|---|
| A1 入口/创建端 | 单档案上传重复唤醒有双端组件结果；N2、路径详情/收尾及完整入口/权限/E/H仍未齐，SC1不通过。 |
| A2 DOCX | 队列目标确用真实 DOCX并读回；不是重新验全部部件/格式/平台。既有限定结论保留。 |
| A3 XLSX | 队列含真实 XLSX；隐藏/公式/类型及完整 E/H不由队列专项证明。 |
| A4 原生/混合 PDF | Windows remote-original含原生PDF后续路由；不证明混合/全部布局/预算。 |
| A5 OCR | 本轮主项不是新 OCR质量专项，三OS/服务质量与故障恢复仍缺。 |
| A6 直接索引 | Windows远端项含投影后续读取；不代 X1六方向、无处理依赖接收环境和完整零调用矩阵。 |
| A7 成套/并发 | 同档案处理中/空队尾两个窗口有证；N2、路径F2、保留C1五项及其余并发/恢复不关闭。 |
| A8 生命周期 | 未改既有消费/发布体；旧F1/F2/F4、active-source取消/最后授权及全生命周期仍在。 |
| A9 查询/原件 | 已选Windows远端原件流程通过补证成立；全scope/浏览器/HTTPS/重启引用和平台入口仍不足。合并表头不重复报旧缺陷。 |
| A10 有界/隔离 | 非阻塞队列协调有证，内容单槽/监督没有新增完整实测；N2、GC及完整预算/任务树/五秒恢复仍未齐。 |
| A11 兼容/发现 | 当前文档入口链与保存wheel源码一致；F4、最终最低Python三平台安装业务及最终三OS CI未齐。 |
| A12 平台/证据 | 原生链完整、独审判定准确，Windows补充仅SSH管理员源码组件；E三格/H三格/X六方向、完整C1与最终独立交付链未完成。 |

用户保留的 active-source、C1 五项和 shared Windows 字符串 argv 未专跑、未修补、未改 skip/xfail，不算通过或 SPEC 豁免。本轮没有重新授予全部历史证据通过，也没有将未到达的断言写成失败。当前可保留单档案补丁的限定实测事实，PR 仍应维持 **needs_revision / R008未完成**。
