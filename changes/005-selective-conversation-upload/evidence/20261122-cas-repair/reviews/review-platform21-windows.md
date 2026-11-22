# AT-SMM-005 R005：最终包 Windows21 独立平台复核

结论：**windows-reconcile21 的 ba8c6d5 安装包 CLI/Web 对账专项证据成立，包括新增 CLI 无版本参数 `--use hub` 新鲜正控。未确认本范围新产品缺陷；不授予正文补传、完整 E1 或 R005 整体通过。** 原始业务/进程清理有记录；调度任务删除后的独立查询快照未提供，单列如下，不把包装器源码等同事后快照。

本轮只读实际附件、冻结控制器、干净最终源码及两个版本的wheel，实际查看3张PNG、解析trace与完整请求/回执，未重新运行产品，未修改产品/测试/原证据。只写本意见两个新文件，未覆盖mac-linux21或15意见。依据本上下文实际读取的 `AGENTS.md`、005 intent/spec/plan，并重新核对 SPEC B1/A11、PLAN §12/12.1；阶段确认与需求级完整判断仍由维护者另行完成。以下证据路径均相对于 `.acceptance-local/native-v1/AT-SMM-005/`。

## 普通 token、安装身份与全部产品字节

`platform-debug/windows-reconcile21/manifest.json` candidate 为干净 `ba8c6d5e86dbe0ecbb58214db14a22d4a556b7a0`；实际运行系统为 Windows11 10.0.26100 AMD64、Python3.14.2。manifest 与 `local-service.json` 均记录 user=<ordinary-user>、`elevated_admin:false`。冻结 `selective_upload_windows_limited.py` 使用 Interactive/Limited 的ScheduledTask启动worker，worker在运行探针前实际检查 `IsUserAnAdmin()==False`；`outer-process.json` 记录worker PID13852、exit0、普通交互会话。不能将SSH父进程身份代替此token结果。

已逐个复算全部 Local **25** 个 Python/HTML 文件、Hub **24** 个产品文件：candidate 清单、实际 installed 清单、`commands.jsonl` 隔离解释器 `-I -X utf8 -c` 的真实 stdout、最终wheel全部产品条目、干净 `<task-path> 源码及 ba8c6d5 git 对象均完全一致。Hub vendored共享文件按构建规则展开核对；独立Local/Hub环境均 `other_package:false`，不存在借开发源码路径冒充安装包的依据。

- Local wheel：`416799968bfc5a22bf2dc1baee6b16491ae3995de0266cf68afa980c980222ee`。
- Hub wheel：`eac8b57564d463ca74fd4ad40e02a0052c062b4cacbace45335bb39d11135800`。
- 再次直接打开 `<task-path> 的旧wheel比较完整集合：Local唯一不同为 `smm_local/upload.py`，Hub全部24项相同，吻合 `work/final-package-comparison21.json`。没有把相同版本名0.4.0当成字节相同。
- trace实际收到的HTML SHA=`1afcb4a170768ba79fe43647febe010c5aa2ea7030cd79dce05310db87f25599`，匹配安装和candidate。
- 冻结reconcile控制器SHA=`3bcfbcf7c404634cd2b1ca7bda9a896d1d7bc96dc184ecd05d9310f228aefdbc`，platform=`ec5329e6240493ad8142bb359478fe2cfd52612ca8eb9f6e0af2553a06f70a8f`，Limited包装器=`78ec82d54e49cb208b91ea5a92fd35592b908e3b0a95f7d0c49c692bebdee519`；均与mac/linux21逐字相同。trace source附件也逐字包含该reconcile探针。

## 真实页面、请求与业务判据

3张原图均已实际查看：`stale-local-rejected.png` 红色本机代次拒绝；`stale-hub-rejected.png` 红色Hub版本拒绝；`adopted-hub-current.png` 绿色双方确认/全部不上传，仍保留历史补传失败提示。浏览器版本158.0.4370.33、page_errors=[]。

`reconcile-browser-trace.zip` 的真实点击 bghr@28 / @56 / @80 分别对应旧本机提交、旧Hub提交、刷新后采用Hub；3次截图为@39/@63/@89。6次 `/api/upload/reconcile` POST 的真实状态依次为 **200/400/200/400/200/200**；各请求体及响应正文与 `reconcile-result.json` 精确相同：

1. 初次查看本机none/generation1、Hubnone/revision2；临时断任务relay后，本机all/generation2 pending/HTTP503，Hub仍none/revision2。
2. 旧CLI带Hub2/Local1，`commands.jsonl:L25` exit2、stdout为空，错误明确要求重新查看本机差异。旧页面Web同样发 `{use:local, expected_hub_revision:2, expected_local_generation:1}` 得400。缺generation的CLI在L26 exit2并明确要求local.generation；`rejected_policy_calls`无policy/set。本机规则前后L24/L27均all/generation2，目标/设备一致；Hub版本/规则/提交头未变。
3. 新鲜CLI带Hub2/Local2成功all/generation3/revision3、confirmed，中间transfer_state=backfilling。另一个入口将Hub收紧到none/revision4后，旧Web仍带Hub3/Local3得400，本机L31/L32均all/generation3。
4. 刷新后Web发送 `{use:hub, expected_hub_revision:4, expected_local_generation:3}`，200，返回none/generation4/revision5、confirmed。adopted PNG对应此步骤，不能将它改称后续CLI正控截图。
5. 新增兼容CLI正控 `commands.jsonl:L34` argv末尾精确为 **upload reconcile --use hub**，没有任一版本参数，exit0；stdout逐字段等于 `cli_use_hub_without_versions`。最终为none/generation5/revision6、confirmed。

最终完整头核对：hub_id=`9db1dd7d46844df89ab09046dce4e541`；device_id=`6bdc14829cb244078fdcec9502b7d0e6`；control_epoch=`666b2ada45a64d7e97c1cc8a176f96e0`；submission_id=`359448370bdb4d96829fdd4124be8548`。`final_local`/`final_hub`/CLI remote回执的目标、设备、none规则与控制epoch吻合；Hub restore_pending/conflict均false。`payloads.json` 中08:35:39.519034Z 的真实set请求恰为该提交ID、expected_revision5、policy none、reconcile:true，返回最终revision6，且本机generation5。并非只核对result.status或mode。

## 进程与清理，以及证据限制

原始result结束于08:35:59.812417Z，status passed/failure null；全部37条记录只有上述两项预期exit2，最后L36/L37为两个档案的stop-on-demand，exit0/ok:true。`service-events.json` 显示Hub PID12824在stop_requested:true后exit1；冻结控制器只在明确请求终止后接受Windows TerminateProcess的1。因此Hub子进程1与worker外层0含义不同，不能把子进程1当业务失败，或把其任意提前退出当正常清理。`cleanup.json.failures=[]`；worker外层PID13852退出0。主执行器另报告SSH父进程exit0；该父进程结果未在本目录单列收据，本意见不把空ssh日志独立解释为退出码证据。

调度器边界：冻结Limited包装器finally确实调用Stop-ScheduledTask和Unregister-ScheduledTask，但两者均 `-ErrorAction SilentlyContinue`。本目录没有事后Get-ScheduledTask/任务不存在的独立查询结果，因此**本意见确认有清理执行路径及业务进程退出收据，不能独立确认调度登记已消失**。这是清理取证边界，不是已确认产品缺陷，也不改变上述规则操作的实际结果；若需要“任务登记已删除”的结论，应另提供只读查询收据，不能回写这次证据。

最终Web/CLI虽然policy confirmed/none，但transfer_state仍failed，transfer_problem为Hub状态/规则/项目登记改变；allowed_pending0、inflight0、confirmed_messages0、not_confirmed_messages5。页面忠实保留“历史补传失败”。这与本探针主动外部收紧期间的状态相容，本专项未断言正文到达或读回，**不能宣称正文补传成功**，也不因规则成功而删除传输失败边界。

本探针未在首次/第二次Hub状态读取或CAS前注入新竞争，不单独替代该修复的源码/红绿灯独立审查。Windows21是新的ba8执行，旧15仍保留7c身份；本意见只补齐三平台最终包对账专项的Windows证据，不覆盖完整E1三入口搜索、E3系统服务、恢复/兼容或R005总体交付判断。
