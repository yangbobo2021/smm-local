# 新 SPEC 的平台补充验收（2026-11-17）

本轮按已合并的 SPEC #24、PLAN #25 补齐 PR #21。验收 ID：`AT-SMM-VIBEINSIGHT-003`，采用定义快照摘要 `1be6849c…6db9`。

**正式执行与独立执行复审：15/15 通过。最终需求交付判定与 PR Review：见本目录后续独立审查记录。**

| 范围 | 实际环境/入口 | 结果及原始响应 |
|---|---|---|
| Linux Hub H1–H9 | Ubuntu 22.04.5，systemd 用户服务，UID 1000；本机 psql 14.24 | [完整结果](hub/linux/result.json)、[服务及 psql 子进程](hub/linux/H1-service-psql-process.json) |
| macOS Hub H1–H9 | macOS 15.3.1 arm64，系统级 launchd，普通运行账户 UID 501；psql 14.17 | [完整结果](hub/mac/result.json)、[服务及 psql 子进程](hub/mac/H1-service-psql-process.json) |
| Windows Hub H1–H9 | Windows 11，LocalService；本机 psql 14.25 | [完整结果](hub/windows/result.json)、[服务及 psql 子进程](hub/windows/H1-service-psql-process.json) |
| 自行管理 P | macOS，独立 Hub wheel，公开 `serve-hub --state-dir`、真实 HTTPS/SQL | [完整结果](standalone/result.json)、[启动/PID/退出](standalone/P-process-events.json) |
| 三平台 C | 三个实际普通本机进程；各自 CLI 和真实 stdio MCP，Windows 使用 Limited 交互任务 | [Linux](clients/linux/verify/result.json)、[macOS](clients/mac/verify/result.json)、[Windows](clients/windows/verify/result.json) |
| 共用 G | 真实 systemd Hub、受控 PostgreSQL、默认参数化回归 | [完整结果](shared/result.json)、[新目标换凭据后的真实续跑](shared/G4-replaced-credential-continuation.json) |

三平台服务均实际观察默认 300 秒周期，完成旧会话 **6→10 条（3→5 轮）**、停机期间新会话、重复轮次、无新增重启、完整游标与原文保留、坏配置不覆盖、批中事务回滚、故障恢复后的独立新增内容。启动、停止、重启经过真实系统服务管理器；不是前台进程代跑。

C 的每个入口分别验证自己的项目范围、每个直接关联目标的独立命中、自己返回的两类精确引用、旧引用、本机关系、断线全局回退与恢复、实际不同显示名及稳定身份。旧进程实际加载模块的 SHA 对照 `d2dee18`；本设备三段会话在补传前后从 Hub 完整读回，逐条核对 ID、位置、角色、正文、时间和总数。[示例：Windows 补传前](clients/windows/prepare/C6-before-metadata.json)、[补传后](clients/windows/prepare/C6-after-metadata-full-conversations.json)。

## 复审及复算

- 正式收据：[三平台服务](native/execution-services-v1.json)、[自行管理](native/execution-standalone-v1.json)、[三平台客户端](native/execution-clients-v1.json)、[共用边界](native/execution-shared-v1.json)。包含实际命令、退出码、时间及输入/附件摘要。
- 独立执行复审：[H](reviews/review-execution-services-v1.json)、[P](reviews/review-execution-standalone-v1.json)、[C](reviews/review-execution-clients-v1.json)、[G](reviews/review-execution-shared-v1.json)。每项仅认领自己的检查。
- H 追加前的原消息 ID 与各阶段真实精确 HTTP 读取，另作可重跑的纯证据复算：[Linux](hub/reference-audits/linux.json)、[macOS](hub/reference-audits/mac.json)、[Windows](hub/reference-audits/windows.json)。原始文件未改写。完整复跑入口及顺序见[探针指南](../../../../scripts/acceptance/README.md)。
- [覆盖表](coverage.md)、[环境与版本](environment/platform-environment.json)、[来源清单与脱敏前后摘要](manifest.json)、[定义快照](acceptance-definition.json)。

## 证据边界

Linux 没有管理员认证方式，**没有执行另一 UID 的 open**。该项用真实服务成功同步、所有者、0700/0600 模式和完整数字 POSIX ACL 支持“其他非特权 UID 在 Linux DAC 下不可读”的推论，独立复审已明确认可此验证方法；不包括特权管理员绕过 DAC。[原始权限审计](hub/linux/H9-posix-access-audit.json)。macOS、Windows 则实际用另一身份尝试读取并遭拒绝。

连接故障采用隔离源读角色的 `NOLOGIN`，另有缺失/不可执行的任务专用 psql 故障；恢复后每类都实际导入新的两条消息。CLI/MCP 断线通过本机透明中继停止转发产生；没有停止用户现有 Hub。

只在两次独立测试轮次之间，用已停止的**任务专属** Hub/Q 快照重建前置条件；不穿插被测重启/故障过程，不作为产品恢复能力。[基线摘要](environment/baseline-public.json)。

本轮没有重新连接真实 VibeInsight staging，也没有向真实服务器造数。原 [2026-11-16 staging 回执](../staging-2026-11-16.json)保留其原日期、版本、142 项目/20,325 会话/113,256 消息及脱敏范围，不能拿它代替本轮平台证据。新数据全为隔离合成事件；[只读 SQL 示例](hub/linux/H1-readonly-sql.json)只含读账号语句，不含管理员建库/密码语句。

历史消息无新增事件的原地改写不覆盖旧档案；每项目从已提交位置回看 24 小时，窗口外迟到事件不保证发现；新项目及新连接目标补齐早期历史。默认回归/CI 使用 UTF-8，不宣称验证了旧式 ANSI 控制台兼容性。

## 回归、失败历史与复用

[本机全量](regression/final-pytest.log)为 83 passed、1 skipped；Windows 专用用例在实际 Windows CI 执行。[三平台 CI](environment/ci-results.json)包含各系统测试、构建及两个 wheel 的独立安装/CLI-MCP 基本入口；它不代替系统服务验收。另重新执行[真实 SQL](compatibility/current-postgres.json)及[旧 Hub 档案升级](compatibility/current-upgrade.json)探针。

旧预演的 `dirty:true`、旧提交和失败记录不改成新成功；新结果用安装模块字节、wheel SHA、探针源码 SHA 与实际执行版本关联。产品 Python 文件在本轮构建后保持相同，较后变更限验收工具、测试夹具、CI 和文档；环境清单逐文件核验了字节等价性。

保留[首次准备审查](reviews/preparation-review.md)、各轮逐 TC 意见及[调试历史索引](attempts.json)。早期包括缺依赖/ACL/代理/控制器错误、60 秒回归超时及断言漏检；这些不是正式通过。首轮 CI 的已退役 macOS runner、Windows 路径/编码/换行、解释器 `.exe` 和启动就绪重试修订，见计划第 10 节及 Git 历史。正式轮次的输出目录全新，原失败不覆盖。

公开文件只保留合成正文、稳定别名、数值、结果及代码/产物摘要；连接地址、私有账户、任务目录已替换。没有凭据文件、私钥、原始 PostgreSQL 日志或真实私有正文。`manifest.json` 区分原始输入 SHA 与脱敏文件 SHA，不把脱敏副本当作原始字节。
