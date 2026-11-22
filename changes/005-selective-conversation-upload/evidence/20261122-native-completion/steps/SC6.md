# SC6实际原件与当前适用性核验

人工验证项：TC-005-sc6-evidence

版本策略：历史业务事件保留原时间和包版本；本轮执行的是原件真实性、覆盖和当前适用性核验。不得用旧 passed 字段替代原始输入、响应、消息集合、服务身份或画面核对。

## 操作与预期

### full1

比较三入口本机未上传独有/Hub直接关联独有集合，核对无二层和本机关联；结合查询中变更两窗口自动断言。

预期：CLI/MCP/Web 默认包含本机未上传及 Hub 直接关联命中，范围使用同一 Hub 快照并排除二层和仅本机关联。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full2

核对三入口显式本机零Hub请求及G/待定/插件来源；全部联合查询Hub来源。

预期：仅本机使用本机关联且不请求 Hub；全部查询包含本机 G、待定和非上传来源以及 Hub 来源。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full3

核对当前会话跨档案排除、各端N和去重不补召回的当前回归及独立候选集合。

预期：当前会话同源副本均按约定排除，两端候选各至多 N，去重不足不扩大召回。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full4

逐E1三入口核对各自实际取得的本机/设备B/合成Vibe原文；核对实际E3/E4范围与读取。

预期：各 E1 平台三入口分别读回本机、其他设备及合成 VibeInsight 原文；E3/E4 服务范围与读取一致。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

## 原件与复核入口

场景原始目录（.acceptance-local/native-v1/AT-SMM-005/platform-debug/）：
- `mac-run8`
- `linux-client-run8`
- `windows-client-run8`
- `linux-hub-service-run8`
- `windows-hub-service-run8`
- `mac-login-run11`
- `mac-hub-main15`
- `mac-scope-run11`
- `linux-scope-run11`
- `windows-scope-run11`
- `linux-hub-scope-run11`
- `windows-hub-scope-run11`
- `mac-hub-scope15`
- `mac-entrances-run10`
- `linux-entrances-run10`
- `windows-entrances-run14`

各目录按 manifest/result 的实际业务时间和提交读取；忽略目录名暗示的版本。核对 commands/service-events、完整响应/消息、必要 PNG 和 trace，不仅读取 result.status。

补充：当前场景全部自动用例debug/execute及独立意见、work/final-package-comparison21.json、已保留的早期模块比较、原始平台独立审查。涉及d80到最终产品的标题修复用scope11/15；对账修复用reconcile21和当前CAS自动断言补足。
