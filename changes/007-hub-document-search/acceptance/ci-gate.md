# TC-007-regression-ci — 完整回归与三系统 CI 门禁

本项承接 SC8 原 packages-2 中“完整回归及三系统CI通过”，不改变 SPEC 或降低最终 PR head 的 CI 要求。独立包构建、安装与模块摘要仍由 TC-007-packages 验证；不能用包探针的退出 0 代替本项。

前置：记录候选 Git 提交、产品/测试/构建/CI 工作流字节摘要，使用本任务独立环境。仅本机和仓库 CI，不访问 ESXi、日常 Hub 或真实资料。

1. 执行当前候选完整 pytest，保存真实 argv、stdout/stderr、JUnit XML、退出状态；核对 XML 总数与失败/错误/跳过及原输出一致。平台限定跳过逐项解释，不能把普通失败改为跳过。
2. 从 GitHub 取得该候选的 Test packages 实际 run/job/step 原响应，逐项核 macOS、Ubuntu、Windows 的 pytest、双包构建及分环境安装步骤全部 success；保留各系统 JUnit 原件、原始/公开副本 SHA 和精确 run/head 链接。不使用排队或单一总状态代替三个实际 job。
3. 在同一证据中记录工作流及产品版本。若后续只有说明/证据提交变化，明确所记录 head 与当前 head 的差别；合并前另核最终 PR head 的三系统 CI 已全部通过，不能把旧 head 的结果称为最终 head 结果。

通过：完整 pytest 实际退出 0、无失败/错误，三系统实际测试/构建/分环境安装步骤均成功，证据与所记候选相符。未完成、缺原件或版本不符即待验证/证据不足；普通单测 CI 不能替代 E1/E2 实际服务、普通身份或物理跨 OS HTTPS 验收。
