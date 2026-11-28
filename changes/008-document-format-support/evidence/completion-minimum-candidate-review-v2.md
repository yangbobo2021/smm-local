独立意见脱敏副本。私有原报告SHA256：9fdf9d3a8ec1cdb66281bf34a0bfeb4dd9c9ceb646c97bb3a38cf8360d06e356

# 最低Python安装候选 v2 独立复审

## 候选设计、实现及Mac调试

结论：`TC-008-minimum-installed-platform` 候选通过，仅认领 `minimum-installed-platform`。不是SC11、三平台或整个008交付通过。

实际打开项目AGENTS、008 intent/spec/plan，以及交付技能的design、implementation、reviewer原文。SC11判据由SPEC A11、C1的最低3.11最小业务及D2支撑；具体安装/输入/步骤放在自然设计，没有新增产品行为。完整C1多目标矩阵、基础无extras接收、Web/MCP/E/H/X和其余OS仍在对应专项，不由这个已准备环境的最小安装TC关闭。

冻结定义：`16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。
目标：`.acceptance-local/native-v1/AT-SMM-008/debug/debug-completion-sc11-minimum-v2/result.json`，SHA `62718839e75aeeecacd360a05d10c8d27776a647db18b3cee6e4ebc1e97d4257`。
自然设计：`case-design/design-completion-sc11-minimum-v2/request.json`；matching/result SHA `1c25f2ded4ac756989fe26f0ef3debed011b085e3f4f36a8f16bef473e388502`；runtime/result SHA `2cde829b6276a1b0f1a7b080a43fc8ed817e332a86dd7f85c86cb0037bfcbb30`。唯一分配项由目标的case_obligations确认。

95 bindings及对应95份冻结source副本、456 artifacts逐份重算SHA全部一致。原始nested stdout/JUnit为5 passed、0 failures/errors/skips，18.47秒：全文自检、wheel/driver分离控制、表格自检和Local/Hub两个真实业务参数实例。不是从外层exit0推断业务完成。

实际产品为各自隔离安装环境Python3.11.11、Darwin、UID501、isolated=1；控制器可用3.14，未冒充产品最低解释器。Local核48个安装文件（47源码/资产加METADATA），Hub核51个（50加METADATA），全部来自准确wheel；Hub不能find_spec Local。两个角色的错SHA、源码导入负控都exit1且错误原因准确。准备原commands/stdout/stderr摘要均匹配，locked requirements确由uv export --frozen导出并require-hashes同步，随后no-deps安装本端准确wheel。旧Mac-only测试git diff为空。

原始业务共246次新CLI（Local123、Hub123），16个原件及独立真值，32全文、64全表（逐格/跨度/独立位置）、32原件信息与32份实际下载。独立读取原始返回重核每份源单元/规定顺序、完整表维度/全部格/跨度/位置，输入与前后下载全部逐字一致。普通/全局各端四类目标分别核身份与来源，64次search中每端16次唯一正确命中和16次空负控。四扫描PDF经独立PDFium读取无原生文字层，四原生PDF均为两页且各页有文字；扫描原件实际识别结果精确匹配源真值。删除来源后任务目录没有残留源文件，全部旧ref读回与此前完整快照相同。

v1→v2 runner差异只增加uuid任务临时目录/位置收据，并把--basetemp移到准备目录下，证据目录外。未删断言、原件或负控；v1历史收集失败不改判。

## 边界反例与首个拦截

以下位置均为冻结 `tests/test_document_formats_minimum_platform.py`：

- 只处理首个适用文件：175–181先核每项目四个文件及唯一身份，217逐item核搜索命中；若虚报ready而读第一份，191/192身份或193独立源全文先拒绝。
- 漏第二表/工作表、重复第一格、错误跨度/位置：198核表全集/唯一性，205–208将每个源表按全部格/维度/跨度和源位置唯一映射，不能靠两个产品一致过关。98–107自检已证明维度/缺格/重复格及五种格字段错误被拒。
- 两端同时用同一错文档：各自原SHA和源真值不同，192–195、205、211、213对独立输入逐项核；仅两端相等无法通过。
- 把部分/重复/注入文字作为完整全文：38–56的完整单元/剩余文字/规定顺序检查拦截；自检正常布局4种通过、8种错序/重复/缺失/额外文字拒绝。OCR仅白名单空白归一并整段相等。
- 动作前状态遗漏：本TC前提为成功捕获，178逐份确认ready/V/P1；222删除全部16份源，223–225对每个旧ref验证全部既有结果不变。没有把动作后新进入ready的资料冒称动作前保护目标。

已覆盖这项最小业务的格式、角色和普通/全局差异后，仅增加同条件标识属于可选补测；不为完整C1额外认领覆盖。

## 跨平台CI准备静态核对

未执行Windows/Linux，不认任何一个平台passed。workflow目前准备三平台原生3.11和OCR材料，Windows通过固定entry、New-LocalUser+Users组、Start-Process -Credential启动，业务identity另拒绝管理员组并核实际SID；不是runneradmin filtered token。任务目录授予修改权，源码/基础解释器读执行，独立wheel读取ACL另处理。正常清理检查临时账户及其进程。成功路径未见必然不能执行的身份/入口错误。

collector保留附件里的实际输入、真值、原返回、下载及JUnit；pack以run/job/commit上下文生成文件manifest并加密，upload-artifact包含隐藏文件。公钥SHA `3af8f1312a8487acb2d6e4c398a4de4c762461f8a1f923ea64088fbe0eca8d26` 与已持久verified的key-receipt、公钥副本一致；没有读取或输出私钥。

发现一个本TC准备前提之外的具体CI故障证据缺口：OCR prepare的work为`.acceptance-local/008-minimum-materials`，内部失败日志写其`logs/`；collector只遍历`.acceptance-local/008-minimum`，只在最终materials JSON存在时另复制该JSON。若OCR prepare在写最终JSON前失败，后续minimum准备不会运行，collector可得到空目录，pack会以`empty evidence`拒绝；材料准备失败的原始日志不能随artifact追回。建议后续准备修订同时采集材料work的日志/既有材料收据，并保留workflow失败状态。这不影响本次已完成Mac业务的证据真实性，也不构成已执行其他OS的证据。

push路径过滤未包括产品源码、PS1及部分共用准备/加密脚本；workflow_dispatch可显式执行当前head，因此不是本次必然阻塞，后续扩大触发路径可作为可选维护项。

本轮只读产品、测试及原始证据；没有运行产品、修改实现或更改历史结论，只写本意见及对应JSON。
