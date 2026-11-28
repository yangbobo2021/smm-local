独立意见脱敏副本。私有原报告SHA256：7dae53fbdc232a08cdad819db2d862031a88796ef3e90098eda17e5f7969997c

# 最低Python安装候选 v3 独立复审

## 候选设计、实现及Mac调试

结论：唯一`TC-008-minimum-installed-platform`候选通过，covers仅`minimum-installed-platform`。仍只认当前Mac普通身份实际运行，不认Windows/Linux、完整SC11或整个008交付。

沿实际已读AGENTS、008 intent/spec/plan及交付技能design/implementation/reviewer约定核验。SC11判据由SPEC A11、C1最低3.11最小业务及D2支撑；本版自然设计只新增采集故障证据的检查，没有改变产品承诺或降低预期。定义SHA仍`16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。

目标debug/result SHA：`5f60e8445f03fa0c2c5fdb4f997daf3df1b4ee3cacd4aff9299a939c1d8756b4`。
设计result SHA：`4009a84946ab1751c8e5bc1a09edff9eada3aa6cbc5b3e25ce009b2630a55932`。
匹配result SHA：`042a7f9d5c3af3a4c0d49b24e30b5dd40bf2f213b656cea210893406b46fc146`。
运行准备result SHA：`59dc611e429a1184b810f37ba1f0e91c0696fc7c564663ceb2da78f83e93940b`。

本轮96个绑定、96份冻结source副本和457份artifacts逐份重算SHA一致。相对v2冻结绑定，只有`document_formats_completion_evidence.py`、`document_formats_minimum.py`变化，新增`test_document_formats_minimum_custody.py`；产品源码、业务测试、Windows provisioner、workflow及wheel没有改变。runner只增加实际执行custody测试文件。

原始stdout/JUnit明确7 passed、0 skipped/failures/errors、19.552秒：既有三自检、Local/Hub两个业务实例、新增两个采证实例，全部到达。不是凭外层exit0或调试绿色推定。

实际两产品均3.11.11、Darwin、UID501、-I；Local48安装文件及Hub51安装文件核wheel（分别47/50源码资产加METADATA）。准确wheel SHA分别：

- Local：`fa6b038d35bf09cd8faed08440425bf06df463ef621244a250ed4550c89e1cc7`。
- Hub：`843e34dcd478937ad6ae8ed4cf548b74693db88b3224279b2db292b2ba6c28b3`。

重新打开本次原始CLI响应与独立输入/真值，重核246CLI、16原件、32全文、64全表及所有源格/跨度/位置、32原件信息和32实际下载。原件/前后下载逐字一致，每份原全文源单元及规定顺序准确，前后完整读取相等，全部测试来源已不存在。不是用v2原件替代本轮业务证据。

## 早期失败采证修订

v2发现的问题对应SPEC证据段与PLAN的always收尾保留失败原件要求。实际workflow将材料输出至`008-minimum-materials.json`，材料work是同名去扩展名目录。collector本版32–39行遍历其中logs，即使最终manifest/target不存在仍复制原始字节；42–47行始终写采集事实，状态仅`collected`，记录work/manifest/logs是否真实存在。既有业务失败、原件下载及材料manifest复制保留。输出在源work内时显式拒绝，避免自递归。

新增custody测试29–31行真实执行独立collector子进程，不是只调用辅助函数。两种动作前状态分别是：只有材料logs且work/manifest不存在；已有业务失败、下载和材料manifest，同时有材料logs。第33行与独立30字节raw比较，第34–35行精确断言context，第37–38行断言collected及真实存在状态，44–45行核早期输出全集，50–52行核业务failed/下载字节/材料值。

已实际打开本轮保留的两个`evidence/collection.json`、context和原stderr：早期分支为work=false、manifest=false、logs=true，已有准备分支三个均true；两者均collected。30字节stderr包含CRLF、无效UTF8和NUL，SHA均`1c4c628dbacb5f7b1b000a06ededc9f6842de19455fec812614b3f7c01fbef9e`；context完全匹配固定独立预期。已有业务失败仍failed，下载字节准确。这个fixture的RUNNER_OS=Windows只用于context字符串控制，实际测试运行在Mac，不充当Windows业务证据。

只正常分支有效会被custody第33或37–38行拦截；转码丢字节在33行拦；错上下文在34行拦；丢已有失败或下载在50–51行拦；把采集伪称业务passed在37行拦。独立raw/context/失败常量可拒绝两边同错。v2指出的具体早期失败日志缺口已覆盖，不修改v2历史意见。

## 既有真值和目标边界

冻结业务测试未改。175–181行核两端每普通/全局项目四目标全集与唯一性；217及193行逐目标搜索身份和独立全文可拒绝仅首目标成功。198及205–208行核表全集/唯一性、所有格/维度/跨度和源位置，漏第二表/工作表/重复首格均不能过。192–195、205、211、213行对独立原SHA、源文字、全表与实际下载拒绝两端同用一个错文档。

全部16目标在删除源之前逐份确认ready/V/P1；222行删除源，223–225行全部旧ref逐份完整读回并与动作前快照相等。全文合法排版与错序/重复/缺失/额外词、表格维度/格字段/缺格/重复格自检仍实跑。已覆盖本最小业务的角色/格式/普通全局差异后，不因增加同条件标识而阻塞。

## 跨平台CI静态检查

当前workflow参数与新增materials工作目录推导一致，always collector现在至少包含collection事实且已有日志实际复制，pack不再因本轮所发现的早期缺manifest/target分支而得到空目录。业务或准备失败状态仍由原失败step及原失败文件保留，collected不改变它们。

Windows固定入口、独立New-LocalUser/Users组、credential进程和无Administrators组的实际SID校验未改；没有把runneradmin filtered token当标准账户。上下文加密、upload-artifact路径和已持久verified的公钥receipt未改；公钥SHA仍`3af8f1312a8487acb2d6e4c398a4de4c762461f8a1f923ea64088fbe0eca8d26`且匹配。未读取私钥。

未执行Windows/Linux或本轮真实CI上传/回收，不把静态检查或Mac的context fixture认作平台passed。完整Web/MCP/E/H/X、基础无extras接收及完整SC11均继续单列。push path过滤的后续维护建议不变，workflow_dispatch可显式运行当前head。

本轮只读产品/测试/证据，未运行产品或修改实现；只写本意见MD及对应唯一JSON。
