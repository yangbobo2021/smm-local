# PR #39 补充红灯独立复审 v2

结论：SC13 `TC-007-cli-scan-boundary` 为 **expected_failure**；SC14 `TC-007-web-review-feedback` 为 **needs_revision / implementation**。两端网页批次的真实产品失败仍成立，本版已修正前轮大部分断言，但独立原文身份绑定、实际可见性及管理说明仍有漏检。不能据首个真实失败将后续未完成断言一并放行。

Reviewer 宿主 canonical session 为 `/root/review_007_pr39_red_v2`。本轮只写两份指定原生意见及本报告；未修改产品、冻结测试、旧记录或代发 GitHub。

## 范围、版本与证据完整性

实际读取 `app-delivery-acceptance-native/SKILL.md`、Reviewer 与用例设计边界说明，项目 `AGENTS.md`、007 的 `spec.md`、`plan.md`、`reviews/pr39-review-v1.md` 及前轮红灯意见。从 B5/B6/B7/B8 原文反查当前场景、自然语言设计和实际断言。C 可成功或明确未处理，不要求必须继续批次；TestClient 映射的真实 Chrome 网页回归不作为 E1 网络、TLS 或服务身份实测。

`AT-SMM-007` 当前定义为 000006，SHA-256 为 `52f35fcc7e84b59d8158ec9c5f1e08460e6989598614b5c7d88d3a8b39b8890b`。与 000005 程序逐项比较，需求及原 12 场景均保持一致，仅新增 SC13/SC14；原 29 项保留，加两项为 31 项。本轮只审两份交接目标，不把这一数量当作已通过数量。

HEAD 为 `de41d7e77fc207f4850fc35a2968dedd6f10ad5a`。两目标各 50 项当前 bindings、SC13 的 15 项 artifacts、SC14 的 39 项 artifacts 均重算 SHA 一致；各自包含五份冻结测试。两份 `match-sc13-v3` / `match-sc14-v3` 的五项 bindings 也一致。冻结主测试 SHA 为 `eaf07dc2240fad87f4e6ea94751049a84676563a911f9749cca81a9be6c56a61`。读取全部日志、请求附件、公共夹具及两份浏览器轨迹，并实际打开两张 PNG；轨迹保留的 HTML 与当前对应产品 HTML 逐字节相同。

| 目标 | result.json SHA-256 | 结论 |
|---|---|---|
| `red-007-cli-scan-boundary-pr39-v3` | `f41d6f02c4cd0b18961d9e81849dcbe4970687349c05fe14ddf57b71fd22c957` | expected_failure |
| `red-007-web-review-feedback-pr39-v3` | `7477cfd9beb80ae440b3a5288fe0fa60720187c144f228e9c714284bc8b303ce` | needs_revision / implementation |

实际命令分别为 `/private/tmp/smm-007/.venv/bin/python -m pytest -q tests/test_document_pr39_contracts.py::test_cli_scan_boundary` 和相同前缀的 `::test_web_review_feedback`；均 exit 1。前者 1 failed，后者 local/hub 两个参数均 failed。stderr 均空，没有把警告或工具故障误判为产品失败。

## SC13：有效红灯

场景与 `design-sc13-v1` 准确表达 B5：外部来源只由执行 CLI 账户明确 refresh，Hub 不是远程任意路径指令入口。两个实际 CLI 子进程 add 成功，分别建立不同 pending 来源。`00006-remote-add-denial.json` 显示第一认证 HTTP add 返回 200 并创建另一个 pending 来源；stdout 在冻结测试第 37 行要求拒绝时失败。`document_api.py:60–62` 直接调用 `native(add)`，`documents.py:194–223` 没有入口区分，支持失败来自产品缺失。

静态核对第 28–48 行及共享守卫：两份各自 add、两个单源 refresh 和无 ID 的全体 refresh 均独立要求拒绝并比完整文档/项目表快照；两份源的 builtins/io/os.open 守卫保留被吞异常的尝试，最终要求零读取；拒绝阶段无正文命中。退出守卫后，同一 state-dir 的实际 CLI 分别 refresh，再逐份 read，以两个互异独立全文的全集核对，能拦截只处理首份或误禁 CLI 的实现。

实际只执行到第一个 add 的拒绝断言。第二个 add、快照、refresh、零打开最终断言和 CLI 正常采集/原文均未到达，本意见仅确认这些后续实现静态可执行，不称其已通过。相同条件的更多标识或目录样例属可选补测。

## SC14：真实失败及本版修订

`local-web-review.png` 和 `hub-web-review.png` 均显示“文件不是严格UTF-8文本”，没有逐文件结果，页面库没有 A。实际浏览器请求 `00012/00024` 已保存 A，`00013/00025` 拒绝 B，`00014/00026-mixed-batch-before-report.json` 各只有 A。轨迹确认顺序，未发 C。两端都在第 95 行因报告元素不存在失败，符合 B8 的真实缺失，不是浏览器启动故障。

本版修订落实了多个前轮意见：逐 li 绑定 A/B/C 状态及 B 的 UTF-8 错误；逐库对象比 ID/名称及全集规模；search 必须非空且 ID 集合完整；同 chooser change 重试等待末份响应后再比 ID；管理链接实际可见、点击 popup、地址正确且打开匿名空壳，不发送浏览器认证头；native 和 shared 分别核独立正文及身份，并沿旧 shared 引用在本机当次资格失效后核 Hub 提供端及正文。

已核后续 selectors、真实路由、引用持有和夹具时序。`Fixture(auto_sync=False)`，remove 仅标脏，不立即撤 Hub 资格，因此保留 Hub 当次同版副本供回退合理。第 96 行以后均未实际运行，不把静态检查写成通过。

仍有三处属于原义务、会改变判定且现有断言可全过的缺口，最早修订阶段均为 implementation：

1. **独立原文仍未按已保存身份绑定。** 第 106 行只核 search ID 全集，第 109 行按被测 hit 的 display_name 选择预期。若合法 C 成功分支的库包含 A/C，search 两个 hit 的 ID 仍正确，但二者 display_name/reference 都误用 C，代码便两次读 C 并通过，A 未准确读回。B8、检查 `web-review-feedback-1` 和设计都要求已保存每份材料按独立原件读取。应以 library 的 asset.id 固定对应名称及独立正文预期，再逐 hit 核对，避免使用被测标签决定预期。无需增加文件样例。
2. **报告和库的正确文本可能隐藏。** 第 95–104 行仅 count/contain_text；名为 visible 的 locator 没有可见性筛选或断言。将报告 li 或库行隐藏但保留正确文本/ID，相关检查仍可全过，用户仍无法看到真实结果。B8“逐份报告”及检查1“显示”要求可见业务结果，应核报告和每个保存对象的结果文本实际可见。管理说明同样不能以隐藏文本充当可发现信息。
3. **管理说明只剩“凭据”字样检查。** 第 114 行只核提示含“凭据”，没有核创建端管理、维护者提供凭据文件的含义，也未核提示可见。只保留隐藏的该字样，或错误说明凭据由 Local 自动提供，其他链接/popup 检查仍过。B6/B8、PR 发现 F3、检查 `web-review-feedback-2` 和设计明确要求说明创建端管理及凭据来源。应核可见提示具有上述含义；不要求锁死逐字文案。

场景及自然语言设计已有这些义务，不需修改场景、添加权限体系、强制继续 C 或引入真实 E1 环境。更多同条件文件数/ID 变体可选，不据此阻塞。本轮 SC14 保留真实产品首失败，同时返回 needs_revision，待修订测试在未改产品上另取红灯。

## 原生意见

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-cli-scan-boundary-pr39-v3.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-red-007-web-review-feedback-pr39-v3.json`

两份仅含目标实际 TC，`target_operation: tdd-red`，使用本轮真实 canonical session，省略 covers。每份落盘后已立即通知主 Agent 登记；本报告不代替登记收据。
