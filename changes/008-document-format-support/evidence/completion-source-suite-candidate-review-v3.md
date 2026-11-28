# Source-suite v3 独立候选复审

结论：**候选通过，可进入三系统 source CI 调试。** 当前范围未发现阻塞项。此结论只针对入口候选与采证控制，不是完整 C1/R008 或安装态 E/H/X 通过。

## 历次问题闭合

- 归档持续覆盖整个 work，包括 pytest-tmp 和日志。Mac 原始 tar 共 90 成员：81 普通文件、8 symlink 元数据、1 FIFO 元数据。逐项与 raw-index 及本机原件核对，SHA/长度/链接目标/类型一致，无漏项。
- 前置失败保留 failure.json；准备、browser、outer 与 Windows credential child 日志在采集范围。采集和 pack 使用独立 no-project Python，不以重新安装产品掩盖准备失败。
- v2 junction 缺口已修正：entries 在递归前检查 symlink/Windows reparse，链接只记元数据，根链接拒绝。真实 Windows 控制的 collector tar 只有一个 junction portable symlink 元数据成员；raw-index 记录原目标和 reparse tag 2684354563。外部 sentinel 未进入这个 collector 归档，其本体在测试结果包中保留且原字节符合独立预期。
- v2 路径发现日志缺口已修正：发现命令 stderr 单独落盘，成功路径以 printf 保存 stdout。sys.stdout.write 不加末尾换行，静态未见 CRLF 尾字符问题。bash/PowerShell 路径均引号保护；真实整条 Windows CI argv 仍待调试确认。

## 实际原件核验

Windows 输入 tar SHA256：`20e5210fd31818f9d59ccb62ab1bc46b4c82c5624d67f9be746605d595d5bd63`。其中采集器和测试源码均与当前候选逐字一致。结果 tar SHA256：`4d24b7a44369d68428c4938377cf90aa8c0e9ac463b46cc154868790d221ad7c`。直接打开全部 16 个普通成员，顶层恢复文件一致；四个原始文件控制逐字核对，坏 DOCX/BOM/早失败日志未被语义检查误拒。

Windows stdout 为 3 passed、1 POSIX-specific skip，1.13 秒；JUnit 为 4 项、0 errors/failures、1 skipped，记录时间0.893秒。该次是管理员 SSH 账户下的组件验证；原结果只有用户/SID，没有普通 token/groups 证明，**不能算标准 E 格或普通身份整套 source-suite 通过**。

Mac 编排 stdout 为 9 passed、1 Windows-only skip，0.17 秒；JUnit 为10项、0 errors/failures、1 skipped，0.176秒。context 明确 local-smoke3-not-ci。283 个源码 bindings 与 target 一致，当前零差异，实际 result 记录 source_unchanged=true。

## CI 调试范围

Windows入口仍设计为新建实际普通账户、以 Credential 启动，拒绝管理员 token 及 Administrators SID，故不接受 filtered-admin。需要由后续 CI 原件确认真实 token/argv/ACL/清理、OCR/browser、所有测试结果与 skip，再核官方 artifact、加密恢复及逐文件原件。当前小型采证控制不替代这些工作。

只写本轮 v3 报告和核验附件，未改候选、未覆盖旧报告。所有所读原件 SHA 和细项核验见同名 JSON 及 source-suite-candidate-review-v3-checks.json。
