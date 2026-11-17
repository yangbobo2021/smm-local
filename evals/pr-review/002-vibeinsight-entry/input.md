# PR Review EVAL 输入说明

本案例来自 PR #21 的用户发现问题。代码固定为 `c891339`，基线为 `d2dee18`。
原 PR 的实现、README、使用指南、需求、计划及完整 diff 已冻结在 Case 01。
验收材料来自评估开始时的 PR 正文，只保留功能验收和真实 staging 回执。
它们属于历史执行证据，评估本身采用材料回放。

将一份 `prompts/*.md` 与一份 `cases/case-*.md` 拼接后交给全新 Reviewer。
Reviewer 不接收本说明、评分规则、其他 Prompt、既有审查结论或本次聊天历史。
每份输入包含所需的文件内容和行号，Reviewer 直接审查材料并输出中文结果。

| 样本 | 来源与用途 |
| --- | --- |
| Case 01 | 真实 PR 快照，首页缺少新能力说明，但详细指南和通用链接存在。每版三次。 |
| Case 02 | 从真实样本构造的对照，只在首页补能力介绍、适用对象和直达指南链接。每版一次。 |
| Case 03 | 从真实样本构造的对照，README 明确以文档站首页为操作入口，文档首页介绍能力并链接指南。每版一次。 |
| Case 04 | 仓库既有 `001-source-cli-help` 样本原文，检查旧 EVAL 能力是否保留。每版一次。 |

Case 02 和 Case 03 的文档变化只存在于评估输入。所有样本使用相同代码变更，
两个对照在输入的 diff 中同时展示对应的文档变化。
输入没有把“检查 README”作为额外任务交给 Reviewer。

`prompts/current.md` 是原审查模板的逐字快照。
`prompts/candidate.md` 是首轮候选，增加从实际主入口逐步核对发现、导航、前置条件和结果的要求。
候选也要求承认已有可用路径，并区分发现成本和操作阻断。

维护者已确认采用 v4，正式模板位于 [`changes/_templates/pr-review.prompt.md`](../../../changes/_templates/pr-review.prompt.md)。
`prompts/current.md` 继续保留评估时的旧版基线，历史比较和后续复跑使用该固定快照。

`frozen.json` 记录 Prompt、输入、评分规则、历史证据和运行器的 SHA-256。
评分规则在运行前冻结，运行期间不调整候选或规则。

## 复跑

需要已有可用认证的 Codex CLI 和 Python 3.11+。运行器使用独立临时目录、
`--ephemeral`、`--ignore-user-config` 和只读沙箱。两版沿用相同的 CLI 默认模型及推理设置，
实际值从每次启动日志记录到回执。每次最多运行 15 分钟。

从本文件所在目录运行，输出目录需为新的路径。

```sh
python3 run.py --output runs/new-comparison --private-logs /tmp/smm-review-eval-logs
```

原始 CLI 过程日志保存在指定私有目录。输出目录保存最终审查回答和执行回执，
包括输入、Prompt、回答的哈希、执行状态、实际模型和时间。
技术失败需先诊断并单独记录。不要把它计入审查能力的得分。

按 `rubric.md` 对最终回答逐项评分。独立评分者仅接收匿名回答、对应样本和规则，
评分后再恢复 Prompt 标签，并逐项核对摘录。比较报告记录在本目录的 `comparison.md`。

每个 case 的回答齐备后，可以用下列命令启动独立匿名评分。
将 `02` 分别替换为 `01`、`03`、`04`，评分结果与匿名标签映射保存在运行目录。

```sh
python3 grade.py --runs runs/new-comparison --private-logs /tmp/smm-review-eval-logs --case 02
```

本次执行方式参考 [OpenAI 非交互模式说明](https://learn.chatgpt.com/docs/non-interactive-mode)。

## 候选修订后的同套复跑

保留原始样本、评分规则和执行器，使用 `replay.py` 对另一版候选进行完整对照。
它先核对原始冻结清单，在临时副本中仅替换候选，再重新运行当前版与候选版的全部 12 次审查及匿名评分。
新轮会保存自己的 Prompt 快照、冻结清单和回执，已有结果保留。

```sh
python3 replay.py --candidate prompts/candidate-v2.md --output runs/new-v2-comparison --private-logs /tmp/smm-review-eval-v2-logs
```

v2 的文本调整见 [revision-v2.md](revision-v2.md)，结果见 [comparison-v2.md](comparison-v2.md)。
v3 的结果见 [comparison-v3.md](comparison-v3.md)。
最新候选为 [candidate-v4.md](prompts/candidate-v4.md)，调整依据见 [revision-v4.md](revision-v4.md)，
完整比较见 [comparison-v4.md](comparison-v4.md)。复跑最新候选时，将命令的 `--candidate` 指向 `prompts/candidate-v4.md`。
