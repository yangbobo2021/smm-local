# 新 SPEC 的提交记录

维护者在检查真实项目生成结果后要求“提交新SPEC，创建PR”。本 PR 据此将整理后的规格写入
[`changes/003-search-vibeinsight-conversations/spec.md`](../../changes/003-search-vibeinsight-conversations/spec.md)，
供维护者审阅确认。没有修改 PR #21 的分支、产品代码或当前实施计划；规格确认后再按流程更新 PLAN 与验收。

## 原始生成与提交稿的区别

[spec.regenerated.md](spec.regenerated.md) 仍是一次独立生成的逐字原文，生成回执及其哈希不变。
提交稿是基于该原文、旧规格已确认场景和项目资料整理的提案，不冒充模型原样生成。
[comparison.md](comparison.md)保留整理前的观察与待补强项；以下说明本次如何处理这些问题。

| 整理项 | 依据及处理 |
| --- | --- |
| 三平台重启续写链 | 将 PR #21 原第 2 条的 3→5 轮、新会话、同一汇总会话标识、顺序、重复同步和进度保留，明确纳入 Windows/LocalService、Linux/systemd 用户服务、macOS/配置账号 launchd 服务各自的验收。另覆盖已提交且无新事件时重启仍可读旧档案。 |
| 关联图与同名项目 | 保留原 A—B、A—C、B—D 图及 A/B 两端结果，能够真正验证反向范围与二层排除；恢复两设备同名但只关联一个的区别场景及旧归属补传前/后引用保持。 |
| 未批准的来源停用 | 移除原生成稿中新增来源停用入口及其在途规则的必过要求。保存有效配置即自动同步，服务启停沿用既有 Hub 入口，不增加来源级或按项目开关。 |
| 周期及非法值 | 将 PR #21 已采用的默认 300 秒、整数且不小于 1 秒明确为本 PR 的规格提案，非法值不能覆盖有效配置。周期指调度间隔，不是完整导入的时限保证。 |
| 回看窗口边界 | 明确 PR #21 的 24 小时回查设计：相对于项目已提交 `created_at` 回看，不是恢复时只看墙上时间最近一天。未同步项目补拉历史不被窗口截断；可见时早于回查下界的迟到事件不承诺发现。 |
| 来源身份 | 明确 PR #21 以数据库主机、端口、数据库名组成来源身份的选择，同目标凭据更新沿用进度，目标身份变化隔离进度/去重但保留原归档；与仓库项目身份分开。 |
| 验收环境与真实数据 | 可以使用合成事件及隔离来源完成实际服务集成，不要求在真实服务器造数；真实来源查询保持只读事务。执行结果仍放在实现 PR，不写入 SPEC。 |

其中数值参数和来源身份是在 PR #21 已选实现中的具体技术选择，原早期规格未完全写明，
本 PR 将它们作为可审阅的规格提案列出供确认，不声称维护者之前已逐项确认这些数值。
没有增加新的来源读取能力或测试执行结果。

## 可复核的设计来源

相关来源固定于 PR #21 提交 `cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd`：

- [原规格第 2–4 条](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/changes/003-search-vibeinsight-conversations/spec.md#L45)：续写、关联图、同名/改名及历史归属场景。
- [Hub CLI 参数和入口](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/src/smm_hub/hub_admin.py#L57)：配置成功启用同步，周期默认 300；来源命令为 configure/status。
- [连接值校验](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/src/smm_hub/vibeinsight_settings.py#L29)：端口及周期合法性；[来源身份](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/src/smm_hub/vibeinsight_settings.py#L97)。
- [24 小时窗口常量](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/src/smm_hub/vibeinsight.py#L24)及[按项目进度构造回查下界](https://github.com/yangbobo2021/smm-local/blob/cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd/src/smm_hub/vibeinsight.py#L264)。

源文件及提交稿的摘要另存于 `submission.json`。这只是静态设计核对，未启动 Hub、访问数据库或执行新增平台验收。
PR #21 现有 macOS 及历史 staging 证据不能自动证明新 SPEC 的 Windows/Linux 条件通过。
目录内 Git 属性只保留冻结输入的原文行号空白及 diff 上下文，不格式化改写模型输入，也不放宽正式 SPEC 的检查。
