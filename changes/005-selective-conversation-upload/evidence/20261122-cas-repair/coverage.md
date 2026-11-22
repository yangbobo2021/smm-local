# 最终候选的验收依据映射（待独立判定）

产品提交 `ba8c6d5`。此表提供逐项复核入口，**不代替独立判定，不表示 PR 已可合并**。最终新包三平台补验与正式执行复审正在回收。

f45→7c只改变Local API/CLI/upload/HTML；7c→ba8只改变Local upload，全部Hub模块字节相同。当前修复针对reconcile提交顺序及回执条件保存，常规choose、候选/正文上传、排序、范围和读取方案保留；`_save`的普通调用沿用原分配新submission/保存pending，新增已确认回执分支只由对账显式使用。平台证据保留实际版本，不重标为ba8执行。最终包module comparison另存。

| 条件 | 实际依据与版本 | 需核对的边界 |
|---|---|---|
| A1 默认/入口/参数 | d80三平台主流程；7c三平台reconcile15实际旧值/缺参数/fresh；ba8 final20 SC1及最终包reconcile21 | 新连接只登记、四模式/空名单共用测试；已安装CLI帮助/Web真实入口。最终包结果以新manifest为准 |
| A2 停止/暂停/竞态 | d80主流程/各真实服务重放；Mac登录f45；ba8 SC2正式执行、12组合远端竞争、在途回执、控制派发回归 | 两端版本/本机写窗口、CAS拒绝无规则改变、未知不当成功；派发后的新保存不得被旧回执覆盖 |
| A3 全局/归属/登记 | 三平台主流程Web；三平台global-cli11强制重放；ba8 SC3正式执行全部7TC；Mac系统main15、Linux/Windows真实Hub服务 | G实际完整集合唯一；assign/map/merge全部受影响消息、预览/旧确认无副作用；最终新测试强制3文件重放并比较完整归属 |
| A4 全量补齐/幂等/公平 | d80三平台完整停止→新增/追加→允许→全部读回；Mac登录f45与Mac系统main15；SC4独立核心正式结果与当前完整回归 | 35条独立完整集合及顺序、单项目失败不饿死另项目、未知回执不确认、物理正文/旧引用不变 |
| A5 隔离/保留 | d80 isolation-run9真实HTTPS、其他设备与合成VibeInsight；三平台真实Hub主流程 | 限制不删除旧副本，关联项目/其他来源继续；managed设备旧式上传不能绕过，新协议仍可提交 |
| A6 联合范围/候选 | d80三平台主流程CLI/MCP/Web；mac/linux-entrances-run10，f45 windows-entrances-run14；SC6/共用范围快照测试 | A/B一层、排除C/D、各入口自己引用逐条原文；显式本机/全部项目准确3/7/10目标；两端各N不扩召回 |
| A7 排序/隐私 | SC7独立修订后正式结果；当前完整回归；三平台主流程真实payload/独立离线audit | 独立BM25公式、精确身份与内容版本、长消息尾部、平局；本机禁止内容没有因重排外发 |
| A8 引用/范围/冲突 | 三平台主流程同号与各入口读取；f45三平台scope11、Linux/Windows实际服务scope11；Mac系统scope15 | 新范围消息与标题只X，旧无范围Y+X兼容、扩大start-end不越界、重启旧引用；原文/引用共用负例 |
| A9 回退/部分失败 | d80三平台主流程按A断线与恢复；f45三平台scope11离线全部；SC9与共用故障回归 | 按A回退仅A、全部回退所有本机项目、解释未查Hub；不同失败不伪装完整零结果/扩大范围 |
| A10 真实新旧组合 | d80 mac/linux/windows compat-run8，真实正式v0.4.0四环境；f45旧无范围读 | 新遇旧Hub不传正文、能力限制明确；同设备旧写门禁、未迁移旧设备兼容、旧游标/引用与目标身份边界 |
| A11 生命周期/恢复 | d80 E1、R1–R4真实恢复；f45 Mac登录、Linux/Windows服务；Mac系统main15/scope15；ba8 SC11及SC2正式执行 | 原目录/真实服务重启仍限制、旧原文可读；本机/Hub恢复与升级失败保护；CAS先接受后条件保存；R4离线安装成功桩边界保留 |
| A12 使用发现/判定 | README→TRIAL_GUIDE→实际CLI/Web/Skill；独立PR审查current16已逐角色回放，ba8最终审查进行中 | 用户/调用方/维护者入口、ID与版本取得、四模式、旧副本、逐条reference、暂停/恢复/排错一致；全部必需证据后才判交付 |

| 环境 | 实际任务 |
|---|---|
| E1 macOS | mac-run8 + mac-entrances-run10 + mac-scope-run11 + mac-global-cli11 + reconcile15，最终ba8 reconcile21 |
| E1 Linux | linux-client-run8 + linux-entrances-run10 + linux-scope-run11 + linux-global-cli11 + reconcile15，最终ba8 reconcile21 |
| E1 Windows | windows-client-run8 + windows-entrances-run14 + windows-scope-run11 + windows-global-cli11 + reconcile15，最终ba8 reconcile21；均普通交互token |
| E2 macOS登录 | mac-login-run11真实专用LaunchAgent，禁止/重启/本机可查/允许补齐 |
| E3 Linux | linux-hub-service-run8 + linux-hub-scope-run11真实systemd用户服务 |
| E3 Windows | windows-hub-service-run8 + windows-hub-scope-run11真实LocalService，CIM实际owner与重启PID |
| E3 macOS | mac-hub-main15 + mac-hub-scope15，系统LaunchDaemon UID501/PPID1，实际重启/补齐/范围原文；两个plist均已移除 |
| E4 自管 | mac-run8实际独立serve-hub，原目录停止/再启动；scope11另外补范围标题 |
| E5 兼容/恢复/共用竞态 | 三平台真实0.4.0组合、R1–R4、R5/R6共用回归；当前控制/引用/排序/恢复测试与独立执行记录 |

旧结果入口：[d80](../20261122-candidate-d80de67/README.md)、[f45](../20261122-scope-f45da53/README.md)。[7c与Mac系统服务证据](../20261122-reconcile-7c72c92/README.md)及其独立五次实际运行审查，明确只认领每次实际范围。部分scope生产者通用标签提到offline-all，但protocol_only实际服务轮未执行浏览器/离线全部，不能据标签扩大认领。Windows旧入口失败与Win10053重试原件保留。R4不证明真实发布下载或未来迁移；005没有连接真实VibeInsight/数据库造数。
