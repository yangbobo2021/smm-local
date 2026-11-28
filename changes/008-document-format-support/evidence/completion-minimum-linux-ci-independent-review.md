# Linux 最低 Python 安装 CI 独立复审

结论：**passed**，仅限 SPEC A11/C1 的 Linux 最低 Python 3.11 独立安装业务子域（`TC-008-minimum-installed-platform` 的 Linux 实跑）。本次为获准的外部 CI 独立补充，不创建或冒充 nativeexecute 收据，不据此关闭完整 SC11、E/H/X、系统服务、完整 SC12 或整项008交付。

## 依据与实际运行身份

只读审阅 AGENTS.md、008 SPEC/PLAN、v4 自然设计和已审候选、workflow、平台业务测试/采证测试及准备/入口/回收代码。自然设计定义摘要为 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`；最低门要求各系统依赖安装、DOCX/XLSX/原生PDF最小提取及一页真实OCR，不要求在本门重跑全部 E/H/X。未更改需求或验收条件。

官方 run `46093625455`，job `140819939488`（`minimum (ubuntu-24.04)`），head `6811238688674fbf156c0b0b7ee4af5ab58609ca`；当前 checkout HEAD 相同。run-latest2 的 job 元数据与 workflow 的 Ubuntu24.04 runner 选择对应，POSIX业务、采证、加密及上传步骤均成功。Windows专用步骤是平台条件跳过；业务 JUnit 没有 skip。实际控制端和两个产品身份均观测为 Linux、UID1001，内核/用户态字符串为 `Linux-7.0.0-1020-azure-x86_64-with-glibc2.39`。

原始 `run.stdout`：7 passed、1项 Starlette弃用提示、30.83秒。原始完整 JUnit：7 tests、0 errors、0 failures、0 skipped、30.835秒，包含3项预期/安装控制、Local/Hub两个业务实例及两个采证故障实例。原 `run.stderr` 为空；`result.json` exit_code=0。

## 官方原件与完整性

artifact `15242620319` 的第二次官方下载 ZIP 为 **2,139,811字节**，SHA256 `36a3eb9cba48b3fc4b5cabd543b3a8b7bfb558da9ccdad5cf4dfc4e6da8a1fa0`，与 metadata-2 的大小、digest、run、head、artifact名称一致；ZIP唯一成员 `008-minimum.smm-evidence`，CRC重检通过。首次45秒超时及1,899,486字节 partial 原样保留，未把残片当成功原件。

独立读取 envelope header，context 精确对应本run/head/job/artifact，manifest SHA `17d60bffc87cbc6712d0372cd03e1784afc1d7dec0bfd864b9a1a0efc25213a4`。公钥原字节SHA与事前 `key-receipt.json` 均为 `3af8f1312a8487acb2d6e4c398a4de4c762461f8a1f923ea64088fbe0eca8d26`；事前receipt时间00:56:36Z早于run开始01:32:38Z。已检查现有 `recovery.json` 为 recovered_verified 及其 verifier 对GCM/AAD/context/manifest绑定的实现；本审查未读取或复制 private.pem，未再次执行需私钥的解密，故不声称独立重演GCM认证。

对 manifest **全部573个成员**逐一读取实际字节、长度及SHA，全部匹配；成员集合与 recovery.opened 精确一致。独立重新打开371个JSON、42个Office/wheel ZIP（全部CRC及XML）、40个PDF（所有页实际渲染）、120个其余文件的全部字节。恢复目录仅另有 manifest 与回收receipt两个控制文件，未发现丢失成员或打不开的支持格式。不能只凭回收摘要认定此项通过。

## 最低解释器与双包隔离

准备记录的7条命令均exit0；先导出 frozen documents 依赖，再在两独立环境 `uv pip sync --require-hashes`，最后对各自准确wheel `--no-deps` 安装。两个产品实际均为 **Python3.11.18**、isolated=1、UID1001，各自 executable/prefix/site-packages 对应本端独立环境。

- Local wheel SHA：`429a9bfa63414f448b908be4b3b518d2f5b5b776dc39a0b4d124441e58526c21`；本包全部48项文件及METADATA逐SHA与wheel匹配。
- Hub wheel SHA：`bdded2167372c6ff14b272e94d87d210ccfdfe95d76527e2deb9aef83107b143`；本包全部51项文件及METADATA逐SHA与wheel匹配。wheel无smm_local，实际Hub find_spec(smm_local)为None。

两端错误安装SHA负控都exit1并明确 `installed package bytes differ from wheel`；故意经PYTHONPATH导入源码的负控都exit1并明确 `source package is not an installed origin`。测试驱动使用checkout生成独立输入，产品身份检查与业务均从测试自有非源码cwd启动；246条实际产品CLI原argv全部为对应独立解释器 `-I -X utf8 -m smm_<owner>.cli`，没有源码产品CLI替代。

## 全部16份文档与源离线后的同引用

逐端都从实际CLI创建 ordinary项目1、global项目2及无关联ordinary项目3。每个目标项目四个独立原件，各端8份、总16份；来源files每次精确4个唯一ID，处理动作后全部ready、内容/处理版本均1，OCR配置revision1、三格式available、实际OCR ready且errors为空。普通/全局同格式有不同原件和锚点。

独立读取16份冻结输入及16份源真值：DOCX真实XML覆盖正文/插入/排除删除、三表（含嵌套和横纵合并）、页眉页脚脚注尾注；XLSX两个实际sheet全部12格；原生PDF两页及3个真实网格表；OCR PDF实际无原生文字层。真值来自源生成规则，未取待测输出。按当次source字节比较当次下载，不要求Office ZIP跨尝试日期字节一致。

重新解析246条CLI的原始stdout，而非只读read-complete摘要。全部 **32次全文、64次全表、304个返回源单元格、32次original-info、32份实际下载和64次项目搜索** 均完成独立逐项核对：

- 每份全部源文本单元恰好一次、无额外词数；DOCX正文及PDF规定顺序正确，XLSX正文允许布局分隔差异。排除文字未混入。OCR只消除空白比较，源两行顺序及每个字母/数字准确。
- 每表维度、全部格的row/column/text/row_span/column_span、全部表唯一一一映射准确；DOCX部件/嵌套路径及每格路径正确，XLSX sheet/序号/A1及文本offset正确。PDF独立按源绘图几何计算每格归一bbox、页码、尺寸及旋转，含第2页90度旋转，全部304个返回格定位/跨度核验通过，非只验首表或首格。
- 搜索目标只在自己的项目命中正确唯一ID，另一目标项目和无关联项目为零；id/origin/source_ids/原SHA/版本均匹配，首次和离线后搜索返回同引用。原件info核格式、长度、可用状态，实际下载逐字等于本轮输入。
- 逐份读取后的测试动作实际unlink源，再以**相同旧reference**经新CLI逐份读取；前后全文、表格、info及引用完整相等、版本不变、下载字节不变。已核测试源码实际unlink循环、完成原观测source_files_unavailable=true，回收中也没有遗留sources目录文件；这里不依靠仅“源离线”摘要替代读回。

| 原件 | 字节 | 源文本单元 | 表数 | 当次输入SHA256 |
|---|---:|---:|---:|---|
| hubalphadocx.docx | 2560 | 16 | 3 | `2f7d8a696d21c25583c36c5d4c937215b8dd280affa346b01d26ff6350630891` |
| hubalphanativepdf.pdf | 3371 | 22 | 3 | `9315f22c21c3e2e5feffe29c1d84499a7df313704693232eb8b1c108c66398d8` |
| hubalphaocrpdf.pdf | 36258 | 2 | 0 | `2690ae52559de0f0384df15d1361152387637db4f64916584557f86ddd08e815` |
| hubalphaxlsx.xlsx | 1792 | 12 | 2 | `75ea7a13c30c910de6a5663b0f27be8a479afd28878bff7b894bf0b415b173a1` |
| hubbetadocx.docx | 2555 | 16 | 3 | `d1844542616ce339cc30ffb96ab2efeb8b15acb79777b12fd4c3f0be30aec498` |
| hubbetanativepdf.pdf | 3362 | 22 | 3 | `e6f574c5d27c1b4c639b988b9d6a0b4eacf7071c190b9eb5611ae487e5edd42f` |
| hubbetaocrpdf.pdf | 35629 | 2 | 0 | `4e32f4e4ff8a2f7fdf7cbdb99beed29104df7407fe49af160df69c340b98c5bd` |
| hubbetaxlsx.xlsx | 1789 | 12 | 2 | `9da372be782fb5ddb3e2cb28d9793a17a4864e899955e17058ab21a7f096ac5f` |
| localalphadocx.docx | 2564 | 16 | 3 | `d8509c6cfe6594cd730529e5f2ea37278ab76ced224aebea9de6fd36f7a977c3` |
| localalphanativepdf.pdf | 3378 | 22 | 3 | `a8aed5f544049396ee5f9a566da20a21a8bceed7a29e60a436f19dcb7bd9871a` |
| localalphaocrpdf.pdf | 36207 | 2 | 0 | `273fc1fe9d58bc5bf22f90e56db3b22921ee990ef895239bde35b33ad6b1dd75` |
| localalphaxlsx.xlsx | 1793 | 12 | 2 | `f4e3be1ee6ee50c5e20cfb3cb90289b35b25fc2a11efc08e8f870256516412ac` |
| localbetadocx.docx | 2564 | 16 | 3 | `41714c43cb6d9c7eb26e38b827dc5f1d1ea0771d294b0189122c05a794447fbf` |
| localbetanativepdf.pdf | 3378 | 22 | 3 | `222b693bcf0508843525fc309ec0afa0391716b7154b10f41db401c03331c095` |
| localbetaocrpdf.pdf | 36365 | 2 | 0 | `6a0b1caac176db7030605f8c95ae1b796738c522c3fe44ba69e86181e4d395ed` |
| localbetaxlsx.xlsx | 1794 | 12 | 2 | `0d07c1fa0666ff81493a70c47e559a37aede7806d9162a36dadfe4daa14ae77a` |

## 四份真实OCR源的视觉核对

在内存中实际渲染全部四份PDF原件并目视检查，没有写入/改造源文件。画面分别为 `HUBSCANALPHA`、`HUBSCANBETA`、`LOCALSCANALPHA`、`LOCALSCANBETA` 加 `RETRY 73428`，第二行均为 `CAPTURED ORIGINAL 12345.67`，清晰可见，与各自CLI全文逐字匹配。返回locations含method=ocr；profile记录本地Tesseract5.5.4、eng/chi_sim摘要、冻结revision和处理流水线。本项证明最低门的一页真实英文OCR，不冒称完整E1/A5的中英多页/扫描网格质量已经覆盖。

## 采证故障控制

打开两个实际pytest临时目录的原件：准备早期无target/manifest情形，collection仍为collected，work_exists和materials_manifest_exists均false，材料日志存在；原始30字节stderr `original preparation error\r\n\xff\x00`逐字保留。有业务失败的控制保持failed，保留manifest、准备日志和30字节真实下载 `exact synthetic original bytes`，后缀为.bin。没有把collected冒称业务passed，也没有把opaque控制字节伪装Word。两项JUnit均实际执行通过。

## 结论边界与写入范围

本次原始证据足以判 **Linux Ubuntu24.04最低Python3.11独立安装的四类文档实际业务passed**；未发现此子域的阻塞项。其他OS、完整基础无extras接收、完整发现性/旧档案兼容、Web/MCP、受管服务、E/H/X与SC12完整链均继续由各专项原件和独立意见判断。不会因run其他job显示绿色而在本报告扩展范围。

审查只运行只读证据检查/独立格式读取与内存渲染，未执行产品业务或pytest、未改产品/测试/计划/收据、未读复制私钥；仅新写本MD和同名JSON。JSON保存全部关键证据SHA及16份原件逐份摘要，便于核对当前报告针对的准确输入。
