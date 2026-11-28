# Windows最低Python3.11真实CI独立补充审查

结论：**passed**。只认领 `TC-008-minimum-installed-platform` 的 `minimum-installed-platform` 在真实 Windows CI 本次运行的子域：独立Local/Hub wheel、标准账户、最低Python3.11，以及普通/全局项目中的DOCX、XLSX、原生PDF和一页扫描PDF解析/OCR、项目检索、完整读取、原件下载和源移除后的旧引用保持。不是完整SC11、A11、C1、E/H/X、SC12或R008交付通过；没有制造native execute收据。

## 分配范围与依据

实际读取 `<CHECKOUT>/AGENTS.md`、`changes/008-document-format-support/spec.md`（A11与C1最低版本门）、`plan.md`的最低安装及2026-11-28续办约定；核对自然设计 `design-completion-sc11-minimum-v4/request.json` 及已审 `minimum-candidate-review-v4.md`。这次是独立外部CI执行补充审查，不以Mac调试推广Windows。三项oracle/包分离自检、Local/Hub两业务实例和两项采证故障控制分别可追溯。

真实head为 `6811238688674fbf156c0b0b7ee4af5ab58609ca`。核对本地此head与workflow、runner、标准用户脚本、业务/采证测试和采证器字节一致。实际CI [run 46093625455 / job 140819939210](https://github.com/yangbobo2021/smm-local/actions/runs/46093625455/job/140819939210)，Windows Server 2022 runner（系统观察Windows-10-10.0.20348-SP0）。官方元数据保存在 `ci-46093625455/run-latest2.json`。不改判旧run `46091817689` Windows两失败五通过。

## 官方归档与原件完整性检查

读取本次Windows目录的metadata、download、context、recovery和实际ZIP。artifact `15242352409`、名称 `008-minimum-Windows-46093625455-1`，实长 **2,014,744 bytes** 等于官方size；ZIP SHA256 `7538d102720afe5d6c5d5096656dec6fd3c0cf19139afa1cc135217a3a3efcd8` 等于官方digest。外层ZIP CRC全部通过，仅包含 `008-minimum.smm-evidence`。

实际解析密文封套头，run/job_key/head/artifact_name与本次官方上下文一致。公钥指纹 `3af8f1312a8487acb2d6e4c398a4de4c762461f8a1f923ea64088fbe0eca8d26` 与持久公钥及事前 `ci-keys/key-receipt.json` 一致；其自检时间2026-11-28T00:56:36.837127Z，早于run启动01:32:37Z。没有读取或复制private.pem，也未自行重复解密。认证解密由现有控制端recovery收据提供；本审独立检查其已解密原件及封套/manifest绑定，明确不冒称重新执行了GCM认证。

manifest原字节SHA256 `66cd0f31819f61108459256e24e6983826ba337d26c8b3fafc5526bf1c593b31` 与封套和recovery一致。**574个manifest成员全部重新读取，实际长度和SHA逐项一致**。不是只读recovered_verified摘要：本审重新解析372份JSON（包括合法UTF8 BOM），1份XML；打开20份DOCX、20份XLSX、2份wheel，共389个ZIP内部成员且CRC正确，内部XML可解析、wheel Python可作语法解析；40份PDF共60页均经PDFium实际打开、读文本并渲染；其余119份原始日志/文本/二进制均读取原字节。唯一报告JSON的evidence_sha256含所有574份观察摘要以及主要上下文/来源摘要，原文件未改动。

`collection.json.status=collected`只表示采证。业务通过另从原始pytest结果、JUnit、逐请求和独立源真值判断。两个故障控制的原始 `original preparation error\r\n\xff\x00` 30 bytes逐字保留；一个work/manifest尚不存在，另一个保留 `failure.json` 的failed及真实 `.bin` 原字节下载，不把opaque样本冒称Word。

## 原始JUnit与实际身份检查

实际打开 `platform/run.stdout`、空 `run.stderr`、`junit.xml` 和 `result.json`：stdout **7 passed, 1 warning in 49.01s**；JUnit **7 tests、0 errors、0 failures、0 skipped、49.001秒**，时间2026-11-28T01:34:21.607926Z。Local业务21.277秒，Hub25.381秒，其他是三自检与两故障采证。warning为Starlette TestClient弃用提示，不是失败或跳过。result真实exit_code=0。

标准用户控制端报告用户 `Smm008Mined70157e15`；实际业务观察为相同标准SID `S-1-5-21-1995136769-2955844435-1397185536-1003`，两产品均 `administrator_group=false`、`isolated=1`。产品身份代码实际执行whoami /user与/groups并拒绝Administrators SID，不以filtered管理员token的is_admin=false单独冒充标准账户。controller实际is_admin=false、pid4484；provisioner启动器pid1740不当作同一个解释器PID。

两产品均 **Python3.11.9，MSC64位AMD64，Windows**。Local/Hub分别位于自己的 `packages/local-env`、`packages/hub-env` 的Lib/site-packages。产品CLI全部246次请求实际使用准确环境Python `-I -X utf8 -m smm_local.cli/smm_hub.cli`，由冻结测试以 `not-source-cwd` 运行新子进程。测试驱动可读源码，不把驱动源码环境当产品安装环境。

## wheel来源和负控检查

实际wheel SHA256：Local `acf1aebf6ab4c535871a3d76b61a2b899d6ef73ea9e016434daf0657a9ea77d1`；Hub `1c2cb0194cc5d12e0e26b1bfdce3e81a09c5f0255c0d4af85edbe936c73b009b`。分别与target、原identity和实际wheel一致。Local48、Hub51个包资产/METADATA的实际安装摘要逐项等于本次wheel。Hub wheel无smm_local包，实际find_spec(smm_local)为None。

另核全部47个Local、50个Hub产品Python/HTML源映射。按照真实build_packages.py的Hub `_archive` vendoring及shim规则反查git head：文件内容一致，Windows checkout的CRLF与git blob LF仅换行不同；不把源blob与Windows wheel宣称全字节相同。安装与本次wheel为严格字节相同。准备日志七步全部exit0：准确3.11、构建独立包、从frozen lock导出documents依赖、分别require-hashes同步依赖、分别no-deps安装准确wheel。

两端真实错误SHA控制均exit1，原stderr为 `installed package bytes differ from wheel`；真实源码导入控制均exit1，原stderr为 `source package is not an installed origin`。没有只依赖代码中存在断言来宣称负控执行过。

## 16份源资料和完整读回检查

两端各普通/全局两个项目，每项目四种独立原件，共16份；另外各一无关联项目。实际项目返回分别ordinary/global/ordinary。对本次16个源输入及独立truth逐份读取：DOCX直接解析源OOXML，确认正文/插入修订、页眉页脚脚注尾注及顺序，删除修订/分隔符排除；逐表网格、横跨/纵跨和嵌套表均从源XML核对。XLSX直接核实际工作表名/序号、所有单元格。原生PDF核真实两页文字顺序，并从源PDF独立读取全部12张表的实际网格/全部格/页。源真值共**32张表、152个锚定格**，未使用产品输出重建期望。

所有246份CLI返回重新解析核对。文件全集每source恰为四个且唯一，各端8份ID无混用，所有资料ready、V1/P1、config_revision1；本次原件SHA对应自己的输入。每份独特锚点在所属项目搜索准确唯一ID；另外两个项目零命中；离线后在原项目仍命中。按实际原search ref逐份核**32份完整全文、64张完整表（304个返回格）、32份original-info及32份实际下载**。全文源单元完整且唯一、规定顺序正确，OCR仅容许空白差异；表格全部单元/维度/跨度/定位唯一对应源，document ID、origin、source、SHA、版本全部一致。

实际下载文件与各自本次输入逐字及SHA一致，不用info等值替代实际下载；两次16份下载分别保留。只与本次源输入比较，不与Mac或旧Windows尝试强求Office ZIP生成时间戳/全字节相同。

实际执行unlink后，保留的business-temp原件目录不含sources0/sources1源文件。沿**相同16个旧ref**的前后全文、全部表格和original-info逐项完全相同，版本仍V1/P1，原下载仍是各自同一原字节。断言不是动作后另取新引用来冒充旧引用。

## OCR原件人工画面检查

实际用PDFium把本次4份输入 `hubalphaocrpdf.pdf`、`hubbetaocrpdf.pdf`、`localalphaocrpdf.pdf`、`localbetaocrpdf.pdf` 渲染并查看。均为单页图像，原PDF文字层为空，画面分别清晰显示 HUBSCANALPHA、HUBSCANBETA、LOCALSCANALPHA、LOCALSCANBETA + `RETRY 73428`，第二行为 `CAPTURED ORIGINAL 12345.67`。没有只看OCR日志，也未给原件添加文字层。画面与独立truth及产品OCR全文一致。渲染只在内存完成，没有改动源PDF。

实际processing-status两端revision1、OCR ready=true/errors=[]，Tesseract5.5.4；可执行文件SHA `d850aa7062d036bdaeae45fee8301e7d8ba8083e510948c62d4db5dfb321754f`，chi_sim语言SHA `a5fcb6f0db1e1d6d8522f39db4e848f05984669172e584e8d76b6b3141e1f730`，eng SHA `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`。实际OCR结果locations标识method=ocr。

## 实际清理与限制检查

读取本次 `standard-user-controller.json` 实际查询值：`unexpected_remaining_pids=[]`、`account_absent=true`、`secondary_final=Stopped`，finished_at01:35:12.930844Z。这证明按临时账户枚举没有遗留用户进程、账户删除后实际查询不存在、Secondary Logon最终停止；不把Remove-LocalUser/taskkill/Stop-Service脚本意图或exit0代替观测。

另打开16个任务自己的cleanup与supervision原件，逐一核stopped=true、token及实际worker pid/created一致、supervision completed及Windows Job atomic=true。结合上述账户进程枚举，不只以启动器退出判定解释器/OCR结束。业务没有创建原生服务、监听器或防火墙规则；不宣称完成H5。证据及自有档案/下载/安装目录有意保留用于回收复核，不把保留证据误作残余运行进程。

没有工作区ACL移除后的独立ACL原文查询，因此不声称已经逐ACL验证所有授权撤销。该项不影响本次标准账户最低安装业务的判据，也不替代完整服务/权限验收。recovery.json的cleanup=null只说明回收器未另填清理摘要，不能据此否定或替代本次原始standard-user-controller及16份任务清理证据。

本审未运行产品业务、未修改产品/测试/原证据、未读取复制私钥，仅写本MD及同名JSON。上述分配子域未发现阻塞或产品缺陷；其他平台、本地Mac原生执行、完整基础包无extras接收、Web/stdio MCP/受管服务/六方向兼容及SC12完整采证义务继续由各自证据判断。
