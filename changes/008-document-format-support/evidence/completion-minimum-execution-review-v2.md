# 最低 Python v2 正式执行独立复审

结论：**passed**，范围仅 AT-SMM-008 / SC11 / TC-008-minimum-installed-platform 的本次Mac普通用户最低3.11安装业务，唯一认领 `minimum-installed-platform`。此次仅检查证据和源码，未执行产品、修改业务、复制私钥；v1和历史失败原样保留。

## 目标、基线与绑定

沿已实际读取的AGENTS.md、008 intent/spec/plan和交付技能Reviewer规则，核SPEC A11/C1最低版本最小业务及定义000003（SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`）。本次读取自然设计v4及另一位独立候选Reviewer的已登记意见，不用其结论代替本轮原件复核。

目标：.acceptance-local/native-v1/AT-SMM-008/execute/execute-completion-sc11-minimum-v2/result.json，SHA256 `e3e16f8daa141f375259e1f36573887d44696fe62dce074673320d62f3000e27`。96个bindings、361个artifacts全部实际读取并核SHA，无缺失/差异；与candidate-v4运行绑定完全一致。case_obligations仅分配minimum-installed-platform。

## 本次原始结果与精确时长

实际打开TC目录中attachments/installed-minimum/{run.stdout,run.stderr,junit.xml,result.json,temporary-location.json}及外层执行记录。stdout为7 passed、1个Starlette弃用警告、19.05秒；JUnit为7 tests、0 errors、0 failures、0 skipped，精确19.051秒。Local业务8.206秒、Hub业务10.481秒，两采证自检0.044/0.033秒。外层entry实际exit0，外层stdout/stderr空。未借用v1的18.853秒或v4调试的22.437秒。

## 变更与UTF-8启动原argv

逐行对比debug-completion-sc11-minimum-v3/source冻结原件：minimum_platform.py仅prefix增加`-X utf8`及两行说明，custody仅生成及断言的下载名source.docx改source.bin，workflow仅扩充触发路径。产品、两个wheel、所有内容真值断言保持原版。

本轮246份原始产品命令逐一核为 `[准确安装python, -I, -X, utf8, -m, 对应smm_* .cli, ...]`，全部exit0、stderr空；两份ensure-global返回仍含中文“全局项目”，没有删中文或放松输出/内容断言。源码外cwd、隔离模式和普通身份检查均保留。本轮只证明Mac实际启动及业务结果；Windows旧失败不因该修改被追认。

## 安装字节、解释器与身份

target.json仍指向minimum-mac-prep-v1中的两个独立安装。两端实际identity为Python3.11.11、Darwin/macOS15.3.1 arm64、UID501、isolated1；不同prefix/site-packages，不能由控制器3.14冒充最低版本。

Local wheel SHA `fa6b038d35bf09cd8faed08440425bf06df463ef621244a250ed4550c89e1cc7`，Hub wheel SHA `843e34dcd478937ad6ae8ed4cf548b74693db88b3224279b2db292b2ba6c28b3`。两个ZIP CRC通过；Local47/Hub50产品源码资产映射、完整wheel成员和含METADATA的Local48/Hub51安装文件，实际源/wheel/安装/运行identity逐SHA一致。Hub wheel无smm_local且隔离探针不可import Local；两端错误SHA与源码导入负控各实际exit1，原诊断与预期含义相符。

## 全部原件、真值与下载

实际打开本轮16份inputs与全部truth，解析4份DOCX ZIP/XML、4份双sheet XLSX ZIP/XML、4份两页原生PDF及4份单页纯图像扫描PDF。原生PDF的源全文可独立读取，扫描页文本层为空；四扫描PDF与前轮已渲染查看的原件逐字相同。

跨尝试准确性：truth全部逐字相同、8份PDF原件逐字相同；8份DOCX/XLSX重新生成后的整体ZIP SHA不同，逐成员名称和payload完全相同，ZIP成员时间戳由09:10段变为09:29段。这里的相同是源内容/fixture/预期相同，**不声称16份跨尝试原SHA全部相同**。本轮下载均按本轮各自原件SHA和字节核验，未重造旧原件。

逐一重核246份CLI返回：64次搜索（32正确命中、32其他项目零命中），32次完整全文，64次完整全表，32次原件信息，32次真实下载，及项目/配置/状态/add/refresh/files。每端普通/全局各四类文件，8份ID唯一；合计16个目标没有遗漏第二份或第二表。全文源单元完整唯一，无多字/重复/遗漏；DOCX正文与PDF规定顺序正确，OCR仅空白归一后逐字正确。表格全集、所有格值、行列、合并跨度和表定位与独立truth完全一致。额外按源部件路径、A1及源PDF页尺寸/几何核304格位置：DOCX64、XLSX96、PDF144。

每份origin/document/source、V/P1、ready、原SHA/长度/可用性均正确；32份实际下载包含本轮原字节。16份源路径实际均不存在，沿before同一旧ref的after全文/表格/信息（包括argv及响应）完全保持，原件下载相同，搜索仍命中同一目标。两个OCR配置均revision1且实际ready。

## 两个真实采证子进程自检

本次JUnit显示两项均真实执行。打开temporary-location指定持久目录的两个控制原件：

- retains0：work/manifest/target尚未存在；collection仍保存准备stderr及context。stderr精确30字节，含CRLF、FF与NUL，SHA `1c4c628dbacb5f7b1b000a06ededc9f6842de19455fec812614b3f7c01fbef9e`，无转码。
- keeps_b0：failure.json真实status=failed、materials.json、上述准备stderr及platform/attachments/downloads/source.bin同时保留；bin逐字为固定不透明控制材料，原source.docx不存在，没有将它误称合法Word。

两context均精确为run_id=123、job_key=minimum-Windows、40个a的commit及artifact_name=008-minimum-Windows-123-1。这是控制输入而非Windows业务身份。collection均只写collected，work与manifest存在值分别false/true，未把采证完成当业务passed。

## 限定与历史

仅本次Mac最低版本业务passed。Windows/Linux新CI、其他OS、完整SC11、SC12文本适配、无extras基础接收、Web/MCP/E/H/X、完整OCR质量/安全/资源矩阵均未据本项判通过。v1与Windows历史失败不改判；源码相同不替代其他平台原件。没有读取或复制任何私钥。
