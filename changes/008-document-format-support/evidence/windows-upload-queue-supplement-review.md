公开脱敏副本：仅替换测试机/账户名称；原意见SHA256 `8702ea2424eb8de615ea7e48a1e670352781325a8dcd5f1cb21a1341cb217489`。

# Windows 上传队列补充证据独立复审

本份补充证据可信：同一队列补丁在实际 Windows 11 SSH 管理员环境中完成四个队列参数分支和一个纯远端原件路由用例，五项均实际通过、无跳过。本轮只读核验已有文件，没有执行测试、原生验收或远程操作，没有修改产品、测试或原意见。`verification.json` 仅作索引，以下结论均反查原始材料。

这份报告不改变已登记的 `review-upload-queue-green-v1`：该意见仍为 `needs_revision / design`。不同 SQLite 档案位于同一父目录时共用队列锁、忙即返回可能遗漏另一档案待办的静态缺口，本次没有覆盖或消除。维护者决定保留该缺口、不加用例或继续修补；本报告据此停止于补充证据复审，不把保留决定写成 SPEC 豁免或通过。

## 源码、传输与证据完整性

实际读取 `controller.py`、`run_remote.py`、`source-manifest.json`、`remote.json`、所有阶段的 stdout/stderr、`transport.json`、`transfer.json`，以及回传 `opened/result.json`、`sha256.json`、JUnit、完整终端输出、附件和诊断日志。

- `source.tar` 内恰有清单所列的 274 个文件，逐个成员 SHA 与本地当前源码及回传 `result.source_manifest` 完全一致。相对清单所指 HEAD `12e5128952ae2929b6c920158022f7d973213f76`，唯一已有文件变更是 `src/smm_local/managed_document_uploads.py`；唯一新增文件是冻结的 `tests/test_document_formats_upload_queue.py`。不存在把其他工作区测试草稿混入这次执行的情况。
- 队列产品模块 SHA256 是 `2cf2ea859f3c8b1d3bba9eb924434d73f28bcffd6be14faf6c00dfe014a05303`。`remote.json` 所列源码 tar、清单及控制器摘要均与实际文件一致。tar SHA256 为 `2180303e19587a55a8082bdd4f1c5dab257e22f8cbdf34dc8d5b797da5261c73`。
- `evidence.zip` 实际 3,483,660 字节，SHA256 为 `9ef7d483a16580c741dbf2754c138343ceef6ff523c64f80ac73dc4b99573b6b`；ZIP CRC 全部正确，无重复成员。`opened/sha256.json` 的 1,507 项逐一核长度和 SHA，并逐字比较解包文件与 ZIP 成员，全部一致；另有清单自身 `sha256.json`，故 ZIP 合计 1,508 个文件成员。清单自身也与 ZIP 内字节一致。
- `run.stdout` 打印的远端传输收据与回收的 `transfer.json` 完全一致，长度/SHA 与实际 ZIP 一致。`transport.json` 六阶段 preflight/mkdir/upload/prepare/run/recover 均 exit 0，所列 stdout/stderr 摘要逐份吻合。该链路是本任务控制器通过 SSH/SCP 产生和回收的收据，不是 GitHub 官方 artifact 或第三方签名凭据。
- 远端控制器在启动 pytest 前校验全部源码 SHA，以显式 `PYTHONPATH=<此次隔离checkout>/src` 运行该源码。使用的 Python/venv 位于该 VM 既有任务目录，因此本次是源码组件执行，不能称为本轮 wheel 安装后的业务验证。

## 实际执行及身份

`preflight.stdout`/`preflight.json` 显示 `<test-host>`、`<test-host>\\<test-admin>`、`admin=true`，实际 MAC 匹配控制器的任务 VM 检查。`result.json` 报告 `win32`、Python 3.14.10 AMD64，完整命令只选择下表五项；没有选择保留的 active-source、upload-restart-C1 或 shared-argv 专门用例。

| 实际 JUnit 用例 | 结果 | JUnit 用例秒数 |
|---|---|---:|
| queue `[processing-local]` | 通过 | 4.198 |
| queue `[processing-hub]` | 通过 | 4.934 |
| queue `[empty_handoff-local]` | 通过 | 4.344 |
| queue `[empty_handoff-hub]` | 通过 | 5.810 |
| `test_pure_hub_original_downloads_via_local_cli_http_and_stdio` | 通过 | 343.255 |

原始 pytest stdout 为 `5 passed, 1 warning in 389.54s`；stderr 为空。JUnit 明确 tests=5、failures=0、errors=0、skipped=0，五个 testcase 都没有 skip/failure/error 子节点，suite time=367.870 秒。终端计时与 JUnit 计时边界不同，两者各自保留，不把 389.54 秒改写成 JUnit 时长，也不拿差额推断某个业务请求耗时。控制器始末实际约 392.557 秒，`exit_code=0`、`timed_out=false`，未触发 420 秒 watchdog。唯一 pytest warning 为 Starlette TestClient 弃用提示。

控制器记录 475 个按 PID/创建时间/argv/exe 区分的观察身份、111 份诊断日志；日志清单长度/SHA全部核实。`cleaned_owned_processes=[]`、`cleanup_errors=[]`，说明最终控制器清理循环没有记录需终止的残留，而不是声称未启动过工作进程。八个队列处理任务均有 completed supervision，含真实 worker 身份；远端路由用到的六次服务启动/停止记录分别为发送端一次、Hub/查询端各两次、错误 Hub 一次，六次停止均 `forced=false`、exit 0，测试停止函数还实际检查原端口不能再返回身份接口。六份服务 stderr 均显示完整启动及正常关闭。

## 队列四分支的实际业务证据

本次冻结队列测试与已审 Mac 测试字节相同。仍以实际 `Snapshots.process` 前门和真实队列锁释放前门控制 processing/empty_handoff 两种窗口；第二份真实 commit 的持久 pending、原 SHA/CID 触发事件后才启动独立 Timer。没有恢复前两版“第二请求先结束”或“第二 kick 必须进入 OS 锁”的错误要求。

逐份只读核对八份原件、冻结真值、全部 native-management 响应和八份实际下载：四份普通 DOCX 各 16 个源文字锚点及三张表，四份全局 XLSX 各 12 个源单元格及两张表，共 20 张表的定位、尺寸、所有格值/跨度与源真值一致，实际原件逐字等于输入。Office ZIP 的 CRC/XML 可读，真值来自无产品导入的生成器；不是两个产品输出互相相等就判正确。

四份 queue-handoff 均 `first_error=second_error=None`；processing 原 SHA 与首份输入一致，empty_handoff 的 `pending_before_second_commit=0`。四份 queue-complete 各有两行自身文档，均 done/error=null。测试 125–143 行要求两份均已发布且无 publication_pending，逐回执核独立 ID、V/P=1、原 SHA、CID/AID、正文/全表/实际下载和完整队列行；末尾 146–151 行真正协调器数据库 RuntimeError 负控也因四参数无 skip 全过而实际到达。只做首份、只修一个端或一种窗口、两份串到同一目标、两输出同错不能通过这些断言。

该四项本身仍是 Windows 上的 ASGI TestClient 队列组件验证，不冒称四条各自都是 TCP 服务请求。下面独立的远端路由项包含真实 TCP 创建端上传/查询流程，可为先前在该准备流程发生的服务队列异常补充实际证据。

## 远端原件确实在准备完成后被读取

实际读了 `test_document_formats_remote_original.py`、`document_formats_remote_fixture.py`、真实 `Server`、remote/CLI 观察器及其冻结源码。该用例不是准备资料后即返回成功：它准备 24 份资料，随后停止发送端、删除全部受保护管理原件路径，重启查询端和 Hub 并安装只读守卫，再经 CLI、HTTP、stdio 获取引用和原件。

24 份资料的构成为 Hub 自有/发送端投影 × 普通/全局项目 × DOCX/XLSX/原生 PDF × 各两份，24 个完整 origin 均不同，查询端自身资料列表为空。真实服务地址是任务专用随机端口的 `127.0.0.1`，原始启动记录核到实际服务 PID、创建时间、完整 argv、执行路径、档案和 nonce；查询使用认证 Hub，未把 mock HTTP 当实际远端。

本人从所有原始记录反查每份输入的 begin SHA/长度、实际 upload_id/commit 和创建端文档 ID，再对照查询结果与下载记录，结果如下：

- 72 份 `remote-verified-download` 恰为每目标三次：`cli-search`、`http-search`、`stdio-reference`。每次都先取得实际查询返回引用，CLI 导出后 `output.read_bytes()==item.raw`（测试42行），再执行实际 Local HTTP 原件接口并核 `raw==item.raw`（47行），之后才写 verified-download。最终保留24份按内容摘要去重的原件下载，逐字等于各自冻结输入；72是下载循环次数，24是保留的不同原件数，不能混报成72份不同原件。
- 实际有192次 CLI记录：168次成功（24次 search、72次 original-info、72次导出）和24次错误 Hub 拒绝。逐份反查144个成功原件信息/导出元数据、72个 HTTP original-info，origin 三字段、目标 ID、格式、V/P=1、原 SHA/长度都正确，profile 与相应查询结果一致且为本次默认 config_revision=0/正确格式。三格式各只有一份适用 profile 变体：Office 为 defusedxml0.7.1/psutil7.2.2；PDF包含冻结的 Pillow13.0.0、pdfminer.six20260107、pdfplumber0.11.11、psutil7.2.2、pypdfium2 5.15.2 和 guarded-native-local-ocr-v1；rendering 为 smm-document-text-v1。profile 的这些核对是本次对原始输出的补充审阅，原测试 `assert_remote_info` 本身主要断言身份、版本、格式、SHA和长度，没有把 profile 全字段独立断言写在该辅助函数内。
- 实际 HTTP 原件响应包含24次准备阶段直读和72次查询后直读，共96次；每个响应的长度/SHA与输入一致，查询后保留原件字节也已逐字核对。另有48份真实 MCP响应，即每目标 search_documents/read_document(original-info)各一次，均无 isError，MCP引用继续进入上述实际 CLI/API 下载；MCP本身仍只返回元数据，不宣称在 stdio 内输出文件字节。
- 24个错误 Hub HTTP请求均4xx并指出 Hub身份问题；另24个 CLI拒绝 exit非0，源测试还断言没有创建导出文件。不能只凭同名或同号路由到其他有效 Hub。

上述支持“纯远端原件经 Local 查询引用正确读回”；该选中用例没有在查询阶段逐份读取完整 text/table，因此不据这次补充重新认领全部远端正文/表格质量或全SC9。队列四项自己的正文和全表检查另有本次真实证据。

## 观察器自检、无额外事件及服务日志

两服务的实际 `/__test_processing_probe` 均200并分别阻止 processing/subprocess；实际 remote-query probe 均200并阻止 source/resolve/connect，真实标准库 socketpair、允许文件正控均成功，Local额外的当前配置 Hub连接正控成功。CLI正控连接当前Hub exit0；读取受保护源、导入解析库、启动子进程、连接其他地址四个负控均以对应 `CLI read observer forbidden` 原因失败，四条原始stderr和四个事件种类一致，不是观察器未启动导致“没有事件”。

测试每次下载后调用 `query_unchanged`，在错误 Hub拒绝之后第116行还再次调用；该函数核 CLI日志、只读processing日志、service-network日志和两服务source-audit均等于自检基线，并确认全部受保护路径仍不存在。五项实际全过证明这些末尾断言已执行。本次又独立比较回传最终 Hub/reader 的 audit-2.jsonl与各自基线，均逐字相等、各只保留自检产生的一次 source open。CLI/network/processing日志保留了基线及通过的原始执行证据，没有另外完整回收三份最终日志快照；故它们的“无新增事件”依据是实际已到达的等值断言，不冒称已有独立最终原始文件逐字副本。

读取所有诊断 stdout/stderr，未发现 `上传控制正在处理其他操作`、`RuntimeError`、`RemoteProtocolError` 或未处理异常 traceback；服务启动前后六份 stderr均正常启动关闭。观察器负控的预期 Traceback 位于专门的 controls stderr，不是产品失败。因而先前远端资料准备上传时的队列 RuntimeError/HTTP断连，在这个相同源码补丁的所选 Windows实际流程里没有重现，且后续查询下载全部完成。该证据不证明所有调度时序都正确，更不证明同父目录多档案条件已通过。

## 构建补充与结论边界

另只读复核 `.acceptance-local/008/upload-queue-20261126/build`：双wheel ZIP CRC正确，实际文件长度/SHA与构建清单一致；Local46个、Hub47个列明源码成员逐字匹配当前源码，Hub `_archive` 的共享队列模块亦含相同 `2cf2ea8…`补丁。

| wheel | SHA256 |
|---|---|
| smm_local-0.4.0-py3-none-any.whl | afde4615d9d78543f48256c1b1016473a759990ba2040eedc9138bf05872e6ae |
| smm_hub-0.4.0-py3-none-any.whl | 0a213c453f43a8a5e52bda0a40609f8258a65a5ab8edfd6841481a32a052fc8c |

构建日志显示两个wheel成功生成。这只认构建及源码/CRC核验；没有本轮安装到独立环境后的业务证据。

本补充支持当前补丁在该 Windows管理员组件环境中的四种单档案队列路径、真实TCP远端准备和24目标原件路由通过，以及现有证据回收完整。它不等于标准非管理员token/session、SCM或其他系统服务、TLS、真实浏览器、最低Python3.11安装、E/H/X或R008完成；不是原生验收中旧TC的新正式执行，亦不修订维护者保留的 active-source/C1/shared-argv状态。跨档案静态缺口仍在原意见中保留，原 `needs_revision` 结论不变。
