# Windows21 清理事后只读观察补充

结论：**2026-11-22 08:40:53.8926777 UTC 的只读快照，支持所查询任务根目录对应的调度任务、Python进程、18921监听和两个服务端点文件均未被观察到。** 这补足原 `review-platform21-windows.md` 中“缺少调度删除事后快照”的取证边界；原意见原件保持不变。本补充不改写早先运行，也不扩大到历史档案或其他路径。

实际读取并逐项核对：

- `.acceptance-local/native-v1/AT-SMM-005/work/final21-cleanup/windows.json`：ssh_exit_code=0；observed.tasks=[]、processes=[]、hub_listeners=[]；service_files.local/remote均false。
- 同目录 `windows-command.ps1`：只调用Get-ScheduledTask、Get-CimInstance、Test-Path、Get-NetTCPConnection及时间/JSON输出，没有停止、删除或其他清理修改动作。
- 原 `platform-debug/windows-reconcile21` 的result、outer-process、service-events与commands，以及原任务配置 `<task-path> 的work/port/解释器字段。

原任务在08:35:59.812417 UTC结束；新快照比它晚约294.080秒。原worker PID13852记录exit0；Hub PID12824于08:35:59.780414Z在明确stop_requested后退出1；两个档案stop-on-demand在08:35:56.003661Z及08:35:59.202344Z均exit0。快照不是这些actor尚在运行时的中途采样。

具体查询范围与证据含义如下：

| 对象 | 实际过滤/路径 | 当前快照结果 |
|---|---|---|
| 调度登记 | TaskName匹配 `SmmSelective005-*` 且Actions.Arguments包含 `<task-root>` | 空集合；包括使用该根下worker脚本的Windows21任务 |
| 进程 | Name为python.exe且CommandLine包含上述任务根 | 空集合；原Local/Hub解释器均位于该根，匹配范围正确 |
| Hub监听 | Get-NetTCPConnection，LocalPort18921，State Listen | 空集合；原任务实际Hub配置端口就是18921，不把relay的52019混作该端口 |
| Local端点文件 | `<task-root>\reconcile21\local\archive.sqlite3.service.json` | Test-Path=false |
| Remote端点文件 | 同任务根 `reconcile21\remote\archive.sqlite3.service.json` | Test-Path=false |

端口查询的无匹配错误由脚本显式SilentlyContinue处理，其余脚本使用ErrorActionPreference=Stop；此处结论严格表述为该命令成功返回的观察结果，不额外宣称做了连接探测。任务/进程过滤也不覆盖不同名称、无该根参数或其他类型的任意进程。本快照证实当前时点范围内无残留登记/进程/监听/端点文件，不能推断此前每一时刻都不存在，也不能证明未来仍不存在。

本次查询没有检查或删除archive.sqlite3、来源会话、历史安装环境或证据目录；**不宣称历史档案已删除**。原Windows21的产品对账结论和transfer_state=failed、正文补传未验收等限制全部保留，不由这份清理补充提升为R005整体通过。

原始观察SHA256：windows.json=`98fb9e722bd61605d874ada37c874daeb7a43d684d4b046c278d6e0cffd3d7aa`；windows-command.ps1=`6be96fe3068f58a0295843c25de2c5328875750a889dd51f5ecd7fbcfc7c1929`。
