# PR #21 规格重生与平台验收对照

使用 PR #23 合并后的正式 SPEC 模板，基于真实项目资料独立生成一次，未使用 EVAL 构造输入。

维护者随后要求提交新 SPEC 并创建 PR。本次[提交稿](../../changes/003-search-vibeinsight-conversations/spec.md)
在原始生成稿基础上整理，具体修改和设计依据见[提交记录](submission.md)。本 PR 提交供确认，不等于实现或平台验收已完成。
以下生成稿、比较报告和回执保留生成阶段原文与状态，不因后续整理而改写。

- [新 SPEC 生成原文](spec.regenerated.md)：保留模型输出，尚未经过提交稿的人工整理。
- [与 PR #21 的逐项比较](comparison.md)：包含平台矩阵差异、原七项条件对应及仍需补强/确认的内容。
- [完整文本差异](comparison.diff)、[PR #21 原规格快照](spec-pr21.md)。
- [冻结输入与来源](inputs-frozen.json)、[生成实际输入](input.md)、[新模板快照](template.md)、
  [生成回执](generation.json)、[生成前固定的比较检查范围](comparison-checklist.md)。

新模板来自合并提交 `8e7ee1b4686dc9eea60ed3d77ffc4e3d68769af1`，PR #21 原规格固定于
`cd8f9aaaec66ac4a5d779eec69fd9c41e40131cd`。生成者没有收到旧验收文字、EVAL 评分规则或历史比较结果，
已确认的需求与设计决定作为补充输入保留。未人工补写生成稿，也没有重复生成挑选结果。

生成阶段的新稿增加了实际平台验收要求，同时留下续写结果绑定和停用规则范围的问题；本次提交稿已按
[整理说明](submission.md)处理。生成与比较阶段没有修改原 SPEC、PLAN、PR #21 正文或产品代码；
本次仅在独立规格分支提交提案，仍未改动 PR #21 分支、计划或实现，未执行新增平台测试或访问 VibeInsight。
这是历史文档对照，不是只更换模板、其他输入相同的严格 A/B 或未知任务总体性能证明。

所有公开材料摘要见 [SHA256SUMS](SHA256SUMS)；可在本目录运行 `shasum -a 256 -c SHA256SUMS` 核对。
