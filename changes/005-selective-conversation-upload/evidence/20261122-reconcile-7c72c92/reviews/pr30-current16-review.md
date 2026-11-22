# PR30 current16 独立审查

审查对象：`7c72c92e902cae9b05b80ce829b516113292b17d`；三点 diff 基线：`78973cf7ae6759332c0a320f630f5ebfb44204b6`。本轮直接读取 AGENTS.md、changes/_templates/pr-review.prompt.md、005 intent/spec/plan 和产品源码/测试；此前审查意见不是本轮结论来源。全文审查完成后补齐结论与证据矩阵。

## 已实际确认的产品发现

### F1 / P2：Hub 在对账第一次读取后改变时，过期拒绝仍持久替换本机规则

- 位置：`src/smm_local/upload.py:249-251`（`_save` 在第二次远端版本核对前提交）；`src/smm_local/upload.py:153-158`（持久更改 desired、generation、submission_id、ack_revision）；`src/smm_local/upload.py:207-208`（随后才拒绝已过期 Hub 版本）。Web 调用入口为 `src/smm_local/api.py:292-299`，CLI 也共用相同 reconcile。
- 规格依据：B1（spec.md:17-21）要求缺失、无效或任一过期版本拒绝且不改变当前本机或 Hub 规则；A11（spec.md:256）要求拒绝不改变两端规则。该问题不是建议新增行为。
- 真实路径：用户从 README → TRIAL_GUIDE 恢复章节 → Web 配置“查看与 Hub 的规则差异”取得本机 none / Hub all 的两个版本，点击“采用 Hub 当前规则”。在请求第一次 `/upload-policy/status` 返回 all 之后，另一个维护入口将 Hub 改为 none。当前 reconcile 仍把旧 all 持久保存到本机，第二次 status 才发现 Hub revision 已变，抛出“Hub 规则已改变，请重新查看差异”。
- 影响限定：Web/CLI 显示拒绝，但本机规则已经从 none 改为 all，本机 generation 增加并成为 pending。合成复现中 Hub 保持 none，未发送任何正文；后续同步仍须通过 Hub 版本/冲突保护，不能据此声称已经绕过停止或泄露正文。此问题破坏拒绝无副作用承诺，给恢复/并发操作留下用户未成功确认的本机允许规则。
- 适度修正：将远端 CAS 失败/后续核对失败与本机条件保存结果统一处理，保证过期失败保留操作前本机规则与代次；需继续保护并发新保存，不能简单无条件回滚。补充“第一次 status 后 Hub 改变”与“第二次 status 后、set CAS 前 Hub 改变”的 Web/CLI 回归，分别断言拒绝、两端规则/版本不变、无正文派发；现有新鲜成功正控保留。

### F1 的可重复合成脚本与实测输出

实际执行命令：在本仓库使用 `.venv/bin/python -` 运行下列脚本。只在 Python TemporaryDirectory 创建合成档案、使用 TestClient 和夹具的本地函数请求；没有连接用户档案、外网或真实 VibeInsight，临时目录自动清理。脚本本身仅保存在本报告，不额外写仓库文件。

```python
import sys, tempfile, json
from pathlib import Path
import pytest
sys.path.insert(0, 'tests')
from test_005_contracts import pair, connect, add_local
from smm_local import federation
from smm_local.upload import LocalUpload

m = pytest.MonkeyPatch()
with tempfile.TemporaryDirectory(prefix='pr30-current16-stale-hub-') as t:
    gen = pair.__wrapped__(Path(t), m)
    p = next(gen)
    try:
        add_local(p, 'synthetic-review', 'A', 'synthetic review body')
        cfg = connect(p)
        federation.choose_upload(p.local, 'none', [])
        request = federation._request
        control = LocalUpload(p.local, cfg, p.hub_id)
        remote = p.client.post('/v1/upload-policy/set', json={
            'hub_id': p.hub_id, 'device_id': cfg['device_id'],
            'expected_revision': 1, 'submission_id': 'external-all',
            'policy': {'mode': 'all', 'projects': []}}).json()
        shown = control.reconcile(request)
        before = control.row()
        injected = False
        def racing(config, route, payload=None):
            global injected
            result = request(config, route, payload)
            if route == '/upload-policy/status' and not injected:
                injected = True
                change = p.client.post('/v1/upload-policy/set', json={
                    'hub_id': p.hub_id, 'device_id': cfg['device_id'],
                    'expected_revision': result['revision'],
                    'submission_id': 'external-stop',
                    'policy': {'mode': 'none', 'projects': []}})
                assert change.status_code == 200, change.text
            return result
        try:
            control.reconcile(racing, use='hub',
                expected_hub_revision=shown['hub']['revision'],
                expected_local_generation=shown['local']['generation'])
            error = None
        except Exception as e:
            error = type(e).__name__ + ': ' + str(e)
        after = control.row()
        current = request(cfg, '/upload-policy/status', {
            'hub_id': p.hub_id, 'device_id': cfg['device_id']})
        print(json.dumps({'error': error,
            'before': {k: before[k] for k in ['desired', 'generation', 'state', 'submission_id']},
            'after': {k: after[k] for k in ['desired', 'generation', 'state', 'submission_id']},
            'hub_policy': current['policy'], 'hub_revision': current['revision']},
            ensure_ascii=False, indent=2))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
m.undo()
```

实际 stdout（随机提交标识原样保存）：

```json
{
  "error": "ControlConflict: Hub 规则已改变，请重新查看差异",
  "before": {
    "desired": {"mode": "none", "projects": []},
    "generation": 1,
    "state": "confirmed",
    "submission_id": "166d872b7bc845faac44dc94801e4d07"
  },
  "after": {
    "desired": {"mode": "all", "projects": []},
    "generation": 2,
    "state": "pending",
    "submission_id": "58f511600c4b48b9a134928c9217f578"
  },
  "hub_policy": {"mode": "none", "projects": []},
  "hub_revision": 3
}
```

stderr 只有当前环境 Starlette TestClient/httpx 弃用提示；执行退出码 0。

## 审查结论（冻结的 current16）

1. **产品：发现一项 P2（F1），需修复后复核。** 本轮未确认其他产品缺陷；没有把历史审查意见重复列成当前缺陷。
2. **交付：尚不能通过。** SPEC A12 明确要求全部必需环境/入口有证据。macOS 系统级 launchd Hub 的 E3 仍未实际执行；当前新包 Windows 双版本对账入口材料在本轮交接时仍待回收。它们是必须缺证，不是已确认产品失败。即使后来平台补验成功，F1 仍须单独解决。
3. **发现与说明：主要用户、Agent/调用方、Hub 维护者和恢复操作者均有可见操作路径。** 不要求为了本次审查再改固定 README。README 已将正式 0.4.0 与未发布候选区分，不能把本次源码能力归给公开旧包。
4. **规格未覆盖建议：本轮没有另一个已确认、需扩大本次 SPEC 的用户路径缺口。** 下述 N1 是计划文字一致性维护，行为与平台要求均不改变。

## PLAN 与当前 diff 的独立核对

已实际查看 `git diff 78973cf7ae6759332c0a320f630f5ebfb44204b6...HEAD` 的产品模块、入口、打包及测试变动，并以 intent/spec/plan 判断，没有把规模大的 evidence diff 当成功证据。

| 计划位置/方案 | 当前实现依据 | 判断 |
|---|---|---|
| 3.1 项目稳定键、全局归属、导入重放 | core.py:239-268、589-674；importers/registry.py:203-206；project_control.py:12-84 | 模块拆分已由 PLAN §10 说明。全局创建由 BEGIN IMMEDIATE 串行，人工归属覆盖留在档案；普通/全局不能合并。 |
| 本机持久规则、同锁派发/保存、按项目有界推进 | upload.py:18-98、136-160、285-311、370-421；federation.py:218-297 | 使用 guard 锁与 SQLite 写边界，派发再检查规则/身份/当前配置。历史枚举不依赖旧设备游标；25 轮上限及 next_project 实现公平轮转。 |
| Hub 单事务规则与正文门禁、恢复保护 | smm_hub/upload.py:108-161、185-214；hub.py:254-372；hub_admin.py:349-370 | 规则和接收在同一个归档数据库写事务及 guard 锁内；managed 设备旧式正文被拒，prepare-restore 阻断独立持久化。 |
| 共同范围、引用、完整候选、BM25 | federation.py:430-556；references.py:56-121；search_merge.py:10-77；hub.py:202-214、447-520 | 明确项目集合不再次扩展；全文签名后才预览压缩；可验证同源同版本先去重再按本次文档重算 BM25。新引用实际消息集有版本核对。 |
| 三入口共用和增量兼容 | cli.py:114-132、212-240；api.py:278-345；mcp_server.py:35-53；static/index.html:148-216 | Web/CLI/MCP 检索和读取进入共用 federation；MCP 未新增修改上传规则工具。旧整数读分支保留。 |
| 独立包、三平台、旧包与实际服务 | build_packages.py:38-44；_archive.py:5-8；默认 tests.yml 与可选 selective-upload-acceptance.yml | vendoring 加入纯协议和引用模块，Hub 无须安装 Local。默认三平台已存在，不需要为文件列表形式而修改它；可选任务明确普通进程，不能代 E2/E3。 |
| 归属传播、双版本对账、目标切换 | PLAN §11–12；upload.py:228-252、440-449；federation.py:254-267；tests/test_reconcile_{snapshot,boundaries,dispatch}.py | 这些后续方案均已记录，并非未说明的临时扩展。旧本机代次、条件保存、第二次 status 后切换目标已覆盖；F1 是剩余的不同窗口。 |

### N1 / 非产品阻断：计划 §5.2 的 audit 文字仍过期

`plan.md:140` 写“原独立 audit 脚本尚未实现”，并要求增加时更新本节；当前 `scripts/acceptance/selective_upload_audit.py:1-4,140-154` 已提供只读原始材料审计，§10 又记录已增加。因此维护者按 §5.2 寻找复核入口时会看到相互冲突的现状说明。§10 已解释实际调整，不属于隐瞒方案，也不影响产品操作或让平台缺证自动通过。建议把 §5.2 更新为实际命令及限定范围，保留“不能替代独立视觉/完整矩阵审查”的边界；通过条件是该节所列命令可定位现有脚本且与其 help 参数一致。此项无需改 SPEC。

## 从真实主入口回放角色与任务

### 角色一：准备接 Hub、希望决定上传范围的本机使用者

目标来自 intent：可以全部不传或按项目选择，同时保留本机归档和 Hub 查询。

| 步骤 | 用户需要知道/要做什么 | 当时可见内容与下一跳 | 核对 |
|---|---|---|---|
| 1. 找到功能和适用版本 | 多机接入是否必然上传，旧正式版是否具备新能力 | README:33-50 为“多台电脑共用档案”主路径；52-68 紧接的“选择上传项目与联合检索（005，尚未发布）”明确适用组件、新连接先只查询、四模式、停止保留、默认联合。54 链接源码开发，68 链接指南精确章节。 | 入口介绍了能力与对象；不是只有 SPEC 中有说明。 |
| 2. 取得实际组件/连接前提 | 安装哪个版本、凭证从哪里来、独立档案如何指定 | README:35-48 有 HTTPS/TLS/uv/setup/status/管理员交付凭证文件；TRIAL_GUIDE:139-145 区分候选，给构建两个 wheel、分别环境、三平台 Python/CLI 路径、顶层 --db；145 给 configure-hub 输入。 | 005 尚未发布已明说；不把重复安装 0.4.0 当升级。凭证由维护者给本机文件，未要求把秘密贴聊天。 |
| 3. 取得项目 ID，选择完整规则 | 本机 ID 与 Hub ID不能混用；空名单和新项目含义 | README:59-64 → TRIAL_GUIDE:147-160：projects、四个替代例子、重复 --project-id、only/except 空名单、all/none 不带名单，156 明确 ID 来源。CLI set help 提供同样含义。 | 本轮实际运行 upload、reconcile、assign-conversation、source --help（全部 exit 0），与文档一致。project_status 提供类型/稳定键/选择与实际允许。 |
| 4. Web 完成同样操作 | 从状态页到上传配置，并识别同名项目 | 指南145给 maintenance open；Web nav:36-38 有“配置”和“项目”，overview:43 有“设置上传范围”；settings:58 四模式、空名单、保留/补传；projects:110 显示 ID、类型、稳定身份详情、上传允许。 | 路径清晰。上传框中也有名称/ID/普通或全局；稳定身份可从“项目”查到，并非仅靠名称。 |
| 5. 判断保存是否真正生效 | 本机保存、Hub确认、在途、补齐不能混淆 | TRIAL_GUIDE:158-160 解释 state/transfer_state/计数/最近失败；Web:171-185 用同一字段展示。暂停独立；历史旧副本保留。 | 有说明与实现依据。mac/linux reconcile15 证据展示真实 pending、拒绝和 confirmed；F1 的拒绝副作用另列。 |
| 6. 处理全局/待定归属 | 缺 cwd 不自动全局，如何取得会话 ID并确认 | TRIAL_GUIDE:162-173 给 ensure-global、仅本机搜索、preview→confirm 两步及 token 来源；Web:50-51 明示仅本机会话 ID、预览标题/来源。 | 可从同指南继续完成；project_control 绑定受影响集合与规则版本，旧确认失效。A→B传播与旧副本保留已有说明。 |

### 角色二：日常搜索者、Agent 和依赖 MCP/CLI/Web 的调用方

目标来自 intent：未上传/不可上传的本机材料与 Hub 候选联合、准确知道范围、读回原文。

1. 从 README:19-23 的日常自然语言搜索进入，Agent 安装入口 README:110-122 直接链接 `skills/smm-search/SKILL.md`。Skill:8-13 先选已提供 configure_hub 的 MCP，否则 first-use；35-56 规定 scope、当前会话、预览与原文；46-50 单独说明 combined/候选重排/逐条 reference/范围回退/0.4.0 边界。
2. 项目调用值从 Skill:39 的 resolve_project 或52的 list_projects 取得；跨项目用 scope=all，显式本机44。CLI 用户从 README:98-108 → TRIAL_GUIDE:175-187 找到 search、--local、--reference 及 ID 来源。不是要求调用者自己拼合整数档案号。
3. 用户/调用方需要知道实际端点是否完成：Skill:48 要求报告 coverage/effective_projects/fallback_reason/candidate_failures/capability_limitations。实际 federation:548-556 返回端点状态、真实项目与 returned_candidates；故障路径523-542只回退所请求 A，已有效快照的部分失败保留其范围；Web:160-164 展示同样状态、范围和逐条来源。
4. 原文从命中提供的 reference 进入 MCP read_conversation、CLI read --reference 或 Web 每条原文按钮。federation:559-620 逐档案路由、Hub身份验证、不以同号本机替代；references:101-121 校验来源/消息/版本并仅取已签消息，标题从实际所选消息生成。组合引用保留 origin_references、指定区间先选来源，指南187和Skill46已有指引。
5. 兼容调用方：旧整数/Hub消息读取仍在 federation:621 之后的旧分支；MCP conversation_id 变可选并新增 reference，不移除原定位参数；冲突形式明确拒绝。Skill:50 教老结果沿旧精确 ID 读，不给老组件承诺 combined。

本轮对调用链和源码语义作直接核对；不是另一次真实三平台 MCP/浏览器运行。那些入口的实际历史证据和当前包新增对账材料在下表单独限定，不能因本段代码可达而视为所有 E1 已重跑通过。

### 角色三：识别未上传项目并配置关联的 Hub 维护者

目标来自 intent：即使 A 不传正文，也能登记最小项目身份、集中关联并理解所收范围。

1. README:35-50 是 Hub 部署入口，74 明确维护者的来源/关系指南链接；沿 TRIAL_GUIDE:66-86 得到 HTTPS/证书/凭证、实际服务状态、平台服务身份/运行账户前提。自行管理入口107-118给 --state-dir 和实际 serve-hub 命令及重启方法。
2. TRIAL_GUIDE:120-128 是关联操作局部入口：122明确“至少一次项目登记，005不要求上传正文”、hub project list、Hub ID 来源，124-128的 link/unlink/links 使用这些 Hub ID；156再次说明不能用本机 ID替代。自定义状态目录由99、116持续要求与实际服务一致。
3. 当前最小登记 federation:314-339 只发送稳定键、名称、类型、设备资料，memberships为空；Hub projects:130-140 列出项目类型、来源、owner/source_key、设备名称，维护者可区分同名设备项目。正文未许可时不会为关联枚举会话。
4. HubUpload:145-161 区分尚未迁移旧设备与 managed设备旧式正文，规则确认后旧批次/旧接口不能重新绕过。指南160/191说明其他设备和VibeInsight不被停止，旧副本仍可查。

该发现路径未确认阻断或增加显著发现难度的缺口。Mac实际系统服务访问状态目录/运行账户属于必须环境验证，不能从终端代码路径推断已成立。

### 角色四：重启/备份恢复的使用者和维护者

目标来自 intent：旧备份不能悄然恢复旧允许，能够看见两端差异并明确处理。

1. README:68 的指南链接文字直接包含“状态解释、新旧版本兼容及备份恢复”；指南189-200说明恢复前用原hub status确认实际目录，用实际 --db/--state-dir执行prepare-restore、写保护后停服务、恢复一致性备份、排除guard/lock，不能只复制运行中主文件。恢复所需文件由命令输出，不要求猜测默认路径。
2. 同节202-210给无参数差异查看、采用Hub、按两个刚显示版本重新提交本机，以及过期重新查看。CLI help给版本的JSON字段来源；Web差异页200-206持有同一显示双版本，并在提交失败后要求重新查看。Skill68给Agent相同边界，不自动对账恢复旧允许。
3. 真实维护入口 hub_admin.prepare_restore 输出数据库/配置及保留秘密文件；LocalUpload.prepare_restore 输出档案和相应Hub配置、不得恢复的保护文件、当前身份和在途数量。正常重启读取持久状态，_verify/Hub _check在不一致时阻断正文。升级失败restore调用同一prepare_restore。
4. 参数/主入口说明均足以开始和走到确认步骤；实际执行在调用中Hub修改后暴露F1，故不能把该恢复路径整体判为符合B1/A11。Hub回滚、配套状态回滚与自动升级失败的旧证据保留R1-R4具体范围，其中R4包安装为离线成功桩，不能扩称真实包下载/未来迁移已验收。

### 角色五：交付维护者/复核验收材料者

主入口为 AGENTS.md 的阶段流程及 README:143-145“规约与验收”。005 PLAN:102-168、scripts/acceptance/README.md提供隔离安装/控制器与平台运行说明；evidence/README.md开头明确草稿/未完成，并链接每轮原始材料。当前材料允许查原始result/manifest/命令/截图/清理，不必只信进度红绿灯。PLAN §5.2 的audit入口现状有N1轻微矛盾；不是隐藏必需平台，也不能据旧passed结束交付。

## SPEC 逐条核对和证据充分性

此表的“代码/共用验证支持”不等同“全部验收通过”。本轮读取 `<task-path> 的真实结束为202 passed、1 skipped、1 warning（106.14s）；没有重跑/伪造该全量输出。审查结束时产品、测试及spec/plan tracked工作区无变更，HEAD仍为7c72c92。本轮独立新增的实际执行只有上述合成反例及四个help命令。

| 条件 | 当前源码/共用测试依据 | 实际材料及本轮判断 |
|---|---|---|
| A1 默认、四模式、参数、迁移、两个版本 | upload.choose/normalize_policy；federation._controller/configure；test_upload_mode_matrix、test_upload_policy、test_reconcile_snapshot | 源码及全量回归提供支持。mac/linux-reconcile15绑定当前源码，新鲜/旧视图CLI/Web实际材料可核；Windows新包专项待回收。不能据此掩盖F1后续窗口。 |
| A2 停止、暂停、在途、并发 | upload.dispatch/_eligible；HubUpload.transaction/set；test_upload_recovery、test_upload_dispatch_fence、test_reconcile_dispatch | 本轮读最新red/green真实stdout及对应测试，目标切换第二次status窗口已绿。F1是另一个实际Hub版本竞争，故A2/B1并发拒绝要求未完全满足；Mac E3缺证。 |
| A3 稳定/全局/归属传播/最小登记 | core、project_control、_push_projects；test_project_identity_boundaries、test_upload_project_moves、test_upload_acceptance_boundaries | 文档/入口可达；assign/map/merge分别有断言。历史global-cli11和scope-run11保留实际f45；本轮不改标新包全平台通过。 |
| A4 全历史、幂等、公平、有界 | upload.catalog/candidates/receipts；federation25轮；test_upload_recovery 中失败项目/大队列/无游标测试 | 有源码/共用验证支持，历史run8与专项独立期望资料存在；本轮未重新逐字审计全部旧平台消息集合，不授予新的完整E1/E3验收。 |
| A5 隔离/旧副本/旧写拒绝 | Hub managed gate、历史归属保留；test_upload_isolation、test_vibeinsight_sync | isolation-run9针对真实隔离Hub的历史范围；VibeInsight只使用合成/既有自动回归，不需也未连接真实来源。旧Hub服务材料不能替Mac launchd格。 |
| A6 三入口共同范围/当前会话/正常N | search_archive:451-556；Hub query-scope/search；test_combined_search | 正常N、直接一层、同名映射、快照与部分失败源码吻合；历史mac/linux/windows entrances与scope专项各有版本，当前reconcile15仅CLI/Web对账而非新三入口搜索复跑。 |
| A7 BM25/去重/长文/禁止外发 | search_merge、references.issue后_display；test_combined_search、test_upload_acceptance_boundaries | 独立公式测试存在，数值参数和副本词频源码检查相符。真实外发隐私材料属于历史平台；本轮F1只验证策略副作用，未发现/未声称正文泄露。 |
| A8 精确引用/消息范围/旧读 | federation.read_archive、references.read；test_archive_references、test_scoped_read_metadata | 同号、版本、篡改、删除/变化、共享消息范围有共用断言。f45修复范围标题并提供实际scope-run11；当前Hub同模块字节可用于保留该端专项价值，不能当当前Local完整平台执行。 |
| A9 回退/部分失败/恢复 | federation:523-542；test_combined_search 中各端故障/无效范围/候选缺失 | 没见将A失败扩大为所有项目的当前源码路径；历史scope/entrances附件保留各实际版本，不把0命中当错误或所有失败当0。 |
| A10 新旧真包及迁移 | D2能力门禁、旧设备managed marker；test_upload_registration、test_upload_recovery、test_hub_standalone | d80 compatibility-run8各平台为真实旧包组合材料，产品新旧模块不同清楚记录。对账修改后的本机路径仍须受当前版本/复跑范围判断；不能只凭0.4.0包名认定新旧字节相同。 |
| A11 生命周期/恢复/双版本 | prepare_restore、guard、receipt epoch、reconcile；test_upload_recovery、test_reconcile_{snapshot,boundaries,dispatch} | **存在F1规格失败**。历史R1-R4与服务生命周期材料保留；Mac E3未执行，Windows新对账补验未完成，不能宣布全部恢复成立。 |
| A12 使用发现/交付 | 上述逐角色导航；README/指南/CLI/Web/Skill相符；source help实际未退化 | 可发现并开始使用有直接文件/帮助证据；功能测试与文档已更新分别有依据。但A12最终整体验收要求未满足，缺环境结果必须保持未完成。 |

### 当前材料与历史材料的版本边界

- `platform-debug/mac-reconcile15`、`linux-reconcile15` 的 result 均明示范围仅为“E1 actual dual-version CLI/Web reconciliation only; not full A/E acceptance”。两份manifest的candidate均为7c72c92；本轮独立计算25个Local源码文件SHA256，与candidate installed_local逐项一致；candidate清单与实际installed.local.files亦完全一致。独立安装Local未带Hub包。
- 两轮真实附件 `reconcile-result.json` 中旧本机代次：CLI exit2且stdout空、Web400；缺本机版本CLI exit2；旧Hub版本Web400；新鲜CLI confirmed/all；刷新后Web use=hub 200且双方none。请求携带实际两个版本，page_errors=[]，cleanup.failures=[]。Mac截图`stale-local-rejected.png`本轮已实际查看，红色“本机规则已改变，请重新查看对账差异”，与响应一致；不是只读result:passed。此专项不会在请求调用中改Hub，因而不能反证F1。
- 最新`red-reconcile-dispatch-v1/.../run.stdout`中第二次status后换Hub，业务断言实际200而预期400；`green-reconcile-dispatch-v1`同用例实际1passed。源码_verify_target位于同保护锁/写边界，解释此特定修复。其独立意见已存在，但本轮先看源码和断言，不以意见替代源码判断。
- 本轮把d80与f45两个公开run-index的全部产品模块清单与当前candidate作比较。d80系列Local不同文件为api.py、cli.py、references.py、upload.py、static/index.html，Hub不同为vendored references.py；f45系列Local不同文件为api.py、cli.py、upload.py、static/index.html，**Hub全模块清单与当前一致**。这支持保留f45实际Hub专项的字节证据；不支持将旧Local执行称作7c72c92新执行，也不以包版本同为0.4.0混为一谈。
- 公开目录保留windows-entrances-run10-failed、run12-failed等历史失败并另有run14成功；本轮不把它们直接判成当前产品失败，也不删除失败。系统服务验证与普通进程明确分开。

### 环境交付判定

| 环境 | 已有材料可支持的范围 | 本轮最终状态 |
|---|---|---|
| E1 macOS/Linux | 历史完整核心/专项流程；当前7c72c92真实CLI/Web双版本对账及安装清单 | 新专项已回收，但仅其明示范围；F1需修复/回归后重定影响范围。 |
| E1 Windows | 历史实际普通交互client/entrances/global/compat；当前新包对账尚在执行 | **当前必需补验材料不足，未通过该新专项**。不以Mac/Linux或源码测试代替。 |
| E2 macOS登录后启动 | 历史实际独立LaunchAgent run8/run11，身份/状态/重启材料 | 保留实际版本；不是E3系统服务。当前改动对E2的复用范围需按字节/行为说明，不擅称新执行。 |
| E3 Linux systemd、Windows LocalService | 历史真实服务run8与f45范围专项；f45 Hub字节与当前一致 | 已有实际服务专项价值；不自动代表所有当前Local调用方/恢复路径通过。 |
| E3 macOS系统级launchd | 用户延期管理员认证，尚未实际执行 | **必须缺证**。终端serve-hub、LaunchAgent和CI均不能代替；本轮无需等待才能发现/审查代码，但完整交付不能通过。 |
| E4独立serve-hub | 历史核心/范围专项；当前reconcile15亦实际启停serve-hub，但仅对账 | 保留已执行具体范围，不把当前短对账探针扩大为E4全部生命周期判据。 |
| E5独立新旧包/恢复 | 历史真实0.4.0组合、R1-R4与共用竞态；R4有明示离线安装桩 | 保留兼容/恢复的实际边界；F1说明共享对账尚有未满足行为，不授予E5完整通过。 |

本报告仅写入获准路径；未修改产品、测试、SPEC或PLAN，未发布/合并/操作日常档案。后续源码修复应另记提交与同版反例红绿灯，平台新材料再作增量复查；不得改写本次冻结源码下的实际F1结果。
