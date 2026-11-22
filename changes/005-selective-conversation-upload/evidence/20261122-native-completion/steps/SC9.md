# SC9实际原件与当前适用性核验

人工验证项：TC-005-sc9-evidence

版本策略：历史业务事件保留原时间和包版本；本轮执行的是原件真实性、覆盖和当前适用性核验。不得用旧 passed 字段替代原始输入、响应、消息集合、服务身份或画面核对。

## 操作与预期

### full1

核对实际断线三入口A仅返回A，排除D/全局并显示Hub未覆盖，不能把零命中当未执行。

预期：Hub/项目范围解析失败时按 A 仅返回本机 A，不扩本机关联、不退全部，并说明未覆盖。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full2

核对三入口offline-all及重连恢复，显式本机范围独立不变。

预期：全部查询退本机全部；恢复后再次联合，显式本机不变，成功零命中与未执行区分。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full3

结合当前单端候选/全文失败、缺全文排除、双端失败的实际自动结果核对覆盖字段。

预期：有效快照后单端失败如实部分覆盖，全文缺失排除不完整候选；双端失败报错。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

### full4

核对当前无效参数报错断言及逐E1三入口真实断线/重连查询和原文；查看断线覆盖画面。

预期：无效参数直接报参数错误，不能冒充 Hub 失败扩大范围；各 E1 三入口实际断线恢复可复核。 核验时保持真实业务原时间/版本；图像判断须查看原图，网络/先后顺序以轨迹或实际断言定位。

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

各目录按 manifest/result 的实际业务时间和提交读取；忽略目录名暗示的版本。核对 commands/service-events、完整响应/消息、必要 PNG 和 trace，不仅读取 result.status。

补充：当前场景全部自动用例debug/execute及独立意见、work/final-package-comparison21.json、已保留的早期模块比较、原始平台独立审查。涉及d80到最终产品的标题修复用scope11/15；对账修复用reconcile21和当前CAS自动断言补足。

## 独立准备复审后的补充实测

- `TC-005-empty-coverage`：有本机/Hub正控，按项目/全部查询不存在词，再真实令Hub请求失败，并显式仅本机。 预期：同为[]时coverage分别complete/unavailable/not_requested，成功无失败原因，未执行有具体原因，且成功确实调用Hub搜索。；本轮真实debug及execute原件分别位于debug-complete31-sc9和execute-complete31-sc9，原有平台事件仍保留原时间/版本。

A9额外E1实际空查询：TC-005-empty-mac/linux/windows分别执行三入口all/project，正式原件在execute-complete31-sc9各TC/probe，查看无命中及双方已检索PNG并结合请求/响应/轨迹。

Windows空查询为独立人工长轮TC-005-empty-windows，按SC9-windows-empty.md实际外部运行并记录；full2核验须加入该本轮原件，不能用原自动超时或Mac/Linux代替。
