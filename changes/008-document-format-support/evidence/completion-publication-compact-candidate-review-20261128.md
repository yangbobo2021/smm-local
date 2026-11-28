# publication 与 compact 候选独立复审 v1

项目 `<TASK_WORKTREE>`，AT-SMM-008 / PR43。独立 Reviewer `/root/completion_publication_notice_candidate_review`。结论仅针对测试/CI候选，不代表正式 C1、E/H/X 或整008通过；未合并。

## 1. 浏览器完成提示观察器候选：passed

实际读取原始 `hub-trace.zip`：`hysq@5219` 成功结果断言于13794.695ms结束；`hysq@5221` 于13799.221ms返回“原件已接收，正在本端处理；处理完成后再按项目检索。”；13858.664ms的真实DOM快照已为“Hub 文档已保存并采集；可立即在当前项目检索。”，相差59.443ms。实际打开原 `hub-failure.png`，可见对应资料成功、ready、版本1/处理版本1；notice不在该视口，不能只用PNG认定notice完成。Hub源码在追踪上传结果后仍await reload，再写最终notice，支持这是跨异步面的瞬时采样故障。

候选保持原 not-processing 与 success 正则，增加有界expect，随后对同次inner_text再核两个规则。没有移除原测试函数或24流程/端：8资料×首次/缓存重处理/替换；Local/Hub、发布门内状态、未发布读取拒绝、真实CID/AID/V/P、旧ref失效和独立全文/表格/原件检查保留。真实浏览器synthetic DOM控制只证明观察器接受异步final并拒绝stuck/wrong，不能替代真实产品路径。无阻塞发现。

## 2. compact 加密诊断证据候选：passed

只复制7个固定platform诊断名和4个prepare/outer日志，逐字节保存并记录长度/SHA、缺失清单；测试排除额外task-token。新增scope明确仍需完整加密原档案；无业务passed或full-recovered声明。compact与full采用不同artifact名称及job_key，run/commit/name均进入既有AES-GCM认证上下文。工作流只上传密文 `.smm-evidence`，不会上传明文日志、context/index或私钥。原完整tar收集/逐成员校验/加密/上传步骤全部保留；compact和full均使用always，compact普通失败不会条件跳过后续full。总job超时/取消仍可能使保存不完整，不能据compact宣称full回收或验收通过。

当前输入是控制器在fresh任务目录产生的固定诊断文件，不递归遍历测试临时材料。`collect_triage` 的is_file/read_bytes会跟随链接，因此它不提供任意不可信路径的no-follow保证；如将来扩大输入信任边界，宜补lstat/reparse及根路径核验。这是当前限定生产路径下的防御性建议，不是已证实当前CI读取外部敏感文件。无阻塞发现。

提交前按AGENTS.md在PLAN补记这两项方法调整及原因；当前候选未提交，不据此判阶段违规。可选补充compact失败后full仍执行的工作流控制。

## 验证及边界

本次独立运行小范围：5 passed、1 Windows junction平台skip、1依赖弃用warning，1.42秒。第一次误选系统Playwright缓存1228而候选要求1255，浏览器启动失败；已保留为环境失败，随后使用任务内准备的1255路径重跑成功。原提供stdout亦实际打开：notice 1passed、custody 4passed/1skip。

未跑大C1，未做正式执行/PR级审查或新CI artifact加解密回收，未修改源文件或历史原件；未读取/导出ci-keys/private.pem，未伪造native意见目标。旧Windows失败保持原结论。精确源码、原件及日志SHA与执行命令见同名JSON。

## 源码 SHA-256

- `AGENTS.md`: `e93069c4772e63e3303453f4b58d21afea931e848c0b9b681a9f3e9a3755e7c1`
- `changes/008-document-format-support/intent.md`: `12a585c4601a087f77a852ea851cad51da19bf74503ab433c755668d43a11394`
- `changes/008-document-format-support/spec.md`: `99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986`
- `changes/008-document-format-support/plan.md`: `7474676bed9d9317047b3e6f653749e227d90f22697c461d5d732798b661e935`
- `tests/test_document_formats_publication_state.py`: `1601ef6f85b8cf9e84d1db894c0f8ce4fb92b640fc027718140d518a550bab7a`
- `scripts/acceptance/document_formats_source_suite.py`: `6e4cc0b1f78256ff0411a930fe929b8009f81ea364080303459512bf9230d23a`
- `tests/test_document_formats_source_custody.py`: `386e1d20490f4f0c59e835fff10f9c294b2449060ee3f757be08e783c803a40f`
- `.github/workflows/document-formats-source.yml`: `76bea0c0f9716f06c99d451afdfc954538ae574fd629f569adce4a1f62283992`
- `scripts/acceptance/document_formats_evidence.py`: `cc4e599066d8c26271f32fb17ee87a5be099e97801248a2494e47a2da961ccc1`
- `src/smm_hub/static/index.html`: `7acc55a752cc508678b073d2fc12a19d853ef9b262e258e32582910740afe9ec`
- `src/smm_local/static/index.html`: `7dd4bf6f9f46fd63a79a3b1fd75eadc33a3d580d5c1ebce639eba87f5069b6f3`
