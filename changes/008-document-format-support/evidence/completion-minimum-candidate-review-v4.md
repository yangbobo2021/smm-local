独立意见脱敏副本；私有原报告SHA256：af3ff9c890269cc00f51dd87288bb2e843d72a09d542b92be6e7cc409a29da7c

# 最低Python安装候选 v4 独立复审

## 候选设计、实现与Mac调试

结论：唯一`TC-008-minimum-installed-platform`候选通过，covers仅`minimum-installed-platform`。限定本轮Mac候选设计/实现及实际调试，不是Windows/Linux、完整SC11或008交付通过。

沿已实际读取的AGENTS、008 intent/spec/plan、交付技能design/implementation/reviewer约定，反查SC11来自SPEC A11/C1最低3.11最小业务及D2。v4自然设计明确-I隔离下显式UTF8协议设置、采证opaque字节真实后缀；没有降低原始业务预期，也没有新增必须产品行为。

定义SHA：`16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。
目标debug/result SHA：`afc873c659608890f40892846dcd9a59c1053bb80898b101a9897325456aa82f`。
设计result SHA：`2f8d93ed6ad867c9a7a0e808ed466b5520837db86e8b79686b6b805988853145`。
匹配result SHA：`e7af84f521c1b63049f83b6a99bd3a7a286b952ce7e98cfb804e265926ce6518`。
运行准备result SHA：`edc766874e21a1952378ba5291dee32911998e42757e8b8469d052aa4384da2d`。

96bindings及对应冻结source、457artifacts全部逐SHA匹配。相对v3冻结绑定仅三处改变：业务测试的CLI prefix显式-X utf8；custody固定opaque下载名从.docx改.bin；workflow paths扩充。本轮产品源码、wheel、原16份业务资料的生成规则、独立真值和业务断言未变。

原stdout为7 passed、22.44秒；完整JUnit为7 tests、0 errors/failures/skips、22.437秒。包括三既有自检、Local/Hub两实际安装业务实例、两个采证实例。两产品实际Python3.11.11、Darwin、UID501、isolated1，Local核48安装文件、Hub核51安装文件（各含本包全部资产与METADATA）。两wheel仍为：Local `fa6b038d35bf09cd8faed08440425bf06df463ef621244a250ed4550c89e1cc7`，Hub `843e34dcd478937ad6ae8ed4cf548b74693db88b3224279b2db292b2ba6c28b3`。

重新打开本轮246次CLI原始返回，全部实带-I和-X utf8；独立输入/真值16份、32全文、64全表（全部源格/跨度/位置）、32原件信息、32实际下载逐份复核。每份源文字和规定顺序完整、全部表唯一对应源真值，下载逐字等于输入；前后完整读回相等，测试外部源均已消失。

## Windows失败原件与UTF8修订

实际打开首轮CI `46091817689` 的Windows authenticated-incomplete/platform/run.stdout，SHA `71fd8444c0d28ec8ed11da3aa473049446f8aa0071e7dacfb8d12127d1e2b405`。原文2 failed、5 passed、3.90秒。Local/Hub都在project ensure-global输出中文JSON时，于Python3.11.9 cp1252编码器产生UnicodeEncodeError；两套文档业务尚未到达，不能称Windows安装业务通过。

原controller身份is_admin=false；两product identity为同一`S-1-5-21-1995136769-2955844435-1397185536-1003`、administrator_group=false、isolated1、各自独立site-packages。standard-user-controller记录failed、无残余PID、临时账户已删除。证明故障已进入真实独立标准用户，不是用管理员执行结果代替。

业务测试143行只将预期UTF8协议设置放入解释器参数，与现有`hub_documents_platform.Probe.argv`的-X utf8一致。-I隔离及非源码cwd保留；中文全局项目、UTF8解码、退出码成功和完整内容断言全部保留。原来-I会忽略PYTHONUTF8/PYTHONIOENCODING，显式参数修正测试的隔离运行配置，未将真实中文业务改成ASCII或删目标。不从Mac新绿推断Windows新参数已实际通过，也不宣称所有默认codepage/调用方式均已覆盖。

## 采证opaque样本修订

实际打开旧CI custody的source.docx：字节确为`exact synthetic original bytes`，SHA `46aaee4914ea18f1c75caf43585122c198f09291000416caa8aa743ce102ab72`，不是ZIP/Office。旧recover-controller2.stderr实际记录严格open_evidence在ZipFile读取处BadZipFile。将此测试控制样本名改为.bin，使后缀符合真实字节类型，不改严格Office读取器，也不移除或转换字节。

新custody24、51行使用source.bin；33行仍核含CRLF/无效UTF8/NUL的30字节stderr，34–38行仍核精确上下文/collected/真实存在状态，50–52行仍核业务failed、下载原字节及材料manifest。已实际打开两个保留evidence/collection.json与原日志：早期无work/manifest分支保持二者false，正常已准备分支均true，二者collected；已有失败分支保留source.bin且无伪Word文件，下载原字节准确。真实16份支持格式业务原件仍按DOCX/XLSX/PDF逐源核对，未改成.bin。

## 反例及实际断言边界

冻结业务测试177–183行核文件全集和唯一身份，219逐item核搜索目标，195核独立源全文；只首目标正确不能通过。200及207–210核全表集合/所有格/维度/跨度/位置和一一映射；漏第二表/工作表、复制首格不能通过。194–197、207、213、215按独立原SHA、源文字/表格与实际下载拒绝两端同错。全部16目标动作前ready/V/P1，224删除源后225–227沿旧ref逐份核完整前后状态，不以动作后新ready资料冒充保护前态。

采证若转码损坏在custody33行拦，错context在34行拦，伪称passed在37行拦，丢业务失败或下载在50–51行拦。独立raw/context/源真值均不取自待测输出。覆盖本项差异后，仅额外更换同条件标识属可选，不追加阻塞。

## CI准备静态核对及范围

workflow path过滤扩至minimum suite、PS provisioner、采集/加密脚本及相关证据测试。标准用户固定入口、实际身份断言和always采证主体未改；v3修复的材料准备早期失败原日志链保持。SC12正在独立审PEM换行/BOM适配，本项不审其完整性，不复制或读取私钥，不把authenticated-incomplete目录称完整回收验证。

Linux/Mac首轮CI完成与Windows失败分别保留，其他平台正式复审及新Windows业务运行需各自原件。完整基础无extras接收、SC11发现性/兼容、Web/MCP/E/H/X继续单列，不由本TC关闭。

本轮只读业务/测试/原件，未运行或修改业务，未复制私钥；只写本意见MD及唯一JSON。
