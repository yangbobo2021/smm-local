# SC9 complete31 人工准备独立复审

AT-SMM-005/R005；定义003 SHA256 493e01b72eee696fccea84c88d0a2e44997cc08a0acc2244ee752755dbf5c98e；Reviewer /root/review_complete26_prep_c；2026-11-22T11:03:57.857931+00:00。

结论：两个人工项的当前设计、步骤与准备来源有效；**准入这次Windows新外部长轮正式运行**，须先更新相应原生PLAN进行中再启动。尚未执行的新正式轮次不能预授通过；原30自动timeout仍不足，不改其结论。

## 当前审阅与真实SHA

- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete31-sc9/request.json` SHA256 `fff061d4c9b0aee391119953ac8cf26249e8a769c21c61d151fd6fa9676138bb`。
- `.acceptance-local/native-v1/AT-SMM-005/case-design/design-complete31-sc9/result.json` SHA256 `f990d2c203d1379b651cc6b2d6f9c70906fbbea8c96e2592673a33169bd374a5`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete31-sc9/request.json` SHA256 `14e48dc58b3a582680cc403461cb6f600af24910856218e7605ec741380de3c0`。
- `.acceptance-local/native-v1/AT-SMM-005/match/match-complete31-sc9/result.json` SHA256 `481e6aaa3cf5034e0f3f9117321d50fca2a5805c2ef5f5e5fb7822a5c29c50a7`。
- `.acceptance-local/native-v1/AT-SMM-005/debug/debug-complete31-sc9/result.json` SHA256 `3ef4dffc65f525f3fd4c8a9ee5d6a57f619eed313ebb9e5ba9b200d3986e6a57`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9.md` SHA256 `f6c7f8ef711ee4510f2bdfa6419466abfd3170b6f7f1b4df309e50ffb2065043`。
- `changes/005-selective-conversation-upload/evidence/20261122-native-completion/steps/SC9-windows-empty.md` SHA256 `21147e7893c00e90a2882e4b3d1f05db92f1c80cc4ff6529f0faef17e2733ebf`。
- `changes/005-selective-conversation-upload/plan.md` SHA256 `8db320775106c941e76e26f5021910cb3672f4b2221adf473ba6446933c7bb63`。
- `scripts/acceptance/selective_upload_empty.py` SHA256 `a277e5bd53df16cee76e3fd49f671c90863585ff584921ea544e5ff545a1c8cf`。
- `scripts/acceptance/selective_upload_empty_recorded.py` SHA256 `04350a3b195613748e25e1deb4063028e8f447ae2bb969434753b3fbee32ad55`。
- `scripts/acceptance/selective_upload_empty_windows.py` SHA256 `eed0b6f6f91e812ffa3287b4e39acb1daf8ef0d6d2fa4aee0e287f395e67b960`。
- 外部长轮计时/捕获脚本 `<task-path> SHA256 `f388bb6a96143131cc2237ae4a3b03ec21668f0ad8042988737c093f915d3f45`（已读源码、未运行）。

已实际读取design31/match31、steps两源、PLAN12.5、外部长轮捕获脚本、当前4auto及Windows回收完整原件；保持原SPEC A9/E1/D4、AGENTS/技能标准。TC-005-empty-windows及empty-e1-windows身份/业务预期不变，仅kind从auto改manual以记录真实约320秒业务，旧auto超时收据/检查去向有明确说明；未制造缺省字段或修改工具。debug31仅四真实auto，JSON未混入两manual。

## 人工项一：TC-005-empty-windows

| 分配检查 | 准备可执行性、原件与版本 |
|---|---|
| empty-e1-windows | **准备有效，准入新外部正式运行**。steps/SC9-windows-empty.md给VM76 MAC/此前tasks空/普通Limited身份、真实empty_recorded命令、唯一ACCEPTANCE_EVIDENCE_DIR、等待真实结束、六响应/两图/trace/完整包/worker/清理取证与另一Reviewer。当前match将同一TC明确kind=manual且active，关联该源步骤，适用于原生manual（casework.mts:282–326）而不伪造自动debug门禁。外部脚本只创建新目录/捕获真实argv、开始结束、原stdout/stderr/exit、输入SHA，实际业务仍版本化recorded→Limited→empty控制器，未把旧result当新执行；out已存在则拒绝，业务timeout1500时记录error并要求先查远端，不静默success。 |

准备正控原件目录platform-debug/windows-empty30-recovered已完整回收，本人实际读manifest、正控、六响应、commands、local-service、service-events、worker、result/cleanup、ZIP及两张原PNG。真实Windows11、普通<ordinary-user>/elevated_admin=false；Local25/Hub24完整模块等ba8 clean候选；真实worker12868 exit0，事件2026-11-22T10:37:54.167326→10:43:14.599196UTC（320.432秒），serve-hub7516清理为stop_requested=true/exit1，cleanup=[]，符合Windows主动TerminateProcess边界，不把早退1一概当正常。浏览器158.0.4370.33、page_errors=[]。

六响应all/project各CLI/真实stdio/Web均空、两端complete、无失败原因。两PNG已逐张实际打开：确定无命中的uniquelyabsentquery、没有匹配结果、本机/Hub已检索；all显示所有项目，project显示synthetic.example/005/V、A、B。ZIP完整testzip无坏文件，network中两次POST /api/search状态200，内置原postData资源分别scope all/project、local=false、query同不存在词；与画面、原响应和控制器定位对应。当前只作为准备试跑原件；不能改写原debug30为passed，也不能替代即将发生的正式新长轮。

关键准备原件SHA：manifest e69e691198145470977175523046e02edfeaf0993f57df6d3e2f49f8979158c9；successful-empty.json 0ba4a870371c7a279dc0985da5a2a9e8324aa5bac6e24058f4bf703a349b4c66；cli-mcp 4b8f83c28533bbd86869629ab6743dff0e02600d04d82c4a7233ef778eb89929；all.png e92227c1cfff776ddef07a497c73f07166831407d7e322926bc7c6ea1c4ba92c；project.png ef31b8cf352c2340ddd3bd3ebf1677b27f124a1aab6b834544a55e0bcdaa345d；trace 8964ab826d5a00f6eb5351a00d7e5a2eab0d042c08135e2bb02e368769e9cd2a；result e6481ddf6aeb8cfc5f03e65c9b314e5b3e5628d0825eb0244b0eb023f738da2a；worker d7cb49fed1639eb4abb45dabea74f9db019167d7a1aba39de8deb2517a3b12dc。均实算。

新执行时保持已审捕获脚本字节，并将其源码副本/此准备MD及SHA与新process.json一并归档（外部脚本不在它自身src/scripts输入清单里，观察记录须另保留其真实来源）；这不要求修改业务或计时器。核process实际外部包装exit0、error=null、输入前后相等断言及外层捕获脚本自身真实完成，不能仅看到内层业务code0就忽略脚本后续验证失败。随后按步骤保存本轮完整包/身份/六响应/两个原图/trace/worker/结束/cleanup原件。若仍timeout或原件不全，保留uncertain而非重跑未知副作用。当前未发现阻塞该新运行的设计/步骤缺口。

## 人工项二：TC-005-sc9-evidence

| 分配检查 | 当前准备意见 |
|---|---|
| full1 | 可观察。原E1三平台断线A/A-new而排D/G、coverage/503原因/精确原文及PNG/trace按前轮已审原件可定位；current fallback31真实exit0，只认其共用分配，不把旧事件改成本轮平台。 |
| full2 | 可观察准备有效。31共用empty及Mac/Linux实际空查询四auto真实exit0、独立六响应/关键图/trace齐；31四张Mac/Linux原PNG也已全部打开。Windows已回收30完整准备原件解决可执行性疑问，正式full2应等待新Windows manual实际完成和独立执行复审，再结合原offline-all/重连/explicit_local原件核验完整平台义务，不能用此准备MD提前称formal full2通过。 |
| full3 | 可观察。原41之外partial_hub_failure/local_error/incomplete_candidate/5类invalid_scope在29完整JUnit各自passed，按原独立完整集合/部分coverage/双失败/排除不补召回断言与当前不变源字节核验，不缩成仅当前四TC。 |
| full4 | 可观察。limit0/51 ValueError且无Hub调用、Web空query400与原三OS三入口断线/恢复/读原文原件可定位；当前31不声称所有参数组合，也不据UI预期自证。 |

这两manual的先后应是先完成独立Windows业务/原件，再核完整SC9证据；无需先有SC9或R005最终passed，避免循环。原平台d80/f45/7c与ba8当前适用性仍按前轮完整依赖/模块与scope11/15/reconcile21补证，不能只一个不变Hub模块推全部有效。新Windowskind变化仅记录编排，原41TC身份/断言与其他平台范围不删。

## 自动结果、反例与正式边界

debug31目标SHA3ef4dffc65f525f3fd4c8a9ee5d6a57f619eed313ebb9e5ba9b200d3986e6a57，四auto全部bindings/artifacts SHA一致、实际exit0；共用原始2附件与Mac35/Linux34附件已按当前JSON/PNG重新核。设计31自动目标只包含四项，本意见JSON没有Windows或总人工项。

所有成功空查询以固定空集合+独立coverage/无原因逐scope/逐入口判，正控及实际请求排除从未执行；两侧同错不能仅靠互等通过，Web两范围原画面独立核。只首scope/入口正确会被其余固定断言/画面拦截，不增加无依据等价ID样本。

共用完整回归仍29真实251pass1skip，当前src/tests/audit未改，不称再次运行；原生timeout不因远端worker0或准备复审而变成成功。正式Windowsmanual需绑定新实际事件、原字节附件/product_files及当前设计/步骤/准备MD，再由另一独立执行Reviewer实际打开新图与核全部SHA。其他自动项继续原生execute。准备工作未启动正式新长轮，也未改产品/工具/原件/旧意见。
