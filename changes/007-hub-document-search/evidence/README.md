# 007 当前验收证据（PR #39，仍为 Draft）

采用已合并 SPEC #37、PLAN #38，原生 `AT-SMM-007`/定义000007/SPEC源不变，共36项（28自动、8人工）。产品字节仍为 `b7ed5d73cc6532dd451c1f6f52d6cd0e88a408da`；本轮只修改获准的测试、探针及验收说明，不表示已发布0.4.0。

维护者2026-11-24允许E1三平台补证一轮、两自动项各一轮。[原话与范围](../../../reviews/authorized-evidence-round-20261124.md)保留；E2服务仍按“保留缺口，先完成其他验收”，本轮没有执行服务，家庭ESXi仍禁止。

| 本轮范围 | 实际结果与限定 |
|---|---|
| library-update | 新增初始/更新后两份文档ID全集及唯一性，允许和暂停两前状态逐份读独立正文；调试exit0、正式exit0，[准备复审](../reviews/approved-two-tests-design-v1.md)及[正式独立复审](../reviews/approved-library-execution-v1.md)passed，只认`library-update-2`。原CAS/中断/重放等检查保留。 |
| listing-coverage | 本轮新增独立预期SQL把接口字段当表列，`projects`无`stable_key`，准备数据即失败，列表业务断言未到达；[独立意见](../reviews/approved-two-tests-design-v1.md)为needs_revision/implementation，非产品缺陷。另需来源列表首次区分只返回首来源；具体SQL/双来源全集纠正草稿已备，尚待额外一轮答复，未应用。 |
| E1三平台 | [实际CI run45260738680](https://github.com/yangbobo2021/smm-local/actions/runs/45260738680)，探针head`3eb918c`，仅`document-installed-e1`前景Hub。三格均在新增`stdio_checks:1753`的归档内ID相等断言失败。完整十份search/read原件、安装模块与清理已回收；combined候选读回本机时归档内ID可不同，稳定origin/版本及独立原文相符。[三平台独立复审](../../../reviews/approved-e1-failure-review-v1.md)均needs_revision/implementation，不认产品失败，也不认后续Web/生命周期/重启已执行。origin纠正草稿待额外一轮答复，未应用。 |
| 入口与用户路径 | C1验收说明旧35项已改36项，并从README所达007段直链当前证据。静态内容已核；本机用户路径复验在同一共享stdio断言停止，导航/Web/CAS阶段未到达，不能授完整通过。单独浏览器隐私四阶段真实exit0，[独立意见](../../../reviews/approved-e1-failure-review-v1.md)确认四张原图/trace只支持局部。 |
| E2实际服务 | 旧[实际运行](https://github.com/yangbobo2021/smm-local/actions/runs/45201802511)及[独立意见](../../../reviews/services-manual-review-v1.md)保留：网页资料停启后按项目/旧ref读取、Windows删除后服务与防火墙不存在查询仍缺。用户决定停止补证不豁免SPEC；没有应用服务草稿。 |
| E2真实跨机器 | 无获准替代机器，未执行。逻辑档案、同宿主服务及普通CI不替代真实跨OS不同机器HTTPS。 |

[逐项索引](acceptance-index.json)按最新适用字节列正式状态，并保留历史收据和准备复审。当前为 **1 passed、4 needs_revision、30 not_executed、1 insufficient_evidence**。1 passed是本轮library-update；4需修订是三E1和用户路径。其余旧正式记录因测试/文档绑定已变，仅保留历史，本轮没有重新正式执行，不以改匹配记录冒充执行。此计数变化不是30项观测到产品回归；产品没有改动，新增测试候选仍有已知故障，后续须在候选修正后取得适用当前证据。

前一候选`e498ba5`的28项正式通过（26自动+2人工）、本机340pass+1skip及最终[三系统CI run45228318311](https://github.com/yangbobo2021/smm-local/actions/runs/45228318311)均留在Git历史与旧原件中。该CI各341项，Mac/Ubuntu335pass+6skip，Win336pass+5skip，五浏览器格因普通test extra无Playwright跳过；当前新增SQL故障不能用旧绿灯代替。当前候选最终CI状态在PR另列；未将旧完整回归或已知测试故障称为本轮门禁通过。

产品F1–F8关闭依据见[完整PR Review v4](../../../reviews/pr39-review-v4.md)及[F8红灯](../../../reviews/f8-red-review-v2.md)/[绿灯](../../../reviews/f8-green-review-v1.md)。旧`manual-regression-ci-f8-v2`尾句product245c236 bytes unchanged为过时元数据；实际产品b7ed已更正，原收据不覆盖。独立包v5 Local30/Hub31模块/18命令与当前产品SHA一致，当前CI E1各自重新构建安装；包通过不替代实际业务。

[公开清单](public-manifest.json)保留旧57选件，并新增本轮6份合成失败/通过原输出，共63份。逐份保留产品版本、原/公开SHA及派生说明；完整MCP响应、保护材料、凭据、数据库及原trace仅私有，CI artifact保留平台原件。旧正确片段、隐私局部和完整性passed不等于E1或整需求passed。

在仓库根运行 `python3 scripts/acceptance/hub_documents_verify_evidence.py` 核公开长度/SHA、36项与登记收据；作者可加`--original-root /private/tmp`核原SHA。覆盖率off/unknown不表示行覆盖率。保持Draft，不合并、不发布、不升级日常SMM，未访问日常Hub/VibeInsight或被排除ESXi。

本轮完整R007的[独立交付判定](../../../reviews/delivery-r007-approved-v1.md)已登记blocked。历史passed不覆盖新测试/说明版本，测试断言故障不当作产品必测失败。两个修订问题仍等维护者答复，未应用待决草稿。

[本轮完整PR Review v5](../../../reviews/pr39-approved-review-v5.md)已在新上下文核全PR、同字节产品与实际入口、新断言/平台原件及逐条规格：保持Draft，不合并；C1静态修正、测试实现故障、业务缺证分别认定，未确认新增产品违约。
