# Source-suite v2 独立候选复审

结论：**needs_revision**。v1 两项主体缺口已闭合；当前还有 Windows junction 采集边界和路径发现日志两处需修订。范围只到 source-suite 入口能否进入三 OS CI 调试，不能据 9 项 smoke 判完整 C1/R008 通过。

## v1 问题回归

- 原始临时材料遗漏已闭合：v2 tar 收录整个 work。独立逐成员核对得到 81 个普通文件、8 个 symlink 元数据、1 个 FIFO 元数据，共 90 成员；长度/SHA/链接目标/FIFO 类型均与本机来源一致，无多收或漏收。原先 BOM、坏 JSON、collector 日志和失败原件现已纳入。
- 前置失败主体路径已闭合：run 外层 try 覆盖配置/身份/材料等前置失败；实际 missing-config failure.json 在本次原始归档中。workflow 分别保存依赖安装、OCR/材料、browser、prepare、POSIX outer 与 Windows credential child 输出。采集/pack 使用 no-project Python，避免依赖安装失败时重跑产品环境安装。

## 新发现

**P1：Windows junction 会越过不跟随边界。** `source_suite.py:149–155` 先 rglob 整树，再判断 S_ISDIR/S_ISLNK。Windows junction 是单独的 reparse point，lstat 不设置 S_IFLNK；当前 S_ISDIR 会跳过 junction 自身，而 rglob 可以先递归到目标。失败或中断测试留下 junction 时，采集器可能读取外部目标、遗漏链接元信息或陷入循环。应在递归前检查 reparse 属性，逐层剪枝，只保留 junction 目标/tag；新增的链接控制在 Windows 整项 skip，现有产品 junction 测试并没有验证 collector。此为静态推断，未声称 Mac 证明了 Windows 实跑。[CPython 文件类型实现](https://raw.githubusercontent.com/python/cpython/3.14/Python/fileutils.c)、[DirEntry 实现](https://raw.githubusercontent.com/python/cpython/3.14/Modules/posixmodule.c)、[glob 递归实现](https://raw.githubusercontent.com/python/cpython/3.14/Lib/glob.py)支持这一判断。

**P2：Windows Python 路径发现还在日志重定向之外。** workflow 第 50 行的 `python_path=$(uv run …)` 先执行，outer 日志重定向只覆盖下一行 PowerShell。查询失败时 bash 提前退出，该 stderr 不进入加密原件。应把整个 Windows run 块统一纳入日志，或单独记录发现命令输出与失败。

## 其余核对

路径查询改用 sys.stdout.write，没有 print 的末尾 CRLF；当前 bash/PowerShell 引号静态未见明确 argv 拼接问题。Windows 仍新建实际普通账户，以 Credential 启动，内层同时拒绝 admin token 及 Administrators SID，设计上不接受 filtered-admin。新增 -I -X utf8 保持隔离模式中文输出。Windows 实际身份、argv/CRLF、junction 与真实 OCR/browser 全部仍待 CI，不从本机控制外推。

原始 stdout/JUnit 对应：新采证控制 3 passed，JUnit 0.031 秒；编排 smoke 9 passed，JUnit 0.151 秒，均零错误/失败/skip。283 个 source bindings 当前零差异，target 与保存的 bindings 一致，实际 result 的 source_unchanged=true。context 明确 local-smoke2-not-ci。没有将这批控制认作官方 artifact 恢复、完整 C1 或安装态 E/H/X 通过。

原 v1 报告保留。未修改候选。所读文件 SHA、完整静态出处和逐成员核验结果见同名 JSON 与 source-suite-candidate-review-v2-checks.json。
