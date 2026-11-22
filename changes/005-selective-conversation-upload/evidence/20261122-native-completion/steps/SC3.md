# SC3实际原件与当前适用性核验

人工验证项：TC-005-sc3-evidence

版本策略：历史业务事件保留原时间和包版本；本轮执行的是原件真实性、覆盖和当前适用性核验。不得用旧 passed 字段替代原始输入、响应、消息集合、服务身份或画面核对。

## 操作与预期

### complete-1

核对全局CLI完整G集合/重导入实际结果及当前全局唯一、未知归属不上传断言。

预期：全局项目唯一、与普通同级；缺 cwd 或归属不足不自动变成全局，也不发送正文。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-2

核对项目/全项目/明确关联查询中的G和待定独有正文，分别比较独立预期。

预期：按 A 查询默认不包含 G，全部查询包含 G 和待定；明确关联后才纳入 G。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-3

核对设备同名项目不同键、改名保持ID/关系及三类归属操作的首次/过期确认前后完整快照。

预期：同名设备项目分离，改名保留身份、规则与关联；扩大允许范围的归属变更需要有效确认。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-4

逐平台检查最小登记载荷键和合成唯一禁传标记，确认无会话/路径/内容旁路。

预期：最小登记不泄露未许可会话身份、标题、路径或内容；E1/E3/E4 实际路径均成立。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-5

核对真实归属传播原件和当前assign/map/merge/retry测试：禁止B无外发，允许B只补归属，A/旧引用保留且实体正文不增。

预期：已接收会话改归属到未允许项目时不外发该会话的新归属、指纹或正文；目标项目允许后补齐归属，保留旧归属和引用且不重复同版本正文；归属确认失败可核对重试，不以旧项目回执跳过。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### minimal

结合本项逐条判据核对下列原始实际事件及当前自动回归；共享SC1 TC-005-default及SC12实际载荷证据交叉核对，不重复伪造新用例；完整E1/E3/E4仍待矩阵审计。

预期：最小登记不泄露未许可会话身份、标题、路径或内容 原缺口只有获得对应原件及适用性依据才认领。

## 原件与复核入口

场景原始目录（.acceptance-local/native-v1/AT-SMM-005/platform-debug/）：
- `mac-run8`
- `linux-client-run8`
- `windows-client-run8`
- `linux-hub-service-run8`
- `windows-hub-service-run8`
- `mac-login-run11`
- `mac-hub-main15`
- `mac-global-cli11`
- `linux-global-cli11`
- `windows-global-cli11`
- `mac-scope-run11`
- `linux-scope-run11`
- `windows-scope-run11`
- `linux-hub-scope-run11`
- `windows-hub-scope-run11`
- `mac-hub-scope15`

各目录按 manifest/result 的实际业务时间和提交读取；忽略目录名暗示的版本。核对 commands/service-events、完整响应/消息、必要 PNG 和 trace，不仅读取 result.status。

补充：当前场景全部自动用例debug/execute及独立意见、work/final-package-comparison21.json、已保留的早期模块比较、原始平台独立审查。涉及d80到最终产品的标题修复用scope11/15；对账修复用reconcile21和当前CAS自动断言补足。

## 独立准备复审后的补充实测

- `TC-005-confirmation-bindings`：assign/map/merge各自预览后，独立改变目标或通过另一有效确认改变已有归属，上传代次不变，重放旧确认。 预期：旧确认均拒绝且当前全部持久快照不变；新预览不变，新确认可实际应用。；本轮真实debug及execute原件分别位于debug-complete30-sc3和execute-complete30-sc3，原有平台事件仍保留原时间/版本。
- `TC-005-forbidden-move-read`：A已上传取得原引用，assign/map/merge至禁止B，保持B禁止并立即读旧A引用、检查A/B及外发。 预期：禁止期间旧引用完整准确读回，A仍有/B无新归属，不发指纹正文，物理行保持。；本轮真实debug及execute原件分别位于debug-complete30-sc3和execute-complete30-sc3，原有平台事件仍保留原时间/版本。

新增禁止B原文核验覆盖两个会话各两条不同角色消息的两个旧会话引用的六次完整/按位置读取；在允许B前分别读回独立预期，并核对全部物理行。

修订取证方式：只用两个真实旧会话opaque引用，每个完整读两条并按start=end位置1/2各读一次，共六次读取；不要求不存在的Hub message.reference字段。
