# 006 本机文档验收证据

当前产品与平台探针为 `9cfd619`，不是已发布的 0.4.0。SPEC [PR #31](https://github.com/yangbobo2021/smm-local/pull/31) 合并后才推进 PLAN [PR #32](https://github.com/yangbobo2021/smm-local/pull/32)，再进入实现 [PR #33](https://github.com/yangbobo2021/smm-local/pull/33)。

本目录提供实际业务与独立意见的脱敏副本。当前逐项状态以[29 项覆盖索引](coverage.json)和[原生结果](native/current-results.json)为准；本索引本身不代替通过判定。最终独立需求意见 [delivery-r006-v3](reviews/delivery-r006-v3.json) 已原样登记为 [passed](native/delivery-r006-v3.json)，并已实际执行 [finish](native/finish-public.json)；前两次 failed 保留。

## 从规格找到证据

| SPEC | 场景/主要检查 | 当前原件与复审 |
|---|---|---|
| A1 | SC1 | [source-config](formal/execute-r006-v5-source-config/result.json)、[entrance-contract](formal/execute-r006-v5-entrance-contract/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A2 | SC2 | [scan-scope](formal/execute-r006-v5-scan-scope/result.json)、[decode-files](formal/execute-r006-v5-decode-files/result.json)、[budgets](formal/execute-r006-v5-budgets/result.json)、[read-races](formal/execute-r006-v5-read-races/result.json)、[platform-files](native-manual/manual-r006-cross-files-v4/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A3 | SC3 | [project-scope](formal/execute-r006-v5-project-scope/result.json)、[project-maintenance](formal/execute-r006-v5-project-maintenance/result.json)、[overlap-version](formal/execute-r006-v5-overlap-version/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A4 | SC4 | [version-lifecycle](formal/execute-r006-v5-version-lifecycle/result.json)、[qualification](formal/execute-r006-v5-qualification/result.json)、[source-lifecycle](formal/execute-r006-v5-source-lifecycle/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A5 | SC5 | [search-rank](formal/execute-r006-v5-search-rank/result.json)、[exact-read](formal/execute-r006-v5-exact-read/result.json)、[invalid-read](formal/execute-r006-v5-invalid-read/result.json)、[empty-query](formal/execute-r006-v5-empty-query/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A6 | SC6 | [refresh-order](formal/execute-r006-v5-refresh-order/result.json)、[refresh-remove](formal/execute-r006-v5-refresh-remove/result.json)、[overlap-order](formal/execute-r006-v5-overlap-order/result.json)、[query-snapshot](formal/execute-r006-v5-query-snapshot/result.json)、[interrupted-refresh](formal/execute-r006-v5-interrupted-refresh/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A7 | SC7 | [isolation](formal/execute-r006-v5-isolation/result.json)、[compatibility](formal/execute-r006-v5-compatibility/result.json)、[packages](formal/execute-r006-v5-packages/result.json)、[user-discovery](native-manual/manual-r006-cross-user-v5/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |
| A8 | SC8 | [e1-macos](native-manual/manual-r006-formal-mac-v4/result.json)、[e1-linux](native-manual/manual-r006-formal-linux-v4/result.json)、[e1-windows](native-manual/manual-r006-formal-windows-v4/result.json)；逐TC独立意见在[覆盖索引](coverage.json)对应review |

## E1 三平台实际完整入口

三轮均用独立安装的 Local wheel、合成资料、隔离档案及普通账户；真实 CLI、浏览器 Web、stdio MCP，核对正文/码点/行号、项目范围、修改旧引用、删除/移除、失败恢复和同档案重启。没有连接 Hub/VibeInsight，没有读取用户文档，没有改日常安装。

| 系统 | 原始完整业务 JSON、画面和安装摘要 | 独立正式意见 |
|---|---|---|
| macOS 15.3.1 / UID501 | [业务时间/结果](platforms/mac/result.json)、[CLI](platforms/mac/commands.json)、[Web响应](platforms/mac/web-responses.json)、[安装26模块](platforms/mac/installation.json)、[普通身份](platforms/mac/product-identities.json)、[首停/重启/清理](platforms/mac/services.json)、[原文画面](platforms/mac/web-original.png)、[错误画面](platforms/mac/web-partial.png) | [passed依据](reviews/review-r006-platform-formal-v4-mac.json) |
| Ubuntu / UID1000 | [业务时间/结果](platforms/linux/probe/result.json)、[CLI](platforms/linux/probe/commands.json)、[Web响应](platforms/linux/probe/web-responses.json)、[安装26模块](platforms/linux/probe/installation.json)、[普通身份](platforms/linux/probe/product-identities.json)、[首停/重启/清理](platforms/linux/probe/services.json)、[原文画面](platforms/linux/probe/web-original.png)、[错误画面](platforms/linux/probe/web-partial.png) | [passed依据](reviews/review-r006-platform-formal-v4-linux.json) |
| Windows 11 / Limited session1 | [业务时间/结果](platforms/windows/probe/result.json)、[CLI](platforms/windows/probe/commands.json)、[Web响应](platforms/windows/probe/web-responses.json)、[安装26模块](platforms/windows/probe/installation.json)、[普通身份](platforms/windows/probe/product-identities.json)、[首停/重启/清理](platforms/windows/probe/services.json)、[原文画面](platforms/windows/probe/web-original.png)、[错误画面](platforms/windows/probe/web-partial.png) | [passed依据](reviews/review-r006-platform-formal-v4-windows.json) |

各平台另保留全部20轮stdio调用、协议服务器退出、源字节/mtime、body-open审计、资格/重启检查点和7张PNG。完整trace含路径，原件保留私有；三份逐平台正式意见均实际查看3份原trace，[9份原SHA](private-trace-sha256.json)可追溯。Windows本轮已实际核对启动器与服务真实PID，首次停服后真实PID消失及端口关闭早于新服务启动，末尾再次验证；不以启动器退出推定清理成功。Unix真实chmod失败与Windows junction/坏编码范围分开，不冒称Windows ACL实测。

## 共用回归、包与CI

- [完整源码回归](support/full-regression-v6/stdout.log)：301 passed、1 skipped（平台限定项），附[JUnit](support/full-regression-v6/pytest.xml)、实际起止/退出及输入绑定。
- [两个包分别构建/安装](formal/execute-r006-v5-packages/result.json)：Local 26、Hub 24模块源码→wheel→安装摘要逐值一致；Hub不依赖Local文档模块。平台统一使用候选4 Local wheel，SHA `412a6815` 开头，完整值见各平台installation.json。另一次独立构建的整个wheel SHA可不同，不能以同版本字符串认定同包。
- 当前产品源的[push三系统CI](https://github.com/yangbobo2021/smm-local/actions/runs/45059349205)与[PR三系统CI](https://github.com/yangbobo2021/smm-local/actions/runs/45059354697)均成功，涵盖pytest、双包构建及分别安装；[真实元数据和原日志](support/ci-9c/)分别保存。最终文档提交的最新CI另以PR检查与PR描述链接为准。

## 审查与返修历史

历史需修订意见完整保留在[独立意见目录](reviews/)，不把旧包通过当作新包通过。Windows最初CI发现TestClient内部socketpair与DOS保留文件名两项测试环境问题，修复断言封装后重取真实红灯/绿灯。独立PR审查又复现Unicode小写展开索引错误；首个IGNORECASE候选因额外等价字符抢片段也形成真实红灯，最终保留原词法并映射回原码点。两轮[真实红灯原件](red-unicode/)与当前[新绿灯和四项旧引用回归](tdd-green/)保留。旧Windows正式轮首次停服缺证为needs_revision，当前新轮已补实际PID/port检查。原生完整历史仍可从仓库[验收索引](../../../.acceptance/native-v1/AT-SMM-006/)追溯。

## 复核公开字节

运行 `python verify.py` 核对[公开清单](SHA256SUMS.json)；维护者持有私有原件时，可加 `--raw-root <该工作树>` 核对原SHA。原/导出双SHA及脱敏方式见[provenance.json](provenance.json)。脱敏副本不是原字节：替换个人路径/账户/测试机地址，省略可回解个人信息的原stdout Base64与编码传输命令，保留解码业务输出、合成正文/Unicode/字符坐标、状态、时间、PID和SHA。公开PNG原本只含中性任务路径，逐字保留。数据库、签名材料、wheel、配置及完整原trace不公开。

首次需求级判定 [delivery-r006-v1](native/delivery-r006-v1.json) 为 failed：旧 all 引用正确依靠连续 S1 读回时，来源数组仍混入退出 S2。新增[真实红灯](red-metadata/)后，当前版本只返回原引用中仍有效的来源，历史采集者仍保留；三平台同旧引用的三入口原件分别见 `overlap-survivor.json`。旧判定保留，最终状态沿原生当前结果核对。JUnit 主机名仅在公开副本替换为 TEST-HOST，原 SHA 与脱敏后 SHA 分列。

人工 user-discovery-v4 原观察第6步沿用了“a66”文字标签；其 entry、product_version 与真实 CI head 均为 4c706b3，当前独立意见已逐值更正，原记录保持不变。

第二次需求级判定 [delivery-r006-v2](native/delivery-r006-v2.json) 为 failed：合法 `cache/**/` 未排除零层直接文件；[独立完整反例](support/pr-review-v2/glob-trailing-recursive.json)与[真实红灯](red-glob/)保留。当前修正覆盖五组完整文件集合、连续 `**`、大小写负控及 LF 匹配语义；各平台另有 `glob-exclusion.json` 的实际直接文件、成功覆盖下零标记词、独立排除计数/预算、未打开正文与原 SHA/mtime 原件。LF 检查是编译器语义，不冒称 Windows 非法文件名实测。
