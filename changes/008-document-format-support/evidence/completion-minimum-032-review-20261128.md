> 脱敏公开副本：任务工作区绝对路径替换为 `<TASK_WORKTREE>`；Windows完整机器/用户SID隐去。原始独立意见私有持久保存，正文判断不改。

# AT-SMM-008：032 最低 Python 安装独立执行审查

结论：**passed，仅三平台最低 Python 3.11 安装及最小 CLI 业务**。候选 0320622918bcca3779d7d9ba3b4b7f32a584d91d，实际 run 46107496120。本结论不关闭完整 E1、H、X 或整项008交付。

## 原始约定与原件复核

已实际打开 AGENTS.md、008 intent/spec/plan，按 SPEC D2/C1 把最低3.11依赖安装、DOCX/XLSX/原生PDF最小提取与一页真实OCR单列。按证据原件要求逐文件审查，没有采用既有独立review结论。只写本意见两文件，未改产品、测试及原始记录。

已打开各端官方ZIP、metadata-1.json、context.json、recovery.json、已解密recovered/evidence-manifest.json和恢复回执。独立核官方ZIP长度/SHA、run/head/context、公开信封头绑定的manifest摘要；全部1,720成员重算SHA/长度并实际打开：Linux573、Windows574、macOS573。每端含20 DOCX、20 XLSX、40 PDF/60页、2 wheel；这些计数包含下载/复制件，不当作独立业务样本。ZIP全部成员CRC/XML结构以及PDFium每页文本和渲染均可读。JSON意见保留逐成员独立复核SHA。

本次使用已认证解密的recovered，未重新解密，未读取、打印、复制控制端私钥。

## 各平台最低安装结果

| 平台 | 状态 | 实际产品Python / 身份 | JUnit正文 | 清单成员 |
|---|---|---|---|---|
| Linux | passed | 3.11.18 / UID 1001 | 7 passed、0failure/error/skip；25.538秒 | 573 |
| Windows | passed | 3.11.9 / 真实标准SID S-1-5-21-<redacted-machine-and-user>；无管理员组 | 7 passed、0failure/error/skip；50.108秒 | 574 |
| macOS | passed | 3.11.9 / UID 501 | 7 passed、0failure/error/skip；38.099秒 | 573 |

Windows两个实际产品解释器均执行whoami /user和/groups，SID为本机真实账户且没有S-1-5-32-544组，非filtered管理员替代。控制器记录临时标准用户、is_admin=false，结束后所属进程为空、账户不存在、seclogon恢复Stopped。Linux为Ubuntu24.04普通UID1001，macOS15.8.2 arm64普通UID501。这里不追加认领完整E1的token/session或H服务身份。

## 源码、wheel与安装全资产

逐端以git show 032精确源码独立核Local47、Hub50个.py/.html全成员集合，包括静态页面、Hub归档模块及重写shim。wheel物理SHA与原打包回执一致；实际安装解释器测量的Local48/Hub51资产（各含METADATA）逐文件等于对应wheel。Windows源对应仅规范Git LF/checkout CRLF；wheel到安装始终比较物理原字节SHA。两包各在独立site-packages，业务用-I、非源码cwd；Hub实际不能import Local。错SHA与源码导入负控实际非零退出。

7个准备命令及18个打包/独立安装命令均逐项核退出码和原stdout/stderr摘要。uv export --frozen后对documents依赖--require-hashes同步，再--no-deps安装各准确wheel。产品真实Python均3.11；Tesseract5.5.4、eng/chi_sim固定SHA、处理状态/profile和真实OCR输出可读，不靠requires-python元数据判断。

## 全部资料、完整文本、全表与逐格位置

每平台16独立资料，Local/Hub各普通、全局两项目，每项目DOCX/XLSX/原生PDF/OCR PDF各一份；每端8个不同文档ID，另有无关普通项目和错误项目搜索负控。每平台独立源真值208文字单元、32表、152格；前后32次全文、64次全表、304格次、32次original-info、32次原件下载，共246条原始CLI请求。

全文核所有源单元、唯一性、允许顺序和排除项；OCR仅归一空白后全文一致。全表核完整集合/唯一性、行列、每格文字及合并跨度。每格位置独立复核：DOCX精确部件/表/row/cell路径，XLSX sheet/index/A1，PDF按源生成几何重算归一bbox、页尺寸、旋转与页码；有start/end者切回全文必须恰为该格文字。origin/document/source/原SHA与V/P=1逐份一致。

另直接读原件XML核Word/Excel全部真值文字，独立PDFium核原生PDF所有页真值；扫描原件无文字层、实际可渲染，人工查看三平台localalpha原页两行文字、73428与12345.67。原件下载前后字节均与输入相同；源mtime/SHA保护由032驱动的真实通过断言支持。没有只拿两端输出互相比相等。

## 移出源后旧引用与清理

032驱动明确unlink全部外部源后逐份重新搜索/read，审查独立确认前后argv含原reference完全相同、全文/全表/original-info完整响应相同、下载字节均等原输入。每请求新建隔离CLI进程，仅证明该最小持久读回路径。

各平台16个任务cleanup均stopped=true，supervision均completed，300秒/1GiB/256MiB限额和worker/token可读。Windows另核临时账户进程扫描、账户删除后查询及seclogon恢复。**POSIX没有独立最终进程树/端口扫描**，不能把每任务回执当作最终全局树/端口、原生服务清理或完整E/H。

## 所有跳过、失败及覆盖限制

三端本run JUnit均无真实失败、无skip；有一条Starlette TestClient/httpx弃用告警。原件中fixture failure.json和含ff00的准备stderr由两项custody负控刻意保留，已核精确032源码，非真实准备/业务失败；错安装SHA/源码导入非零也是预期控制。旧run错误和失败不在本意见中改判。

本次最低范围无阻塞缺口。仍不覆盖完整E1所有入口/选择拖入/生命周期/关联同步/深表/真实全入口重启及最终树端口，不覆盖H1–H5受管服务或X六方向无组件接收。四份OCR业务仅单页清晰英文文字，不能冒称完整中英多页扫描网格质量矩阵。环境未整体打入artifact，此处依据实际安装逐文件测量及其wheel，不声称本机重建了CI环境。当前web_uploads后续测试修订不属032，不能重标本run。

## 原件绝对路径与摘要

### Linux

- 官方ZIP：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Linux/artifact-15247688699-attempt-1.zip
- metadata/context/recovery：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Linux 下对应JSON；恢复原件：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Linux/recovered
- artifact ID：15247688699；ZIP SHA256：4b8147cf9e0f6c208ac67d53fe0db3cb27f4da969076d530a38788950c7f8901
- manifest SHA256：d49b061d9b53dc147ad3a56bf3acd18e80ff243bde8e6ad0827377dfbf996db1

### Windows

- 官方ZIP：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Windows/artifact-15248340979-attempt-1.zip
- metadata/context/recovery：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Windows 下对应JSON；恢复原件：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/Windows/recovered
- artifact ID：15248340979；ZIP SHA256：5bb15076bbaee9295ad16ce44a242632a5515a7534016aa6893f30597937e31a
- manifest SHA256：750bd391d202ddb461ac30f3ef27324c5283d20ae63bf80d79eee4f9b82aa06a

### macOS

- 官方ZIP：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/macOS/artifact-15247874915-attempt-1.zip
- metadata/context/recovery：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/macOS 下对应JSON；恢复原件：<TASK_WORKTREE>/.acceptance-local/008/completion-20261128/minimum-ci-46107496120/macOS/recovered
- artifact ID：15247874915；ZIP SHA256：669d81b21d2d2c8c502ec2bb4b7cffe89e7b054beec2107cf2a90698a85431c2
- manifest SHA256：0cc1046170eb280920c569b90f67dbca52dd88848d7d8f73e9785e0a4e957a0b

逐成员SHA、两包SHA、身份、计数、具体原件路径及范围限制见同名JSON。
