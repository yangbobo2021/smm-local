# 候选包实际验收（进行中）

产品源码提交 `d80de6731d681ca06276dd6231a1eb77c0a7111c`。后续 `7ab6d6c`、`06dd2ef` 仅增加测试/控制器/计划和记录，产品模块字节相同。两个 wheel 及实际安装文件的完整 SHA-256 见各 `manifest.json`，不可仅凭未发布的包元数据 `0.4.0` 与正式旧版区分。真实旧版来自 tag `v0.4.0`/`4d58202f60d8dfa1292e0feae28447e115d08cd9`，使用另两个环境并验证完整模块。

本目录均为实际运行的脱敏导出；没有连接实际 VibeInsight/PostgreSQL，没有在服务器造数。`provenance.json` 保留原始文件与导出文件摘要、当轮控制器摘要。本文仍是中途证据，不代表完整 A1–A12/E1–E5 验收通过。独立[实现审查](reviews/pr30-final-06dd-review.md)确认 P1 过期对账视图可能提交另一条本机规则、P2 范围读取标题带出范围外正文，均需修复；本目录不代表可合并版本。另需补齐各 E1 的离线全项目三入口和各 E3/E4 的共享会话分项目读取证据。

| 环境/专项 | 当前证据 | 状态与边界 |
|---|---|---|
| macOS E1/E4 | [manifest](mac-run8/manifest.json)、[result](mac-run8/result.json)、[真实三入口](mac-run8/combined-stopped-cli-search.json)、[归属传播](mac-run8/affiliation-propagation.json) | 核心流程通过；独立 serve-hub、重启拒绝旧批次、补齐及原文 |
| macOS E2 | [manifest](mac-login-run8/manifest.json)、[result](mac-login-run8/result.json)、该目录 `login-service-*.json` | 核心流程通过；真实任务 LaunchAgent 定义、普通 UID/PID 及重启，不以 Hub 前台事件替代登录服务证明 |
| Ubuntu E1 | [result](linux-client-run8/result.json)、[manifest](linux-client-run8/manifest.json)、[归属传播](linux-client-run8/affiliation-propagation.json) | 普通用户真实 CLI/MCP/Chromium 核心流程通过 |
| Ubuntu E3 | [result](linux-hub-service-run8/result.json)、[service-events](linux-hub-service-run8/service-events.json) | 实际 systemd 用户服务核心流程通过，不宣称此项含浏览器 |
| Windows E1/E3 | [普通用户](windows-client-run8/result.json)、[LocalService](windows-hub-service-run8/result.json)、[安装身份](windows-hub-service-run8/manifest.json) | 本轮主流程通过且cleanup无失败；不代表尚缺的离线全部/分项目共享会话验证 |
| macOS E3 | 尚无本轮实际运行 | 用户已表示稍后认证；系统级 launchd 必须实际验收，仍为必需未验证项 |
| macOS/Linux/Windows 真实旧版组合 | [Mac](compat-run8/result.json)、[Linux](linux-compat-run8/result.json)、[Windows](windows-compat-run8/result.json) | 组合实际通过；新旧环境/模块摘要另在各目录，不是伪造协议旧版本 |
| R1/R2 | [R1](restore-r1-debug8/result.json)、[R2](restore-r2-debug8/result.json) | 实际安装包恢复流程通过 |
| R3/R4 | [R3](restore-r3-debug8/result.json)、[R4](restore-r4-debug8/result.json) | 实际 Linux systemd 用户服务；R4 真实升级失败/恢复控制流程，离线安装成功桩不验证发布下载安装 |
| A5 真实隔离 | [结果](isolation-run9/isolation-result.json)、[范围](isolation-run9/result.json) | 甲停 A 后，同设备关联 D（规格示例 B）、设备乙和合成 VibeInsight 新内容继续；完整正文/旧引用/禁止载荷逐一断言 |
| 显式本机与全部项目的三入口补验 | [macOS](mac-entrances-run10/result.json) | 实际 CLI/MCP/Web 按独立夹具逐条读原文；[Linux](linux-entrances-run10/result.json)通过；[Windows失败](windows-entrances-run10-failed/result.json)保留，旧自动扫描被当作新扫描的前提问题已补控制器/自检，待新轮；不扩大为完整E1判定 |

`regressions/full-pytest.txt` 是该产品版本的 179 passed、1 skipped；之后新增5项补强测试独立执行通过，不能把此日志改写成后来的全量结果。新的最终全量与三平台 CI 另行追加。

新增已确认 B3/A3 的实际证据：各主流程 `affiliation-propagation.json` 使用夹具 D 作为目标 B，先禁止 D 后改归属，不发会话指纹/正文；允许 D 后仅核对已有消息，按 D 能读完整两轮，A 旧引用仍只读原有一轮，前后物理正文行相同。共用回归另外覆盖 assign/map/merge、两段会话各两条消息及丢确认重试。

完整检查分工仍需最终 A/E 矩阵与独立审查；缺少系统级 Mac 服务时不得标为交付通过。所有 `cleanup.json` 和退出码需与对应成功结果一起核对，旧失败结果不重标。

更新：后续f45da53已修复范围标题并有同版独立红/绿灯；本目录仍保留d80已知缺陷时的原始证据与审查，不把旧轮重标为修复后的版本。对账输入补充草稿待确认，未修改确认规格或该实现。
