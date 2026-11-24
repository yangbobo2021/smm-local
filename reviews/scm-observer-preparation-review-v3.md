# SCM 观察流准备修订独立审查 v3

结论：本轮限定修订可接受，未发现阻断用户已明确批准的额外一轮 Windows 观测实跑的问题。它把管理员观察输出保留在父目录，同时继续观察普通账户实际使用的夹具及阶段，并补回独立管理员身份和源打开检查。本意见仅认定准备修订有效；尚无本候选真实 Windows 运行，不授予 E2 SCM/LocalService、正式 TC、需求或最终 PR passed。

## 范围与适用版本

- 审查根 `/private/tmp/smm-007`；HEAD `1ebac269c4d73225b9f50fee1bbbc352b04787a9`。
- SCM helper SHA-256：`aa1960f2649001938cc238add771b5bd9123a40dcbd3cfe1b6e49439dc0ce8b4`；CI helper：`e684e847be80e19e1ec8247ace557b950feb75bf58f47c434dabc500b2c0e21a`。当前 diff 与 `/private/tmp/smm-007-scm-observer-streams-draft.patch` 的行为一致，增加部分仅经 black 展开。
- 实际阅读 AGENTS、007 SPEC 的 B5/平台边界/A9/E2/证据要求，PLAN 的 E1/E2/证据要求、验收 README、`scm-evidence-preparation-review-v1.md` 和 `scm-program-preparation-review-v2.md`，以及交付验收技能、探针自检和独立 Reviewer 规则。SPEC 明确 Windows 管理 CLI 与实际 LocalService 分别取证、普通 Local 不得以管理员 token 冒充；外部源只可明确采集。PLAN 要求独立任务及原始输出/SHA、真实清理，不把回收失败与业务退出混淆。
- Reviewer 对产品、测试、旧证据只读，仅写本文件；便携检查只写自动删除的独立临时目录。未连接 Windows/ESXi/日常服务，未发 GitHub，未代正式执行或需求判定。

## 前轮原件确证与推断边界

实际核对 run `45187607945` 对应本地 diagnostics-v6 与 server-logs-v6 的 SCM 文件。两份 selective-download 指向 artifact `14823903677`；实际核验 diagnostics 的 32 份 SCM 已下载文件及 server-logs 的 2 份 SCM 已下载文件，SHA 均与各自下载清单一致。这是选择性下载核对，不声称下载或审阅了全部 artifact。

1. `platform/commands.json` 共 12 条。程序权限两步、实际解释器启动均退出 0；`task-program-access` 原 stdout 为管理员身份、`verified_modules: 31`、`readable_expected_modules: true`，随后 hub setup 退出 0。这证明 v2 已实际越过前轮管理员解释器启动阻塞，不代表完整服务业务已通过。
2. `platform/service-events.json` 两次记录同一实际 PID 7520、Running、LocalService、SID `S-1-5-19`、session 0。两条是同一次运行中的身份观察，并非两次重启成功证据。
3. `platform/ordinary-client/platform/scm-client-boundary.json` 明确记录普通 worker `is_admin: false`、Hub 数据库读取被拒。不能用该拒绝推断普通账户所有文件有效权限，也不能将其当成产品故障。
4. child `failure.json` 只定位到 prepare 启动 a 后 `('a', 'server exited')`。实际打开另一下载目录的 `platform/ordinary-client/platform/a-server-0.log` 后可进一步定位：`<string>` 第 6 行在 `open(SMM_007_IDENTITIES, 'a')` 追加 child `process-identities.jsonl` 时触发 PermissionError。bootstrap 在此后才安装审计钩子并 `runpy.run_module`，因此该次退出发生在产品入口之前；不能报告为 Local 产品已启动后崩溃。旧 env 把管理员 Hub CLI 的身份流写入此 child 路径，与冲突方向相符；现有原件没有该文件的实际 DACL，精确 ACL/所有者成因仍属推断。
5. child cleanup 记录 a PID 2132、退出 1、alive=false、已检查 PID 树 `[2132]`、端口关闭；child commands 中 disable 的 RPC 回执明确 `stopped_pid: 7520`。parent service-cleanup 记录目标服务及空 failures。结合静态 finally 的固定 disable/delete 和 PID/端口检查，可支持本次已到达的清理路径无报告错误；这些原件不能补成未完成业务、服务重启持久性或全局无残留的证据。未将空 failures 单独扩大成所有清理步骤均有原始命令输出。

关键原件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| diagnostics-v6 / platform/commands.json | `8cf609934d23ac64bfb61167e670829b0c8d3017e05558f2729c848e9527949c` |
| diagnostics-v6 / platform/service-events.json | `a0356b3cdadadb7c1e22b5b609f7557ed049fdc951d43b6521a776f2257bfd88` |
| diagnostics-v6 / child scm-client-boundary.json | `0672f994bca52176e7e9858eebd145251c7cae9fda0835b92375226dfb41fd0d` |
| diagnostics-v6 / child cleanup.json | `80cd9ef014773b1d834562410a827379effcaef402894b59403ace1f6c4e22a8` |
| diagnostics-v6 / platform/service-cleanup.json | `7aa4fedaa2d52133bf69d67d572f86413d1ae2f7b0654bcb7c7793393c79e752` |
| server-logs-v6 / child a-server-0.log | `a6d5022efa9f9ffd39dc49aecbb2107948b1d6bfcbb6b94fcbe1e5c15584efcd` |

上述 diagnostics 根为 `/private/tmp/smm-007-ci-windows-diagnostics-v6/007-scm-public-evidence`，server-logs 根为 `/private/tmp/smm-007-ci-windows-server-logs-v6/007-scm-public-evidence`；child 指 `platform/ordinary-client/platform/`。

## 新候选的覆盖与权限边界

- `Administrator.env:47–55` 不再覆盖 `SMM_007_IDENTITIES` / `SMM_007_AUDIT`，因此继承 `Probe.env` 的父目录日志路径。仅 Hub 角色在 child phase 文件已经存在时改用 child `资料 空格` 和 `phase.txt`；管理员实际 refresh 不会因观察错夹具而漏记，阶段也不再误用父 prepare。普通 Probe 自己的日志仍在 child 目录。此修订没有让标准账户获得父日志写权限。
- `administrator:374–401` 仍先要求普通包装器退出 0、child result passed；然后逐条要求父 audit 只出现 explicit-refresh / conversation-import，父身份流非空且每条均 `is_admin is True`、`argv[0] == smm_hub.cli`，随后才保存父 result。管理员记录移出 child 后没有从判定中消失。普通 Probe 原末尾逐条身份/源打开断言保留；SCM 实际 SID/session 校验未改。没有以一条管理员记录或最终 result 字段替代全部身份检查。
- CI exporter 原有 `process-identities.jsonl` 白名单按相对路径保留父/子两份身份原件，不因同名覆盖。本轮仅新增 `administrator-source-open-audit.json`，成功时保留父审计 entries 与检查回执；普通账户 `source-open-audit.json` 仍独立保留。凭据、数据库、wheel 排除及 trace 加密规则未改。
- 原始 `source-opens.jsonl` 两端均仍不在导出白名单；新回执是解析后的 entries，并非逐字节原始 JSONL。若新检查先失败，成功回执不会生成，不能把缺少该回执当作“无违规打开”或完整审计证据。本轮成功路径未遗漏父身份或父源打开判定；没有据此声称失败路径任意诊断均能完整回收。
- 当前 diff 未触碰 `src/`、标准账户包装器、packages ACL、Hub state ACL、实际服务身份、普通账户 Hub 数据库拒读或 IPC allowlist。既有 IPC 仍只接受固定操作、固定 Hub 档案，并对 documents add 限定 child fixture 根；不存在本轮新增可执行代码、任意 state-dir/服务名/程序写权限通道。本报告不把此有限差异核查扩大成整个既有 IPC 的安全审计。

## 独立便携复核

实际重跑 `/private/tmp/smm-007-observer-selfcheck.py` 退出 0，绑定当前 SCM helper SHA，证实父子日志路径不同、管理员 fixture/phase 仍指实际 child。已读原 stdout/stderr；stderr 为空。该脚本 SHA 为 `05ea07645beebde21b861cdef0ff1b7a2d2b6f22a52be3c391516416be0f1e0e`。

Reviewer 另在独立 TemporaryDirectory 中从当前 AST 提取实际新增父审计/身份断言块执行：合法管理员 Hub CLI + explicit-refresh 接受；archive-only 打开、非管理员、错误模块、空身份流四种负控均被实际断言拒绝。再用实际 CI exporter 导出父身份、父新回执、child 身份、child 审计，四份与输入字节一致且逐 SHA 验证，合成 hub-token 未导出。两份 helper 内存 compile 与 `git diff --check` 均通过。没有写 pycache 或改动仓库其他文件。

另实际读取 export-after-stream-fix.stdout，报告回收自检 passed，绑定当前 CI helper SHA；该结果仍只证明其合成样本。所有本机检查均不证明 Windows 内核权限、LocalService 后续业务或完整 E2。

## 后续停止点

本轮是默认两轮已经用完后，用户明确批准的额外一轮观察修订；不是重置自动返修计数。允许继续的是原限定的 Windows 新观测及其原件核查，不能先计 E2/TC passed。若该轮仍失败，应保留真实首错、回收缺件与清理状态并停止本项返修，不能改名或拆项继续消耗额外轮次。相关实际方案和结果提交时仍须按 AGENTS 更新 PLAN。本报告不代正式执行复审或需求交付判定。
