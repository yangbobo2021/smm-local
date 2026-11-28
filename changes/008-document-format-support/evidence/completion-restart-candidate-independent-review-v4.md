本报告为独立意见的脱敏副本；私有原件SHA见 completion-acceptance-20261128.json。

# SC7 重启候选 v4 独立复审

结论：`passed`。设计、实际断言和本轮debug证据支持唯一实际TC `TC-008-managed-upload-restart` 的分配检查 `managed-restart`。v3残留的首次pending冻结配置缺口已修复；这不是完整SC7、R008或E/H/X通过结论。

## 基线与绑定检查

已沿用并复核本会话实际读取的AGENTS、008 SPEC/PLAN、Reviewer规则和自然语言设计边界。定义000003 SHA256为`16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。SC7判据来源A7/B5/B6/B9；本项按B2/B4/B5/B7/A7/A9/C1核对，没有增加产品行为。具体命令和样例留在用例设计，场景保持业务判据。

| 目标收据 | SHA256 |
|---|---|
| design-completion-sc7-restart-v4 | 58362a0b0f88484378e3e1b74b3e95da8e5af0d5682f7477ab325c29647edc2b |
| match-completion-sc7-restart-v4 | 6d613195a8fb88bf6a92864fdb00c3db4bf93ab73dfbf4c6f27746344cc88f40 |
| runtime-completion-sc7-restart-v4 | 4edce539e55a3cb0e2dc68289079ccdfbdfd094411f4d4f2a3abb86c1626dff0 |
| debug-completion-sc7-restart-v4 | 46298e246648076b12144bc4e90fd40873b395182d7474c69a5c0dd1a8a1e701 |

match100份、runtime/debug各87份绑定均与实际文件逐字SHA吻合；debug/source87份冻结副本也逐文件吻合。1415份artifacts全部存在且SHA正确，其中1217份事件gzip可读（1127 HTTP、18×4启停事件、16原件下载事件、2状态汇总）。与v3相比，运行绑定仅`tests/test_document_formats_upload_restart_c1.py`变化；产品、restart_server/platform/retry等既有动态依赖同字节，旁路PDF新测试未混入本次绑定。

## 设计与实现检查

自然设计v4保留两端、普通/全局各两适用目标，分别覆盖未commit半传、首次pending、既有partial、empty-success、旧ready加新pending。B5要求冻结处理配置及原CID/AID续办；设计已明确所有这些动作前状态的检查，而非仅首个目标或仅配置1矩阵。

所有代码行号均指C1测试文件。原始四DOCX在:46–47冻结pending_attempt，并独立断言默认config_revision=0、created_at非空。恢复及稳定重启的verify_all在:71–74核原receipt CID/AID、pending_attempt中的CID/AID/config_revision/created_at及合法ready终态；:82另把正文profile绑定同一默认配置0。v3报告的config_revision=999反例现在首先被:73拒绝；若只改正文profile，则被:82拒绝。

12目标矩阵的AST与v3完全相同，保留:159–175逐全部目标的check_attempts：partial/empty完整latest_attempt不变，replacement按原pending receipt保留CID/AID/config_revision/created_at，pending时整项相等，完成时ready/finished/error正确且published CID等于原候选。:247/:259/:266/:272/:289覆盖初次重启、等待准备/重启、恢复完成和稳定重启。初始receipt及配置1由:241–243锚定，新pending由:254–257锚定。

DOCX三处:23/:232/:235按独立源truth前12正文单元核顺序，含title、段落和表格流。完整源oracle还拒绝重复、遗漏和额外文字；不增加页眉、页脚或脚注相对于正文的未规定顺序。16份保存DOCX解包后全部可见XML文字与独立truth逐项一致，未从产品输出生成预期。

## 实际断言反例检查

以下只读回放提取本轮debug/source中的原断言函数，使用本轮原始HTTP响应、truth和原件，在内存改变一个字段；没有修改产品/源码/原件，也不将回放称为新的产品执行：

- 首次pending两端各4目标，恢复及稳定重启4组真实状态均通过；逐目标改CID、AID、config_revision、created_at或正文profile共80个反例全部被原verify_all拒绝。
- 矩阵两端各12目标、4个边界共8组真实状态通过；384个身份字段突变、128个partial/empty状态或error突变全部被原check_attempts拒绝。
- 8份首次DOCX的title移到After后、重复、缺失、多字共32个负例均被原完整源helper拒绝。

JSON持久化的表格cell数组在回放中还原为原夹具tuple，保持实际输入语义；keep/observe为空操作，不产生旁路文件。

| 从动作前状态及全部目标推演的反例 | 第一个拦截位置及原因 |
|---|---|
| 只有首个/普通项目/一种状态正确 | :61完整唯一列表、:70–84逐目标终态与独立真值；矩阵:157/:164/:168/:183–212逐全部状态与目标 |
| 重复首行、重复ID或错项目集合 | :53–54/:61/:104/:125/:157长度、唯一ID、项目全集 |
| 两端误用同目标或同错正文/表格 | :76–96及:185–212按自身ID、源SHA、完整正文、全表全部单元/跨度和原字节核独立真值 |
| title移尾、交换正文单元、重复或缺字 | :84/:195调用完整源oracle；独立前12正文单元顺序已覆盖title |
| 重启后旧ref换正文/表格 | :85/:93完整文本/表格前后相等，矩阵:258/:270/:290完整snapshot相等 |
| 重开删除副本/源路径 | :56/:261–264实际删除，Server.start deny和Python audit拒绝open；各stop记录无源open |
| 稳定启动/查询偷偷解析或OCR | :285–296启用processing/任何Popen禁止守卫，业务读完日志不存在，再以实际双正控验证恰好两类拦截 |
| 旧引用被拒绝但业务状态被改 | :280–282对旧text/table/original-info/download各请求独立比较全部document/hub_document/hub_processed业务表 |

各个不同档案的内部ID只与自身receipt/目标比较，没有要求跨档案ID相同。现有行为差异均已覆盖，没有以额外同条件样例或任意标识特判设想继续阻塞。

## 调试证据检查与边界

原生debug实际命令执行同一文件Local/Hub两端两类，共4个pytest实例。stdout为`4 passed, 1 warning in 43.87s`，execution exit0，无skip。分配的managed-restart检查均实际达到，没有未到达检查。

每端原始4份半传DOCX、12份状态矩阵（partial/empty/replacement各4份）均实际执行。18次停启中4次run_pending等待屏障强停exit -15：`00034`、`00166`、`00504`、`00973-restart-server-stop.json.gz`；其余自然退出。矩阵每端初次12个内容worker、恢复替换4个worker，稳定重启0 worker，最后进程和端口退出由Server验证。

这些证据证明本次共享C1 Mac普通UID隔离前景档案的续传、合法等待任务续办和已发布结果保留。不能宣称全部正常关闭，不能替代正在运行的processing worker恢复、OS服务恢复或E/H/X环境。v2/v3意见及历史失败原件保留，不以本轮通过覆盖。正式执行仍由另一Reviewer复核。

本次只写此报告和同轮JSON，不改其他文件、源码、原件或PR，不合并。
