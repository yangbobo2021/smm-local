# 当前完整回归与 CI 正式独立复审 v2

结论：**TC-007-regression-ci passed**，仅覆盖 `packages-2-gate`，验收 ID `AT-SMM-007`。本轮为独立正式 manual 复审，没有修改产品、测试、原件或其他记录，没有运行服务、ESXi 或日常来源，也没有 GitHub 写操作。

采用项目 `AGENTS.md`、007 SPEC A8/A9 与平台边界、PLAN 实施步骤7–9及回归段、`acceptance/ci-gate.md`、SC8 `design-sc8-final-v3` 和交付验收技能 `references/execution/reviewer.md`。完整回归/三系统 CI 与独立包模块摘要、用户发现/浏览器画面、E1/E2 是分开的检查分配。

## 版本与收据

- 当前与实际本机运行候选：`b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da`。
- handoff：`.acceptance-local/native-v1/AT-SMM-007/work/gate-f8-v2-handoff.json`。
- 目标：`manual-regression-ci-f8-v2`；result SHA `49eeb84ce599f080258ca01de1c2185f87d989d978e982f9d6974edce487caf3`，与 handoff 精确匹配。
- 定义 SHA `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`；设计收据 SHA `e5edf2b6015282f3f1925d51c47aece8014947d384acf4009b0c234978c2c944`。
- 104 项目标 bindings 和 13 项 artifacts 全部按实际字节重算匹配；完整回归 100 项 src/tests `.py`/`.html` 绑定均与当前文件、候选 Git blob 一致。四项构建/工作流文件也匹配。没有用旧 `222e` 结果代替当前结果。
- 10 份完整回归/CI 原件与工作副本逐项 SHA 相等；目标 attachments 亦验证匹配。

版本说明有两处精度问题，但不改变上述实际绑定：收据 product_version 尾句 `product245c236 bytes unchanged` 是过时说明，`git diff 245c236 b7ed5d7 -- src tests` 实际含 Local `document_search.py` 修复及新增 F8 测试，本意见不采用该尾句。100 项 source-bindings 只覆盖全部 `.py`/`.html`，未包含 `tests/fixtures/document_legacy_cli.json`，不应称作全类型 src/tests 文件 SHA；该元数据 JSON 当前与候选 head 一致（SHA `fceb9a0cc9864cb5196e55dd6a7e85896bae5ef9e4517d486e8b9f59edddc4a3`），实际兼容测试读取该元数据并已通过。

## 本机完整回归

原件 `/private/tmp/smm-007-complete-regression-v2/`，独立进程真实 argv：

```text
/private/tmp/smm-007/.venv/bin/python -m pytest -q --junitxml=/private/tmp/smm-007-complete-regression-v2/pytest.xml
```

cwd `/private/tmp/smm-007`；UTC 起止 `2026-11-23T16:30:50.174273+00:00` → `2026-11-23T16:35:06.609302+00:00`；真实 exit `0`。stdout 明确 `340 passed, 1 skipped, 1 warning in 256.13s`，stderr 空。重解析 XML testcase 共341，340通过、1跳过、0失败/错误，套件头与实际节点计数一致。唯一本机跳过为 `tests.test_service_startup::test_windows_waits_for_a_slow_background_service`，源码 `os.name != "nt"` 的明确 Windows 限定。警告为 FastAPI/Starlette testclient 的 httpx 弃用提示。

| 原件 | SHA-256 |
|---|---|
| result.json | `3835656707dd2f35147c332e8471084dde1d5693264f9c69dbf0735f34f85ce2` |
| source-bindings.json | `72d19234b8ebd284ebab879ef217b53164a3799f0665647a0335770e5896641d` |
| pytest.stdout | `34c417c9e4db54dac4a0fe4314380e167590ce74a0c1958a89152d482e123713` |
| pytest.stderr | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| pytest.xml | `75c93f86f008c23a5920c230d865499f80f6a4047115dfccb3b062e958b540b5` |

## 三系统实际 CI

原件 `/private/tmp/smm-007-ci-unit-b7ed-v3/`。保存的 run/API 与本次只读 `gh api` 现场返回相符：[Test packages run 45217257120](https://github.com/yangbobo2021/smm-local/actions/runs/45217257120)，事件 pull_request，API head 为候选完整 SHA，completed/success。逐项核 job 与 step，未以 run 总绿替代。

| 实际 job | pytest step6 | 双包构建 step7 | 分环境安装 step8 | JUnit 重计 |
|---|---|---|---|---|
| [macos-15 / 137841646152](https://github.com/yangbobo2021/smm-local/actions/runs/45217257120/job/137841646152) | success | success | success | 341 = 335 pass + 6 skip |
| [ubuntu-24.04 / 137841646724](https://github.com/yangbobo2021/smm-local/actions/runs/45217257120/job/137841646724) | success | success | success | 341 = 335 pass + 6 skip |
| [windows-2022 / 137841646679](https://github.com/yangbobo2021/smm-local/actions/runs/45217257120/job/137841646679) | success | success | success | 341 = 336 pass + 5 skip |

每个 XML 都是0 failure、0 error，原日志 stdout 总结分别335/6、335/6、336/5，与 XML 一致。原日志还逐系统显示 `smm_local` 和 `smm_hub` 两 wheel 成功构建，Hub/Local 分别安装到 `hub-env`/`local-env`，各自 CLI/MCP help 已执行；工作流中的 `Install wheels separately` 实际是此两独立环境步骤。

GitHub PR 默认 checkout 实际为合并提交 `e709327e39685b4fde684dfcfa11f64ae4bad39f`，父提交为 `83b50fcbbad1f29484aa54104ca0f9e75d0498e3` 与本候选。只读 GitHub commits API 确认该身份，[compare b7ed5d7...e709327](https://github.com/yangbobo2021/smm-local/compare/b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da...e709327e39685b4fde684dfcfa11f64ae4bad39f) 返回 `files=[]`，没有文件差异。因此可把此 CI 归属于所记候选，且保留 API head 与实际 checkout 的区别。

| CI 原件 | SHA-256 |
|---|---|
| run.json | `2c5f3768cff31300bc53f908da5e76a79c1d912345b6716174a370985bcf916d` |
| artifact-api.json | `b7ad828deb0c53df8034958aa79598dc4d3c0a0a6eced7893cc26356cc714675` |
| tests-macos-15/test-results.xml | `2cda85935e90cf9239dea985ba29db7cd884bbfaf31234a848526fdc8ac93aca` |
| tests-ubuntu-24.04/test-results.xml | `9c701ca8f44307ce02cdebd835935c7598b98ea1d9d6b8c9b828dc034b3b2ca1` |
| tests-windows-2022/test-results.xml | `70486573411cb9af6b0df530fc0482b4b633c924330a916ec200ff42bc43af0d` |

artifact API 三个产物分别14839109368（macOS）、14839852202（Ubuntu）、14840197579（Windows），workflow_run.id/head_sha均正确。无损副本清单 SHA `c49814cf1e78818b8e9d8c77f407d4ab1f56e81c351fdff0807a87763dd336b6`，逐源/副本验证相等。

## 测试身份与跳过边界

旧公开335项 XML 仅用于核对测试身份保留，不作为当前产品通过依据。按完整 `(classname,name)` 集合比较，四份当前 XML 均包含全部旧335项，无删除/重命名；仅增加 `tests.test_unconfigured_hub_documents::test_unconfigured_hub_root[0-cli/0-api/0-mcp/1-cli/1-api/1-mcp]` 六格，四份 XML 全部六格通过、无跳过。

CI 五个跳过为 `test_web_review_feedback[local]`、`[hub]`、`test_hub_retained_state`、`test_folder_guidance[local]`、`[hub]`，原因为 `could not import 'playwright.sync_api': No module named 'playwright'`；对应测试使用 importorskip，工作流仅 `uv sync --extra test`，pyproject 把 Playwright 放在 acceptance extra。Unix 第六个跳过为上述 Windows 专属项。没有把失败改为跳过的证据。本机完整回归中五浏览器格已执行通过；本TC不承担实际 Chrome 画面、平台完整流程或产品 UI 义务的独立验收。

## 范围与登记

`packages-2-gate` 的本次实际证据完整，故为 passed。后续报告/证据提交后的最终 PR head 必须再取得实际三系统 CI，不能把本意见推广成其他 head。SPEC A9 的 E1/E2、独立包完整摘要以及其他两项待修订自动断言仍须各自处理，本意见不构成豁免或整体交付通过。

已先写唯一 JSON 并通知主 Agent 登记：

`/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-regression-ci-f8-v2.json`

JSON SHA `c6ab553cf42e9e06d7f24a6859c7dab93021a51f953fe6787d91b8c1b7dffdcb`；cases 仅 TC-007-regression-ci、covers 仅 packages-2-gate。
