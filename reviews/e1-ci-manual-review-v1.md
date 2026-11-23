# E1 CI 人工执行独立复审 v1

验收：`AT-SMM-007`。仅复审精确交接 `work/e1-ci-final-v1-handoff.json` 的 Windows、Ubuntu 两份正式 manual 记录，不复审 E2。独立读取 AGENTS、007 SPEC E1、PLAN E1 1–6、`acceptance/manual-cases.md`、`design-sc9-final-v2/result.json`、验收技能及 reviewer 规则；没有继承其他 Reviewer 的通过结论，没有连接 ESXi、执行产品、重跑 CI 或修改测试。

## 正式结论

| 目标 | 唯一分配检查 | 结论 | covers |
|---|---|---|---|
| TC-007-e1-windows / manual-e1-windows-final-v1 | e1-windows-3 | insufficient_evidence | [] |
| TC-007-e1-linux / manual-e1-linux-final-v1 | e1-linux-2 | insufficient_evidence | [] |

两项均有大量有效实测，但仍不能认领不可拆分的完整长检查。未确认产品缺陷。意见已分别写入交接指定的 `review-inbox/review-manual-e1-windows-final-v1.json` 和 `review-inbox/review-manual-e1-linux-final-v1.json`，每完成一份即通知主 Agent 登记。

## 必需缺证及原始依据

1. **真实 stdio 对私有与 Hub 自有文档的原文读取未执行。** PLAN E1 第2步（plan.md:102）明确要求 CLI/本机Web/Hub Web/真实stdio 分别检索本机私有、另一逻辑设备和 Hub 自有资料，按独立文件集合、版本/出处/文本和字符行号核对；SPEC E1（spec.md:154）明确包含真实 stdio MCP 联合检索及准确原文。冻结 `work/runner-snapshots/e1-222e0e5/hub_documents_platform.py` 的 `stdio_checks` 先查询 A/B 项目，随后仅对 `a_entries + b_entries` 调用 `read_document`。两平台原始 `platform/mcp-3.json` 都只有4次 read，正文分别为 B one、B two、A one、A two。`mcp-5.json` 对 all 范围的 private、Hub D/E 仅调用 search；`mcp-7/9` 是对话搜索/读取。没有 private、Hub 自有的 `read_document` 响应及与独立原字节比较正文、码点端点和行号的证据。搜索结果的完整短片段、Local Web 的逐份原文，能保留为各自有效证据，不能证明未调用的 stdio 读取入口。
2. **实际产品停启后的 Web/stdio 原文读取未执行。** PLAN E1 第5步（plan.md:105）明确写“CLI/MCP/Hub/Web新进程读取同档案，不重新配置、不刷新仍得到相同当前有效内容/ref”。冻结 runner 的 `execute()` 顺序是 `stdio_checks` → 两个 `web` → `lifecycle`；实际5个 stdio 会话与两浏览器 trace 都先于生命周期停启。`lifecycle` 中真实重启 Hub、A/B 后，原有效 native ref 的 CLI read、Local CLI 查询确有原件，但没有此后 Web/stdio 的读取。Windows 最后浏览器网络分别为 15:29:48.221Z（Local）/15:29:34.170Z（Hub），Ubuntu 为15:31:35.346Z/15:31:26.286Z，均早于其随后生命周期停启读取段。

以上只要求已写明的入口及重启动作，不新增“每入口 × 每状态”的组合门禁；也没有要求把所有版本、暂停、撤回状态在每个界面各复制一轮。两项缺证都不能从“runner/status=passed”补出。

## 收据、版本与原件完整性

| 核对对象 | Windows | Ubuntu |
|---|---|---|
| 目标 result.json SHA-256 | f5cf45cbaf946c8776c3fd8300c533771cb579f01714eebf521a00e97ba4a3aa | f0ce08c86e840400d8d155d3cb017f3f90023012273221f90647974e6c85ef67 |
| 目标附件 / 当前产品绑定 | 114 / 45，全匹配 | 113 / 45，全匹配 |
| 外层 artifact.zip SHA-256 | ca7f82aebdf56fbf2e9400e493258df06797514b3522d7595f4f8848585d3c4e | 9595541b7ac6c7a34c12eaf8ba9e6716508591b3a5e9329e57f76ba65c1259a4 |
| 外ZIP项数 / CRC | 106 / 全通过 | 105 / 全通过 |
| 内层 manifest 文件 SHA/长度 | 105项全匹配 | 104项全匹配 |
| 两copy manifest声明的源/副本逐字节比较 | 105项全匹配 | 104项全匹配 |
| 安装模块 | Local30 / Hub31，全匹配 | Local30 / Hub31，全匹配 |

外层 digest 与现存 download-receipt 中 GitHub digest 相等。仅核已有 GitHub 回收收据，未发起新的 GitHub 查询。原件根分别是 `/private/tmp/smm-007-ci-e1-windows-v3/007-public-evidence`、`/private/tmp/smm-007-ci-e1-ubuntu-v3/007-public-evidence`，解密原件为相应 `-decrypted-v3/platform/`。逐文件重算，而非只读取既有 matches 摘要。

当前产品字节对应交接的 src245c236；实际执行为 run45205483868/head222e0e5，工具源码以 `work/runner-snapshots/e1-222e0e5` 冻结。安装的 Hub `_archive/__init__.py` 依 `scripts/build_packages.py` 对 `src/smm_hub/_archive.py` 替换导入生成（SHA 62e7eee1bc2db691bf61e22ff770dda8f6fef2f0356369a1b3881f3c07312976），其余内置归档模块逐项映射 Local 原源码；没有将生成布局差异误判成产品换版。独立包运行使用安装解释器与 `-I`，runner移除 PYTHONPATH。

两平台 CMS ciphertext 的 SHA 与原 manifest/解密收据一致，解密 ZIP 的长度、原 SHA、全部 CRC 及每项资源均实际打开读取。Windows Local/Hub 原 trace SHA 为 dd708016dc0f74bc033de2b8064793e1e99cc435b5779632cfffca2ad3f3d6ff / f341295d8f1a43260c564697b88d80157efc1b2bf53d10bf815c9d7e75455b8e；Ubuntu 为 c6460ae4981945c9562dbd73d97af4f6230be6356af2a3651d47f73c15fa8b4e / d91cf3addde8c47a7291f2b167494d400f7d9272045530bbe1214cc6080953a6。未输出 token 或私钥。

## 已核实的局部业务证据

| 步骤/边界 | 两平台本次实际证据及结论 |
|---|---|
| 普通身份、前景HTTPS、两个Local | Windows controller is_admin=false，173条产品进程身份均false/session2；Ubuntu controller及175条产品进程均UID1001。原serve argv带独立state-dir/TLS，A/B archive/device不同。Windows Limited账户控制收据有任务账户及无剩余PID；不是SSH管理员或SCM。 |
| CLI配置与明确采集 | 原始commands有项目创建、默认off、KEY/HID/generation选取、pending→明确refresh、允许/sync、私有/全局/未绑定及Hub自有目录。独立fixtures提供正文，集合断言按origin+version、原SHA/归一化SHA/文本长度及码点/行号逐项比较。 |
| Web创建端管理 | 两端各新建项目，实际文件选择+DataTransfer拖放，不同receipt ID，正确项目集合及两次read响应ID独立对应；实际PUT更新版本、旧ref拒绝、DELETE后只剩第二份。Local默认off与允许后仅剩余材料远端资格相符。Hub先选凭据文件，重载后无凭据业务请求。 |
| 联合范围与原文 | CLI/Local Web私有、另一设备、Hub D/E及全局/未绑定资料的集合/原文断言有效，Local Web实际12次read。C↔D两根与D↔E第二层负控，CLI/Local Web范围集合以及stdio对话read原件有效。stdio私有/Hub原文缺口如上。 |
| 越端只读和真实拒绝 | 每平台8次：Hub对设备投影添加/更新/删除/改来源；Local对Hub native同4操作，均400及具体原因。Windows commands索引136/145/154/163/172/181/190/199，Ubuntu132/141/150/159/168/177/186/195；各请求后逐次比较两端sources/files/library全集、Local14/Hub21张文档表SHA，以及每端4份managed文件SHA/长度/mtime，均等于动作前。不是仅最终状态或HTTP状态判断。四种持久/API改变负控被拒。 |
| 生命周期 | 暂停前两有效文件，编辑两文件/新增第三后Hub仍旧快照；Windows真实删除、Unix实际chmod0失败后撤回旧资格；重叠来源连续原ref可读、最后来源退出拒绝；离线remove+sync为pending/error，B重启任务仍pending，恢复同epoch后退出；native外部源移走、Hub真重启后旧native ref的CLI逐字读取有效，随后移除退出。没有重启后Web/stdio证据。 |
| 原生路径与无隐式扫描 | 两平台中文空格路径、BOM/CRLF/Unicode原文；Windows原cmd mklink /J退出0、随后CLI明确junction拒绝，invalid UTF8实际失败；Ubuntu实际符号链接拒绝及chmod0读取失效。各10份原源SHA/mtime在非编辑段相同；源open Windows24、Ubuntu25，仅explicit-refresh/conversation-import。 |
| 进程清理 | 所有8次产品服务停启均有stopped-processes/cleanup；Windows包含真实launcher及child PID树，Ubuntu实际解释器PID；独立process_alive/监听关闭断言，5份stdio process均exit0/alive=false，Windows控制器unexpected_remaining_pids=[]。 |

## 实际图像与浏览器轨迹

两平台均亲自打开原始 `web-a-literal-original.png`、`web-hub-literal-original.png`、`web-hub-device-readonly.png`、`web-local-joint-read.png`、`web-local-project-one-hop.png`。看见对应项目身份与两份不同命中、chosen的中文/Unicode正文、dropped原样script/img及原文、设备投影无写入口、联合结果及C根只含D两个文件。Unix Local原图有一时重复的library行呈现，而底层receipt和检索/read身份均为两份；该呈现不作为本轮两个缺证点的替代或产品失败判据。

完整trace直接读取：Windows Local1156/Hub608事件、73/47网络项；Ubuntu Local1166/Hub603事件、73/47网络项。逐读response资源核两初始文档id、正文、start/end及行号；Local还有10个联合文档read。网络含实际选择/拖放POST、编码错误400、更新PUT及删除DELETE。无trace action error。纯文本记录每端独立保留new-project、query-snippets、original-chosen.txt、original-dropped.md四阶段，window两个标记均unset、main嵌入节点0、全部网络无/smm-document-executed；核重复/误指第二目标的两个负控及四种副作用负控。截图不能单独证明无执行，本结论结合实际evaluate、全网络和源码断言。

## 范围保持

本意见不把E1逻辑设备称为物理跨机器，不替代systemd/SCM。用户已明确选择保留的E2网页资料停启后读取、Windows服务/规则删除后不存在查询及真实跨OS机器缺口保持未完成；没有补跑、没有把局部有效证据升级为整体需求通过。
