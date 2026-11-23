# PR #39 补充红灯独立复审 v3

结论：SC13 `TC-007-cli-scan-boundary` 和 SC14 `TC-007-web-review-feedback` 均为 **expected_failure**。本版测试封住前两轮指出的阻塞缺口；现有产品仍在实际首个必要断言失败。后续未执行到的断言只经静态核查，不据此认领正式通过或需求通过。

Reviewer 的真实 canonical session 为 `/root/review_007_pr39_red_v3`。本轮只写两份指定原生意见和本报告，未修改产品、冻结测试、旧证据，也未代发 GitHub。

## 范围与证据完整性

实际读取 `app-delivery-acceptance-native/SKILL.md`、`references/execution/reviewer.md`、用例设计边界说明，以及项目 `AGENTS.md`、007 `spec.md`、`plan.md`、`reviews/pr39-review-v1.md`、两轮红灯复审报告。按 B5/B6/B7/B8 原文核对场景、自然语言设计、实际输入和断言，不把 PR 建议扩展为新权限体系、强制继续 C 或 E1 网络要求。

验收 ID 为 `AT-SMM-007`，定义 000006 的 SHA-256 为 `52f35fcc7e84b59d8158ec9c5f1e08460e6989598614b5c7d88d3a8b39b8890b`。程序比较 000005 与 000006，原需求和原 12 场景均一致，仅新增 SC13/SC14。原 29 项保留，本轮只审交接的两个实际 TC，不将 31 项总数称为通过数量。

HEAD 为 `de41d7e77fc207f4850fc35a2968dedd6f10ad5a`。两份目标各 50 项当前 bindings 均逐个重算一致；SC13 的 15 项 artifacts、SC14 的 39 项 artifacts（各含五份冻结测试）也一致。`match-sc13-v6` / `match-sc14-v6` 各五项 bindings 一致。冻结主测试 SHA 为 `0df2d96991182b6ccf5c46232c9b8211afed70fe39d9584267d3c3e13eb92bf1`。逐份读取实际 stdout、stderr、请求附件及公共夹具，并打开两张原始 PNG、检查两份 trace；轨迹中的 HTML 与对应当前产品 HTML 逐字节相同。

| 目标 | result.json SHA-256 | 结论 |
|---|---|---|
| `red-007-cli-scan-boundary-pr39-v6` | `dab18f9c0552a8b45e40df2a5167b2b45ad9d2313b5f4a56759e303a7b6d73c9` | expected_failure |
| `red-007-web-review-feedback-pr39-v6` | `b37a4bd00436761be83720a8e9cb21f6dd0a8396bcfa9bd8a8fdccec6436a1e7` | expected_failure |

实际命令均为 `/private/tmp/smm-007/.venv/bin/python -m pytest -q tests/test_document_pr39_contracts.py::<selector>`，两个 selector 分别是 `test_cli_scan_boundary`、`test_web_review_feedback`。前者 exit 1、1 failed；后者 exit 1、local/hub 两参数均 failed；两份 stderr 为空。FastAPI 的弃用 warning 不影响本轮产品失败判定。

## SC13：采集调用边界红灯有效

SC13 和 `design-sc13-v1` 准确表达 B5 的账户与调用入口边界。两个实际 CLI 子进程在同一明确 state-dir 保存两个独立外部来源，`00003/00004-scan-cli.json` 均为 exit 0、pending，来源 ID 不同。

第一个认证 HTTP add 返回 200 并创建另一个 pending 来源；`00006-remote-add-denial.json` 与 stdout 一致。实际在 `tests/test_document_pr39_contracts.py:38` 要求拒绝处失败。`document_api.py:60–62` 直接转交 `native(add)`，`documents.py:194–223` 没有入口区分，故失败来自已确认产品边界缺失，不是环境故障或错误预期。

静态核对第 29–49 行及共享守卫：两个 add 分别拒绝并比完整文档/项目表快照；两个单源 refresh 和省略 ID 的全部 refresh 分别拒绝并比同一动作前快照；两份原文件的 builtins/io/os.open 守卫保存被吞异常的读取尝试，最后要求零尝试，拒绝阶段也无正文命中。退出 guard 后，同一 state-dir 的实际 CLI 分别 refresh，再逐引用 read，以两个互异独立原文的全集核对，能够区分仅处理首源或误禁 CLI。

本次只执行到第一个 add 的拒绝断言。第二个 add、状态快照、三种 refresh、最终零打开和正常 CLI refresh/read 均未到达，不称已经通过。相同条件的更多目录、路径或标识样例属于可选补测。

## SC14：前轮阻塞已修订，真实产品失败保留

实际打开本目标 `local-web-review.png` 和 `hub-web-review.png`：两端都只显示“文件不是严格UTF-8文本”，没有逐文件结果，页面库未显示已保存 A。`00012/00024-browser-request.json` 已保存 A，`00013/00025` 拒绝 B，`00014/00026-mixed-batch-before-report.json` 各只有 A。两份 trace 确认顺序且没有发送 C；产品循环外 catch 与此一致。

两参数均在冻结测试第 96 行因 `#doc-upload-results` / `#hub-upload-results` 不存在而失败。这是 B8 逐份真实报告缺失的有效红灯。真实 Chrome 页面加 TestClient 映射足以证明该产品回归，但不作为 E1 的实际网络、TLS 或服务身份证据。C 可以成功，也可以明确未处理。

本版将前轮三项 implementation 缺口封住：

1. 第 96–105 行对报告、A/B/C 各 li 及每个库行核实际可见，用 `inner_text` 将文件名与本份真实状态绑定，B 另核 UTF-8 原因。库行按 asset.id 唯一定位，再比可见名称/ID与全集规模。A/B 状态倒置在第 101 行失败；正确文本隐藏在行内或整行隐藏会被可见断言或 `inner_text` 拦截。
2. 第 106–114 行先精确核 search ID 全集和数量，再从 `library_by_id` 固定每份名称及独立原文/SHA，不再用 hit 自己的标签决定预期。逐 hit 核 name/SHA，逐 read 核 id/text/SHA。A/C 两 hit 即使均误用 C 引用，A 在第 114 行即失败，不能两次读 C 代替 A/C 各自原文。
3. 第 119–125 行同时核链接和管理说明可见，说明具有创建端管理及维护者凭据来源的含义；地址精确且无 query/username，真实点击 popup，正确 Hub 空壳页的凭据控件可见、workspace 隐藏，该 Hub 浏览器请求无 Authorization。不锁死整段中文逐字文案。

其余后续路径也已静态核查。第 115–117 行复用同 File 对象触发实际 change，等待本轮末份响应再核保存 ID 集合不增加，保留 C 成功和明确未处理两种合法分支。

第 127–149 行准备 native/shared 两份独立正文。native 命中行可见 `inner_text` 核 Hub 自有、HID、档案及项目；shared 行核稳定设备、档案、设备名及项目。三次 read 是 native Hub、shared Local、撤本机当次资格后沿旧 shared 命中的 Hub 回退；每次等待实际响应，核 `archive_scope` 和独立正文，随后核阅读区可见实际端、稳定设备/档案及正文。实际端依次 Hub/Local/Hub，端变化的等待避免前次元信息冒充本次。最后另核回退阅读区设备名。名称和项目已在各命中行绑定；原文依据要求读取端和身份明确，不将每次阅读区重复全部命中字段新增为本轮契约。

夹具的 `auto_sync=False`，remove 仅标脏，不立即向 Hub 撤回副本；页面仍使用原 `documentResults` 引用且没有重搜，保留精确同版回退准备。只有 Hub 单端引用会在首次 Local 读取失败，只有 Local 单端引用会在最后 Hub 读取失败，不能以一个端始终正确漏过这两种状态。

真实执行在第 96 行停止，第 97 行及以后均未运行。本意见确认其设计、断言和静态路径有效，不将链接、批次后续或三次读取称为已实测通过。原有适用目标和三种业务状态已被区分，继续增加同条件文件或 ID 变体属于可选补测。

## 原生意见

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-cli-scan-boundary-pr39-v6.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-web-review-feedback-pr39-v6.json`

每份仅包含对应目标实际 TC，`target_operation` 为 `tdd-red`，canonical session 与本轮独立身份一致，省略 covers。逐份写完后均已立即通知主 Agent 登记；本报告不代替原生登记，也不抹去两轮 needs_revision、既有产品失败或平台缺证。
