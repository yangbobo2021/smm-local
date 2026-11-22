# VibeInsight 的可选验收探针

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
