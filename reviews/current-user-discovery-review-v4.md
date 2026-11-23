独立正式复审结论：`passed`。本轮只复审 `AT-SMM-007` / SC8 / `TC-007-user-discovery`，认领且仅认领 `user-discovery-3`。没有阻塞发现。

目标为 `manual-user-discovery-f8-v4`，收据 SHA-256 为 `66d838ba9b7dc5904359e64602d1360b8a17aaa824437e8f99ef8ee45c9e1b41`。定义 SHA-256 为 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`，设计为 `design-sc8-final-v3`。产品范围为 F8 修复 `b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da` 的当前源码及 v5 独立安装包，以实际模块摘要核版本。

已实际读取项目 `AGENTS.md`、007 `spec.md`、`plan.md`、`acceptance/manual-cases.md` 的用户发现第1–6步、SC8设计分配、handoff及验收技能的独立 Reviewer 规则。判定依据为本次原始观察与断言，不继承先前 passed。正式 JSON 已先写入 `review-inbox/review-manual-user-discovery-f8-v4.json`，并通知主 Agent 登记；本报告不替代原生登记。

1. 版本与证据链。49 个 bindings、104 个 artifacts、103 个 attachments 全部逐 SHA-256 相符。两个 original-copy-manifest 的71份用户路径原件和24份浏览器隐私原件，源文件与归档副本长度、摘要、字节均相符。当前四份用户文档与运行快照的摘要一致。Local 30、Hub 31 模块逐项检查源码、wheel、实际安装字节；Hub vendor 模块按 `scripts/build_packages.py` 的复制/命名空间变换核验，无不一致。

| 当前文档 | SHA-256 |
| --- | --- |
| `README.md` | `fa79b2c7f2b9169c5ce9813d4b2b22be2673c1f8608681886e3e5e992f996030` |
| `TRIAL_GUIDE.md` | `a64b30392c6f4613c85bb908928137136b00799585acb835744cff26edab2ba3` |
| `skills/smm-search/SKILL.md` | `8198ce2cc99dd3f9e854287bcb7e8c4968ab799f626df9c7bb625b07892e8425` |
| `scripts/acceptance/README.md` | `767639b4a9d24dc7b73e6a1b640c7d0205688be149e38ea4ed8cfdba864b6f1c` |

2. 实际运行范围。冻结的 `actual-discovery-wrapper.py` SHA-256 为 `7af99ead475f21498589db9c3a1773b51172c77635c5d7117e128ff632c1692e`。实际顺序为一次 prepare、既有 C-D-E 合成关联准备、真实 stdio、Hub Web、Local Web、旧页面 CAS；`PreparedOnce` 使 observe 内再次调用 prepare 不重建夹具。四份 trace 的 `src/` 源资源与冻结 wrapper/platform/user_paths/privacy 源码摘要一致。未从初版漏关联失败或第二版无 stdio 的记录拼凑本次结果。129条 CLI/安装命令的原始双流 base64 与文本字节一致，退出均为0；预期 HTTP 拒绝单独保存。

3. 普通用户、Agent与维护者发现。实际核 README 的未发布边界与指南链接，指南提供独立双包安装、来源所属电脑、项目/来源ID、稳定KEY/HID/generation、不透明state的取得、默认不同步、允许/暂停/撤回/恢复、共享文件版本与联合/本机范围。Skill 给出只读来源列表→项目身份→文档查询→精确 read，创建端管理与凭据取得可发现。维护入口链接自然语言步骤、隔离探针、依赖与当前私有证据，明确尚未覆盖项不能计通过。三条实际 CLI 帮助退出0。这里的暂停/恢复部分为使用说明的发现核验，不冒称完整生命周期已运行。

4. 双端项目文档库。已打开 `web-a-literal-original.png`、`web-hub-literal-original.png`，画面显示各自新项目身份、chosen.txt/dropped.md 两份独立资料、精确原文、出处和版本；script/img 标记原样可见。另直接从两份 ZIP 内存读取并显示项目创建完成后的原始 screencast，看到本机 #5、Hub #8 创建成功与对应选项。完整 trace 中可定位文件选择、`DataTransfer` 拖放、按所选项目搜索、两个独立上传ID的逐份 read、更新版本+1、删除后仅剩另一ID。原网络资源给出两个创建端分别不同ID、相同独立规范化期望正文；实际读取断言同时比较 ID、正文、Unicode端点与LF行号。重复/误指第二目标负控均拒绝。更新后新正文与旧ref拒绝在命令原件中，删除后搜索资源中只有 dropped.md。

5. 默认同步关闭与创建端只读。`commands.json[110]` 的 Hub webneedle 查询仅有 Hub 自有 dropped.md（`067c0fd48f6d498e8da1f0e619b91ced`），没有 Local 上传资料；Local 项目 enabled=false。允许并 sync 后 `[120]` 的正确投影项目恰命中 Local dropped.md 的原始ID `9c5bfaf6f0064d3fa4438d57de760d9b`，并准确读回。已打开 `web-hub-device-readonly.png`，见设备来源、只读说明与隐藏写控件；Local画面/轨迹显示Hub管理入口与查询范围。8次越端添加/更新/删除/配置请求均为400，每次比较 API来源/文件/库、完整文档表摘要及管理副本逐文件SHA/长度/mtime不变。

6. 纯文本与项目范围。`literal-display-a.json`、`literal-display-hub.json` 均含 new-project、query-snippets、original-chosen.txt、original-dropped.md 四阶段，实际断言 window 两标记未设置、`main img/main script` 数为0、所有资源请求中触发路径为空；四类恶化状态负控与双目标负控均拒绝。两条合法文件均真实读取，未只检查首条。已打开 `web-local-project-one-hop.png`，从只对话 C 查询仅得 D 的两份独立文档，排除第二层 E；`web-local-joint-read.png` 见本机私有、另一逻辑设备、Hub自有等完整集合及原文。C-D-E的CLI与stdio对话反查/read原件存在。

7. Agent真实stdio。`mcp-1.json` 的实际工具为 list_document_sources 默认/含Hub、list_projects含Hub、按项目 search_documents；`mcp-3.json` 有 A/B 四份逐独立原文的 read_document：B two、B one、A one（emoji/LF）、A two。`mcp-5.json` 为完整all文档查询，`mcp-7/9.json` 为对话反查/read。实际 MCP 工具 schema 核三个文档工具只读注解；五组子进程分别 PID7395/7397/7399/7401/7403，均 exit0、alive=false。此证据只证明本项分配的 Agent发现/真实工具操作；私有/Hub自有资料在该stdio脚本中只有search的问题仍归完整E1缺证。

8. 两条真实旧页面。实际打开 `same-hub-before.png`、`same-hub-old-generation.png`、`switch-hub-before.png`、`different-hub-equal-generation.png`，分别见原选择代次、暂停的新代次与两种红色错误。完整 `stale-pages-trace.zip` 的网络原payload与冻结对象逐字段相等：同Hub旧G1提交时新G2；第二次旧H1/G2提交时已切H2且恰G2。请求始终携旧稳定KEY/HID/G，两个响应400分别说明代次变化、Hub身份切换。两个JSON的 before/after 完整状态逐字段相等，覆盖全部5个项目及顶层状态。没有提交前重新取当前状态替换旧值。

9. Hub认证隐私。实际打开 `privacy-anonymous.png`、`privacy-authenticated.png`、`privacy-reloaded.png`、`privacy-reauthorized-read.png`：匿名和刷新后仅连接空壳，选文件后显示项目和资料，重选后恢复准确 D native one 原文。实际 browser-privacy.json 的四阶段 URL/localStorage/sessionStorage/cookie 均无 token。独立检查完整 trace 的12个原请求：10个认证均只到同源、正确Authorization，URL、其他请求头、请求正文无token；匿名/重载至重选前无API或认证请求。源码与trace实际执行 evaluateExpression/cookies/真实文件选择/reload/read，不是以静态HTML或401替代。检测器也拒绝URL与三存储面含token的反例。

10. 原图与完整轨迹、清理。共实际打开13张关键PNG，另显示ZIP内两端创建前后原始帧。四份完整ZIP均CRC正常；读取全部trace、network、snapshot、源码及157个resources，逐资源SHA1与文件名一致，无action error。用户路径、second-context及隐私任务的 cleanup/stopped-processes 保存实际PID退出与端口关闭，stdio五组也有独立退出收据。未启动产品、未重跑测试、未操作服务、ESXi或日常材料。

原始证据入口：

- 用户路径归档：`.acceptance-local/native-v1/AT-SMM-007/work/manual-evidence/user-discovery-f8-current-v4/`；其原件根为 `/private/tmp/smm-007-user-discovery-current-v3/`。
- 隐私归档：`.acceptance-local/native-v1/AT-SMM-007/work/manual-evidence/browser-privacy-f8-current-v4/`；其原件根为 `/private/tmp/smm-007-browser-privacy-v3/`。
- 冻结源码：`.acceptance-local/native-v1/AT-SMM-007/work/runner-snapshots/user-discovery-f8-v4/`。

当前证据足以支持完整 `user-discovery-3`。本结论不包含完整E1生命周期、三平台、E2系统服务或物理跨机器；既知E1私有/Hub自有stdio原文及重启后Web/stdio缺证保留，不以本项passed替代，也不把未分配给本项的E1门槛扩成它的阻塞。
