# SC12 人工项准备独立复审

AT-SMM-005 / R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e。Reviewer /root/review_complete26_prep_c；复审时间 2026-11-22T10:02:33.428505+00:00。

结论：自然设计与准备来源有效；complete-1/complete-2可进入真实人工观察，complete-3有执行前置条件：其余11场景全部已取得当前有效通过证据后才观察完整台账。现在不能判SC12或R005已通过。本场景仅TC-005-guidance人工项，没有也不需要自动debug目标。

## 实际审阅及摘要

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc12/request.json` SHA256 `a069c58ab09718edb44d50411019f06273b0ec3c9eb876183c02f43d29fae953`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete26-sc12/result.json` SHA256 `30529f46822e998fbfa54696d380ea222fe56fa010f1d14a3ae2ab09c67a7911`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc12/request.json` SHA256 `bbdc4661748e60465cd0aef24e6e40964925409ddbb36c239205881fbcdc9163`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete26-sc12/result.json` SHA256 `b9304a439447edc726cefb33e7511ced993324151cf2f14154270884b52a1272`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC12.md` SHA256 `d2640a1b2ade804365759f9741cb6508123a2ee8426321bd9fac60f33356d071`。
- 本次实际打开 `README.md` SHA256 `7d39d6361c74bcd4955bdf9a487dd151497fddbbe71ff400c812fa375b1c02be`。
- 本次实际打开 `TRIAL_GUIDE.md` SHA256 `30a226cfc76571a1c434fc18a95d2a8f41d8a8e3bc8846dd08c27e0e01c294d7`。
- 本次实际打开 `skills/smm-search/SKILL.md` SHA256 `69f1dc2fc42c152cf628fbf56830e08d3bc54e7046d307f978b64c492b6912ae`。
- 本次实际打开 `src/smm_local/cli.py` SHA256 `f1133ae0cec7bfaccae9b93663c88870a589d88504a74cefa8769214a8aa86bd`。
- 本次实际打开 `src/smm_local/static/index.html` SHA256 `1afcb4a170768ba79fe43647febe010c5aa2ea7030cd79dce05310db87f25599`。
- 本次实际打开 `tests/test_cli_help.py` SHA256 `355468c0783ed01394d9f5a8a2bb9e3092e94c4899a654e8b745beef8e028bc1`。

已逐条反查SPEC A12/B1/D4、确认intent/plan及AGENTS/PR Review Prompt。三条criteria均有原文依据：发现路径、语义与旧帮助、必要环境齐全后才交付。文档检查一环境逐链接，E1实际操作仍三平台，无擅自增加平台组合。

## 逐检查分工及可执行步骤

| 检查 | 准备意见 |
|---|---|
| complete-1 | 有效，可观察。README用户主路径先说明已发布0.4.0，紧接“多台电脑共用档案”中005尚未发布小节，清楚介绍连接后可选上传/默认联合查询，并以“项目上传与联合检索”链接到TRIAL_GUIDE对应标题。指南明确本机projects取得ID、all/only/except/none及空列表、停止保留、reference读取、prepare-restore/状态目录/双版本对账。README“Agent接入”直接链接skills/smm-search/SKILL.md，Skill有相同范围、默认待选择、最小登记、当前包版本边界及恢复入口。观察应保留从README实际链接走到指南/Skill的路径及逐项原文位置，不能只从SPEC或直接给定深链接开始。 |
| complete-2 | 有效，可观察。当前已安装Mac解释器<task-path> SHA f1133ae0cec7bfaccae9b93663c88870a589d88504a74cefa8769214a8aa86bd与ba8一致；mac-reconcile21 manifest全模块匹配，旧帮助不是仅源码推论。实际help观察应以该解释器-I -X utf8 -m smm_local.cli并指定隔离任务--db，逐运行--help、upload --help、upload set/status/reconcile/prepare-restore --help、project/ensure-global/assign-conversation --help、search/read --help、source/source batches/source purge-batch --help；help解析在创建Archive之前退出，不需访问日常档案。当前准备仅确认入口/源码/旧原件，不能把它称作本轮已运行所有help；后续manual须保存真实argv/exit/stdout与包模块摘要。test_cli_help.py共6参数case（source/batches/purge × 新路径/既有库）均在本轮JUnit实际passed，断言完整帮助预期片段、exit0、stderr空、目录逐字节不变，分配旧来源不退化；不替代本轮安装包help观察。三平台实际CLI/MCP/Web入口材料见下段，每端按独立expected_bodies比较，不能仅三端互等。 |
| complete-3 | 设计有效、执行依赖尚未满足。必须在SC1–SC11正式执行/人工核验及独立执行复审全部有效通过后，以results.mts view当前输出逐场景核case_plan/match/执行或manual来源、有效review covers、missing_obligations为空、状态passed及产品/证据SHA；逐E1–E5环境核真实安装/账户/服务/三入口/重启恢复/清理。SC12当前自己的complete-1/2观察可成为同次台账证据，不能要求先有SC12或R005最终passed，避免循环。R005新独立需求判定应在十二场景有效证据形成之后。旧delivery passed/外部审查不替代本轮当前台账。 |

## 原件可用性与当前适用性

manifest所列9目录已核实际存在及时间/版本。mac-entrances-run10为7ab6，Linux入口run10为06dd，Windows入口run14为f45，global-cli11为f45，reconcile21三个为ba8。三平台入口专项local-project.json/ local-all.json /combined-all.json均保留各自CLI/MCP/browser请求、独立expected_sessions/expected_bodies、各自引用读原文、PNG和trace：显式本机project=A/D/private、all含G/U/U2/plugin，combined-all含本机/Hub/VibeInsight各独立正文及覆盖字段；global-cli.json保留同G两次、预览/确认、源重放后归属及另一待定会话；对账21有实际旧值拒绝/刷新成功和双版本请求。之前已逐张打开三平台reconcile21的stale-local-rejected.png，确见重新查看差异错误、对话上传四模式/项目选择/停止保留说明。正式人工观察仍应打开各自分配的原图和trace并引用原始SHA。

依赖核验不能只比较一个不变模块。当前已读d80→ba8源码diff及work/final-package-comparison21.json、reconcile-package-comparison15.json：后续查询/来源帮助/全局操作闭包不变；CLI/API/Web新增双版本对账、references修新范围标题、upload变控制CAS/目标核对。旧入口普通查询不能证明新对账，须ba8 reconcile21；d80不能证明新标题，须f45后scope11/15。原服务身份由SC11等对应实测证明，SC12入口专项不能替代E2/E3。原事件时间/版本与本轮读取时间分别记录，不以目录名称推断版本、不将历史平台执行改标ba8新执行。

## 本次全台账状态与边界

准备复审中实际只读调用results.mts view AT-SMM-005，返回定义003及R005 pending_delivery_review，SC1–SC12均not_fully_validated；当前SC9/full2成功零命中、SC10/complete-3升级前旧关系、SC11/full3已确认消息丢失恢复已分别在本轮MD给出具体需修订意见。因此现在complete-3不能观察成“齐全”。这不否定该检查的设计：如实保留依赖并在其他11通过后执行，才满足用户指定停止点。无需修改验收工具或虚构SC12空debug。

本轮full-pytest-receipt已结束exit0，inputs摘要2f79acd1d49efec1b4043a1616ed4d21b76499f695e4e9d5e646b1b4e2eec4d1实算一致；JUnit旧帮助6项均passed，Windows专属startup在本机skip，不将其当本机已执行。最终CI须在正式全台账观察时重新读实际状态/版本，不能沿用口头三平台success。

反例推演：只有首入口正确会由三OS各自CLI/MCP/browser的独立expected集合及原文检查拦截；两端同时误用相同target不应仅做互等，独立原文和实际scope/reference身份是第一拦截。发现路径的不同角色（普通使用者、管理上传的Agent、Hub维护者）分别有README→指南/Skill→本机ID或Hub状态目录来源，不依赖自行猜值。若只有部分场景通过，complete-3必须按缺项拒绝整体交付；不能拿自身“台账已核”反向证明SC1–11业务。当前不存在需要设计外增加的固定样本数量，等价标识变化仅可选补测。
