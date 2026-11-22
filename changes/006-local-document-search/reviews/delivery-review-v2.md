# R006 需求级独立复审 v2

结论：**failed**。当前产品 `4c706b304e904b126ea3103523069b265d101b31`、定义 `000002`，本意见未修改产品或验收状态。

已完整逐 A1–A8/E1 写入本轮原始意见：`.acceptance-local/native-v1/AT-SMM-006/review-inbox/delivery-r006-v2.json`。本报告为审查索引，登记必须使用原意见字节。

## 当前必修失败

- 原文：`changes/006-local-document-search/spec.md:29` 的 `**` 零或多目录段、尾 `/` 排除对应目录及后代；A2要求自定义规则逐项正确。
- 当前反例：`.acceptance-local/native-v1/AT-SMM-006/work/pr-review-v2/glob-trailing-recursive.json`，SHA256 `aba525c7925296dd5ac8621b1946b3de194149cbb5c9e71225c692539000ea88`。
- 真实输入：`exclude=["cache/**/"]`；预期仅 `visible.txt`，实际还采集并命中 `cache/direct.txt` 正文 `needle direct`，来源错误报告为 ready。
- 独立复核：本 Reviewer 打开输入/refresh/search原件并核提交，另只读求值当前 `_glob`，实际正则 `^cache/.*$` 对 `cache` 不匹配、对 `cache/sub` 匹配。`documents.py` 仍 SHA256 `43d3762cd9d413bc5954df362bf99132beed242bb30348cd6911de470e5930a0`。
- 原因与缺口：`documents.py:80–90` 把末尾 `**` 前斜杠固定，扫描目录名无尾斜杠，零目录段分支失败。`test_document_scanning.py` 只分别覆盖 `**/private.txt` 与 `cache/`，未检查组合；原29项passed不足以覆盖已真实观察的差异。

## 已实际核查的当前证据

私有根为 `.acceptance-local/native-v1/AT-SMM-006/`。

| 条款 | 直接读取的主要材料 | 判定界限 |
|---|---|---|
| A1 | `execute/execute-r006-v4-{source-config,entrance-contract}`，`tests/test_document_sources.py`，API/CLI/MCP和E1真按钮 | 输入、pending、完整配置、只读发现支持；未发现新增失败 |
| A2 | `execute/execute-r006-v4-{scan-scope,decode-files,budgets,read-races}`；扫描/预算测试、三平台native-file-errors及partial PNG | 已有边界有实测，但上面的合法glob组合实际失败 |
| A3 | `execute/execute-r006-v4-{project-scope,project-maintenance,overlap-version}`；项目维护源码 | remove/failed/continuous三分支当前来源元信息已正确；历史失败另保留 |
| A4 | `execute/execute-r006-v4-{version-lifecycle,qualification,source-lifecycle}`；生命周期测试和read校验 | 终态资格中断后不借新源、不复活旧ref；多源仅保留连续资格 |
| A5 | `execute/execute-r006-v4-{search-rank,exact-read,invalid-read,empty-query}`；`tests/test_document_search.py` | Unicode/长文/排序/范围/签名负例；当前İ展开映射与三平台正控支持 |
| A6 | `execute/execute-r006-v4-{refresh-order,refresh-remove,overlap-order,query-snapshot,interrupted-refresh}` | 确定屏障/完整状态及持久refreshing注入有证；不冒称真实崩溃 |
| A7 | `execute/execute-r006-v4-{isolation,compatibility,packages}`；`work/full-regression-v5`；`work/ci-4c`；README/指南/Skill/维护入口 | 301pass1skip、双包及4c两CI三OS全成功；未重跑005管理员服务矩阵 |
| A8/E1 | `work/platform-mac-formal-v3`及另两平台`probe`原件；三份正式独立意见 | 三OS普通身份、Local26模块/HTML、CLI84、stdio20、原图、trace、同档案重启与清理均有当前证据 |

实际查看原图为每OS的 `web-original.png` 与 `web-partial.png`：原文版本/码点/行号、项目及来源字段、惰性HTML纯文本和错误原因可辨。实际解析9个原trace的动作/网络记录；原viewer不兼容新版trace，改为直接读zip中的事件和请求/响应资源，未宣称viewer成功。三平台 `overlap-survivor.json` 的CLI argv、原trace最后read请求均与原 `original_hit.reference` 精确相同，返回仅剩余S1、历史采集S2及独立raw2正文一致。

三个E1统一Local wheel SHA256 `c8422b57c4e5de4fb5a1089bac1165df83a0c96ad805bf50e3a60eb35a393d4e`，安装全部模块逐值等于当前源码。首次真实服务PID退出/端口关闭严格早于新服务启动，末尾清理再次核真实PID/端口。Win普通token/session核各实际进程，不用控制端身份代替。

当前全部24自动正式artifacts/bindings逐SHA核对无差异；各实际进程exit0，所有导出API预期/实际状态一致。公开 `verify.py --raw-root /private/tmp/smm-006-impl` 实际输出 `Verified 2148 published files and private original SHA`。

## 历史与未完成项

`delivery-r006-v1` 的a66来源元信息failed完整保留；真实metadata红灯2failed1passed及当前4c三分支3passed表明那项已修。此次glob失败独立成立，应保留本次failed意见并按新同版证据重审。`user-discovery-v4` 观察第6步的a66标签是原记录笔误，实际entry/product_version/两CIhead为4c，已公开更正而不改原件。

本轮没有运行新的三平台业务、改产品/测试/AT或登记意见。最终文档提交CI和PR合并由主流程完成。发布、升级日常安装、007/008、实际用户资料或staging均不在此判定范围。
