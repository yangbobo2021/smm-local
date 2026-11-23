# 007 验收证据（PR #39，未通过整体交付）

本实现采用已合并 SPEC #37、PLAN #38。产品源码最后变更为 `245c236ddc41057cd78694902283574d1175e309`；此后的修改属于验收工具、工作流、说明和证据，独立包全部模块逐 SHA 与当前源码核对。预览包中的 0.4.0 版本字符串不表示本功能已发布。PR 保持 Draft。


F8 修复候选正在刷新证据：`document_search.py` 的两个反馈字段已按 B6 保留已算覆盖/原因，新增无 Hub 配置回归六格及14项相关回归、独立包v5通过独立绿灯复审。SC6新增一项后为36TC（28自动/8人工）；本页下方35项索引及245c236产品的平台/回归原件仍是修复前快照，不能称当前新源码验收已通过。当前正式自动项、用户路径和完整回归/CI将以新源SHA另取；E1额外轮待决定，E2保留决定不变。

原生验收 `AT-SMM-007`：定义 000007，35 项（27 自动、8 人工）。[逐项索引](acceptance-index.json)列实际收据 SHA、公开登记索引、独立状态及认领检查，不以作者总结替代意见；`coverage=off/unknown` 不表示行覆盖率。完整私有记录、原命令、源指纹、请求及浏览器 trace 保存在本任务档案中，仓库只提交脱敏选件和索引。

| 范围 | 当前依据与实际边界 |
|---|---|
| 27 项自动正式验收 | 全部实际退出 0，逐项独立 passed，31 个检查；见[正式执行复审](../../../reviews/formal-execution-review-v1.md)。保留所有红灯、准备返修和旧版不足意见。 |
| 独立包 | Local/Hub 分开新环境安装，18 条命令、源码→wheel→安装全部模块 SHA；Hub 不安装 Local 发行包。实际平台安装另核 Local 30 / Hub 31 个模块。 |
| macOS E1 | v16 完整 CLI、两端真实浏览器和 stdio，按项目逐文档准确原文、选择/拖放/更新/删除、同步开关、一层关联、版本/暂停/失效撤回/共享资格/离线重连/重启、源指纹和实际 PID/端口清理。双向 8 次越端管理请求均拒绝，逐次 API/完整文档表摘要/管理副本 SHA、长度、mtime 保持；[独立人工复审 v3](../../../reviews/manual-mac-user-review-v3.md) passed。不是 launchd 或物理跨机器。后来共同平台探针的 stdio 私有/Hub原文及停启后 Web/stdio 检查缺证被独立指出，[Mac补审](../../../reviews/macos-protocol-recheck-v4.md)同样判 insufficient_evidence，不能继续把原 passed 当完整 E1 已满足。 |
| 用户发现、旧页与浏览器凭据 | README→指南→CLI/Web/Skill/复跑入口；两次真实旧页提交仍带原 KEY/HID/G，拒绝且完整新状态不变。实际 Chrome 四阶段核 URL/持久存储/cookie 无 token，同源认证头、刷新空壳/重选恢复。两创建端项目名、片段、原文中 script/img 只显示文字，无嵌入节点或触发请求；同上独立人工复审 passed。 |
| Ubuntu/Windows E1 | [222e0e5 的 E1 专项](https://github.com/yangbobo2021/smm-local/actions/runs/45205483868)已分别实际完成普通身份业务；当前加强后的纯文本和越端拒绝原件已完整回收；[独立 E1 复审](../../../reviews/e1-ci-manual-review-v1.md)仍判两项 insufficient_evidence：stdio缺私有/Hub原文读取，且停启后缺Web/stdio检查；有效局部证据保留。Windows 使用专有标准账户，不能用 runner 管理员冒充普通身份。 |
| 完整回归与常规 CI | 本机完整回归 334 passed、1 skipped（Windows 专属启动时限），已补独立进程原始退出收据。[独立门禁复审](../../../reviews/regression-ci-review-v1.md) passed，所记 [222e0e5 常规 CI](https://github.com/yangbobo2021/smm-local/actions/runs/45205399891)三系统测试/双包构建/分开安装全部 success；JUnit 各335项，Mac/Ubuntu329 passed+6 skipped，Windows330 passed+5 skipped。5个浏览器参数格因普通 test extra 不含 Playwright 跳过，Mac/Ubuntu另跳过 Windows 专属项；不可说三平台334全过。实际浏览器证据由正式用例/安装包业务另给；最终 PR head CI 另核。 |
| 两项实际服务 E2 | [465d27e 服务运行](https://github.com/yangbobo2021/smm-local/actions/runs/45201802511)实际成功，Ubuntu UID1001 user-systemd、Windows SCM LocalService SID S-1-5-19/session0，Windows普通Local不能读HubDB，管理CLI采集与服务身份分开。源采集/同步/两份Web原文和更新删除、外部采集资料移走后停启读取、PID/端口清理有有效局部证据。完整人工项仍为 insufficient_evidence，见下方缺口及[独立服务复审](../../../reviews/services-manual-review-v1.md)。 |
| 不同 OS 不同机器 E2 | 未执行。维护者已禁止家庭 ESXi，且确认暂无非 ESXi 替代机器；托管同宿主服务和两份逻辑档案均不能替代，原生已记录 uncertain 并独立判证据不足。 |

当前另发现的 E1 缺口：stdio 对本机私有及 Hub 自有文档只有检索、没有实际 read_document 原文；PLAN 明写的重启后 Web/stdio 读取也尚未执行。两平台已独立判证据不足，Mac已独立重核为证据不足，原 passed 保留为历史；准备了只补 E1、不执行服务的草稿，额外轮等待维护者决定。

当前按维护者决定保留的 E2 必要缺口：Ubuntu 与 Windows 服务停启后，尚未再次按项目检索并用原有效引用读取网页上传资料（旧证据只重读外部 CLI 采集资料）；Windows 另缺服务及防火墙规则删除后的不存在查询；真实跨 OS 不同机器 HTTPS 未执行。这些是验收证据缺口，未确认产品失败。维护者明确选择“保留缺口，先完成其他验收”，因此不应用补证草稿、不继续这两项服务重跑，也不将整体需求标为 passed 或合并。

CI 原件以公开 X509 证书加密完整 trace，本机验证 artifact API 外层摘要、ZIP CRC、逐份内层 SHA，并解密逐原件 SHA 核对；私钥、token、数据库、签名保护材料、wheel 和原配置不入仓库。脱敏选件及原/公开 SHA 在 `public-manifest.json`；派生摘要明确标明，不冒充原始业务输出。[复跑说明](../../../scripts/acceptance/README.md)描述 E1 与全服务模式，执行说明本身不代表通过。

[PR Review v1](../../../reviews/pr39-review-v1.md)的 F1–F4 已由[v2](../../../reviews/pr39-review-v2.md)核对关闭；v2 的文件元信息、暂停保留状态、目录拖入指引三项有[独立同测试绿灯](../../../reviews/status-green-review-v1.md)。本轮最终 PR Review 与逐需求交付判定将按现有通过项和保留缺口收尾。未访问日常 Hub/VibeInsight、未使用被排除 ESXi、未发布或升级本机安装。

在仓库根运行 `python3 scripts/acceptance/hub_documents_verify_evidence.py`，校验全部公开文件的长度/SHA、35项唯一身份及收据索引对应。原件在作者本机时可加 `--original-root /private/tmp` 同时核原SHA。输出的 `integrity=passed` 仅代表字节与索引一致，业务结论须看逐项状态和独立意见。
