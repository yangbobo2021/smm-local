# PR #30 独立审查：06dd2ef

审查人：`/root/review_005_final_pr`。审查对象：[PR #30](https://github.com/yangbobo2021/smm-local/pull/30)，已确认 PLAN 合并 `78973cf7ae6759332c0a320f630f5ebfb44204b6` 至 `06dd2efd4e6b58165d6854cd5dc848c7c4d568b0` 的实际 diff。产品模块与 `d80de6731d681ca06276dd6231a1eb77c0a7111c` 无差异，不能用同为 0.4.0 的包版本字符串替代字节身份。

按 `changes/_templates/pr-review.prompt.md` 执行：独立阅读已确认意图/规格/计划、全部实际产品模块改动和新增验收控制器；核对主要测试的断言和原始证据；由 README 回放实际角色路径。没有只按既有通过记录下结论。仅写本报告和自有探针，未修改产品、测试、验收注册或证据。

**结论：需要修订，当前不可判为完整交付通过。** 有两处独立复现的实际行为缺口；必需 macOS E3 系统 launchd 仍未验证，Windows 等在途材料不能预判通过，另有下述实际入口覆盖尚不能确认。现有核心通过、文档路径可达、完整交付通过是三项不同结论。

## 已确认的实际行为缺口

### [P1] 对账提交未绑定所展示的本机规则，可确认另一入口后来保存的允许规则

性质：违反 B1 “明确重新提交所显示的本机规则”及对过期页面重新查看的要求；同时损害 B4/B8 的有效意图与恢复确认边界。

位置：`src/smm_local/upload.py:213–229`，尤其 `223` 从当前 `self.row()['desired']` 重新取规则，`228` 没有传入 `_save` 已支持的 `expected_generation`。`api.py:58–60` 的对账请求只接受 Hub 版本；Web `static/index.html:198–204` 展示 `uploadDifference.local.policy` 后只传 `uploadDifference.hub.revision`。按钮明确写着“重新提交上面所示的本机规则”（同文件 `58`）。

复现：同目录 `pr30-final-06dd-reconcile-probe.py`（原执行文件 `/tmp/smm005_review_reconcile_probe.py`），合成临时档案，实际 LocalUpload 与 TestClient Hub：

1. 双方规则 none；取得差异，本机 generation=1、Hub revision=1，页面所示本机是 none。
2. 另一入口保存 all，模拟仅规则 set 请求断线；本机 generation=2/all/pending，Hub 仍是 none/revision=1。
3. 原页面以旧差异的 revision=1 选择重新提交本机规则。
4. 实际结果为 all/confirmed，而被确认页面显示 none。现有 Hub CAS 合法通过，因为 Hub 并没有改变。

实际输出：`displayed_local_policy=none, displayed_generation=1, concurrent_local_policy=all, concurrent_generation=2, result=all, state=confirmed`。

影响：恢复或离线并发管理中的用户核对了停止规则，却由旧页面确认并开放了未展示的全部上传；后台随后可发送正文。操作可完成，但完成的是用户未核对的规则，不只是增加发现难度。

建议：差异输出提供绑定本机目标/规则/代次的确认材料，CLI/Web 提交时同时核验本机快照与 Hub 版本，并在同一 `_save` 写边界拒绝本机已改变的视图；不能只在网络请求前取一次 generation。保持查看差异不修改规则。通过条件：上述场景明确拒绝旧视图、Hub 仍 none；重新查看并明确确认 all 后才可开放，另覆盖差异读取与提交间的本机修改竞争。

### [P2] 范围引用过滤了消息，但读回标题仍包含范围外用户正文

性质：违反 B7/A8 的共享会话范围正确性；不是新增多用户授权要求。

位置：`src/smm_local/references.py:106–119` 先读完整会话，再仅替换 `messages`，保留完整会话 `title`；Hub `hub.py:506–518` 没有重算 scoped title。`core.py:776–803` 的标题来自 conversations。Web `static/index.html:152` 直接显示读回 `d.title`。搜索端 `core.py:757` 附近已按项目内消息生成标题，读回反而放大了可见内容。

复现：同目录 `pr30-final-06dd-title-probe.py`（原执行文件 `/tmp/smm005_review_title_probe.py`）。共享 Hub 会话的第一条用户消息属于 Y，正文 `OUTSIDE Y ONLY SECRET TITLE`；第二条属于 X，正文 `common allowed X`。本机 A 只关联 X。实际按 A 搜索并读取其返回 reference：

- search_title：`common allowed X`
- read_title：`OUTSIDE Y ONLY SECRET TITLE`
- read_messages：仅 `['common allowed X']`

影响：CLI/MCP 得到的响应以及 Web 原文标题带出范围外消息的首行正文（通常至多 120 字），尽管 messages 数组正确过滤。原文按钮可操作，但其结果突破了所声明的项目范围。

建议：新范围引用的返回标题从引用允许消息生成，避免复制范围外文本派生的整会话字段；同时检查其他整会话内容派生字段。旧整数/旧 unscoped 读取语义继续保留。通过条件：上述 split-X/Y 场景在 CLI/MCP/API/Web 读回的所有可见内容均无 Y 唯一标记，消息仍准确，旧式读取仍可见其原有整会话标题。

## PLAN 核对与实施偏差

实际模块分工和主要方案与计划对应：本机持久规则/回执、同锁派发边界、Hub 规则与归档同 SQLite 事务、独立保护标记、共同范围、完整候选 BM25、新引用及三入口共用逻辑。新增 project_control、known-upload-messages、register/managed marker、独立签名表、旧 Hub 候选核验、实际恢复入口、验收控制器和 Windows 锁/CA 修复均已在 PLAN 调整记录解释。新增 A→获准 B 的归属传播已先进入 SPEC B3/A3 和 PLAN 第11节；不是实现自行决定的新行为。R4 离线安装成功桩与真实服务重启/健康失败/restore 的测试边界已明确，不能认领发布下载验证。

一处轻微未解释的方案偏差：PLAN `plan.md:42` 写“全局项目通过类型唯一约束”，实际 `core.py:603–607` 以 BEGIN IMMEDIATE + 查询后插入保证公开 ensure-global 入口唯一，未见数据库唯一约束。所有公开创建入口走同一方法，未发现可由正常操作产生第二个 G 的反例，故不列为产品阻断 bug。请在计划记录实际依赖的事务保证及原因，或实现计划中的约束；不要把未实现约束写成已交付事实。

## 实际角色与使用路径回放

### Hub 使用者：控制上传并确认进度

- 主入口 README “多台电脑共用档案”提供 setup/status、地址、显示名、管理员交付凭证文件的来源（README `32–50`）。相邻“选择上传项目与联合检索（005，尚未发布）”直接介绍适用版本、新连接查询优先、四模式、旧副本保留、联合查询，并链接具体指南（`52–68`）。目标用户有理由进入该链接，无需先知道 changes 目录。
- 指南 `TRIAL_GUIDE.md:139–145` 明确 0.4.0 正式包/启动器没有此能力、候选源码/wheel 的安装方式、两个独立环境和不同系统的实际解释器/CLI 位置；不是让用户重复安装旧版期待新功能。
- 指南 `145–160` 给出配置值、项目列表、四个替代设置、空名单及完整替换含义。本机 ID 来自 smm projects；Hub ID 的另一套来源被明确区分。`upload status`、确认与正文进度、失败/在途/补齐的含义都有解释。CLI help 与 Web 文案相符。
- Web 原入口“导入进度”有对话上传摘要及“设置上传范围”，跳至“配置”。四模式、项目复选项、停止保留和空名单说明可见；“项目”列表含 ID/种类/是否允许和可展开稳定身份。实际保存需同源控制；预览/引用不是凭同号猜来源。已查看 mac-run8 的 config-2-except.png 与 combined-stopped-search.png，文字可读，按钮和实际覆盖说明可见。真实浏览器响应/CLI 对照在 browser-configuration.json、combined-stopped-browser.json 等。
- 正常保存路径可完成；旧差异提交路径存在上面的 P1，文档路径可达不能消除此行为缺口。

### 使用者及 Agent：联合搜索、定位原文与限制范围

- README `64–68` 先交代联合/一层范围/显式本机和 reference，再由指南 `175–187` 给出项目 ID、CLI、MCP、Web 具体入口，说明各条档案、bundle、旧读取和失败回退。
- 已安装 Skill 的原入口是其 SKILL.md。该文件给维护状态→resolve_project→search→read 的顺序，新的 combined 和逐条 reference 规则、局部/全部/离线范围、正常零命中与失败区别均明确；MCP工具说明也交代默认联合和 local=true。first_use.py 保留 source 入口并对旧运行组件的 upload/project/reference 操作报明确版本边界，未让安装器假称支持 005。
- 指南 `164–173` 与 Web“全局项目与明确归属”提供本机会话 ID 的取法、目标 ID、confirmation 的取法及失效条件。仅本机搜索→复制会话 ID→预览→确认的路径连贯；路径映射/合并扩大允许的确认边界可见。
- CLI/MCP/API 的默认/显式本机/回退/引用共用 federation，真实入口材料有实际响应与逐条读回；范围引用标题的 P2 是局部完成结果不正确，不是找不到入口。

### Hub 维护者与恢复操作者

- README “搜索 VibeInsight 和关联项目”链接指南“管理汇总端的项目关联”。指南 `120–136` 说明无需正文即可登记、用 hub project list 找 Hub ID、link/unlink/links，并解释一层双向关联与设备同名身份。日常使用者无须擅自配置 Hub 关联。
- 指南 `189–210` 从兼容边界转入恢复。实际状态目录从原 hub status 的 database 父目录确认，并沿用服务原 --state-dir；prepare-restore 输出 restore_files、do_not_restore、identity，之后停服务、恢复一致性备份、保留保护文件、重启、查看差异、明确处理。expected-hub-revision 来自刚取得的 hub.revision。所需值的含义和取得方式充分。
- 恢复后的差异查看与两种处理入口存在，R1–R4 原始材料展示真实执行；它们不能证明所有并发视图都安全，P1 是该路径漏掉的必要边界。

未发现需要额外纳入本次范围的、已确认的独立发现路径阻断。没有要求为了本次变更固定修改其他导航文件。文档/API/实际角色入口可达的结论不等于每个系统已实际验证。

## SPEC 与验收证据核对

可复核的正面证据：

- 独立复跑 `test_upload_review_regressions.py`、`test_upload_dispatch_fence.py`、`test_upload_project_moves.py`、`test_upload_acceptance_boundaries.py`，`PYTHONDONTWRITEBYTECODE=1 ... pytest -q -p no:cacheprovider --basetemp /tmp/smm005-pr30-final-review-pytest`：**19 passed**。验证晚到 offset 前缀、目标/消息身份竞争、时间版本、持久传输失败、三种归属迁移/丢确认、多会话完整集合等；这不覆盖本次新增的两个探针反例。
- 读取 `/private/tmp/smm-005-full-v8.log`：最终 **184 passed, 1 skipped**，104.71s。不是把 v7 的179改称184；我没有独立重跑全量。唯一 skip 的具体覆盖不在本次独立声明内。
- 对 mac-run8 原始证据运行 selective_upload_audit.py + 当前两个 wheel：通过，输出 `/tmp/smm005-pr30-final-review-mac-run8-audit.json`。其检查包括完整包/安装文件摘要、实际回读与独立 BM25、旧批次拒绝、禁止载荷形状。审计器自身明确不是完整 A/E 或视觉验收。
- mac-run8、mac-login-run8、linux-client-run8、linux-hub-service-run8、compat-run8、linux-compat-run8、restore-r1-debug8 至 restore-r4-debug8，逐项读取 manifest/result/cleanup：实际候选 d80de67，Local 25/Hub24 文件清单，result passed，cleanup failures=[]。身份分别为 macOS普通UID501、Linux普通UID1000；systemd 项采用 protocol-only 明确不认领浏览器。
- isolation-run9/mac-entrances-run10 的 manifest 绑定 7ab6d6c，但产品模块与 d80de67 相同；两轮结果和 cleanup 通过。归属传播另有主流程 affiliation-propagation 原文和物理行、共用 assign/map/merge 测试支持。
- native 定义000002与当前核心 SC3/SC7/SC11 收据已针对当前设计/检查分配保留准备/调试与复审；其理由明确仅认领所分配检查，不声称完整平台。不能把核心 reviewed 或某条 passed 外推为整个 SC/需求通过。

逐条件判定：A1/A2/A3/A4/A5/A6/A7/A10/A11 均已有相应共用代码/测试与部分真实环境材料；本次未新增证明这些正常已覆盖分支的产品缺陷。A8 有 P2；A1/B1及A11恢复并发有 P1。A9 的 project 离线路径有实际材料，全项目离线的实际三入口证据见下述缺口。A12 的可发现说明本身可达，但“必需环境全有证据才通过”的总交付条件尚未达到。

## 必需未验证及材料不足（不能写成产品失败或通过）

1. **macOS E3 系统级 launchd 是必需未验证项。** 当前候选索引明确尚无本轮实际运行、用户表示稍后认证；没有用 E2 登录服务或普通 serve-hub 替代的依据。即使两处产品问题修复，也不能在此项未完成时判完整交付。
2. Windows E1 普通客户端/E3 LocalService 当前候选主任务、Windows 真实旧组合的收回，以及 Ubuntu/Windows supplemental explicit local/all：审查时仍在执行或待收回，不能推断结果。应核验新 result、cleanup、实际身份/端点及完整包字节，再填最终矩阵。
3. **E1 A9 全项目离线回退的三入口实际证据尚不能确认。** platform.py `500–514` 的 offline 只调用固定 project A 的 interfaces；isolation.py `74–76` 的 supplemental cases 是 online local-project/local-all/combined-all，不含 offline-all。当前 Mac 目录未见另一个对应原始附件。共用 all-project fallback 正确或 explicit local-all 不能替代各平台真实“默认全项目 + Hub断线”的 CLI/MCP/Web。通过条件：三系统分别保存三入口自己的搜索/逐条引用读取、Hub unavailable及完整本机普通/G/U/plugin集合，恢复后再次联合。
4. **E3/E4 A8 共享会话含范围外消息的实际服务读取尚不能确认。** main 平台夹具是分开的会话；affiliation_propagation 是同版本消息增添 A/D 两归属，未包含必须排除的 X/Y 不同正文；旧引用冻结追加消息的校验也不是项目范围排除。test_shared_conversation_reference_cannot_expand_to_outside_project 是共用测试。应给每个规定 E3/E4 服务实际跑该 split-message 条件的证据，特别结合 P2 检查返回标题；若已有另处原始记录，请补矩阵精确链接而非重复执行。
5. 最终公开 evidence A/E 矩阵、candidate/result/cleanup/服务事件/安装字节与 SHA256SUMS 汇总尚未完成。本轮索引明确 interim，且若修复 P1/P2，涉及产品字节的原生绑定、两个 wheel 与相关平台/恢复/原文结果须按影响重新记录，不能改标旧证据候选版本。

这些是已确认规格中的覆盖/材料缺口，不是建议新增规格。当前没有把“某系统任务慢”或“材料未展示”当成已确认产品错误。所有 source/Vibe 事件均为合成归档；未连接真实 VibeInsight 服务或写入实际来源。
