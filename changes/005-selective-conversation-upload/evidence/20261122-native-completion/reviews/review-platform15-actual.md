# AT-SMM-005 R005：platform15 五次实际安装证据独立复核

结论：**五次运行在下列限定范围内证据相互吻合，可以支持其专项结果；不能认领 R005 或 E1/E3 全矩阵整体通过。** 未在本范围新确认产品失败。此意见只读核对既有实际执行，没有重新运行产品，也没有修改产品、控制器、SPEC/PLAN 或原始附件。

本轮实际读取仓库 `AGENTS.md`、005 `intent.md`、`spec.md`（尤其 B1、E1/E3、A1/A2/A3/A4/A6/A8/A11）及 `plan.md` §12/12.1。AGENTS 的阶段确认、验收证据和独立审查要求照常适用。本意见不是维护者的阶段确认，也不是 nativecases 登记输入。以下附件路径均相对于 `.acceptance-local/native-v1/AT-SMM-005/`；`commands.jsonl:Lx` 指实际 JSONL 行号。

## 版本与执行身份

五份 `platform-debug/<run>/manifest.json` 的 candidate 均为干净 `7c72c92e902cae9b05b80ce829b516113292b17d`。逐份核对 `installed.local.files` 全部 **25** 个 Python/HTML 文件、`installed.hub.files` 全部 **24** 个文件，均等于 candidate 清单，且与各 `commands.jsonl` 的隔离解释器 `-I -X utf8 -c` 实测 stdout 完全一致；两个安装环境均 `other_package:false`。独立按 git 对象复算全部 Local 与 Hub/vendored 模块 SHA，亦吻合；不是只核对包名或少数变更文件。

现存 `dist/packages/` 两个 wheel 的完整字节与五份 manifest 一致：Local SHA256 `9d8fbd7bbc27c560c06aa8f054e335fcd2c9852fa063f3682c19fec5eabe35be`；Hub `3cfef6cf52176b17ee5443be49ef9ac34428f58ae6f44972cbeb62dc6c656ccd`。wheel 中全部产品文件集合和 SHA 也分别恰为 25/24 项。三份浏览器 trace 实际返回的 HTML 均为 29390 字节，SHA `1afcb4a170768ba79fe43647febe010c5aa2ea7030cd79dce05310db87f25599`，等于安装及 candidate 的 `smm_local/static/index.html`。

五目录冻结控制器相同：`selective_upload_platform.py` SHA `ec5329e6240493ad8142bb359478fe2cfd52612ca8eb9f6e0af2553a06f70a8f`，reconcile 为 `7400bfad874b4a667aa647c8135d13bd44fa04ae778444d493d2bb70c29e26fb`，scope 为 `eb42b7af7b66f4ac7c6d7e26fa18d2c715fb22c0d44e8930c635ed184fc12636`。三份 trace 的 source 附件均包含逐字匹配的冻结 reconcile 控制器。产品子进程清除开发 PYTHONPATH 并使用独立安装解释器；合成数据夹具及 HTTPS relay 的边界已在冻结源码明确。

| run | 实际身份/系统 | 仅可支持的范围 |
|---|---|---|
| mac-reconcile15 | <ordinary-user>，UID 501；macOS 15.3.1 arm64 | E1 新包 CLI/Web 双版本对账专项 |
| linux-reconcile15 | <ordinary-user>，UID 1000；Linux 6.8 x86_64 | 同上 |
| windows-reconcile15 | <ordinary-user>，`elevated_admin:false`；Windows 独立安装 | 同上；`outer-process.json` PID 11440、exit 0；冻结包装器使用 Interactive/Limited 并在 worker 内检查非管理员 token |
| mac-hub-main15 | system LaunchDaemon，运行 UID 501，PPID 1 | E3 API/CLI/真实 stdio MCP 核心流程，无浏览器主张 |
| mac-hub-scope15 | system LaunchDaemon，运行 UID 501，PPID 1 | E3 共享消息范围/标题及重启旧引用专项 |

## 三平台对账：专项成立

实际查看三平台各 3 张 PNG 原图，共 **9 张**：`stale-local-rejected.png` 红字“本机规则已改变，请重新查看对账差异”；`stale-hub-rejected.png` 红字“Hub 规则已改变，请重新查看差异”；`adopted-hub-current.png` 为双方确认/全部不上传。三份 `reconcile-browser-trace.zip` 均逐项解析实际点击、请求体和响应正文，并与 `reconcile-result.json` 精确比对：6 次 POST 的状态顺序均为 **200/400/200/400/200/200**。Mac 按钮 call@31 / call@63 / call@91、Linux ijfo@28 / @56 / @80、Windows gtsb@28 / @56 / @80 对应旧本机拒绝、旧 Hub 拒绝、新鲜采用 Hub；不是只读 result.status。

三份 `reconcile-result.json` 均呈现同一业务变化：

- 初始本机 none/generation 1，外部 Hub none/revision 2；断开任务 relay 后本机保存 all/generation 2、pending，Hub 仍为 none/revision 2。
- 旧 CLI 带 Hub 2/Local 1，exit 2 且 stdout 为空；实际旧页面 Web 同样发送这两个版本并 HTTP 400。缺 generation 的 CLI exit 2，明确要求 `local.generation`。该负例窗口 `rejected_policy_calls` 无 `/v1/upload-policy/set`。
- 负例前后本机仍 all/generation 2。Mac `commands.jsonl:L23/L26`，Linux 与 Windows `L24/L27` 直接证明；Hub 头未变由控制器真实 status 比较及 payload 记录支持。
- 新鲜 CLI 使用 Hub 2/Local 2，返回 all/generation 3/revision 3、confirmed。之后外部 Hub 收紧到 none/revision 4，旧 Web 使用 Hub 3/Local 3 得到400，本机仍 all/generation 3（Mac L30/L31；Linux/Windows L31/L32）。
- 刷新 Web 后实际发送 `{use:hub, expected_hub_revision:4, expected_local_generation:3}`，HTTP 200；最终本机 none/generation 4，Hub none/revision 5。页面无 pageerror；CLI help 实际包含新参数及其来源说明。

Windows 成功页同时显示“历史补传失败”，`adopted_hub_web.response.transfer_state=failed`、允许待确认0、已确认2。这与其后台在外部收紧期间留下的传输错误相符；规则 confirmed 与传输状态分别展示。**本专项没有以此证明补传完成**，也未据它新增一个已确认产品缺陷。Mac/Linux 最终 transfer_state 为 complete，同样不把短对账运行扩大为完整补传/搜索验收。

清理逐目录核对：`cleanup.json.failures=[]`；各自最后两个 CLI stop-on-demand exit0；Hub 服务事件记录显式 stop_requested=true 后退出（Mac/Linux -15，Windows1，符合冻结控制器的 Windows TerminateProcess 边界）。Windows 的外层0与 Hub 子进程被显式停止后的1是不同层级，不能混用。

## macOS E3：真实系统服务核心与范围专项成立

`mac-hub-main15/service-events.json` 与 `commands.jsonl:L4/L5/L62/L63` 共同证明：`system/ai.smm.hub.e3454cc838bf`，`type=LaunchDaemon`、`state=running`、`domain=system`，实际 `ps` UID501/PPID1，PID **57818→58048**；同一安装 Hub 解释器、同一 `<task>/hub-state`。`mac-hub-scope15` 对应 L4/L5/L29/L30、label `ai.smm.hub.9d5b68956b8a`、PID **58224→58288**。不能用 manifest 的控制器用户代替这些服务实测。任务 target 的真实目录分别为 `<task-path> 和 `<task-path> `protocol_only:true`。管理员脚本 `<task-path> 在 Terminal 执行 sudo -v 后启动任务；本轮不读取、记录或重做认证秘密。

main15 的负例与正例已从数据附件独立复算：

- `payloads.json` 中 4 次最小 project-metadata 只有 hub/device/device_name/projects/memberships；项目仅 id/name/kind，memberships 为空。新连接 needs_selection 时没有本机正文；`hub-projects.json`/`hub-links.json` 和实际 Hub CLI list/link 已能识别关联未上传 A。
- `initial-stop-replay.json` 与 `after-hub-restart-replay.json` 中带版本/旧式批次均 HTTP409，前后完整返回的 selective 消息集合相同（4条）。这是拒绝响应及可检索集合证据；不把它描述为另有逐时点全数据库 SQL 快照。
- `stopped-state.json`、`local-restart.json`、`hub-restart-rule.json` 均 none/generation4/revision4、confirmed。`stopped-payloads.json` 的62项请求没有 A 新会话/停传追加轮次、插件正文或变更版/长文的禁止内容。
- combined-stopped/reconnected/local-restarted 的 CLI/MCP 搜索均恰为 local-A、local-A-new、remote-B、vibe-V，并逐条完整读回预期正文，排除二层 C/仅本机关联 D；offline CLI/MCP 恰为 A/A-new，coverage 明确 Hub unavailable。MCP 由冻结源码中的 `StdioServerParameters` 启动已安装 `smm_local.mcp_server`，不是直接调用 Python 方法冒充 MCP。
- `backfill.json` 允许后 confirmed/all、transfer_state complete、allowed_pending=0、inflight=0；`sync-observations.json` 与10次实际 `started:true/running:false` 扫描相符。A 原轮次/停传追加/新会话均到达；`old-reference-read` 仍仅原消息，`retained-version-original.json` 保留旧版原文。逐条上传载荷还有 D/G、更新版与24023字节长文；未给待定 U2 上传。
- `affiliation-propagation.json` 证明 D 禁止时不发新归属/指纹/正文；允许后通过 known-upload-messages 增归属而无正文 upload，A 旧引用保留，前后两条物理正文行完全一致。此附加证据不扩称 assign/map/merge 全矩阵。

scope15 的 `split-scope.json` 先实际接收同会话 Y/X 两条，然后只关联 X。CLI/MCP 新命中和 CLI/MCP/直接 API（含扩大 start0/end999999）的新范围读，标题、全文、项目均只含 `boundaryneedle allowed X full original` / scope-X，未带 `OUTSIDE_Y_ONLY_SECRET_TITLE`。旧式无范围读取仍返回 Y+X，标题为 Y；实际 Hub 停启后旧范围 reference 仍只读 X。`browser:null`，目录无该专项浏览器 PNG/trace，且没有 offline-all.json；所以其 result.scope 中通用“offline-all E1 supplement”文字**不代表本次执行了该部分**，本意见明确排除。

清理不是只信 cleanup：main L85–L88、scope L31–L34 为两个本机服务停止、Hub disable (`running:false`/连接拒绝)、只删除各自 `/Library/LaunchDaemons/<label>.plist`，均exit0。复核时额外只读确认两个 plist 实际均不存在，Hub 49924/49925 端口均拒绝连接，两个任务 local/remote 的 service.json 均不存在。任务数据库和原始证据按设计保留。

## 不能由这五次运行作出的结论

1. 所有执行绑定 **7c72c92 安装包**；当前工作区后续未提交竞态修复准备，未由这些执行验证。不能将时间较晚的源文件状态回填到旧运行。
2. `review-inbox/pr30-current16-review.md` F1/P2 的“第一次 Hub 读取后改变，拒绝但本机已被替换”是另一窗口；本次旧值在请求前已过期，没有在第一次/第二次读取或 CAS 前注入竞争。这五次专项不消除该已确认失败，也不证明 §12.1 新方案已实现或通过。
3. 三次 reconcile 没有重新覆盖全部 E1 CLI/MCP/Web 搜索、四模式、生命周期、兼容与恢复；两次 Mac E3 protocol_only 没有浏览器及 scope offline-all。历史平台记录保留实际版本，不能改标成这次新执行。
4. 本次没有新认领全部 E3/E4 或 A1–A12，故不授予 R005 整体交付通过。无需用泛化的 result.status 抹去这些边界。
