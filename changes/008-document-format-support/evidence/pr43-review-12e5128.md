# PR #43 检查点独立审查：12e5128

审查结论：**needs_revision；R008 未完成。** 合并表头增量的限定修复成立，未发现该补丁新增的可确认产品回归。旧 F3 在本次限定范围内关闭；旧 F1/F2/F4/F5 仍成立。另确认 Windows 上传队列争用导致后台异常及后续 HTTP 断连，是新识别的产品问题，不属于维护者保留的 argv 审计缺口。

实际核验提交：`12e5128952ae2929b6c920158022f7d973213f76`；全 PR 比较基线 `d8894d429ebe0915e377513a637b5dfc0fc7ea1a`，本次主要审查增量 `abf46cab699f07214af07038b0ae5a22b1389a2d..12e5128`。实际读取项目 AGENTS.md、当前 PR Review Prompt、已确认 intent/spec/plan 和旧全 PR 审查 `evidence/pr43-review-abf46ca.md`。这是该全 PR 审查后的只读检查点，不冒称重新审遍全 PR 的 648 个变化文件或通过全部验收。未运行 pytest、native 工具、包构建或业务客户端；只新增本文，无产品修改、PR 写入、合并或发布。

## 新确认的问题及依据

### N1 · P1 · 上传队列锁超时逸出响应后台任务，合法后续上传发生 HTTP 断连

位置：`src/smm_local/managed_document_uploads.py:183–200`；`src/smm_local/archive_protocol.py:107–125`；`src/smm_hub/document_api.py:80–84`。

每次 commit 均安排一个 `run_pending` 后台调用。该调用在整个队列消费/内容处理期间持 `upload-queue.lock`；另一调用争用该锁时使用默认 5 秒获取期限。锁获取发生在内部处理异常捕获之外，超时抛出的 RuntimeError 可以直接逸出 Starlette 响应后台任务。

**原始证据直接支持，未采用主 Agent 判断代替核实：**

- 两次 abf46ca 正式普通 CI 的 Windows JUnit 均出现 `test_document_formats_remote_original::test_pure_hub_original_downloads_via_local_cli_http_and_stdio` 的 `httpx.RemoteProtocolError: Server disconnected without sending a response`。原栈位于准备上传路径，尚未进入原件路由读取断言。它不能证明 original 读取算法错误，也不能算这项 Windows 业务已通过。
- 补充 Windows 原件 `.acceptance-local/008/windows-original-disconnect-20261126/opened/diagnostics/test_pure_hub_original_downloa0/world/hub/server-1.stderr` **开头第一份 traceback**，先是 `archive_protocol.py:117` 的 `msvcrt.locking(...LK_NBLCK...)` PermissionError，随后在 `managed_document_uploads.py:186` 获取 `upload-queue.lock` 时，经 `archive_protocol.py:124` 变成“上传控制正在处理其他操作，请稍后重试”。栈明确经过 `responses.py → background.py → run_pending`，不是观察器的 worker 数量断言，也不是 OCR 组件缺失。后续同类异常仍在原日志。
- 本次独立核对补充诊断包 SHA、ZIP CRC、25 份原始日志摘要，以及 273 个源文件的 Git abf46ca / tar / runner 回传清单逐项摘要一致。实际选择命令只运行上述新 remote-original 项；退出 1、未超时、cleanup_errors 空。管理员组件复现不能替代 E1-win 标准用户或 H-win 服务身份验收。

影响：合法连续/重叠的管理上传会触发后台协调器异常，并使随后请求以网络断连结束；普通用户无法可靠完成应支持的上传准备流程。违反 B1 的可用纳入入口及 B9 持久、有界队列的行为要求，关联 A1/A7/A12。当前日志足以确认超时逸出与该次断连，不足以证明所有上传必现、队列永久死锁、锁持有者具体调度顺序或数据已经损坏；本报告不作这些推断。

建议为队列协调器提供安全的重复唤醒/已有消费者处理，避免正常争用以未处理后台异常结束连接，并保留已提交任务的持久可见性及恢复语义。通过条件应包含真实 Windows 多次合法 commit、跨越 5 秒内容任务的队列争用、逐资料终态/检索/原件完整及服务后续请求可用；不能以吞异常或把测试改 skip/xfail 关闭问题。**本轮只审查，不实施、不专跑。** `windows-upload-queue-diagnostic.json` 已准确将该项公开为新问题待修；不是本次 merged-header 补丁引入。

## 原遗留项与本次关闭项

| 旧项 | 当前独立核对 | 结论及适度处理 |
|---|---|---|
| F1 / P1：失效、已提交未发布候选的 canonical 字节不回收 | `document_snapshots.py:50–62,79,118–122` 仍遍历所有 raw/results 并仅扣曾发布 ledger；替代 CID 只改状态。`document_transfers.py:63–89` 明确保留 canonical，只删除过期 incoming；路径/资料库删除仍仅撤来源/资格及 FTS | **仍成立**。未重做满额试验；源码足以证实回收分支缺失。按 B5/B9 补最后用途/活跃分配感知 GC，不能 TTL 删除合法失败候选。 |
| F2 / P1：路径 refresh 发布拒绝缺失败终态 | `documents.py:428` 已置 refreshing；`:429–433` 只包扫描，未包 `_publish`；`:459` 的 `Snapshots.publish` 在冻结配置变化时由 `document_snapshots.py:141` 抛错，`:482` 来源终态写入因此不执行。已有 `fail_current` 未接此路径 | **仍成立**。来源/attempt 会残留等待发布，需按批次/CID/AID CAS 收尾并公开原因。不是声称新结果已错误发布；未执行保留取消断言。 |
| F3 / P2：左侧跨入的合并表头被漏掉 | 新 `_covers_columns` 按主格真实 column_span 判断相交；merged_into 仅占自己的坐标，table 和 hit fallback 两处共用；原件及真实响应核验见下文 | **限定关闭**。仅本次两端 Mac ASGI / DOCX/XLSX / 普通全局 / 三档头长专项；不推成整个 A2/A3/A9 通过。 |
| F4 / P2：外部来源“文件状态”缺当前候选/重试值 | Local HTML:141 仍只显示 path/status/version/error；API `documents.files` 有详细快照字段，而 nativeDetails 仅在上传资料库使用 | **仍成立**。用户可改用 CLI files/API 取得 CID/AID/V/P，因此是局部 Web 信息不足与状态误读，非所有入口阻断。应在该处显示 latest_attempt/published_snapshot/retry_target 并指向显式重试。 |
| F5 / P2：活跃服务 CLI 内容任务交接未实现 | PLAN:75 仍要求交同 state 服务 worker；`hub_admin.py:435–445` 直接分派，`document_cli.py` 构造 HubDocuments；`HubDocuments.reprocess:338–343` 和 refresh:368 仍在调用 CLI 流程启动 process | **仍成立，已说明的计划未完成**。短 guard/单槽不改变实际任务账户；补服务交接并验证服务/OCR 子进程身份，不能前景 CLI 成功替代 H。 |

旧审查对 managed 上传/同步缓存 reprocess 发布失败 CAS 收尾、纯 Hub original 路由及处理版本隔离的限定关闭不因本次检查点被撤销；相关产品文件在本增量没有改动，且本次相关回归有原始退出记录。没有重新逐件核它们全部历史原件，因此不重授整域通过。

维护者明确保留的在途来源取消、C1 新候选五项设计/实现/绑定缺口，以及共享 Windows 字符串 argv 审计缺口仍保留。没有修改 skip/xfail、没有专跑、没有把“保留”写成 SPEC 豁免。最初三份未跟踪 `test_document_formats_active_source.py`、`test_document_formats_upload_restart_c1.py`、`document_formats_lifecycle_hook.py` 未计作正式可执行候选；审查期间其他 Agent 新增的 upload_queue 草稿/原生投影也不在本报告的已提交绑定及通过范围。

## 合并表头修复：设计、红绿灯与独立原件复核

SPEC B2 要求保留 Office 合并跨度，不复制主值填格；B8/A9 要求相关列真实表头、精确定位和预算。这足以支持本次具体修复，不需要改变已确认规格。增量仅一个产品文件 `document_results.py` 的 10 行差异；解析器、正文 cells 按锚点选择、格式、协议和额度没有变动。PLAN:309 已记录方法、证据、平台限制及 N1，未发现本增量未说明的实现偏差。

`_covers_columns` 正常窗和超额 fallback 均使用真实列相交；union 仍按行列唯一格计 1000/16000 预算。新测试不从产品输出推导预期：独立源直接指定 A1:N1、O/P 独立头、M243 命中，普通/全局 × DOCX/XLSX × 64/2001/16000 Unicode 码点 × 每组两份，每端 24 个目标。使用真实 FastAPI TestClient 管理上传和内容 worker，随后删管理源文件再查询；这不是实际 TCP/TLS/浏览器/系统服务验证。

本次实际独立核对：

1. 两端全部 48 份原件以标准库 ZIP/XML 打开：DOCX 确有 250 行、gridSpan=14 和 tblHeader；XLSX 确有 A1:N1 合并，源实际非空格及 O/P/M243 值正确。逐源格核真值、结果的完整坐标集合/值/跨度/类型/位置，逐份全文和下载字节一致；未调用 SMM 解析器或测试生成函数作预期。
2. 重新计算红灯 Local 273 件/1,464,061 字节、Hub 276 件/1,731,503 字节；绿灯 Local 491 件/1,903,610 字节、Hub 494 件/2,345,589 字节，所有 artifact SHA 均相符。所有绿灯当前 bindings（92/94）与盘上文件相符；62 个产品绑定又与 `git show HEAD` 相符，红产品与 abf46ca 相符，红绿 24 个测试绑定完全相同且与 HEAD 提交字节相符。未混入未跟踪草稿。
3. 实读原 stdout：红灯 Local 1 failed / 9.69s、Hub 1 failed / 12.00s，都是 expected 3 个头实际 2 个，漏左侧 A1；真实 HTTP search 中 M243、后列窗口和两个 O/P 头已存在，非准备/环境失败。红灯在首个目标即停，不能把其余设计断言说成红灯已全部实际执行。
4. 绿灯 Local 主项 1 passed / 12.21s，相关 7 passed / 96.33s（table_context、remote_original）；Hub 主项 1 passed / 20.31s，相关 10 passed / 68.06s（table_preview、multiple_hits、version_isolation）；对应 execution exit0。相关回归只是记录中的组，不是全量或正式 E/H/X。
5. 逐两端各 168 条查询/读取/原件 HTTP 记录重新核：24 search、56 成功 text、48 成功 table、24 original、16 个明确 400 超额拒绝。所有成功读取的 ID/V/P/rawSHA/resultSHA/profile 与保存快照匹配；正文准确区间、窗口源格及完整必要表头集合一致。64/2001 档默认后列窗含 M243，2001 摘要截短并要求扩读；16000 头加命中明确拒绝且给原件指引，头行自身 16000 唯一格成功，O/P 窗不引入 A:N。两端各 24 完成事件和最终 guard 基线记录存在。
6. 实读四份独立 reviewer.txt 及 result：红灯各为 expected_failure，绿灯各为 passed，target_sha 精确对应被审结果，四份意见及请求 artifact SHA 完整。独立意见对真实来源/反例/预算/最终副作用的限制与原件相符；covers 为空，不代表 R008 已整体验收。

关键结果摘要：

| 原生记录 | 实际 SHA256 |
|---|---|
| red-sc9-merged-header-local-v1 | 144d9358b8e6f442065afc37b036faf74e3e85e3137ecc023ee5fee0e150f8dd |
| red-sc9-merged-header-hub-v1 | 4e72714b6302bb0dbb2ff1f2b1b51adcf23a9efa05dd07b5152c9034f2a4b88e |
| green-sc9-merged-header-local-v1 | eca5a7c21e0c1ad98ca2a2de3923b28a4878e943324fb89f8a1ac244b6555d13 |
| green-sc9-merged-header-hub-v1 | a361e41740db0e7032fefcfc1f77a588df25d0f9501b5b35e49244402978d365 |
| review-merged-header-local-green-v1 | a08effa5bfbb6f1368f01084065d8b80915d6270242146de2cd3fb7b9f8cd945 |
| review-merged-header-hub-green-v1 | 8df34ff4eb9890674631e5e2a38da87e7dc4fa96259ccc83723681264916822f |

公开 `merged-column-header-development.json` 的上述计数、result/review SHA、product SHA 与实物一致；未把 scoped passed 写成 SC9/A9/R008 passed。

## 构建、CI 与公开口径

本次只读打开私有 build/verification.json 指定的两 wheel，独立复算长度/摘要与 ZIP CRC，再逐 Local 46、Hub 47 个声明源码成员与当前源字节比较（Hub `_archive` 映射回对应 smm_local 源）。全部相符；两包均含本次 `document_results.py` SHA `f9063b07a980e0e4e3644ec104774ca8705f23fa0595285f7564e3a070a25350`。Local wheel SHA `0b2d6a7378e236eb2bc586a85ebe20f622fc14d1a7e9276dbde1ed1cce8723bb`，Hub wheel SHA `779faeeb869bcf4a73b6a276530673b98c9b8b573b197cc4592a1bc0921613ea`。这证明已保存构建的源码一致，未执行安装或安装后业务，不扩成包验收。

独立核 `.acceptance-local/008/platform-audit-20261126/ci-abf46ca` 两 run（45759887102 / 45759878324）全部六份 official.zip：摘要匹配公开/inspection 记录、CRC 正常，外置 test-results.xml 与 ZIP 内 XML 原字节一致，重新解析每个 testcase 得：

| 两 run 各自平台 | passed | skipped | failed | errors |
|---|---:|---:|---:|---:|
| macOS 15 | 459 | 68 | 0 | 0 |
| Ubuntu 24.04 | 459 | 68 | 0 | 0 |
| Windows 2022 | 457 | 67 | 3 | 0 |

Windows 两个旧失败确为 restart[local/hub] 的 worker observed0/expected2；第三个确为上述 remote-original 上传准备断连。`ci-regression-abf46ca.json` 分别列出 retained/new，`windows-upload-queue-diagnostic.json` 承认新缺陷和管理员补充诊断范围，公开口径准确。这两 run 都是 **abf46ca，早于本次表头补丁**；本轮未取得/核验 12e5128 最终三 OS CI，不以 abf 结果代替。68/67 skip 均不计作 E/H、OCR/浏览器/配置终态实际通过。

## Intent 角色及入口回放

沿当前可见文档/源码回放；未实际操作浏览器或 CLI。本次没有引入新命令或入口，故核入口链对该修复的适用性，并保留旧审查的范围限制。

| 角色与期望结果 | 当前可见起点及下一跳 | 信息充分性与实际限制 |
|---|---|---|
| 本机使用者按项目纳入三格式并核原件 | README:61–67 明示开发中、同构建独立包和适用格式 → TRIAL_GUIDE:153–180 安装、材料清单取绝对 OCR 路径、revision/check → :188–210 add/refresh/files/search/read/table/original | ID/ref/table_id、坐标及路径来源可见；本修复直接改善后列读表。路径失败终态及文件状态仍受 F2/F4，三平台完整业务未证。 |
| Web 使用者上传或纳入路径并确认结果 | README:65 指网页/指南 → 指南:184–186、212 起的上传/处理/读表/下载说明 → Local 文档来源与项目资料库、reader；Hub 认证项目资料页 | 正常能力和“收到不等于可检索”可发现；Local 来源文件状态缺详细 retry 目标是已确认局部缺口。Windows 上传入口 N1 另影响完成操作。 |
| Hub 维护者准备创建端及服务 | README 的 Hub/007/008 入口 → 指南给 HTTPS/hub-token、实际 state-dir、Hub OCR 前缀及实际身份检查 | 凭据、目录和依赖可取得；服务 CLI 身份交接未实施 F5，不能以交互 check 宣称服务就绪。 |
| 查询同步资料的用户/Agent | README 同步默认关闭与创建端责任 → 检索 Skill:58–72 list 项目/来源 → search 精确 ref → read text/table/original-info，再交认证 CLI/API 下载 | 表格参数、精确引用、处理/OCR/缓存限制可达；本次只测创建端 ASGI 表头，不扩大为全部联合/一层/离线/stdio。 |
| 维护者复核交付 | README:67 SPEC/PLAN/证据 → scripts/acceptance/README 的普通回归、材料准备、组件/独立包/E/H/X、回收入口 → pending | 能区分实际证据和未完成门；普通 CI/构建/本 TC 不足以通过整个平台矩阵，保留项不是豁免。 |

## SPEC 逐条增量判断

| 验收条件 | 当前可核证据与结论 |
|---|---|
| A1 入口/创建端 | 本次两端上传/查询限定路径有实际结果；F2/F4/N1 及完整 E/H 尚未关闭。 |
| A2 DOCX | 本次 24 DOCX 的合并头/全源格定位子域正确；其余部件/平台完整性沿旧证据及缺口，不判整项。 |
| A3 XLSX | 本次 24 XLSX 合并跨度、后列上下文/字节正确；隐藏/公式等完整格式范围与 E/H 不由此验收。 |
| A4 原生/混合 PDF | 本增量无新 PDF 主项；既有专项及平台/资源缺口保留。 |
| A5 OCR | 本次表头主项不用 OCR；不得由配置环境或 skip 认领三 OS/服务 OCR 质量通过。 |
| A6 直接索引 | 未改接收协议/解析路径；本次非 X1 六方向，完整无依赖接收矩阵仍缺。 |
| A7 成套/并发 | CID/V/P/SHA/profile 在本次读取一致；F2/N1、C1 五项及全并发/恢复缺口仍在。 |
| A8 生命周期 | 删除管理源后保存快照可读已核；F1/F2/F4、保留取消/最后授权等不由此关闭。 |
| A9 查询和原件 | F3 合并列头专项关闭；既有路由/版本隔离限定结论保持，完整 scope/network/Web/重启/平台入口仍不足。 |
| A10 有界/隔离 | 本次摘要/表格 Unicode 预算、guard 最终事件可核；F1、完整资源/5秒槽位及各 OS 服务监督仍缺。 |
| A11 兼容/发现 | 本次 wheel 精确源字节及入口链可核；F4、最终最低 Python 三平台安装业务/旧档案完整回归仍不齐。 |
| A12 平台/证据 | 原生 TDD/独立意见/公开证据限定一致；E1 三格/H 三格/X1 六方向、完整 C1 与最终 HEAD CI/安装链未全齐，R008 未完成。 |

维持 PR 草稿和 **needs_revision**。合并表头补丁可保留当前 scoped passed；其余实际缺陷、计划未完成项及未验证矩阵应分别修复或补证，当前没有 merge/release 授权。
