# SPEC 平台交付与验收 EVAL

维护者已于 2026-11-17 确认采用候选 v3，正式 [SPEC 模板](../../../changes/_templates/spec.md)已按该版本替换。
生效范围、确认依据和模板摘要见 [采用记录](adoption.md)。以下保留评估时的两版比较标签。

| 最后一轮 | 全项通过的回答 | 检查得分 |
| --- | --- | --- |
| 评估时旧模板（current） | 3/18 | 48/75 |
| 候选 v3（candidate，现已采用） | 18/18 | 75/75 |

六个样本各三次，三轮共 108 次生成、18 组匿名模型评分。
这是已知问题开发集上的规格生成结果，不是产品跨平台实测或对未知任务成功率的估计。

- [最终比较与证据](comparison-v3.md)
- [采用的模板快照](templates/candidate-spec-v3.md)与[评估时提案 diff](candidate-v3.patch)
- [v1 比较](comparison-v1.md)、[v2 比较](comparison-v2.md)及各版修改依据
- [冻结的 EVAL 定义](input.md)、[评分规则](rubric.md)、[历史来源](provenance.md)

所有公开材料的校验和见 [SHA256SUMS](SHA256SUMS)，可在本目录运行 `shasum -a 256 -c SHA256SUMS`。

`input.md`、`frozen.json` 的“尚未执行”及比较报告中的“正式模板尚未替换”，均保留各自阶段的历史状态。
原始输入、规则、比较报告、运行回执和评分不随采用决定改写。各轮 `current.md` 是评估时旧模板，
复跑继续以该固定基线比较；不会把现已采用的 v3 当成历史旧版。本次真实执行在各轮
`runs/2026-11-17-v*` 中独立保存。

## 复跑候选 v3

需要已认证的 Codex CLI 和 Python 3.11+。从仓库根目录运行，指定全新的输出目录。
执行器的历史默认候选是 v1，复跑 v3 须明确传入 `--candidate`：

```sh
python3 evals/spec-generation/002-platform-acceptance/compare.py run \
  --output evals/spec-generation/002-platform-acceptance/runs/new-v3 \
  --candidate evals/spec-generation/002-platform-acceptance/templates/candidate-spec-v3.md \
  --private-logs /tmp/smm-spec-eval-private
python3 evals/spec-generation/002-platform-acceptance/compare.py grade \
  --output evals/spec-generation/002-platform-acceptance/runs/new-v3 \
  --private-logs /tmp/smm-spec-eval-private
python3 evals/spec-generation/002-platform-acceptance/compare.py summarize \
  --output evals/spec-generation/002-platform-acceptance/runs/new-v3
python3 evals/spec-generation/002-platform-acceptance/verify_results.py \
  --runs evals/spec-generation/002-platform-acceptance/runs/new-v3 --write-report
```

每个调用最多 15 分钟，默认三个并发。技术失败单独诊断并保留原记录，不能算内容失败。
若评分引文校验失败，保留原始评分，审查对应回答后单独记录 `citation-audit.json`，
不能修改原始答案或评分来绕过校验。首轮实际例子见 [核正记录](runs/2026-11-17-v1/citation-audit.json)。

只复核现有结果、不调用模型：将下列命令的 `v3` 换为 `v1`/`v2` 可核对其他轮次。
默认只读，不更新已有回执；`--write-report` 仅用于保存新的核验记录，拒绝覆盖。

```sh
python3 evals/spec-generation/002-platform-acceptance/verify_results.py \
  --runs evals/spec-generation/002-platform-acceptance/runs/2026-11-17-v3
```

执行方式依据见 [OpenAI Docs](https://learn.chatgpt.com/docs/developer-commands#codex-exec)及
[项目指令读取配置](https://learn.chatgpt.com/docs/config-file/config-advanced#project-instructions-discovery)。
