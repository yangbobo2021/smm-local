本报告为独立意见的脱敏副本；私有原件SHA见 completion-acceptance-20261128.json。

# 数值边界与真实 PDF 流候选独立复审 v3

结论：两个实际TC均passed，仅认literal-numeric和real-pdf-streams分配项。v2缺少原件reader前置的实现问题已由当前真实断言和本轮原始证据关闭；v2意见保持原样。

## 版本与证据

本轮沿用且已实际读取的AGENTS.md、008 intent/spec/plan及交付技能design.md、implementation.md、execution/reviewer.md。定义000003实算SHA仍为16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633；新目标debug v3 SHA为399a435f7ca8a5e92dbe9e1c087d572b5d73d9280af6d4bbb46c0da04b9bd86d。v3的80个bindings、206个artifacts及80份source快照均逐SHA正确；match122个绑定、runtime80个绑定及2个smoke产物正确。设计收据SHA e202d707bb1baabb709ddbcd0e34d2b455f6f672179d49acbe9213fd1f1ed008与目标引用相符；两TC自然设计与v2逐字段相同。运行绑定相较v2仅tests/test_document_formats_pdf_safety_complete.py改变，产品未变。未复跑业务或修改项目源码。

匹配收据SHA：3b93bb6557e1221d1f30481571fdc86c14e8229eb4ac81fc41f1b91512837c35。运行收据SHA：17a02dfc2a2e35af70809b92adb8d246a9ba4ff0b11f957692ef18597bb93e11。

## literal-numeric

设计结论：有效。SPEC B9固定默认额度和A10等于上限/+1直接支持本项，PLAN要求独立全集/逐目标真值；六项组件边界未增加无依据的产品行为。设计只承接10000成员、100MiB展开、8MiB规范UTF8文本、16MiB完整序列化结果、64非空工作表及200实际PDF页，不认其余预算或文件全链路。
实现与原日志结论：通过。tests/test_document_formats_numeric_limits.py:35–44核成员全集/总字节和10001拒绝，:50–61核独立100MiB实际payload及+1拒绝，:67–77核独立Unicode全文/SHA及+1，:87–95核规范JSON实际16MiB/+1，:107–114核全部64个sheet名称/独立格值及65拒绝，:124–132核实际PDFium页数200、201拒绝且无输出。附件独立读取得到10000/10001实际ZIP成员、104857600/104857601实际展开字节、8388608文本UTF8字节、16777216完整结果字节。原run.stdout为6 passed in 1.51s、exit0、stderr空，六项均执行到，无skip或未到达项。
边界推演：仅首sheet正确而后续缺失/重复在:107首次拦截，伪造64份首sheet在:108拦截，名称正确但后续值错在:109拦截；仅首页存在而宣称200会在:126实际reader长度拦截。丢容器成员在:39，错大payload在:56，文本两边同错在:72独立原文/SHA拦截；JSON仅自报16MiB被:89实际序列化长度拦截，超限误接纳被各pytest.raises拦截。该TC为隔离组件调用，没有更新既有发布态的承诺，旧ready/partial保护属于其他分配项，不能据此扩大认领或要求额外等价标识样本。
本轮重新读取数值附件：成员10000/10001、实际展开104857600/104857601、规范文本8388608字节、完整结果16777216字节。六份Office原件容器字节相较v2不同，但逐ZIP成员名称与内容全部相同，不将ZIP元数据变化误称业务内容变更；本次按v3独立原件及其实际摘要认领。

## real-pdf-streams

设计结论：有效。SPEC B2/B3的原生文字/原件保持、B9/A10的有界处理，以及PLAN“PDF有界解码的接入位置与确认门”的预测器/滤镜/对象流/中间材料保真支持本项。设计将本项限定为TIFF2、PNG10–15的8bit Gray小样、短LZW及五种过滤器/两级组合、嵌套Form和压缩字体对象；没有增加无依据的产品行为，也没有把该子域冒称完整SC10或平台通过。
实现与原日志结论：通过，v2唯一implementation缺口已关闭。tests/test_document_formats_pdf_safety_complete.py:25–30现在对每个原始raw先执行真实PDFium打开、实际1页、render和全部六个固定源点与手写expected逐项相等，再于:31调用intermediate；:35仍核全部解码字节/图像尺寸/移除Filter，:36–39再核私有材料全部六点。原14份源PDF及私有产物相较v2逐字未变。逐份打开本轮14个guard-predictor-pixels JSON，已见source_pixels与rendered_pixels分别匹配独立expected的全部六值，source/private SHA分别匹配对应原件附件；七种预测器×两variant全集完整。不是只增观察字段而未执行断言。
其余既有检查本轮保持有效：对象分支:53–57由两个源reader先核源词，:63–68核双目标集合、唯一性、正确来源；:71–76逐文件核全部词/顺序/无表格错误/原件逐字及mtime。滤镜分支:97–98先读各原件，:100/:102两个私有reader分别与独立key相等。实际observer自检仍为1个完成guard、pdfium/pdfplumber各1个合法读取、5个拒绝（两reader拒原件路径和内存原件，另拒篡改私有副本）；resources.py:155–161实际核退出、计数、guard和原SHA身份。两个对象原始reader-events各有2个guard/2个pdfplumber读取，分别对应两份源SHA，无rejected。纯原生文字没有PDFium读取符合B3，不要求强迫渲染。
边界推演：仅首variant/首像素正确会先在新增:29对该源输入的六点失败，或在:35的独立六字节/:39的私有六点失败；原件fixture与guard若对同一预测器共同误解、仍生成私有自洽六点，新增源reader的:29在guard之前拦截。只首文件成功在:63/:66拦截；漏非首INNER词在:71拦截、文字顺序错在:72、错下原件在:75。两私有reader同取ALPHA并误用于BETA，:100的独立key首次拦截；source/raw与private两边同错不能靠相等放行，因为两边各自对固定expected断言。动作前源字节/mtime已于:58冻结、动作后:76逐两文件复核；没有本项应覆盖却遗漏的旧ready/partial更新状态。已覆盖同条件差异后只换第三个key或像素值属于可选补测，无需增加。
本次原run.stdout明确17 passed in 1.12s、exit0、stderr空，无skip或未到达检查；17为7预测器参数、2对象参数、7滤镜参数加1探针自检，各参数内部两份源样本。只认real-pdf-streams分配项。其他位深、LZW宽度/EarlyChange、JBIG2、完整PDF安全与E/H/X仍待各自证据；v2 needs_revision及更早失败原件保持原结论。

本轮只读项目与既有证据，未复跑业务、修改源码或重造附件。不得以这两项候选结果认领完整SC10/R008或三平台通过。
