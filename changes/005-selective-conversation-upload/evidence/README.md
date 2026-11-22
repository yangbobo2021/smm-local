# 005 验收证据（进行中）

当前 PR 仍为草稿，**尚未完成整体验收，不可据本索引判定可合并**。

最新进展：已确认并实现双版本对账、远端CAS先接受后本机条件保存，最终源码234 passed、1 skipped，80项专项、原4组21TC及补充5TC/14参数正式执行均获独立复审。macOS系统级launchd的主流程、范围读取和重启已实际通过且任务注册清理完成。最终新包三平台补验与独立SPEC审查已通过；原生登记因场景内外证据未全关联而blocked，待维护者确定登记收尾方式。当前证据见[CAS修复与最终候选](20261122-cas-repair/README.md)、[7c对账与Mac系统服务](20261122-reconcile-7c72c92/README.md)。

以下段落是早期 630610f 的历史记录；后续 [d80 候选](20261122-candidate-d80de67/README.md)与 [f45 专项](20261122-scope-f45da53/README.md)保留各自实际版本和失败，不改标为当前候选已通过。

## 历史候选与共享逻辑（630610f）

- 独立审查基线：`b76b68320d591a870cf9ac6b5090ca1e0f61e1f1`。发现两个 P1（晚到重复轮次漏传、切换目标后旧端仍启动上传）和三个 P2（时间戳版本错误确认、无效范围扩大回退、正文失败状态缺失）。[PR 审查记录](https://github.com/yangbobo2021/smm-local/pull/30#issuecomment-7074028944) 区分明确规格问题、未定义路径和证据边界。
- 无效范围修复：`8631be4`；另四项修复：`630610f`。保留实际反例红灯、独立复审、原样测试绿灯及独立绿灯复审。新包的 Local/Hub 全部模块摘要与各运行 manifest 一一核对，不以版本字符串判断新旧。
- [完整源码回归](20261122-interim/regressions/full-pytest.txt)：158 passed、1 skipped（macOS 跳过 Windows 专属项），实际源版本 `630610f`。另有[六项派发边界](20261122-interim/regressions/dispatch-boundaries.txt)通过；后续新增两个同名/改名/全局查询边界回归分别通过，尚不借此重述成同一轮完整 160 项结果。
- 当前构建仍是未发布候选，包元数据为 0.4.0；正式 `v0.4.0` 与候选分别用来源提交、wheel SHA-256 和全部安装模块 SHA-256 区分。没有发布、升级日常 SMM 或合并本实现 PR。

## 实际平台与恢复记录

[运行索引](20261122-interim/run-index.json) 保留每轮原始 candidate/结果。所有条目是已实际执行的**调试/补充验证**，不能替代最终正式执行和完整覆盖判定。候选源码提交可能不同，但下列运行的安装模块清单均对应 `630610f` 的产品字节；之后仅变动验收控制器、测试或证据时，仍按实际 manifest 标识，不改写旧记录。

| 运行 | 已实际验证 | 原始结果与关键证据 |
|---|---|---|
| mac-run5 | macOS 15.3.1 普通客户端，CLI/真实 stdio MCP/Chrome；独立 serve-hub；四模式、归属预览、范围/全文/版本/长消息、断线恢复、停止与重启补传 | [结果](20261122-interim/mac-run5/result.json)、[安装摘要](20261122-interim/mac-run5/manifest.json)、[三入口配置](20261122-interim/mac-run5/browser-configuration.json)、[CLI](20261122-interim/mac-run5/combined-stopped-cli-search.json)、[MCP](20261122-interim/mac-run5/combined-stopped-mcp-search.json)、[实际页面](20261122-interim/mac-run5/combined-stopped-search.png)、[清理](20261122-interim/mac-run5/cleanup.json) |
| mac-login-run5 | 真实专用 LaunchAgent；停止积压后登录服务重启，不重配，仍禁止；允许后补齐/幂等 | [服务身份与事件](20261122-interim/mac-login-run5/service-events.json)、[重启状态](20261122-interim/mac-login-run5/local-restart.json)、[补传](20261122-interim/mac-login-run5/backfill.json)、[结果](20261122-interim/mac-login-run5/result.json) |
| linux-client-run2 | Ubuntu 22.04.5 普通客户端、CLI/真实 MCP/该机 Chromium；完整核心入口流程 | [安装摘要](20261122-interim/linux-client-run2/manifest.json)、[CLI](20261122-interim/linux-client-run2/combined-stopped-cli-search.json)、[MCP](20261122-interim/linux-client-run2/combined-stopped-mcp-search.json)、[结果](20261122-interim/linux-client-run2/result.json) |
| linux-hub-service-run2 | 真实 systemd 用户服务；版本/无版本旧请求在限制和 Hub 重启后仍拒绝，精确原文及补传 | [实际服务](20261122-interim/linux-hub-service-run2/service-events.json)、[重启后重放](20261122-interim/linux-hub-service-run2/after-hub-restart-replay.json)、[结果](20261122-interim/linux-hub-service-run2/result.json)。本轮为 E3 protocol-only，不冒充 E1 浏览器。 |
| compat-run3 / linux-compat-run1 | macOS/Ubuntu 各自四个独立环境，真实正式 0.4.0 与候选组合；同目标旧游标迁移、旧引用、旧写门禁、换 URL/实际换 Hub | [Mac](20261122-interim/compat-run3/result.json)、[Ubuntu](20261122-interim/linux-compat-run1/result.json)、[旧包身份](20261122-interim/compat-run3/old-smm-local-identity.json)、[实际迁移](20261122-interim/compat-run3/migrated-old-device.json) |
| R1 | 实际 Local prepare-restore、停止服务、旧允许库恢复、查看差异、明确采用 Hub 停止、允许后幂等补齐 | [恢复清单](20261122-interim/restore-r1-debug2/restore-preparation.json)、[差异](20261122-interim/restore-r1-debug2/difference-before-decision.json)、[结果](20261122-interim/restore-r1-debug2/result.json) |
| R2 | 独立 serve-hub 的旧数据库恢复，原控制保护保留，恢复后不自动开放正文 | [恢复清单](20261122-interim/restore-r2-debug2/restore-preparation.json)、[采用停止](20261122-interim/restore-r2-debug2/adopted-stop.json)、[结果](20261122-interim/restore-r2-debug2/result.json) |
| R3 | Ubuntu 实际 systemd 服务，配套 Hub 旧配置/库恢复，明确对账后仅补允许内容 | [实际服务](20261122-interim/restore-r3-debug1/service-events.json)、[恢复清单](20261122-interim/restore-r3-debug1/restore-preparation.json)、[结果](20261122-interim/restore-r3-debug1/result.json) |
| R4 | 实际已安装 Hub.upgrade、systemd 重启及健康失败后的恢复路径；失败前确认新的停止规则仍受保护 | [故障/恢复实际输出](20261122-interim/restore-r4-debug1/upgrade-failure-recovery.json)、[结果](20261122-interim/restore-r4-debug1/result.json)。**包安装为离线成功桩，候选字节未更换，不声称验证真实发布、下载或未来版本迁移。** |

这些流程均使用合成 Agent/插件对话与隔离 Hub 的合成 VibeInsight 归档；005 不连接真实 VibeInsight/PostgreSQL，不向外部服务器造数。各目录 `provenance.json` 保存私有原件和公开导出的分别摘要。公开导出替换测试机地址、用户名及绝对任务路径，未改合成消息正文，不导出 Token、证书私钥、数据库或输入配置。每次结果还须结合真实命令、具体响应与清理收据复核。

## 当时剩余项与已知失败（历史记录）

- Windows 第一轮遇到后台 CA 继承问题已修复；第二轮实际普通交互测试被验收包装器八分钟时限中断，不能据此判功能通过或失败。已停止该轮客户端、核对并清理任务进程；新轮使用延长的有界时限执行。Windows E1、真实 LocalService 和真实旧包迁移结果尚待回收。
- macOS 系统级 launchd Hub 必须按 E3 实际验证。管理员认证由维护者明确延期，普通进程、LaunchAgent 或 CI 不能替代该格。
- 原生工具单条自动执行最多 300 秒；Mac/Ubuntu 已用新状态重跑真实业务并收回原生调试附件，正在独立设计/执行证据复审。Windows 外部自动运行较长，其原生收据组织方式待落实，不能把旧 `result.json` 重新包装成新业务执行。
- README→指南→参数/状态/恢复入口回放、Skill/旧来源帮助及完整 A/E 矩阵仍需最终独立审计；场景级部分通过不能上升为 R005 整体通过。
- 已接收会话 A→B 改归属在 Hub 的新增归属传播尚待维护者确认。本次没有擅自撤回旧 A 副本或改变已确认 SPEC；对应独立审查的未覆盖路径保留。
