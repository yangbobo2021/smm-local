# SC5实际原件与当前适用性核验

人工验证项：TC-005-sc5-evidence

版本策略：历史业务事件保留原时间和包版本；本轮执行的是原件真实性、覆盖和当前适用性核验。不得用旧 passed 字段替代原始输入、响应、消息集合、服务身份或画面核对。

## 操作与预期

### complete-1

核对真实停止前后差集和旧引用原文，禁止A新标记不在Hub正文。

预期：停止 A 保留已接收副本和旧引用，A 新禁止内容不进入 Hub。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-2

核对实际HTTPS隔离记录：A停止但B/其他设备/合成VibeInsight仍可查询且原状态不变。

预期：其他项目、其他设备和 VibeInsight 原有状态不被该设备规则关闭。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### complete-3

核对真实旧包未迁移/迁移同设备两种状态的接受/拒绝请求、旧读取及当前允许正控。

预期：已迁移设备旧式正文请求拒绝，当前新规则仍可接收有效请求；未迁移设备继续兼容。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### legacy

结合本项逐条判据核对下列原始实际事件及当前自动回归；SC10 TC-005-register、实际旧包组合及SC2旧请求确认共用证据；此处不重复伪造相同身份。

预期：已迁移设备旧式正文请求拒绝 原缺口只有获得对应原件及适用性依据才认领。

## 原件与复核入口

场景原始目录（.acceptance-local/native-v1/AT-SMM-005/platform-debug/）：
- `isolation-run9`
- `compat-run8`
- `linux-compat-run8`
- `windows-compat-run8`
- `mac-run8`
- `linux-client-run8`
- `windows-client-run8`
- `linux-hub-service-run8`
- `windows-hub-service-run8`
- `mac-login-run11`
- `mac-hub-main15`

各目录按 manifest/result 的实际业务时间和提交读取；忽略目录名暗示的版本。核对 commands/service-events、完整响应/消息、必要 PNG 和 trace，不仅读取 result.status。

补充：当前场景全部自动用例debug/execute及独立意见、work/final-package-comparison21.json、已保留的早期模块比较、原始平台独立审查。涉及d80到最终产品的标题修复用scope11/15；对账修复用reconcile21和当前CAS自动断言补足。
