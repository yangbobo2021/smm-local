# AT-SMM-007 Mac E1 正式证据独立重核 v4

`TC-007-e1-macos` 本轮结论为 **insufficient_evidence**，`covers: []`。本次唯一分配项 `e1-macos-1` 是完整 E1 长检查，不能用大量已通过的局部动作认领整项。未确认产品缺陷。

交接：`.acceptance-local/native-v1/AT-SMM-007/work/macos-protocol-recheck-v4-handoff.json`。目标仍为 `manual-e1-macos-final-v3`，原 result SHA-256 为 `c15df7d65ed335c35aacf7337de83ca3ab99f47fedb6795773c1b340fde85bd6`。定义摘要为 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`，设计为 `design-sc9-final-v2`。

Reviewer `/root/review_007_macos_protocol_recheck_v4` 直接读取 AGENTS、SPEC E1、PLAN E1 第1–6条、`acceptance/manual-cases.md`、该设计及目标收据、验收 Skill 和独立 Reviewer 规则。历史 `manual-mac-user-review-v3.md` 与 CI 复审报告只作定位；下述判断来自 Mac 自身原件和冻结断言。产品、证据及测试只读；仅新增指定 JSON 和本报告，没有业务重跑、测试修补、服务/ESXi/日常档案或 GitHub 操作。

意见先写入 `review-inbox/review-manual-e1-macos-protocol-gap-v4.json`，cases 仅含 Mac TC，完成后已立即通知主 Agent 登记，再撰写本报告。

## 两项必须保留的缺证

### 真实 stdio 的私有及 Hub 自有原文入口

原始依据是 SPEC E1（`changes/007-hub-document-search/spec.md:154`）的“真实stdio MCP联合检索、项目关联及准确原文（本机未传、其他设备、Hub自有均有独立正文）”，PLAN E1 第2条（`plan.md:102`）进一步明确各入口按独立文件集合、版本/出处/文本和字符行号核对。Mac 人工步骤也明确“真实stdio查询私有本机/另一设备/Hub自有原文”。这是已写的入口义务。

逐项读取 `/private/tmp/smm-007-macos-e1-v16` 的全部五组协议原件：

| 原件 | 实际工具调用 | 实际覆盖 |
| --- | --- | --- |
| `mcp-1.json` | sources 两次、projects 一次、A 项目 search 一次 | A/B 四份命中及元数据 |
| `mcp-3.json` | `read_document` 四次 | B one、B two、A one、A two |
| `mcp-5.json` | all `search_documents` 一次 | 十份命中，含 private、Hub D 两份和 Hub E |
| `mcp-7.json` | `search_conversations` 一次 | D 根关联 C 会话 |
| `mcp-9.json` | `read_conversation` 一次 | `e1chatneedle original discussion` |

冻结 `work/runner-snapshots/mac-v16/hub_documents_platform.py:1663` 的 `stdio_checks` 在第1721行附近只对 A/B 项目搜索结果调用 `read_document`；独立预期限定 `a_entries + b_entries`，逐份 `exact_read`。随后 all 范围虽把 private/global/unbound/D/E 纳入 `document_set`，却只有 search，没有再调用原文工具。搜索短片段对独立正文的校验有效；它不证明该正文经过 stdio `read_document` 后仍准确。Local Web 的十份逐文档 read 也保留为 Web 证据，不能补出未调用的 stdio 入口。

### 实际停启后的 Web/stdio 读取

PLAN E1 第5条（`plan.md:105`）原文要求“实际停止/重新启动产品进程，CLI/MCP/Hub/Web新进程读取同档案，不重新配置、不刷新仍得到相同当前有效内容/ref”。

冻结 `execute()` 的实际顺序是第2133行 stdio、第2134行 Hub Web、第2135行 Local Web、第2150行 lifecycle。原时间和协议与此一致：

| 观察 | Mac 原件时间（UTC） |
| --- | --- |
| 五组 stdio 总起止 | 15:18:56.909269–15:18:58.429844 |
| Hub trace 最后网络 | 15:19:01.062 |
| Local trace 最后网络 | 15:19:07.273 |
| lifecycle 重启 B / PID47271 | 15:19:13.161210 |
| lifecycle 重启 Hub / PID47274 | 15:19:13.757512 |
| lifecycle 重启 A / PID47309 | 15:19:15.116150 |

时间来自五份 `mcp-*-process.json`、两个完整 ZIP 的 network 及 `process-identities.jsonl`，没有用文件 mtime 推定业务顺序。随后 commands（零起始索引）270–272 的确通过 Hub CLI 读取三个旧有效 native ref；274–276 是 Local CLI 从 C 根查询并读取 D 两份，原文/码点/行号正确。该段其余 HTTP 是状态/info 等请求，没有 Web 或 stdio 原文操作。`lifecycle.json` 的 `native_cached_after_process_restart=true` 因而只可由这些 CLI/API 证据支撑，不能扩展为全部入口完成。`prepare()` 较早的 A/B 停启发生在新建项目/采集文档之前，不能验证当前有效内容/ref 的停启持久。

两项缺口均由已确认条款直接推出；没有要求“每入口 × 每生命周期状态”组合，也没有要求暂停、撤回、离线等状态在每个入口各复制一轮。本次是正式执行缺证，不能根据 runner `status=passed` 或源码可能正确推断缺失动作实际发生。

## 完整性和仍然有效的局部结果

目标 result 的45项当前产品绑定、66项附件全部逐文件重算匹配。Mac original-copy manifest 的61项源原件/复制件逐字节、长度及 SHA 均匹配；三份 `mac-v16` 冻结 runner 与原 `runner-bindings.json` 一致。实际安装 Local30/Hub31 模块与其安装记录逐项匹配，两份 wheel 原 SHA 也匹配。没有改写旧收据或旧意见。

| 范围 | 独立读取的原始依据及保留结论 |
| --- | --- |
| 身份与隔离 | controller 为 macOS15.3.1 arm64、UID501；175条实际产品身份均UID501。Hub 是同UID独立前景HTTPS，A/B是不同档案和逻辑设备。不是物理跨机器，也不声称本轮执行 launchd。 |
| CLI与独立预期 | 282条 commands：178个 exit0、8个预期 exit2、96条HTTP；186条进程命令的原 stdout/stderr 与base64原字节相符。冻结 helper 对完整 origin/version 集合、两摘要、文本长度、项目/来源及 Unicode码点/LF行号断言；原CLI包含默认关闭、KEY/HID/G允许、目录 pending→显式refresh/sync及各独立原文。 |
| 范围与stdio局部 | CLI联合/本机/项目范围和C↔D直接一层、第二层E负控有独立集合及原文结果；stdio A/B四份read和对话read有效。private/Hub在stdio只有search的局部界限如上。 |
| 两创建端Web | 两端各从新项目开始，文件选择+DataTransfer拖放两份独立文件，创建回执ID不同，正确项目逐份read；创建端PUT保留身份并升版本、旧ref拒绝、DELETE后仅剩第二份。Hub实际选择凭据文件后才显示业务，reload回空壳。Local默认off和允许后真实device投影的结果与独立ID相符。 |
| 越端管理拒绝 | `ownership-forged-management.json` 的两方向各POST添加/PUT更新/DELETE移除/PUT来源配置，共8次400，与 commands132/141/150/159/168/177/186/195及服务日志对应。每端9份实际快照逐份完全相同；Local14/Hub21张文档表SHA，每端4份managed文件SHA/长度/mtime不变。API sources/files/library也逐次比较，不只看HTTP状态或最后状态。 |
| 生命周期 | 原commands及冻结断言证实暂停前两文件有效、编辑后保旧Hub快照且新文件不传；实际chmod0失效撤回和恢复后旧ref仍拒绝，重叠来源连续资格可读、最后资格退出拒绝，离线pending/Hub根fallback、B重启仍pending、同Hub重连补齐、来源移除退出。源移走后新Hub/A进程的CLI读取有效；Web/stdio停启部分仍缺证。 |
| 原生路径与源保护 | 中文空格路径、BOM/CRLF/非BMP/组合字符、真实符号链接拒绝及invalid UTF8均有原结果；10份源的前后SHA/mtime相同。25条源open仅23次explicit-refresh和2次合成conversation-import，没有用注入权限错误冒充实际chmod0。 |
| 清理 | stopped-processes/cleanup记录8次本任务服务停启真实PID及监听退出；五stdio子进程均exit0/alive=false。独立工具源码确实检查真实PID与端口，未将仅父进程退出作为标准。 |

## 实际图像和trace核对

实际打开原 PNG：`web-a-literal-original.png`、`web-hub-literal-original.png`、`web-local-joint-read.png`、`web-local-project-one-hop.png`、`web-hub-device-readonly.png`。看见两端不同资料ID及chosen中文/Unicode正文、dropped原样script/img事件文字；联合结果含private、B和Hub D/E独立原文，C根只有D两个文件；Hub设备投影明确只读且无写控件。这些画面属于原Mac v16，不能用作生命周期之后的画面。

两份 ZIP 全成员实际读取且 CRC 通过：Local1126条trace事件/73网络项、Hub601事件/47网络项，无action error。Local12次、Hub2次原文响应资源实际读取；两创建端初始chosen/dropped按独立字节及创建回执ID逐份比较，正文20/197码点、LF行号1–2/1–4相符。Local另外十份read与保存的joint原响应逐一相同，并以冻结夹具独立字面量核正文、端点、行号及归一化SHA。轨迹含真实选择/拖放、PUT更新和DELETE移除。

纯文本的每端四阶段（new-project、query-snippets、original-chosen、original-dropped）实际evaluate和原记录均为两个window标记unset、main内img/script节点0；完整network无`/smm-document-executed`请求。重复/误指目标负控及四副作用负控有冻结执行路径和原输出，不以截图单独证明无执行。

## 历史v3的适用范围

历史 `reviews/manual-mac-user-review-v3.md` 应原样保留。它对Mac的 `passed / e1-macos-1` 曾认领完整长检查；本轮直接重核发现上述两项已写义务没有实际证据，因此该完整通过结论不宜继续作为当前Mac完整E1通过依据。身份、安装、CLI、Web、已调用stdio、纯文本、8次拒绝、持久摘要、生命周期CLI及清理等局部仍有有效原证，不能因本轮结论而一并丢弃。

本轮仅审Mac唯一TC；不重新判断该历史报告另一项用户发现TC，不替代Ubuntu/Windows复审或E2，也不产生需求级通过结论。
