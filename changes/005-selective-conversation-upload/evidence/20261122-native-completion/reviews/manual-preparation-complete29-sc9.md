# SC9 complete29 人工准备独立复审

AT-SMM-005/R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；Reviewer /root/review_complete26_prep_c；2026-11-22T10:33:35.072624+00:00。

结论：needs_revision，最早implementation。完整自然设计已经增加E1三平台三入口零命中，修复28设计范围缺口；实际三平台新探针均非零、完整业务未到达，不能进入声称full2已完整可核验通过的人工观察。没有产品缺陷结论。

## 当前审阅摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete29-sc9/request.json` SHA256 `3eb73d128254abec7abe45e61709a85f1c18a1f9790ca91c0703ad6366eaef59`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete29-sc9/result.json` SHA256 `ba813d8cf807f42df03c6e0534ac68bd1dfed39a2a7b128c3679acff6ae7da69`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete29-sc9/request.json` SHA256 `70bb56d0d250236965f56e2217c94e0f86061ecfacf0f432da9cfd0082ca8e56`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete29-sc9/result.json` SHA256 `b90f74f0d438d78c23efa027e1473fa449728b5af050e4bfd256561dbbc5cad5`。
- `.acceptance-local/native-v1/AT-SMM-005/debug/debug-complete29-sc9/result.json` SHA256 `7e4b2e98c2a752de80598da8ee99eb44df29021c1b5383d15449bc22fc4d1ad3`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9.md` SHA256 `6c52163e418d0e5cb4246f6d25996c40a25cf6a2d535dc400f48b89b9bd65552`。
- Windows只读诊断原件 `.acceptance-local/native-v1/AT-SMM-005/work/empty29-windows-inspection.json` SHA256 `7078cb860fe7e986d489cd3c336e265497ec69e841d18910fa85ab0bfa5f4757`。

实际读29交接/manifest、当前完整设计/匹配、empty/recorded/Windows控制器、新三平台debug日志及Mac31/Linux30附件、Windowsworker原始诊断。完整SPEC A9首段/E1/D4仍适用，没有把输出键或固定元数据扩成新要求。

## 逐人工check与新增分工

TC-005-sc9-evidence仍full1/full2/full3/full4；原fallback=tdd-core、empty-coverage=additional-empty-coverage；新empty-mac/linux/windows分别分配empty-e1-mac/linux/windows。三平台六响应（all/project × CLI/真实stdio/Web）与空结果覆盖画面现在有明确自然设计。

- full1：原E1三平台offline三入口只A/A-new、排D/G、coverage/503原因、逐条原文、PNG与trace可定位；旧原件按真实时间及d80/f45→ba8完整依赖适用性，不改标当前新业务。当前fallback29仍真实pass，只认其共用分配。
- full2共用：empty-coverage29两个scope重新真实pass，完整空列表三状态/原因及真实Hub调用断言和两个原始JSON到达；28已修get问题未回归。不能拿这2个源TestClient参数代替新增3E1真实身份/入口/UI。
- full2 Mac/Linux：**需修implementation**。两平台实际安装/正命中project三来源及CLI all空查询原响应确已到达；之后sync_playwright活动循环中再asyncio.run(MCP)于empty.py:30抛RuntimeError。MCP产品调用尚未执行、Web空提交/画面尚未开始，project全组也未到达，successful-empty.json与两关键PNG未生成。故不把已生成trace或原stdout当六响应业务通过。最小修复控制器事件循环组织，CLI/MCP可先在同步Playwright上下文外完成，浏览器仍实际操作；不改产品或删除必需断言。
- full2 Windows：**需修implementation/运行准备**。本次native仅回收目录不存在、没有probe附件；只读inspection的worker receipt PID9020 exit1、tasks=[]，worker.log明确配置读取PermissionError13，在empty.py:59读临时target.json发生、尚未installed/setup，所以不是产品返回失败也不是已通过包/身份业务。Limited普通进程对包装器临时配置不可读，需修录制包装配置交接，然后全新真实debug与回收。该214MB PowerShell深序列化诊断有非UTF8字节，本人保留原始SHA，替换解码仅提取content.value的明确ASCII异常/receipt，未改原件；无需把巨大PSProvider对象当业务附件。
- full3：可执行准备。29实际全套JUnit的partial_hub_failure/local_error/incomplete_candidate/invalid_scope各声明按26详细分工继续支撑Hub失败保快照、本机失败Hub可读、双失败报错、缺全文排除/不补召回及范围解析失败独立完整集合；不缩成只看5个当前auto。
- full4：可执行准备。limit0/51不发Hub与ValueError、Web空query400等当前全套个案及原3OS断线/恢复/逐条原文仍可定位；不声称所有非法字段组合或新空画面已实际检查。

## 版本、实测与停止点

当前debug29完整bindings/artifacts SHA实算一致；Mac31/Linux30附件保留真实失败与cleanup无失败，Windows0附件由只读worker诊断补明失败原因，不伪造probe目录。Mac15.3.1 UID501、Linux6.8/glibc2.35 UID1000及ba8实际模块/原正控可核；Windows尚未包验证，设计VM76/Limited准备依据不冒充业务实测。

29完整共用回归已完成252项251pass1skip、exit0；inputs SHAef4b3b069e8301cadaf6eaacf2a18a320bd37fc7a1308c92f00f61e0b3b62c5c、stdout3a9cd119df766b3f7c16f5ca49abde836d6f136876c81b5193bb665c9cb53776均实算，JUnit无failure/error。七离线audit均0只核原件。这份回归没有包含外部三E1探针，不能消除其真实非零。

只首入口正确/只all正确反例目前仍可能落在未到达部分，故新三TC covers空；原两个共用TC独立passed全分配。正式准备需在控制器/配置可读性修复后真实跑到三平台各六响应/画面、再独立准备复审，不重跑与本缺口无关的停止/补传全流程，不造产品失败或通过。
