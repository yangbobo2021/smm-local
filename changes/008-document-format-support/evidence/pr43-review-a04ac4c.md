# PR #43 证据检查点独立复审：a04ac4c

结论：**本次证据增量未发现新增的实质性问题；PR 整体仍为 needs_revision，SC1/R008 未完成。** 六份普通 CI 原件、路径刷新保留记录和 Windows 临时目录诊断的公开表述与本轮实际读取的原件相符。没有证据可以关闭既有产品缺口、维护者保留项或完整平台验收。

## 范围、依据与未核边界

复审严格冻结于 `a04ac4cd987a29de9970071060df94de0ad2d5d5`，比较区间为 `7c2348a8b1dfa9550ce024d1cc42b25eaaaa3fb3..a04ac4c`；全 PR 基线仍是 `d8894d429ebe0915e377513a637b5dfc0fc7ea1a`。增量恰为 25 份文档/原生历史投影，产品、测试、脚本没有提交差异。本轮是证据检查点增量复审，**不是全 PR 复验，也不是重新执行验收**。既有整体问题与此前限定通过依据引用 `changes/008-document-format-support/evidence/pr43-review-7c2348a.md`，没有重新授予全部历史证据通过。

已读 AGENTS.md、`changes/_templates/pr-review.prompt.md`、008 已确认 intent/spec/plan 的相关约束、25 份增量、前检查点全文、相关原生定义/结果/独立意见及私有原件。冻结 SPEC SHA256 为 `e6ba46812b4083b20820278005bb3cb0d32764372d8c8ef8e23b2e638ddfea28`；实际定义是 `.acceptance/native-v1/AT-SMM-008/definitions/000001.json`，SHA256 `3cb55956c42617a68775c52cd0dcfbfc97d713fb2e36fc671328691f1e6bcf3d`。本轮涉及的原生投影、设计、红灯与复审均对应这一版本。

只使用 Git 及标准库读取、摘要、ZIP/tar/XML/JSON 静态核对；没有启动产品、pytest/native、构建、服务、CI、远程或浏览器，没有向 GitHub 写入或提交。仅新建本文。完整性核对不等同于对每份业务原件重新建立独立真值：本轮没有重新核全部 Word/Excel/PDF 的逐格/全文真值、全部历史浏览器轨迹、完整 E/H/X、最低版本安装或清理链。

主 Agent 在复审过程中告知维护者随后确认了一次完整重采样澄清；该后续授权和工作区/提交不属于 a04ac4c。本文下述“待确认”“当前 PLAN”均限定为 a04ac4c 当时的状态；不会用后续行为变更反推旧测试已经有效，亦不评判后续实现。

## Findings 与历史问题

### 本轮新增发现

无新增的、有充分依据的产品或证据发布问题。新增 Windows CI 失败是**新的实际观察、原因未确认**，不是已经定位的产品缺陷，也不是维护者已保留的两项 argv 审计失败；公开索引没有将它伪装为通过或保留豁免。

### 既有问题及适用范围

| 项目 | a04ac4c 判断与影响 |
|---|---|
| 旧 F1 / P1：失效已 commit、未发布 canonical 候选缺安全 GC | 产品与 7c2348a 相同，仍未关闭；会影响暂存容量。raw-only 未 commit TTL 的限定修复不能替代此项。 |
| 旧 F2 / P1：路径 refresh 发布被拒后缺终态收尾 | 新增 Local v3 与 Hub v2 原件支持已有问题：真实配置变更后拒绝发布，来源仍 refreshing。候选补丁没有进入产品，仍未关闭。 |
| 旧 F4 / P2：路径 Web 文件详情不足 | 沿用前检查点；API/CLI 有可用路径，不能夸大为所有入口无法操作。当前增量未改善该局部信息缺口。 |
| 旧 F5 / P2：活跃服务 CLI 未交服务 worker | Hub 路径 v2 实际为前景 CLI，不能视作服务身份通过。仍未关闭。 |
| 既有 N2 / P1：同父目录多 SQLite 档案队列丢唤醒静态风险 | 维护者保留，尚未复现；四个单档案队列专项及普通 CI 通过不能关闭它。仍保留原生 needs_revision/design。 |
| 已有关闭或缓解的子项 | 合并表头、纯 Hub 原件路由、处理版本隔离及单档案队列改善的既有限定结论保留；没有因历史报告文字而重新把这些限定改善列成同流程仍失败。 |

本轮不提出继续修复或专跑维护者明确保留的在途取消、C1 五项、共享字符串 argv、跨档案队列和路径刷新 Hub 搜索封套。保留决定不构成 SPEC 豁免，也不能将对应 TC、SC 或 R008 假关闭。其后若恢复工作，应以相应有效版本的设计/实现/独立审查和实际结果判定，不能靠本报告签结。

## PLAN 与实际增量一致性

a04ac4c 的 PLAN 追加记录（313–320 行）准确区分：路径 TC 的分版失败/复审、候选撤回、六份普通 CI、Windows 环境诊断与设计冲突。没有产品方案暗中落地，也没有修改冻结 SPEC 或降低验收。旧 PLAN 第 91 行规定访问拒绝/观察盲区时停止，第 244 行仅容忍正常清理 ENOENT、权限异常仍报错；Windows 原设计强制暂态 PermissionError 后成功，与该版本约定不一致。将其记为 needs_revision/design 而先提澄清，符合 AGENTS 的行为变更先确认要求。

路径候选产品补丁仅存为 `retained-candidates/path-finalization-product-v1.patch.txt`：9768 字节，SHA256 `6fbfd74404a3603cd08615dcdd875de64379b4575032bb6d132d9bbc36f56112`。测试惰性文本 `path-finalization-test-v3.py.txt` 为 24286 字节，SHA256 `e3263f4ac03593d88219fa529ca9796c4a89489d5cb52e4dd10747783049a428`，与 v3 冻结测试字节相同。两者均与 `path-finalization-retained.json` 原摘要一致。a04ac4c 的 `src/smm_local/documents.py:418–433,459,482` 仍为未修路径；产品与 7c2348a 的 Git 字节相同，因此不能将惰性 patch 当已应用。

Git 对象检查确认五份未就绪 Python 文件均不在 a04ac4c 树中：`document_formats_lifecycle_hook.py`、`test_document_formats_active_source.py`、`test_document_formats_upload_restart_c1.py`、`test_document_formats_path_finalization.py`、`test_document_formats_live_temporary.py`。本轮未修改它们。公开保留文本不构成可执行测试交付。

## 实际证据复核

### 六份普通 CI

原件位于 `.acceptance-local/008/platform-audit-20261126/ci-7c2348a/`。逐份打开官方 ZIP，重新计算 SHA256/长度、检验 CRC，并将归档内 `test-results.xml` 与旁存 XML 逐字比较、实际解析全部 testcase；结果与每份 inspection、私有 summary、公开 `ci-regression-7c2348a.json` 一致。保存的两份官方 artifact metadata 中 ID/name/head_sha/size/digest 全部对应；六份摘要与官方保存 digest 一致。本轮没有联网重新查询官方服务，run 的 push/PR 名称沿已保存归档命名及公开记录，未另行核线上事件元数据。

| 已保存 run / 平台 | JUnit tests / passed / failed / errors / skipped | ZIP 字节 |
|---|---|---|
| 45769770076 / Windows | 533 / 464 / 2 / 0 / 67 | 16151 |
| 45769770076 / macOS | 533 / 465 / 0 / 0 / 68 | 13529 |
| 45769770076 / Ubuntu | 533 / 465 / 0 / 0 / 68 | 13190 |
| 45769761597 / Windows | 533 / 463 / 3 / 0 / 67 | 16610 |
| 45769761597 / macOS | 533 / 465 / 0 / 0 / 68 | 13421 |
| 45769761597 / Ubuntu | 533 / 465 / 0 / 0 / 68 | 13265 |

六份各有 4 队列、1 远端原件、2 合并表头实际 passed，共 42 实例，无将 skip 算 passed。Windows 两轮均在 Local/Hub restart 的 subprocess 审计 `0 == 2` 失败；push 另有 staging-dedup 缺 OCR 预期收到 pdf-* 目录 WinError5 的实际失败，PR 同项实际 passed。逐份 failure 文本也与 inspection 相同。后者成功不能抹去前者失败，不能与旧队列 HTTP 断连混同，也不证明最低 Python/独立安装/普通身份/服务/E/H/X。

### 路径刷新历史链

17 个新增原生公开投影（3 设计、7 匹配、7 复审）都能打开对应私有 result，result SHA、定义 SHA、请求 ID、场景、操作及状态相符；其已列 artifacts 摘要也相符。六份路径 red 的全部 artifacts 分别为 Local v1/v2/v3 各 262、Hub v1 48、v2 326、v3 61，逐份可读且 SHA 一致；每版 62 产品绑定都与 a04ac4c Git 字节相同，24 测试绑定都与各自冻结 source 副本相同，case_design 摘要匹配。此处证明证据身份与可读取性，不冒称本轮逐份重验所有业务真值。

复审状态实际为：v1 Local needs_revision/implementation、Hub needs_revision/design；v2 两端 expected_failure；v3 Local expected_failure、Hub needs_revision/implementation。读取原 stdout/门/响应确认 Local v3 首目标真实结果 ready、冻结 revision1，变更到 revision2 后 HTTP400 拒绝发布，来源仍 refreshing，在测试293行失败；Hub v2 同类情况由真实 CLI 执行，exit2、来源仍 refreshing，在265行失败。它们只证明已到达的首目标流程，不证明其后资格/缓存重试/最终全集或其余目标通过。

Hub v3 在额外 control 准备时，测试把搜索根封套的 `hub_id` 当 hit 字段，127 行 KeyError，未进入目标发布门；不能把 v2 有效业务红灯移为 v3 实测结论，也不要求产品重复提供未承诺字段。公开历史如实保留。

候选 green result SHA `39fa46a15fe4e345aa3a709c14b27aa20c6b2d712c3f06c0dd9d2ac6989ed590` 实为 blocked；963 个 artifacts 全部 SHA 可核。主项 1 failed / 14.04s，另行相关回归 15 passed / 87.15s。独立诊断原件 SHA `79f242ddf0b77e1f331f20a598fe4b5b24a93f32c297cdcbe116b3a0e8c95e85` 与 note 一致，结论 needs_revision/implementation；note 的 registered=false 与没有正式 green review 相符。15 回归通过不能替代 blocked 主项。

### Windows 临时目录诊断

实读普通 RemoveDirectory 和 disposition-v2 两份 observations：普通删除后是 FileNotFoundError；真实 FileDispositionInfo 删除待定、句柄未关闭时 scandir/缓存 walk 观察 WinError5，最后句柄关闭后为缺失。它证明相同可观察错误机制，不能证明原 CI 发生了完全相同的因果链。

`red-sc10-live-temp-v1/result.json` 实际 SHA `1491a0a29eccd58fcf5a21aa9a2393dd01317b94e36a92fd1d00ad00af190c1f`；26 项 artifacts、4 个冻结测试绑定、3 个产品 Git 绑定及 case_design 摘要全部相符。source.tar 含 5 份源码和自有 manifest，逐成员与 manifest 一致；回收 5 项 checksums 全部相符。JUnit 为 1 测试、1 失败、0 error/skip；stdout 与 native run.stdout 原字节相同，gb18030 解码与 UTF-8 JUnit/JSON一致。实际链为测试159 → `temporary_bytes` → 真 os.walk onerror → PermissionError/WinError5，非编码故障。

独立 inbox 与正式 review 同 ID；正式 review SHA `74a1308c54ba2cd2617474c445180ec5540e455eafb456e1dedd7c472a676bf2`，target 精确对应上述 red，判 needs_revision/design、covers=[]。公开诊断将执行状态 red_observed 与审查判定分开，是正确的；**a04ac4c 依据下不是可授权产品修改的 expected_failure**。源码 `document_supervisor.py:18–30` 仅容忍 FileNotFoundError，其权限错误抛出符合该版 PLAN。

实际已执行持续拒绝（原生和产品均 WinError32）、根缺失、256MiB 及 +1、普通计数；错误记录仅首个 onerror。37 字节暂态成功值、第二目录后续遍历及最终 scan/assertion 未到达，不能算通过。finally 记录句柄全关、Timer 结束无错误、保留文件未变，与公开 JSON 相符。此项仅 Windows11 SSH 管理员源码采样组件，不认完整任务入口、任务树/槽位恢复、普通身份/服务或 E/H/X。

## Intent 角色及入口静态回放

以下读取的是 a04ac4c 的可见内容，未实际操作 CLI/浏览器。此增量没有新增产品动作或输入值。

| 角色及要达到的结果 | 可见主入口与下一步 | 局部充分性和整体边界 |
|---|---|---|
| Local 使用者纳入 DOCX/XLSX/PDF、检索并核原件 | README:61–67 说明开发中、创建端处理及 008 指南；指南:153–208 给同构建 wheel、独立档案、OCR材料清单/绝对路径、revision/check、add 返回 source-id、项目列表与搜索 reference/table_id | 能发现并开始；收到文件与已处理/可检索明确区分。整体完成仍受 F2/F4/N2 与平台缺口限制。 |
| Hub 维护者准备所在端并处理资料 | 同指南:168,180 说明实际 state-dir、所在端配置和真实执行身份；本机路径用 Hub CLI，网页上传本地文件字节 | 本轮路径历史纠正了不存在 HTTP 路径入口的假预期。F5 未完成，前景 CLI 成功不代表服务 worker。 |
| Web 使用者判断状态、读取表格/下载 | README:65 → 指南:184–186,212–218，给项目资料/reader入口、处理状态、命中默认窗口与原件下载 | 必要参数及概念有说明；路径文件局部详情历史缺口仍在，不宣称全部真实浏览器流程可完成。 |
| Agent/同步使用者按出处读取 | README Agent入口 → `skills/smm-search/SKILL.md:58–72`：实际 schema、真实项目/返回 reference、text/table/original-info、转 CLI/认证 API 下载 | 只读边界、坐标和引用来源可见；本轮不重新认领全 scope/同步/原件入口矩阵。 |
| 维护者复核证据与当前交付状态 | README:67 的 SPEC/PLAN/证据 → `scripts/acceptance/README.md:3–32` → pending-verification 及各证据文件 | 有可达的普通回归/组件/安装/E/H/X/回收区分；本轮索引与真实结果一致，不能据目录存在认验收通过。 |

## SPEC 逐项判断

| 条件 | 本次证据增量能支持的结论 |
|---|---|
| A1 入口/创建端 | 路径现有入口及失败终态有更精确分版证据；F2、F4、N2和完整入口/身份仍缺，不关闭 SC1。 |
| A2 DOCX | 没有新的完整 DOCX 验收；路径 ready 输入及已有专项 CI不替代全部部件/平台。 |
| A3 XLSX | 没有新的完整 XLSX 验收；保持前检查点限定结论。 |
| A4 原生/混合 PDF | staging失败及环境诊断不授予 PDF处理质量/覆盖通过。 |
| A5 OCR | WinError5没有放宽 OCR断言；三OS/服务的完整质量故障门仍缺。 |
| A6 直接索引 | 远端原件专项六份 CI passed可保存，不能替代无依赖接收/零处理/X六方向。 |
| A7 成套/并发 | 单档案队列专项六份 CI passed，但跨档案/C1/路径收尾未关闭。 |
| A8 生命周期 | 路径 F2确有业务失败证据；候选未应用、在途取消保留，不认完整生命周期。 |
| A9 查询/原件 | 合并表头/远端原件专项CI均实际通过；Hub v3是测试封套错误，无新的产品缺口判定或整体通过。 |
| A10 有界/隔离 | Windows采样有真实错误/边界/清理组件事实，设计判定不通过；GC、完整预算、任务树/五秒恢复未闭环。 |
| A11 兼容/发现 | 静态入口链可发现/开始；普通CI已回收且Windows仍失败，最低三平台安装/完整发现未补齐。 |
| A12 平台/证据 | 本次原件和投影可读且摘要一致；E三格/H三格/X六方向、完整C1及最终独立交付仍未完成。 |

## 索引、PR 正文与公开脱敏

冻结 pending-verification 的 latest_ordinary_ci/current_ci_checkpoint 均更新到 7c2348a，两份数字一致；旧 abf CI移入 historical 键。windows_upload_queue_defect 不再把单档案限定修复写成 fix pending；合并表头旧结论移入 historical_other_findings，并有 current_other_findings 明确仍缺项。路径记录明确未修、候选未应用；Windows临时目录条目标明未保留、未定根因和设计冲突。PLAN/公开诊断/原生结论没有实质矛盾。

`pr43-review-7c2348a.md` 中“当轮未取得该CI”“当轮路径尚未执行”和旧索引陈旧建议，属于其7c检查点当时的事实。该历史意见原样保存是正确的；a04 的 CI/路径记录与索引更新补充后续事实，不应把它读作 a04当前状态，也不应重写旧意见抹掉历史。

本轮读取的 PR 正文原件是 `.acceptance-local/008/windows-temp-observation-20261126/pr-body-next.md`，SHA256 `c2b57c3959a19a59e336940d3173449fc2bcade8a5c61e6b684d8e68f983d89f`。其 a04 仅证据、产品等同7c、草稿/R008未完成、needs_revision、候选撤回和五类维护者保留项表述，与上述证据一致。“重采样待确认”是 a04当时状态；后续授权不使这份历史正文错误。本轮未访问线上 PR，不能独立确认该本地正文是否已经完整发布、当前在线正文或 GitHub draft标志。

25 份公开增量人工结构检查及常见凭据/私钥模式检查未发现实值凭据、私钥或原始数据库/trace被提交。公开 native文件只给结果定位/摘要/状态，不含私有业务负载；候选是合成测试/产品差异文本，且用途明确为惰性历史。摘要不替代私有原件，本轮已实际打开关联原件；此检查也不是全仓库秘密扫描。

**最终判定：证据检查点增量记录可信，未发现新增实质问题；既有修复只保留各自限定范围，PR #43 仍 needs_revision，R008 未完成。**
