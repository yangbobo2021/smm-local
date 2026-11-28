# Source-suite 候选独立审查

结论：**需修订（needs_revision）**。先补齐下列两项采证边界，再进入三系统 CI 调试。本轮没有执行大 CI，也没有修改实现；6 项本机 smoke 不等于完整 C1 或 R008 通过。

## 本轮范围

只审 `document_formats_source_suite.py`、Windows 普通账户启动脚本、source workflow 与 source-ci-request.json，以及所给本机 smoke 原件。验收 ID 为 AT-SMM-008。完整 R008、安装态 E/H/X、三 OS 真运行结论及合并均在本报告范围外。

## 需修订项

1. **P1：归档漏掉未显式转存的每用例原始材料。** `source_suite.py:99–103` 只设置附件目录；`:116` 将 pytest 临时目录放在 `work/pytest-tmp`；`:125–139` 却只归档 `work/platform`。实际六项 smoke 的四个 case 目录为空，BOM/坏 JSON 与 minimum collector 的原始日志还在 pytest-tmp，未进入 16 成员 tar。小型独立实验也确认相同损坏 DOCX 放在 platform 可保真归档，放在 pytest-tmp 则遗漏。修订时按 case 稳定保存需要复核的输入、输出、失败及断言依据，并验证每 case 原件与映射。保留敌意样本字节，不能用“tar lossless”代替“采集完整”。

2. **P1：测试前失败未稳定落盘完整原始错误日志。** `source_suite.py:46–74` 的身份/绑定/材料前置检查在 try 之外；小实验缺 materials 时只有 identity/bindings，没有 failure.json 或 stdout/stderr。workflow `:31–44` 的 uv/OCR/browser/outer runner 未统一保存原始 stdout/stderr。collector 能保留已有 materials/logs，但下载失败、超时、browser 安装或 outer 前置失败仍可能只有 CI 文本日志，未随加密原件保存。修订时从控制命令启动前就记录 argv、输出及失败上下文，让无 target/materials/platform 时也能采集。以早失败控制验证加密恢复后的原始 stderr。

## 已核实的正向结果

- stdout 与 JUnit 一致：6 passed，0 failures/errors/skips，JUnit 0.158 秒。selection 明确为 orchestration smoke subset；用例是采证设施控制，没有实际 OCR/浏览器业务。
- 六个 nodeid 有独立目录，两个 key-format 目录实际携带文件；四个为空的目录按缺口保留。
- 原 tar 的 16 个成员逐一与 raw-index 及 platform 原件核 SHA/长度一致；归档范围内的损坏 .docx 可原字节保留。
- workflow 安排真实 OCR/font 与 Chromium 准备先于测试，并向测试显式传路径。此为代码顺序，不是本机 smoke 已验证环境准备。
- Windows 新建独立 LocalUser 并用 Credential 启动，runner 拒绝 is_admin 或任何 Administrators SID；设计上可排除 filtered-admin。尚无本轮 Windows 实际通过证据。POSIX Probe 拒绝 root，本机 actor 为 uid501。
- always 分支对原件 pack 并只上传加密 envelope，设计兼容 tar 内敌意字节；source-suite 本轮完整 pack/官方 artifact/恢复尚未实证。
- 入口范围清楚，skip 与安装态 E/H/X 仍单列；没有把 pytest exit0 自动解释为完整 R008 交付。

## 版本与原件

smoke target 与 source-bindings 完全一致，共 282 个绑定；result 记录运行结束时 source_unchanged=true。两个 source 候选脚本仍与 smoke SHA 相同。审查时 `document_formats_protocol_guards.py` 已有后续改动，因此不能将旧 smoke 扩大为当前全部源码同版通过。workflow/request 不在 bindings() 内，本报告 JSON 单独冻结其 SHA。

完整所读文件 SHA、逐 case 清单、原 tar SHA、静态依据及小型独立采集/前置失败实验见同名 JSON 与 `source-suite-candidate-review-checks.json`。本轮只写这三份审查文件。
