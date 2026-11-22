# SC6 人工准备独立复审

AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_b，2026-11-22T09:57:22.793403+00:00。准备意见不代表人工执行通过。

实际审阅design `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc6/request.json` SHA256 `822b623df65df112d217bdb5890223874f61c44d9f0afee8a0830a5012193d3e`；match `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc6/result.json` SHA256 `51630cb303f09b2a35b90d9c360d242507bec0e362650d0ef394c2e313d76986`；steps `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC6.md` SHA256 `410c1ad7e51ee1380926b1a850d10744eae95ba496ad5c4b8148a42dd84eb3cd`。人工TC-005-sc6-evidence分配full1/full2/full3/full4。A6/B5–B6支持四条criteria；没有额外行为。

| 检查 | 可执行性、证据可用性及边界 |
|---|---|
| full1 | 可进入观察。各main run的combined-stopped-cli/mcp-search、browser及reads可逐入口核对集合：local-A/local-A-new本机未传，remote-B与vibe-V来自Hub，排除remote-C/local-D；effective_projects为A/B/V。fixture和hub-links独立给定预期，不能只比较CLI=MCP。当前scope-race两窗口分别在返回scope、返回Hub候选时解除D/B并连接E/C；独立旧集合与新集合和每条原文断言补同一次快照。 |
| full2 | 可进入观察。mac-entrances-run10、linux-entrances-run10、windows-entrances-run14各有local-project/local-all/combined-all.json，逐一带CLI、MCP、browser、reads、browser_reads、requests及独立expected_bodies。仅本机requests必须空；local-project应A/D及A-private，不以Hub关系替代；全部应G、U/U2、有效插件来源及远端集合。已实际打开windows-entrances-run14/local-project.png：选择仅本机，显示A/D、Hub本次未请求，结果含A旧/追加、D旧/追加、A-private且原文可见。完整正式画面核验仍由后续观察覆盖各平台。 |
| full3 | 可进入观察。当前full-pytest.xml逐case通过：test_current_session_excludes_both_copies_only_in_the_same_source（同源Codex两端副本排除而Claude同号保留，include_current正控）、test_each_endpoint_receives_only_normal_n_without_topup_and_invalid_n_never_calls_hub（单次Hub search limit2，两端count2、最终<=2、非法N不请求、N50三条）、test_incomplete_hub_candidate_is_excluded_without_losing_valid_peers_or_topping_up（坏候选排除，a/good保留且只一轮search）。这些41之外源码已读，应明确在本check收据引用真实JUnit和输入绑定。 |
| full4 | 可进入观察。E1三main目录各combined-stopped-*reads及browser包含逐命中原文；三平台入口专项再次保存CLI/MCP/browser逐条读取。各E3/E4 main run保存scope/reads和service-events；scope11/15的split-scope提供当前标题修复后的范围原文，不以API共用测试代替实际服务身份。必须逐入口比较完整独立正文，不能只看source_session_id或三入口相等。 |

依赖闭包与版本：读取/查询链为CLI/MCP/Web→federation.search_archive→_validated_scope/HubProjects→Archive.search→references与search_merge，逐条读取走federation.read_archive及references.read。当前federation/core/merge/project_control/MCP和Hub范围/策略模块与早期主流程一致；d80的references标题读取有实际变化，scope11（f45后）及mac-hub-scope15（7c）补新范围标题。旧api/cli/static修改是reconcile输入与UI，不改变search/read入口；upload最后ba8变化的目标校验/reconcile不能用于宣称旧对账通过，本场景只复用查询路径；当前scope-race/test_combined_search真实执行补共用编排。final-package-comparison21证7c到ba8完整Hub模块一致、Local仅upload改变；需在后续观察中保留manifest/服务身份和原时间，不将新离线audit冒充平台重跑。

完整回归2026-11-22T09:53:42Z exit0，stdout/inputs摘要一致；已逐case核对上述边界、test_common_scope_is_one_hub_hop_without_local_reexpansion及invalid_scope五个输入。把one_hop分配full1/full2，invalid_scope分配full1；相关fallback类由SC9承担，仍可引用但不以其替代这里的正常范围。

反例推演：只正确处理首个本机A而遗漏D/HubB，scope-race:48-51独立effective/Hub/final身份集合首次拦截；所有端点一起误用新范围，则:48旧范围独立集合失败。两个窗口均真实改变关系，旧引用在新查询后再读，动作前旧状态没有被新状态替代。若CLI和MCP都路由同一错误目标，人工原件的逐会话expected_bodies与每条真实读会拦截，不能仅比两端相等。没有依据要求枚举同条件的第二套随机项目标识，作为可选补测。

结论：TC-005-sc6-evidence四项准备有效，可进入实际原件与适用性观察；正式业务、人工观察和执行独立复审仍待完成。
