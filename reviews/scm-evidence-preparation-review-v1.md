# SCM 证据回收准备修订独立审查 v1

结论：本次限定的证据回收修订可接受，未发现阻断项。它修复已知的“首个白名单文件不可读即停止回收，后续可读业务诊断也丢失”问题；缺件仍使导出失败，没有把不完整证据变成验收成功。此结论仅为准备工具审查，不是 E2 Windows SCM/LocalService passed、正式 TC passed 或最终 PR Review。

## 范围与依据

- 审查根：`/private/tmp/smm-007`，HEAD `245c236ddc41057cd78694902283574d1175e309`。唯一已跟踪代码 diff 为 `scripts/acceptance/hub_documents_ci.py` 的 `export`，31 行新增、3 行删除；未修改产品源码、业务断言、账户、服务 ACL 或身份判断。
- 候选 helper SHA-256：`8accbcb765de7b6f0f404f1cb62b8d5a073a25b328ade3592ece6e64844f3377`；HEAD helper SHA-256：`316250bddd6470370550b27b069934d5d50d3d5e8f2aeb63ef8fccb64b72a800`。结论绑定该候选字节。
- 已阅读 `AGENTS.md`、`changes/007-hub-document-search/spec.md`、`plan.md`、`scripts/acceptance/README.md`，以及交付验收技能的 `SKILL.md`、`references/case-preparation/implementation.md` 和 `references/execution/reviewer.md`。适用依据是 SPEC A9/E2 的真实服务证据门槛、PLAN 对业务退出与回收失败分开保留及原始输出/SHA 的要求、技能的已知样本探针自检与实际执行/未到达区分要求。
- 只读核对实际失败日志、下载成员清单和部分原件，并在本机独立临时目录运行合成样本；未执行 Windows、ESXi、产品服务或真实业务验收，未改旧证据。仅写本审查文件，不登记原生 case passed。

## 原始失败能证明什么

`/private/tmp/smm-007-ci-installed-v4-failed.log` 第 18–49 行显示，run `45178028154` 的 Windows SCM 路径先由 `run("platform", ...)` 得到非零退出，形成 `AssertionError: ('platform', 1)`；在 `finally` 回收时，又于 `shutil.copyfile` 读取任务内 `packages/build.stderr` 触发 `PermissionError: [Errno 13]`。这是先发生业务探针失败、后发生证据回收失败的两层事实。

`/private/tmp/smm-007-ci-windows-diagnostics-v4/names.json` 的 SCM 前缀只有 `007-scm-public-evidence/failure.json`，没有该前缀的 `platform.stderr`、平台结果或 SHA 清单；该 `failure.json` 只保存父控制器看到的 `('platform', 1)`。另一 `007-public-evidence` 前缀的 E1 材料不能补作 SCM 材料。现有原件因此不能定位首个 SCM 业务失败的具体原因，更不能据此判定产品缺陷、清理成功或服务业务通过。

## 对实际 diff 的判断

1. `hub_documents_ci.py:132–145` 在复制白名单原件遇到 `OSError` 后，删除可能留下的不完整目标，记录相对路径、异常类别和 errno，然后继续后续文件。没有修改源权限，也没有用空文件代替不可读原件。
2. `:146–167` 对已复制的目标字节计算长度和 SHA；缺件报告也进入清单。目标字节取样避免再次读取原件产生第二次权限失败，实际输出文件是摘要核对对象。
3. `:168–169` 在清单写出后仍抛出 `Evidence export incomplete`。`main` 的 `run` 非零断言、平台 `status == "passed"` 断言、保存原始业务 traceback 的 `failure.json` 和重新抛出逻辑均未放松（`:188–201`、`:292–301`）。业务失败仍可从原始 `failure.json` 和可读 stdout/stderr 追溯，最终退出也保持失败。
4. 原白名单、目录排除、符号链接排除和 trace 的证书加密分支未变。新报告只记录相对路径、类别和 errno，没有复制异常消息或不可读文件内容；不会把异常消息中的秘密带入报告。合成 `hub-token` 继续排除。没有发现本次改动新增凭据导出通道，但此项不等于对未来实际日志内容做过脱敏审计。
5. `.github/workflows/selective-upload-acceptance.yml:112–119` 保留 `if: always()` 上传相应目录，支持非零回收后保留已经写出的诊断。这只是静态调用路径核对，不是新候选已在 Windows 运行的证据。

## 自检与独立复核

已检查 `/private/tmp/smm-007-export-selfcheck.py`（SHA-256 `69d81367a06e4c216a624c5fa3bfd44ba44e80c6f4f2e8b0ab7ff03c6eac65fe`）及其 before/after stdout、stderr。before 的实际红灯是读取缺失的 `c.stdout` 时 `FileNotFoundError`，不是产品失败；after 输出 `status: passed`，绑定上述候选 helper SHA，stderr 为空。

本 Reviewer 实际运行 `python3 /private/tmp/smm-007-export-selfcheck.py`，退出 0，得到同一候选 SHA 和四项自检成功。该脚本只在 `TemporaryDirectory` 写合成文件，以 mock 注入 `b.stderr` 的权限失败。

另以 `git show HEAD:scripts/acceptance/hub_documents_ci.py` 和当前候选分别在内存加载 `export`，在 Reviewer 自有的 `TemporaryDirectory(prefix="007-review-export-")` 复核。独立夹具包含带 NUL/CRLF 的可读原件、不可读文件、排在其后的可读原件、原始业务 `failure.json`、排除的合成 token；复制失败先写出部分目标再抛 `PermissionError`，异常消息内含合成秘密。实际结果：

| 核对项 | HEAD | 当前候选 |
|---|---|---|
| 不可读文件之后的 `c.stdout` / `failure.json` | 未回收 | 均与独立源字节一致 |
| 复制失败留下的部分目标 | 保留于提前退出目录 | 已删除 |
| 明确缺件 | 无缺件清单 | 准确列 `b.stderr` / `PermissionError` / errno 13 |
| 最终退出语义 | `PermissionError` | `RuntimeError: Evidence export incomplete; see evidence-unavailable.json` |
| SHA 与长度 | 未生成完整清单 | 三份可读原件和缺件报告的路径全集、长度、SHA 全部吻合 |
| 合成 token / 异常消息内的秘密 | token 未导出 | token 未导出，报告不含异常消息秘密 |

上表的“全部”指本次合成输出中除清单自身外的文件；没有将此结果扩大成所有导出分支均已实测。原 before stderr SHA 为 `e82e8ce819b3b1ab968e7e6606f3c0c89c7bc460277599518a3ce0b276772cda`，after stdout SHA 为 `17aee5a2f9ec9e80314aa080c5dc3b6c626ce98047d0aac719a6f8859d3e8884`，before stdout/after stderr 均为空文件。

## 仍未验证与后续边界

- 新 helper 尚无实际 Windows SCM 重跑与 artifact 回收证据。合成 `PermissionError` 验证复制失败分支，不证明 Windows ACL、LocalService 启动、业务行为或完整清理。
- 历史 SCM 业务非零的底层原因仍未知。本次修订提高后续可读诊断的回收机会，并未修复或否定该业务失败。若关键诊断本身不可读，新报告会明确缺件，仍须保留证据不足状态。
- 本次异常处理限定于普通白名单文件复制；目录遍历/类型检查、目标写入与摘要阶段、trace 加密分支的其他失败未被宣称均能继续回收。它们不影响此已知 `copyfile` 失败的修正判断，也不能据本次自检声称任意故障均已覆盖。
- 本次是首次实际到达 SCM 后暴露的证据准备问题，与既往 E1 普通账户准备额外授权分开记账；后续仍遵循该项默认最多两轮自动修订，不凭拆分场景扩张轮数。保持产品 `245c236` 及既有正式 TC 判据，待新一轮真实原件及独立执行复审后再判 E2。
