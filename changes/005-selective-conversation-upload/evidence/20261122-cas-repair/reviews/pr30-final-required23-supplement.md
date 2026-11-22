# PR30 required23 测试与计划增量补审

本补充保留 `pr30-final-ba8-review.md` 原文，不覆盖其产品与入口审查。审查时 HEAD 为 `9473a61779b6fd78e0ad64ca963478675333d462`；新增测试及计划调整尚未提交。实际执行 `git diff --name-only ba8c6d5 -- src` 为空，产品仍为 ba8 的全部相同字节。本轮只读新测试、当前 diff、相关 SPEC/PLAN、冻结测试与原始执行链，只写本文件。

## 结论

**本次测试/计划增量审查可通过，未确认新增产品缺陷、无依据的新产品契约或削弱既有业务断言。** required23 的5个TC、14个参数实际执行通过，可补足下列 SPEC 已明确点名的共用边界。计划 §3.3 对齐实际签名项目集合方案，§12.2 记录补验原因与顺序，与源码和证据相符。

原报告“各A/E必要行为均可由证据支持”的概括，不能单独视为本轮这五项指定分支当时已经专门实测；此次需求反查发现的缺证及 required22 的准备缺口应保留。现以原报告、这份增量补审、正式执行独立意见及需求级最终判断共同评估交付。**本意见不代填 R005 整体通过**，也不把共用 TestClient 用例扩大为新增三平台/真实服务验收。正式执行独立Reviewer与需求级Reviewer的最终登记，以各自实际出具记录为准。

## 计划与实现的一致性

- SPEC B5:74–76/A6:224 要求本次查询使用已取得快照、下一次才采用变更后的关联，未要求独立关联版本字段。最终 `hub.py:202-212` 签名目标、设备、请求稳定项目及完整有效项目集合；`:454-472` 消费该集合并验证稳定身份后查询，不重新展开；`federation.py:491-497` 从同一集合精确映射本机项目并发送同一 scope_reference。plan §3.3 去掉并未实现的独立版本号、解释集合本身冻结关联结果，是方案记述纠正，不是降低 B5/A6。
- §12.2 明确新增测试为原 SPEC 点名条件补证，先设计/调试与独立准备复审，再正式执行/独立执行复审，保留旧缺口。实际 required23 链有 runtime、match、准备独立意见和新执行时间/进程/附件；没有把 required22 调试结果重包装成正式成功。
- 唯一 G 的计划措辞已用同一 SQLite 写事务中的查询/条件插入对齐源码，原报告已核，无新增产品差异。用户/Agent/Hub维护者入口所有产品字节均未变，原入口回放仍适用；本次无须另造文档改动或重复全部平台运行。
- §12.2 “最终CI加入新用例再回归”是后续验证约定。本轮已读源码全回归 v14，未把此前不含新测试的 CI 45002908134 当作已运行这14项的新CI。

## 五项测试的业务判据与实际证据

所有行号指 `tests/test_required_snapshot_and_batch_boundaries.py`；正式目录相对 `.acceptance-local/native-v1/AT-SMM-005/execute/`。

| TC及规格依据 | 实际触发、独立预期与通过边界 |
|---|---|
| TC-005-scope-race；B5/A6 | :24–70 两参数分别在实际 query-scope 返回后、Hub候选返回后改变 A—D/RemoteB 为 A—E/RemoteC。control_only登记后先确认Hub无本机正文，本机A/D/E独有、Hub仅另设备B/C，不能由Hub副本掩盖本机漏查。旧快照ID完整集合恰A/D/B，Hub结果仅remote-b，最终会话及逐条来源恰A(local)/D(local)/B(hub)，逐条全文独立匹配固定文本；新查询恰A/E/C，之后旧引用仍读旧允许消息。两份正式附件均呈现端点B→C、最终旧A/D/B→新A/E/C，2 passed。 |
| TC-005-reference-boundaries；B7/A8 | :73–141 七参数。本机/Hub各建立两条不同正文、实际position均1，先完整读两条；重复位置再分别签发单消息引用，逐一读回独立第一/第二正文，并核stamp实际消息ID及内容版本。四个删除参数分别删真实首/非首消息ID，旧完整引用都必须错误，物理剩余正文恰另一条。真实换Hub建立另一个hub_id和同号错误正文哨兵，重新配置确认身份已变，旧引用报错且新Hub没有/read调用，本机/新Hub错误正文不被混读。七份正式附件有准确删除剩余项、重复位置双正文及不同Hub/空read_calls，7 passed。附件没有逐条单引用成功输出，精确读取由冻结测试:101–107和实际完整7 passed证明，不夸称另存了不存在的返回附件。 |
| TC-005-policy-triple-order；B4/D1/A2 | :144–185 实际all→none→all提交revision1/2/3，嵌套延迟使响应实际3/2/1返回。任何后续push前，即要求公开hub_revision3/正确epoch、remote与持久submission绑定第三次真实receipt，ack_generation=generation=3/ack_revision3/ack_epoch正确；不能仅靠mode相同或后续自愈掩盖旧回执覆盖。重放已提交前两次请求保原回执但完整Hub头不变，另一个从未提交的过期停止请求409；最后两轮上传只一份独立正文。正式附件三次提交/反序响应及最终确认均吻合，1 passed。 |
| TC-005-batch-failure；B4/D1/A4 | :188–215 两参数两条不同会话正文同批：before-commit在调用真实Hub前故障，Hub应零正文；partial-receipt先真实归档两条再把accepted改为正数1，Hub应完整两条而Local必须ControlConflict。两种失败后确认0/待确认2/在途2均独立断言；恢复后确认2/待确认0/在途0、完整两正文，重复再同步不增加。正式before-commit附件25次有界尝试、partial一次提交，失败/恢复计数及正文均准确，2 passed。前者不是“已提交响应丢失”的替身，后者也不是accepted=0的弱负例。 |
| TC-005-mixed-batch；D1/A4 | :218–243 先实际control_only登记且独立核对A/B均在当前设备稳定键集合；采用当前真实revision/epoch，只B允许。允许在前/禁止在前两顺序都必须403/project_disabled、Hub完整正文前后恰空、批次回执空。纯B同版本正控必须200/accepted1且完整正文仅B，不能以全拒绝或未知项目拒绝冒充事务原子性。两份正式附件均明确许可错误、空receipts与成功正控，2 passed。 |

## required22→23 是否通过放宽测试取得成功

独立读取 required22 冻结测试并与当前新文件逐行 diff，变化保持原检查目的并补强可区分性：

1. 范围测试把会提前上传D/E的正文同步改成只登记，并增加Hub空正文、独有来源断言，关闭“本机漏D却由Hub副本补足”的假通过。
2. 删除从只删首条扩为首/非首两类，本机和Hub均跑；重复位置移除不属于公开读取返回值契约的 `read.messages[0].source_key`，保留逐条独立正文读取，并改为核真正签名stamp的实际ID/内容版本。这是纠正测试字段前提，未放弃精确消息身份。
3. 三次乱序新增push前对第三次真实receipt及持久ack精确检查，关闭“mode/generation未错但ack被旧响应覆盖，后续push再自愈”的假通过。
4. 混批增加真实项目登记和当前设备身份核验，把泛化HTTP错误收紧到403/project_disabled，并保留零正文、无回执、纯允许正控。旧unknown_project失败不再被当成产品原子性通过。
5. 整批失败/正数部分回执的正文与账本断言保持，未因新增混批删除其原职责。旧准备意见及失败调试附件仍在 required22 目录。

## 真实执行链核对

从 `work/required23-execution-manifest.json` 进入四个正式result，分别核对 request选TC、设计ID/SHA、design_review及真实命令；各份 **38个bindings** 与 **6/11/5/11份artifacts** 全部重新计算SHA256，无不符。runtime-required23 为ready；match-required23-sc6/sc8/sc2/sc4为matched，所有artifacts/bindings再次核验一致。SC6/SC2/SC4沿用未变化的required22自然设计，SC8为新增首/非首删除后的design-required23-sc8，引用均准确匹配实际设计原始字节。

| 正式目标 | 实际运行时间UTC / PID | 原始结果 |
|---|---|---|
| execute-required23-sc6 | 09:14:38.641–09:14:39.342 / 7788 | scope-race 2 passed；2附件 |
| execute-required23-sc8 | 09:14:39.552–09:14:40.326 / 7818 | reference-boundaries 7 passed；7附件 |
| execute-required23-sc2 | 09:14:40.527–09:14:41.001 / 7841 | triple-order 1 passed；1附件 |
| execute-required23-sc4 | 09:14:41.206–09:14:42.053 / 7856；09:14:42.053–09:14:42.537 / 7863 | batch-failure 2 passed、mixed-batch 2 passed；4附件 |

五次真实业务执行的 execution.exit_code 均0，stderr为空；stdout唯一warning为既有TestClient/httpx弃用。14份正式JSON业务附件逐份读取，比对上述作用前状态、请求/回执/最终集合，不仅依据passed标签。四份 `review-preparation-required23-scN.json` 独立意见均限定到对应新增TC，未替旧case/full/gaps重新签通过，本补审维持该范围。

另实际读取 `<task-path> **234 passed, 1 skipped, 1 warning in 97.92s**；比原220项新增14个参数，符合当前测试集合。没有为本补审再次重复全量，亦未修改产品或测试。是否已有新的三平台CI、正式执行独立意见及R005最终交付结论，应由后续实际记录另证，本报告不推定其完成。
