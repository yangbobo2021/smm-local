# 007 当前验收证据（PR #39，仍为 Draft）

采用已合并 SPEC #37、PLAN #38。当前产品为 `b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da`：PR Review v3 的 F8 已修复，未配置 Hub 时显式 Hub 项目根保留 `unavailable` 和具体原因，不借同号本机项目；普通本机查询排序保持。六格真实红灯、同测试绿灯/14项相关回归、独立包 v5 均有独立意见：[红灯v2](../../../reviews/f8-red-review-v2.md)、[绿灯](../../../reviews/f8-green-review-v1.md)。预览包的 0.4.0 字符串不表示功能已发布。

原生 `AT-SMM-007`、定义000007/SPEC源不变，SC6补无配置状态后共36项（28自动、8人工），原35项与所有失败/旧通过均保留。[逐项索引](acceptance-index.json)分开列当前正式状态、当前准备复审和历史收据；`current_bindings=false` 不能当新产品通过。当前正式28项通过，7项未执行当前版本、1项证据不足；覆盖率 `off/unknown` 不表示行覆盖率。

| 范围 | 当前实际结论与依据 |
|---|---|
| 26 自动正式项 | 全部当前源实际退出0并独立passed，30个检查、33个外层pytest参数；[正式复审](../../../reviews/current-formal-review-v2.md)。28项调试虽全exit0，[独立准备复审](../../../reviews/current-design-review-v3.md)只放行26项，不能写28项正式通过。 |
| 两项自动准备缺口 | `library-update` 未独立保证两份Hub文档ID全集，`listing-coverage` 的正常/断线列表可能共同漏项目；尚未按当前候选正式验收。最小断言补丁已准备，历史修订达上限，额外一轮等待维护者决定；产品未因这些假设被判失败。 |
| 当前用户发现 | 新独立包v5实际README/指南/CLI/Skill路径、真实stdio四份原文、两端项目库选择/拖放/更新删除、逐项目逐ID准确原文、同步开关与只读。两真实旧页携旧KEY/HID/G（含换Hub恰同G）被拒且完整新状态不变；浏览器四阶段URL/持久存储/cookie无token、认证只同源头、刷新空壳/重选恢复。纯文本script/img在项目名/片段/原文无DOM执行或触发请求；[独立人工复审](../../../reviews/current-user-discovery-review-v4.md)passed，仅认用户发现，不认E1/E2。 |
| 完整回归与所记CI | 本机完整341项：340 passed、1 skipped（Windows专属启动时限），原进程argv/起止/退出0/JUnit/双流齐全。[b7ed常规CI](https://github.com/yangbobo2021/smm-local/actions/runs/45217257120)三OS pytest、双包构建、分开安装全success；各341项，Mac/Ubuntu335pass+6skip，Win336pass+5skip。五浏览器格因普通test extra无Playwright跳过，Unix另跳Windows专属项；实际Chrome由独立正式/用户路径另证。[门禁复审](../../../reviews/current-regression-ci-review-v2.md)passed只认所记head，最终PR head另核。PR实际checkout为与b7ed树相同的merge commit，报告已区分。 |
| 独立包v5 | 18条命令、Local30/Hub31个模块的源码→wheel→安装SHA一致；Hub不安装Local发行包。构建/安装通过不代替实际平台。 |
| E1三平台 | 修复F8前的普通账户主要流程/原图/trace保留为历史；当前v5尚无完整E1通过。共同缺口是stdio对私有/Hub自有只有search没有read，以及PLAN明写停启后Web/stdio读取。Mac原完整passed已由[补审](../../../reviews/macos-protocol-recheck-v4.md)纠正，[Ubuntu/Windows复审](../../../reviews/e1-ci-manual-review-v1.md)同为不足；额外E1轮等待决定。托管E1 run的Windows/Ubuntu job成功、Mac job取消，不能称整run全绿。 |
| 实际服务E2 | [旧实际运行](https://github.com/yangbobo2021/smm-local/actions/runs/45201802511)有Ubuntu UID1001 user-systemd、Windows SCM LocalService/S-1-5-19/session0、Std拒读HubDB、网页两份原文/更新删除、外部native资料停启读取与PID/端口清理原件。仍缺网页资料停启后项目检索/旧ref读取，Windows另缺服务/防火墙删除后不存在查询；[服务复审](../../../reviews/services-manual-review-v1.md)不足。维护者明确“保留缺口，先完成其他验收”，不应用补证草稿、不再补跑；旧局部证据不冒称新完整候选通过。 |
| 不同OS不同机器E2 | 未执行。维护者禁止ESXi且确认暂无替代机器，同宿主逻辑档案/服务不替代真实跨机器HTTPS；独立资源判定与原件保留。 |

[公开清单](public-manifest.json)现57份选件，逐份标明产品版本、原/公开SHA及原样或派生，混合版本不会冒充当前全部通过。包含F8六格实际反馈、当前/历史JUnit、关键PNG、服务身份与artifact/trace回收摘要。完整trace、token/私钥、数据库、保护材料和wheel不公开。公开图实际打开核对，只含合成任务资料。

`manual-regression-ci-f8-v2` 的 `product_version` 尾句“product245c236 bytes unchanged”是复制遗留文字；真实进程/当前绑定/CI head均b7ed，两个产品字段与新增六格测试已改变。原收据不覆盖，索引及独立门禁报告明确更正。完整回归源码表绑定全部 `.py/.html`，不声称绑定所有类型文件；legacy JSON另由当前Git/CI相同树及兼容测试原件核对。

在仓库根运行 `python3 scripts/acceptance/hub_documents_verify_evidence.py` 核公开长度/SHA、36项身份与登记收据关联；作者本机可加 `--original-root /private/tmp` 核原SHA。`integrity=passed`只证明字节/索引一致，不表示交付通过。

[PR Review v3](../../../reviews/pr39-review-v3.md)对旧head425f140判需要修改，F1–F7关闭、F8及平台缺口分开；F8已按其意见修复；[当前 PR Review v4](../../../reviews/pr39-review-v4.md)已独立核完整diff、角色入口与逐条规格，结论仍不可合并，未确认新的产品失败。另有C1小缺口：README的“当前验证状态”所达验收工具007段仍写旧35项且未直链现有证据；可经指南→PLAN找到当前证据，正常使用不被阻断。该文档修订与其受影响的用户发现证据尚待一起更新，本轮不将其宣称已修复。[当前逐需求独立判定](../../../reviews/delivery-r007-v2.md)为 blocked：当前28项正式通过仅为部分范围，两个自动断言和六个平台项仍有缺口。必要验收未满足，维护者保留缺口不等于豁免SPEC，不合并、不发布或升级本机。未操作日常Hub/VibeInsight或被排除ESXi。
