# SC8 人工准备独立复审

AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_b，2026-11-22T10:02:17.368103+00:00。本意见不认领人工或正式业务通过。

实际审阅design `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc8/request.json` SHA256 `0935a178ccee62db5b1c2c88abc7152f1298ed214a1ec2771c87afacf73a3127`；match `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc8/result.json` SHA256 `463f01411f7ccd3bfa78dad492c530dd8c471e1ce3f79978428cfbd64b73151d`；steps `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC8.md` SHA256 `8af16b84e5c92a078a595545592987945e15ae5fdbfbf749586be27f9be62b05`。人工TC-005-sc8-evidence分配full1/full2/full3。A8/B7、PLAN §7/8.1支持criteria，没有新增产品承诺。

| 检查 | 可执行性、原件和版本准备判断 |
|---|---|
| full1 | 准备有效，可进入观察。三E1 main保存CLI/MCP/Web各自新命中reference与reads，夹具local-A与vibe-V同整数ID但不同来源及正文；version-and-long-originals及retained-version-original有不同版本完整原文。当前reference TC实测远端失败不回本机同号，boundaries七输入补首/非首删除与真实换Hub。正式核验需逐入口按独立原始正文匹配自己的ref，不能拿同整数ID或两入口相等作证。 |
| full2 | 准备有效。六份scope11/15 split-scope原件都有独立fixture（Y首条OUTSIDE_Y_ONLY_SECRET_TITLE、X第二条boundaryneedle allowed X full original）、本机A仅关联X、CLI/MCP/direct、legacy_unscoped及after_hub_restart。已逐份实际比较原始消息与标题：新读均仅X，旧整段仍Y+X及Y标题。三客户端另有browser/trace/PNG。实际打开windows-scope-run11/boundaryneedle-browser.png：查询boundaryneedle，实际档案本机+Hub，scope-X命中仅位置2，原文标题和正文均为X，无Y秘密。其余平台画面仍须在正式核验逐张打开；准备阶段确认原件可用不等于画面全验。篡改/冲突与来源改变由当前test_archive_references原件补。 |
| full3 | **证据准备不足，需修订implementation/补原件。** 旧CLI与Hub API有compat/linux-compat/windows-compat的真实旧包调用及旧读正文；当前test_federation.py:161–166真实CLI旧整数/hub-message形式，test_archive_references.py:76–83共用旧式本机/Hub读取，test_pipeline.py:264–276旧Web GET有当前回归。但没有找到005原件或当前回归实际调用旧MCP `read_conversation(conversation_id=...,hub_id=...,hub_message_id=...)`。已搜索完整tests及005所有probe的read_conversation：test_federation、test_vibeinsight_sync、selective_upload_platform/isolation/scope均传新reference，test_pipeline MCP用例只调用search。compat脚本77–94保存的旧引用读取仅API和旧CLI；没有旧MCP进程/请求/响应。PLAN §8.1明确“旧包调用旧命令和旧MCP参数，不通过新包helper代跑”，SPEC B7/A8要求旧CLI/MCP/Web调用继续可用。当前mcp_server.py:48–53保留可选旧参数只能作源码推论，不能冒充实际旧MCP调用原件。应补真实旧MCP调用原件（原执行者/包/时间/请求/完整独立正文），或定位已有可复核原件后将具体路径补入steps/match并重审；不需要扩大为重跑所有平台。E1三入口新调用与E3/E4范围部分已有有效原件，不因缺旧MCP而否认它们。 |

41之外共用回归分工：full1/full2引用test_archive_references的tampering_cross_archive_and_conflicting_parameters（循环每个本机/Hub命中，篡改末字节、conflicting conversation、message_id拒绝；另外本机引用跨档案拒绝）、local_content_change_between_recall_and_signing（独立旧内容回忆后改库，签发失败）、shared_conversation_reference_cannot_expand_to_outside_project（扩大区间仍仅X及X项目，start=2为空）、old_read_parameters_still_work_without_new_reference（分配full3旧common函数正控）。完整JUnit逐case均无failure/error；full-pytest receipt于09:53:42Z完成exit0，inputs/stdout摘要核对一致。不能把这些共用函数调用写成已经实际执行旧MCP形式。

版本与依赖闭包：CLI/MCP/Web各入口→federation.read_archive→references.decode/read及Hub read/project范围、Archive和archive_protocol。d80 references有后续新范围title修复，不能沿用d80证明范围标题；f45后的三E1 scope11及Linux/Windows服务scope11、Mac系统服务scope15实际补足。scope manifest及final-package-comparison21支持7c→ba8完整Hub字节相同、本机仅upload变化；本场景federation、references、core及MCP字节与scope实际版本相同。API/CLI/static变化只reconcile输入与UI、upload变化限控制/对账，不改变这些新读取分支。原同号正常读取和旧参数API/CLI原件在该闭包及当前回归下可支持其限定义务；旧MCP仍缺实际原件，不以模块相等无条件放行。

边界推演：本机/Hub只有首档案正确会在独立local/remote正文断言失败。删除只检首stamp会被本机/Hub deleted-last分别的raises拦截；重复position只处理首消息会在第二条独立正文、ID和version断言失败；两个入口同错把Y标题带出由独立title=X和Y秘密排除拦截；旧整段正控同时证明Y仍在，不能靠删夹具蒙混。换Hub存在新Hub及本机同号哨兵，要求抛错且不向新Hub发read，挡住误用同目标。旧MCP形式若被适配器拒绝或丢旧参数，现有新reference测试可全过，这正是full3缺失的第一层实际输入。

结论：full1/full2准备有效；full3旧MCP子项需补原件/步骤实现后重审，整个人工TC暂不能以当前清单判准备通过。自动三TC各分配断言仍有效，JSON仅包含真实debug目标，不将该人工缺口伪装成自动产品失败。
