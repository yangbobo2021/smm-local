# SC10 complete27 人工准备独立复审

AT-SMM-005/R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；Reviewer /root/review_complete26_prep_c；2026-11-22T10:10:29.912378+00:00。

结论：needs_revision，implementation；新的自然设计已补旧非空关联前状态，实际探针因无依据的完整扩展对象相等断言提前退出，且失败前未保存after响应，complete-3尚不能作为完整可核验通过来源。未认定产品缺陷。

## 审阅摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc10/request.json` SHA256 `63c1ccda53686b92262a21b19af10b2776355288182923712d0e3beec9f1f007`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete27-sc10/result.json` SHA256 `1bd751f7d61a3ace96fe2ab437223c0933c9433018f3e8469ca6aff45ad7ba13`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc10/request.json` SHA256 `b99902445a88c6cbff2bc5585167fab7cef94df54180d25221d4850f033b8feb`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete27-sc10/result.json` SHA256 `da3c69aa60a6c88c8b2a351fd8b67af3bb276056f9fea8ff7fbb0398aa88147f`。
- `.acceptance-local/native-v1/AT-SMM-005/debug/debug-complete27-sc10/result.json` SHA256 `dbbbc033aaecaa36c306cd3493130b1a64f0f7e115babdf371760686e8ae8af3`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC10.md` SHA256 `000994299dc27542482dd0be4a6b2e73eabc743468f181186ef029db317dcc80`。

本轮实际读PLAN12.4、当前设计/匹配、完整控制器及当前真实debug附件；原确认SPEC A10/B8/D1-D2及AGENTS/技能约定沿用实际已审文本。新增义务additional-legacy-links引用原complete-3，不新增强制全对象同构产品行为。

## TC/check准备

- TC-005-sc10-evidence仍分配complete-1/2/3；TC-005-register仍adoption，TC-005-legacy-links新增additional-legacy-links。
- complete-1：可按原26MD实际三OS compat-run8旧/新组合、0.4.0实际模块、new-old不上传/按项目只本机/能力说明/旧原文路径核验；原件时间和d80版本保持不变，完整依赖比较仍由f45/7c/ba8范围与对账补证，不能只看status。
- complete-2：可观察。三compat目录的migrated-old-device/unmanaged-old-local/actual-hub-change以及register27真实200/409与全文集合仍可定位，合法旧设备接受、迁移后同设备拒绝和旧读取保留不被新测试错误推翻。
- complete-3：需修订implementation。当前legacy-links真实旧包已建A/D双向local linked_ids，Hub links=[{a:1,b:2}]，cursor值2，两个独立完整正文及旧精确引用；commands内升级后Local A/D完整投影/路径/ID/name/相互linked_ids、cursor、Hub两个owner/source_key/name与同一links均已到达并通过。失败点是line63整个messages对象相等，旧响应无新Hub固定新增canonical_id/content_version/source_order及origin.source_order；D2增量字段允许，A10不要求完整JSON同构。前后同错应通过独立两条fixture正文/身份/原引用及完整计数排除，而非把合法元数据加入判失败。after-upgrade.json未生成，因为save晚于断言；HTTP after未落盘，后续关联查询、策略all显式检查、再次同步幂等与after汇总均未达。需要先保存原始after再按有依据业务字段投影精确比较，并跑完后续步骤；禁止以我已读新代码产生预期替代实际响应。

## 版本与最低平台范围

当前新Local/Hub由installed逐文件核ba8模块与独立包隔离；actual-old-local/hub记录真实0.4.0、前置身份与完整模块清单。before-upgrade、commands、manifest、service-events、result failed与cleanup无失败均已打开。debug27全部bindings/artifacts SHA实算无差异；原失败不覆盖。错误断言使additional-legacy-links覆盖不完整，因此auto covers空；旧register独立通过不能补新检查。

SPEC E5要求至少一个实际支持平台的新旧包组合与恢复，PLAN12.4据此在一个平台补共享迁移分支。关系/cursor/旧引用依赖core/federation/HubProjects/Hub read，未引入平台分支；原E1三OS真实升级和包组合证据仍存在，故只修复并复跑本Mac独立实际包专项即可，不要求每OS再跑该变体。

自然设计完整目标为两个项目、两条原文：只首目标保留会被Local/Hub完整字典与links集合、逐消息集合拦截；误用同一引用须分别比较独立session/正文/消息标识。当前原始after缺失及未达后续检查意味着这些最后拦截尚无完整证据，准备须待修后新debug和复审。原26缺口已由设计解决，不再退回scene/design，不将测试错误写成产品失败。
