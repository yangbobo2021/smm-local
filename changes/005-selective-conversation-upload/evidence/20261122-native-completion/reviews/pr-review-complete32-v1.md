# PR #30 独立完整审查（complete32 v1）

审查结论：在本次检查范围内，未发现需要修改产品、测试或验收控制器的新增可行动问题。已读当前完整改动清单，并对策略/正文事务、对账、项目预览、范围快照、联合排序和引用路由的实现作独立源码核对。审查收尾时另实际读回新的 R005 独立需求意见及原生 delivery-judge 收据：status=judged、judgment.status=passed；本PR审查与该需求级判断相互独立，维护者仍决定是否合并。

## 审查基线与方法

- 首先实际读取任务工作树 `AGENTS.md` 和 `changes/_templates/pr-review.prompt.md`，然后读取已确认 Intent、当前 SPEC、完整 PLAN（含第11、12及12.1–12.5节调整）。未使用历史 PR 意见代替本次判断。
- diff 基线 `78973cf7ae6759332c0a320f630f5ebfb44204b6`，被审 HEAD `5f14cde73fd8135c97718067822e2e6e7025861c`；包括当前未跟踪原生记录和 `evidence/20261122-native-completion/` 导出。本意见仅写入自己的新文件，没有修改产品、测试、旧证据和旧审查。
- 实际执行 `git diff --exit-code ba8c6d5 HEAD -- src`，无差异；逐个计算当前 `current-product-bytes.json` 所列全部 src 文件摘要，全部相符。不能仅由包的 0.4.0 字符串判断候选身份。
- 独立运行 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_complete_scene_boundaries.py`：17 passed，2.11秒；只有既有 Starlette TestClient 弃用提示。未重跑长平台任务，也未启动真实服务、升级日常 SMM 或访问真实 VibeInsight。

## PLAN 对照

实际模块与 PLAN 第2节职责相符：core/registry 保存稳定键和人工归属；LocalUpload 与 federation 分离控制/正文、确认/扫描；HubUpload 在保护锁和同一 SQLite 事务内检查规则与归档；纯协议/引用模块由构建脚本纳入 Hub 独立命名空间；CLI/API/MCP/Web 接入共同搜索读取；服务 label 和 Windows 环境继承仅为实际运行适配。浏览器依赖处于 acceptance extra，未进入生产依赖。没有发现未说明的模块、方案或验证方法偏差。

PLAN 对 G 唯一性的实际 BEGIN IMMEDIATE 查重插入、签名集合冻结关联范围、远端 CAS 成功后本机条件保存、当前源码共用回归、历史原件适用性核验及 Windows 超过300秒转外部长轮人工记录，都有明确修订。实际代码分别可见 `core.py:604`、`hub.py` 的 query-scope/search、`upload.py:235` 及新增控制器。规格里没有承诺的数据库唯一索引或独立关联版本字段，不再被计划误写为已实施。AGENTS.md/CLAUDE.md 没有本次差异。

## 从真实主入口回放角色

| 角色与结果 | 当时可见入口、下一步与所需输入 | 结果确认与判断 |
|---|---|---|
| 初次连接/已有Hub用户，限制上传并保留查询 | README“多台电脑共用档案”给出HTTPS、凭证文件、设备名称；紧接着 `README.md:52` 标明005未发布、正式0.4.0不具备能力，指向源码环境及 `TRIAL_GUIDE.md:139`。指南给出独立Local/Hub wheel环境及各OS实际CLI路径、`--db`位置，再于143节给出configure-hub、maintenance open、projects及四个互斥设置例子。 | 项目ID明确来自本机projects，模式空名单、禁止名单组合、保存替换、来源范围、停止保留及重开补齐都有说明；158节解释规则与传输两个状态。Web导入进度的“设置上传范围”可到配置；配置实际有四模式/项目复选/差异按钮。可发现、开始并确认结果，没有只能在SPEC找到的必要值。 |
| Agent/CLI/Web检索调用方，查未上传内容并准确读回 | README联合查询说明及指南175节连到search/read；README Agent接入提供Skill安装路径，Skill search步骤要求先查状态、取得项目、使用每条reference。默认联合、显式本机、共同一层范围、失败/部分覆盖和旧版参数分别有说明。 | 搜索输出逐条引用读取，不把顶层combined或Hub整数ID拼到本机命中。实际CLI/MCP/Web原始结果包含local-A/local-A-new、remote-B和vibe-V；共同集合A/B/V排除C/D。三OS零命中原始响应和截图明确“两端已检索”，不同于unavailable/not_requested。 |
| 需要明确全局归属的用户 | 指南162节和Web项目页提示从仅本机结果取得会话ID，由projects/ensure-global取得目标ID；先预览、核对来源/标题/允许变化，再使用confirmation。 | Web实际包含“创建或取得全局项目”“预览归属变更”与确认；代码签名绑定操作、目标、受影响归属和规则。缺cwd不冒充全局，普通与全局不混并；旧副本保留和B禁止时无新归属/指纹均解释。 |
| Hub维护者，关联未上传项目 | README70节“由汇总端维护者配置”及明确链接进入指南120节；说明最小登记不要求正文、先list取得Hub ID，随后links/link/unlink。包部署/HTTPS/凭证前提由同一指南66节提供；自行管理入口在107节。 | 本机ID与Hub ID清楚区分。原始Hub项目清单包含设备、来源与稳定身份，系统服务运行期间的范围响应和原文可复核。该路径不依赖先允许正文。 |
| 恢复操作者/维护者，恢复后继续按当前限制同步 | 同一005指南189节先由实际hub status确认database父目录及原服务状态目录，再prepare-restore、停服务、一致性备份、保留guard/lock、重启和reconcile。两个local重提版本明确取自刚查看的hub.revision/local.generation；CLI帮助与Web按钮绑定一致。 | 有恢复文件清单、状态目录取得方式、拒绝过期、采用Hub和重提本机的区别，以及任意回滚保护标记不受支持的边界；Local/Hub和serve-hub入口说明一致。没有让操作者猜版本或恢复默认目录。 |

以上是对当前可见文档、源代码及已保存真实入口输出的回放。本次未重新进行三平台交互操作。已直接打开 Mac/Linux 的 successful-empty-all PNG、Windows successful-empty-project PNG，文字和覆盖状态与各自原始JSON一致。

## SPEC 与证据独立核对

| 条件 | 实际核对的实现、断言与原件 | 判断 |
|---|---|---|
| A1/A2 | `LocalUpload._save/sync_policy/reconcile/dispatch`、Hub CAS/transaction；四模式、非法输入、双版本输入和远端竞争测试；三OS主流程与reconcile21实际旧视图拒绝/刷新成功原件。 | 本机保存、Hub确认、在途和传输分开；CAS拒绝不先覆盖本机规则；不以状态字符串代替前后规则与请求。新增逐模式暂停/禁用来源测试每次保存后直接核对设置、消息和正常正文派发。 |
| A3/A5 | project_control快照、Hub消息级归属/known核对、项目移动回归与实际隔离原件。 | assign/map/merge的目标改变和现有归属改变各自六参数负例，不改变规则代次也须拒旧确认；持久快照拒绝前后相等。B仍禁止时直接读六个旧A会话/单消息引用且物理正文行不变；没有先允许B掩盖边界。 |
| A4 | 有界项目轮转、整批确认、未知回执与新增持续失败测试；实际backfill、重复同步与完整消息清单。 | 三轮A持续失败中每轮新增B都推进，A仍待确认。整批失败/部分无效回执/混批顺序由专门回归覆盖；候选未确认不因旧游标跳过。 |
| A6/A7 | federation共同快照/精确本机集合、search_merge BM25、required_snapshot测试、原始联合结果/完整正文和各入口引用。 | scope-return及hub-results-return两个窗口实际改关联，本次旧范围/下一次新范围分别断言；独立多词公式使用df(amber)=1、df(blue)=3并重复查询词，非调用被测排序器生成预期。原始平台候选集合、长消息和禁止载荷检查可与独立清单复核。 |
| A8 | references完整签名、消息版本与档案路由；Hub范围标题修复；删除首/后消息、重复position、切Hub、冲突参数测试及scope11/15原件。 | 不以整数同号替代档案。新增真实新旧stdio MCP专项用旧参数对同整数ID分别读local-A与vibe-V，原文不同且正确；不是三次调用同一Python函数冒充入口。 |
| A9 | 共用empty-coverage与三OS实际成功空查询专项。 | 共用测试区分complete/unavailable/not_requested。Mac/Linux原生execute及Windows新外部长轮各有project/all × CLI/真实MCP/Web六响应、正控与画面；均为空且local/hub complete。Windows process真实11:06:33Z至11:11:43Z、exit0，worker11220 exit0，普通交互elevated_admin=false、cleanup空；旧超300秒timeout没有改判passed。 |
| A10 | 实际旧包摘要、旧非空档案专项before/after-upgrade、三OS兼容原件和现有兼容控制器。 | 专项真实0.4.0生成A/D本机/Hub关系和cursor=2，新包接管后保持项目稳定键、名称、关联、游标和旧原文，重复同步无新增；不以新包造旧库。完整组合仍由三OS原兼容证据承担，新专项只补共享迁移遗漏。 |
| A11 | prepare-restore/自动恢复入口、控制epoch、confirmed-loss专项及原R1–R4原件。 | 备份后实际确认近期消息及新none限制，再恢复缺二者的旧Hub库；先conflict、none保留且不补近期消息，显式只允许A后精确补回原文并归零，旧引用仍可读。R4安装是离线成功桩，当前索引如实限定，不扩大成真实发布下载。 |
| A12/E1–E5 | 当前文档路径与真实主流程、登录服务、三个Hub系统服务、serve-hub、兼容恢复原件；52自动+13人工原生链及当前回归/CI。 | E1普通Windows与E3提升的维护端明确区分；系统级Mac Hub原件有UID501/PPID1与两次PID，Linux为实际systemd用户服务，Windows Hub owner为NT AUTHORITY/LOCAL SERVICE；独立serve-hub有实际停启事件。场景完成不自动代替R005最终独立需求判断；审查收尾时已另读回真实R005 judged/passed收据。 |

新增六个测试函数按4+2+6+3+1+1展开为17个实例，与本次独立运行相符。新增旧关系、旧MCP和已确认消息丢失专项分别由 `selective_upload_completion.py:38/79/99` 执行；E5只要求至少一个实际平台，共享迁移没有平台分支，因此一平台补专项与保留三系统既有组合相符。空结果仍按E1要求三OS分别实测，没有用E5缩减。

## 版本适用性、完整性和发现

d80→f45实际仅改references标题，f45→7c改Local API/CLI/Web/对账，7c→ba8仅改Local upload；Hub完整模块字节相同。已实际核对git模块差异与公开两次package-comparison的范围。较早E1/E3/E4主流程可以证明未改动调用路径；后续scope11/15、reconcile21实际安装包与当前远端CAS/共享边界回归补足改变的行为。没有把旧平台事件改时间或标为ba8执行。

当前 `ci-source-5f14.json` 绑定HEAD5f14，三job success；日志实际Mac/Linux 251 passed+1 skipped、Windows252 passed，并构建两个独立wheel。完整源码回归保存同样251+1。以上引用CI原件，不将本次17项独立复跑写成再次完整回归。

本次确实观察到两项导出/索引缺口，已在审查过程中向根代理报告，最终读回均已修复：

1. 新README的SC12链接最初指向不存在的manual-complete32-sc12/record.json，影响审查者从索引复核A12；现该收据及公开原件已存在，当前README/TRIAL_GUIDE/新证据README文件链接缺失数为0。
2. 旧evidence/README开头最初仍以原生blocked和234回归作“最新进展”，会使维护者误判当前交付状态；现开头已链接新索引，写明65TC、5f14/ba8和实际R005 passed，并把旧CAS blocked明确作为历史保留，当前不再有该冲突。

最后逐文件复算新导出SHA256SUMS，全相符；provenance每条original_sha256与export_sha256分别对应实际原件及公开副本，全相符；current-product-bytes所有src摘要相符。没有发现新的必需原件断链或可行动产品/文档问题。未对每一张历史PNG和大trace重新穷尽复演；这不是脱敏安全审计或未来版本的证明。

收尾补充：实际读取另一独立Reviewer的逐A1–A12/E1–E5意见，并核对原生delivery-judge收据SHA-256为78c8b42cca9290e7b6a873a3db0fcc476b10e3a6ff41baf7c88a272470b0f718，操作status=judged、judgment.status=passed，Reviewer为/root/review_complete_requirement_final，定义SHA与本轮一致；公开current-summary的R005也已更新passed。新增scripts/acceptance/README末节已给出三个completion探针、真实旧wheel及全模块清单输入、六空查询/Windows普通身份与300秒记录边界，命令参数和实际控制器一致；PLAN同步记录这一文档位置，属于维护入口补充，没有改变产品或验收条件。

交维护者前仍须由根代理完成当前PR最终摘要、把本轮未跟踪证据纳入最终提交，并在最后一次导出后复核链接、双SHA、脱敏与摘要一致性。本意见没有代替最终提交或维护者的合并决定。
