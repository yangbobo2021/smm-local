> 历史完整独立审查，固定HEAD 3c2c42c；后续F3文档ID及Hub帮助修复见[six-fixes-followup.json](six-fixes-followup.json)。原文仅替换电脑目录/VM地址；原始SHA d7f424deaea55913698e7b40ca422b56e8b23b22ea497e5ce8d16702fe20de91。完整R008必要矩阵仍开放。

# PR #43 完整独立审查：3c2c42c

审查结论：**needs_revision；当前完整 PR 不宜合并。** 六项专项修复的限定实现及现有专项通过证据可信；本轮发现一处新增的网页→CLI 重试交接信息缺口（F3-P2）。此外，整个 R008 的必要验收仍未闭合。后者是交付证据不足，不等于已经证明所有未验分支损坏。本报告没有把历史故障或缺失矩阵冒充当前产品的新失败。

## 审查身份、版本及方法

- Reviewer：独立新上下文 `/root/sixfix_pr43_review_3c2c42c`，2026-11-28（UTC 2026-11-27 17:34 左右）。实际读取本工作树 `AGENTS.md` 及当前 `changes/_templates/pr-review.prompt.md` 后执行。本轮只读产品、测试和证据，只新增本报告；未运行业务测试、未构建、未登记原生验收、未修改旧意见或发布 PR 评论。
- PR：[#43](https://github.com/yangbobo2021/smm-local/pull/43)，实际 `gh pr view` 读回 draft=true；base=`d8894d429ebe0915e377513a637b5dfc0fc7ea1a`，head=`3c2c42ccb473b438eb8436f2d277b8635b0f5530`。审查范围为 base..head 的完整 PR，六项最新增量另以 `25dec277a92850c3214ceb0a8d7ab34fec1ac9c0..3c2c42c` 核对。base 25dec27 不是六修已实现源码。
- 完整 PR diff 为874文件（含大量验收记录），六修增量150文件。对完整模块/证据清单及需求作审查，重点读实际产品主路径、解析/接收/检索与六修实现；不宣称逐字审过全部78,498行新增记录。
- 起始工作区仅三份约定旧 untracked：`tests/document_formats_lifecycle_hook.py`、`tests/test_document_formats_active_source.py`、`tests/test_document_formats_upload_restart_c1.py`。它们不属于本次可执行交付源码，也未被本轮专跑。审查过程中主 Agent 补充了公开平台索引/意见，产品64文件保持不变；以下新补充明确标为本机原件，不反写本 head 的提交事实。

| 基线文件 | SHA256（实际原字节） | HEAD Git blob |
|---|---|---|
| PR Review Prompt | `6a7cc899a5eca649dffa4cd4202dc746d7b58bfd0c5ec4e2321abecb5bfacdb4` | `8e045467d169c458464ac4becf95d53612b15d01` |
| intent.md | `12a585c4601a087f77a852ea851cad51da19bf74503ab433c755668d43a11394` | `83d0eef753d01db82c89eaa7c1896fc172110e2d` |
| spec.md | `99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986` | `00b52ddd400a2d8afb6f12499bd798b1cccb50f3` |
| plan.md | `f1237df01fbacc4402a54775917ca34d579904db9ea49389d9401dc620c7d231` | `435e4c7af1b85c74ee30ca5687da297c564662a4` |

实际重算 `sf/final-source-candidate-v2.json` 全64项（本报告以下 `sf` 指 `.acceptance-local/008/six-fixes-20261127`），同时用 `git show 3c2c42c:路径` 逐文件核 SHA：与当前产品文件及公开索引 `final_product_sha256` 全相同。原生结果的 revision 可能记录 base+工作变更，故以冻结逐文件摘要绑定实际执行代码，不把 revision 字符串当完整源码等同证明。

## 审查发现：本次增量

### F3-P2：路径详情引导 CLI 重试，却遗漏必需的文档 ID

**性质与用户影响：已确认的局部交接信息缺口。** 用户从本机 Web「文档」→来源「文件状态」→「查看处理详情与重试比较值」，确实可以看到 published/latest/retry。但新路径行仅显示路径、状态、版本，`nativeDetails` 也不显示 `asset.id`。详情把 retry 标为「创建端 CLI 使用」，而 CLI 必须传 `--document-id`。页面提供的三份 JSON 只有 CID/AID/SHA/V/P，没有该 ID。首次失败无搜索命中时尤其不能从搜索结果取得 ID。

依据：

- `src/smm_local/static/index.html:141` 新路径行构建只输出 `file.path`、`file.status`、`file.version` 后调用 `nativeDetails`；`:294–306` 详情构建不输出 `asset.id`，`:299` 明示「重试目标（创建端 CLI 使用）」。
- `src/smm_local/cli.py:140–142`、`src/smm_hub/document_cli.py:16–20` 均要求 `--document-id`。指南 `TRIAL_GUIDE.md:218–224` 给出 `reprocess --document-id <ID> ...`，要求从当前目标取得值。
- 原生 `tdd-green/green-sixfix-path-web-completion1/TC-008-path-web-details/attachments/` 的12张 `pathdetail{0,1}{ready,partial,failed}{0,1}.png` 本轮逐张实际查看：四failed全部为 published=null、V/P0，仍无文档ID；ready/partial同样没有。真实 `local-trace.zip` CRC通过，1196事件、无after error，能看到先点击主导航 `nav [data-tab=documents]`、来源 `data-doc-files` 后逐项展开详情。不是仅凭静态HTML推断。
- `tests/test_document_formats_path_web_details.py:63–96` 已从独立DB取得 `doc['id']`，但网页断言 `:124–143` 只比较三JSON和coverage，不要求可见ID。这解释该TC通过为何未发现缺口；其通过仍有效证明自己声明的字段，不是伪造绿灯。

**已有可用路径：** README→008指南→`documents files --source-id <来源ID>`（指南`:193`）会返回该路径项的 `id`；再与页面CID/AID/V/P合用可完成重试。故不判整个重试功能不可用，不认定保存字节丢失，也不把 API 内已有ID说成后端缺字段。已知CLI用户能绕路，网页直接转CLI的用户需要额外查询。

**适度建议和通过条件：** 在该路径资料行/处理详情显示可复制的当前文档ID并标明对应 `--document-id`，或提供明确命令说明如何由当前来源/路径取得它；继续保留原CID/AID/V/P。真实12目标中逐项以独立DB的ID核可见值，failed无命中时也能完整填写当前重试命令。此建议补齐现有入口所需信息，不新增网页重试按钮或管理能力。它与B4/B5/A11目标相关；不将B4允许从files取得值的替代路径解释为要求所有JSON都必须新增同一字段。

本发现已及时通知主 Agent；其拟修复不属于本审查 head，本报告不预审后续实现。

### 其余六修增量

未发现另一个可以由当前原件和真实触发确认的新增实质产品缺陷。该结论限本次代码/证据审查，不能外推为完整并发、服务、PDF安全及所有平台均正确。

## 审查发现：整个 R008 尚未闭合

### R008-P1：必要平台及交付证据不足，不能作完整需求通过或合并依据

SPEC A12（`:192`）、C1（`:196`）、E1（`:200–224`）、H及X明确必须三平台最低Python业务、E三格、H三格、X六方向和共享完整边界。PLAN`:210–223`要求相应原件可读/回收/独审，缺格不能判整个008通过。

目前 `evidence/pending-verification.json.remaining_required`、`active_source_lifecycle_gap`、`restart_and_audit_retained`、`resumed_test_repairs` 及当前 PR 正文均保留：完整PDF安全/资源、完整生命周期/在途来源取消、C1重启、旧Windows共享argv观察器、最低Python三OS安装、E/H/X、完整原件及清理/需求级独审。六修只关闭相应分域，未产生这些完整格的证据。实际用户影响是尚不能向规定平台/身份用户作完整交付承诺；这是验收阻塞，不能据此断言每项实现已损坏。

现有Mac/Python3.14基础包、源码前景、Windows管理员、Ubuntu22.04普通uid的补充都保留其真实价值，分别不能替代Python3.11三OS、Windows标准token/SCM、Ubuntu24.04/user-systemd或macOS系统launchd。建议按原确认矩阵补齐；如维护者希望改变交付边界，应先重新确认SPEC，不能由本报告或局部绿灯默默豁免。

### R008-P2：Hub CLI 局部帮助不足，独立从 CLI 开始时需转查指南

真实只读执行（`.venv/bin/python -B -m smm_hub.cli ... --help`，均exit0）表明：`hub documents --help` 列出processing-status/configure/reprocess，却不介绍支持.docx/.xlsx/.pdf、[documents]依赖、创建端处理或指南入口；`refresh --help` 只有 `--source-id SOURCE_ID`，不解释来源ID取得方式；`reprocess --help` 列5个必填参数，均无取值说明。源码对应 `src/smm_hub/document_cli.py:11–30`。Local父层及refresh已有较完整描述（`src/smm_local/cli.py:137,157`），不能以Local帮助替Hub。

这是SPEC B8`:119`「各层CLI帮助」与PLAN`:83`的可发现性欠完整，主要增加Hub维护者查找成本。README`:61–67`有明确008能力和指南链接，指南`:168–180,188–224`给实际state-dir、命令前缀、ID/比较值、OCR准备与执行责任，**整体路径可以从README到达并完成**，不判Hub业务被阻断。建议Hub documents/refresh/reprocess的局部帮助补支持面及必要取值来源/指南提示；无需复制整份指南。

可复核原始输出（本轮未单独写文件，直接在本报告保留）：

```text
$ .venv/bin/python -B -m smm_hub.cli hub documents --help
usage: smm-hub hub documents [-h]
                             {processing-status,processing-configure,reprocess,add,set,sources,files,refresh,remove,search,read,recovery-status,recover} ...

positional arguments:
  {processing-status,processing-configure,reprocess,add,set,sources,files,refresh,remove,search,read,recovery-status,recover}
    processing-status   查看创建端格式/接收能力、OCR配置revision与最近探测身份
    processing-configure
                        所在创建端持久配置本地OCR；不自动重处理已有资料
    reprocess           只重处理Hub自有且仍获授权的保存原件；设备投影只读
    add                 保存配置为pending；需明确refresh
    set                 保存配置为pending；需明确refresh
    sources             列出Hub自有与设备来源及其创建端
    recovery-status     查看文档保护冲突、影响及不透明state
    recover             重建文档epoch，使全部旧引用失效；需明确重新采集/选择

options:
  -h, --help            show this help message and exit

$ .venv/bin/python -B -m smm_hub.cli hub documents refresh --help
usage: smm-hub hub documents refresh [-h] [--source-id SOURCE_ID]

options:
  -h, --help            show this help message and exit
  --source-id SOURCE_ID

$ .venv/bin/python -B -m smm_hub.cli hub documents reprocess --help
usage: smm-hub hub documents reprocess [-h] --document-id DOCUMENT_ID
                                       --capture-id CAPTURE_ID
                                       --expected-attempt-id EXPECTED_ATTEMPT_ID
                                       --expected-version EXPECTED_VERSION
                                       --expected-processing-version EXPECTED_PROCESSING_VERSION

options:
  -h, --help            show this help message and exit
  --document-id DOCUMENT_ID
  --capture-id CAPTURE_ID
  --expected-attempt-id EXPECTED_ATTEMPT_ID
  --expected-version EXPECTED_VERSION
  --expected-processing-version EXPECTED_PROCESSING_VERSION
```

## PLAN 一致性与实施偏差

完整PR的产品位置与PLAN`:67–100`数据流可对应：`document_formats/`为创建端解析，`document_processing/worker/supervisor/windows`承担受监督任务，`document_snapshots/results/transfers`承担保存/候选/成套结果，Hub `processed_documents`是纯接收校验/索引分支，CLI/API/两端HTML/MCP接入既有文档入口。独立Hub包包含vendor共享模块；原件和结果摘要、P及资格进入读引用和去重。未见擅自引入外部模型/Office执行、另建格式项目类型或把接收端重解析作为补救的变更。

六修PLAN`:344–367`已经说明：内核退出证明、Windows创建时JOB_LIST、路径CAS终态、路径保存详情、Hub同state lease/jobs交接、每DB协调器、稳定档案/DB用途证明及复制身份保守GC；新增模块和验证方法有相应记录。未发现未说明的模块/方案偏差。

方法差异均须保留限定：

- F4/F5最后native重放被SC1整体设计版迁移在业务执行前阻塞。当前5主实例+24回归是补充执行，不能写成那次native green。已读 `integration-final-v2/design-comparison.json` 及意见：三个case中的交接/队列自然语言对象v2/v3相同，变化的是path-finalization；这使补充证据可用于功能复核，但不自动生成原生状态。
- 容量长批次拆分、准备进度握手、Windows就绪JSON/argv、退出观察器是已说明的测试方法调整；产品300秒/1GiB/256MiB与故障判据未据此提高。旧超时、失败、准备故障原样保留。
- SPEC早期禁止ESXi与PLAN后述允许测试VM之间有明确维护者后续授权记录（`:346`），属环境授权更新，不是擅改平台通过条件。Ubuntu22.04不替24.04、Windows管理员不替标准账户。
- 最终普通CI在审查时仍执行；PLAN要求的最终C1/E/H/X/最低Python与原件闭环是未完成事项，不是以文档增加一条「已调整」即可消除的偏差。

## Intent 用户角色与主入口回放

Intent`:11–17`的角色是本机资料使用者、Hub维护者/资料使用者、读取出处的Agent及后续调用方。维护/验收调用方也受新包、运行身份、证据流程影响。以下将可见说明、功能证据和可发现性分别核对；没有从内部直接路径跳过主入口。

| 角色/目标 | 主入口→当时可见说明→前置→操作→确认 | 结论及边界 |
|---|---|---|
| 本机用户纳入Word/Excel/PDF | README`:61–67`明确008开发中、0.4.0/首次安装器不含、新格式和创建端责任→文字为「008使用指南」的链接→TRIAL_GUIDE`:153–177`同构建独立wheel/[documents]、Python路径、私有OCR材料及revision/check→`:188–197`建项目、add/refresh/files/search/read/original→`:200–224`文本/表格/原件及failed retry说明 | README路径清晰可达，输入含义/来源总体足够；不是要用户猜内部路径。各功能有分域实测；E完整安装业务仍缺。F3网页转CLI的document ID另见发现。 |
| 本机浏览器用户上传/查看状态 | README`:35,54,65`指Web「文档」及状态→Local HTML主导航「文档」→HTML`:58–65`显示格式、端责任、项目创建/选择、选择器/拖放、刷新/文件状态、同步选择/检索→处理详情、读取原文/表格/原件 | 本轮真实trace从nav点击到来源文件状态再到详情；12画面证实ready/partial/failed可见。partial行先有旧通用membership ready，再有明确PDF partial标签及coverage；不是完全掩盖partial，但可考虑给两个状态加名称减少混淆，此为非阻断改善建议。本TC不证明整套选择/拖入及网页生命周期全部通过。 |
| Hub维护者创建/处理资料 | README`:55,61–67,71–86`给HTTPS/凭据及指南→指南`:102–116`解释Hub机器路径与远程浏览器字节、state-dir/来源ID→008`:168–180`本端依赖/OCR/服务身份与活跃同state交接→`:188–224`换Hub前缀及自己的项目ID→files/library与搜索/原件确认 | 替代路径完整；Hub CLI局部帮助不足另列。F4动态证明同state服务处理、异state/停服务前景差别；该「服务」为实际前景HTTP生命周期，不冒称H的原生OS服务。 |
| Hub浏览器资料使用者 | README`:55`直接Hub HTTPS根地址/选hub-token→Hub HTML`:5–12`先给凭据来源/内存认证说明，认证后项目创建、支持格式/20MiB、只在Hub管理及投影只读、选择/拖放和检索→read/原件组件 | 身份/字节来源及管理归属有可见说明。源码/指南可达，不以此静态存在替代最终三OS浏览器业务或H账户ACL证明。 |
| Agent读取依据 | README`:146–156`链接同仓库Skill/MCP；README`:35`列三文档工具→`skills/smm-search/SKILL.md`「Search captured documents」先核工具能力、0.4.0边界→list_document_sources/list_projects→search exact reference→read text/table/original-info，下载转CLI/API | Skill实际说明格式、创建端/接收职责、partial、禁止自动refresh/升级、P及摘要、只读权限；未把对话查询当文档。CLI/stdio分域原件有实测；全部E三入口/远端全格式重启仍缺，不据工具名存在认通过。 |
| 同步本机文档的用户/接收调用方 | README`:56,63`默认关闭/原件+结果→指南`:118–144,226`取得KEY/HID/generation，明确sync-policy/sync、覆盖及共同范围→源码接收分支`processed_documents.py:47–123`校完整包并安装已有结果→搜索/text/table/original确认 | 默认关闭、未索引不等于未上传、接收无需处理依赖均有说明。direct-index及remote-query-routing等限定证据存在；无处理依赖三OS接收/六方向真实HTTPS仍不能确认。 |
| 开发/验收维护者 | README`:67,168,181`分别链接SPEC/PLAN/证据、构建、AGENTS→`scripts/acceptance/README.md:3–32`区分普通CI/组件/实际包、合成隔离及OCR材料清单→具体命令与环境变量/证据回收→原件/独审/逐A判定 | 当前入口明确尚无单命令完成全矩阵，不以job success代验收。新的跨平台探针约定`:314–322`说明身份/退出/argv/就绪/准备与业务时间；最终完整回收/清理仍待验。 |

以上可见入口没有发现需要把内部实现路径当作先验知识才能进入008指南的问题。局部缺口仅按实际影响报告；本轮没有借指南完备推定所有操作已经在必要环境成功。

## 六修代码与原始证据核验

逐实际文件SHA读取全部8组native green结果及其**20,460个artifact**，无缺失/摘要不符；每组green与对应red的完整cases/test_bindings逐结构相同，red均为red_observed。实际读run.stdout，核exit；另外读独立意见，未以摘要代替原件。F3额外逐张看全部12PNG、打开trace。未将历史TDD里与最终不同的 `document_snapshots.py` 抹去。

| 修复 | 代码判断 | 当前可以支持的专项结论 |
|---|---|---|
| F1 看守健康 | `document_supervisor.py:174–234`退出确证；`:275–283`看守意外exit0/非零而worker仍活时失败；`:303–327`停止树/清负载和lease。存活AccessDenied未改成已退出。Windows独立模块原子JOB_LIST加入，内核创建时间及kill-on-close限定 | `green-sixfix-health-{local,hub}-final-preparation2`两端各12目标，main各1过，16/15控制回归；最终64产品一致。普通/全局×none/旧ready/旧partial×denial/exit0，真实树/负载/槽位、旧快照、同CID新AID和后续任务；非完整资源矩阵。 |
| F2 路径终态 | `documents.py:436–506`冻结目标核对/发布拒绝转失败；`document_snapshots.py:379–393`document/CID/latestAID/config CAS，旧尝试不能改新目标。复用原发布快照与新结果分开 | Local/Hub native各12目标（main各1，回归2/2）通过，覆盖初始/旧ready/旧partial及连续重叠来源、保存字节重试、旧ref拒绝和过期请求全表不变；native早于复制保护。最终Ubuntu两端同64源码各12另实测独审，补版本边界。 |
| F3 路径Web详情 | HTML`:141,294–306`复用保存published/latest/retry，partial只读保存coverage，textContent安全呈现 | native main1+3回归，12画面/真实trace与保存raw/result/DB独立预期。无回源/解析的只读探针正负控及原字节/mtime不变。此TC结论不含document ID可见性，新缺口已列。 |
| F4 Hub CLI交接 | `document_cli.py:57–60`仅refresh/reprocess接入；`document_execution.py`同DB lease+持久jobs、活跃服务诊断，不静默前景降级；lifespan启动协调 | 早期native绿灯有其精确版本；最终 `integration-final-v2`实际29过=交接1+队列4+回归24，同最终源码；六初始+六删源reprocess任务归真实服务父身份，CLI0；异state/停服务前景为正控。native新重放因设计门blocked，无业务执行。 |
| F5 两DB队列 | `managed_document_uploads.py:23–32,198–227`按规范化DB路径协调；父目录OS槽争用保留本DB等候者，同DB重复kick合并 | 最终集成四参数holder0/1×processing/empty_handoff，两个DB各两资料，仅一次commit启动仍全部完成；独立真值、CID/AID、项目命中及原件核对。无靠重启/人工kick补齐，不认整个SC1。 |
| F6 最后用途/遗留pin | snapshots稳定身份+DB registry，只读其他合法库用途；OS pin lease和精确task cleanup证明，先retired再删；未知/歧义保守计费，发布ledger保护；复制同archive_id前置阻止canonical GC | 最终native GC14过1Win skip+7回归，当前64源码。正常共享最后用途、真实POSIX控制端死亡仍活树保护、普通/任务遗留pin、复制库已登记/未登记首次准入+第三库、未知/路径重用/拒删计费。Windows最终29过2POSIX skip及Ubuntu最终30过1Win skip补OS分支；不认全SC10/完整256MiB矩阵。 |

`integration-final-v2`实际result SHA=`ab6878c0a84eb8caad2190a1ee07613315d0da5bedcccfde910065335f746d20`；JUnit29项零fail/error/skip、stdout29过。独立补充意见SHA=`4aa671191089a53d018676695bc8c664572a46355098174330feac0c2eb400a0`。最后native阻塞与补充不是同一执行，旧失败均保留。

## 最终平台补充、包与CI

本轮逐六包独立核传输ZIP摘要/长度、ZIP CRC、manifest全成员长度/SHA及与verified解包字节一致，实际解析全部JUnit与gzip JSON；逐236个source.tar文件核摘要，64产品全部与3c2c42c一致。六包result均exit0、timed_out=false、cleanup_errors=[]，但不把它扩成全环境清理证明。

| 本机原件目录（sf/） | 实际JUnit | ZIP SHA256 | 身份/范围 |
|---|---:|---|---|
| windows-recovery-final-v2 | 29过/2 POSIX skip | `16ffc38a6e352e56fc9259fecddc77f7689aa5fe1f9eb54b5caea7f41f372aea` | Windows管理员、源码前景；含实际Job归属/控制端死亡及复制保护、控制。不是标准用户或SCM。 |
| ubuntu-health-hub-final-v2 | 6过/0skip | `ec3c94ed05f19565d4588b2e5e7e159acc351e0e89eb10ff4179a2b0f56416b7` | Ubuntu22.04 uid1000；1个完整12目标健康case+5准备控制。 |
| ubuntu-path-local-final-v2 | 1过 | `ac4e305bbfaeaec896d40c0c378c7f5f56702dea2e90ebbca0d478feb828a2f2` | 同环境Local完整12路径目标。 |
| ubuntu-path-hub-final-v2 | 1过 | `ad356a210933764b3b34de7f17e005aa8018ad6a8bdac5e43e6ed9b841744e19` | 同环境Hub完整12路径目标。 |
| ubuntu-recovery-final-v2 | 30过/1 Win skip | `75b57a2609dcf169ac7810fde0ef9b7d64069b0288548a343ff85b2190b3fa9b` | 同环境恢复/复制保护及观察器控制；真实POSIX孤儿树。审查开始时公开索引仍pending，现已读新本机原件及独审，不据旧pending抹去新结果。 |
| ubuntu-health-local-final-v2 | 6过/0skip | `0b61568148fc535f3c221cfe0c0a5a42a23faf8d088004cb324a21837a2c0197` | 同环境Local完整12目标+5控制；本机新增意见已读，不推为Ubuntu24.04/user-systemd。 |

六manifest分别515、6197、3441、3551、518、6868项均核对无误。最后两批新独立意见原SHA分别 `6fe2d85a6c081ff168823a2aa253dd27b67c2250213833da23fd25959e8756db`、`00c8cdd33ea323d3ecb7df868bad2b5c8f043335f849ce8a4d19bf64ffe8e6e3`。旧Ubuntu705.87秒13过1失败是注入前gate耗尽，旧结论保留；新版5项准备控制不改产品预算/故障8秒观察及5秒恢复断言，不能反向改判旧批。

两wheel实际原件 `packages-final-v2/wheels/`：Local SHA=`13ac9776208a88991868b8b43336f5e430e9a04668db6e979e747c70faac3b84`，Hub SHA=`bbdee1e90e0f19db522df48f11702a5f4035fbf48183bbd762a38b29be210bb3`。本轮独立核ZIP CRC、完整RECORD各摘要/长度、47+50=97映射的wheel成员SHA，18命令stdout/stderr摘要及exit0均吻合；实际输出含独立文本项目纳入/搜索/读回与MCP工具发现。安装部分另读独立意见和真实模块stdout，范围为Mac/Python3.14基础包，不替三平台3.11/三格式OCR/E/H/X。

审查时再次 `gh pr view`：本head的两轮Test packages运行 `46041866120`、`46041856740`，每轮Ubuntu24.04/macOS15/Windows2022均IN_PROGRESS、conclusion空；**没有当前普通CI通过结论**。旧 `1abe6cd` 等官方回收的Mac GC/Windows共享argv失败仍各属原提交；当前专项通过既不改其原结果，也不能预判新CI。当前CI完成后仍须回收官方ZIP/digest/CRC/完整JUnit，普通CI也不代业务矩阵。

## SPEC A1–A12 验收清单结论

下表“局部证据”指实际已有分域；它不表示本轮重做了所有历史测试，也不表示已升级为本head完整需求通过。历史证据精确版本以各JSON/native bindings为准。

| 条件 | 功能/文档/可发现性依据 | 当前判定及尚缺 |
|---|---|---|
| A1 入口/创建端 | native-management、managed-upload、publication-state、配置终态与本轮交接/队列/详情；README→指南及两端页面显示归属 | 分域通过；本次F3-P2及Hub帮助缺口；完整E/H入口与投影/旧页边界组合未全证。 |
| A2 DOCX | Word解析正文/表格/嵌套/页眉脚注与定位实现；已有Local/Hub CLI、真实stdio和管理专项，六修还实际处理DOCX | 分域证据；不能由六修的DOCX样本认全部支持细分及每E/H格。 |
| A3 XLSX | spreadsheet解析多表/隐藏/公式缓存/类型/日期/合并实现及专用测试；本轮队列/交接含XLSX独立表真值 | 分域证据；全细分+三OS入口/最低Python/H持久路径仍不足。 |
| A4 PDF原生/表格 | mixed-pdf-development（两份三页/六表/28格）、原生/表格相关测试，六修路径/健康实际PDF；支持范围指南可达 | 分域通过不等完整布局负例/安全/全部E/H；不从源码存在推全部PDF正确。 |
| A5 真实OCR | 固定本地Tesseract/语言资料、独立真值与混合/OCR开发原件；指南明确chi_sim/eng质量边界/识别误差 | 已有Mac子域；各实际OS/E/H服务质量、缺依赖恢复/完整错误条件未全证。runtime安装清单不能替业务CER。 |
| A6 同步直接索引 | direct-index及接收纯校验路径；指南明默认关闭、创建端负责、原件+结果及接收无需组件 | 分域证据；X六方向实际无处理依赖接收/HTTPS、各E/H规定零调用及源端离线全套仍缺。 |
| A7 成套并发 | 分块/回执、reservation、update-replay、原件结果绑定及当前CAS；单轮失败不抹去历史 | 全C1故障/中断/晚回执/恢复与三OS共同完整回归未闭合；不能把局部29过或CI当全成套矩阵。 |
| A8 生命周期 | cached-inflight、replace-retry、源授权修复、config-finalization、本轮路径/健康/GC；详情与显式retry说明 | 分域通过；在途来源取消保留、C1重启设计/实现问题、完整ready/partial/恢复/撤回组合未闭合。旧三untracked不能算已交付补完。 |
| A9 查询/原件 | cli/mcp/hub-cli views、remote-query-routing、processing-version isolation、merged-column-header、表格后半命中专项；指南text/table/original操作可达 | 分域证据；web-reader原记录仍测试repair/无完整通过，E/X/H全部入口/旧ref重启/全资料仍不足；不因新增路径详情截图认网页全文阅读用例通过。 |
| A10 有界/隔离 | B9任务树/内核、PDF guard、staging、reservations、temporary sampler及本轮健康/最后用途原件 | 本轮关键监督和GC分域可信；完整PDF解码/像素/恶意输入/数值等于与+1/生命周期/所有用途矩阵及E/H异常恢复仍不足。 |
| A11 兼容/发现 | README/指南/Skill、restore-set/legacy专项、双包97映射18命令及基础业务 | 文档入口总体可达；F3-P2与Hub帮助建议待处理。最终三OS CI、三OS最低Python当前包完整最小业务仍未齐；Mac3.14不能代3.11。 |
| A12 平台/证据 | 本轮六批原件/旧专项及新上下文独审可读，身份/version边界明确 | **未通过完整R008**：E三格、H三格、X六方向、C1和全部原件/清理/需求级独审仍必需；不是规格豁免。 |

## 合并判断

本head能支持「六项修复已有相应分域通过」；F3新路径详情尚需补齐向CLI交接的必需ID信息，Hub帮助可作局部完善。完整PR仍因A12及关联A7/A8/A10/A11必要交付条件未完成而 **needs_revision，不建议合并**。继续保持草稿并按现有待验清单工作是与实际证据一致的状态。维护者后续决定范围或例外前，应保留未完成项、历史失败/超时、实际身份/版本与新专项结果，不能将此报告的审查完成等同R008验收完成。
