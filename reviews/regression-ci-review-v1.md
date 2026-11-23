# AT-SMM-007 完整回归与三系统 CI 独立正式复审 v1

结论：`TC-007-regression-ci` **passed**，仅认领 `packages-2-gate`。适用候选为 `222e0e55c788bd7693b9b25ce08964e967ef14c7`，产品字节与 `245c236ddc41057cd78694902283574d1175e309` 一致。此结论不是 A9、E1/E2 或整体交付通过；后续证据提交改变最终 PR head 后，必须另核最终 head 的三系统 CI。

本轮独立只读复核 AGENTS、007 SPEC A8/A9 与平台条款、PLAN、`acceptance/ci-gate.md`、SC8 `design-sc8-final-v3`、交接及目标 manual 收据。未重跑产品、pytest、Windows、服务或 ESXi，未进行 GitHub 写操作。该 TC 不执行 Web 操作，浏览器业务和画面由各自正式项负责。

目标为 `.acceptance-local/native-v1/AT-SMM-007/manual/manual-regression-ci-final-v1/result.json`，SHA-256 `a2c21c197b9c44f5d9db121cf632ed3b772e215fde6c5dcc1b22f6131d71077f`；设计收据 SHA-256 `e5edf2b6015282f3f1925d51c47aece8014947d384acf4009b0c234978c2c944`。唯一分配检查 `packages-2-gate` 来自 SPEC A8 的完整 pytest 与三系统 CI，符合已审设计，无额外产品行为要求。

## 原始回归

独立读取 `/private/tmp/smm-007-complete-regression-v1/` 中 result、完整双流、JUnit 及 source-bindings 原件。真实命令为：

```text
/private/tmp/smm-007/.venv/bin/python -m pytest -q --junitxml=/private/tmp/smm-007-complete-regression-v1/pytest.xml
```

cwd 为 `/private/tmp/smm-007`；记录 head 为上述 `222e0e5`。UTC 起止为 `2026-11-23T15:34:41.933157+00:00` 至 `2026-11-23T15:38:50.658533+00:00`，退出 0。stdout 为 `334 passed, 1 skipped, 1 warning in 248.13s`，stderr 长度 0；JUnit 重算 335 个 testcase，334 通过、1 跳过、0 failure、0 error，与 suite 汇总相符。唯一跳过为 `test_windows_waits_for_a_slow_background_service`，与 `tests/test_service_startup.py:16` 的非 Windows skipif 一致。

source-bindings 的 45 个 src 文件和 54 个测试文件逐 SHA 与当前 worktree、Git `222e0e5`、`245c236` 比较一致；其未列入的静态 `tests/fixtures/document_legacy_cli.json` 另核三者字节相同。构建脚本、两个打包 pyproject 及 CI 工作流另有绑定并一致。原件证明实际完整回归，不能从包探针退出码推导这一结果。

## 原始三系统 CI

独立读取 `/private/tmp/smm-007-ci-unit222-v2/run.json`、`artifact-api.json` 和三份原始 JUnit。运行 [Test packages 45205399891](https://github.com/yangbobo2021/smm-local/actions/runs/45205399891) 已 completed/success，head 与本机完整回归相同。逐个 job 核对实际步骤 6（pytest）、7（build_packages）及 8（Install wheels separately）均 completed/success，未仅采用 run 总结论。

| 系统 | 实际 job | JUnit 总数 | 通过 | 跳过 | 失败/错误 | 三项步骤 |
|---|---|---:|---:|---:|---:|---|
| Ubuntu 24.04 | [137799611645](https://github.com/yangbobo2021/smm-local/actions/runs/45205399891/job/137799611645) | 335 | 329 | 6 | 0/0 | 全 success |
| Windows 2022 | [137799612418](https://github.com/yangbobo2021/smm-local/actions/runs/45205399891/job/137799612418) | 335 | 330 | 5 | 0/0 | 全 success |
| macOS 15 | [137799612705](https://github.com/yangbobo2021/smm-local/actions/runs/45205399891/job/137799612705) | 335 | 329 | 6 | 0/0 | 全 success |

三份 JUnit 的 testcase 身份全集均与本机 335 项一致。artifact API 的三件原响应均明确绑定 run 45205399891、head `222e0e5`，各平台 XML 已实际打开解析并与原生附件逐 SHA 一致。冻结 `.github/workflows/tests.yml` 中 build_packages 构建双包，下一步骤分别新建 hub-env/local-env，安装对应 wheel，并校验 Hub CLI、Local CLI/MCP 帮助入口。

三个平台共同跳过五个浏览器参数格：`test_web_review_feedback[local/hub]`、`test_hub_retained_state`、`test_folder_guidance[local/hub]`。原始原因均为缺少 `playwright.sync_api`；源码在相应 importorskip 位置，pyproject 的普通 test extra 确实不包含 Playwright，acceptance extra 才包含。macOS/Ubuntu 另跳过 Windows 专属启动时限项。没有证据显示普通产品失败被改为 skip；也不能把五格计作三平台浏览器已实跑或宣称三系统各 334 全过。对应真实浏览器、身份、服务及跨机器业务须看独立 TC，不由本门禁代替。

## 字节绑定与结论边界

目标收据中 103 项 bindings、13 项顶层 artifacts，结果中的 12 份附件及 12 份操作证据均实际存在、逐 SHA 匹配；原始/复制 manifest 的 10 组文件逐原件/副本 SHA 及长度一致。完整回归收据内部的四项证据 SHA 与原件相符。核对时 Git HEAD 仍为 `222e0e5`；本意见不提前认可之后任何 head。

另只读检查公开 manifest 当前 21 件的长度/SHA 均匹配，并读取 `hub_documents_verify_evidence.py`：它核字节及索引对应，明确 `integrity_does_not_mean_delivery_passed`，不执行完整业务验收。公开 README 仍引用旧常规 CI 和“正在补收据”，新 gate 原件尚未列入公开 manifest；主 Agent 应在最终公开同步时更新。本 TC 的正式原生原件已齐，此说明不增设产品验收条件，也不把公开完整性当业务通过。

独立原样意见已先写入 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-regression-ci-final-v1.json` 并通知主 Agent 登记；JSON cases 仅含本 TC，covers 仅 `packages-2-gate`。完整回归和所记 head 的三系统测试/双包构建/分环境安装有实际证据，故通过该检查。E1/E2 现有缺口、指定服务身份、真实跨 OS 不同机器 HTTPS、以及合并前最终 head CI 均未被豁免。
