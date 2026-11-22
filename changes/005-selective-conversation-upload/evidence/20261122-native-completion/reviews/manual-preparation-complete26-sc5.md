# SC5 人工准备独立复审

验收 AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_b；审阅时间 2026-11-22T09:56:01.303207+00:00。本意见只放行准备，不认领尚未进行的人工观察或正式业务通过。

实际审阅 design `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc5/request.json` SHA256 `b80749bca6157e7eb0f134051669ed677afcd21d79f9f68aef5511d61a68c340`；match `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc5/result.json` SHA256 `a83ba251ff872b0a77f641e962552afb1b360acd342a7937cc63a62208167776`；steps `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC5.md` SHA256 `8052e185007f1f14a068c16758496011383e311c7074e1bb1ec402475b94ad00`。人工TC TC-005-sc5-evidence，分配 complete-1、complete-2、complete-3、legacy。自动TC只承担case-1/other-sources。

A5/B2–B4/D2原文支持全部三条criteria，没有新增产品行为。步骤可照做：目录给出原件入口，逐项读响应、消息和服务事件，保持原业务时间和安装身份。不得以expected或旧passed自证。

| 检查 | 可执行性和原件准备判断 |
|---|---|
| complete-1 | 可进入观察。isolation-run9/isolation-result.json有停止规则、完整reads、old_reference_read、local_search和requests_after_stop；可独立核对local-A旧一条，禁止append/new只在本机。当前debug测试分别断言完整Hub集合、出站禁传标记及旧A读取。 |
| complete-2 | 可进入观察。同一原件expected_bodies须与reads逐会话独立比较：允许D（本场景B）旧+append、remote-B另一设备旧+append、vibe-V旧+append；isolation-links.json给关联，service-events给实际HTTPS serve-hub进程。不能只比总数。Vibe来源为合成归档；SPEC明确不要求真实staging。 |
| complete-3 | 可进入观察。compat/linux-compat/windows-compat-run8真实旧包迁移前、未迁移新设备与迁移后材料齐全：migrated-old-device旧writer exit1/HTTP409，state confirmed、old_read仍旧正文；unmanaged-old-local有独立未迁移设备正文。每个E3/E4还须读各main run的initial-stop-replay（versioned/nonversioned均409、before/after不变）和随后恢复允许的真实upload/read，不能拿三平台兼容代替四个服务入口。 |
| legacy | 可进入观察，与complete-3共用原件；当前SC10 TC-005-register的真实断言补新连接注册即拦同设备旧writer，另一未迁移设备200、旧式原文读取200；SC2 CAS补已确认限制后的旧请求，不能在此重复伪造自动身份。 |

版本适用性：原事件isolation为7ab6d6c，compat及早期main为d80，Mac系统Hub main15为7c；均保留manifest安装清单与服务事件。实际比较7ab/d80→ba8：federation/core/project_control/search_merge及Hub策略/归档核心字节一致；references变化为新范围title仅选中消息（本旧A单消息读不受扩大）；API/CLI变化限双版本reconcile；upload变化包括reconcile先CAS后保存及目标派发校验，不能笼统以Hub未变宣称整个Local未变。当前isolation debug直接走最终choose/push/read闭包，当前CAS/registration与reconcile21补控制路径；scope11/15补范围标题；完整Hub模块比较final-package-comparison21及manifest支持服务端复用。实际观察需把这些材料连同调用闭包写入收据。

完整回归receipt于2026-11-22T09:53:42Z结束exit0，stdout与inputs摘要核对一致；JUnit逐case确认isolation、registration，以及Vibe原有历史发现、追加、失败重试、凭证重启/混合项目、事务回滚、延迟回复、范围消息、迟到归属、流式检查点、仓库身份host/port/path、停止取消均无failure/error。把tests/test_vibeinsight_sync.py这些用例及test_vibeinsight_boundaries的lookback/target-isolation/invalid-interval分配给complete-2，使用full-pytest.xml实际case结果，不能仅写234通过。

边界推演：若仅A旧副本正确而B/另一设备/Vibe被关闭，tests/test_upload_isolation.py:37完整独立集合首次拦截；若只保留B而其他目标缺失亦同。若A禁止新会话被拦但旧会话append漏传，集合与后续出站字符串检查拦截。动作前各来源已经有旧消息，旧A引用在停止前取得；动作后才新增的数据不冒充已存在状态。原件的完整独立expected_bodies与逐会话reads会拦两端同错或误用同一会话。增加同条件第二个项目属于可选补测。

结论：TC-005-sc5-evidence各分配检查的设计与原件准备有效，可进入本轮实际核验观察；人工执行与另一位执行Reviewer仍待完成。
