# SC3 complete28 人工准备独立复审

TC-005-sc3-evidence：**needs_revision（design，随后implementation）**。两个会话/四消息的业务范围已在design28补入；当前调试仍因错误假定Hub每message有reference而提前退出。不是产品缺陷，不预授完整覆盖。

Reviewer/root/review_complete26_prep_a，时间2026-11-22T10:19:26.824225+00:00。AT-SMM-005/R005，定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。AGENTS/intent/spec/plan/PR Review/技能原规则前已实际读，本轮28交接、manifest、当前design/match/steps/源码/原stdout已读，摘要：
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete28-sc3/request.json` SHA256 `1e7c45521b3553371dcf151d9f486e2c354ccbf712a2c4fa9bca733ba197204c`
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete28-sc3/result.json` SHA256 `643ab1919e8849aeb4a77573e79aa78a43244952647e52dccbc298f782c3f7d8`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete28-sc3/request.json` SHA256 `d15cd9d544b6fe93369ac17abf5eabe0700c80469a8e609bb9d387f48e84577d`
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete28-sc3/result.json` SHA256 `02c8281f8d211dfcab02bda7a2d869c25bd3fe622cd8f6560657daae2ff6c534`
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC3.md` SHA256 `5d7de13f52f9f799f90b3f2ac429422ccd062170920cc4908bd43336dd6fd870`


| 人工check | 当前准备意见 |
|---|---|
| complete-1 | 可观察。三主客户端Web global/归属预览确认/reimport，三global-cli11真实first/second(id,key)、unknown None，当前global数据库完整唯一集合及缺cwd/all不上传断言。 |
| complete-2 | 可观察。当前global-query独立A/G/unknown集合、明确A-G前后与显式本机，真实scope11及全项目原件按其实际入口核对。 |
| complete-3 | 可观察。confirmation-bindings六真实参数依旧generation1、合法target变C/另一次实际确认改变affiliation；旧标识拒绝且完整五表快照不变、fresh预览无副作用与实际确认正控。28六附件已开且SHA重算一致，原project-preview完全未修改。 |
| complete-4 | 可观察。七主流程/scope的最小payload白名单/禁传唯一标记、真实Hub project list/link的owner/stablekey/账户与安装包原件；default/registration及离线audit支持，不用同名映射。 |
| complete-5 | 需修订design方法表述及implementation取值。design28明确两个已接收A会话各两条不同角色，独立四元组/来源会话、禁止B期间全量读取，业务范围正确。实际stdout三参数在line143 message['reference'] KeyError，只到上传4条与old_hits两会话集合，尚未move、尚未观察B禁止期，也无6次读取/physical比较附件。B3/A3仅承诺原A归属/旧引用可用，B7仅每条新命中有reference；不承诺Hub原始search的每matched_message有独立opaque reference。 |
| minimal | 可观察。直接核七实际payload/项目登记，不引用SC12未来总表passed构成循环。 |

## 最小且有依据的修订边界

把当前action“取得六个会话/消息旧引用”改为保留**两个旧会话opaque reference，进行六次读取**：每会话旧ref先无区间完整读两条，再沿同一ref分别以start=end=1、start=end=2读取一条。不得重新签发伪引用或为了测试新增message.reference产品字段。src/smm_hub/hub.py:495–518的Read reference路径真实传递start/end至reference_read；src/smm_local/references.py read按原引用消息身份与版本验证，再按位置选消息，是现有支持的读取方法。

每次仍使用独立expected按source_session_id/source/position/role/完整text/time断言；两个会话需分别定位，四条消息要逐一精确读取。在此夹具位置唯一1/2，用start=end能区分消息；重复位置另有原SC8专门边界，不需把这次再扩大。三个动作继续assign分别确认两段、map/merge共同转移；旧ref必须全部在B仍禁止且无后续规则保存时读取。原A检索两段、B无新归属、当前onlyA、不出known指纹/body、四物理行全量前后不变均保留。若只首会话或首消息可用，第二会话全量或任一位置单读的独立预期便首次拦截。

这只是更正实现取得/使用引用的方法与自然设计的过细方法假设；业务承诺与全目标范围不变。最早design澄清，随后implementation停止索引不存在字段；原preview/move-batch等旧源码/断言不应改。重匹配、真实debug、独立准备后才可认additional-forbidden-move-read覆盖。

当前debug28其余八TC实际exit0，forbidden三参数exit1且无附件；全部bindings/运行输出/有效附件SHA重算一致。完整回归28完成receipt为10:15:57Z/exit1，JUnit252=248pass/3同KeyError fail/1Windows专属skip，非运行中日志、非全套green。inputs绑定重算一致；七离线audit0仍只是当前核原件。已执行/未到达边界如上，不把准备expected或测试失败误记产品缺陷。

产品src仍ba8、各旧平台原业务保持d80/f45/7c真实时间/包/账户。Local双版本/CAS及范围标题变化仍分别由ba8 reconcile21、scope11/15与对应现行测试补，而非单个模块相同推全路径。前两轮本会话实际看过的必要原图未变，正式人工仍须按check逐原图/trace读取。当前complete-5不可进入声称完整验证的人工观察，其余check的原件准备不因独立测试故障自动无效。
