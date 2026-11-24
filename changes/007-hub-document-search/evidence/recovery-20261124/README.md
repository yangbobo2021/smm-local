# 007 验收材料恢复记录（2026-11-24）

本轮续接时，原 /private/tmp/smm-007 工作树和同根未提交验收资料已不存在；仅确认丢失，未确认原因。Git/远端仍保存候选 5083227897ab9612390a4cbc4997df961dff96d7。恢复工作树位于 /Users/boboyang/work/smm-007-recovery，原用户工作区未改动。

上一轮续接摘要记录过 33 passed / 2 not_executed / 1 insufficient_evidence，但更新后的原生收据、四份独立复审意见、97 件公开选件以及本机原件未提交，当前不能重读。摘要不能替代原始证据，暂不把这个统计作为当前可复核的正式验收结果，也不据此重建原生通过收据。已提交的旧索引保留历史。已提交的521份JSON实际包含7份定义、1份manifest和513份尝试索引；513份索引所指私有result均未恢复，不能称为521份完整可用收据。原生看板显示0项有效执行，表示索引/原件不能读回，不代表此前没有执行，也不代表341项回归出现失败。

可恢复的资料为 GitHub E1 run 45297175901（探针 head 8210b25）、常规 CI run 45298310517（head 5083227）和本轮重新执行的本机回归。原 E1 私有 trace 的解密密钥随临时材料缺失，CMS 原件仅能保存，不能声称当前已重新打开 trace。

原有 E2 两服务补证按维护者“保留缺口，先完成其他验收”不再执行；真实跨 OS 不同机器缺少获准环境。未使用家庭 ESXi、日常 Hub/VibeInsight 或用户文档。以上限制不是 SPEC 豁免，PR 继续保持 Draft。

## 已重新核实的结果

- 维护者批准的一行四源守卫已在5083227提交；本轮不改产品/测试。产品src与b7ed5d7相同。
- [本机实际回归](local-regression.json)：341项，340通过、1 Windows限定跳过、0失败/错误、exit0；[JUnit](local-junit.xml)、[stdout](local-stdout.log)、[stderr](local-stderr.log)和[执行后101份src/tests摘要](source-test-sha256.json)保留。执行后Git确认src/tests无差异，不把事后摘要声称为执行前测量。
- [常规CI](https://github.com/yangbobo2021/smm-local/actions/runs/45298310517)：head5083227，实际checkout4f43857，API父提交/完整树及各job日志均核相等。[步骤与统计](ci-508-summary.json)，Mac/Linux各335通过6跳过，Windows336通过5跳过；每格341。5个浏览器参数因普通test extra未安装Playwright而跳过，不能把该门禁当完整E1/E2。
- [E1实际run](https://github.com/yangbobo2021/smm-local/actions/runs/45297175901)三job成功，探针head8210b25；[job/步骤](e1-run-summary.json)显示服务步骤未执行。三原始ZIP均exit0，GitHub长度/外SHA/CRC及内层Mac115/Ubuntu115/Windows116件均通过。下表链接新增重启读取的可复核部分，既有CMS轨迹未解密，不把这些原件当新正式E1通过收据。

新公开选件的长度/SHA见[独立恢复清单](manifest.json)。原有63件manifest与旧索引原样保留历史，不声称已恢复上一轮未提交的97件清单。完整性核对与正式验收通过分别判断。

## E1 恢复选件

| 系统 | 原执行器结果 | 重启stdio/Web摘要 | 原件完整性 | 原网页画面 |
|---|---|---|---|---|
| macOS | [结果](e1-macos-15-result.json) | [6旧ref、Local6/Hub3原文](e1-macos-15-restart-summary.json) | [115件](e1-macos-15-integrity.json) | [Local](e1-macos-15-restart-web-a.png)、[Hub](e1-macos-15-restart-web-hub.png) |
| Ubuntu | [结果](e1-ubuntu-24.04-result.json) | [6旧ref、Local6/Hub3原文](e1-ubuntu-24.04-restart-summary.json) | [115件](e1-ubuntu-24.04-integrity.json) | [Local](e1-ubuntu-24.04-restart-web-a.png)、[Hub](e1-ubuntu-24.04-restart-web-hub.png) |
| Windows | [结果](e1-windows-2022-result.json) | [6旧ref、Local6/Hub3原文](e1-windows-2022-restart-summary.json) | [116件](e1-windows-2022-integrity.json) | [Local](e1-windows-2022-restart-web-a.png)、[Hub](e1-windows-2022-restart-web-hub.png) |

摘要按固定独立合成正文集合校验全文、稳定origin、版本、文本SHA、Unicode码点与LF行号，省略原始引用与路径；六张PNG原字节保留。三OS独立安装的Local30/Hub31模块亦由独立Reviewer逐模块映射核为当前产品，未将E1探针head8210b25混写成测试修订head5083227。

## 当前独立判定与续接条件

[完整R007独立报告](../../../../reviews/delivery-r007-recovery-v1.md)结论为blocked，已由原生工具[实际登记](delivery-r007-registration.json)，[独立JSON原件](delivery-r007-reviewer.json)原样保留。登记前[实际视图](native-before-judge.json)与登记后[当前摘要](native-current-summary.json)分开；[17张当前截图检查点](native-checkpoints.json)含两张公开[需求](native-00-R007-current.png)/[平台场景](native-16-SC9-current.png)原图，其他15张在持久私有目录保留，不回填历史画面。

待补齐的条件：恢复或重新取得适用当前候选的逐项正式执行/独立意见及可读轨迹；按维护者新的明确授权补两服务证据；有获准环境后执行真实跨OS不同机器HTTPS验收。没有改变SPEC或要求现在重新提供机器。

完整PR Review将在定稿后与本报告一并提交，最终head CI据实际另更新PR；不以旧CI代替新提交门禁。

[干净上下文 PR Review v6](../../../../reviews/pr39-recovery-review-v6.md)已完成：未确认新增产品或用户入口缺陷，32选件逐件核验一致；正式证据链/可读轨迹与既有E2缺口仍阻止交付，保持Draft。最终提交CI将在PR按实际运行另记录，不循环修改冻结证据。
