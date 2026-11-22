# AT-SMM-005 R005：最终包 platform21 macOS/Linux 独立复核

结论：**mac-reconcile21 与 linux-reconcile21 的新安装包 CLI/Web 对账专项证据成立，新增 CLI 无版本参数 `--use hub` 新鲜成功正控也成立。仅支持本专项，不授予 R005、完整 E1 或正文补传验收通过。Windows21 尚未纳入本意见。** 本轮只读原始材料，未运行产品、未修改产品/测试/控制器或旧15记录；仅写本意见两个新文件。

依据仓库 `AGENTS.md`、005 SPEC B1/A1/A2/A11 及 PLAN §12/12.1 的双版本/条件保存要求作范围判断。AGENTS 已在本独立审查上下文实际读取；原意图/规格/计划与先前实际读取的同项目材料保持连续。以下路径均相对于 `.acceptance-local/native-v1/AT-SMM-005/`，JSONL 行号为实际行号。

## 最终安装包、完整模块和普通身份

两份 manifest 的 candidate 均为干净 **ba8c6d5e86dbe0ecbb58214db14a22d4a556b7a0**。逐份核对全部 Local 25 个模块/HTML 与 Hub 24 个模块，结果同时吻合：candidate 清单、manifest installed 清单、该运行 `commands.jsonl` 中隔离解释器 `-I -X utf8 -c` 实测 stdout、当前最终 wheel 中完整产品文件集合和 SHA、`<task-path> 的干净源码及 ba8c6d5 git 对象。该独立源码 checkout 的 HEAD 正确、tracked 工作区为空；两个独立安装环境均 `other_package:false`。

- 最终 Local wheel SHA256：`416799968bfc5a22bf2dc1baee6b16491ae3995de0266cf68afa980c980222ee`。
- 最终 Hub wheel SHA256：`eac8b57564d463ca74fd4ad40e02a0052c062b4cacbace45335bb39d11135800`。
- 独立打开 `<task-path> 的两个旧 wheel 与当前 wheel 比较完整产品文件集合，Local 唯一变更为 `smm_local/upload.py`，Hub 24 个文件字节均相同。旧 wheel 全文件 SHA 也与 `work/final-package-comparison21.json` 一致，故没有仅信比较文件。Hub wheel 外层 SHA 不同不能被误认为 Hub 产品模块已改变。
- 两份 trace 实际载入的 HTML SHA 均为 `1afcb4a170768ba79fe43647febe010c5aa2ea7030cd79dce05310db87f25599`，等于安装和 candidate；不是开发目录页面。

mac21 的 manifest/local-service 身份为 **<ordinary-user> UID501**、macOS15.3.1 arm64，Local 解释器 `<task-path> 为 **<ordinary-user> UID1000**、Linux6.8 x86_64，解释器 `<home>/smm-005-20261122/local-env/bin/python`。冻结控制器拒绝 UID0，实际身份输出与两份 manifest 一致；这里证明普通非 root 运行，不推断账户是否有可用 sudo 资格。

两目录的冻结 `selective_upload_reconcile.py` SHA 均为 `3bcfbcf7c404634cd2b1ca7bda9a896d1d7bc96dc184ecd05d9310f228aefdbc`，trace 的 source 附件逐字包含同份源码。与15冻结探针直接 diff，新增仅是在 Web采用Hub成功后实际执行一次 `upload reconcile --use hub`、验证 confirmed/none 和 Hub policy 一致，并将其结果记为 `cli_use_hub_without_versions`；其他既有负例/正例未被删除。

## 六张原始 PNG、两份 trace 与规则头

已逐张实际查看 `platform-debug/{mac-reconcile21,linux-reconcile21}/` 各三张原始 PNG：`stale-local-rejected.png` 为本机规则改变的红色拒绝；`stale-hub-rejected.png` 为 Hub 规则改变的红色拒绝；`adopted-hub-current.png` 为双方确认且全部不上传。没有从15复制截图作21结论。

两份 `reconcile-browser-trace.zip` 均逐项核对真实按钮点击与6次 `/api/upload/reconcile` POST 请求体/响应正文，状态顺序均 **200/400/200/400/200/200**，并与各自 `reconcile-result.json` 精确一致。Mac 的负例/正例点击为 call@31、call@63、call@91；Linux 为 msle@28、msle@56、msle@80。浏览器版本分别为157.0.8103.50、159.0.8154.6；page_errors 都为空。

两次运行均独立呈现以下规则变化：

1. 显示本机 none/generation1、Hub none/revision2；临时断 relay 后本机保存 all/generation2、pending/HTTP503，Hub仍 none/revision2。
2. 旧 CLI 带 Hub2/Local1，exit2、stdout为空；旧 Web 同样携带两值得400。缺 generation 的 CLI exit2并明确提示 `local.generation`。负例窗口 `rejected_policy_calls` 没有策略 set，之后本机仍 all/generation2，Hub头不变。Mac status 原始行 L23/L26，Linux L24/L27；实际非零仅为这些预期拒绝及缺参两条。
3. 新鲜 CLI 使用 Hub2/Local2，成功变为 all/generation3/revision3、confirmed，transfer_state=backfilling。外部 Hub 随后改为 none/revision4；旧 Web 携带 Hub3/Local3得400，本机仍 all/generation3（Mac L30/L31；Linux L31/L32）。
4. 刷新 Web 后采用Hub，请求为 `{use:hub, expected_hub_revision:4, expected_local_generation:3}`，200，返回 none/generation4/revision5、confirmed。该结果对应两张 adopted PNG。它发生在最后一条 CLI 正控之前，不能把 PNG 当 generation5 的画面证据。
5. 新增 CLI **实际未带任何版本参数**：Mac `commands.jsonl:L33`、Linux `L34`，argv 末尾精确为 `upload reconcile --use hub`，exit0，stdout与 `cli_use_hub_without_versions` 完全一致；返回 none/generation5/revision6、confirmed。此结果是命令/规则头证据，没有另行声称有该步骤浏览器截图。

最后 CLI 正控的完整规则头交叉核对：

| run | hub_id / device_id | 最终 Local / Hub | 最终 submission_id |
|---|---|---|---|
| mac-reconcile21 | 487006252e76409688f14c54931bab67 / d7689c8288e1477ca1d319bbee3ccd7f | none,generation5 / none,revision6 | 9700597d8e3543cc9a1b3bc56f476f19 |
| linux-reconcile21 | 46e510c780dd43b686eaf0f764e12af1 / 25ffac1828de4414b36cf4db32816d00 | none,generation5 / none,revision6 | cc67360bc0044855b5db5364f11d1d53 |

最终 Hub status、CLI remote回执、final_local 的目标/设备/规则一致；control_epoch一致，Hub restore_pending/conflict 均false。各 `payloads.json` 中恰有该最终 submission_id 的真实 `/v1/upload-policy/set`，expected_revision5、policy none，精确对应返回revision6。Mac control_epoch=`44ceaa4b1990499ba6a7f78d5b1061f8`，Linux=`85d2e3f05a4847abbea75648d11a1de2`。不是只检查 status=passed 或只比较 mode。

## 清理和结论边界

两份 `cleanup.json.failures=[]`。Mac `commands.jsonl:L35/L36`、Linux L36/L37 为两个档案 stop-on-demand exit0/ok:true；`service-events.json` 记录 Hub PID73431 /154230 均在 stop_requested:true 后 exit-15，与冻结控制器的显式终止逻辑相符。两次 result 均在清理后结束，finished分别为08:28:13.185573Z、08:30:01.968174Z；未将仍运行任务当作通过。

最终传输状态两者均complete、allowed_pending0、inflight0，但当前规则none、not_confirmed5；这只能表示当前允许范围无待处理，**不是5条正文已补传**。新鲜CLI中间 all 状态仍backfilling。本专项没有等待/断言完整正文到达、查询读回或幂等，因此不能推导正文补传成功。

这些新运行能证明 ba8c6d5 在两平台的旧值拒绝/缺参拒绝、新鲜双版本 CLI、刷新 Web采用Hub及兼容 CLI无版本参数采用Hub的指定结果；没有在首次/第二次Hub读取或CAS前注入真实并发，因此本意见不单独判定更深竞态修复是否全面成立。那部分应引用对应新反例/源码/独立修复复核，而不能让平台短流程取代。

旧15运行和旧意见仍绑定7c72c92，未改标；Hub模块相同仅支持字节边界说明，不创造新的旧服务执行。本意见未审Windows21，也未覆盖完整三入口检索、真实系统级Hub生命周期、兼容/恢复或A1–A12矩阵；不认领R005整体通过。
