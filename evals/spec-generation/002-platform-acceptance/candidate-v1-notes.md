# 候选 SPEC 模板 v1

当前正式模板和固定基线都是 `changes/_templates/spec.md` 的原文，SHA-256 为
`4b11b4be6983781c6a11e1ac02ae0fb90ef5e40d64593b520aa9e978cb52ac3c`。
本次仅新增 `templates/candidate-spec-v1.md` 参与比较，没有替换正式模板。

候选保留原有四节和可观察行为要求，新增三处约束：

1. 边界从项目既有承诺识别受影响组件的支持环境，不从开发电脑或包格式猜测。
   只有会改变交付或验收的环境决定缺失时，才列为待确认。
2. 设计说明对环境的依赖及风险，连接到验收覆盖，避免已有设计与验收要求脱节。
3. 验收在 SPEC 内确定必要的实际环境和通过结果；同时允许有依据地复用当前环境的
   共用行为证据。机器、脚本、顺序和 CI 留给 PLAN，不机械规定完整平台笛卡尔积。

模板没有写入 SMM、VibeInsight、`psql`、固定操作系统名称或任何评分 ID，适用于本项目
不同类型的变更。平台范围、风险程度和所需证据由具体资料决定。

比较沿用已冻结的六个输入、25 项检查及旧 CLI 帮助评分，未为候选修改 EVAL。
每版每个样本三次，共 36 次生成；评分隐藏版本和顺序，按逐字摘录核对。
原始提取说明中“尚未执行”记录的是定义时状态，本轮执行和结论另存，不覆盖该历史快照。

执行器使用独立空目录、禁用项目指令读取、忽略用户配置、临时会话和只读沙箱；
两版不指定模型或推理覆盖，实际启动信息逐次记录并核对一致性。
非交互执行参数参考 [OpenAI Docs](https://learn.chatgpt.com/docs/developer-commands#codex-exec)，
项目指令读取限制参考[官方配置说明](https://learn.chatgpt.com/docs/config-file/config-advanced#project-instructions-discovery)。

重跑使用已有 Codex CLI 认证和 Python 3.11+，从仓库根目录运行，输出目录必须为新路径：

```sh
python3 evals/spec-generation/002-platform-acceptance/compare.py run \
  --output evals/spec-generation/002-platform-acceptance/runs/new-comparison \
  --candidate evals/spec-generation/002-platform-acceptance/templates/candidate-spec-v1.md \
  --private-logs /tmp/smm-spec-eval-private
python3 evals/spec-generation/002-platform-acceptance/compare.py grade \
  --output evals/spec-generation/002-platform-acceptance/runs/new-comparison \
  --private-logs /tmp/smm-spec-eval-private
python3 evals/spec-generation/002-platform-acceptance/compare.py summarize \
  --output evals/spec-generation/002-platform-acceptance/runs/new-comparison
```

第一步会在任何生成前冻结模板、材料、执行器、评分指令/Schema 和完整运行顺序。
运行中不修改候选或规则。技术失败单独保存，不能算成内容失败；处理失败保留原始记录。
原始过程日志保存在私有目录，回答、回执、匿名映射及评分在运行目录。
每个调用最多 15 分钟；`--resume` 只续接缺失调用，不覆盖已有回答或失败记录。
