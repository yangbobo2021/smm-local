# SCM IPC UTF-8 准备修订独立审查 v4

准备结论：**accepted**。当前限定补丁可进入用户再次明确批准的一轮 Windows 实际执行及执行后独立复审。未发现本次两处编码修正的阻断问题。本结论只接受准备修订，不判 E2、SCM/LocalService 业务、正式 TC、需求或最终 PR passed。

## 范围与依据

- 审查根：`/private/tmp/smm-007`；HEAD：`795b5691d8aa22bb268f345c74551bcd1c6d170d`。
- 阅读本仓库 AGENTS、007 SPEC 的平台说明/A9/E2/证据要求、PLAN 最近 E1/E2 准备与失败记录（特别是 189–199 行）、PR Review Prompt、SCM helper 全文及前轮 v3 准备审查。维护者/验收执行者需要通过既有 SCM 探针得到真实服务业务与可复核原件；本次只修复该维护入口内部文件 IPC 的编码契约，不改变用户产品入口或发现路径。
- 本次授权是默认轮次及既往额外轮用完后，用户再次明确批准的编码修订/执行/独立复审各一轮，不重置历史轮次。PLAN 199 行如实记录该范围与失败停止点。
- 当前工作树还有其他文件差异；本审查不接受或否定它们，也不将它们算作本编码补丁。SCM helper 相对 HEAD 已独立逐字核验，恰为 `answer.read_text()` 和 `request.read_text()` 两处改成 `encoding="utf-8"`，无第三处变化；与所给 `/private/tmp/smm-007-scm-ipc-utf8-draft.patch` 一致。
- 审查绑定 helper SHA-256：`bf8ea3352bac48198f68be486520bd6c6be12cbee7487a887e76e1be3a5207dc`。Reviewer 对源码、原件只读，仅新增本报告；独立便携检查只在自动删除的临时目录写合成 JSON。未连接 ESXi、Windows 或日常服务，未执行实际业务、发起 CI 或修改其他仓库文件。

## 前轮实际失败的诊断

实际逐件阅读 run `45194460889` 的本地原件，根为 `/private/tmp/smm-007-ci-windows-diagnostics-v7/007-scm-public-evidence`。没有输出 commands 内可能包含的 token；命令记录仅提取 label、operation、exit_code 用于辅助定位。

1. `platform/standard-user.stderr` 与 child `platform/failure.json` 一致：普通 worker 已进入 `Probe.execute → prepare → source("hub") → cli → rpc`，在原第 171 行 `json.loads(answer.read_text())` 的文件读取阶段使用 Windows cp1252，遇响应字节 `0x9d`、位置 445 后抛出 `UnicodeDecodeError`。因此此次可确认的阻塞是测试 IPC 响应解码故障，不是 JSON 语法或产品返回断言失败。随后 PowerShell 找不到 `result.json` 是该异常后未生成成功结果的后果；最外层 `('platform', 1)` 仅是退出传播。
2. 这证实普通 worker 已越过前轮 bootstrap 日志写入故障。父 commands 共 15 条，已记录项 exit_code 均为 0；child 有实际 enable/archive_identity/两个已记录 hub_cli 回执及最终 disable。不能因部分命令成功推断完整业务通过，也不能从无法解码的响应断言该次响应的产品语义正确。
3. `scm-client-boundary.json` 记录 `is_admin: false` 和 `hub_state_read_denied: true`，支持该实际普通进程不能直接读取 Hub DB。此拒绝是要求的隔离边界，不是应放宽的权限错误；不扩大解释为所有文件的完整权限审计。
4. `service-events.json` 两条均为同一 PID 1636，Running、LocalService、SID `S-1-5-19`、session 0。它们支持当时实际服务身份，不能当作两次重启持久性通过。
5. child cleanup 记录四个已拥有 Local 进程及其已检查 PID 树均 alive=false、当前端口关闭；其中 exit_code=1 不应改写为业务成功。parent service-cleanup 记录任务服务 `smm-hub-c6da31167baf`、空 failures。结合 child 的已记录 disable 和代码固定 stop/PID/端口/delete 路径，支持已到达清理路径未报告错误；空 failures 本身不证明全部系统无残留，也不补足未执行的 E2 业务。

前轮判定保留为失败，根因分类为**工具编码失败；完整产品/E2 结果不确定**。不得抹去本轮或此前失败，也不得将它们累计为成功证据。

本次实际阅读原件的 SHA-256：

| 原件（相对上述根） | SHA-256 |
|---|---|
| `platform/standard-user.stderr` | `b0e71886648ea7751540b471a9bba4fb11347698fa72957d19f0982c998a2a87` |
| `platform/ordinary-client/platform/failure.json` | `c33cbfd379e28fb350b1c5f42398b2c1d375133329ffd9eca82ba4cb08e1a317` |
| `platform/ordinary-client/platform/scm-client-boundary.json` | `6e36b568d570d7aaac9058be4342c3686223590bf670b1554cb464c85814ed66` |
| `platform/service-events.json` | `eaba5cccbff8ac7f5100a7f766cb28c734981b3a6ceeea0c92ab54e8ab6965a4` |
| `platform/service-cleanup.json` | `a1a49be26dd878f6256999c70f5c7b4346c003bbe85722bde70119de620ef56a` |
| `platform/ordinary-client/platform/cleanup.json` | `b2e82edf31544a4f9d29ecdf96bf75d31941d1c9e274ea305dd43048f602dd09` |

这是对本地指定原件的核对，不声称重新下载或核验整个远端 artifact。

## 修正的契约与未变边界

- `atomic_json` 第 29–32 行原本以 `ensure_ascii=False`、显式 UTF-8 写临时文件并原子替换。修正第 171、361 行，使普通客户端读响应、管理员读请求都按同一既有 UTF-8 契约解码，消除对进程默认 locale 的依赖。中文路径、空格及其他 Unicode 值逐值保留，没有转义删除或字符替换。
- 两处读取均继续严格解码和 `json.loads`；没有 `errors=ignore/replace`、cp1252 回退或捕获后当成功。客户端仍先要求 `value["ok"]`，管理员异常仍返回 `ok=False`，错误不会被本修正吞掉。
- `Administrator.rpc` 固定 operation/Hub CLI 子命令允许列表、禁止传入 `--state-dir`、add 路径限定 child fixture、期望退出码仅 0/2、任务固定状态与服务选择均未变。本次没有新增可执行代码或任意路径 IPC 通道；这只是有限差异核查，不是对全部既有 IPC 的安全认证。
- 产品 `src/`、任务及 Hub state ACL、LocalService SID/session 检查、标准账户 Hub DB 拒读、管理员/普通账户观察流分离、实际身份与源打开断言、完整业务的退出/result 判据、证据导出与清理均未因本补丁变化。没有降低 SPEC E2 对服务读采集原文、服务网页写入、Local 同步/检索/读取及实际停启持久性的要求。

## 独立便携复核及其限度

已读 `/private/tmp/smm-007-scm-ipc-utf8-selfcheck.json`，其绑定 helper SHA 与本候选一致。Reviewer 另从当前 AST 提取实际 `atomic_json` 和两处实际 reader 调用，在独立临时目录写入并回读含 `资料 空格 中文” 😀`、`资料/对话.txt` 的合成 JSON，两端 reader 都逐值相等；原子写临时文件完成后不存在。相同字节以旧 cp1252 解码实际触发 `UnicodeDecodeError`（见证位置 55、字节 `0x9d`）。见证字节 SHA `392dc9f8d4a94e91bfd603e5f70653d8dc97685e510b54dd3a94b60e737f3f6b`，与给定自检一致。当前 helper 内存编译通过；没有生成 pycache。

这些检查直接覆盖本次写读编码匹配及旧错误模式，不证明 Windows 权限、进程调度、实际请求/响应内容或后续完整业务；没有据 Mac 便携检查判 E2 通过，也未替代实际 Windows 重跑。

## 后续执行与停止点

可按此次明确授权继续：提交与本报告绑定的限定修订后，用当前同版独立包执行原 Windows SCM 场景，保存原始首错、实际身份、业务与清理原件，再独立复审实际结果。不能预填 passed；成功也只覆盖实际完成并有证据的 SCM 部分，E2 的物理跨操作系统机器间 HTTPS 等其余条件仍须各自满足。

若本次实际执行再次失败，保留本次及所有旧失败与缺件，按 PLAN 199 行和用户限定停止该项自动修订；本报告不授权扩展到产品、ACL、IPC 允许集或新增轮次。最终实际结果及方案变化仍须按 AGENTS 记录于 PLAN 与后续 PR。
