# 范围标题修复与实际平台补验

本目录记录当时产品源码 `f45da53` 的执行。到 `86471ee` 为止后续提交只增加验收控制器、测试及证据，产品模块字节未改变；控制器版本与产品版本分别追溯，不能只凭包元数据 `0.4.0` 判断。每轮的两类wheel/实际模块/HTML全部SHA、OS/Python/浏览器/真实账户及运行方式见对应manifest，原始/脱敏输出与控制器摘要见provenance。

**f45 版本 R005 判定未通过（保留历史结论）。** [独立需求判定](reviews/delivery-r005-current-v1.json)在 f45 产品复现：旧差异展示none后，另一入口只在本机保存all，Hub版本不变，旧重提能确认all，违反B1。维护者随后已确认双版本方案，SPEC/PLAN 已先提交，新版实现与实测另记，不能改写本目录旧结果。Mac系统级launchd仍按用户“稍后认证”保留为必需未验证项。不能以全量测试/这些专项通过宣布可合并。

P2标题泄漏已修复：新引用只从实际允许且选中的消息生成title，无范围旧读仍保留整段语义。[红灯复审](reviews/review-red-scoped-title-v1.json)与[同版绿灯复审](reviews/review-green-scoped-title-v1.json)分别独立通过；绿灯实际到达两入口的准确X标题、X消息和旧式Y标题/Y+X消息兼容检查。f45 产品[全量187 passed、1 skipped](full-pytest.txt)；控制器后来新增的两项传输自检另行验证，不扩写旧日志计数。

| 实际环境/入口 | 本轮结果与原始响应 | 独立复核范围 |
|---|---|---|
| macOS独立serve-hub、CLI/MCP/Chrome | [result](mac-scope-run11/result.json)、[离线全部](mac-scope-run11/offline-all.json)、[共享会话](mac-scope-run11/split-scope.json) | 离线全项目三入口各用自己的引用完整读回；在线只读X、Y不经title泄漏、扩大区间不越界；旧无范围读与Hub重启引用 |
| Ubuntu普通用户、CLI/MCP/Chromium | [result](linux-scope-run11/result.json)、[离线全部](linux-scope-run11/offline-all.json)、[共享会话](linux-scope-run11/split-scope.json) | 同上 |
| Windows普通交互用户、CLI/MCP/Edge | [result](windows-scope-run11/result.json)、[离线全部](windows-scope-run11/offline-all.json)、[共享会话](windows-scope-run11/split-scope.json) | 同上；实际非管理员token，非SSH管理员冒充 |
| Ubuntu实际systemd用户服务 | [result](linux-hub-scope-run11/result.json)、[service-events](linux-hub-scope-run11/service-events.json)、[共享会话](linux-hub-scope-run11/split-scope.json) | 实际服务账户、重启PID、只读X及旧无范围读；不认领浏览器/离线全部 |
| Windows实际LocalService | [result](windows-hub-scope-run11/result.json)、[service-events](windows-hub-scope-run11/service-events.json)、[共享会话](windows-hub-scope-run11/split-scope.json) | CIM实际服务owner为LocalService；控制器提升权限单独记录；同上，不认领浏览器/离线全部 |
| macOS实际登录LaunchAgent | [result](mac-login-run11/result.json)、[补齐](mac-login-run11/backfill.json)、[归属传播](mac-login-run11/affiliation-propagation.json)、该目录login-service文件 | 在标题修复包重跑原主流程；服务定义/普通UID/PID/重启、停止保留与完整补齐 |
| Windows显式本机/全项目专项 | [成功新轮](windows-entrances-run14/result.json)、[三入口全部](windows-entrances-run14/combined-all.json)、[保留的上一失败](windows-entrances-run12-failed/result.json) | 实际保留一次10053并确认新扫描，实际选择仅本机项目/仅本机全部/联合全部，3/7/10个目标各用自己引用准确读回；失败不重标 |
| 三平台CLI全局归属 | [Mac](mac-global-cli11/global-cli.json)、[Linux](linux-global-cli11/global-cli.json)、[Windows](windows-global-cli11/global-cli.json) | 实际CLI两次取得同一G、预览确认U归G、强制来源头变化后重放仍保留、U2待定；Windows普通token/外层进程退出0可核对 |
| macOS系统级launchd | 未执行 | 必需E3；不能被登录服务、前台进程或CI替代 |

已完成[Mac/Linux独立平台复核](reviews/review-platform-scope-f45-mac-linux-v1.md)与[Windows独立平台复核](reviews/review-platform-scope-f45-windows-v1.md)，只认领交接的实际结果及画面。protocol_only旧生产者的scope文案通用，具体检查以实际模式/响应/断言为准，服务轮没有离线全部和浏览器证据。Windows外层调度收据与真实普通token/服务owner不能相互代替；结束时仍需核对任务级清理。

原主流程、三平台真实0.4.0组合及R1–R4的[d80原始结果](../20261122-candidate-d80de67/README.md)保留源版本，不改标为f45执行。d80→f45产品只改引用title，上传/控制/排序/恢复模块按manifest可核对相同字节；本目录补改动相关的真实读取与旧无范围语义。R005还有P1及必要缺证，最终影响与通过判定不能据此省略。

四项[入口/CLI全局归属独立复核](reviews/review-platform-entry-global-f45-v1.md)均通过其限定范围。另有本轮只读[清理观察](cleanup-observation/)：6个已知Mac登录注册不存在，6个已知Linux任务单元not-found/PID0且没有任务路径单元文件，4个已知Windows Hub服务与任务路径服务不存在、任务Python进程及调度任务为空。档案/原始证据保留供后续修复，不声称已删除所有任务文件；Mac系统级Hub从未启动。
