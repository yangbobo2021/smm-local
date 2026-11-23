# AT-SMM-007 最终候选设计与调试独立复审 v2

本轮15个debug目标、27个自动TC的结论为 **26 passed、1 needs_revision（design）**。需修订的是 SC8 / TC-007-packages 的检查分配：包构建安装本身有充分原件，但所分配 packages-2 同时要求完整回归和三系统CI，当前自然设计与TC命令没有承接后两项。未发现本批已执行断言的产品失败。不认定正式执行、7个人工项、R007或整体交付通过。

Reviewer：`/root/review_007_final_design_v2`。工作根 `/private/tmp/smm-007`，仅只读产品、测试、冻结证据并写本轮15份唯一JSON和本报告；未执行产品业务重跑、登记、GitHub、ESXi、日常Hub/VibeInsight或服务操作。每份意见完成即通知主Agent登记。

采用 handoff `.acceptance-local/native-v1/AT-SMM-007/work/final-debug-v2-handoff.json`，15个目标及各自SHA逐项实算相符；定义 `.acceptance/native-v1/AT-SMM-007/definitions/000007.json` 实算SHA为 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。目标采用候选 `245c236ddc41057cd78694902283574d1175e309`；收口时HEAD为 `873b500dcd93062eaa0cdab6c7c332c3fc6bd080`，两者在src、tests及本批构建/包/检查探针入口无diff；全部本批bindings仍逐字节匹配。不得将后续定义或重新分配未复审的结论移入本版。

实际读取交付验收SKILL及execution/reviewer、case-preparation/design、implementation，原AGENTS、007 intent/spec/plan及项目文档库授权原话、PR Review Prompt；后者仅作原始整体入口检查背景，本轮不代完整PR Review。按需求→场景→自然设计→匹配原声明→实际独立断言/探针→本次原件的顺序判断。当前主测试SHA `42562ef13fcccef6b98e1f7534a7db7575712aed23d732459cd85622cee6fe77`，review补项 `060f6b0bf82b5e16854d240c06a945e3717b4bc0e5e57b81efdfca0747aa244a`，PR39补项 `0df2d96991182b6ccf5c46232c9b8211afed70fe39d9584267d3c3e13eb92bf1`，status补项 `81e29a9751c1b2e3f6793ea2b70ba14e285ae0c72ab27488e1db1f02f69d0d00`。逐份读回最终自然设计、匹配source及covers，源选段与当前行逐字匹配；没有因定义快照clone而删除旧义务。

**唯一阻塞的设计发现。** packages-2 原句为“Local和Hub独立构建安装，全模块源码/wheel/安装摘要一致；Hub无Local发行包或客户端依赖，完整回归及三系统CI通过。”这可从SPEC A8和PLAN推出，不是场景额外增需求。design-sc8-final-v2只描述包构建、独立venv、模块与CLI/MCP；match-sc8-final-v2指向tests/test_hub_documents_contracts.py:1125–1134及hub_documents_packages.py:23–95，实际只执行18条包命令。反例是两包全部正确而完整pytest其他用例或最终head任一OS CI失败：本TC仍可全部通过，没有最早拦截点。主Agent核实没有实际TC承接完整句，PLAN的单独门禁不等于本TC已覆盖。最早修订阶段为design：保留原条款去向，为完整回归/三系统CI独立分配验证项，包TC只承接其实际包范围，再重取匹配/debug并独立复审。本版packages意见covers为空，不能授整句passed；这不是产品缺陷。

包原件缺失这一旧问题本轮已关闭。TC附件内package-probe-originals完整保留18命令的stdout/stderr、commands.json、result.json、local/hub-expected.json；逐命令exit0及两流SHA实算一致。独立解释器-I/-X utf8、清PYTHONPATH，Local30/Hub31模块完整集合及当前源→wheel→安装SHA全匹配，Hub实际find_spec(smm_local)为None，真实两包项目/纳入/刷新/检索/read各自独立role正文准确。本轮不再沿用旧insufficient_evidence理由，也不因包通过放过上述分配缺口。

逐目标原样意见（每份JSON恰含目标全部实际TC；passed完整认领其全部分配checks）：

| 场景/目标 | TC真实结论 | 原样意见 | 目标SHA-256 |
|---|---|---|---|
| SC1 / debug-sc1-final-v2 | policy-choice passed | [review-debug-sc1-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc1-final-v2.json) | `e5f438c27d496baaecdaab26766a460d231f9663f55bade5013e1aa15e1c945b` |
| SC2 / debug-sc2-final-v2 | sync-boundaries passed；sync-publication passed；sync-retry passed | [review-debug-sc2-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc2-final-v2.json) | `a8f7b149465d93989578182aaca8a3d89ad923d2312a39b78bfe4a40411690bb` |
| SC3 / debug-sc3-final-v2 | overlap-publication passed；paused-lifecycle passed | [review-debug-sc3-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc3-final-v2.json) | `a656a196420d2c731942824983c96143e3a2851e091468500895bcaa243ce54a` |
| SC4 / debug-sc4-final-v2 | ordering-concurrency passed；origin-identity passed；recovery-controls passed | [review-debug-sc4-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc4-final-v2.json) | `2ea21595c7b4b8ac941444961083ab0c90012a8236af2002cca92385a1abf89e` |
| SC5 / debug-sc5-final-v2 | hub-native passed；project-scope passed | [review-debug-sc5-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc5-final-v2.json) | `44ac614ac0970353fff271b5b601837225d4c4ec2a14dacacffb5d94e5921df1` |
| SC6 / debug-sc6-final-v2 | search-candidates passed；search-fallback passed | [review-debug-sc6-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc6-final-v2.json) | `e761101509d5d0f72432af31e8b3eb1c62963ab45169fbe7e19f8db9a2be7382` |
| SC7 / debug-sc7-final-v2 | read-exact passed；read-rejection passed | [review-debug-sc7-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc7-final-v2.json) | `b8e6695424166d97630da68e9b8fa6d6f5c36c3b6fe55ceb39c3604df11c7c3f` |
| SC8 / debug-sc8-final-v2 | compatibility passed；packages needs_revision | [review-debug-sc8-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc8-final-v2.json) | `6e3bfc6ed190e03209436952476e35448283b14951d7a085e55d3c2c46658d93` |
| SC10 / debug-sc10-final-v2 | library-ingest passed；library-update passed；project-ownership passed | [review-debug-sc10-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc10-final-v2.json) | `c3d5d1644cf60f168a9052d4790ed1778f61a4839900fdf59e6209ecbb9eaeeb` |
| SC11 / debug-sc11-final-v2 | listing-coverage passed | [review-debug-sc11-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc11-final-v2.json) | `64f2777cfaad5bf6af52618f056d3edd7e026ece90842104aa3a94761ff691a7` |
| SC12 / debug-sc12-final-v2 | snippet-conflict passed | [review-debug-sc12-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc12-final-v2.json) | `182133af6da960fd5c184a8c3354da130ef37785398672f96689cc71d448577c` |
| SC13 / debug-sc13-final-v2 | cli-scan-boundary passed | [review-debug-sc13-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc13-final-v2.json) | `1611219c4a41911cdb2fe150d8d6480a63ff100d7b53cf377f585c8c53973260` |
| SC14 / debug-sc14-final-v2 | web-review-feedback passed | [review-debug-sc14-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc14-final-v2.json) | `a553b5eb5d2cc75ceceeaa1d1245b5bbe5613686dd1932d0dc38dfcf83429fb9` |
| SC15 / debug-sc15-final-v2 | hub-status-provenance passed；hub-retained-state passed | [review-debug-sc15-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc15-final-v2.json) | `2130d791b37c334d7bd582213447a21c20546e8f1b25b99f1024972eb3db7aed` |
| SC16 / debug-sc16-final-v2 | folder-guidance passed | [review-debug-sc16-final-v2.json](../.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-debug-sc16-final-v2.json) | `b6611507e4d3cbcb3f2b8dad382192d4f66cb0350dfee6884a4ff66f36995f3c` |

逐TC的reason均分别交代场景/设计与实现结论，并以当前目标、动作前状态和动作推演“首目标正确而其他目标错误”、遗漏状态、两个结果同错或误用同一目标，引用首个实际拦截断言。已覆盖会改变判定的active/paused、device/native、零/多项目、同generation换Hub、合法另一身份/非法域、独立版本/资格等差异；在这些差异已覆盖后，未仅因相同条件下更换名称/ID或增加等价样本继续阻塞。

原件真实性核对覆盖全部15目标、所有当前bindings及6752条artifacts清单引用，无缺件或SHA不符。27个自动TC都按精确选择器单独运行exit0；SC14和SC16各有两个端参数，因此其stdout各为2passed，其余各1passed。兼容TC内旧005/upload/Vibe/help子回归为42passed。结论依据实际断言和原件，未以result.status或stdout一个passed字段替代业务核验。

两份无损封装manifest均逐文件重算gzip SHA/长度并解压重算原SHA/长度、完整JSON解析：sync-boundaries 2742份、32444815原字节；library-ingest 494份、13469934原字节，共3236份/45914749原字节。2MiB逐16000码点窗口及9成员增长来源的尾部均保留，没有截正文。conftest只在测试结束后封装，包原stdout在pytest临时目录清理前复制，均不改业务输入/断言/退出码。

历史审查适用性逐项核实：preparation-design-review-v3的20声明仍由42562ef保持，当前重新读断言/证据，未把19红灯或旧passed直接移用。green-review-v3指出的列表/片段缺口分别由SC11/SC12当前060f6b声明承接，且SC5完整项目集合、SC6摘要负控保留；PR39补绿中的SC13/14原F1–F4检查均保持。pr39-review-v2的F5–F7由SC15/16承接；status-red-review-v4、status-green-review-v1中的SC15第一检查仍归元信息TC，原第二检查已独立到retained TC，初始/确认暂停/恢复的四来源/四命中全集及共享资格实际均到达，未因拆分遗漏旧声明。旧红灯未到达路径只由本次真绿灯完成后才认领。

本轮实际图像检查：SC14本目标4张PNG（hub-web-review、local-original-provider、local-web-review、hub-management-empty-shell）逐张打开，分别看到A/C成功与B UTF8失败/真实库、Local→Hub同bundle回退与独立正文/身份、未认证空壳及凭据来源。两trace实际611/282条记录及30/21网络，HTML SHA等于当前产品，无after错误；两轮A/B/C请求的submission不变，末两read的reference完全相同。SC15打开本目标Hub暂停PNG及trace关键JPEG，清楚可见只读Status P、暂停保留/共享可更新、Q允许与两native；trace121条无错误。SC16打开本目标两PNG和两trace的关键纯目录/混合JPEG，最终图中Local/Hub对应指引与valid唯一库ID正确；trace273/290条无错误、每次drop重定位并真实isDirectory，先自检枚举再清零。Local选取的纯目录screencast帧为报告重置瞬间，未当其本身显示指引，纯路径由当次逐行可见断言/trace inner_text/00017支持，最终PNG另完整显示相同适用指引。各意见写有精确文件/所见/检查归属。

状态探针已按本次源码与原始自检结果复核。另在内存AST抽取retained两个实际helper，只装入独立人工四来源夹具：初始/暂停/恢复三个正例均接受，Q错origin、漏native、native误暂停、Q错项目、Q命中错state、重复P代Q六负例均拒绝；原输出为六条REJECTED和“Current AST: 3 four-source positive states and 6 independent negatives passed; no product execution”。此自检没有运行产品，也不代产品结果。

需要保留的真实边界：SC10 CLI竞态本次原件为写exit0/恢复exit2，恢复stderr是“此档案已有同步服务正在启动或运行”，是控制互斥，不能写成实际旧epoch竞争拒绝。随后fresh state恢复、旧ref拒绝与显式refresh V2均实际通过；各写路由旧epoch另有独立负控。本地TestClient/Chrome映射HTTP只支持局部产品/API/UI回归，不是E1真实网络/TLS、普通账户身份、服务或物理跨OS传输。

完整回归附加原件 `/private/tmp/smm-007-status-fixed-regression.{stdout,stderr,xml}` 已直接读，334passed/1skipped，XML唯一skip为Windows专用slow-background-service测试；它不代27个TC原件，也不修复packages-2未分配问题。包v4及托管CI另有执行记录，本轮没有操作GitHub或替最终CI结论。

7个人工项仅匹配：SC8 user-discovery（真实旧页面、凭据内存/认证头/reload、两端纯文本不执行及主入口路径）与SC9 E1三系统/E2跨机器、Linux服务、Windows服务。已读当前设计/match-sc9-final-v2的分配；本轮未评其正式执行，不授人工passed。当前Mac v10/用户路径v3原件不在本次自动debug授passed范围，后续正式记录须由执行Reviewer独立判断。Windows实际SCM/LocalService、必要物理跨OS、全部当前同版正式/需求级判定及最终CI门禁不得由本报告消除。

本报告限定handoff冻结15目标。后续SC8拆分或定义快照更新必须保留本版needs_revision与原件，使用新请求ID重取受影响证据，不修改本版意见或由本Reviewer代登记。
