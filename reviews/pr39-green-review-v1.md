# PR #39 补充同测试绿灯独立复审 v1

SC13 `TC-007-cli-scan-boundary` 与 SC14 `TC-007-web-review-feedback` 均为 **passed**，仅表示本轮同测试绿灯及适用回归通过。Reviewer canonical session：`/root/review_007_pr39_green_v1`。验收 ID：`AT-SMM-007`。

本轮实际读取交付验收技能及 Reviewer 规则、项目 AGENTS、007 SPEC/PLAN、PR39 原审查与补红灯 v3、定义和自然语言设计、当前测试/公共夹具、相关产品修复及原始证据。只写指定两份原生意见和本报告，没有修改产品、冻结测试、旧记录或代发 GitHub，也未运行改变状态的业务。

## 版本与完整性

定义 000006 SHA-256 为 `52f35fcc7e84b59d8158ec9c5f1e08460e6989598614b5c7d88d3a8b39b8890b`，已直接读取并重算。SC13/14 分别承接 SPEC B5、B6/B7/B8，不增加权限体系、不强制批次继续 C，不把浏览器 TestClient 映射扩大为 E1 网络或服务身份。

HEAD 为 `de41d7e77fc207f4850fc35a2968dedd6f10ad5a`；当前修复尚未提交，结论绑定当前产品字节，不能只据 HEAD 宣称新旧产品相同。每份绿灯 55 项 bindings、45 项 product_bindings、5 项 test_bindings 全部逐项重算匹配。SC13 的 32 项 artifacts、SC14 的 88 项 artifacts 均匹配。红灯 artifacts 也逐项核对；两端红/绿冻结副本的五份测试逐字节一致，主测试 SHA 为 `0df2d96991182b6ccf5c46232c9b8211afed70fe39d9584267d3c3e13eb92bf1`。

| 场景 | 绿灯目标 | result.json SHA-256 |
|---|---|---|
| SC13 | green-007-cli-scan-boundary-pr39-v6-a | bfba9505c6b4a5a0fd13f84da9d0900dd863991c66ead73948850eb60f0245d2 |
| SC14 | green-007-web-review-feedback-pr39-v6-a | a2a6b7999a9e0cf98d2d47f3afc864003a4986c6157ba16cb64ba26619493417 |

红灯为 `red-007-cli-scan-boundary-pr39-v6` / `red-007-web-review-feedback-pr39-v6`，目标摘要分别 `dab18f9c0552a8b45e40df2a5167b2b45ad9d2313b5f4a56759e303a7b6d73c9` / `b37a4bd00436761be83720a8e9cb21f6dd0a8396bcfa9bd8a8fdccec6436a1e7`；已读取独立 `/root/review_007_pr39_red_v3` 登记的 expected_failure。旧失败与需修订历史保留。

红/绿业务命令完全相同：`/private/tmp/smm-007/.venv/bin/python -m pytest -q tests/test_document_pr39_contracts.py::<selector>`，selector 分别为 `test_cli_scan_boundary`、`test_web_review_feedback`。实际原始 stdout 分别为 1 passed、2 passed，exit 0、stderr 空；FastAPI 弃用 warning 不构成业务失败。每份绿灯另运行四文件回归 `test_document_compatibility.py`、`test_document_lifecycle.py`、`test_document_search.py`、`test_document_sync_recovery_scope.py`，均为 19 passed、exit 0、stderr 空。

## SC13：采集调用边界

已逐份读取 20 份 JSON 附件。`00003/00004-scan-cli.json` 是同 state-dir 的真实 CLI add 子进程，两份独立外部文件均 exit 0、pending，来源 ID 不同。认证 HTTP 两次 add 均 405，两个单源与省略 ID 的全体 refresh 均 404。冻结测试第 29–45 行在每次拒绝后比较完整文档/项目表快照；两源 builtins/io/os.open 守卫累计打开尝试，最后要求零；拒绝阶段查询零结果。本次执行已通过全部这些断言。

当前 `src/smm_hub/document_api.py` 移除远程 add/refresh 路由，使请求在采集前拒绝。`00013/00014` 的真实 CLI 显式 refresh 各 exit 0、ready，`00016` 检索两份互异原文，`00018/00020` 逐引用 read 返回各自全文；第 49 行按独立原文全集核对，不能仅首源正常或误禁 CLI 而通过。状态不变与零打开由绑定测试实际断言和拒绝分支支持，没有假称另有独立磁盘指纹日志。

## SC14：批次、管理入口与读取出处

已实际读取 70 份 JSON 附件、两份 trace 的动作和 51 个浏览器网络请求及响应资源。trace 内 Local/Hub HTML 分别与绑定产品 HTML 字节相同，没有动作错误。实际浏览器运行页面与 JS；HTTP 经 Playwright route 映射到真实 App TestClient，属于本轮网页回归，不能替代 E1 网络/TLS/实际服务身份。

本轮实际打开四张原始 PNG，画面文字可读：

- `hub-web-review.png`：已认证 Hub，批次为 2 成功、1 失败或未处理；逐行明确 A.txt 成功、B.txt 严格 UTF-8 失败、C.txt 成功；库只有 A/C，名称和各自不同文档 ID 对应。
- `local-original-provider.png`：Local 文档页显示相同逐份报告与 A/C 库行；下方可见 Hub 创建端管理链接和维护者凭据来源说明。native.txt 命中为 Hub自有，显示 HID、档案和项目 #3；origin.txt 为本机与Hub，显示 synthetic-007、稳定设备/档案及项目 #2。阅读区是“实际读取端：本机”和独立 shared 原文。
- `local-web-review.png`：同一搜索结果仍在，阅读区变为“实际读取端：Hub”，显示 synthetic-007、相同原设备/档案及 shared 原文。
- `hub-management-empty-shell.png`：只有连接说明、凭据文件选择器和“尚未认证；未读取项目或文档”，没有项目库工作区数据。

首轮浏览器上传 `00012–14`、`00054–56` 分别依次返回 200/400/200。本实现继续 C；允许 C 成功或明确未处理的既定判据保留。第 96–105 行逐份可见 li 与库行、inner_text 名称/真实状态/文档 ID 绑定均已实际执行。第 106–114 行先核 search 完整 ID 集合及数量，再由 library_by_id 确定每份独立原文/SHA，逐 hit 核名称/SHA，逐 read 核 ID/正文/SHA。该部分为直接 TestClient 调用的绑定断言通过，没有另逐份浏览器网络日志；不把它描述成浏览器搜索操作。

两端同一 chooser 再触发 change 后，trace 中三份请求的完整 JSON 载荷及 submission_id 与首轮各自完全相同；`00020–22` / `00064–66` 返回原成功 ID，第 117 行库 ID 全集不增。`00068-web-feedback-complete.json` 在重试的异步 reload 期间读取到暂空报告，随后最终原始 PNG 的逐份报告已完整；它不单独承担最终报告证明，也不推翻首轮完成的可见断言和重试幂等检查。

Local 第 119–125 行与 trace 确认真正点击无 query/username 的精确配置链接，popup 到 `http://localhost:18770/`，请求无 Authorization，凭据控件可见、workspace 隐藏。截图清楚支持创建端管理及凭据取得说明，未要求锁死整段中文。

出处与回退有三个独立读取响应：`00040` native 为 Hub 及 native 独立原文；`00041` shared 为 Local；`00042` 移除原 Local 来源后 `00043` shared 为 Hub，稳定原设备/档案、版本、SHA 与正文相同。trace 中后两次 read 的请求/reference 完全相同且没有重搜。fixture auto_sync=False，移除仅使 Local 当次资格失效，尚未撤回 Hub 副本，因而实际证明沿旧合并引用的同版精确回退。每次等待本次响应，并核实际读取端、稳定身份及可见独立正文，不能用上次元信息或另一份正文蒙混通过。

## 原生意见与限制

两份指定原生意见均仅包含目标实际 TC，target_operation 为 tdd-green，status 为 passed，省略 covers，session 与本轮真实身份一致。每份写完均已立即通知主 Agent 登记：

- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-cli-scan-boundary-pr39-v6-a.json`
- `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-green-007-web-review-feedback-pr39-v6-a.json`

本轮不认定未读取/未绑定的 scripts/acceptance CI、service 或 Probe 修改已经实测；当前 Mac 独立包 v3 也是另项补充证据，本报告没有代替其独立复审。正式全项、最终 CI、其他必需平台/E2及逐需求判定仍待完成，不能据这两个 TC 宣布整体交付通过或合并就绪。
