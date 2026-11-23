# SCM 程序权限准备修订独立审查 v2

结论：本次限定的第二次准备修订可接受，未发现阻断此次 Windows 实测的明确问题。候选将任务程序树的权限保护改为“根建立可继承权限、子项恢复默认继承”，并在 Hub setup 前新增真实解释器启动及安装模块完整性正控。此结论是静态准备审查，不是 Windows ACL 修复已实证、E2 SCM/LocalService passed、正式 TC passed 或最终 PR Review。

## 范围、版本与依据

- 审查根 `/private/tmp/smm-007`，HEAD `873b500dcd93062eaa0cdab6c7c332c3fc6bd080`。本次代码差异限定于 `scripts/acceptance/hub_documents_scm_platform.py`（23 行新增、1 行删除）及 `hub_documents_ci.py`（白名单增加 `program-access.json`）。其余当前文档/验收文件变动未据此认领完成。
- 候选 SCM helper SHA-256：`193c7a6dfc08855c194576e3c28e2b33369ad96d970e903c088322a71d275de5`；CI helper：`27f61feb34eab39003f0590f176df693b9560aeaf365eedd5254483d4bc45a6b`。意见绑定上述字节。
- 已实际阅读项目 `AGENTS.md`、007 SPEC 的 B5、边界与平台验收要求，PLAN 的准备、E1/E2、证据规则及历史修订，验收 README、首次证据回收修订独立意见，以及交付验收技能的准备、探针自检和独立 Reviewer 规则。SPEC 要求实际 SCM/LocalService 身份及跨进程档案访问，管理员前景不能替代；PLAN 要求独立任务目录、业务退出与回收失败分开保留、原件/SHA 和真实清理证据。
- Reviewer 对代码、旧证据只读；仅写本报告。未连接 Windows、ESXi、日常 Hub 或其他服务，未修改产品、测试、旧证据或原生验收结果。

## 原件支持的失败边界

实际读取 `/private/tmp/smm-007-ci-windows-diagnostics-v5/007-scm-public-evidence/platform.stderr`、`platform/commands.json` 和 `platform/service-cleanup.json`，另核 `names.json` 和 `selective-download.json`。三份业务原件 SHA 均与 selective-download 清单相符：

| 原件 | SHA-256 |
|---|---|
| platform.stderr | `626d1e1fd6b13d275ca3a8173b87a1fd74fd7c12acc16f9143a2ecdb4400f291` |
| platform/commands.json | `abf3d34a60fe072039f1156d168705075612f7e34b2a68ae392a3386c4422d5c` |
| platform/service-cleanup.json | `989104dfbec20d94945f7a55938c527d61694cafe6778ed8789219108dde8dd2` |

`commands.json` 仅有 openssl 和 protect-task-programs 两条已完成命令；后者实际带 `/inheritance:r /grant:r … /T`，退出 0，原 stdout 末尾报告成功处理 3243 个文件、失败 0。该退出 0 只能证明 icacls 命令完成，不能证明随后程序可执行。

`platform.stderr` 的首个异常在 `manager.cli("hub", "setup", …)` 经 `subprocess.run` 到 `_winapi.CreateProcess` 时产生 `PermissionError: [WinError 5] Access is denied`；没有 Hub CLI 已启动、服务已创建或 LocalService 业务失败的证据。cleanup 的 WinError 5 对应后续 disable 同样不能启动解释器；`sc delete` 返回 1060 表示当时目标服务不存在。不能将这两个清理错误改写为产品服务业务失败，也不能将其认作完整 PID/端口清理成功。当前下载为选择性材料；names 列出但本地未下载的 evidence-unavailable/sha256 等文件，本报告不声称已打开或完成全 artifact 核对。

## 权限、路径与身份核对

1. SCM helper `:254–270` 的 `packages` 仍从受控 CI 配置的 `…/packages/hub-env/Scripts/python.exe` 上推三层取得；CI helper `:205–227` 在新建任务 work 下构建该配置，不接收 ordinary IPC 传入任意路径。保护命令取消 `/T`，只对 packages 根去继承并授 Administrators/System F、LocalService RX；随后 `/reset /T` 目标是 `packages/*`，不包含 packages 根本身。没有将重置范围扩大到 work、系统 Python 或系统目录。
2. `Probe.__init__` 将实际 Hub 状态建在独立 `out/hub`；它不是 packages 子项。新 diff 不触碰 Hub 状态 ACL、资料/密钥目录或外部来源。packages 内已有包探针合成 state 会随程序树重置，不能与实际 SCM Hub state 混称。没有发现本次 diff 对 Hub state 放宽权限。
3. 后续标准账户包装器仍只对 `ordinary-client` 授 M，对 `ReadPath=packages` 授 RX；两份 wheel 的既有 reset/R 流程未改。packages 根已移除上层继承，因此 client 的 M 不会传播到程序树；本次没有给标准账户新增写程序权限。普通 worker 仍实际要求 `is_admin=false`，其 Hub 数据库直接读取必须被 PermissionError 拒绝。管理员 CLI、LocalService 和标准 Local 的角色断言均未放松。
4. 微软 [icacls 官方说明](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls) 将 OI/CI 定义为目录继承标志，reset 恢复匹配项的默认继承 ACL，T 遍历子项；这支持本候选的修正方向。旧命令逐文件移除继承与随后 exe 启动拒绝相邻，但旧原件没有 exe 的实际 DACL，故仍不能断言权限根因已百分之百确认。新候选的有效权限、遍历和 LocalService 执行结果须用真实 Windows 原件判定。

## 新增正控与证据

- SCM helper `:272–289` 先记录实际 Hub exe 的 icacls 输出，再直接以该配置解释器运行 `-I -X utf8 -c`：从安装位置定位 smm_hub，读取独立构建时生成的 hub-expected 映射，并逐项重算全部期望模块 SHA。构建探针原有源码→wheel 成员全集→安装字节检查未改；正控不替换 manifest、不重新安装包、不通过源码 PYTHONPATH 启动，也不访问 Hub 档案。
- 它在真实子进程内读取 IsUserAnAdmin、返回 sys.executable 和核对数量，并要求管理员身份及成功核对后保存 `program-access.json`。实际解释器无法启动、manifest 不可读或任一摘要不同都会使正控失败；setup 尚未开始。该正控覆盖管理员对真实程序的启动/读取与未换模块，不能证明 LocalService 已能执行，后者仍由原服务启动、实际 SID/session、业务及重启检查承担。
- CI exporter 仅增加上述准备收据名；该收据仅含身份布尔值、解释器路径、模块数量及成功标志。commands 原件继续保存 argv/stdout/stderr 与原字节编码。原凭据/私钥/数据库/wheel 排除、trace 加密、不完整回收仍失败的规则均未放松。路径仍应按 PLAN 在后续公开副本中脱敏，不据白名单静态审查声称真实日志已完成隐私审计。
- 原 cleanup 逻辑未改。新正控位于 setup/installed 标记前；若它失败，则没有本次服务 setup 副作用，不能因没有 service-cleanup 收据反推服务清理成功。若进入 setup 后失败，仍需区分原始首错和 finally 的派生错误，保留已回收原件与缺件说明。

## 本机验证与后续适用性

Reviewer 用 Python 的内存 compile 核对两份当前 helper 语法有效，`git diff --check` 通过；没有在只读审查中生成 pycache。已打开 `/private/tmp/smm-007-export-after-program-fix.stdout`（SHA `66cbc148b2485ae3287d464c2040b89b83e2b0540d7b8dfe397b7e178e45b4bf`）：其合成回收自检实际报告通过，绑定当前 CI helper SHA。它证明该已知样本的回收行为，不是 Windows 程序 ACL 或新 program-access 收据的实际运行证明。

当前没有本候选的 Windows 新结果。可按原既定流程实测，不能提前授予 E2/TC passed，也不影响 E1 已实际取得的普通账户结果或物理跨 OS 缺口。此次为 E2 第二次默认准备修订；后续若再失败，应保留真实失败并暂停自动返修，不通过改名或拆分扩张轮数。提交本次修改时须按 AGENTS 在 PLAN 同步记录此次方案、原因及真实结果；当前 PLAN 尚停留在第一次回收修订“重跑待结果”的历史描述，不宜将其作为第二次修订已经执行成功的说明。
