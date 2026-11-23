# AT-SMM-007 网页证据候选准备复审 v2

结论：**accepted（局部候选准备）**。`literal-preparation-review-v1.md` 的两目标身份漏检和 `manual-mac-user-review-v2.md` 的 E1 越端伪造管理证据缺口，本轮候选均已补上可复用断言，Mac v16 原件实际到达并通过这些断言。此意见不判完整 E1、SC8/SC9、A8/A9/A10 或 R007 通过，不替代后续正式人工执行复审；旧 needs_revision / insufficient_evidence 意见仍保留。

## 范围与原始依据

只读检查 `/private/tmp/smm-007` 当前候选及 `/private/tmp/smm-007-macos-e1-v16`，唯一写入本文件。实际读取项目 AGENTS、007 spec/plan、acceptance/manual-cases.md、两份前轮意见，以及 app-delivery-acceptance-native 的 SKILL 和独立 Reviewer 规则。未修改产品、测试、收据或原件，未启动产品服务、重跑业务、执行 Windows/ESXi 或 GitHub 操作。额外自检只从候选 AST 提取三个纯判定函数执行，无产品导入或实例化。

**自然语言判据有效且本轮范围完整。** SPEC B1/B8（spec.md:11、103–110）已规定两端纯文本及创建端管理；A10/E1（:152、154）明确两份逐文档原文、对端只读、伪造添加/更新/删除/配置请求拒绝及资料/磁盘不变。PLAN:96–97、102–103 要求独立完整集合、两创建端逐字读取和越端拒绝；manual-cases.md:3、10–15、20 明确不能只检查首条，且新项目、查询片段、原文都检查脚本/事件不执行、无嵌入节点或触发请求。PLAN:201 将此次两处修正、双向四操作、逐次 API/完整文档表摘要/管理副本指纹和 E1 身份范围写明。这些都是既有义务的取证实现，没有增加产品行为或降低门禁。合法 UTF-8 dropped.md 与 TXT 同属 SPEC 明确支持的纯文本入口，不据扩展名提出新阻塞。

## 候选实现及反例

**实现结论：两处既有缺口关闭。** `scripts/acceptance/hub_documents_platform.py:677–682` 的 read_target_check 核数量、完整名称集合、名称无重复及每名对应独立回执 ID。`:1055` 要求两创建回执 ID 不同，`:1082–1085` 核 API 命中全集，`:1091–1094` 从各文件创建回执建立预期；每次真实按钮读取后 `:1130` 先核 read.id，再由 `:1132、1137` 核独立原字节规范化全文及阅读区。`:1146–1153` 最终核全部目标、四阶段全集和必需原 PNG。没有继续以被测 DOM 名字反选同一原文后就结束的漏口。

`:1096–1117` 包含正确见证及重复目标、第二行误指首目标两个负控；两个 literal-display 原件均记录负控拒绝。本人直接执行候选纯判定函数也确认正确全集接受，缺目标、重复目标、第二目标误指均拒绝。该自检证明探针判定能力，不冒称向产品注入了错误页面。

`ownership_state`（:688–727）每次从两端实际 GET sources/files/library；E1 另在隔离包解释器中用 SQLite URI `mode=ro` 对完整所有 `%document%` 表的全部行（含 FTS BLOB）稳定编码后逐表 SHA-256，仅输出摘要；逐个 `.documents` 管理副本保存相对路径、SHA、长度及 mtime_ns。`forged_ownership`（:729–877）以真实已同步投影及真实 Hub 自有网页资料为不同归属目标，向每个接收端分别发 POST 添加、PUT 更新、DELETE 移除、PUT 来源配置。Hub 请求带真实 HID/epoch/投影 project_id/project_key；本机添加用确实存在于 Hub、且不在 Local 项目全集中的 ID，更新/删除/配置用实际 Hub 自有文档/来源 ID。不是随机不存在 ID 代替合法另一端对象。`:1334–1342` 在真实两端网页上传和 Local 项目允许/同步后调用。

每次 `request` 的真实状态由 `:283` 必须等于 400；`:855–857` 紧接着重新取得两端完整快照，并由 `:686` 与最初快照完整相等比较。不是只核最后一次，也不是逐次更新基线。正确/四个坏状态自检（:730–747）涵盖 API、表摘要、副本内容及文件集合变化；本人另用纯函数确认仅 mtime 改变也拒绝。

| 必推反例 | 第一拦截断言及原因 |
| --- | --- |
| 只有首目标正确，第二目标返回首份正文/身份 | 名称正确但 read.id 错，`:1130` 即失败；身份正确但错文，由 `exact_read`（checks.py:25）失败；仅阅读区错，由 `:1137` 失败。 |
| 两行都叫 chosen，按钮也都读 chosen | 两次可以暂时读到正确 chosen，但 `:1146` → `:679` 名称全集不等而失败；两阶段/必需图也不能作为完整阶段通过。 |
| Local 与 Hub 两边同错或误用同一目标 | 每端独立建立本端两回执映射，各自 `:1130、1146` 及独立原字节全文检查；不是两个返回相等就通过。本次 trace 的两组文档 ID 实际也互异。 |
| 只某一端、某一显示前状态不安全 | 每端独立执行 web；新建项目、片段、两份原文各调用 literal_state。`:669–674` 分别拒绝 window 标记、嵌入节点、累计触发请求，`:1147` 要求阶段全集。 |
| 只对 Hub 投影拒绝、本机代理 Hub 管理却放行，或只首操作拒绝 | operations 同时含两方向四操作；每次 `:855` → `:283` 拦截非 400。Hub 投影只读与 Local 无该对象两种动作前状态分别经过真实对应请求。 |
| 返回 400，但已经修改 API、任一文档表或任一管理副本 | 状态码虽通过，每次 `:856–857` → `:686` 必须与最初完整快照相等；内容、文件新增/删除、长度、mtime 及任一表变化均使其失败。 |

当前目标覆盖了本次既有缺口涉及的创建端/对端归属差异和显示阶段。再增加相同条件下的等价名称/ID，未见会改变本次判定的依据，不作为阻塞。本意见不将这八请求扩称所有 A10 非法值、生命周期或服务身份的完整覆盖。

## Mac v16 实际原件

result.json 记录 darwin、2026-11-23T15:18:48.416402Z 至 15:19:16.204342Z、passed。controller 为 macOS 15.3.1 arm64、UID 501；175 条真实业务进程身份全部 UID 501。commands.json 共 282 项，其中 186 项有真实进程退出码（178 个 0，8 个业务拒绝用 2）；这里只据相关原始动作判断本轮局部准备，不据总 result 认领整个 E1。

两张原始 PNG 已实际打开，没有用缩略图或源码代替：

- `web-a-literal-original.png` 显示 Local 创建项目 #5、两份成功上传及 chosen.txt/dropped.md 两命中；恶意项目名按文字显示，dropped 的 script、img/onerror、legacy script 在片段和下方原文均可见，原文为 `[0,197)`、行 1–4。
- `web-hub-literal-original.png` 显示认证后的 Hub 创建项目 #8、两份成功上传、两命中及相同恶意标记原文；原文同为 `[0,197)`、行 1–4。两图没有把文档 img 标记当图片加载。

逐项核 literal-display 两端 JSON 与各自 web 创建回执，再打开两个原始 trace ZIP（CRC 完整）解析动作、全部网络及 resources 响应，确认：

| 端 | chosen.txt 创建/读取 ID | dropped.md 创建/读取 ID |
| --- | --- | --- |
| Local | `19ca663e27f64f84afb7756d66621fbe` | `9cc4d025673a4f4ead85fae649c0034d` |
| Hub | `7a0203fd135742d7a026538297b8c09a` | `9055eb0fde19425985b4a416f7d8d310` |

两端实际 h3 顺序均为 chosen.txt、dropped.md；四次 POST read 的请求 reference 各自对应独立预期 ID，响应 ID、原文、码点及 LF 行号均逐原件相等（chosen 20 码点/2 行，dropped 197 码点/4 行）。两端各四次原始 evaluate 均为 window/legacy 未设置、embedded_nodes=0；四阶段 JSON 完整且 trigger_requests=[]。Local trace 156 对 before/after、73 条网络，Hub 91 对、47 条网络，均无触发 URL；literal 原件的累计请求列表分别 43/35 条，也无触发。Hub 后段 reload 清空的 network 数组没有被拿来证明此前安全。

**八请求及逐次不变已独立核实。** commands 的零基索引 132、141、150、159 为 Hub 四操作，168、177、186、195 为 Local 四操作，均真实 status=400；服务器原日志同时记录相应 POST/PUT/DELETE 和 400，排除了仅凭保存的 expected_status 推断。Hub 返回创建端/设备投影只读拒绝；Local 返回本机项目/管理文档/来源不存在的对应拒绝，与真实另一端对象的归属一致。

每次请求之后紧随六份真实 GET 和两次只读持久快照，均逐值比较最初快照；初始六份 GET 也与 ownership 原件 before 逐值相同。18 个 snapshot 子进程全部 exit 0，九组每组 Local 14 张、Hub 21 张文档表及每端 4 个管理副本的摘要/长度/mtime 完全相同，最终 before=after。本人以 `mode=ro` 仅查询保留数据库的 sqlite_master 表名，确认两端摘要键确实覆盖全部匹配文档表，没有只选业务首表；未输出表行或保护材料。原件 persistent_snapshot_taken=true，四坏状态自检标记=true。

## 版本、敏感边界与保留记录

runner-bindings 三项均重新计算等于当前候选：platform `c56f4fdd15f89cb0d2033e5528e65d0645248d6cac81619c066e17f43e81f203`，checks `3f1d1921c0646dbdec12ccd04ddcd3f44666602ad50f6faadfd3ad5c87859334`，MCP worker `aa2188fbb7197c5ef13259c1eb8b74917ab89a775b288f37f3dd90d908171f32`。独立 v4 Local/Hub wheel 实物 SHA 分别为 `0eca3d5828ab443e94396d1af39e1d775d4311b2b82a9c59b5fa8f4052a15fd9` / `3268544c4475087c64d76d3124b1aec6c3ab7e41c5f4385828fd9d55849ddd44`。Local 30、Hub 31 个模块/HTML 的实物安装、wheel 与当前源逐项一致；Hub vendor 映射 Local 源，生成 shim 另按 build_packages.py 的替换规则计算一致。`git diff 245c236 -- src` 为空；tests、checks、MCP worker 相对该产品基线及当前工作树无差异，未用本轮修改冻结测试换取通过。

快照源码在 E1 两端同一普通 actor 自有档案内只读；包含 external_hub 的 SCM 配置明确跳过直接持久快照，且保存 persistent_snapshot_taken=false，不授予普通账户 Hub 状态权限。SCM 配置原实现确实使用 external_hub；本次未改 ACL、RPC 或服务身份，也没有认领其磁盘检查通过。

持久快照 stdout 的实际结构仅有 table_sha256 和 managed_disk（sha256/bytes/mtime_ns），BLOB 编码仅在隔离子进程内参与哈希，没有输出数据库行、BLOB 十六进制值或保护密钥。CI helper:72 仅明确新增 ownership-forged-management.json；原 `.documents`/环境/源目录排除、数据库/密钥不在白名单及原始 trace CMS 封装边界不改。新增 document-installed-e1 的三系统普通 E1 路由与先前审查一致，服务步骤仍只匹配 document-installed，默认 005 未变；本次未运行托管 CI 或据此声称三平台通过。

v13 的 BLOB 不能 JSON 序列化、v14 的 created_project KeyError 失败原件仍存在；v15 成功但详细快照保留私有，不作为当前摘要输出证据。v16 使用新目录，未覆盖这些历史。cleanup.json 记录八个任务进程均 alive=false、全部当前端口关闭；本次未重启任务。

关键原件 SHA-256：ownership `9aed9d65177e9f2c1c6f94c1044275b34aa24efda2c4119d571d452e88346e07`；Local/Hub trace `8bd0d055f3fd9679abf891bf32430173688e5be5e7e5d7469d14290c9fd2c1d2` / `5435e40bb8ef1f9f45cfc0573560e8f5542ed78111ecd05599cf6fd876b49033`；Local/Hub literal 原 PNG `2c82c245b6e45ff710dcf0e1531512e86d8e9a826b586df341c803e54002e409` / `50f848806b47e1d1bea5db86e20d8d9e8a5b0ea21df3ddd23230cffdeae23f05`。

可将本轮候选和 Mac v16 这两项局部原件交后续正式独立复审；没有本轮必须再修订的候选准备问题。
