# AT-SMM-007 准备阶段独立设计与红灯复审 v1

审查者：原生独立 Reviewer `/root/review_007_red_prep_v1`。根目录 `/private/tmp/smm-007`；产品 HEAD `83b50fcbbad1f29484aa54104ca0f9e75d0498e3`；定义 `000002` SHA-256 `96bb8f88ac5b2c53deb933a8a185301fc4f0af1eca8ed47bbd3b329c784697a6`。

本轮读了 AGENTS.md、已合并 SPEC/PLAN、项目文档库授权原话、独立 Reviewer/设计/实现约定、SC1–SC10 定义、design-sc1..8-v2 / sc9..10-v3、当前匹配收据、20份目标收据和实际stdout/stderr及绑定测试/夹具。20份目标摘要、TC集合、所有记录artifacts摘要逐一核验。评审中的源码行号指本轮各目标保存的 `source/tests/test_hub_documents_contracts.py`，不是未来修订版本。

本轮只写自己的20份JSON意见及本报告，没有改产品或测试，没有重跑产品用例。逐份JSON写完即通知主Agent，未覆盖既有意见。实际判定以JSON为准。

## 实际运行与准备判定分开

19项新增能力实际均失败，首个失败属于SPEC要求的公共能力缺失：sync-status或library路由404、local参数422、认证info缺document_epoch、Hub CLI缺project create，以及成功构建的Hub wheel缺自己的Web HTML。没有把环境/导入/依赖错误当红灯。每份意见都写明首个失败和之后未到达的检查。

但19项各自均有具体设计或断言缺口，因此准备结论为needs_revision，未授expected_failure。首个有效失败不能代替后续实际断言。

compatibility基线确实运行1 passed、exit 0、stderr空。它只证明已写的两个旧对话ref/正文前后保持、一个本机文档库查询/read隔离及MCP工具名集合；没有执行分配给compatibility-1的005许可/暂停/回执、VibeInsight、MCP实际调用只读与公共显式local。因此其准备结论也为needs_revision，未伪报整个义务passed。

总计20份needs_revision：scene 1、design 1、implementation 18。没有正式平台/浏览器结果，七个人工项只作为设计和步骤查阅，不授运行结论。之后新增、未绑定本批的跨平台探针及其自检不能补算本批覆盖。

## 逐项意见索引

| TC | 最早修订阶段 | 关键缺口 |
|---|---|---|
| hub-native | implementation | 单原生来源；失败隔离、列表身份、不隐式读源缺实际检查 |
| library-ingest | implementation | 同名文件ID→独立正文未映射；链接根/raw副本/磁盘不变/边界read缺失 |
| library-update | design | B8上传与更新均要求submission幂等，设计只安排上传；另无新正文read/完整CAS/中断与同步状态 |
| ordering-concurrency | implementation | 无旧回执/Local待办；旧版本与sequence混变；屏障在HTTP之前 |
| origin-identity | implementation | 两设备正控有效；异文只测第一设备，合法archive/project替换和本TC其他已写检查缺失 |
| overlap-publication | implementation | 仅all及项目/来源数量，暂停Q按项目不可查或错归属仍能过 |
| packages | implementation | 缺全新环境安装/真实入口及Hub全模块源→wheel→安装核对 |
| paused-lifecycle | scene | A3要求未暂停与暂停前已有状态分别验证，SC3只表达后者；两个unlink不等于不可读/整源失败 |
| policy-choice | implementation | 既有项目、不同对话许可、第二项目选择、真换Hub同代次、并发/离线、合并未实现 |
| project-ownership | implementation | 添加混变ID/key；缺逐动作合法对端/超域身份、磁盘、CLI原子屏障和配置正控 |
| project-scope | implementation | 反向对话只核ID未read轮次；列表可空；零/多绑定、全局、改名/合并/映射缺失 |
| read-exact | implementation | 四ref独立切片正确；无路径不可达/禁止现读及误路由不同正文负控，长文本窗口有空隙 |
| read-rejection | implementation | 有效签名只改epoch/HID/archive/kind，缺device/doc/version/revision/qualification及新来源/重启 |
| recovery-controls | implementation | 只Hub回退+Local删保护，缺其余故障、自有pending、冲突拒发布、重新允许后旧ref永拒和005不变 |
| search-candidates | implementation | 私有文件在enabled时refresh后才暂停；统一BM25/每端limit/tie/反序/异常及逐版本原文未核 |
| search-fallback | implementation | 只info前断网；缺签名错误/已冻结后故障/拒绝/Local单端故障及真实覆盖状态 |
| sync-boundaries | implementation | +1同时带错长度/摘要；边界只读前7字或stage200，完整发布与尾部未核 |
| sync-publication | implementation | 正文/双SHA独立预期有效，项目只非空；第二来源单文件、来源全集/版本/暂存read缺失 |
| sync-retry | implementation | 旧ref文本只属集合，两个均误读first可过；Hub/进程中断、重复stage、持续失败隔离未做 |
| compatibility | implementation | 实际基线通过，但分配的005/VibeInsight/MCP实际只读/公共local未执行 |

每行对应交接中完整review_file；所有JSON均只含该目标实际TC，并没有越界认领covers。

## 共同问题与最小修订方向

1. 独立目标必须有独立预期映射。`set(texts)==expected`可验证全集，却不能在同名资料场景证明每个ID读到自己的正文；`text in expected`甚至允许两个ref都指向首个目标。数量和非空字段不能代替项目/来源/身份/资格的精确值。
2. 拒绝负控保持其它条件当前有效。超限正文同时摘要错、旧version与旧revision同时变、对端project_id搭本端key，均可由另一校验先拒绝，不能证明目标约束。
3. 核清动作前状态。暂停后才创建的目标不证明暂停前已有资格；恢复允许后移除来源不证明暂停时移除；允许时refresh后的文件不能直接当作从未上传私有材料。
4. 公共入口与存储观察都要落地。库函数不代替CLI/MCP调用；数据库snapshot不代替管理副本磁盘不变；wheel名单不代替独立安装与入口运行；函数导入不等于执行该文件的回归。
5. 不要把设计大段文本作为源码已覆盖的依据。匹配收据当前把整函数挂给粗粒度检查ID，但函数里没有的动作/断言仍然缺失。独立可执行的失败检查应按设计拆分/分配，保留本轮历史后重新取得同版收据。

## 跨场景补查项

以下是从SPEC反查时发现、当前20项之外也没有明确设计承接的要求，需在下一轮场景/设计中明确去向，不因本轮已有红灯省略：

- B2明确全局自动暂停只停止后台正文、控制/撤回仍可重试、手动documents sync仍可执行，而且文档选择/任务不能改变对话暂停。SC1只有项目授权/状态，SC3只有项目暂停，SC8的旧005暂停兼容不能自动承接文档后台这一差异。需要把全局后台/手动行为单列业务判据，再给可区分的动作前状态。
- B4明确不得跨网络请求持有本机数据库事务或控制锁。SC4当前顺序判据没有这个并发可用性要求，现有ordering线程也只在发送HTTP前等待。需要能在真实请求停留期间完成本机另一控制动作的检查。
- B8要求上传/读原文纯文本渲染、不执行文件内容。当前SC10的字节/格式判据与七份人工步骤只用普通合成正文，未明确把嵌入可执行标记的资料按纯文本显示作为业务判据及浏览器观察；应在场景/设计中分配，并保留关键画面和无执行副作用的独立断言。

这些跨场景要求并非新增产品行为，出处均在已确认SPEC；本报告不把它们补写进旧JSON或授予未运行覆盖。

## 本轮保留有效的证据

多个TC已有独立全文与集合断言，能拦截首条之外的错误，意见中已逐点肯定：publication逐文档ID/正文/双摘要，ingest两端两项目全集，paused两份暂停前正文及逐旧ref，read-exact四类ref逐切片和LF，compatibility两种来源的独立原文。无需只换名字/数字再添等价样本。修订应针对已指出的目标关系、动作前状态、独立字段约束与观察面。
