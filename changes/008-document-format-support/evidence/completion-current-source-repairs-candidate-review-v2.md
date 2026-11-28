# AT-SMM-008 源码回归候选修订独立审查 v2

结论：passed，限本轮测试/控制器修订的候选正确性及实际Mac源码回归范围。UV/PATH修订仅代码审查通过，真实Windows尚待；不据28项本机通过裁定三OS或E/H/X。v1意见和旧失败原件保留，本报告不是原生receipt。

## 版本和实际执行

独立重算before/end的286份src/tests/scripts源码摘要、完整snapshot及当前文件，全部逐字相同。JUnit实际28项、0失败、0错误、0跳过，216.992秒；case-map的28个SHA24 node键逐一重算一致。产品源码没有本轮修改。新GC并发TDD不在本审查内。
.gitattributes不在286份manifest内，已另核当前原字节/摘要及git属性，只认代码配置结论，不冒称Windows checkout已验证。

## 继承v1检查

v1的namespace -I、latest.error、prepare发布等待、download当前响应绑定、cache-Hub实际服务发布者及Hub request-scoped守卫六项判断保留。本轮重跑这六类适用目标；新的Web上传等待和PerItem改动以下列v2判断为准。未将28项目录中的直接pytest driver冒称-I控制器重跑；此前smoke4的20项-I证据保持原精确版本。

## 新增逐项审查

### web-upload-publication-boundary-v2：passed

依据：SPEC B4/B5/B7；原上传用例每份成功后独立核原SHA/内容。位置：tests/test_document_formats_web_uploads.py:191-211。

新轮询把latest.ready与真正同CID成套发布区分：每一行均ready、published存在、非publication_pending且published.CID==latest.CID后才离开等待；failed立即失败，最终逐份SHA、V/P及verify_original断言全部保留。冻结v1原04373-restart-http.json.gz实际捕获Local id95db20a7245b41b4ae6973591145498d/latest.ready、published=null、sha=null、publication_pending=true，故原14过1失败是真实观察竞态，不能改判。

反例推演：第二份未发布或旧发布CID仍在：all逐行轮询/45秒截止首先拦；同CID却错字节：紧接全集SHA以及逐份原件/正文/全表真值拦。另一端/另一项目/第二轮只有首目标正确：两端×chooser/drop×2轮×3格式均实际遍历，稳定ID和receipt检查仍在。不是降低原成功预期，也不把pending隐性认成功。

### restore-durable-posix-key：passed

依据：原TC-008-snapshot-restore-set完整恢复集和当前fence契约；SPEC B5已保存快照一致性/A11旧档案兼容；PLAN归档恢复保护不豁免。位置：tests/test_document_formats_restore_set.py:92-96; tests/test_document_formats_restore_set.py:100-141。

仅把跨OS清单内部键从str(relative Path)改为as_posix；实际Path文件读写、六raw/四results精确数量、原摘要、完整manifest覆盖、排除运行锁/tasks、复制后逐字比较、元数据全等与当前guard/fence拒绝仍保留。Windows原三参数均在/raw/计数0处失败，符合Windows分隔符与硬编码斜线匹配不一致；未重写产品manifest或修改原数据。

反例推演：遗漏第二raw/result或两个项目只保留首份：6/4数量与captures SHA集合先拦；同数量但丢错字节/同错目标：源原SHA和metadata独立核对、每个durable实际字节复制比对拦；只local-private正确：local-private/local-sync/hub三分支均实际执行，legacy两分支亦实测。三OS路径实际通过仍待新CI。

### c1-restart-published-capture：passed

依据：SPEC B4重启仅续保存快照；B5成套发布/晚到不能覆盖；A7/A8状态差异。位置：tests/test_document_formats_upload_restart_c1.py:145-158; tests/test_document_formats_upload_restart_c1.py:165-180; tests/test_document_formats_upload_restart_c1.py:241-307。

wait_ready保留所有项目资料数量/独立ID，逐资料等终态；非failed还必须有published、非pending且同latest CID。failed仅允许退出等候，后续snapshot/check_attempts仍强制该资料期望状态，不会放过合法样本处理失败。原Windows在终态ready但旧published.CID时过早check，当前等待不篡改后续期望。

反例推演：只首replacement发布/只ready正确而partial或empty恢复失败：每端12资料（ordinary/global×partial/empty/replacement×2）及check_attempts/snapshot全遍历首先拒绝；重启后换CID/AID/config/created_at：check_attempts逐字段拦；旧ref误指新原件：独立raw/text/全表真值、旧引用400及存储不变拦；两端同错不能只靠相等过关。四项C1 restart（含原半传/pending两端）本次均实到。

### inflight-runtime-process-identity：passed

依据：原inflight barrier必须属于本次显式reprocess；SPEC B5旧快照在途可读、B4缓存重试不回源；PLAN真实进程身份边界。位置：tests/document_formats_inflight_observer.py:18-26; tests/test_document_formats_inflight.py:144-164。

marker在真正执行document_supervisor的运行时记录PID/ctime/完整psutil argv/exe；父进程登记launcher PID/ctime并枚举其真实树，marker必须匹配树中同PID/ctime、完整argv且argv[1:]==本次CLI命令、samefile exe属于明确解释器。替换固定Popen.pid相等，不允许任意进程满足门。原Windows原tar marker pid5164与JUnit中launcher6444不同，证明确有运行时差异；原marker没有ctime等，不能据旧原件反向补造新验证。

反例推演：伪同PID/外国进程/错token/另一目标：树与ctime/argv/exe先拦，随后raw SHA与快照路径、CID/AID/config/status绑定拦；只首ready或partial成立：四个独立reprocess目标各在门内遍历自身及其他四份资料，读旧全集、查询守卫/源守卫与存储不变，然后逐目标终态和旧ref失效仍核。实际Mac四个新运行marker已读取，Windows新逻辑实测尚待。

### legacy-cli-lf-golden：passed

依据：SPEC A11既有CLI兼容；原test_compatibility冻结历史文件SHA且比较9个source帮助入口。位置：.gitattributes:5-6; tests/test_document_compatibility.py:90-108。

只固定历史fixture的Git工作树LF字节，不改旧CLI、metadata SHA或help预期。当前LF实际SHA=f1133ae0cec7bfaccae9b93663c88870a589d88504a74cefa8769214a8aa86bd，独立仅LF→CRLF转换的SHA=dacbc2fbd437fb2404e1ac3e9598b88db6ab803c572ede64c6aed48037641d63，与旧Windows失败两端摘要精确对应；git check-attr实际返回text set/eol lf。

反例推演：为接受坏fixture改真值：metadata和fixture都未改且原固定SHA断言保留；仅首help一致：9动作逐一before/after exit和完整stdout相等仍在。实际本机兼容回归通过；Windows新checkout真实LF与业务待CI，不把Mac通过视为该平台证明。

### per-item-evidence-reuse：passed

依据：SPEC A12及证据逐用例可追溯要求；v1发现共享basename trace覆盖。位置：scripts/acceptance/document_formats_source_suite.py:114-155。

PerItem仅提为item_evidence可复用工厂。nodeid SHA24作为独立目录，重复键拒绝；hookwrapper在yield前设ACCEPTANCE_EVIDENCE_DIR，finally恢复旧值。实际28个case-map键独立重算全部正确、目录各自存在；两上传trace与两blank trace分别在各item目录，已实际打开ZIP的trace/network和本轮六PNG，无沿用v1被覆盖trace。

反例推演：上传与blank同名local-trace.zip/hub-trace.zip互相覆盖：nodeid目录不同，实际四路径/摘要分开；另一参数漏项：case-map与JUnit28项逐一映射。各上传trace均12commit200/2drop，无call error；各blank trace均6original200，无call error。不改变测试断言或产品。

### task-owned-uv-path：passed

依据：SPEC A11/C1源码包构建回归入口可执行；原Windows test_packages真实FileNotFoundError。位置：scripts/acceptance/document_formats_source_suite.py:35-56; scripts/acceptance/document_formats_source_suite.py:86-100; scripts/acceptance/document_formats_source_standard_user.ps1:17-35; .github/workflows/document-formats-source.yml:49-58。

prepare在管理员准备阶段从实际which uv解析二进制，复制到任务work/tools并冻结SHA；credentialed标准用户已获work递归M权限，run_checked先读副本核SHA再仅在本任务子进程env的PATH前置该目录；没有修改系统PATH/产品配置，也无需给管理员用户profile额外授权。原test_packages调用默认uv，继承该env可找到副本；-I及产品子进程独立安装检查未移除。

反例推演：工具缺失/副本被换字节：prepare assert或run SHA在pytest前失败；子用户仍找不到/不可执行、复制uv运行依赖或PATH受Windows实际环境影响：只能由真实标准用户CI证实，28项本机driver未调用prepare/run_checked或test_packages，不认已经覆盖此项实际修复。

## 本轮画面和轨迹

实际打开per-item-v3的Local chooser第二轮pending/ready、Hub drop第二轮pending/ready及两份空白library六PNG。pending画面可见三格式V0/P0且原件按钮未启用，ready后V1/P1及成套SHA/状态，空白显示empty-success且下载启用。未使用旧被覆盖trace。
- source-repair-per-item-v3/attachments/e5799ddcff355dbae03f9f4c/local-trace.zip：591 calls，12 commits，0 original，2 drop，call errors=0。
- source-repair-per-item-v3/attachments/5641dc8457c528ecd262579a/hub-trace.zip：577 calls，12 commits，0 original，2 drop，call errors=0。
- source-repair-per-item-v3/attachments/eb31c1a368e051e803993860/local-trace.zip：264 calls，0 commits，6 original，0 drop，call errors=0。
- source-repair-per-item-v3/attachments/60e95c5ee07cce83650f99c8/hub-trace.zip：264 calls，0 commits，6 original，0 drop，call errors=0。

## 原失败核对

实际流式打开官方恢复的Windows/macOS原tar的JUnit和inflight marker，分别核raw-index长度及SHA；未整体解包。Windows实际367项/15失败/23跳过，Mac367项/6失败/14跳过。冻结v1新增ready未发布原响应已打开；旧14过1失败不反向改判。legacy LF→CRLF独立计算精确重现旧Windows错误SHA，未改golden真值。

## 尚待范围

- task-owned uv/PATH fix真实Windows标准账户执行与package回归尚待；28项未走prepare/run_checked/test_packages。
- Windows .gitattributes checkout、restore分隔符与launcher真实后代路径均尚待新平台执行；Mac只证明候选本机断言通过。
- 原Windows active-source及web-management失败不在本次修订审查结论内；相关GC并发TDD归其他Reviewer，本轮未改/执行/审查其产品与测试。
- 完整新三OS source正式回归与原件独审、C1总义务及E/H/X均未由本报告关闭。
- v1所有原件/历史失败保持；本轮只写两份独立意见文件，没有改产品、测试或既有绑定。

机器可读完整意见及28项映射：source-repairs-candidate-review-v2.json。
