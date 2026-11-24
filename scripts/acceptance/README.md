# 可选实际安装包验收探针

## 007 项目文档库与Hub同步

[007 SPEC](../../changes/007-hub-document-search/spec.md)及[实施计划](../../changes/007-hub-document-search/plan.md)当前含36项（28自动TC、8人工项）和A1–A10/E1/E2。[007当前验收证据](../../changes/007-hub-document-search/evidence/README.md)及其逐项索引关联原始材料与独立意见，并区分当前版本和历史记录。原始记录在任务`AT-SMM-007`私有目录；未执行或缺环境项不能计passed，不能用本说明或006历史结果代替007证据。

- 回归入口：`python -m pytest -q`（包含主契约、列表/片段补充、PR扫描/网页回归；网页回归需acceptance依赖及Chrome，无该依赖时明确skip）。全部使用独立合成档案/只读源见证，不连接真实Hub、VibeInsight或用户资料。设置`ACCEPTANCE_EVIDENCE_DIR=<全新私有目录>`保存逐次实际请求/响应。
- 包入口：`python scripts/acceptance/hub_documents_packages.py --uv <uv实际路径> --output <全新目录>`。分别构建和安装Local/Hub，逐所有模块/HTML核源码→wheel→安装字节，验证真实CLI/MCP；Hub环境不得安装Local。这只证明对应命令和包，不代替E1浏览器/普通身份或E2服务。
- 独立判定探针：`python scripts/acceptance/hub_documents_checks.py --selfcheck`。两个独立原件、文本/范围/版本/摘要/项目/来源/资格逐项负控，以及真实PID/端口存活负控均必须拒绝。自检仅表示工具可用于验收。
- 实际平台按`changes/007-hub-document-search/acceptance/manual-cases.md`逐动作执行：两Local档案、前景Hub、真实CLI/浏览器选择与拖入/stdio、项目完整命中及逐字读取、双端更新/只读归属、生命周期/离线/重启、链接及权限、实际进程/端口清理。平台入口为 `python scripts/acceptance/hub_documents_platform.py --target-config <独立包配置> --output <全新目录>`；Windows须由实际标准账户运行。Hub凭据浏览器观察另用同参数的 `hub_documents_browser_privacy.py`；没有业务原件不能计通过。
- 维护者已要求不再使用家庭ESXi Windows/Linux，且目前没有其他实机资源，先继续本机与CI。CI环境能力探测独立于产品验收；Ubuntu实际user-systemd能力不等于007服务业务已通过，Windows创建LocalService配置也不等于真实LocalService进程/普通Local已通过。
- 原始输出含合成文档及本地路径。公开前保留原始/脱敏副本双SHA，不公开token、TLS私钥、签名材料、数据库、wheel或原始trace。保护冲突按用户指南明确恢复，不删除保护文件或自动重授权以“修复”测试。

`Selective upload installed-package acceptance` 的 `document-installed-e1` 只复跑三系统E1，明确跳过服务，不代替E2；`document-installed` 继续同时执行适用的真实Ubuntu用户服务和Windows SCM。默认005模式不变。新增模式用于独立重取E1某项证据，不能以它的整体success声称服务或跨机器已验证。

## 006 本机文档（可选实际包验证）

本次候选的[实际验收证据](../../changes/006-local-document-search/evidence/README.md)提供 A1–A8/E1 与29项用例索引、三平台原文/画面/安装摘要、双包/回归/CI入口、独立意见及公开字节校验。复跑方法见下文；当前状态以索引关联的原生结果为准。

日常 CI 运行 `pytest`，不依赖浏览器、远程机器或实际用户资料。完整 E1 另用下面探针，每次要求全新输出目录/档案，仅生成合成文档，不接 Hub。

1. 从当前源码构建两个 wheel；`local_documents_packages.py --uv <uv路径> --output <新目录>` 会另行构建并分别安装 Local/Hub，逐模块核对源码→wheel→安装字节，验证 Local 新命令及 Hub 独立归档/项目方法。它不代替三系统 E1。
2. 目标机准备独立 Local wheel 环境，以及另一个控制环境（`mcp`、`playwright`）。控制环境用 `python -m playwright install chromium` 准备浏览器，或配置本机 Chrome/Edge 可执行路径。Linux 需要实际可用的浏览器依赖，不能跳过浏览器后称通过。
3. 私有目标 JSON 提供 `local_python`、`wheel`、`expected_platform`（`darwin`/`linux`/`win32`），可选 `browser`；Windows 另需 `controller_python`。路径均是目标机实际可读取的路径；Windows 新环境用复制安装依赖，确保普通交互账户可读，勿依赖管理员缓存的硬链接权限。配置不含用户凭据。

```text
<控制环境Python> scripts/acceptance/local_documents_platform.py --target-config <目标JSON> --output <全新业务输出>
```

Windows SSH 管理进程不作为普通用户证据，使用当前已登录用户的 Limited 交互任务：

```text
<控制环境Python> scripts/acceptance/local_documents_windows.py --target-config <目标JSON> --output <全新业务输出>
```

包装器核对实际非管理员 Token 和交互会话，保存 worker/控制进程退出并删除本任务。20分钟等待上限不改变原生自动执行300秒上限；较长平台轮按已确认人工外部步骤记录真实执行。macOS/Linux 直接用普通账户，不需要管理员认证或注册系统服务。

探针记录实际安装/wheel全部模块摘要、命令起止/退出/响应、源字节与mtime时间线，真实Web按钮及PNG/trace，真实stdio MCP与子进程退出，链接/junction及适用权限错误、版本/旧ref、删除/移除和同档案重启。产品子进程的只读审计钩子只观察来源打开，不改变产品返回；仅明确刷新可打开正文。`local_documents_checks.py` 用独立原字符串/码点公式/完整集合判定，并用错误正文/坐标/身份/集合自检；不能只凭最终status字段验收。`local_documents_mcp_worker.py` 转发真实stdio并保存服务器退出。

每轮调试后独立核查设计、断言和原始材料，正式轮必须换全新输出重新执行。源码变更按模块SHA判断适用性；完整矩阵、证据要求与未验证项对照[006 PLAN](../../changes/006-local-document-search/plan.md)。输出中有个人路径和账户信息，公开前保留原件SHA并对副本脱敏，不公开数据库、wheel、配置或原始trace。

## VibeInsight 的可选验收探针

日常回归运行 `pytest`，来源由合成事件夹具控制，无需 PostgreSQL 或 staging 凭据。
设置 `ACCEPTANCE_EVIDENCE_DIR` 可导出选定场景的实际响应；不设置时不产生报告：

```sh
PYTHONPATH=src ACCEPTANCE_EVIDENCE_DIR=/tmp/smm-evidence/pytest python -m pytest -q
```

以下探针验证已安装的独立发行包、真实 SQL 和升级兼容，按需运行，不是默认 CI 的前置依赖。
从仓库根目录运行，需要 Python 3.11+、`uv`、`openssl`，以及本机 PostgreSQL 的
`initdb`、`pg_ctl`、`psql`。PostgreSQL 探针在独立临时目录初始化数据库，仅监听该目录的
Unix socket；造数仅发生于此临时数据库。两个探针都只启动本机 Hub，不接受远端数据库参数。

```sh
python3 scripts/build_packages.py
uv venv /tmp/smm-hub-acceptance
uv venv /tmp/smm-local-acceptance
uv pip install --python /tmp/smm-hub-acceptance/bin/python dist/packages/smm_hub-*.whl
uv pip install --python /tmp/smm-local-acceptance/bin/python dist/packages/smm_local-*.whl
python3 scripts/acceptance/vibeinsight_postgres.py \
  --hub-env /tmp/smm-hub-acceptance --local-env /tmp/smm-local-acceptance \
  --output /tmp/smm-evidence/postgres.json
python3 scripts/acceptance/vibeinsight_upgrade.py \
  --hub-env /tmp/smm-hub-acceptance --local-env /tmp/smm-local-acceptance \
  --output /tmp/smm-evidence/upgrade.json
```

旧客户端和旧数据库由仓库中的 `d2dee18fcc050dcf20bd4108429975477399db8d` 源码生成，
需本地 Git 含该提交。导出时将调用方的当前会话标识替换为 `<current-session>`，
pytest 另将夹具临时路径替换为 `<fixture>`。脚本先核对已安装模块与当前源码的 SHA-256，不一致时拒绝执行。
只有所有断言通过才写出 `status: passed` 的 JSON；非零退出时检查终端异常，不能用旧文件
宣称此次通过。报告记录执行时间、HEAD、源文件及 wheel 哈希和实际响应。临时服务、档案和
数据库在退出时清理。脚本中的口令、Token、事件和项目均为隔离夹具，不使用用户凭据。

探针目前面向 macOS/Linux；Windows 文件 ACL 不在这组探针覆盖范围。
本次执行结果及七项验收映射见[验收证据索引](../../changes/003-search-vibeinsight-conversations/evidence/README.md)。

## 新 SPEC 的平台验收

新增 `vibeinsight_fixture.py` 和 `vibeinsight_platform.py` 对应已确认 PLAN 的 H/G/C/P。
这些任务独立于默认 pytest，不连接真实 VibeInsight，不向真实服务器造数。
实际系统服务需要相应管理权限；不能把前台进程、托管 CI 或下面某一个系统的通过当作三平台服务通过。

### 准备隔离来源和候选包

1. 构建两个 wheel，在目标系统两个独立环境安装。没有外网时可准备离线依赖；仍须检查依赖相容性，并核对实际安装模块和 wheel 摘要。
2. 在一台受控测试机用 PostgreSQL 工具创建全新目录和 TCP 实例。默认只允许回环地址；跨机执行时显式指定测试网段。`--host` 是目标 Hub 能访问的该测试机地址，`--pg-bin` 为本机 `initdb` / `pg_ctl` / `psql` 所在目录。

```sh
python3 scripts/acceptance/vibeinsight_fixture.py create --root <新目录> --pg-bin <PostgreSQL工具目录> --host <测试机地址> --allow-cidr <测试网段>
```

输出 `private-fixture.json` 的路径。该文件包含**临时实例的随机秘密**，只通过受保护的本地文件/文件传输交给测试控制器，不提交仓库。构造控制器时先查询随机实例标记，不匹配则拒绝造数。来源账户仅有 SELECT，Hub 查询继续走真实 `psql` 与显式只读事务。夹具管理员负责合成事件的原子写入；角色、实例及读写操作与真实 VibeInsight 无关。

3. 创建目标系统的私有 `target.json`，必要字段如下。解释器必须为候选包的安装环境，证书使用包含实际测试地址的 SAN，`address` 是本任务 HTTPS Hub 地址。

```json
{
  "work": "<任务独有目录>",
  "state_name": "state-run-1",
  "hub_python": "<Hub环境解释器>",
  "local_python": "<Local环境解释器>",
  "psql": "<任务专用客户端绝对路径>",
  "cert": "<测试CA/证书路径>", "key": "<测试私钥路径>",
  "port": 18770, "address": "https://<测试地址>:18770",
  "candidate": {
    "revision": "<实际源码提交>", "dirty": false,
    "installed_hub": {"smm_hub/cli.py": "<wheel内对应文件的sha256，实际清单包含全部Python模块>"},
    "installed_local": {"smm_local/cli.py": "<同上>"}
  }
}
```

从构建出的 wheel 使用 Python `zipfile.ZipFile` 枚举包目录内所有 `.py`，以归档路径为键、`hashlib.sha256(wheel.read(name)).hexdigest()` 为值生成两份模块清单，并保存 wheel 文件本身的摘要。控制器逐个核对安装位置的实际字节，不一致拒绝开始。`state_name` 对同一轮续跑保持不变；新轮应使用新的状态和输出目录。`work` 内的独立 psql 及其所需动态库用于依赖故障注入，不修改共用系统客户端。

### 执行 H / P / G

```text
python scripts/acceptance/vibeinsight_platform.py hub --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
python scripts/acceptance/vibeinsight_platform.py self-managed --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
python scripts/acceptance/vibeinsight_platform.py shared --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
```

`hub` 注册并使用该平台的真实服务，包含默认 300 秒周期的实际观察，因此一次执行会超过五分钟。Linux 要有可用的 systemd 用户管理器和启动运行配置；macOS 需要 sudo 注册系统级 launchd，使用配置普通账户运行；Windows 在提升权限的控制终端执行，LocalService 必须能读取/执行 Python、包文件、psql 及动态库。不能只给目录增加继承规则后就假定所有文件可读：从缓存硬链接安装的文件可能有受保护 ACL，应核对实际文件权限，再以服务结果确认。凭据状态目录的受限 ACL 单独保留。

`self-managed` 使用公开 `serve-hub`，不注册服务，验证配置持久、周期、3→5 轮、无新增重启、冲突数据库及旧无来源入口。P 与 H 使用不同来源夹具/状态；不要在并用同一来源时重置合成事件。

`shared` 使用已经配置的实际服务档案，执行精确回看、长停服、新可见项目、同时间事件、原地改写、关联解除、仓库身份及连接目标切换。它的前置条件包括 C 准备阶段产生的设备甲/乙项目及既有 5 轮会话；按 PLAN 先准备。为构造部分提交后的起点，它在**停止的验收 Hub** 中设置两个已归档项目的不同有效进度，并记录完整前置清单；不会修改真实 Hub。主机/端口/库名三个字段的来源隔离另由默认参数化测试覆盖，共用 SQL 端到端切换库名。

非授权读取由 `vibeinsight_denied_read.py` 验证：POSIX 用另外的普通 UID（控制器需要 sudo），Windows 创建临时普通账户、实际尝试读取并在 finally 删除该账户。它不会输出读到的秘密。`hub` 最后停用本任务服务；失败时也保留日志和非零退出，不覆盖旧成功文件。

### 三平台 C 路径

`client` 在目标系统的 Local 环境运行，先把真实旧版本 `d2dee18` 的 `src/` 导出到独立目录。私有目标配置增加 `phase`、`client_name`、`baseline_src`、`hub_token_file`、`client_data_name`。客户端导入目录必须位于测试工作区，避免意外归入当前源码仓库；控制器使用独立本机档案。

先以 `phase: "prepare"` 执行 `client`：实际旧客户端上传并保存旧引用，新客户端在不新增消息时补传归属。然后由 Hub 所在机通过项目 CLI 建立 PLAN 中的关系。把实际 Hub 项目 ID 写入 `expected_projects`（当前项目在首位），修改为 `phase: "verify"` 后以新的输出目录执行：

```text
<Local环境解释器> scripts/acceptance/vibeinsight_platform.py client --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
```

`verify` 分别调用真实 CLI 与 stdio MCP，核对集合、两类来源/事件位置、独立合成原文、旧引用、显式本机、断线与恢复及改显示名。断线通过客户端本机的透明 TCP 转发关闭/恢复连接产生，Hub 配置与请求逻辑不被替换。`vibeinsight_mcp_process.py` 只转发真实 stdio，并保存实际服务器退出码。

Windows 可用 `vibeinsight_windows_limited.py` 启动相同 `client` 参数：它通过当前已登录用户的交互会话、Limited 任务运行，避免 SSH 服务桌面对普通进程的 DLL 初始化限制；结束后删除任务。该用户须保持登录。工作目录应在该用户可写的位置；产品仍是安装包，进程中断言当前 token 不是管理员。控制器的提升权限不会冒充本机用户入口。

### 证据与清理

每次输出独立的 `result.json`、`commands.jsonl`、版本/实际模块摘要、服务身份或客户端身份、请求/响应、原文、进度和权限记录。结果不能单靠 `status` 判断：对照 PLAN 的 H/G/C/P 逐项核对断言、日志及未到达的检查。中途失败只保留此前已执行部分，不能宣称整个平台通过。`private-fixture.json`、原始 PostgreSQL 语句日志和私钥属于私有测试材料；公开源事务证明只导出已脱敏的读账号语句。

收回日志与退出码后，用本任务状态目录 `hub disable` 停止服务；确认对应服务/PID 已停，再清理本任务配置、服务注册与临时目录。来源实例由创建者执行：

```text
python scripts/acceptance/vibeinsight_fixture.py stop --manifest <private-fixture.json>
```

默认 CI 不运行这些管理员/数据库任务。手动 SQL 工作流运行原可选 SQL/升级探针；系统服务矩阵仍由具备实际权限的测试机执行并导出证据。

修订后的 C 配置还需 `expected_hits`：每项包含独立夹具声明的 `project_id`、`source`、`session`、`texts`（允许的完整合成正文），逐一核对每个关联目标确实命中。`shared` 需 `device_projects: {"mac": <甲的Hub项目ID>, "linux": <乙的Hub项目ID>}`，避免用可修改显示名寻找稳定身份。

H/P 保存完整已提交原文和精确旧引用的重启/故障读回、各项目完整进度、服务重启 PID、失败期间最近成功状态及每类故障恢复后的独立新增内容；P 另记录真实公开启动 argv/PID/退出码。C 的 CLI 与 MCP 分别使用各自搜索返回的引用，名称修改前后必须不同。默认 CI 明确使用 UTF-8 Python/stdio；此结果不宣称验证了旧式 ANSI 控制台兼容性。

`vibeinsight_readonly_audit.py --fixture-log <隔离实例日志> --output <新文件>` 逐 PostgreSQL 后端 PID 核对读账号的 SELECT/COPY 均在 `BEGIN READ ONLY` 内。只导出计数和每类首个合成 SQL 示例，不导出管理员语句、连接元数据或含随机密码的原始服务端日志。H 使用短暂的合成表锁让服务自己的 psql 子进程可观察，控制器与服务分别使用夹具管理账号和 SELECT 账号；不修改查询实现。

### 完整 P/G 合同及旧引用复核

复用平台控制器的完整 P/G 验收入口为：

```text
python scripts/acceptance/vibeinsight_contracts.py standalone --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
python scripts/acceptance/vibeinsight_contracts.py shared --target-config target.json --fixture-manifest private-fixture.json --output <新输出目录>
```

它在共用控制器之上，额外保留**追加之前**的每条精确消息引用并在追加后、旧入口恢复后读取；完整比较旧入口恢复的全部原文；并在新来源目标中替换同目标凭据、核对完整进度、重启并实际归档更早时间轴上的新增消息。原 `platform.py` 的低层模式保留，完整 P/G 结论采用本入口。

每轮 H 结束后，再针对该轮原始材料复算追加前的原消息 ID 与后续真实精确 HTTP 读回，防止只比较新取得的引用：

```text
python scripts/acceptance/vibeinsight_contracts.py references --evidence-dir <H输出目录> --output <新的引用审计JSON>
```

C 准备阶段记录旧进程实际加载的 core/federation SHA，并从 Hub 完整读回本设备的三段会话；补传后再次完整读回，逐条比较消息 ID、位置、角色、正文、时间和总数。项目元数据允许从空变为有效归属，消息不允许增加或重写。

## 005 上传规则与联合检索（可选）

`selective_upload_fixture.py` 仅生成任务目录内的合成 Agent/插件历史及本机 Hub 的 VibeInsight 归档，不连接 PostgreSQL 或实际来源服务器。
`selective_upload_prepare.py` 要求候选提交干净，记录两个实际 wheel 的摘要及全部安装模块预期，生成任务 HTTPS 证书及私有目标配置。
`selective_upload_platform.py` 在两个独立 wheel 环境上核验实际模块，再通过 CLI、独立 stdio MCP、真实浏览器按钮完成范围/原文、断线恢复、停止保留及补传；保存请求审计、截图、trace 和清理退出结果。输出目录必须全新。

```text
uv sync --extra test --extra acceptance
uv run python scripts/build_packages.py
uv venv <local环境>
uv venv <hub环境>
uv pip install --python <LocalPython> <本次LocalWheel>
uv pip install --python <HubPython> <本次HubWheel>
uv run python -m playwright install chromium
uv run python scripts/acceptance/selective_upload_prepare.py --work <新任务目录> --local-python <LocalPython> --hub-python <HubPython> --local-wheel <本次LocalWheel> --hub-wheel <本次HubWheel>
uv run python scripts/acceptance/selective_upload_platform.py self-managed --target-config <任务目录>/target.json --output <新证据目录>
```

浏览器可用 `prepare --browser <实际Chrome或Edge路径>`；否则使用本环境 Playwright Chromium。Linux 缺少系统依赖时先由有权限的环境准备，不能跳过浏览器后称通过。
`hub-service` 模式通过实际 Hub setup/enable/disable 执行 E3，需各平台相应服务管理权限；`login-service` 仅 macOS，使用内部 label/logs 参数注册任务专用 LaunchAgent，保留日常 `ai.smm.local`。`client` 在本系统普通用户运行，Windows 不能以管理员进程冒充普通交互用户。
目标配置中的解释器、TLS 文件与目录必须能被实际 Hub 服务账户访问；Windows LocalService 的叶子文件 ACL 也需核对。配置与 Token 保持私有，脚本只导出脱敏的合成资料。

这些探针只证明实际执行的检查，完整矩阵仍对照[005 PLAN](../../changes/005-selective-conversation-upload/plan.md)填写；R1–R6、新旧真实版本组合和剩余边界不能仅以某次核心流程通过替代。

`selective_upload_recovery.py` 在独立档案上执行 R1/R2/R3 的实际 `prepare-restore`→停服务→恢复清单→重启→查看差异→明确采用 Hub→允许补传。R3 要求 `hub-service`，同时恢复旧 `hub.json`，保留排除的保护文件。R4 在真实 Linux systemd 用户服务中调用已安装候选的 `Hub.upgrade`，以离线安装成功桩避免访问发布仓库，在真实服务启动后确认一条新停止规则，再注入健康失败；验证实际恢复路径保留该限制。它不模拟已发布新包安装成功，包字节始终是本次候选，证据明确记录这一边界。R4 的 Hub 环境放在任务自己的 `tools/smm-hub` 下，使实际升级入口的环境检查仍正常执行。

```text
<控制端Python> scripts/acceptance/selective_upload_recovery.py self-managed --case R1 --target-config <新配置> --output <新证据目录>
<控制端Python> scripts/acceptance/selective_upload_recovery.py self-managed --case R2 --target-config <另一新配置> --output <另一新证据目录>
<控制端Python> scripts/acceptance/selective_upload_recovery.py hub-service --case R3 --target-config <另一新配置> --output <另一新证据目录>
<控制端Python> scripts/acceptance/selective_upload_recovery.py hub-service --case R4 --target-config <另一新配置> --output <另一新证据目录>
```

Windows 真实客户端用 `selective_upload_windows_limited.py --mode client` 在当前已登录用户的 Limited 交互任务中运行，配置增加 `controller_python`；对应 Hub 服务探针用 `--mode hub-service` 的 Highest 交互任务，仍核对服务实际为 LocalService。包装器保存实际 token 判定和退出码，结束后移除本任务。不能把管理员控制端当成本机普通用户的证明。

005 Windows 旧版本组合同样必须以普通交互身份运行，包装器支持 `--probe compatibility --mode client`，调用实际四环境控制器。Windows VM 启动 Python/浏览器较慢，任务允许最多 30 分钟，调度器硬上限 32 分钟；必须保留过程收据，超时不能算完成，并核对任务服务/后台是否已清理。

`selective_upload_recorded.py` 将每次原生验收调试/正式执行绑定到新的实际业务运行，自动创建新任务状态，把原始安装摘要、命令、接口结果、截图与清理结果收进 `ACCEPTANCE_EVIDENCE_DIR`。私有目标可用 execution 指定 SSH 测试机/控制解释器/脚本目录；SSH 保持严格主机校验，Windows 仍经交互任务核对实际身份。它不会把先前通过的 JSON 重新包装成新执行。

记录收回后可用 `selective_upload_audit.py --evidence-dir <原始运行目录> --local-wheel <该轮LocalWheel> --hub-wheel <该轮HubWheel> --output <新审计文件>` 独立核对包摘要、完整合成原文、范围、排序公式、补齐进度和请求形状。此工具只读原始文件，不重新运行产品；不能替代截图审阅或 A1–A12/E1–E5 的完整验收。其自检用例包含正文缺失、错误排序、排序候选外发、假补齐和错误原文等负例。

A5 可运行 `selective_upload_isolation.py --target-config <独立新配置> --output <新目录>`，只验证真实 HTTPS Hub 下同设备关联项目、其他设备与合成 VibeInsight 继续推进，禁止 A 不外发且旧副本保留；它不覆盖三入口或整个验收矩阵。

在上述隔离配置增加 `extra_entrances: true`，还会通过 CLI、真实 stdio MCP 和浏览器实际选择“仅本机按项目/全部项目、联合全部项目”，逐条读取并与合成夹具完整正文比较。Windows 包装器支持 `--probe isolation --mode client`，仍必须使用普通交互身份。

`selective_upload_scope.py <client|self-managed|hub-service> --target-config <新配置> --output <新目录>` 单独补离线全项目三入口及共享会话分项目原文读取。夹具通过真实上传协议在任务Hub写入同会话X/Y两条消息，只关联X，验证允许标题、完整消息、旧无范围读取与重启引用；`protocol_only` 的实际服务任务只执行范围原文部分。Windows包装器选择`--probe scope`并保留对应mode，服务仍需实际LocalService身份。

`selective_upload_global_cli.py --target-config <已结束的任务配置> --output <新目录>` 仅在该任务自己的合成档案/来源上验证CLI唯一全局项目、明确归属与强制源重放。须在对应主流程结束后运行，不用于日常档案；Windows包装器支持`--probe global_cli --mode client`。

`selective_upload_reconcile.py --target-config <新配置> --output <新目录>` 使用真实新包CLI/Web验证旧本机代次、旧Hub版本、缺版本拒绝和新鲜双版本成功。所有状态和断线仅在独立测试Hub/任务转发中构造，保存两端头、请求、界面与trace。Windows包装器选择`--probe reconcile --mode client`；仍需普通交互身份。

### 原生十二场景补齐的包专项

`selective_upload_completion.py` 的三个独立探针补充旧非空档案关联/游标升级、旧参数的真实 stdio MCP 读取，以及 Hub 备份后已确认消息丢失的恢复。使用上面的新包独立 Local/Hub 环境、loopback HTTPS 证书和模块清单；另从正式 `v0.4.0` 源码构建并在两个独立环境安装旧 Local/Hub 包。在私有目标配置增加 `old_local_python`、`old_hub_python`，以及 `old_candidate.installed_local` / `old_candidate.installed_hub`（按旧 wheel 全部模块生成，与新包清单相同的键与 SHA 格式）。不能仅填写相同的版本字符串代替真实旧包。每次执行新建合成档案及 loopback Hub；不注册系统服务、不访问日常档案。

```text
ACCEPTANCE_EVIDENCE_DIR=<全新输出目录> <控制端Python> scripts/acceptance/selective_upload_completion.py --target-config <私有配置> --probe legacy-links
ACCEPTANCE_EVIDENCE_DIR=<另一全新输出目录> <控制端Python> scripts/acceptance/selective_upload_completion.py --target-config <私有配置> --probe legacy-mcp
ACCEPTANCE_EVIDENCE_DIR=<另一全新输出目录> <控制端Python> scripts/acceptance/selective_upload_completion.py --target-config <私有配置> --probe confirmed-loss
```

`selective_upload_empty_recorded.py --target-config <私有配置> --output <全新目录> --mode client` 专门执行成功零命中：目标配置增加 `expected_platform`（`darwin` / `linux` / `win32`），先保存非空正控，再核对 project/all 在 CLI、真实 stdio MCP、浏览器上的六个空响应及两张画面。控制解释器需要验收依赖与浏览器；包解释器仍为已安装的独立环境。Windows 配置另含 `controller_python`，包装器调用 `selective_upload_empty_windows.py`，要求已登录用户的 Limited 交互任务并核对实际非管理员身份；控制终端不作为普通用户证据。子进程读取的唯一配置位于任务根目录既有 ACL 下，只含路径/模块摘要和运行参数，退出删除，不放用户凭据。

空查询包装可沿用 `selective_upload_recorded.py` 的私有 `execution` SSH 目标字段，由控制端回收原始响应/画面/worker 与清理收据。Windows 长轮可能超过原生单条自动命令 300 秒上限，应按独立确认的人工外部执行步骤保存新命令的实际起止与退出，再登记复审；超时的自动收据仍为超时，不能靠回收旧结果改判成功。以上都是可选实际包验证，默认 CI 仍运行不依赖服务/浏览器/远程机器的共用 `pytest`；完整平台与原生记录范围见[本轮证据入口](../../changes/005-selective-conversation-upload/evidence/20261122-native-completion/README.md)。

007 托管平台流程：手动运行 `Selective upload installed-package acceptance`，选择
`document-installed`，依次保留 Linux/macOS/Windows 的独立包 CLI、真实浏览器和
stdio 原件。默认 `selective-upload` 仍执行005流程。`document-platform-preflight`
仅探测环境能力，不代表产品验收。Windows007业务使用新建标准账户，实际进程必须
`is_admin=false`；仅创建SCM配置或普通前景进程不算E2实际服务通过。
`hub_documents_ci.py`只导出允许的合成业务日志、截图和SHA，不上传任务凭据、私钥、
数据库、wheel或完整浏览器trace；失败保留真实退出，输出failure及清理记录。

007 的实际服务模式由同一CI分别运行Ubuntu user-systemd、Windows SCM/LocalService；
Windows标准Local与Hub管理员分开，状态/程序ACL、真实服务SID及唯一实例清理均留证。
这些模式是同机服务身份验收，不能替代E2物理跨OS机器。完整trace回收需将
本机临时X509公钥证书的Base64填入workflow `evidence_certificate`；私钥只留本机，
CI加密原始trace并保留原件/密文SHA，下载后本机解密校验再复审。未传公钥时
artifact明确报告原trace未回收，该轮不能宣称完整正式证据。

在本机仓库以外的私有任务目录准备回收证书（下列路径替换为你的实际私有目录）：

```text
openssl req -new -newkey rsa:3072 -nodes -x509 -keyout <私有目录>/reviewer-key.pem -out <私有目录>/reviewer-certificate.pem -days 30 -subj /CN=SMM007-evidence
python -c "import base64,pathlib; print(base64.b64encode(pathlib.Path('<私有目录>/reviewer-certificate.pem').read_bytes()).decode())"
```

将第二条输出填入 `evidence_certificate`，选择 `document-installed` 运行。
下载artifact后，对每个`private-traces/*.cms`解密；按artifact的`sha256.json`
同时核密文SHA与`original_sha256`，二者一致才用于独立复审：

```text
openssl cms -decrypt -binary -inform DER -in <原件.zip.cms> -inkey <私有目录>/reviewer-key.pem -recip <私有目录>/reviewer-certificate.pem -out <私有目录>/原件.zip
```

`reviewer-key.pem`只留在该私有目录，不提交或传入workflow。公开证书不含私钥。
