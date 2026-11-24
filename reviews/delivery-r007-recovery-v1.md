# R007 恢复后完整需求独立交付判定：blocked

验收 `AT-SMM-007`，项目 `/Users/boboyang/work/smm-007-recovery`。本 Reviewer 为 `/root/delivery_007_recovery_v1`，执行需求级复审，不承担 PR 源码 Review。只读项目与证据，没有启动产品、测试、服务或 GitHub 变更，没有访问家庭 ESXi、日常归档/Hub/VibeInsight 或用户文档；仅写本轮两份意见文件。

原生意见 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/delivery-r007-recovery-v1.json` 严格只含 `status` 与 `reason`，写出后已立即通知主 Agent 注册。注册结果以主 Agent 实际工具收据为准。

## 采用的完整基线

实际读取交付验收技能 `SKILL.md`、`references/execution/reviewer.md` 的需求级规则、根 `AGENTS.md` 和 007 `intent.md`、完整 `spec.md`、`plan.md`；并读取定义 v7、当前恢复结果视图、历史验收导航、服务及此前需求独立报告、当前回归/CI 和恢复 E1 原件。范围为 B1–B8、A1–A10、SC1–SC16 与既定36个 TC，不因本轮执行授权或资源限制删减必要平台。

实算 SPEC SHA-256 为 `590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`，定义 `000007.json` 为 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`，与交接一致。复审读取的 `.acceptance-local/recovery-20261124/native-results-view.json` SHA 为 `87c2f788d56f9aa9efc913668a1f3ab5c74de10d57d1856c674e4bba73b0cf42`。

技能判据是：当前有效正式证据已证明任一必测产品行为失败，判 failed；未确认这种失败且证据不足，判 blocked。当前适用后者。

## 恢复后正式记录的边界

结果视图的16个场景 `cases`、`history` 均为空，R007 为 `pending_delivery_review`；这不是36项当前正式通过，也不能把空的 `missing_obligations` 当作完整覆盖。已提交521份 JSON 实际组成是7份定义、1份 manifest、513份尝试索引。逐条检查513份索引的 `record` 路径，其指向的私有 `result.json` 当前均不存在。旧索引保留可追溯身份和摘要，未恢复其完整目标收据、附件或新独立身份。

`evidence/acceptance-index.json` 仍明确标为此前候选的历史状态（1 passed、4 needs_revision、30 not_executed、1 insufficient_evidence）；它不是恢复后的正式结果。续接摘要所述33 passed，以及缺失的新版执行/复审，均不能由摘要重造。本报告也不把本机完整 pytest 拆写成28个自动 TC 的正式通过。

## 本机完整回归检查

实际打开 `.acceptance-local/recovery-20261124/local-regression/{exit.json,stdout.log,stderr.log,test-results.xml}`。进程起止为2026-11-24 08:14:52Z至08:18:52Z，候选 `5083227897ab9612390a4cbc4997df961dff96d7`，实际退出0。原输出与 JUnit 一致：341项、340 passed、1 skipped、0 failure/error；跳过是 Windows 专用后台启动测试。stderr 为 pytest-asyncio 配置弃用提示，没有测试失败。

实核 `source-test-sha256.json` 101份 src/tests 字节全部匹配；`git diff b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da -- src` 为空，src/tests 当前未提交 diff 为空。故新执行可关联当前产品与测试，不把更早平台包当成这次回归。实核恢复公开 manifest 初始10件长度/SHA 全匹配；这是完整性检查，不代替业务通过。

## 常规三系统 CI 检查

实际核对保存的 run45298310517 API run/jobs、日志和三个 JUnit 原件，三 OS 的 pytest、`build_packages.py`、`Install wheels separately` 步骤均 success。API head 是 `5083227`；日志实际 checkout 是 `4f4385709ace965a3b1b1953d1d266ac8e51ee88` 合并提交，两者保存的 Git commit API 的 tree 均为 `215677b6609468e465a5b15b5e3d48a8459096e5`，没有把两个 SHA 混写成同一个提交。

| 系统 | JUnit 总数 | 通过 | 跳过 | 失败/错误 |
|---|---:|---:|---:|---:|
| macOS | 341 | 335 | 6 | 0/0 |
| Ubuntu | 341 | 335 | 6 | 0/0 |
| Windows | 341 | 336 | 5 | 0/0 |

各 OS 五项跳过明确因为普通 CI 没有 Playwright，涉及两端 Web feedback、Hub retained-state、两端 folder-guidance；Mac/Ubuntu 另跳过 Windows 专项。没有把它们称为三系统真实浏览器实测。该证据支持所记候选的回归/构建门禁，不替代 E1/E2；后续证据提交的最终 PR head CI 仍须另核。

## 恢复的三平台 E1 原件检查

实际原件在 `.acceptance-local/recovery-20261124/run-45297175901/document-installed-e1-<os>/007-public-evidence/`。保存的 API 和 job 日志显示 head `8210b2570b19a4e58b2a1da118828634fb6487cc` 三格 E1 job success；两个 E2 服务步骤明确 skipped。

本 Reviewer 重新读取三个 ZIP，逐一对 GitHub artifact API 比实际长度与外 SHA，并 `ZipFile.testzip()` 核全部 CRC；重新对各内部 `sha256.json` 每件算长度/SHA，结果如下。

| 系统 | ZIP 字节数 | ZIP SHA-256 | 内层校验 |
|---|---:|---|---|
| macOS | 17390744 | cce371b6abd61ff31db701e8f52f64e6ec051123c1a934d9e56cc895eebd78e9 | 115件全部匹配 |
| Ubuntu | 18387230 | a76516e9287647affb1a8c941b217c31c12f5db6d9c3efe897821cd740aa0828 | 115件全部匹配 |
| Windows | 13816219 | 219d79e015b5dff0c6e1f71dcc91043a74395d5e94eaea9ccbd868484874e6b6 | 116件全部匹配 |

三个 `platform/result.json` 均保存 passed 与实际起止；这只是执行器结果，不能单独当完整人工独立复审。三 OS 的实际 `packages/*-installed-modules.stdout` 各30份 Local、31份 Hub 模块摘要与当前源码逐项吻合；Hub vendored `_archive` 按 `scripts/build_packages.py` 实际复制及 shim 替换规则映射，而非误作源码文件夹。三个 Hub 均 `hub_has_no_local=true`。包 SHA 与命令原件已保留，未因版本号相同假定模块相同。

新增 `restart-stdio.json` 三平台各有6份旧有效 ref 的真实读回，含本机 private/global/unbound 和 Hub native D/E；可读正文、码点范围与行号存在，并与当前探针中独立字面原件一致。三个 `restart-web.json` 各有 Local 6 / Hub 3 份 `exact_reads`、26条请求、空 `page_errors`。因此此前“完全没有新增重启 Web/stdio 读取”的历史缺口不能继续套用到这些新原件。这里确认局部事实，不在未逐项审完 E1 长检查的情况下认领全项。

实际打开 macOS `platform/restart-web-hub.png`，见 Hub 的3份 native 文档命中、版本/设备/项目出处及 `two.md` 的 emoji 与两行原文；实际打开 Windows `platform/restart-web-a.png`，见 private/global/unbound 与 Hub native 命中、暂停/默认不同步状态和读取端明确的 native 原文。本报告不将这两幅图扩展成所有阶段/平台的图像复审。

每 OS 三份 CMS 轨迹均有密文，内层 SHA 校验包含这些密文；恢复记录明确 `decrypted=false`，私钥未恢复。本 Reviewer 未解密或实际打开完整 Playwright trace，未把密文 CRC/SHA 当作原 trace 的事件/网络内容已检查。完整 E1 新独立执行复审收据当前仍未恢复。恢复原件是有效进展，不能据此直接登记三项人工 passed。

## E2 与不可替代的需求缺口

依据完整 SPEC A9、E2 和 PLAN E2，以下缺口各自独立阻止需求 passed：

1. **真实跨 OS 不同机器的 HTTPS 业务。** 当前没有获准的不同 OS 两机业务环境及对应同步、远程 Hub 网页上传/更新、另一端精确原文、断线待办和恢复证据。两个同机 Local 档案或托管同宿主的前景/服务流程只能证明逻辑设备和同宿主路径，不能排除物理网络、TLS 与远程浏览器条件改变结果。
2. **实际服务网页资料停启持久。** 已读取 `reviews/services-manual-review-v1.md` 及现存 Ubuntu/Windows `public/*-service/{result,service-events,service-cleanup}.json`、Windows `scm-client-boundary.json`。Ubuntu 实际 UID1001、PID3778→4324，Windows LocalService SID S-1-5-19/session0、PID7104→6300，普通 Local 非管理员且不能读取 Hub DB，这些都是可保留的局部原始事实。此前独立服务复审明确指出停启后只重读外部 native 采集资料，未按网页新建 Hub 项目再次查询并沿保留网页文档旧有效 ref 读回。服务身份、存储创建方式、ACL 与停启后的管理副本访问是可能改变结果的条件；native 缓存通过、普通进程通过或代码同字节不能证明缺失路径。原服务完整私有请求/trace本轮未重新恢复，不能声称本 Reviewer 重读了该阶段全部原件。
3. **Windows 服务与规则清理的后验状态。** 当前公开 cleanup 只有 service 标识、时间及 `failures=[]`；它不包含删除后的服务不存在及防火墙规则不存在查询。停止 PID/端口可支持部分清理，不能排除残余服务配置/规则。未据此断言残留真实存在，也不把原删除命令意图等同后验结果。

维护者已明确“保留缺口，先完成其他验收”；这是执行范围约束，未修改 SPEC，也不是平台豁免。本轮没有运行补证、请求新的执行授权或创造服务等价路径。macOS 同 UID 前景替代 launchd 是 SPEC 明文允许的有限依据，不能类推取消 Windows SCM、Ubuntu user-systemd 或真实跨机要求。

## 完整范围如何归结

| SPEC 范围 | 当前能支持的事实与判定边界 |
|---|---|
| A1–A4 授权/发布/生命周期/顺序 | 当前完整回归与 E1 原件提供支持；历史逐 TC 索引和丢失的原执行/复审不能组成当前正式全覆盖。不从局部通过推全条通过。 |
| A5–A7 原生/联合范围/准确读取 | 当前回归、同版模块与新增 Web/stdio 原文是局部实证；既定公开入口和故障组合仍以逐 TC 适用证据为准。本次没有从源码静态推断全部输入已验收。 |
| A8 兼容/独立包/发现 | 本机完整回归、三系统构建/分安装及 E1 模块摘要实核有效；完整发现链/CAS/凭据浏览器独立收据未恢复，普通 CI 五项 Web skip明确保留。 |
| A9 实际平台 | 三格 E1运行及新增补证有效，完整独立执行复审未恢复；E2两服务必要子项与真实跨机器证据仍缺，直接阻止需求 passed。 |
| A10 网页库 | E1 可读请求/JSON/PNG及本机回归支撑多项局部行为；完整浏览器 trace当前不可读，服务创建端网页副本停启路径仍缺，不能升级整条通过。 |

源码同字节只用于核证据版本，没有用它替代跨身份、持久存储或物理网络实测。当前回归、常规CI与恢复 E1可读记录未确认必测产品行为失败；此前 SQL/内部归档ID断言等测试实现故障也不能当产品失败。故本轮结论是 **blocked，非 failed**；必要实机条件、当前正式收据及独立复审证据尚不完整，故 **不能 passed 或据此合并交付**。
