# PR #33 最终独立审查 v2

结论：**passed；没有未关闭的产品、用户路径或验收证据发现。** 这份结论针对下述产品和当前文档内容；最终文档提交的 CI 与 GitHub 实际合并尚待主 Agent 完成，不在此提前声明成功。

审查者 `/root/review_006_pr_final`，最终核读时间 `2026-11-22T19:54:47.565638+00:00`。base 为 `f797fe843430b48faf379cd76b4ae18fd52f5c64`，当前产品/测试/平台探针头为 `9cfd6193262b692f779abe1b240cd82f67b1eb50`；`documents.py` SHA-256 为 `390880bf58192317846ed1db29f271b9c5f6c7530b3811736634fa7aa4f74d66`。本 Reviewer 在干净上下文独立开始，未实现产品或修改 AT；同一审查期间真实发现尾 glob P2、复审红灯后继续审查返修。旧 [v1](pr-review-v1.md) 是 a66 历史意见，不是当前批准。

## 方法、计划与范围

已实际读取并在最终核读时再次打开 [PR Review Prompt](../../_templates/pr-review.prompt.md)，对照006 [Intent](../intent.md)、[SPEC](../spec.md)、[PLAN](../plan.md)及实际 base→当前 diff；实际查看产品源码、必要测试/探针、独立意见、业务请求/响应、私有原图和 trace，不以汇总 passed 代替复核。

实现位置和方案符合 PLAN P4–P9：独立本机文档表/FTS、手动刷新和有界扫描、文件版本与来源连续资格、原子发布、独立三入口，项目迁移仅在文档表存在时执行，Hub包不导入新模块。测试按职责拆分、额外项目确认回归、Windows控制环境及事件循环/设备名处理、Unicode定位、来源元数据及尾 glob 返修，都在 PLAN 的“实施时的验证组织调整”说明，未降低 SPEC。未发现未说明的实施方案或验证偏差。规格31、计划32先后合并再实施；007/008、发布、日常升级与真实用户资料均未混入本次范围。

## 从真实主入口回放

Intent 影响普通使用者、取得文档依据的 Agent，以及安装/维护和复跑的维护者。以下从当时可见入口逐步核对，而非从内部SPEC直接提供命令。

| 角色/步骤 | 当时可见的信息、必要输入与可继续的路径 | 核对结果 |
|---|---|---|
| 普通使用者发现能力 | [README](../../../README.md)主使用路径“本机文档检索”介绍Markdown/TXT、本机边界、Web“文档”与CLI，并明确0.4.0正式包/首次安装器不含006 | 能判断适用对象与版本，链接到源码开发及[指南](../../../TRIAL_GUIDE.md#本机文档检索006尚未发布)，无需猜测重复安装旧包会新增能力 |
| 准备可运行环境 | README源码开发提供Python3.11+/venv/安装/serve与本机地址；指南提供独立wheel构建/uv安装、两系统解释器目录、每条CLI前置同一个--db、MCP同档案与合成演示空Agent来源 | 路径均有含义及取得方式；Windows有Scripts入口，Web沿已有本机启动说明，不把浏览器另一电脑路径当服务器文件 |
| 创建与纳入 | 指南1–4及Web表单给出普通项目创建/项目页和projects取ID，服务器本机绝对路径、零/多/全局绑定、递归/排除语法、set完整替换及pending | 从无项目档案也能开始；add/set尚未采集，下一步明确refresh；来源ID从sources/页面取得，不要求从SPEC找输入 |
| 查询、读原文与恢复 | 指南5–9、各层CLI帮助及Web来源表/文件错误/查询/reader，给出覆盖状态、项目直接一层范围、精确reference、码点范围、采集时间/版本/SHA、旧ref失效、修复再刷新与移除影响 | 输入与后果充分，能完成并确认结果；失败覆盖不被0条掩盖。当前Web原图与真实按钮轨迹相符，惰性script文本不执行 |
| Agent调用方 | README“Agent接入”实际链接[Skill](../../../skills/smm-search/SKILL.md)，文档专节先检查支持能力，再list_document_sources→search_documents→read_document；明确不隐式扫描/刷新、不混对话ref、未发布边界与CLI/Web管理 | 三工具readonly及真实stdio可发现；项目ID取得、范围、引用与位置可判断。需要讨论和文档时分用两类工具；SMM不外发与Agent正常上下文处理的边界有说明 |
| 维护者复跑与审查 | 指南末尾链接[scripts/acceptance/README](../../../scripts/acceptance/README.md#006-本机文档可选实际包验证)，首段直达[当前证据](../evidence/README.md)；下文有双包构建/独立环境、控制依赖、目标JSON字段/取得方式、全新输出、普通账户和清理 | 能准备并开始复跑，也能找到当前29TC/A1–A8/E1、业务原件/独立意见/CI/双SHA。父[004导航](../../004-project-knowledge/README.md)现准确记录31/32合并及33/证据入口，没有提前说实现已合并 |

审查期间曾在全新隔离档案亲自走14次CLI和真实stdio三工具、重跑17项项目/定位/兼容测试，均成功；原CLI/MCP记录保存在私有 `work/pr-review-v2`，公开副本位于 [support/pr-review-v2](../evidence/support/pr-review-v2/)。这些是当时4c版本的附加审查检查，不冒称9c新的formal TC；17项测试原stdout仅在工具输出观察，未保存磁盘原日志。当前9c结论采用下述重新取得的正式/包/平台证据。

## 逐项规格与当前证据

已重新核对24份 `execute-r006-v5-*` 当前bindings及1139份artifacts，逐文件SHA全部一致；当前[覆盖索引](../evidence/coverage.json)的29项无重复，独立正式意见与实际退出相符。

| SPEC | 核对的当前行为与证据 | 结论 |
|---|---|---|
| A1 | source-config/entrance-contract：新普通项目身份、文件/目录pending、完整替换、非法输入不改配置；严格API、CLI与三个readonly工具；平台真实Web管理 | passed |
| A2 | scan-scope/decode-files/budgets/read-races：完整路径与正文、默认/自定义排除、链接、编码/权限/变化、真实2MiB/1000/16MiB边界及预算优先级；尾glob返修详见下文，平台真实文件差异另证 | passed |
| A3 | project-scope/maintenance/overlap-version：零/多/全局与直接一层、改名/合并/映射、去重；S1/P/v1→S2/Q/v2的P/Q/all及remove/failed/continuous完整时间线，当前有效来源与历史collector分开 | passed |
| A4 | version-lifecycle/qualification/source-lifecycle：修改换版、改回旧字节不复活、移动/删除/配置/移除、同字节恢复须新资格、最后正文/FTS退出；当前平台跨进程/重启持久 | passed |
| A5 | search-rank/exact-read/invalid-read/empty-query：51文件、排名/limit/稳定去重、长文/边界/Unicode、独立码点/行号/16000边界、引用篡改/串档/旧资格拒绝及真实覆盖 | passed |
| A6 | refresh-order/remove/overlap-order/query-snapshot/interrupted-refresh：真实屏障与持久快照比较、旧任务不覆盖、查询冻结范围、连续资格中断；中断注入与平台真实停服重启有明确区别 | passed |
| A7 | isolation/compatibility/packages与full-regression-v6：无Hub/已配Hub/暂停不改对话状态且网络哨兵有效；旧参数/帮助兼容；Local26/Hub24源码→wheel→独立安装；301passed/1skipped及9c三系统两轮CI六jobs成功 | passed |
| A8/E1 | 三个普通账户新formal-v4、独立Local wheel、实际CLI/Web/stdio、文件/目录/中文空格/坐标/修改旧ref/删除移除/错误修复/重启/实际PID端口清理；user-v5和files-v4当前独立意见 | passed |

当前平台候选4完整wheel SHA为 `412a68157d685f93bda6dbe8a4fbd77945dea53e7faa8578fdcc46235a2ba6fb`；本人对三平台26个installed/expected模块与HTML逐一重算，均等于9c源码。各平台85条命令、20轮stdio、7PNG/3trace有原件。本人直接解析当前9份原trace：主各137动作/34请求、partial13/8、重启50/13，均0工具错误；实际文档主导航、配置/刷新/检索/读、旧ref400、删除来源及同旧ref200可追溯。已看当前Mac原文PNG；三平台其余原图的逐图独立复审和第三需求意见完整记录，不冒称本人本次又打开了全部原图。

原文读取的source_ids只从原签名stamp中筛选仍通过存在/状态/revision/qualification校验者，不补新来源。当前三平台survivor三入口均保留连续S1、历史已移除S2及准确edited正文；它证明同一个旧双源P引用的三入口，不夸称平台完整执行all/remove/failed/continuous时间线，后者据当前共用三分支。首次真实failed因此关闭，且未回退Unicode lower码点映射或额外等价字符负控。

## 本审查发现、返修与最终闭环

本Reviewer在4c实际复现P2：`cache/**/`漏排cache直接文件，违反B2零目录段语义；当时未批准，原[反例](../evidence/support/pr-review-v2/glob-trailing-recursive.json)、红灯与第二次[failed](../evidence/native/delivery-r006-v2.json)保留。原4c新断言真实exit1因额外cache/direct.txt失败，本人独立授expected_failure/covers[]后才修产品。

9c修复后的五次原search完整集分别5/3/5/3/7，23份read逐路径核为独立 `globneedle ` + 相对路径；包括cache/**/、**/cache/**/、outer/**/cache/**/、连续**和大小写负控，未以emitted wanted作唯一预期。green-v5/formal-v5运行与全部原SHA均已亲核。额外独立段递归解释器有限比较95,940组0差异，仅作为工具观察的补查。LF是编译器语义检查，不冒称Windows创建LF文件名。

三个新平台实际配置excluded/**/，有独立51字节direct文件；各10份时间线SHA/bytes/mtime未变，实际项目CLI恰3文件，排除marker零命中但indexed_files=4，来源候选3/预算6130/排除1/链接1，23项body-open原审计无excluded且均仅显式刷新、只读。原P2现已关闭。旧Windows首停只看launcher的缺证也由新原actualPID+port补齐：Mac58418→58793、Linux164023→164420、Windows1176→10884，首次退出核验均早于第二启动，末次同样停止。旧Unicode两次红灯、来源元数据failed、尾globfailed及user-v4标签笔误均保留，不追授旧版本passed。

最终核读 [第三需求报告](delivery-review-v3.md)与[已登记判定](../evidence/native/delivery-r006-v3.json)：Reviewer为另一个全新会话 `/root/review_006_delivery_v3`，其原意见SHA `eeaa6630ce97b5286a6aa249e828d09f78c1610b61212cca9273cc840889cf27` 已亲算一致，当前8SC/29TC/R006均passed。已看最终看板原PNG及JSON，并核[finish摘要](../evidence/native/finish-public.json)：真实finished，原私有snapshot SHA `218403eaae9f8d7d9d30ac7e6ceab05bdfddab14d080a898603ac81889bd604b` 与原记录亲算相等，pending_requirements与unfinished均空。不是以预先写好的索引替代判定或finish。

最终本Reviewer运行 `python3 changes/006-local-document-search/evidence/verify.py --raw-root /private/tmp/smm-006-impl` 实际返回 `Verified 2327 published files and private original SHA`。公开副本脱敏与原SHA分列；私有原trace此前已实际解析，未因脱敏缺trace而跳过关键原件。已审主Agent准备的最终PR正文预览，行为、通过/历史失败/范围外及当前head CI边界与上述实证一致。没有要求无影响的格式改动，也没有确认新的规格外用户路径缺口。

**剩余交付动作**：主Agent提交最终文档/证据/本意见，等待该实际最终head的CI成功，更新线上PR正文、转正式并按既有授权合并，读回GitHub实际MERGED。产品源9c的两轮三系统CI已成功；本报告不把它们冒充尚未生成的文档提交CI，也不声称PR已合并。
