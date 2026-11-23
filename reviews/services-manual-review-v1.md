# AT-SMM-007 实际服务与跨机器人工执行独立复审 v1

本轮只读复核三份指定人工收据及原件，不执行产品、Windows、ESXi、日常Hub或修改GitHub。依据为本仓库AGENTS、007 SPEC E2与PLAN“E2跨机器和实际服务”、`acceptance/manual-cases.md`、`case-design/design-sc9-final-v2/result.json`及交付验收技能执行Reviewer规则。意见只适用于本次真实记录；不是需求级交付结论。

## 结论

| 实际TC | 目标 | 独立结论 | covers |
|---|---|---|---|
| TC-007-e2-windows-service | manual-e2-windows-service-final-v1 | insufficient_evidence | [] |
| TC-007-e2-linux-service | manual-e2-linux-service-final-v1 | insufficient_evidence | [] |
| TC-007-e2-cross-machine | manual-e2-cross-machine-resource-v1 | insufficient_evidence | [] |

三份目标各自唯一意见已写入`review-inbox/review-<目标>.json`并逐份通知主Agent登记。两项服务已有大量有效实测，但各自分配的是一条完整复合检查；缺少下述明确要求的网页资料重启持久证据，故不认领完整检查。未观察相应产品失败，不判product_defect。

## 原件完整性与版本

- Windows目标SHA `f971a66b14a56142258d299a4630f0ca3ec0d537851189de5904c50166824d34`，165项bindings/artifacts全部核对；Ubuntu目标SHA `b9f10a545e13c7ad77e119b72aeaf223af8071abe9e5c3a4abc963f57c095a95`，154项全部核对。跨机器目标SHA `38a4ad45333866d94301e4f60297478e9a4978919c7d83bdebef5fab402292f2`，1项binding、2项artifact全部核对。
- 两个实际artifact根为`/private/tmp/smm-007-ci-final-windows-v2`和`/private/tmp/smm-007-ci-final-ubuntu-v2`。外层ZIP分别为79cd3ed0…80bc9及f21d1841…2554，与download-receipt的GitHub digest一致；实际ZIP CRC通过。SCM内manifest全部109份、systemd全部98份的长度/SHA通过。
- `work/manual-evidence/{windows,linux}-service-ci-465-v1/original-copy-manifest.json`分别106/95份，解密原件manifest各3份，共207份的源文件及无损副本逐长度/SHA一致。4份trace的解密ZIP各自长度/SHA与原始trace登记一致，实际打开检查CRC、事件和网络资源。没有输出token或私钥。
- 实际运行采用run45201802511/head465d27e、`work/runner-snapshots/service-465d27e/`旧helper，runner-bindings吻合。不能套用后来E1纯文本/越端管理/按ID全文核对修订。两端安装Local30/Hub31模块实际摘要逐份与当前src吻合；Hub `_archive`按`build_packages.py:37`的vendoring规则映射，并单独核shim替换，不能直接误当src/smm_hub/_archive文件夹。

## Windows原始观察

原件入口`work/manual-evidence/windows-service-ci-465-v1/platform/`及解密目录`windows-service-decrypted-465-v1/`。

- controller/program-access记录管理者Admin与已安装Hub解释器实际可读31模块。service-events记录任务服务`smm-hub-c6da31167baf`真实PID7104、重启6300；StartName/owner均LocalService、SID S-1-5-19、session0。普通client PID1808非Admin，113份实际Local CLI/MCP进程身份均非Admin；`scm-client-boundary.json`实际HubDB读取拒绝。管理账户和普通账户审计分离，管理员63份进程身份为Hub CLI；源打开均只在明确采集阶段。
- 实际打开`web-hub-search-read.png`，看到Hub项目8的chosen/dropped两个不同文档ID及chosen的emoji/组合字符精确原文；实际打开`web-hub-device-readonly.png`，设备投影项目9显示只读创建端指引，无上传/更新控件。
- 实际解析私有`web-hub-trace.zip`：lhxq@100及@111分别对两个结果点击read；网络资源的ID分别是dropped `0bb745376a9f4b1681e9819a2460e37c`与chosen `be745ed49cfe4684882d092648958d9a`，正文分别是独立脚本文字样例和中文/emoji/组合字符样例。由真实资源核实，当前执行没有发生两次读同一目标的误判。PUT/DELETE原网络及web-hub.json证明chosen版本1→2、准确新正文后移除，dropped仍在。
- 移走外部D目录、真实stop/start后native旧有效ref/当前采集原文仍可读；普通Local实际子PID树及端口关闭有记录。10份源SHA/mtime在应保持阶段相等。

**缺口1（阻止完整通过）**：已审SC9 `e2-windows-service-6`明确要求网页管理副本“按对应新建项目命中/read及重启持久”。旧helper `hub_documents_platform.py:1666–1744`停启后只遍历native外部D/E采集原文，并以Local项目D查询；重启15:12:41.591395后管理/普通两份commands.json均没有两份网页文档ID，Web trace也已在重启前结束。保留dropped没有重启后项目8查询及有效旧ref/read；不能把native缓存成功扩展为网页资料持久已验证。

**缺口2（清理证据边界）**：冻结`hub_documents_scm_platform.py:412–433`发出disable/sc delete及netsh delete；`service-cleanup.json`仅failures空数组，未保存服务/防火墙规则不存在的后验查询，netsh删除的返回也未核验。实际PID停止/端口退出支持已执行部分，不能代替全部服务/规则残留检查。

前轮run45194460889的cp1252 IPC失败及用户批准的两个read_text UTF-8修订历史保留；本次不据旧工具失败宣称产品缺陷，也不进行任何再修订或重跑。

## Ubuntu原始观察

原件入口`work/manual-evidence/linux-service-ci-465-v1/platform/`及解密目录`linux-service-decrypted-465-v1/`。

- systemctl原输出、unit定义与service-events一致：任务unit`smm-hub-73e65458f6c8.service`，ExecStart为独立Hub包，实际UID1001、PID3778→4324。176份产品进程身份为UID1001。停止后实际PID/端口检查、任务unit移除及daemon-reload有原件；没有把当前OS的普通前景Hub称为systemd。
- 实际打开两份Hub关键PNG，分别看到Hub项目8的两份不同文档与chosen准确原文、设备项目9只读。私有Hub trace mrfx@100/@111的真实read响应分别返回dropped `89b1a171e1dd4cdf986ec5e9ad51045a`、chosen `f1d8298cd54a4f2ca038880b302f2a04`及各自独立正文。PUT/DELETE、web-hub.json记录chosen变为版本2后移除，dropped保留。Local trace也实际打开并核两份文档及独立全文。
- 25份source-open记录只有explicit-refresh/conversation-import；10份源在保持阶段SHA/mtime相等。移走外部合成源后真实stop/start，native当前正文与旧有效ref准确，最终服务与Local子进程及端口清理有证据。

**缺口（阻止完整通过）**：SC9 `e2-linux-service-5`同样明示网页管理副本重启持久。旧helper只重读native外部采集资料；15:12:38.381351重启后commands.json无两份网页ID，Web trace已结束。保留dropped的项目8精确检索/原有效ref在重启后未实测。不能用`native_cached_after_process_restart=true`或成功汇总代替该项。

## 跨机器资源边界

实际打开`work/manual-evidence/cross-machine-resource-v1/resource-observation.json`。用户明确排除家庭ESXi Windows/Linux，替代环境回答为“暂时没有，先继续本机与CI”；观察记录actual_business_execution=not executed且未访问排除主机。本次没有两台不同OS机器的业务请求、准确原文、远程网页写入更新或断线恢复/独有通道清理证据。托管服务与Local在各自同一宿主，不能代替物理跨机器。资源阻塞保持，covers=[]；不由此推断产品错误。
