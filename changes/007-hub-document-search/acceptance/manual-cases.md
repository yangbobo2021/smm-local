# 007 实际用户路径与平台验收步骤

本文件是可执行的自然语言步骤，不是结果。使用已合并 SPEC E1/E2、PLAN 的当前候选独立包；每次新输出目录记录产品/探针 SHA、OS、真实身份、源原字节及 mtime。每个适用目标逐项核预先独立定义的集合、原文、码点和行号，不能只检查首条。token、私钥、档案及完整 trace 只留私有；关键 PNG 实际打开，公开副本脱敏另记 SHA。

<!-- @case-id: TC-007-user-discovery -->
## 用户发现与旧页面、Hub 认证

前置：同版独立 Local/Hub，以普通身份使用两个隔离档案；H1/H2有不同身份，待检查项目在两个目标的 generation 恰相同。只使用合成材料。

1. 普通用户从 README 使用主路径进入指南，实际按其指示取得项目ID、路径所属电脑、Hub地址、既有凭据文件、稳定KEY/HID/generation，创建本机项目并通过文件选择与拖放纳入两份不同内容。只在正确项目检索两份文档，读取原文逐字相等；默认同步关闭，Hub查不到。开启项目选择并同步后查到；创建端更新/移除后各资格/版本和待确认正确。截新项目、两份命中、原文及确认状态，记录各下一跳链接与CLI原命令。
2. Hub管理员直接打开远程Hub地址，匿名只显示空连接页。按指南取得凭据文件，实际选择后才出现项目与资料；新建Hub项目、选择和拖入文件，按所选项目命中/精确read，Hub更新/删除，本机只读。Agent从Skill走真实stdio文档工具，维护者从同一路径找到双包安装、复跑脚本与当前证据。保存可见项目身份、命中/原文、创建端入口和对端无写动作的PNG/轨迹。
3. Hub认证后检查地址栏/全部请求URL、localStorage、sessionStorage、cookie均无token。认证请求只在同源Authorization头带token。保存认证后的真实浏览器状态、请求与关键PNG；重载后必须回空连接/空数据页，重新选择文件前不发认证数据请求；重新选择后恢复访问。检查不能仅依赖HTML源或401。
4. 在真实Local网页打开项目选择旧页，记录显示的稳定KEY/HID/G。用CLI或另一页改变选择，保存完整新状态。回旧页提交，网络请求仍携旧页的原KEY/HID/G，收到拒绝、新状态逐字段完全不变，错误在页面可见；截新状态和拒绝画面并保存请求/响应/trace。不能提交前重新抓最新值替代旧页。
5. 保留H1旧页，CLI切到H2并使项目G与旧页相同。旧页提交必须带H1的旧HID，不能覆盖H2状态。逐字段核H2完整状态不变、错误可见，保存两目标身份及相同G的见证、原请求/拒绝PNG/trace。全部动作清理任务进程及端口。
6. 两个创建端各上传含`<script>window.__smm_document_executed=true</script>`及`<img src="/smm-document-executed" onerror="window.__smm_document_executed=true">`的合法TXT。正确项目检索后打开原文，关键PNG可见原样标记；真实浏览器断言window标记未被设置、未创建img/script元素、没有/smm-document-executed请求，保存轨迹和请求日志。新项目、查询片段和原文显示均用相同纯文本判据，不以查HTML源码代替。

<!-- @case-id: TC-007-e1-macos -->
## macOS 普通账户完整链路

按PLAN“E1每个平台的完整执行”1–6逐条运行：同普通UID独立前景HTTPS Hub、两份Local逻辑设备及各自空Agent根；真实CLI创建普通/全局项目和明确目录，pending后refresh，默认不传→KEY/HID/G允许→sync。两端各自真实Web先新建空项目、选择及DataTransfer拖入两份不同UTF8资料，Hub先实际选择凭据文件；在正确项目逐文档命中/原文、创建端更新/删除、另一端只读及伪造管理拒绝、本机项目同步开/关分别核。CLI、本机Web和真实stdio查询私有本机/另一设备/Hub自有原文及C↔D一层关联，第二层负控排除。两份文件在暂停前已有效，编辑后保旧Hub快照，新文件不传；删除/刷新失效仍撤回，连续重叠来源保留、最后来源退出。只停任务Hub，离线待确认/回退范围正确，重连补齐；移除来源。真实停止/重启新进程不扫描源仍读同内容和有效ref。实际中文空格路径、链接拒绝及Unix权限失败，保留源SHA/mtime。另按用户路径第6步验证嵌入脚本/事件标记只显示文字、不执行或发请求。关键状态、命中/原文、创建端更新/拒绝保存PNG/trace和原CLI/stdio/HTTP；最后核全部真实子PID与监听退出。系统launchd本轮按SPEC等价依据不冒称实测。

<!-- @case-id: TC-007-e1-linux -->
## Ubuntu 普通账户完整链路

与macOS完整链路相同的每一个业务动作均在Ubuntu当前独立包重跑，不能引用Mac结果代替。记录真实UID和Python>=3.11；两份Local逻辑身份、同UID前景HTTPS Hub；按PLAN E1 1–6的真实CLI/Web/stdio、两个创建端选择及拖放、逐项目原文、同步开关、创建端更新删除/越端拒绝、版本/暂停/失效撤回/共享连续来源/离线重连/移除/新进程持久逐项核验。中文空格路径、真实链接和实际权限不可读分别取证。另按用户路径第6步核纯文本显示及无执行副作用。保存每端实际安装模块SHA、业务请求、命中/原文及拒绝画面PNG/trace和源指纹；最后真实进程/子进程及端口无残留。同机两个档案仅称逻辑身份。

<!-- @case-id: TC-007-e1-windows -->
## Windows 普通交互token完整链路

使用当前独立包和任务专用Limited交互计划任务入口运行Local及同token前景HTTPS Hub；读取实际token is_admin=false、会话及真实进程身份，不以SSH管理员冒充。PLAN E1 1–6全部业务在Windows重跑：两逻辑设备、CLI/真实本机Web和已认证Hub Web/stdio；两创建端各自新建空项目、选择和拖入两份资料、正确项目命中和逐字原文、更新删除/对端只读及伪造请求拒绝、本机同步开/关；一层关联、版本及旧ref、暂停前有效材料的保留/失效撤回、重叠连续资格、离线待办重连/移除/重启。真实中文空格路径/换行和junction拒绝，编码错误，不能把注入异常称为真实ACL。另按用户路径第6步核脚本/事件标记纯文本、不执行或发请求。保存关键PNG/trace、原CLI/stdio/HTTP和安装/源SHA；最后核真实Hub/Local子PID及监听端口退出，不只核启动器。

<!-- @case-id: TC-007-e2-cross-machine -->
## 不同操作系统真实HTTPS

前置两台真实不同OS机器：Mac普通Local与Ubuntu或Windows独立HTTPS Hub，使用任务专用CA/TLS/凭据和独有转发端口，记录OS/实际身份/HubID和传输映射。真实CLI在原端建项目/明确采集/允许同步，另一端按该项目命中并精确读取两份独立原文；浏览器直接到远程Hub选凭据文件，新建Hub项目，选择/拖入/更新文档，Local只读。只对话C↔Hub只文档D从两个根分别用公共对话/文档查询及ref核准确会话/正文，第二层和同名负控不含。原端更新换版旧ref拒绝；断开独有通道再修改/撤回，显示待确认，恢复后补齐当前正确版本。保留两端原请求、CLI、浏览器关键画面/trace、源/安装指纹和真实进程身份；清理独有通道与业务进程，不能停其他任务转发。同机两档案不算本项。

<!-- @case-id: TC-007-e2-linux-service -->
## Ubuntu实际user-systemd读写

在唯一state-dir使用现有Hub管理CLI配置任务专有用户服务和TLS，记录unit/User/UID/MainPID及实际监听。管理CLI明确采集两份Hub来源（pending→refresh），服务按项目检索/逐字原文；另一普通Local档案允许项目并sync，同样读取。真实浏览器到该服务选择凭据文件、新建Hub项目，通过选择和拖放纳入两份不同资料；确认服务账户实际写入自有资料目录，逐项目命中/原文，创建端更新/删除，另一端只读。移走合成外部源后stop/start，持久材料和有效引用仍准确、未隐式扫描。保存真实systemctl输出、文件/安装SHA、业务请求、关键PNG/trace及原文断言。最后stop/disable，仅删除任务unit并daemon-reload，核unit、真实PID/子PID与端口清理。

<!-- @case-id: TC-007-e2-windows-service -->
## Windows实际SCM LocalService读写

管理员管理CLI在唯一state-dir配置SCM Hub，记录管理员身份；服务实际账户必须LocalService，取sc queryex真实PID及GetOwner/SID、实际监听。管理CLI明确采集两份Hub自有来源，服务按项目检索/原文；普通Local为Limited进程或另一真实机器普通Local，按项目允许sync/读回，不能用SSH管理员替代。浏览器直接到实际服务认证、新建Hub项目、选择和拖入两份不同资料、逐项目准确命中/read，创建端更新/删除；核LocalService实际写/更新自有资料目录，另一端只读。移走合成外部文件后停启服务，无refresh仍读准确持久正文及原有效ref。保存身份/模块/源指纹、真实SCM状态、请求和关键PNG/trace。最后停服并删除唯一任务服务与防火墙规则，核实际PID/子PID及监听退出，不碰其他服务。
