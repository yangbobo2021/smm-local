# 固定验收记录

以下为本轮评估开始时读取的 PR #21 正文节选。保留验收结果，省略既有审查结论和早期失败记录。

## 变更

依据已确认的意图 #18、规格 #19 和计划 #20，Hub 通过只读连接同步 VibeInsight 可读取的全部项目，CLI 和 MCP 按当前项目及 Hub 中的直接关联查找并读取原文。现有设备历史可补传项目归属。同步凭据与进度跨重启保留。实现选用 `psql`，常规测试用可控上游夹具。

## 验收

验收 ID `AT-SMM-VIBEINSIGHT-003`，验证提交 `963a8f7`。

### 验收环境与真实服务器覆盖

| 环境 | 状态 | 证据范围 |
| --- | --- | --- |
| 本机隔离 PostgreSQL 14，使用合成 `fact_events` | 已验证 | 独立安装的 Hub wheel 走实际 `psql` 查询、只读账号和 SCRAM 认证，并验证本机 HTTPS、CLI 和 MCP。 |
| 真实 VibeInsight staging | **完整只读同步通过** | 独立 Hub 从空档案开始，上游超时后从持久化检查点续跑并完成整轮同步。CLI/MCP 均搜到并读回同一条消息，与 staging 原始事件核对一致。见完整复跑回执。 |
| 真实 VibeInsight 生产 | 未执行 | 本次补验只连接 staging。 |
| 生产规模吞吐、Windows 服务和 ACL | 未验证 | 本次验证使用本机合成样本。 |

下面七项结论适用于本机夹具和隔离 PostgreSQL 环境。

| SPEC | 结果及证据 |
| --- | --- |
| 1. 自动拉取全部可读取项目 | 通过。夹具覆盖初次导入和可见性变化。隔离 PostgreSQL 的行可见性探针确认较早的第三个项目自动补齐。独立检查验证配置输出、Hub 日志和 SQLite 数据库中无合成密码。 |
| 2. 凭据持久与旧会话续写 | 通过。新进程沿用同一个状态目录，原会话从 3 轮补到 5 轮且保留标识。本机隔离 PostgreSQL 的 SCRAM 拒绝错误密码，权限不足的替换账户也被拒绝，原凭据继续可用。 |
| 3. 跨设备和跨来源关联 | 通过。双端检索验证双向直接关联、重复建立、解除后的项目范围及全局检索。共享会话与跨仓库会话按消息所属项目过滤。 |
| 4. 同名、改名和已有历史 | 通过。基线 `d2dee18` 的 Hub 创建档案后原地升级，补传项目归属后同名项目可分别搜索，旧对话和旧消息引用保留。设备项目改显示名后关联有效。 |
| 5. 检索入口与引用可追溯 | 通过。CLI 和真实 stdio MCP 项目范围一致，两类来源的原文与返回引用可对照。另验证长预览中的一字命中仍归到实际来源项目。 |
| 6. 回退和兼容 | 通过。实际旧客户端上传、全局搜索、读取兼容。断线后 CLI/MCP 回退本机全局并给出原因。 |
| 7. 失败批次与重读去重 | 通过。注入归档中途失败，核对内容与进度一同回滚。本机隔离 PostgreSQL 验证时间相同的事件按 ID 分页、窗口内迟到回复和归属修正。旧消息原地改写保留已归档正文。 |

- 早期提交 `963a8f7` 的全量 pytest（Python 3.14）：61 通过，1 个 Windows 专用测试跳过。Python 3.12 定向复审通过。
- `python3 scripts/build_packages.py` 通过。两个 wheel 分别安装到干净环境，用独立 Hub wheel 跑隔离 PostgreSQL 14 与 HTTPS 服务，再用 Local wheel 验证 CLI 和 MCP。
- `git diff --check origin/main...HEAD` 通过。
- VibeInsight 仓库路径变化按新来源身份处理，设备项目显示名变更已验证。

### 本机执行日志摘录

```text
PASS: SQL page boundary with equal created_at, mixed-repository and unpaired trace attribution, and unsafe credential replacement refusal.
PASS: PostgreSQL SCRAM credentials and late repository provenance without changing the archived message.
PASS: independently installed Hub wheel with PostgreSQL 14 and managed HTTPS lifecycle.
PASS: read-only source, later-visible older history, same-timestamp restart, late completion, original edit preserved, original event reference.
PASS: independently installed Local wheel used CLI and stdio MCP to query Hub.
PASS: actual client from baseline d2dee18 uploaded, searched and read via the new Hub.
PASS: real prior Hub archive migrated in place; distinct scope, identities and old message references verified.
61 passed, 1 skipped in 98.98s (0:01:38)
```

### 真实 staging 完整只读复跑 · 通过

北京时间 2026-11-16T18:06:16+08:00 从空档案启动，2026-11-16T22:10:06+08:00 从检查点续跑，2026-11-16T22:21:19+08:00 结束。Hub 记录整轮成功时间为 `2026-11-16T14:21:17.093536+00:00`。

- 两段均使用独立安装的 Hub wheel 和同一份逻辑档案，通过实际部署的 VibeInsight staging 读取。首次提交 `85280fb` 在四小时查询上限处中断，已保存 **111,587 条消息**。提交 `c891339` 从持久化检查点续跑，新增 **1,669 条消息**并记录整轮成功。最终归档 **142 个项目、20,325 个会话、113,256 条消息**，持久化项目检查点 143 个。
- 按授权使用现有凭据。上游连接默认事务为只读，Hub 的每次 `psql` 调用均检查 `BEGIN READ ONLY`。两段共放行 11 次，拒绝 0 次。探针额外核对和原文比对在只读事务内完成。服务端没有写入或造数据；临时 Hub 已停止。客户端报告 staging 连接未启用 PostgreSQL TLS 或 GSSAPI 加密。
- 样本在独立安装的本机端 CLI 和 stdio MCP 都命中，精确读回的来源会话、源事件、消息位置与角色一致。正文和 staging 原始事件逐字相同。公开回执只保留比较结果。
- 初次实跑在逐项目分页处反复超时。修复后以固定上界的只读 PostgreSQL COPY 流传输，Hub 仍分项目提交内容和进度。首次完整流式查询达到时限后，将每个项目的回看窗口下界加入 COPY 查询，避免续跑时重新传输窗口前的历史。独立复审覆盖停服取消读取、读取中断续跑以及新可见项目的较早历史。复审在隔离 PostgreSQL 14 中核对了实际 COPY 输出，确认各项目的检查点和回看窗口生效，窗口内延迟事件仍能进入档案。普通回归 63 项通过、1 项 Windows 用例跳过。独立 wheel 的隔离 PostgreSQL、旧版客户端和旧档案升级验证通过。

```text
hub_sync_cycle_completed=true
resumed_from_saved_archive=true
sample=staging-message-01 source=vibeinsight role=assistant
cli_search=hit mcp_search=hit
same_source_event_and_session=true
same_cli_mcp_message_position=true
staging_cli_mcp_body_equal=true
upstream_default_transaction_read_only=true
server_writes=false
isolated_hub_stopped=true
```

