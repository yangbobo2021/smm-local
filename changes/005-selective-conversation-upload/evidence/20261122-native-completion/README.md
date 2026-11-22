# 005 原生十二场景补齐记录

当前原生定义为 v3，SHA-256 `493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e`，对应已确认 SPEC `879c904b7217dda4124079094d7f0fa7f96e4554436516385d3d262b0293882e`。十二场景及 65 条当前用例均已登记 passed：52 条自动正式执行、12 条逐场景人工核验及 1 条 Windows 外部长轮新正式执行。独立 Reviewer 逐 SPEC A1–A12、E1–E5 判定 R005 passed 后，原生 `delivery-judge` 已实际接受登记（`status: judged`、`judgment.status: passed`），当前结果视图的 R005 也为 passed。见[真实判定收据](delivery/delivery-r005-complete32-v1/result.json)和[独立意见](reviews/delivery-r005-complete32-v1.md)。

[当前结果索引](current-summary.json)列出每条 TC 的原生状态；[原生正式收据](../../../../.acceptance/native-v1/AT-SMM-005/)保存真实登记链。此前 blocked、insufficient_evidence、调试错误、超时及原判断均保留，未改标为成功。本目录是补齐后的新记录；旧证据目录按原事件时间和版本阅读。

| 场景 / SPEC | 当前状态 | 自动正式执行 | 人工记录 | 检查步骤 |
|---|---|---|---|---|
| SC1 / A1 | passed | [5 自动](formal-auto/execute-complete30-sc1/result.json) | [人工原件核验](formal-manual/manual-complete32-sc1/record.json) | [步骤](steps/SC1.md) |
| SC2 / A2 | passed | [9 自动](formal-auto/execute-complete26-sc2/result.json) | [人工原件核验](formal-manual/manual-complete30-sc2/record.json) | [步骤](steps/SC2.md) |
| SC3 / A3 | passed | [9 自动](formal-auto/execute-complete30-sc3/result.json) | [人工原件核验](formal-manual/manual-complete30-sc3/record.json) | [步骤](steps/SC3.md) |
| SC4 / A4 | passed | [9 自动](formal-auto/execute-complete30-sc4/result.json) | [人工原件核验](formal-manual/manual-complete30-sc4/record.json) | [步骤](steps/SC4.md) |
| SC5 / A5 | passed | [1 自动](formal-auto/execute-complete26-sc5/result.json) | [人工原件核验](formal-manual/manual-complete30c-sc5/record.json) | [步骤](steps/SC5.md) |
| SC6 / A6 | passed | [2 自动](formal-auto/execute-complete26-sc6/result.json) | [人工原件核验](formal-manual/manual-complete30-sc6/record.json) | [步骤](steps/SC6.md) |
| SC7 / A7 | passed | [4 自动](formal-auto/execute-complete30-sc7/result.json) | [人工原件核验](formal-manual/manual-complete30-sc7/record.json) | [步骤](steps/SC7.md) |
| SC8 / A8 | passed | [4 自动](formal-auto/execute-complete30-sc8/result.json) | [人工原件核验](formal-manual/manual-complete30-sc8/record.json) | [步骤](steps/SC8.md) |
| SC9 / A9 | passed | [4 自动](formal-auto/execute-complete31-sc9/result.json) | [人工原件核验](formal-manual/manual-complete31-sc9/record.json)；[Windows 新执行](formal-manual/manual-complete31-windows-empty/record.json) | [步骤](steps/SC9.md) |
| SC10 / A10 | passed | [2 自动](formal-auto/execute-complete30-sc10/result.json) | [人工原件核验](formal-manual/manual-complete30-sc10/record.json) | [步骤](steps/SC10.md) |
| SC11 / A11 | passed | [3 自动](formal-auto/execute-complete30-sc11/result.json) | [人工原件核验](formal-manual/manual-complete30-sc11/record.json) | [步骤](steps/SC11.md) |
| SC12 / A12 | passed | — | [人工原件核验](formal-manual/manual-complete32-sc12/record.json) | [步骤](steps/SC12.md) |

## 证据时间与版本

- `formal-auto/` 是本轮真实原生 execute：共用测试重新运行产品逻辑，旧非空档案升级、真实新旧 stdio MCP、备份后新增消息和限制的恢复，以及 Mac/Linux 三入口成功空结果使用最终安装包另起合成档案运行。过程命令、起止、退出、响应及必要画面均保存。
- `formal-manual/` 的十二个场景人工项是**本轮核验旧平台原件与当前版本适用性**，并非本轮重跑全部平台业务。原始事件的时间、来源提交、安装模块、普通/服务身份和清理仍保留；本轮观察另有自己的时间、原件摘要和独立意见。`source-regression/audit-*` 仅为离线正文/范围/公式核验，不能代替原始业务执行。
- `windows-formal/` 则是新增 Windows 普通 Limited 身份空查询的**新正式执行**：外部命令实际 2026-11-22 11:06:33.033069Z—11:11:43.051752Z、exit 0，worker 11220 exit 0。六个 CLI/MCP/Web project/all 空响应、正控、两个画面、轨迹摘要和清理原件完整。先前 320.432 秒试跑虽远端成功，原生自动命令已超 300 秒上限，仍保留 timeout/null；未用回收旧结果替代本次执行。更换人工记录编排经过独立准备审查，未修改工具上限或检查条件。
- 最终安装包产品来源 `ba8c6d5e86dbe0ecbb58214db14a22d4a556b7a0`；本轮源码/测试/控制器提交 `5f14cde73fd8135c97718067822e2e6e7025861c`。两者 `src/` 产品字节相同，见[完整模块与差异清单](current-product-bytes.json)。包元数据仍为未发布 0.4.0，通过来源提交、wheel 及安装模块 SHA 区别正式旧包和候选。较早真实平台候选仅复用于未变化调用路径，后续范围/对账实际安装包专项及当前专门回归补足改动，详见人工原件与独立意见。

## 平台与覆盖

真实 macOS、Ubuntu、Windows 普通客户端涵盖三入口、四模式、归属/全局、项目/全部/显式本机、原文/版本/排序、断线与重启；成功零命中另在三平台各入口新执行。macOS 登录服务、实际系统级 launchd Hub（UID 501、PPID 1）、Ubuntu systemd、Windows LocalService 的原始注册/运行身份、重启和清理均关联到场景。三系统真实 0.4.0 兼容组合，Local/Hub prepare-restore 与实际 systemd 恢复、升级健康失败恢复的限定范围均保留。

R4 的包安装仍是已披露的离线成功桩，不声称验证真实发布/下载或未来版本迁移。005 使用隔离的合成 Agent 与合成 VibeInsight 档案；本轮不连接或写入真实 VibeInsight/PostgreSQL，不升级日常 SMM，不修改真实对话。

[完整源码回归](source-regression/full-pytest.stdout)为 251 passed、1 skipped；[5f14 三系统 CI](https://github.com/yangbobo2021/smm-local/actions/runs/45016214762)全部成功，Mac/Linux 各 251 passed、1 skipped，Windows 252 passed，均构建并分别安装 Local/Hub wheel。见[实际 CI JSON](ci-source-5f14.json)与[日志摘要](ci-source-5f14-summary.txt)。历史 234/80 项结果属于较早轮次，未改写成这轮结果。

## 复核与脱敏

[独立准备/执行意见](reviews/)与[原生 review 登记](native-current/review/)绑定各自实际 target SHA 和 Reviewer。执行审查检查原始请求/完整正文及引用、实际画面与服务身份，不仅接受 result.status。SC1 最初人工核验缺三平台兼容原件的 insufficient_evidence 保留，新 SC1 原件分包重新核验后才登记 passed。

[source-evidence-links.json](source-evidence-links.json)将人工收据中的每个私有原件路径和 SHA 对应到现有或本目录公开文件；字节相同的附件复用同一公开副本，实际运行身份以原始路径和各运行 manifest/命令为准。大 trace 仅在私有原件保留原 SHA，公开的完整业务 JSON、必要 PNG 与审查意见支撑通过判定，未将缺失补充 trace 当作新的业务执行。

[provenance.json](provenance.json)记录原始与导出两个 SHA；文本副本替换测试账户、主机/IP、个人绝对路径与会话专属环境路径，保留合成消息、路由身份、版本与原始时间。已冻结的匹配步骤源按原字节保留，其中通用 `/private/tmp/smm-005-control-env/bin/python` 命令仅表示隔离测试解释器，不含账户、主机、随机会话或凭据；该源文件的原 SHA 继续作为实际匹配输入。无凭据配置、Token、私钥、数据库、wheel 或原始 trace 导出。`SHA256SUMS` 校验公开文件；README、摘要、映射和差异清单为派生索引，应结合原始过程和独立意见阅读。

## 最终收尾

[新的 PR 独立审查](reviews/pr-review-complete32-v1.md)无未关闭的可行动发现，记录了两项索引/导出缺口及其关闭依据；新增维护者复跑说明已同步 `scripts/acceptance/README.md`。原生 [finish 实际返回与快照摘要](delivery/finish-r005-complete32-v1/result.json)为 `finished`，采用实际有效 R005 passed 判定，没有使用 allow_unfinished。

[最终看板读回](dashboard/checkpoints.json)逐条记录 R005 与十二场景的实际状态、快照/收据摘要及真实截图；[总览](dashboard/001-overview.png)显示 12 个通过场景、65 条当前用例、0 个产品缺陷，[需求详情](dashboard/002-R005-passed.png)与各场景详情均为通过。看板只展示原生落盘数据，不代替原业务验收。

原生 finish 的完整原始快照含全部原始意见及本机路径，保留本地原字节，并由 `.gitignore` 排除公开提交；上面的公开收据保存真实幂等读回返回、原始快照 SHA/大小、R005/十二场景状态和未完成清单（均空）。它是可核对的脱敏摘要，没有修改原快照或工具判定。
