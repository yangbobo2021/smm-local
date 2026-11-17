> 本文件保留首次验收历史。按已合并 SPEC #24 / PLAN #25 补充的平台验收入口见 [2026-11-17 新 SPEC 证据](platforms-2026-11-17/README.md)；旧“七项通过”不代替新平台矩阵。

# PR #21 验收证据索引

验收 ID：`AT-SMM-VIBEINSIGHT-003`。本轮按维护者确认的 SPEC 和仓库身份边界复验，
并补齐四项复审问题的公开材料。未向真实 VibeInsight 服务器写入或造数，本轮也未重新连接 staging。

## 本轮执行与重跑

自动测试与构建的源码提交为 `3053de7`。完整版本、执行命令、退出码、源文件、wheel 和证据文件的 SHA-256
见 [execution.json](execution.json)。独立复审后另补充通用原文核对指引和 PLAN，见 [docs-verification.json](docs-verification.json)；
没有改动该次执行绑定的产品、测试或探针文件，原报告保留执行时的文档哈希。
环境为 macOS arm64、Python 3.14.2、PostgreSQL 14.17。常规回归 **66 passed, 1 skipped**，
跳过项是 Windows 专用检查，见 [pytest.log](pytest.log)。独立发行包构建见 [build.log](build.log)。

默认回归不依赖 PostgreSQL。来源同步测试使用合成事件，真实 Hub、CLI 和 stdio MCP 在本机运行。
开启导出及运行两项可选探针的完整命令见[探针使用说明](../../../scripts/acceptance/README.md)。
PostgreSQL 探针只在自建临时数据库造数，Hub 的来源查询在只读事务执行；不能将此探针当作真实 staging 记录。

以下 JSON 保留合成会话的实际正文、位置、来源、检索范围及状态；临时路径标记为 `<fixture>`，
调用方当前会话标识标记为 `<current-session>`。随机的 Hub/设备标识来自临时夹具。
脚本只在断言全部通过后写成功报告，重跑应使用新的输出目录，不能将旧报告误作新执行。

## 七项 SPEC 对照

| SPEC | 用例与实际证据 | 可复核的通过判据 |
| --- | --- | --- |
| 1. 全部可读项目 | [`test_all_visible_projects_and_historical_discovery`](../../../tests/test_vibeinsight_sync.py) 的[响应](pytest/test_all_visible_projects_and_historical_discovery.json)；[postgres.json](postgres.json) 的 `initial_search`、`after_project_discovery`；管理进程的[响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) | 起初 alpha、beta 可读，后增加较早 gamma 历史仍可读；实际 SQL 行可见性变化后第三项目补齐。管理命令断言拒绝输出合成密码。 |
| 2. 凭据持久与追加 | [`test_resume_appends_to_same_conversation_in_source_order`](../../../tests/test_vibeinsight_sync.py) 的[前后原文](pytest/test_resume_appends_to_same_conversation_in_source_order.json)；[管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `initial_read`、`resumed_read`、`before_restart`、`checkpoints` | 单会话 6 条消息（3 轮）追加为 10 条（5 轮），标识保留，重复拉取不增；实际停止、重启 Hub，无密码文件仍续跑。同步位置从 `event-0016` 推进到 `event-0024`。无效凭据替换被拒绝，原配置保留。 |
| 3. 双向单层关联 | [管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `links`、`cli_a`、`cli_b`、`after_unlink`；[`test_project_links_filter_before_ranking_and_follow_only_one_hop`](../../../tests/test_federation.py) | A 仅命中设备甲、设备乙、Vibe A；B 仅命中设备乙、设备甲、Vibe B 的两个会话；关系去重为三条；解除后 A 仅命中两设备，全局仍保留 Vibe A。 |
| 4. 同名、改名及历史 | [管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `project_list`、`cli_a`、`old_reference`；[upgrade.json](upgrade.json)；仓库变化的 [host](pytest/test_repository_identity_change_requires_new_link%5Bhost%5D.json)、[port](pytest/test_repository_identity_change_requires_new_link%5Bport%5D.json)、[path](pytest/test_repository_identity_change_requires_new_link%5Bpath%5D.json) | 两设备同名但身份不同，显示名修改保留关联；旧档案由真实旧 Hub 建立并原地升级，补归属后分别命中，旧引用保留。仓库身份变化后新旧项目 ID 不同，原关联不变，全局可查新项目；新增关联后项目检索包含新会话。 |
| 5. CLI/MCP 与原文 | [管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `cli_a`、`mcp_a`、`cli_reads`、`exact_reads`；[postgres.json](postgres.json) 的 `cli_search`、`mcp_search` | 两入口有效项目集合相同；两类来源均用命中返回的 Hub/消息引用精确读取，正文、角色、位置与独立合成预期一致。样本 `device-a` 为 `evidence from device-a`，Vibe 样本为 `evidence vibe-A 20`。 |
| 6. 回退与旧客户端 | [管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `offline_cli`、`offline_mcp`；[postgres.json](postgres.json) 的 `legacy_client_search`、`legacy_client_read` | 停止 Hub 后两入口均返回本机全局、回退原因并命中两个本机项目。Git 基线 `d2dee18` 的实际旧客户端能上传、全局检索和读取新 Hub。 |
| 7. 失败重试与去重 | [回滚前后进度](pytest/test_archive_and_cursor_rollback_together.json)；[重试和迟到原文](pytest/test_failed_batch_retries_and_late_event_is_read_once.json)；[管理进程响应](pytest/test_managed_hub_credential_restart_and_mixed_project_search.json) 的 `recovered_status`；[postgres.json](postgres.json) 的 `sql_pages`、`resumed_read` | 注入批中写入失败，消息和进度一同回滚，恢复后整批可读。重复同步和迟到事件不重复。实际 SQL 同时间按 ID 分页得到 E020/E021/E022；历史原地改写未覆盖已归档正文。 |

测试函数均在仓库中，可以按上述名字运行单项。完整断言包含未导出的错误凭据尝试、故障注入及去重检查；
导出的 JSON 是断言通过时的选定观察值，不能代替阅读测试断言。可选探针的退出日志见
[postgres.log](postgres.log)、[upgrade.log](upgrade.log)，脚本与实际包内容均有哈希绑定。

## 四项复审问题的处理

1. [检索 Skill](../../../skills/smm-search/SKILL.md) 移除了“所有 Hub 请求都是全局”的过时说法，按实际响应报告范围。
2. [使用指南](../../../TRIAL_GUIDE.md#3-实际提问) 区分 Web 本机关联与 Hub CLI 关联，并链接到管理命令。
3. [README](../../../README.md#搜索-vibeinsight-和关联项目) 从主入口介绍能力、适用角色，并直达连接准备和关联管理。
4. 本索引、可重跑脚本、实际响应、进度和构建身份共同替代只有 PASS 摘要的证据展示。

维护者于 2026-11-17 同意显示名与仓库身份变化的边界，已更新 SPEC、PLAN 和指南。
本机 PostgreSQL 的实测结果仅存放于验收材料，没有写入 SPEC。

返修的[首轮独立复审](review-initial.md)确认上述四项及七项受控验收证据，并发现通用原文核对说明仍将 Hub 命中引向本机 Web。
据此修订指南的提问和故障复核段落，限定本机 Web 的适用档案，明确 Hub 沿用返回引用读取原文；产品运行时未变。
最终修订的独立复核见 [review-final.md](review-final.md)。所有公开材料的校验和见 [SHA256SUMS](SHA256SUMS)，可在本目录运行 `shasum -a 256 -c SHA256SUMS` 核对。

## 真实 staging 历史实测及边界

[staging-2026-11-16.json](staging-2026-11-16.json) 是当时原始回执的脱敏摘录，保留时间和两个实际提交：
`85280fb` 从空档案开始，四小时 SQL 时限处中断时有 111,587 条消息；`c891339` 从已提交进度继续，
新增 1,669 条，最终 **142 项目、20,325 会话、113,256 消息**，整轮成功。
两段合计 11 次受保护的 Hub `psql` 调用，均要求只读事务，服务端无写入；独立 Hub 已停止。
CLI/MCP 样本的会话、事件、位置和原文均与上游一致。

真实地址、账号、凭据、项目和会话/事件标识、检索词、正文及正文摘要不公开。
因此该回执支持“当时确实执行了 staging 整轮同步”的历史结论，不能由公开字段独立复算正文相等，
也不将其冒充本轮新执行。可独立复跑的完整响应验证由上述合成夹具承担。
此前 staging 账号具备写权限，但所有访问均按用户授权限制在只读事务；客户端当时未报告 PostgreSQL TLS/GSSAPI 加密。
真实生产、Windows 服务/ACL 和生产性能基准未验证。原地改写旧消息且不新增事件仍为首版明确边界。
