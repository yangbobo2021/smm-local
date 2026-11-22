# SC8实际原件与当前适用性核验

人工验证项：TC-005-sc8-evidence

版本策略：历史业务事件保留原时间和包版本；本轮执行的是原件真实性、覆盖和当前适用性核验。不得用旧 passed 字段替代原始输入、响应、消息集合、服务身份或画面核对。

## 操作与预期

### full1

核对各入口实际引用和对应完整原文、同号碰撞；结合当前删除首/非首消息和Hub切换断言。

预期：新引用精确区分实际档案、消息和内容版本；同整数 ID 不误读，远端失败不读本机同号。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full2

核对split-scope完整标题/正文无越界，篡改/身份变化/参数冲突拒绝；实际查看范围画面。

预期：共享会话引用不读范围外正文；篡改、身份切换、消失消息和参数冲突明确失败。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full3

核对真实旧包读取和旧CLI/MCP/Web调用形式，E1三入口与E3/E4实际作用域原件。

预期：旧 CLI/MCP/Web 引用和调用形式继续可用；各 E1 三入口及 E3/E4 实际读取满足范围。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

## 原件与复核入口

场景原始目录（.acceptance-local/native-v1/AT-SMM-005/platform-debug/）：
- `mac-scope-run11`
- `linux-scope-run11`
- `windows-scope-run11`
- `linux-hub-scope-run11`
- `windows-hub-scope-run11`
- `mac-hub-scope15`
- `mac-run8`
- `linux-client-run8`
- `windows-client-run8`
- `linux-hub-service-run8`
- `windows-hub-service-run8`
- `mac-login-run11`
- `mac-hub-main15`
- `compat-run8`
- `linux-compat-run8`
- `windows-compat-run8`

各目录按 manifest/result 的实际业务时间和提交读取；忽略目录名暗示的版本。核对 commands/service-events、完整响应/消息、必要 PNG 和 trace，不仅读取 result.status。

补充：当前场景全部自动用例debug/execute及独立意见、work/final-package-comparison21.json、已保留的早期模块比较、原始平台独立审查。涉及d80到最终产品的标题修复用scope11/15；对账修复用reconcile21和当前CAS自动断言补足。

## 独立准备复审后的补充实测

- `TC-005-legacy-mcp`：真实最终包Hub及本机含同整数ID的本机A/合成V；分别启动真实0.4.0和最终包stdio MCP，用旧本机ID和旧Hub三参数读取。 预期：两个真实MCP进程均准确区分同号本机/Hub完整正文和来源；模块摘要匹配独立安装包。；本轮真实debug及execute原件分别位于debug-complete30-sc8和execute-complete30-sc8，原有平台事件仍保留原时间/版本。
