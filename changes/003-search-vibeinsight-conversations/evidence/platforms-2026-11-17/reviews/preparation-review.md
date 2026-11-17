# 候选平台验收准备独立审查（首轮冻结）

本轮只审查 P、G、三系统 C 的设计/实现/已有预演及 Linux H9 方法调整，不是最终产品交付判定；三平台正式 H 尚在执行，不预判缺失结果。初始 HEAD=8323f8c。后续 CI/其他测试夹具修订不在本轮范围，client/shared 源码在本轮未改。

已实际读取 AGENTS.md、已确认 intent/spec/plan、PR Review Prompt、scripts/acceptance/README.md、题列八个探针与三份新增测试，追读既有 federation/sync 测试、构建脚本和用户入口说明。先确认八个预演目录均存在，再读公开脱敏证据。没有访问私有 target/fixture 清单或凭据，没有执行测试、数据库、服务、跨身份操作；唯一写入为此文件。

## 需处理项

以下为验收漏检/补证问题，不表示产品已经发生假设中的错误。父任务已决定修订工具后重跑正式 P/G/C，旧预演保留。本首轮结论不随之后修订静默改写。

### R1 P1：C1/G6 的实际命中只有子集断言，解除后未检查实际命中

SPEC 170–172、180 行及 PLAN G6/C1 要求当前项目与每个直接关联项目实际命中，同时排除其他项目。client.py:129–134 对 effective_projects 作等式，但对结果项目只作 <= expected_ids，再要求当前会话和任意一个 VibeInsight 命中。A/B/C 或 E/C/D 中第二/第三目标丢失仍可能通过。shared.py:92–99 更弱，命中仅子集断言，空结果亦可通过；解除后只验 effective_projects，未保存或断言解除后的实际命中；links 输出也未验证重复建立后的唯一性。

最早修订检查器：由独立夹具/预先核对的项目映射取得每个目标的必有会话或独有词，逐目标检查包含/排除，并保留有效范围等式。解除后检查 A/B 实际命中、C 全局命中与旧引用，重复关系与独立预期集合比较。等价标记可用，不要求特定排名或无关总数。

现有三平台 C1 原始 CLI/MCP 响应确实包含各自三目标；Linux G6 两响应也包含全三项目。这些具体响应可以人工逐目标复核，不能仅凭 passed 宣传完整性。linux-shared-preview 缺少解除后搜索响应；G6-unlinked-old-reference 不能证明解除后的实际命中缩小，须补此动作证据。

### R2 P1：C2 没有沿 MCP 自身搜索返回的引用读取原文

SPEC 178、181 及 PLAN C2 要求每系统分别走 CLI/MCP 的命中→引用→原文。client.py:167–178 虽取得 global_cli/global_mcp，两类引用却全部取自 global_cli，再用 CLI 引用调用两个读取入口。global_mcp 只受171–172行来源集合和字段非空检查。

如果 MCP search 的 hub_id/conversation_id/hub_message_id 错误，CLI search 与 MCP read 正常，本用例仍通过，用户却无法从 MCP 自己的命中打开原文。首个需修订点为173行选样循环：每入口分别选择自身两类命中，使用其自身 hub_id/消息引用读回，再各对独立清单检查正文、角色和来源位置。允许任意已知合成消息；按来源位置索引独立正文公式本身可以保留。

现有三平台选中消息的 MCP/CLI 引用一致、原文符合合成规则，但使用 MCP 自身引用调用 read 的动作没有发生。需三平台补该动作；CLI 不因本项必须全部重跑。

### R3 P2：C6 未验证名称更新；Mac/Linux 预演实际是同名重复写入

SPEC52、173及PLAN C6要求改变显示名并保留身份/归属/关系。client.py:160–165 调 rename/push 后只验ID/命中，服务端忽略名称更新也可通过。Mac verify-3 与 linux-client-preview 的 C1-cli-initial 已是 renamed-mac/renamed-linux，随后再次写同名，不能证明变化发生。Windows初始 duplicate name、最终 renamed-windows，可支持该次动作。

应先记录旧名且确认不同，改后核对新名以及原稳定身份、归属和关系。Mac/Linux需要实际变化的前后证据；正式新档案若已做出变化，核对原始响应即可。

### R4 P2：G3 前置 cursor 未核验，G5 旧正文预期取自产品旧读回

SPEC158–161、PLAN G3/G5及独立期望要求在正确已提交位置上构造样本。shared.py:13–28 未断言T的独立十条基线，cursor UPDATE亦未检查来源键、行数和实际(K,event_id)等于计划值，28行只保存。G5:67 用启动时Hub旧读回的前十条作为预期；若两次产品读回同错则可通过。

最早应在启动/造数前核对独立声明的两条cursor和T的fixture 0–9完整角色/正文；G5应比较独立清单。现有 G3-starting-positions 实际late-A=2026-09-20T12:00:01/E000201、late-B=2026-09-21T12:00:01/E000301，与独立样本对应；四个boundary/inside在各自下界或其后，原文也正确。因此该次前置状态未发现错误，可有限复用；缺口是检查强度与G5独立基线，并非要求实际等待一天。

### R5 P2：P公开启动/退出没有结构化命令证据

PLAN P140要求完整无秘密启动命令、PID、退出码。platform.py:149–169、431–440直接Popen/停止，不走command且未另存argv/wait返回码；service_identity仅存Popen.pid。因此commands.jsonl没有这些公开serve-hub动作。

这不是产品故障：preview-standalone-2日志有77963→78029→78052→78069→78188真实启动/正常关闭，初末PID对得上报告；legacy PID78187亦完整启停。6→10完整正文/角色和N两条都符合独立合成规则。已有日志支持有限生命周期事实；未记录argv/returncode不可事后冒充实测。新P应保存每次argv/PID/起止/wait返回码，并确认子进程仍活着才接受健康响应。

## 必测判据、反事实与首个拦截点

- P需求来自SPEC121/124、PLAN P，一个平台足够。platform:202断言新状态目录，:216核对六条完整正文，:267–268比较十条完整角色/正文；首条正确其余错误会在列表比较失败。P stop实际wait直接子进程，保证停机顺序。新N只在:269验存在、:270保存读回，缺少独立全文断言；本次旧artifact的N人工核对正确。旧入口:437–438验不同Hub ID/空全局，:441–442验恢复原ID/T十条。
- G需求来自SPEC154–160。shared:47 required全集合、:48–52逐目标独立角色/正文：首目标正确后目标缺失在:47超时，后目标正文错误在其:52失败。但仅一个K错误过低，可能把其变成普通补齐并通过；两个K都错也不能靠最终原文证明起点，故R4必须动作前核对。
- 窗口外迟到不保证发现（SPEC159）。当前required不含outside-A/B，未强制发现或排除，符合需求，不应扩大承诺。
- 同时间排序/重读（SPEC157）：shared:77完整四条独立正文、:80重读仍四条，拦截首条正确余下缺失/乱序/重复。分页/跨批/固定上界须另映射既有共用测试/SQL证据，不能由此四条包办。
- 来源host/port/database隔离（SPEC107–109、160）：boundaries参数化每字段，独立早期正文/来源键；shared:126/129实际SQL换库。PLAN246已说明相同组合键路径用三字段回归+换库端到端，等价组合可接受，不强求三次SQL搭建。
- G/C一层关系：有效范围错先在client:131/shared:94失败；范围对而后目标无命中可漏过client:132–134/shared:95，见R1。两入口同错不能靠相互相等证明正确，须各对独立期望。
- C每入口原文：CLI在client:181–190比独立正文/角色/位置；第二类读回错误在其:182失败，两边同错且违背独立公式也在:182失败。但MCP search自身引用错误没有拦截，因为未使用，见R2。
- C离线/本机/恢复（SPEC183/184）：client:137–138验回退范围/原因/三会话集合，:142验本机直接关系集合；两入口分别执行。恢复:130/131重验Hub与范围，遗漏目标仍受R1。
- C旧历史（SPEC168/185）：prepare用真实旧源码上传后push_pending、不新增消息；:108验本机消息数不变、verify自身会话及:196旧引用。完整链须连接prepare输出和真实基线身份，不能仅把prepared.json输入当原始事实。名称漏检见R3。

共同词/独有词是检查手段，有独立会话/项目映射的等价样例可用。既有test_federation四同名设备TestClient同时检查范围与实际项目集合，可支持共用同名身份区分，不能冒称三系统C。仓库host/port/path已有参数化独立比较旧/新会话、旧关系及重新关联；本次SQL实际只变path，应分层映射，不能说SQL三字段均执行。

## Linux H9调整结论

完整数字POSIX ACL、owner/mode核验可以支持SPEC145“凭据限制非授权账户访问”的结果条件。SPEC未强制各平台跨UID open；PLAN248已明确与原H9方法的差别。platform:393–407检查文件/目录非symlink、owner为服务用户、组/其他权限为零，以getfacl --absolute-names --numeric读取完整ACL，拒绝命名user/group和default授权，要求group::---/other::---。

实际H9-posix-access-audit为目录0700、凭据0600、owner1000、无扩展授权；H1-service-psql-process为systemd主进程UID1000及其真实psql子进程/<readonly-B>。结合相同状态目录的成功同步，可推出服务可读，以及其他无特权UID在Linux DAC下不可读。授权所有者、特权管理员或可绕过DAC的能力不属被排除的普通非授权身份。

报告明确other_uid_open_executed:false，未执行跨UID open，不能说观察到另一UID返回EACCES。该子任务为passed-permissions-and-process-only，仅支持局部，不证明完整Linux H。Windows当前helper临时普通账号impersonate后实际open，Mac helper euid≠owner后实际open，三者须分别陈述。正式证据应串联ACL、服务身份/成功同步和同一状态目录；不需额外索取管理员权限来维持同一SPEC结果。

## 预演版本与有限复用

八份result均记录aeeff661a41b6a22a5286fc9e0a92e5a765ee9f6、dirty:true。按build_packages.py:32–43将Hub _archive映射回Local core/support/importers，shim使用真实from smm_local.→from .转换后，逐项核对每份candidate的21 Hub+19 Local Python模块SHA，全部等于当前源码字节（含本次cli.py）。不能事后改写旧revision/dirty为正式当前轮，也不能仅因dirty就否认产品模块一致。

|目录|实际可支持的事实|工具差异与复用边界|
|---|---|---|
|preview-standalone-2|Mac自行管理真实PID/日志、6→10原文、N、旧入口/重启|无probe-source；platform/fixture/shared/denied_read旧SHA不同，几个SHA也不匹配0114b54/0a3146c/8323f8c，无法复原完整旧源码差异。R5补记录。|
|linux-shared-preview|systemd背景、多K/迟到/跨天/新可见/同时间及两G6响应|无probe-source，旧platform/shared/fixture SHA不同，不能猜测完全相同；R1解除后命中及R4独立基线需补。|
|preview-client-mac-verify-3|UID501非root、CLI/真实stdio、已存在线/本机/离线/引用|client/mcp_process与当前同SHA，通用工具较旧且无旧源；R1/R2/R3。设备原文还保留旧误归属项目的多个origin，不能说全新干净夹具。|
|linux-client-preview|UID1000非root、CLI/真实stdio及具体响应|client/mcp_process当前相同，通用工具较旧；R1/R2/R3。|
|windows-limited-client-preview|普通token、stdio实际退出0、名称确实变化、Windows路径执行|client/mcp_process/denied_read/windows_limited当前相同；platform/fixture旧SHA不同且无旧源；R1/R2。|
|linux-permission-process-preview|systemd UID1000真实psql子进程、完整ACL、秘密扫描|有probe-source。platform当前相同；fixture逐条INSERT→原子批量INSERT并增加allow_cidr；shared当前增加G7后unlink；旧denied_read为Windows restricted token，当前临时普通账号，后两项不影响Linux ACL分支。仅局部通过。|
|windows-permission-process-preview|LocalService真实psql子进程、临时普通用户实际拒绝、秘密扫描|有probe-source，platform/denied_read/windows_limited当前相同；fixture仅allow_cidr参数/校验及默认回环边界差异，该局部不调用create。仅局部通过。|
|preview-mac-service-2|系统launchd生命周期/默认周期/原文/实际拒绝读取预演|有probe-source；fixture/shared/denied_read当前相同。platform新增实际父子进程audit、Windows deny X→RX；后者不影响Mac，前者本次旧预演未执行。额外H1-readonly-sql不在result.observations内，须独立关联版本/来源。|

无法复原旧工具源码时，已保存的原文/PID/范围/ACL仍可逐条人工核对，但status和文件名不证明当前整套通过。未保存动作、未变化的改名前状态和未走的MCP自身引用必须补证。fixture由逐条改原子INSERT影响并发读取/H8批次安排，旧逐条结果不能直接证明当前批中失败方法；不自动否定已逐字保存且正确的读取结果。

## 用户入口及未验证边界

按Intent角色回放：维护者从README多机档案到setup/status，再由52–56行明确能力/角色并链接指南来源配置/项目关联；指南90–105说明数据库维护者提供参数、所需列、全部可读项目获准、psql服务身份、周期/故障确认；107–118给自行管理状态目录/Token/TLS、配置/同目录重启。日常用户从README快速开始到Skill的resolve_project→search→read，范围、引用及Hub/本机关系职责明确。材料可达，未确认新导航阻断。

C5当前只存search --help和mcp_server --help，未见list_tools/schema实际回放或单独导航核对记录；可由独立文档审查/工具调用补映射，不能说两个help证明全项。G8接管状态、完整固定上界/跨批、pytest/构建/CI须另映射证据，本轮未执行或包办，不因这里未展示而判失败。

可选增强为校验器加入删除第二目标、仅改MCP引用、忽略名称更新的反例，不要求新框架。产品serve-hub已静态接入保存配置的同步lifespan，与新增测试意图一致；本轮未跑测试，不能声称运行通过。最终由正式H、修订后P/G/C、有限复用和问题闭环共同决定。
