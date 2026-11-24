# AT-SMM-007 准备阶段独立设计与红灯复审 v2

审查者：`/root/review_007_red_prep_v2`。产品HEAD `83b50fcbbad1f29484aa54104ca0f9e75d0498e3`；定义000004 SHA `0203f41968d96272ce5bd204e8e6cbbd273fc6d9c7441f27f9fa517b206481b3`。R007规格SHA `590633b2257ca6c636058c34e5550e669d0d92dbd288076166fd9264fcb0b6e6`未改。

本轮实际读取AGENTS、SPEC/PLAN、项目文档库直接授权、首轮独立报告、reviewer/design/implementation约定、当前SC1–10判据与design-sc1..10-v4（SC8-v5）、绑定主测试/辅助/包脚本和20目标原始stdout/stderr。20目标结果SHA、19红灯绑定测试/产品文件及附件SHA、compatibility-v3的全部bindings/artifacts均逐一核验。只写本轮20份意见和本报告，没有改产品/测试、重跑产品或操作远端机器。

20份意见均已逐份写指定review-inbox路径并立即通知主Agent：11份expected_failure、8份needs_revision（均implementation）、1份compatibility基线passed。每份仅含目标实际TC。tdd-red不认领运行covers；baseline covers完整compatibility-1。逐份JSON为正式意见，以下只供导航。

## 已认可的修订

新旧项目和不同对话策略/暂停、两项目独立选择、真实换Hub同代次、并发/离线/合并前态；四文件ID到独立正文/双SHA/精确资格；两设备分别异文/提交负控；P/Q/all暂停重叠版本；真实Hub子进程stage后中断/幂等恢复与逐ref原文；真实Hub CLI两源各两文件、投影误操作源open审计；纯文档↔纯对话准确会话轮次、完整项目列表、零/多绑定/全局/合并；统一BM25、稳定tie/反序、候选冲突、私有前态与逐版本原文；四ref长文连续窗口与源不可达/禁止现读及单端fallback；逐字段重签名引用和新来源不救旧ref；两端上传安全存储/raw/链接根/2MiB全窗口；更新submission幂等、分字段PUT CAS、中断和active/paused；真实另一HID/旧epoch逐写动作及当前正控、CLI恢复竞态均已找到实际断言。

SC3两动作前态及全局后台/手动区别、SC4接受后HTTP延迟期间SQLite与控制可用、SC8人工纯文本浏览器观察已在新版场景/设计承接，未发现新增无原始依据的用户行为。真实进程重启与对象重建作了区别，七个人工项只作设计查阅，不授运行通过。

## 仍需修订的实际断言

| TC | 具体缺口及反例 |
|---|---|
| sync-publication | 175–176暂存read用内层`staged-not-qualified`，可由格式先拒绝；暂存正文误暴露于合法read但未入FTS时仍全过。需其他签名/字段有效、唯未发布资格的read探针。 |
| ordering-concurrency | 488新pause即时确认，旧ack释放时没有较新pending。只错误清空pending而保留generation的实现仍过497–498。需真实较新未确认任务。 |
| sync-boundaries | 仍无B4重叠来源被另一来源推进文件版本后不能据旧预算截合法成员的输入；设计承诺Hub原生006预算入口亦未执行。已补2MiB/+1和16MiB发布read不能替代此条件。 |
| paused-lifecycle | unlink和整源_scan PermissionError仍无单成员不可读导致partial且同源健康兄弟保留的状态。需active/paused分别恢复同字节不救旧ref。 |
| search-candidates | 正文全短于2000；727长度断言不能拦截总返回全文。需两端长文实际有界片段与独立窗口/片段重排。 |
| search-fallback | 静态图结果正确不能证明只取一次共同scope；未核请求数/冻结身份。825旧能力只核reason truthy，可误报离线。 |
| recovery-controls | 556–557用从未control授权的新project key，正常也可拒stage；Local故障前没有真实新正文待办。需当前有效授权/待发正文，防其它拒绝或无任务掩盖冲突仍接收发布。 |
| library-update | 所有DELETE都用当前CAS值；PUT单字段过期不能证明旧页DELETE不误删新版/新来源配置。需两端DELETE各字段旧值拒绝并完整不变。 |

以上均指出SPEC业务差异或已写设计，未以仅更换ID/数量等价样本阻塞。首轮已有覆盖明确认可，不重复要求；跨TC归属亦明确（例如预算在boundaries，真实重启在sync-retry/E1）。

## 原始调试结果的边界

本轮新增19项都实际失败，但只有设计/断言有效的11项授expected_failure。多数首失败为sync-status或library 404、local参数422或认证info缺document_epoch；hub-native为真实CLI无project create。packages本轮已推进到独立Local安装后CLI无--local，Hub与后续MCP尚未到达。search-fallback首失败是默认文档查询未做已约定最小登记，helper查不到P/Q投影抛StopIteration；未误写成旧轮缺epoch或ImportError。ownership首失败发生在library404，未来HubDocuments.context竞态导入尚未到达，未把它当本批importerror。

compatibility-v3实际exit0、1 passed，stderr空；非空Vibe、两对话来源旧ref、none/only/all×pause两态两端legacy完整快照、三个实际MCP只读调用与原公共API、源open/网络零、旧回归真实子进程exit0/42 passed均到达。SC8-v5把新增local参数明确交SC6/包入口，基线仅用原参数，故passed只覆盖compatibility-1。

全部后续未到达行为仅判准备断言是否有效，没有授正式运行通过。保留历史失败/首轮意见。本轮全在Mac自动测试证据范围；未使用家庭ESXi，旧跨平台准备不是产品通过。非ESXi替代环境仍未落实，七个人工平台/用户项及最终CI/正式验收仍待真实执行，不能据本轮准备结论声称交付通过。
