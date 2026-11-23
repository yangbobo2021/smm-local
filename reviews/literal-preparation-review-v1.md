# AT-SMM-007 纯文本探针准备与 Mac v12 局部独立审查

结论：**needs_revision**，`revision_target: implementation`。当前候选的逐行原文读取没有独立核实两份目标均被遍历，存在两行误用同一目标仍通过的断言缺口。**本次 Mac v12 的局部实际观测成立**：原始 trace 和两张原图明确显示两端确实分别读取了 chosen.txt、dropped.md，恶意标记按文字显示，四个检查阶段均无执行标记、嵌入 img/script 节点和触发请求。候选准备缺口不能改写为本次产品失败；本意见也不判整个 E1、SC8、SC9、A8/A9 或总需求通过。

## 范围、依据与版本

只读审查 `/private/tmp/smm-007` 当前未提交 diff 和 `/private/tmp/smm-007-macos-e1-v12` 原件；唯一写入为本意见。未改产品或测试，未执行 Windows/ESXi、未启动服务。已实际读取 AGENTS.md、007 spec.md/plan.md/manual-cases.md，采用 app-delivery-acceptance-native 的候选审查规则，分别核对自然语言依据、实现断言、实际证据及反例。

- `spec.md:11` 要求不执行嵌入内容，`:110` 明确上传/原文纯文本渲染，`:152,154,158` 要求两端两份独立文档的准确原文及浏览器原件。
- `plan.md:96–97,102–103` 要求独立夹具、完整文件集合、两创建端逐文档原文，不能两边同错。
- `acceptance/manual-cases.md:3,10–11,15,20` 明确不能只核首条，并给出两个创建端、新项目/片段/原文、script/window 与 img/onerror、无 DOM/请求的既有检查。
- 自然语言判据有上述原始依据，未增加产品要求；本轮新增工具检查承接原第 6 步。恶意正文当前为合法 UTF-8 `dropped.md`，不是 `.txt` 扩展名；SPEC 将 md/txt 同列纯文本入口，本意见不凭此等价扩展名新增产品阻塞条件。

逐字节复算 v12 `runner-bindings.json` 三项均等于当前 helper：platform `0ade1ce2cd6a0dd317f025c79da0fe894bcaccb9b95b303df4045bfad5e34932`，checks `3f1d1921c0646dbdec12ccd04ddcd3f44666602ad50f6faadfd3ad5c87859334`，MCP worker `aa2188fbb7197c5ef13259c1eb8b74917ab89a775b288f37f3dd90d908171f32`。安装来源为 `/private/tmp/smm-007-installed-candidate-v4`：Local wheel `0eca3d5828ab443e94396d1af39e1d775d4311b2b82a9c59b5fa8f4052a15fd9`、Hub wheel `3268544c4475087c64d76d3124b1aec6c3ab7e41c5f4385828fd9d55849ddd44` 均实物重算相符。Local 30 项、Hub 31 项模块/HTML与记录、wheel、安装文件相符，并核当前 src；Hub vendor 项映射当前 Local 源，生成的 `_archive/__init__.py` 另按 `scripts/build_packages.py:39–40` 的 shim 替换规则复核相符。无产品源 diff。

## 必须修订的候选断言

**F1：两行读取的期望目标由被测 DOM 名字反选，缺少完整独立目标校验。** `hub_documents_platform.py:878–882` 确认 API 搜索结果含两份创建回执 ID，但 `:888–905` 对两行只读 `h3`、断言 `name in raws`，再用 `raws[name]` 校验响应和阅读区；没有断言 DOM 名称集合恰为两份且无重复，也没有将每行按钮请求/响应身份与该行独立期望 ID 绑定。`hub_documents_checks.py:22–28` 的 `exact_read` 只核文字、范围、行号，不补身份约束。

可放过的既有义务反例：API 搜索仍返回 chosen/dropped 两个正确 ID，第二行片段仍含恶意标记，但两行 h3 都错误显示 chosen.txt、两按钮都读 chosen 的引用。`:879` API ID 集合、`:884` 容器含恶意片段均通过；两次 `:891` 名称成员断言和 `:900,905` 独立 chosen 原件比较都通过；`:906` 会两次保存 original-chosen.txt；`:907–913` 只条件性截图，没有必须出现 dropped 截图/阶段的最终断言。纯文本 helper 仍正确接受两个安全 chosen 画面，后续更新/删除与 API/CLI 原文断言不强制回到这个被漏掉的浏览器 dropped 原文。因此没有第一拦截断言，本轮新增恶意原文的浏览器动作可被漏掉。这个缺口来自已规定的两份逐文档核验，非要求添加等价样例。

最小修订：先按创建回执建立独立文件名/ID/原字节映射，断言浏览器行全集各一次，并在点击时核真实 read 请求/响应对应该独立目标；结束时断言完整阶段集合与必需截图存在。给误指同目标/重复目标的探针负控。保持现有正文/DOM/window/请求判据及实际 Mac 原件不变，新增版本重取准备证据；不需要据此改产品。

## 已核实的实现、反例与边界

`hub_documents_platform.py:721–759` 在导航前监听所有页面 request，`:745–749` 固定原始 script/img 及两端不同项目名；`:813–819` 比较完整既有项目标签并检查创建阶段；`:884–887` 片段包含原样标记；`:900–906` 校正文/阅读区并检查每次读取后状态。每端都独立调用 web（`:1882–1883`），没有以 Local/Hub 响应互比当原件。

| 反例 | 第一拦截位置或现有限制 |
|---|---|
| 仅首份正文正确，第二份保留正确名字却返回错文 | `:900` → checks `:25` 独立原字节文字比较；阅读区单独错则 `:905`。 |
| 两行误用同一个目标且名字也同错 | F1，现有断言没有拦截；本次 trace 实际未发生。 |
| 只 Local 安全、Hub 执行或反之 | 两次 web 各独立到相应地址；执行标记最先由 `:669–672` 拦截，嵌入节点由 `:673`，触发请求由 `:674`。 |
| 仅项目创建/片段/原文中一个动作前状态不安全 | 各阶段分别 `:819,887,906` 调 helper；window 持续标记和累计请求也保留先前副作用，不能只末态清零通过。 |
| 两端都返回同一错误安全文本 | 各端 `:900` 的独立上传 raw 比较失败；两个端都安全不构成相互佐证的唯一依据。 |
| 两端误导航同一 Hub | Local 分支 `:792–806` 的真实 Local 文档页元素/项目选择先失败；实际 trace 还分别核了 HTTP Local 与 HTTPS Hub 端口及创建回执。 |

四字段 helper 自检 `:722–744` 包含一个正确值和四个单字段错误值，各端 `literal-selfcheck-{a,hub}.json` 均记录接受/拒绝成功。它证明判定函数会拒绝坏见证，不能补 F1 的目标遍历遗漏。不要求任意其他 HTML 标签、所有等价项目名或瞬态 DOM MutationObserver；原承诺及本轮范围没有提供需据此再阻塞的独立条件。

## Mac v12 原始观察

`result.json` 为 darwin、2026-11-23T14:48:27.793894Z 至 14:48:53.361008Z 的 passed；controller 为 macOS 15.3.1、UID 501。`commands.json` 200 条混合命令/HTTP记录，167 条含实际进程退出码，安装校验为独立 v4 Python 的 `-I`；含产品拒绝用的非零返回，不把它们归为测试失败。此处只引用相关安装/业务记录，不据总 result 认领完整 E1。

已实际打开两张原图，未用缩略图或源码代替：

- `web-a-literal-original.png`：本机项目 `Web Local <img ...>`（#5）原样可见；chosen.txt/dropped.md 两份命中可见，dropped 片段和下方原文均完整显示 `<script>window.__smm_document_executed=true</script>`、`<img src="/smm-document-executed" onerror="window.__smm_document_executed=true">` 及 legacy script；原文显示 `[0,197)`、行 1–4。
- `web-hub-literal-original.png`：已认证 Hub 项目同类原样名字（#8 · hub）、两份命中，以及 dropped 的同样完整标记片段和原文，原文 `[0,197)`、行 1–4。未见加载的文档图片，标记是可读文字。

两端 `literal-display-*.json` 均有 new-project、query-snippets、original-chosen.txt、original-dropped.md 四个独立阶段：window/legacy unset=true、embedded_nodes=0、trigger_requests=[]。其 `all_resource_requests` 在两次原文读取前后累计，均无触发 URL。

直接读取原始 trace ZIP，CRC 完整、不是仅看 JSON 总结：Local 156 个 before/after 动作、73 条网络记录；Hub 91 个 before/after、47 条网络记录。两端各四次 evaluate 的原始结果均与 literal JSON 一致，网络均无 `/smm-document-executed` URL。两端第一次/第二次读取的 h3 实际依次为 chosen.txt/dropped.md，read 响应从 ZIP resources 逐字读取：Local ID `57b51aff77084cb4a398f3b3b81e29ff` / `9fd8f695246f4c5d9d9c0f2001e9e45e`，Hub ID `529fec39d88244e8bf6fdf556e50d5e1` / `3804cd5b6ed24dae9cf642805b9d5586`；分别是独立 chosen 20 码点及含完整恶意标记的 dropped 197 码点，与 `web-{a,hub}.json` 两份创建回执一致。这是本次原件实际排除了 F1 反例的直接依据。

trace 原件 SHA：Local `68f1b4f2f9aaf32d0990ffe1de0323e1e3c56b97ed33819bce9aa38a49fc08f1`，Hub `a1320a162148511760faa79678396f2b347793282e1c13bc436242cce7477681`。`web-hub.json.network` 因后段 reload 前清空而为 []，未拿这个空数组证明前段无网络；这里用私有完整 trace 和新增累计请求原件。`cleanup.json` 八个任务进程见证均 alive=false，记录全部当前端口关闭；本意见未重新启动任务。

v11 `failure.json` 保留了对项目 option 只期望 project_name、实际标签有 ` · #8 · hub` 的断言失败；v12 `:814–818` 已保留原标签后缀作完整比较。此为探针预期问题，不列作产品缺陷。

## CI 准备差异

`hub_documents_ci.py:72–75` 恰追加四份 literal-display/selfcheck 的明确 JSON 文件白名单；原有敏感目录/凭据/数据库排除及 trace CMS 封装不改。`.github/workflows/selective-upload-acceptance.yml:8–9,18` 仍默认 selective-upload/005；`:80,84,105–106` additive 的 document-installed-e1 覆盖三系统普通 E1；`:108,111` 两个服务步骤都只允许 mode=document-installed，故新模式不执行 E2 user-systemd/SCM。旧 document-installed 模式仍走原普通业务及两个适用服务步骤，未豁免 E2，README 也明确该适用边界。这里只给静态路由准备结论，未运行托管三系统/Windows/服务。

允许保留并引用本次 Mac v12 的上述纯文本实际观测；候选准备须关闭 F1 后再认领可复用完整断言。后续正式 manual 独立复审及完整 E1/E2 判定由各自收据处理。
