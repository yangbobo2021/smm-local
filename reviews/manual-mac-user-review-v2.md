# AT-SMM-007 正式人工执行复审 v2

本轮按 `work/manual-final-v2-handoff.json` 只复审两份指定目标，读取 app-delivery-acceptance-native 与独立 Reviewer 规则、项目 AGENTS、007 intent/spec/plan/manual-cases 和两份授权。未修改产品、测试、目标收据或证据，未运行服务、Windows/ESXi、日常数据或 GitHub 操作；只写两份意见和本报告。未继承 v1 insufficient_evidence 结论。

| 实际 TC / 目标 | 正式结论 | covers | 意见文件 |
| --- | --- | --- | --- |
| TC-007-e1-macos / manual-e1-macos-final-v2 | insufficient_evidence | [] | review-inbox/review-manual-e1-macos-final-v2.json |
| TC-007-user-discovery / manual-user-discovery-final-v2 | passed | user-discovery-3 | review-inbox/review-manual-user-discovery-final-v2.json |

以上路径均在 `.acceptance-local/native-v1/AT-SMM-007/` 下。每份完成即单独通知主 Agent 登记；结论仅覆盖对应正式观察，不判完整 A8/A9、E1/E2 或需求总体。

## 版本和完整性

两目标 SHA 分别为 `eadf368ee76bc98084cad786c7ee1634069c8cd96278616a7b80998d1ee5f0e1`、`63869a74bb9c07132ed0005f9e25c96cb78e4d2884656968f52673399393c938`，均实际重算一致。设计记录 design-sc9-final-v2/design-sc8-final-v3 的 SHA、定义摘要及 case_obligations/expected 一致，分配分别只有 e1-macos-1、user-discovery-3。

两目标全部 bindings/artifacts 分别110/142项，以及 results 内122/174个嵌套文件摘要均逐一复算一致。三份 original-copy-manifest 共116项（macos-e1-v12 60、user-paths-v5 32、browser-privacy-v2 24），源原件和复制件均实际打开、重算长度及SHA，未发现不一致。四份用户文档冻结全文与当前文件也逐SHA一致。

独立 v4 两wheel实物SHA一致，实际已安装Local30/Hub31模块与记录及当前源码相符（Hub vendor映射Local源码；生成shim另有准备审查依据）。`git diff 245c236 -- src` 为空，故本轮适用产品字节未被后续验证/CI/文档变更替换。

## macOS E1逐步核对

1. 原 controller 为macOS15.3.1 arm64、UID501，174条业务进程身份同UID；使用独立wheel解释器、两个Local档案/逻辑设备和前景HTTPS Hub，空Agent根。CLI配置目录、pending→明确refresh、默认项目关闭和稳定KEY/HID/G允许/sync均有原命令。
2. commands共200项，真实stdio五组含工具列表、覆盖/项目、查询、原文、会话双向关联；完整独立夹具集合和字节/码点/LF行号由checks原断言逐项核，Web全量/项目一层及负控由实际trace和PNG支撑。
3. 两端真实Web新建项目，文件选择/拖放、两份命中与逐字read、同身份更新新版本/旧ref拒绝、移除及本机同步关/开有原请求。实际打开web-a/hub-literal-original、web-local-joint-read、web-local-project-one-hop、web-hub-device-readonly和两张mixed-batch原图。图中Hub投影明确只读且无写控件，本机Hub搜索结果只提供读取操作。**但本项原义务的“伪造管理拒绝”没有执行证据**：platform.py没有越端伪造添加/更新/删除/配置请求和拒绝后库/磁盘不变断言。commands中的两次HTTP400只是旧ref读取；两ZIP网络各一个上传400是混合批非法UTF8，所有PUT/DELETE均为创建端合法200。隐藏控件不能替代后端伪造拒绝。
4. lifecycle实际原CLI含暂停两份既存文件保旧Hub快照、新文件未传，chmod(0)真实不可读失效撤回、恢复仍拒绝旧ref、重新允许新版本、连续重叠来源及最后资格退出；离线撤回待确认、重启Local待办持久、Hub根拒绝猜本机范围、重连同步和来源移除均有对应结果。
5. 原文件指纹前后相等，source-open-audit只见明确refresh/合成会话导入；真实链接拒绝，移动Hub源后真实进程重启仍读取采集内容/引用，八任务PID与端口清理记录成立。不称物理跨机或launchd实测。
6. 纯文本局部实测见下节，已补齐原v1所缺script/img onerror、DOM和全网络证据，但不能替代第3步尚缺的独立业务检查。e1-macos-1是一个完整长检查ID，不能用部分通过认领整个covers，故本项insufficient_evidence，尚无越端产品失败事实。

注：已交macOS JSON末句附带“还未见Local展示Hub资料时的管理动作缺失观察”的早期疑点，在后续用户路径复核web-local-joint-read原图后可消除；已立即通知主Agent，不覆盖既有意见。阻塞依据仅保留上述确实缺少的越端伪造请求/状态和磁盘不变证据；正式状态不变。若登记需要更新表述，应使用新请求ID，保留原意见。

## 用户发现逐步核对

1. 直接读取README主路径→TRIAL_GUIDE→CLI帮助/Web/Skill及acceptance README。文档说明独立包、源路径所属端、项目ID、KEY/HID/G/state、HTTPS及凭据取得、暂停/撤回/恢复/范围/版本、维护复跑与当前证据位置；真实安装CLI三级help及实际业务原件相符。default关时Hub命令第110条仅有Hub dropped，开后第120条为Local投影 dropped，未凭非空数量冒认同步控制。
2. Mac v12真实两端Web和stdio原件证明按项目命中、准确原文、创建端管理及对端可见只读。Hub匿名/选择凭据前置与图像/真实请求相符。Agent路径是仓库Skill与实际stdio，不冒称另开全新Agent会话。
3. 已实际打开privacy-anonymous/authenticated/reloaded/reauthorized-read四张原PNG。原ZIP四次evaluate及cookies响应为固定无token URL、空localStorage/sessionStorage/cookies；12条全network仅同源API带Authorization。重载GET到重新选择前无API或认证请求；重新选择后读到独立D原文，不以HTML源码或401代替浏览器观察。
4. 已实际打开same-hub-before/old-generation原PNG，见旧G1和红色错误。ZIP实际按钮POST资源携旧KEY/H1/G1，而CLI已变G2；400为“本机文档选择已变化，请重新查看generation”，原始完整before/after已独立逐字段重比相等。
5. 已实际打开switch-hub-before/different-hub-equal-generation原PNG。旧H1/G2页面真实按钮POST仍携H1/G2，CLI当前H2且G2；400为Hub身份切换，完整before/after逐字段相等，未通过提交前fetch更换旧值。两目标及second-context清理原件均记录任务进程/端口退出。
6. 下节纯文本实测成立。该项分配为user-discovery-3，以上实际证据支撑其完整用户发现/旧页/认证/纯文本义务，判passed，只认领此检查。

## 纯文本原件和候选准备边界

两端原图中恶意项目名、dropped查询片段和原文都完整显示规定的 `<script>window.__smm_document_executed=true</script>` 及img src/onerror文字（另有legacy script），没有渲染为图片。每端ZIP四次原始evaluate分别对应new-project、query-snippets、original-chosen.txt、original-dropped.md，window/legacy未设置且main img/script节点为0；全network Local73条/Hub47条无触发路径。没有把web-hub.json清空后的network=[]当作全程证明。

独立按每端web创建回执ID提取两ZIP read响应资源，实际均chosen.txt、dropped.md各一次，与独立UTF8原件分别20/197码点相等；不是只读literal-display总结或条件截图存在。四字段正反自检有原输出。载荷实际在合法UTF8 dropped.md而非步骤文字的TXT后缀；SPEC B1/B8将md/txt同列纯文本入口，规定载荷和全部显示面/副作用检查都已到达，因此本轮不凭等价扩展名差异新增阻塞条件。

已读 `reviews/literal-preparation-review-v1.md` 交叉定位材料，其“可复用候选未独立强制两目标完整遍历”的准备缺口应保留并在新版关闭；本次正式复审仍以实际原件逐目标核验，两份目标确实到达，未发生其反例。准备缺口不改写成本次产品失败，也不据局部纯文本成功声称完整E1通过。
