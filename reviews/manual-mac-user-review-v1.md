# AT-SMM-007 两项人工正式执行独立复审 v1

本轮两项均为 **insufficient_evidence**。未确认产品缺陷；共同缺口是已定义的两端事件载荷、嵌入 DOM 与请求副作用检查未实际执行。主要业务、旧页 CAS 与浏览器凭据边界已有有效局部实测，不能升级为完整长检查通过。

Reviewer：`/root/review_007_manual_mac_v1`。根 `/private/tmp/smm-007`。仅只读产品、脚本和冻结原件，写本轮两份唯一 JSON 与本报告；未执行产品业务重跑、ESXi、日常档案/服务或任何 GitHub 变更，未代主 Agent 登记。

采用 `work/manual-final-v1-handoff.json`，恰两目标，operation 均为 manual：

| 目标 | 实际 SHA-256 | 结论文件 |
|---|---|---|
| manual-e1-macos-final-v1 / TC-007-e1-macos | 2c4c151bdd8d745f41530c6841d04716d8fe90e9e294edda477bdb3b1f3af1f6 | review-inbox/review-manual-e1-macos-final-v1.json |
| manual-user-discovery-final-v1 / TC-007-user-discovery | c9684ed791be6dd640f1e5d2da815af10f47a7b2c795d40b40b412435fb5f98f | review-inbox/review-manual-user-discovery-final-v1.json |

以上 review-inbox 相对 `.acceptance-local/native-v1/AT-SMM-007/`。两份完成时分别立即通知主 Agent，第一份通知在继续第二份之前。每份 cases 仅含对应单 TC；分配分别是单个长检查 e1-macos-1、user-discovery-3，未完整确证所以 covers 均为空，局部证据明确记在 reason 中。

实际读取验收 SKILL、execution/entry 与 reviewer、AGENTS、007 intent/spec/plan、原授权 authorization.md 与 project-library-authorization.md、人工步骤 manual-cases.md；核 SC9 final-v2 与 SC8 final-v3 的实际设计记录及现有设计复审。定义摘要 d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd。本轮不是27自动TC复审，也不对35TC/27自动8人工整体、CI gate或R007交付作判断。

版本与完整性：两目标 SHA 实算相符；Mac48项 bindings/56项 artifacts、用户54项 bindings/82项 artifacts 均逐项重算无缺件或不符。四组copy manifest（macos-e1-v10 54、user-macos-gui 22、user-paths-v4 32、browser-privacy-v1 24项）原source与副本长度和SHA全部匹配。实际runner记录的 platform/checks/mcp_worker/user_paths/browser_privacy SHA与审查时源码一致，用户原件四份文档摘要等于审查时内容。

产品为245c236内容；本次独立v4 wheel与当前产品源码逐模块重算一致：Local30项、Hub31项。另从包成员全集核对源码→wheel字节→安装文件；Hub `_archive/__init__.py`按packages.py的 `from smm_local.`→`from .` 改写，以及7个pure Local模块/importers映射均逐项实算，非只核版本字符串。Local wheel SHA 0eca3d5828ab443e94396d1af39e1d775d4311b2b82a9c59b5fa8f4052a15fd9；Hub3268544c4475087c64d76d3124b1aec6c3ab7e41c5f4385828fd9d55849ddd44。后续脚本修订或新执行不移入本版。

Mac原件 `/private/tmp/smm-007-macos-e1-v10`：实际UID501/macOS15.3.1、两份独立Local逻辑档案和前景HTTPS Hub，200条命令记录含159个exit0、8个预期exit2及33个HTTP等非exit记录；CLI/stdio、两端新建项目/选择与DataTransfer拖放、独立正文及码点行号检查、版本及旧ref、暂停保留/不可读撤回/重叠连续资格、离线待办与重启原件存在。生命周期原件明确暂停前两份版本1、恢复后版本2及新文件、连续来源读回成功/末资格拒绝、离线错误、原Hub档案新进程读回；源打开审计只在显式refresh/conversation-import阶段，10份初始源的SHA/mtime前后相等。cleanup记录8个真实任务服务PID均退出、当前监听全闭。同机逻辑身份不算跨物理机器；前景Hub不算launchd。

实际打开的Mac PNG为 web-a-search-read、web-hub-search-read、web-hub-device-readonly、web-local-project-one-hop。前两图可见各创建端独立文档ID/版本、中文组合字符及script字面片段，第三图明确投影只读且无写控件，第四图从Conversation C仅命中Hub D两文档、阅读区出处/原文准确。两trace逐行读取：web-a1079记录/73网络、web-hub551/47，均无after错误；实际打开关键JPEG `page@4234d6e5f5801227c2e9dc75e9e2f5c0-1795439636685.jpeg`（删除后只剩dropped）、`page@e79b6ae50d3f26f2a9719e6395b2224e-1795439633969.jpeg`（A/C成功与B严格UTF8失败）。PNG和trace不由结果passed字段替代。

用户路径原件 `/private/tmp/smm-007-user-paths-v4`：实际原文README→007指南、Skill及维护复跑入口说明预览包边界/独立安装、路径所属端、凭据来源、项目及稳定KEY/HID/generation取得、暂停/撤回/保护恢复state和版本/ref；已装CLI三个help实际exit0并显示对应参数。操作部分结合本次附入的Mac Web/stdio原件，不称新Agent对话。旧页两条实际网络请求资源逐一打开：同H1旧页G1、新完整状态G2；换H2后旧页仍H1且新旧G恰为2；两POST均旧KEY/HID/G、均400，完整before==after。实际打开 same-hub-old-generation.png 与 different-hub-equal-generation.png，分别红色显示“本机文档选择已变化，请重新查看generation”和“Hub身份未知或已切换，请重新查看sync-status”，原选择值仍可见。stale-pages-trace181记录/13网络，无after错误，最后JPEG `page@8e033f0d8537e34c4fd0d416da501275-1795442650596.jpeg`已打开。主请求前没有以新fetch值替代旧form值。

独立隐私原件 `/private/tmp/smm-007-browser-privacy-v1`：四张privacy-anonymous/authenticated/reloaded/reauthorized-read PNG全部实际打开；匿名及刷新为空连接壳，认证后显示Hub项目，重新选文件后准确显示独立预期 `e1needle D native one`。实际trace234记录/12网络，无after错误；四个evaluate返回URL均为任务HTTPS根、localStorage和sessionStorage均空，cookie原记录均空；逐条读实际网络头并私下比较任务token，认证仅同源Authorization，URL无token，未输出token。reload与第二次setInputFiles之间仅根GET、无API/认证请求，重选后才恢复API；四类URL/local/session/cookie已知反例检测器有实际拒绝记录。仅任务SPKI而非全局忽略证书。最后JPEG `page@6fe6b7e33cd1b505ef6632b58bf84912-1795443429970.jpeg`已打开；画面位置在底部来源，不将其本身冒充原文展示，准确原文由本次完整PNG及DOM断言支持。user/privacy两组各5服务PID清理/监听退出记录成立。

阻塞依据相同且具体：manual-cases第6步要求两个创建端同时上传script和img/onerror标记，检索/原文仅文本，无相应DOM元素或请求。SC8 v3设计明确承接该步，Mac步骤也明确“另按用户路径第6步”。实际绑定platform.py只在dropped.md加入script，且仅检查 `window.SMM_007_EXECUTED===undefined`。本次原图也只有script字面片段；trace中onerror仅为产品FileReader.onerror，未有规定img事件载荷。新隐私探针验证凭据边界，未执行此载荷；旧页探针仅验证CAS。因此对img/onerror的执行、嵌入元素、事件请求副作用没有实际输入和观察。浏览器innerHTML插入script可能不执行script但仍生成元素，window标记undefined不能证明相同承诺。缺口属于测试执行证据，不能据此断言产品确实会执行，也不能以源代码textContent或另一自动TC代当前人工实际操作。

需保留原件和两份insufficient_evidence意见，按已定义第6步补强实际输入/DOM/完整网络观察，取得新版本执行及独立复审。该续接建议不改变SPEC、不删除原检查、不修改本版记录；是否后续重跑由主Agent依授权处理。
