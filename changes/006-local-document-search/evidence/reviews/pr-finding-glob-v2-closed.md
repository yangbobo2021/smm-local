# 目录尾部 glob P2 返修复核：已关闭产品缺口

Reviewer：`/root/review_006_pr_final`；复核产品头 `9cfd6193262b692f779abe1b240cd82f67b1eb50`，`documents.py` SHA-256 `390880bf58192317846ed1db29f271b9c5f6c7530b3811736634fa7aa4f74d66`。观察时间 `2026-11-22T19:43:25.786837+00:00`。本意见只关闭 `pr-finding-glob-v1.md` 中的 B2/A2 具体缺口，不提前判断最终 R006、finish 或未产生的最终文档提交 CI。

当前 `_glob` 把末尾 `**` 的前置分隔符整体纳入可选后缀，合并连续 `**`，裸 `**` 使用路径段字符类，保留 `*`/`?` 的单段规则。未修改 SPEC，也未改弱原判据。旧 4c 反例与 red-r006-glob-v1、delivery-r006-v2 failed 保持原件。

亲自核当前 tdd-green/green-r006-v5-scan-scope 的47 bindings/83 artifacts、execute/execute-r006-v5-scan-scope 的48 bindings/75 artifacts，全量 SHA 重算一致；分别真实 exit0 / 1passed。另从正式逐次原 API 请求/响应重建独立预期，不以 emitted wanted 当预期：

| 模式 | 完整预期文件（相对独立 docs 根） | 原 search 响应 |
|---|---|---|
| cache/**/ | visible.txt、cachex/keep.txt、outer/cachex/keep.txt、outer/cache/direct.txt、outer/deep/cache/deep.txt | 00031-api-004，完整5项一致 |
| **/cache/**/ | visible.txt、cachex/keep.txt、outer/cachex/keep.txt | 00040-api-012，完整3项一致 |
| outer/**/cache/**/ | 上述三正控与cache/direct.txt、cache/sub/deep.txt | 00047-api-018，完整5项一致 |
| **/**/cache/**/**/ | 三正控 | 00056-api-026，完整3项一致 |
| CACHE/**/ | 全部七项，大小写负控 | 00063-api-032，完整7项一致 |

23份原 `read` 响应逐路径核为独立字面串 `globneedle ` + 相对路径。selector末尾 LF 编译器断言已实际通过；没有声称三系统创建 LF 文件名。附加只读比较中，另用路径段递归/`fnmatchcase` 的独立解释器比较 95,940 个有限模式/路径组合，0差异；此项仅为本审查工具输出观察，不冒称原生 formal TC。

亲自回查三个全新 `work/platform-{mac,linux,windows}-formal-v4`（Linux/Windows位于probe）：

- 各当前 wheel SHA为 `412a68157d685f93bda6dbe8a4fbd77945dea53e7faa8578fdcc46235a2ba6fb`，26份 installed/expected 模块及HTML逐一重算均等于当前源码。不是借候选3/4c旧包通过。
- `source_config.exclude=['excluded/**/']`；实际 `excluded/direct.txt` 为51字节，独立字面串 `needle globexcludeduniquemarker must not be indexed` 的SHA为 `dcdadb7ea7c9219e835dc9066334f7c0b80a0206a31b33b8019207d149949ea4`。各10份source时间线中该文件原SHA/bytes/mtime完整相同。
- 各85条commands中真实初始项目CLI检索完整集恰为指南.md、nested/notes.txt、control.txt；marker查询实际零命中且coverage indexed_files=4。各`glob-exclusion.json`来源ready3/candidates3/billed_bytes6130/ignored_excluded1/ignored_links1，排除的51字节未计候选或预算。不是用pending或失败下的零命中掩盖未处理。
- 各23次body-open原审计没有excluded正文路径，全部仅明确refresh。已看当前Mac web-original PNG，其中来源配置确为excluded/**/、成功3/忽略2、项目范围原文及UTF-8/采集提示可见。
- 9份新原trace直接解析：各主137动作/34请求、partial13/8、重启50/13，0工具错误；实际主导航/按钮、旧ref read400及移除后同ref read200可追溯。当前真实服务PID首次退出与port_closed早于第二启动（Mac58418→58793、Linux164023→164420、Windows1176→10884），不借旧轮清理。
- 各当前overlap-survivor三入口读相同旧双源reference后source_ids仅连续S1，collector仍历史已移除S2，edited中文emoji原文准确；本项未回退4c修复。平台仅证明这一P引用生存路径，完整all/remove/failed/continuous时间线仍据当前共用overlap-version正式证据。

据此，原P2的零目录段排除失效已由当前产品及当前独立正式/三平台原件关闭。其余 A1–A8 的最终需求级判定、父导航、PR正文、finish及最终提交CI由后续交付闭环核读；此意见不批准尚未存在的结果。
