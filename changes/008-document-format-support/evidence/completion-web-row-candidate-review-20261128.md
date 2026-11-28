# SC1 网页上传 web-row-v1 独立候选复审

本轮本机、Hub 两个候选均 **passed，无需修订**。此结论只适用于 `TC-008-web-native-upload`、`covers: [creator-web-native-upload]`，评的是当前网页上传候选与探针，不是整个 SC1、008、三 OS 源码 CI 或 E/H/X 验收通过。旧失败和旧 blocked 记录均保留。未把当前 installed 脚本、日志测试纳入本次结论。

## 版本、授权边界与需求推导

按 `<LOCAL_USER>/.agents/skills/app-delivery-acceptance-native/references/execution/reviewer.md` 独立复审。产品、测试和原始证据只读；只写本轮两份 review-inbox JSON 与本 MD。重新打开 AGENTS.md、changes/008-document-format-support/intent.md、spec.md、plan.md、tests/conftest.py、tests/test_document_formats_web_uploads.py，而非继承上轮 passed。

定义 `<TASK_WORKTREE>/.acceptance/native-v1/AT-SMM-008/definitions/000003.json` 实际 SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。本子项原文：“两端支持新建普通/全局项目、明确纳入路径及网页选择/拖入，并显示真实处理状态，文档同步默认关闭。”SPEC 第 9、59、63–79、97、103、181 行支持项目、三原生格式、真实处理/发布状态、独立资料及同步默认值的判据。独立原件、正文、表格和身份控制用于证明上传确实对应正确资料及状态；这些是证据的判别力，不是另加业务行为。

自然设计仍为 `case-design/design-completion-sc1-web-ui-v1/result.json`，SHA256 `c771444d5a1556f8d0d444715ceed8622a38f32f9f78b806d643206c084a9090`。每端普通项目 chooser、全局项目 drop 各两轮，每轮 DOCX/XLSX/原生 PDF 三份，合计每端 12 份。显式路径、失败/替换、投影拒绝、陈旧版本和其他 creator 子项依然有各自检查，不把本候选扩写成这些场景的证据。没有要求新增等价样本或设计未要求的完整交叉积。

匹配 `match-completion-sc1-web-row-v1/result.json` SHA256 `c5b84f0cfd8d5451c5b8d8a1b3c238f03f586097aa48f6104da18823a0e0f3fd`；运行准备 `runtime-completion-sc1-web-row-v1/result.json` SHA256 `e9a55ea1a9b1d0b8a994cba5c499624937c022b6c0ed7b0a10d0eb5fc4b99d32`。准备阶段原始 stdout 为 7 tests collected、stderr 空、exit 0，仅视作实际收集成功。当前测试文件 SHA256 `45f02f8dc646986bf3414a5032b963f23f7c2416adf5eb524d2f330d7ec45671`。

| 当前 debug | result.json 实际 SHA256 |
| --- | --- |
| debug-completion-sc1-web-row-local-v1 | de6f712a67b199709077439a9632cc29cb3ab5970538c61d1bd37bab30ad1b2d |
| debug-completion-sc1-web-row-hub-v1 | d7c96dca0d48ba930fe061952334ff8910beee273ea148ac2190322afca76058 |

## 旧 source-032 失败的实际根因证据

实际读取 `<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/source-032-linux-triage/{inspection.json,diagnosis.json,run.stdout,run.stderr,result.json,case-map.json,junit.xml}`，并实际打开该目录下 `web-hub/hub-failed.png` 和完整 `web-hub/hub-failed-trace.zip`。源 commit `0320622918bcca3779d7d9ba3b4b7f32a584d91d`、run 46107496051 的 Linux 原 stdout 是 **357 passed / 1 failed / 15 skipped，2269.12s**，不是 passed。唯一失败是 Hub 网页测试旧 185 行调用旧 101 行，对独立 `inner_text()` 返回空串做 json.loads。

旧失败图实际所见：全局项目 #2 有六行，三旧 ready V1、三新 pending V0，详情折叠，上传回执存在。故该图不支持“文件丢失”解释。

旧 trace 实际 SHA256 `764489e572417349b3bcb0fe6aae194808eb0584cf88b2dd0403dcfddd33223a`。用匹配 trace v10 的当前 Playwright CLI 实际 open/action/snapshot，Linux、15.2 秒、475 动作、123 请求、无浏览器 error。关键动作不是只采信 diagnosis 摘要：

| 动作 | 实际返回/所见 |
| --- | --- |
| nmvy@13731 | details open 属性缺失 |
| nmvy@13733 | 实际点击 summary |
| nmvy@13735 | published_snapshot.innerText 返回字面 `null` |
| nmvy@13737 | latest_attempt.innerText 为有效 pending JSON，capture b388370cb3314092a2799532866a9655、attempt a873456b2e3a43e7b5a80072d7e62cd1 |
| nmvy@13741 | 期间响应回调后 retry_target.innerText 返回空串，但该 pre 节点的 textContent 仍为 `null` |

实际对 13737 与 13741 的 after DOM snapshot 取同一 DOCX `f06d23bb7c8f4924b93bc42bce8262ad`：前者 details.open=true，retry_target innerText/textContent 都是 `null`；后者 details.open=false，innerText 为空而 textContent 还是 `null`。六份资料及三面板数据仍在。这证明旧观察器跨多个浏览器回合遭遇轮询重绘关闭详情的竞态，不能据 JSONDecodeError 推断 stored JSON 坏了。Linux 官方 ZIP/AEAD/19 外层原件的全链路核验为主 Agent 已完成的前置；本 reviewer 独立打开的是上述原始 triage、PNG、完整 trace，不冒称在本次复审重做全外层解密链。

macOS 只实际核 `<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/source-ci-46107496051/macOS/authenticated-triage/inspection.json` 及其五份定向原件（case-map、junit、result、stdout、stderr），逐文件 SHA/长度匹配。其 stdout **356 passed / 2 failed / 15 skipped，2847.62s**，本机/Hub 都在同一旧 json.loads 行失败。inspection 状态 `authenticated_triage_subset_verified`，官方 artifact 15249792265、SHA `a93a117dc67f9d6d4f34dcb3adc825f1017af9b1d04e0b5548e58dfd91fda252`；raw tar 压缩流 299162609 字节、SHA `d707c318f7d3fb66517aa84fc6d7ccbd9f4be4f3b5d5cd5c17d4a4f73b5eb8ef`。这仅是定向认证原件，不是完整成员回收，也没有 Mac 失败原图/trace 可在本轮逐动作重建根因；同错误与 Linux 诊断相容，不把所有 OS 失败都宣称已证明同因或已经通过。

## 当前观察器与反控

对比上轮 web-ui-v3 冻结源码，逐函数/类 AST 核实：只改 `assert_ui_snapshot` 并新增 119–143 行自检，其余函数/类 AST 相同。所有每份资料、每种状态、全集、保留旧状态、独立正文/全表/原件及分块/身份控制都在。

当前 89–104 行重新定位唯一行，必要时真实点击展开。99–101 行在同一个 evaluate 回合保存 `row.isConnected`、当前 details.open、row.innerText、三个 data-native-detail 的 textContent；只有当前行未 connected 或详情未 open 才重开/重试，20 秒有界。105–114 行在退出循环后立即断言可见名称/格式/V/P/状态，并解析、完整比较三个 JSON；错误 JSON、错误 CID/AID/配置等不会被循环吞掉。published/latest/retry 各对象有独立预期，latest 仅按设计选取明确五个字段。

核当前 nativeDetails 的三个 pre 确实在同一个 details 内，没有隐藏分支。两份原始 debug 各 38 个 web-visible-row-snapshot（36 产品、2 自检）全部 connected=true/open=true；独立对每份产品快照做空白规范化后，三个 JSON 的完整文字都在**同一份** innerText 中。所以本轮不是读取关闭详情或隐藏文字冒充用户可见。textContent 仅避免跨回合读取，实际可见性仍由同回合 live DOM 与 innerText 证明。未凭空要求持续展开或消除全部轮询重绘的业务 SLA。

119–143 行在真实浏览器设置 DOM：首次 summary click 同步用 innerHTML 换成全新关闭行；观察器实际重开新一代行并通过。分别向三个面板注入 foreign capture_id，均要求立即 AssertionError；两 owner 原控制记录均 replaced/reopened=true、wrong_capture_panels_rejected=3。这覆盖本次已知失败的适用分支。

| 反例/前置状态 | 当前首拦截位置（tests/test_document_formats_web_uploads.py） |
| --- | --- |
| 只第一个目标成功，第二/第三目标错绑 receipt | 261–264 对每份 commit ID、CID、AID 及该资料独立 pending/V/P0 校验；不是取首份代表 |
| 空项目已有残留 | 239 的完整 UI 集合检查 |
| 项目中漏行、重行、外来行、不可解析行 | 268/297/313 调用 146–158：不先 set 去重，逐行解析并比较完整 sorted ID 多重集及标签；155–156 首先拒绝 |
| 第二轮 pending 将第一轮 ready 清空/覆盖 | gate 释放前 271 对完整 entry、272 对当前可见三面板、273 对独立全文/全表/原件逐旧目标检查 |
| 两端 API/UI 同时展示了别的目标 | 24 的精确单 ID 搜索结果、27–33 来自独立库的 origin/V/P/格式/原 SHA/源词，44–47 全格/跨度，50–51 原字节；不会仅 API=UI 即通过 |
| begin/parts/commit 两面同错，误项目/顺序/截断/上传键 | 70–86 独立目标项目、稳定键、原长度、分块边界/序号/实际 SHA、commit 对应 CID/AID；不是仅看 receipt 数量 |
| 当前可见面板正确状态但错 CID | 113–114 的完整字典等值直接失败；119–143 三 panel 反控实际执行 |
| 点击后行被同步替换并关闭 | 99–104 connected/open 检查有界重开；真实 DOM 自检覆盖 |
| 新目标提前发布或 gate 没有真挡住 | 265–267 可见 pending/无 published/search 空；373–397 真服务 gate 控两次 hold 后 release 到 ready |

还保留 161–183 两容器各八种全集拒错、347–369 二十种身份/分块负控；最终 301–302 再读所有旧 entry，308 验 12 个唯一 ID，310–315 切项目并验最终全集、全部原件/内容。本机 318–321 两项目精确同步状态默认 disabled；Hub 317 的授权边界没有被删掉。每个 debug 实际到达五项 pytest，不因增加无依据等价样本而阻塞。

## 当前原始运行、依赖与无损证据

每份 result 及其全部 artifacts 都逐件重新计算 SHA。113 个源码 binding 与工作树、各 debug 冻结 source 和 runtime 绑定全一致：64 份实际产品 py/html、49 份测试源；递归实际测试 import AST 22 模块与动态 restart_server/sitecustomize 也在绑定内，没有以人工列表替代动态依赖核对。当前 trace 没有内嵌 src 文件，源码依据是冻结 source 原字节。

| 检查 | Local | Hub |
| --- | --- | --- |
| 原 run.stdout | 5 passed, 1 warning in 12.48s | 5 passed, 1 warning in 18.56s |
| 原 run.stderr / process | 空 / exit 0，无 skip | 空 / exit 0，无 skip |
| 全 artifacts / attachments / bindings | 903 / 786 / 113 | 897 / 780 / 113 |
| gzip JSON 数 | 670 | 672 |
| 解压原 JSON 字节 → gzip 字节 | 4,763,476 → 1,213,513 | 6,206,138 → 1,827,128 |
| 附件总字节 / 全 artifacts 字节 | 20,753,250 / 22,089,698 | 20,758,052 / 22,094,494 |
| 产品 row 快照 | 36（12 pending、24 ready/保留） | 36（12 pending、24 ready/保留） |
| 独立全文 / 全表 / 原件信息 | 60 / 200 / 60 | 60 / 200 / 60 |
| 实际下载原件 / 分块 | 12 / 14 | 12 / 14 |
| 浏览器请求 / errors / cleanup errors | 133 / 0 / 0 | 126 / 0 / 0 |

唯一 warning 是 Starlette httpx 弃用。每个 lossless-evidence.json 中每一项实际读 gzip 原字节、解压、对照原 SHA/原长度、gzip SHA/长度，且 JSON 解析成功；不是只检查 manifest。浏览器 response 原文件 SHA/长度也逐一核；begin 源 SHA/长度、每个 part 实际字节及 commit 身份均与独立预期吻合，下载实际原字节 SHA 均正确且 12 份不同。所有 server-stop 原件读到正常 exit=0、forced=false；cleanup 原始事件无错误。

conftest 仍只在 JSON 单项大于 8 MiB 或总附件大于 20 MiB 时无损 gzip JSON；PNG/trace 原字节没有变化。各本轮 gzip manifest 自身也在全 artifacts SHA 校验内。旧 web-ui-v1/v2 超限 blocked 记录没有改写，不将其作为当前通过证据。

## 实际打开的当前图片

下列 16 张均用 view_image 实际打开，而不是读文件名或引用上轮图片。pending 截图发生在可见行断言之后，轮询可能已将详情再次折叠；因此只据这些图确认可见行/状态/数量，不把折叠面板当作展开内容证据。展开内容由同回合原子快照与相应 ready 原图交叉支持。

- [local-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-1-pending.png)：普通项目 #1，三格式 pending V/P0；详情关闭，下载禁用；两项目默认不同步可见。
- [local-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-1.png)：普通 #1 三份 ready V/P1，三份详情展开。
- [local-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-2-pending.png)：普通 #1 六行，三旧 ready1、三新 pending0；详情关闭；全页下方空白不等于缺行。
- [local-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-chooser-2.png)：普通 #1 六份 ready1，旧三份与部分新份详情展开。
- [local-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-1-pending.png)：全局 #2 三份 pending0，详情关闭；全页有长空白，行均在。
- [local-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-1.png)：全局 #2 三份 ready1，三详情展开。
- [local-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-2-pending.png)：全局 #2 六行，三旧 ready1、三新 pending0，详情关闭。
- [local-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-drop-2.png)：全局 #2 六份 ready1，六详情展开。
- [hub-chooser-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1-pending.png)：普通 #1 三份 pending0 均可见，详情关闭；下方长空白，非空列表。
- [hub-chooser-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-1.png)：普通 #1 三份 ready1，三详情展开。
- [hub-chooser-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2-pending.png)：普通 #1 六行三旧 ready1/三新 pending0；旧 PDF 详情展开，其余关闭。
- [hub-chooser-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-chooser-2.png)：普通 #1 六份 ready1，旧三份及最后 PDF 详情展开，部分新份关闭。
- [hub-drop-1-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1-pending.png)：全局 #2 三份 pending0，详情关闭。
- [hub-drop-1.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-1.png)：全局 #2 三份 ready1，Word 关闭、XLSX/PDF 详情展开。
- [hub-drop-2-pending.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2-pending.png)：全局 #2 六行三旧 ready1/三新 pending0，详情关闭。
- [hub-drop-2.png](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-drop-2.png)：全局 #2 六份 ready1，六详情展开。

另实际打开旧失败图 [hub-failed.png](<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/source-032-linux-triage/web-hub/hub-failed.png)，所见如前述，未将其混入当前图。

## 实际打开的当前 trace

用本项目当前 Playwright 1.65.1 驱动 open 完整 ZIP，读原 trace.trace/network，并执行 action、after snapshot。旧 skill 附带 CLI 不支持 v10 时改用当前同版本 CLI；没有用不兼容读失败替代 trace 审阅。两份都是 darwin Chromium、1280×900，仅证明这些当前原生 debug，不宣称 Linux/Windows 当前重跑。

- [local-trace.zip](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-local-v1/TC-008-web-native-upload/attachments/local-trace.zip)，SHA256 `cdeb78c45e2df65dbb20773af2816349cbeab48752caeb0b79c9a4aef1d3532e`。8.6 秒、429 动作、133 请求、0 browser errors；chooser bxan@158/339、真实 DataTransfer drop 583/752；截图 252/326/457/561/670/748/875/979；最终 997 切回 project2，1011 after snapshot 六 ID 完整。

  最终实际 snapshot ID：`97703bfe5bd54598b013dc9c36653dc0, 11079922d1a14179935bae4999497395, a61753f6684f4776afe23dc79f6fe1f1, 7740c01ee87b47bfb68b768bae7a174d, 93f1a34762694975b79afecd9b06b8ac, dd123330b78540f1a7fd2d3d9f18eb51`。

- [hub-trace.zip](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc1-web-row-hub-v1/TC-008-web-native-upload/attachments/hub-trace.zip)，SHA256 `7c05519f4da931f4aadf7c4980b04bcfa3a43fcb09bf6b50c6df84e1fe847eb8`。13.3 秒、415 动作、126 请求、0 browser errors；chooser jlpo@146/321、真实 DataTransfer drop 567/730；截图 232/308/443/545/658/726/849/951；最终 969 切回 project2，983 after snapshot 六 ID 完整。

  最终实际 snapshot ID：`11fefb1f2320448da7db43547efa5cac, cbc1295e85ed497ab3e9dcecfd874b01, f96a40f5e8c94883b11beda437ca2ad9, a80d8199321d445ba459df2f02c699d6, 5aa94b9fc95149fc88b0f8da46199014, bd5780748d6847c7a76063e60f38d33e`。

trace 给出动作顺序、真实 DOM frame、请求及截图；它没有记录本轮 element evaluate 的返回值。因此 connected/open/三面板同回合结果引用已核原字节的 web-visible-row-snapshot JSON，不把 trace 未记录内容说成 trace 中存在。反过来，JSON 也没有替代实际打开 PNG 和 trace。

## 登记意见与修订结论

场景/自然设计：与已确认需求一致，原设计保持，不需新增业务行为。实现/探针：修复观察窗口，保留原状态/身份/内容判据，对已知整行替换竞态及三面板错误值有实际反控，当前两份原生 debug 的原始运行和所有证据支持限定通过。

已分别完成并立即通知主 Agent 登记以下唯一 TC 意见：

- [review-completion-sc1-web-row-local-candidate-v1.json](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-sc1-web-row-local-candidate-v1.json)：passed，covers 仅 creator-web-native-upload。
- [review-completion-sc1-web-row-hub-candidate-v1.json](<TASK_WORKTREE>/.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-sc1-web-row-hub-candidate-v1.json)：passed，covers 仅 creator-web-native-upload。

无需修订。该结论不改写旧 source-032 测试失败、旧超限 blocked 或其他场景的验收状态；完整源码三 OS CI 的后续修复/回归由主流程判断。
