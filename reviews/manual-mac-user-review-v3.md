# AT-SMM-007 正式人工执行独立复审 v3

本轮两项均 `passed`。结论只覆盖本轮目标中分配的两个长检查，不代表其他 TC、35 项整体、E2、CI gate 或 R007 需求交付结论。原 v1/v2 的不足意见保留，本轮直接复核新目标、当前文档和原始业务证据，未继承其结论。

Reviewer `/root/review_007_manual_mac_v3` 在 `/private/tmp/smm-007` 只读产品、测试与证据，仅写本报告和交接指定的两份意见 JSON。未运行产品业务重跑、Windows/ESXi、日常服务或 GitHub 操作；未代主 Agent 登记。读取验收 Skill 与独立 Reviewer 规则、AGENTS、007 intent/spec/plan、两份授权及 acceptance/manual-cases.md。

| 目标 / 实际 TC | 目标 SHA-256 | 结论 / covers |
| --- | --- | --- |
| manual-e1-macos-final-v3 / TC-007-e1-macos | c15df7d65ed335c35aacf7337de83ca3ab99f47fedb6795773c1b340fde85bd6 | passed / e1-macos-1 |
| manual-user-discovery-final-v3 / TC-007-user-discovery | f02e1356ba9ec0c17f8bf1a59838c77edf7f29c628916ad1d669d2dfe740cab6 | passed / user-discovery-3 |

两份意见位于 `.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-e1-macos-final-v3.json`、`review-manual-user-discovery-final-v3.json`。每完成一份即写出并立即通知主 Agent 登记，各 JSON 的 cases 只有对应 TC。交接为 `work/manual-final-v3-handoff.json`；定义摘要 d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd。设计分别为 design-sc9-final-v2、design-sc8-final-v3，其文件 SHA、当前定义和分配均已实核。

## 版本及完整性

Mac 45 bindings / 66 artifacts、用户 49 bindings / 94 artifacts 逐项实算一致；results 中另外130/186个嵌套文件摘要均相符。macos-e1-v16、user-paths-v5-record-v3、browser-privacy-v2-record-v3 三份 original-copy-manifest 共61+32+24项，源原件与复制件长度和 SHA 全部一致。四份文档冻结全文与当前 README.md、TRIAL_GUIDE.md、skills/smm-search/SKILL.md、scripts/acceptance/README.md 逐文本/SHA一致。

`git diff 245c236 -- src` 为空。独立 v4 两 wheel 原件 SHA 与记录一致；Local30、Hub31个实际安装模块逐一重算并与 wheel 字节、当前源码一致。Hub `_archive/__init__.py` 使用 src/smm_hub/_archive.py 的规定 import 改写，其他 vendor 模块按 build_packages.py 映射 Local 源码，不把生成包路径当仓库同路径。产品 bindings 只有产品与用户文档；实际工具另存在 runner-snapshots。Mac v16 runner-bindings 三文件分别匹配 mac-v16；用户路径 v5、隐私 v2 的旧观察实际匹配 mac-v12，绝不称其旧 helper 是 v16。两个专用 wrapper 自身记录 SHA 与实际源码相符。

## Mac E1

原件 `/private/tmp/smm-007-macos-e1-v16` 为 macOS15.3.1 arm64 UID501，175条业务身份均为UID501。两个 Local 是独立档案/逻辑设备；Hub 是同 UID 前景 HTTPS，不冒称物理跨机或系统 launchd。282条原 commands 含178个 exit0、8个预期 exit2 和96条 HTTP；CLI 原 stdout/stderr、base64原字节、五组真实 stdio 及生命周期均实际读取。

按 PLAN 1–6核 pending→显式refresh、项目默认关闭与 KEY/HID/G允许同步；完整独立身份集合及正文、私有本机/另一设备/Hub自有、联合/本机/project范围、C↔D公共查询与精确会话、第二层负控均有本轮原结果。Mac脚本对每个结果核双摘要、码点、行号及身份/版本；不是仅比较两端响应或首条。生命周期 commands204–281证明暂停前两份有效材料，编辑后保旧Hub正文/新文件不传，chmod0真实不可读失效撤回和恢复仍旧ref拒绝；重新允许当前版本、连续重叠来源/最后资格、离线撤回待确认、Local待办重启、Hub根离线不猜范围、重连补齐、来源移除和新Hub进程仍读源已移走的采集原文。10份初始源指纹前后相同；源打开审计仅显式refresh/合成conversation-import，真实链接拒绝。cleanup/stopped-processes原件显示8个任务服务实际 PID 与当前监听全部退出。

实际打开两端 literal-original、web-local-joint-read、web-local-project-one-hop、web-hub-device-readonly 及两 mixed-batch PNG。画面见对应新项目、两独立资料 ID、纯文本载荷、正确原文/来源；C只含D两文档。Hub device投影明确只读且无上传/更新/移除控件；Local显示Hub文档仅读取及创建端管理入口。混合批逐份两成功、严格UTF8失败可见。完整读取两 ZIP 所有成员/资源、解析全部 trace/network，无 after 错误；Local73/Hub47网络，创建端更新身份保持/版本增加、旧ref400、删除和正确范围由实际资源核对。CLI110仅Hub自有Web文件，120允许后按真实设备投影项目读回Local文件，确认关闭/开启两状态。

v2缺少的后端伪造管理证据本轮已到达。ownership-forged-management.json 对应 commands 索引132/141/150/159与168/177/186/195；原服务日志逐一确认两方向各POST添加、PUT替换、DELETE移除、PUT来源配置，共8次实际400，使用真实另一端项目/文档/来源身份。每次后两端 sources/files/library 完整值均与 before一致；两端各9次持久快照的原stdout逐项相等，覆盖 Local14、Hub21张全部文档表SHA及各4份管理副本的 SHA/长度/mtime。快照只读 `mode=ro`，只读本任务档案及管理副本，无外部源扫描；原保护值不输出。完整状态检测器正控及4改坏负控实际执行。Mac JSON reason 的“Hub22”是纯计数笔误，正确为21；已立即通知主 Agent，结论和逐表核验无变化，不覆盖可能已登记原意见。

## 用户发现与纯文本

直接沿 README→007指南→已安装CLI帮助/Web/Skill及维护复跑入口核必要输入、独立包/公开0.4.0边界、路径所属机器、凭据/TLS、项目ID/KEY/HID/G/state、默认关/暂停/撤回/离线/保护恢复/共享版本与精确ref。三个实际CLI帮助exit0，原参数可见。Agent证据是仓库Skill加本次真实stdio，不冒称全新Agent聊天；完整Web主路径结合本次Mac v16原件，不用旧摘要代替。

实际打开same-hub-before/old-generation、switch-hub-before/different-hub-equal-generation四PNG；原ZIP13条网络中两POST资源分别携H1旧G1（新G2）及H1旧G2（当前H2恰G2），均400并显示准确红色错误。完整before/after逐字段重比相同，未在提交前fetch新form值替代旧值。真实点击、请求正文、拒绝响应和两Hub身份见证一致。

隐私四张原PNG全部打开：匿名和重载仅连接空壳，选凭据后才显示项目，重选后准确原文 `e1needle D native one` 可见。完整隐私ZIP12网络逐私下核token，仅同源Authorization；URL无token，四次原evaluate的local/session均空，四cookies原响应为空。reload893.951至第二次setInputFiles1436.645间仅896.392根GET，无API或认证请求；1441.972重选后才恢复API。原read资源文本独立比对成功；四泄露负控有原输出，TLS仅任务证书SPKI。user/privacy各5任务PID、H2独立一PID及监听清理成立。

两个创建端纯文本使用本次Mac v16两完整ZIP，不由web-hub.json清空后的network=[]证明。新项目名含img/onerror、合法dropped.md含规定script及img事件载荷，MD/TXT同属SPEC纯文本入口。逐创建回执两独立ID核chosen/dropped各一次原read资源，独立预期正文20/197码点及起止/行号一致；两个目标完整集合/唯一身份、四阶段集合及必需PNG均核。各端new-project/query-snippets/original-chosen.txt/original-dropped.md四次实际evaluate均两个window标记未设、main img/script为0；全网络无触发路径。重复/误指目标负控及四副作用负控均实际拒绝。故本轮两个指定长检查各有完整实际证据，可分别登记passed。
