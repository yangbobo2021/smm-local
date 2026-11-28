# macOS CI 最低 Python 3.11 独立复核

结论：**passed_scoped**。仅通过 SPEC A11/C1 对 macOS 最低 Python 3.11 的独立双包安装与最小文档业务子域。这是额外真实 macOS CI 原件复核，与本机 native Mac 证明分开；未登记或伪造 native execute。

- Run：46093625455；Job：140819939503，minimum (macos-15)。
- Head：6811238688674fbf156c0b0b7ee4af5ab58609ca。
- 官方业务步骤于 2026-11-28T01:33:37Z–01:34:17Z 执行；JUnit 7 passed、0 failed/error/skipped，39.292 秒。
- Artifact：15242154313；2,132,274 字节；有效期至 2026-12-28T01:34:18Z。
- ZIP SHA256：0ad5876cd210612b9ebd766dfec2d0c185de7c1d4c8a115594db70e79b09cb89。
- Manifest SHA256：52a842e56dc04ca210a76c72af8460a84f85bd4c57d57015fd09bbfa9095b5c8。

## 官方原件、回收与完整性

实际读取官方 run-latest2.json、三份 metadata、context、下载记录、原 ZIP、recovery 与 recovered_verified 回执。run/job/head/artifact/context 一致，ZIP 实际长度及 SHA 与官方 metadata 一致，ZIP CRC 和所有成员读取成功。前两次各 45 秒下载 TimeoutExpired 与 partial/stdout/stderr 保留；第三次 90 秒限时内下载成功。这是同一 artifact 的下载恢复，不是业务重跑。

逐一重新读取 manifest 的 **573 文件、4,030,933 字节**，全部长度/SHA 相符。类型计数：371 JSON、67 stderr、47 stdout、40 PDF、20 DOCX、20 XLSX、3 TXT、2 WHL、2 BIN、1 XML。JSON/XML实际解析，Office/WHL ZIP CRC和成员实际读取，Office XML/relationships实际解析；40 PDF通过Poppler打开，共60页；TXT实际UTF-8读取，日志/不透明BIN逐原字节读取。非UTF8故障stderr没有伪装成文本或Office文件。

控制端key-receipt为persisted_verified，记录在业务启动前00:56:36Z完成持久私钥重载小样。按授权只读该摘要，未读/复制private.pem，未重复解密。GCM成功依赖已给回收回执；本复核独立核明文manifest全成员，未将纯job success当回收通过。

## 指定候选与独立安装

读取AGENTS.md、SPEC A11/C1、PLAN最低门、design-completion-sc11-minimum-v4/request.json和candidate-v4设计意见。实际测试/采证/入口脚本及原件生成器均逐字比对本CI指定head，不从另一次尝试重造输入或更换真值。

两个产品环境实测均为 **macOS 15.8.2 arm64、Python 3.11.9、UID 501**，各自prefix与site-packages完整分离。产品246次真实CLI调用均显式-I -X utf8，按head驱动从非源码cwd新进程运行。Local完整47模块/静态资产及METADATA共48项、Hub完整50资产及METADATA共51项，逐项重新对真实wheel字节；两包全部.py/.html集合也重建对应至指定head源码，Hub共享代码按构建映射核对。Hub wheel无smm_local包，实际find_spec不能发现Local。

- Local wheel SHA：22859cff6d08ba38d75b8998005e879c164826353dbaae0fb86c5973d84dd5f2。
- Hub wheel SHA：e7040fbc585be53416fb99e41203d5248c185e9328f07aea8a85330d53d89355。

实际build、独立安装、含hash锁定documents依赖同步、最后准确wheel无依赖安装均有原命令/退出0及日志SHA；全部日志摘要重新核对。两端错误模块SHA、PYTHONPATH源码导入负控都真实exit1并保留明确原因。通过不是单凭import或requires-python。

## 完整业务、独立真值与源离线

两端各有普通项目、全局项目和无关联负控项目；普通/全局各DOCX、XLSX、原生PDF、单页扫描PDF，共 **16份不同源原件与16份独立真值**。源定义先于解析；DOCX/XLSX真值词实际核入原XML，原生PDF词实际核入独立Poppler提取文本。扫描原件无可直接提取文本，实际为图像PDF。两端配置revision1、四格式能力和OCR check ready，未跳过真实OCR。

逐CLI原始argv/exit/stdout/stderr，重新从响应链配对所有目标：**32次完整全文、64份全表响应共304格、32份original-info、32份真实下载**。逐份核文档/项目/来源/origin/V1/P1/格式/原SHA；全文单元必须各出现一次，无额外单词、金额或缺词，按B2明定顺序而不强制无契约的部件分隔；删除/排除文本不得出现。OCR仅去空白后全文与独立真值完全相同，金额与锚点准确且方法为ocr。

所有表按独立源维度、全部单元文字、行列与合并跨度唯一匹配，表集合无缺漏/重复。304格定位另独立核对：DOCX部件与精确table/row/cell路径，XLSX sheet/坐标与文本偏移，原生PDF页/旋转/尺寸/文本偏移；其中144个原生PDF格的bbox逐一对照源绘制几何，误差小于1e-9。32份实际下载逐原字节与本CI对应输入比较，不从摘要代替下载。

原始驱动在首轮后对16个测试自有源文件逐unlink；随后实际CLI仍使用首轮旧ref。复核逐目标完整比较删除前后旧ref、全文、全部表、original-info相等，保持V/P及结果字节；两端completion明确source_files_unavailable。32次合法唯一项目命中和32次跨项目/无关联零命中逐响应重核。源字节/mtime不变断言保留在已比对head驱动；本审查不是系统调用级无回源/无网络审计。

## 扫描原件实际视觉核验

四份输入分别用Poppler在内存实际渲染并查看整页，不以OCR输出或回收摘要代替原图：

| 原件 | 第一行 | 第二行 |
|---|---|---|
| localalphaocrpdf.pdf | LOCALSCANALPHA RETRY 73428 | CAPTURED ORIGINAL 12345.67 |
| localbetaocrpdf.pdf | LOCALSCANBETA RETRY 73428 | CAPTURED ORIGINAL 12345.67 |
| hubalphaocrpdf.pdf | HUBSCANALPHA RETRY 73428 | CAPTURED ORIGINAL 12345.67 |
| hubbetaocrpdf.pdf | HUBSCANBETA RETRY 73428 | CAPTURED ORIGINAL 12345.67 |

页面清晰、两行独立可读，与各自冻结真值和实际OCR读回一致。本项仅一页清晰英文扫描，不能延伸为A5完整中文、多页或扫描网格质量通过。

## 采证故障控制

两个实际custody用例及保留目录均打开：材料尚无manifest/target时，准确保留original preparation error后的CRLF、FF、00原字节及上下文；有业务failed/opaque下载时，failed记录、准备日志与source.bin原字节都保留。collected只作采集事实，未改判故障控制为产品业务passed。

## 范围与局限

只认本次macOS最低3.11安装、创建端四类材料解析/OCR、项目检索、完整文本/表/原件及已捕获快照源删除后的读取业务。完整SC11发现性/旧升级、E1/H服务、Web/MCP、X1六方向、SC12、Linux/Windows最低门均不由本报告关闭。POSIX身份依据是真实非0 UID，不以此推断受管服务身份或权限。未运行产品业务、未重新下载、未修改产品/测试/原证据；审查仅写本报告与同名JSON。Office ZIP只与本CI原输入及下载比较，不要求跨尝试日期字节相同。

未发现阻碍该限定子域通过的缺陷。结构化JSON包含逐读回明细、实际复核指标、官方job、下载历史、审阅输入SHA与全部573 manifest成员SHA。
