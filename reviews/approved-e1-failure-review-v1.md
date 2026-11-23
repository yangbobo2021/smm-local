# 获准额外一轮 E1 实际失败独立执行复审 v1

验收 ID：AT-SMM-007。项目根：/private/tmp/smm-007。

结论：三平台 E1 及追加的用户发现记录均为 needs_revision，revision_target 为 implementation，covers 均为空。已确认共享测试实现错误导致提前停止；没有据此证实产品缺陷，也没有完整 E1 或用户发现通过证据。原始 observed_failure、CI 失败和旧轮历史应全部保留。

本次只读复审现有原件，写四份单 TC JSON 和本报告；没有运行测试、启动产品、应用纠正草稿、修改产品或脚本，也未操作 GitHub、ESXi 或日常资料。

## 原始依据与检查分配

实际阅读了根 AGENTS.md、changes/007-hub-document-search/{intent,spec,plan}.md、changes/007-hub-document-search/acceptance/manual-cases.md，以及 /Users/boboyang/.agents/skills/app-delivery-acceptance-native/SKILL.md 和 references/execution/reviewer.md。handoff 中的 acceptance/manual-cases.md 实际位于007变更目录下，根下没有该文件。

逐份读取目标 case_obligations、obligations 与 case_design 指向的 design-sc9-final-v2/result.json。每份 E1 目标只有一个实际 TC 和一个完整业务长检查：macOS 为 e1-macos-1、Ubuntu 为 e1-linux-2、Windows 为 e1-windows-3。每项均要求 CLI、真实 Web、stdio、创建端管理、同步选择、版本/暂停/撤回/离线恢复/来源移除/业务后重启。局部事实不是分别分配的小检查，故不能把完整长检查放入 covers。

SPEC B6 以原档案、设备、文档 ID、版本及双摘要认定同源同版合并。B7 允许合并命中沿任一仍有效的当次同版本精确来源读回，并明确实际端。A7 要求独立原文与准确身份，禁止换另一目标或版本。以上未规定联合候选的归档内部 id 必须等于实际读取端的归档内部 id。

## 原件、版本与运行身份

三份 target 原字节 SHA 与 handoff 完全一致。macOS/Ubuntu 各79份 artifacts、Windows 80份 artifacts 的 SHA 全部匹配；每份45项产品 bindings 均与当前文件匹配。Local 安装原件含30个模块，Hub 含31个；逐项比较可直接映射的 Local 30项和 Hub 30项（含 vendor 映射）均与当前源码相同，Hub 生成的 _archive/__init__.py 不冒称直接源文件。相关 smm_local/document_search.py 摘要统一为 79eb9dd928a45e75aecbaf190aef8c7a4d522020cd797bb5d44e9837efc31360。

本轮记录标识为 CI45260738680/head3eb918c；本地 work/e1-approved-dispatch-v1.json 记载 head3eb918c、document-installed-e1、services_requested=false。下载收据记录 artifact 14859473738 / 14861600252 / 14860536361，分别列出下载/GitHub 摘要一致及 ZIP CRC 通过。本报告基于这些冻结原件和交接追溯执行，没有另行请求 GitHub API。

冻结 runner 位于 .acceptance-local/native-v1/AT-SMM-007/work/runner-snapshots/e1-approved-3eb918c/。三平台附件及 runner-bindings 对应 platform SHA 7a707b8b0ab8dc6732a7715a5b0fdc8f8acbbed5e4fb319c21a7737e5c8e8557、checks SHA 3f1d1921c0646dbdec12ccd04ddcd3f44666602ad50f6faadfd3ad5c87859334、MCP worker SHA aa2188fbb7197c5ef13259c1eb8b74917ab89a775b288f37f3dd90d908171f32。产品和测试版本分别核对，没有把未应用草稿作为执行版本。

controller 和每平台83条实际进程身份原件分别为 macOS UID501、Ubuntu UID1001、Windows is_admin=false/session2。全部四组 MCP 子进程退出0。cleanup.json 的本任务所有已记 PID/子 PID 均 alive=false，all_current_ports_closed=true；Windows 包含启动器子进程树。这些事实支持普通前景进程及收尾，不是服务 E2 证据。

## 三平台实际失败

| 平台 | 目标及 target SHA | 首个失败的 all 结果 | search id → 实际 local read id |
|---|---|---|---|
| macOS | manual-e1-macos-approved-v2 / 0e9edb68848cf0b74883a1e7e4263c85cbe346898213a9c169ef48b3d064704b | 第7份 A one | 109bac8cd9022144faef2babad22a0cb → d9da08d71b744973a197678cb3e07362 |
| Ubuntu | manual-e1-linux-approved-v2 / 85458cdcee5cba1e1db917f63223d5e049c25d24d5242006d200eaf38e0cc7a6 | 第5份 A two | 84086ae4cc9418e13dcaadfb1a073edd → 6b7977619dc9445188ede2e83ef44f0f |
| Windows | manual-e1-windows-approved-v2 / d40cd9b10a01858d083f15d1555430d6e8cf98f720d189fd214c6c3c7c729c99 | 第8份 A two | b4c5c4656f103214f942b8e1b0692e19 → 72d582fd10a04f21a766b98c70870659 |

每份 origin.document_id 均为表中 read id，完整 origin 相同，version 均为1，search archive_scope 为 combined，read 明确为 local。排序顺序差异不改变根因。第二份 A 的合并命中也有相同的合法 ID 差异，完整 origin/版本/原文仍吻合。

业务原件分别位于：

- /private/tmp/smm-007-ci-e1-approved-macos-v1/007-public-evidence/platform
- /private/tmp/smm-007-ci-e1-approved-ubuntu-v1/007-public-evidence/platform
- /private/tmp/smm-007-ci-e1-approved-windows-v1/007-public-evidence/platform

内层 failure.json 与实际 stderr 均定位 hub_documents_platform.py:2210 → stdio_checks:1753 的 actual.id == hit.id 断言，phase=archive-only。macOS/Ubuntu 外层包装为 platform exit1，Windows 包装为 standard-user exit1；不能把外层包装推定为产品崩溃。

## 完整 MCP 与独立原文核对

逐平台展开 mcp-5.json 的 records[0].response.content[0].text，再逐条展开 mcp-7.json 的 records[].response.content[0].text，没有只看摘要或 structuredContent。每平台10个 search reference 都原样用于对应10次 read；十次读取均已返回业务对象。

每个平台十份 read 的完整 origin 与对应 hit 相同；版本、双摘要、文本长度、起止码点及 LF 行号均正确，正文逐份对照冻结 runner:1442–1491 的十份独立原字节一致。包括 A 的 BOM/CRLF/emoji、两份 B、private/global/unbound、两份 Hub D 和 Hub E；全集唯一完整，没有发现误读另一个目标、版本或正文。执行先在 :1745 调用 document_set；其 checks.py:31–55 按独立 origin/version 全集、原字节双摘要和准确正文判定，已到达 :1753 也证明该前置检查实际通过。

十份 read 在循环断言之前全部发出，所以原始协议支持对十份读取做本次独立核对。但执行器循环中只有首个不等 ID 之前的 exact_read 完成；失败后的 exact_read 和 stable_mcp 全集断言未完成。不能把独立复审读取原件得出的局部事实说成控制器全部断言实际走完。

## 根因与修订边界

当前 src/smm_local/document_search.py:241–268 先遍历 local，再 remote，以稳定 origin 和版本为 key。遇同源同版时核双摘要/窗口相容，以 local ref 和 remote ref 构造 bundle，保留 remote 候选对象并标 combined。因此 search.id 可为 Hub 归档内部的投影 ID。:325–332 按 bundle 的当次精确 parts 依序读取，返回第一个有效来源；本机可读时返回 local 原档案 ID 及真实端。稳定 origin 不变而内部 ID 可不同，符合 B6/B7。

新增 actual.id == hit.id 把不同档案内部 ID 误当跨端稳定文档身份，属于实现测试的错误预期。最早修订阶段为 implementation，无需改 SPEC、场景或自然语言设计。应核完整 origin/版本，并保留独立原文、字符/行号及精确 ref 路由核验；不能仅删除身份断言，也不需要修改产品以迎合错误预期。

只读查看了 /private/tmp/smm-007-e1-origin-assertion-correction-draft.patch：三个位置把 id 相等改为完整 origin/版本相等，方向符合根因。后两个重启位置未到达；静态认可不代表补丁已应用或复跑成功。本次没有应用或运行草稿。

## 有效局部与未到达范围

prepare/CLI、直接一层范围、部分 stdio 和十份协议 read，以及最终实际进程/端口清理均有有效局部原件。execute:2210 抛错发生在 :2211–2212 两端 web() 之前，后续创建项目、选择/拖入、更新删除、伪造管理拒绝、纯文本 DOM/无执行，以及 :2227 生命周期、暂停撤回/离线重连/移除、业务停启后的 Web/stdio 原 ref 读取均未到达。该轮没有相应关键 PNG/trace/重启业务原件，不能借旧轮画面补成当前 passed。

prepare 中连接后的 Local 停启不替代 PLAN E1 第5条业务后持久性；源指纹最终比对也在 stdio 后，不能认完整无源变化检查已完成。因此三项唯一长检查均不认领 covers，完整 E1 未通过。E2 服务补证停止及物理跨机资源缺口不在本次授权复跑范围，不能由该局部结果豁免。

## 追加：用户发现同一测试故障

按 /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/work/user-approved-failure-v1-handoff.json 复审 manual-user-discovery-approved-failure-v2，只涉及 TC-007-user-discovery/SC8。target SHA af6eebb3596188ff2cc89681b674c5eb7e13ecf086246af746cdf9b123d680a8 匹配；66份 artifacts 和49项当前产品/说明 bindings 全部匹配。唯一分配 user-discovery-3 包含发现、业务、两种旧页面 CAS、隐私和恶意标记纯文本长检查。

附件 actual-user-wrapper.py 显示 prepare → shared_conversation_range → stdio_checks → 两端 web → observe。实际 failure 在 wrapper:14 调用共享 stdio_checks:1753 停止，文档导航与 Web/CAS observe 未到达。展开本机 mcp-5/mcp-7 完整响应，十份 ref/完整 origin/版本/正文对应，首失败第6份 A one：combined id70fe9b0000aa6e33bf3a5bbf518683f4 → local id3a338469585a44eb940e3d15a19b1ca4；origin.document_id 始终为后者。故与三平台相同，判测试 implementation 需修订，不能判产品缺陷。

独立隐私流程附件 result.json 实际 passed；browser-privacy.json 保留四阶段浏览器 URL/持久存储空值及12份同源认证请求，privacy 脚本:128–162 对重载后重新选文件前不发 API/认证头有实际断言。trace ZIP 可读、CRC 正常，实际动作有 goto、首次凭据选择、reload、再次选择、search/read，不是静态 HTML 推测。

本次实际打开四张目标附件原图：

- attachments/9dc504f88a84de31/privacy-anonymous.png：未认证连接空壳，无项目或正文。
- attachments/c5b1402a5b5c4a03/privacy-reloaded.png：重载后回同样空壳。
- attachments/9a5763df6dc8688c/privacy-authenticated.png：已认证 Hub 身份、项目和来源可见。
- attachments/04d298667f4dd8af/privacy-reauthorized-read.png：重新认证后可见独立原文 e1needle D native one、版本、范围及实际 Hub 出处。

以上路径均相对该 target 的 TC-007-user-discovery 附件目录。画面与 JSON/trace 相符，支持隐私局部事实；未把这些图当新建项目/拖入/更新删除/CAS或恶意脚本/事件材料的完整证据。

当前 scripts/acceptance/README.md:5 已显示36项/28自动8人工并直链007当前证据，C1 静态修正确实存在；但新的导航阶段没有实际到达，旧说明绑定的历史 passed 不能替代当前复验。故用户项同样 needs_revision/implementation、covers=[]；隐私局部通过不授完整 user-discovery-3。

## 单份独立意见

四份意见均在写出后立即分别通知主 Agent 登记，未等待报告；每份 JSON 只含其目标实际单 TC：

- /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-e1-macos-approved-v2.json
- /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-e1-linux-approved-v2.json
- /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-e1-windows-approved-v2.json
- /private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/review-manual-user-discovery-approved-failure-v2.json

后续若获准修订/重跑，应保留这些失败和意见，冻结新 runner，取得完整实际后续业务及独立复审。本报告不新增执行授权，也不判完整007交付通过。
