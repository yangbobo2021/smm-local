# R007 完整需求独立交付判定：blocked

项目 `/private/tmp/smm-007`，验收 `AT-SMM-007`。Reviewer `/root/delivery_007_approved_v1`。本轮只读项目、测试与证据，没有执行测试或产品，没有操作 GitHub、服务、ESXi，也没有应用纠正草稿。仅写本轮原生意见和本报告。

原生意见：`/private/tmp/smm-007/.acceptance-local/native-v1/AT-SMM-007/review-inbox/delivery-r007-approved-v1.json`，严格仅含 `status`、`reason`，写出后已立即通知主 Agent 登记；登记成功以主 Agent 返回的收据为准。

## 判定依据与完整范围

实际阅读根 AGENTS.md、007 intent/spec/plan、当前定义 `000007.json`、交付验收技能及其 `references/execution/reviewer.md` 的需求级规则、额外轮授权、两项测试准备复审、library 正式执行复审、三平台及用户路径失败复审和服务复审。范围是完整 B1–B8、A1–A10、SC1–SC16/36TC，未因执行授权较窄而缩减需求。

定义原字节 SHA 为 `d0f03b256990c6105b6a8bda288c66124a098a9779bf1b319cee65f1940f8bcd`。实际重算交接快照 `work/delivery-r007-approved-v1-view.json` SHA 为 `c6d13ce7164e777bdd314a7f6ed0c5ec8c5245745e0cab13304a4c1e5352a8c2`，与交接一致。逐项读取当前状态，得到 **1 passed、4 needs_revision、30 not_executed、1 insufficient_evidence**，16个场景均未完整验证。未逐一重复校验全部历史附件；关键收据、失败原件、源码与强制平台缺口足以排除 passed。

需求级规则要求：当前正式证据证明任一必测产品行为失败则 failed；尚无法确认产品失败且证据不足则 blocked。以下已核材料支持后者。

## 实测结果、测试故障与未到达范围

| 范围 | 独立核实与边界 |
|---|---|
| library-update | `execute/execute-library-update-approved-v1/result.json` SHA `1d493010be647ebf32a91128f42315f3f755e6e0cec52e9797d315a1d079e8da`；原 stdout 为 1 passed，stderr 空。已登记正式复审只认领 `library-update-2`，包含两创建端、两目标和允许/暂停前已有材料状态。支持这一个检查通过，不能推及整个 SC10、真实浏览器或 E1/E2。 |
| listing-coverage | `debug/debug-listing-coverage-approved-v1/result.json` SHA `6ce054cf3b18a43ead1c4c02b4a50d45ba1c3461a0d44dc72619dc09a9ea4f3a`。原 `TC-007-listing-coverage/run.stdout` 在测试第31行 SQL 读取不存在的 `projects.stable_key`，尚未调用后续列表断言。源码和准备独立意见吻合：是测试 implementation 故障。每端只一来源的输入还不能排除遗漏第二来源，准备复审已指出独立来源全集/唯一性缺口。没有正式放行，不能判产品列表失败或通过。 |
| E1 三平台 | 当前三份 `manual-e1-{macos,linux,windows}-approved-v2` 原 failure 都定位 `hub_documents_platform.py:1753`，抛错在 `execute:2210` 的 stdio 阶段。已核各目标原 SHA 与交接报告一致。之后两端 Web、生命周期及业务后重启 Web/stdio 未到达，故三个完整长检查均缺覆盖。 |
| 用户路径 | `manual-user-discovery-approved-failure-v2/result.json` SHA `af6eebb3596188ff2cc89681b674c5eb7e13ecf086246af746cdf9b123d680a8`，原 failure 同为共享 stdio 的 ID 断言。后续发现链/Web/CAS未到达。实际查看 `scripts/acceptance/README.md:5` 可确认36项与当前证据直链静态修正；隐私四阶段局部原件已有独立复审支持，但不授完整用户路径通过。本 Reviewer 未另作图片判定。 |

E1 三份目标原 SHA 依次为 `0e9edb68848cf0b74883a1e7e4263c85cbe346898213a9c169ef48b3d064704b`、`85458cdcee5cba1e1db917f63223d5e049c25d24d5242006d200eaf38e0cc7a6`、`d40cd9b10a01858d083f15d1555430d6e8cf98f720d189fd214c6c3c7c729c99`。实际读取相应 review result，三平台及用户项都是 `needs_revision / implementation`、`covers=[]`；library 正式 review 为 passed、仅 `library-update-2`，listing 准备 review 为 `needs_revision / implementation`。

独立展开四组 `mcp-5.json`/`mcp-7.json` 的原始 `content[0].text`，每组均10个搜索结果、10个实际 read；逐目标完整 origin、版本及响应中存在的双摘要/长度相同。每组两份 combined 命中读取 local 时内部 ID 不同，而 `origin.document_id` 相同；相关 MCP 文件 SHA 与目标 artifacts 相符。这是本轮直接复核的局部事实，没有声称执行器后续循环断言均通过。

SPEC B6按原档案/设备/文档身份及版本、双摘要合并，B7允许沿当次同版本精确来源读回并显示实际端。实际源码 `src/smm_local/document_search.py:241–268` 遍历本机后远端，保留远端候选内部 ID、将两端 ref 合并；`:325–332` 沿 bundle parts 返回首个有效端的真实 read。满足同源同版且本机 ref 有效时会进入该分支，产生合法的搜索/读取归档内 ID 差异。产品契约未规定这两个内部 ID 相等，因此新增断言的失败不能判产品实败。此源码说明仅解释已观察到的 ID 差异，不能证明未执行的 Web、重启或生命周期。

## 必需环境和证据缺口

SPEC A9明确 E1 三格及 E2 均须当前同版业务与独立复审，缺任一必需环境不得需求 passed。A8发现链及A10真实网页主路径也不能由本轮提前停止推成通过。

`reviews/services-manual-review-v1.md` 及关联历史记录支持大量真实服务局部事实，但 Ubuntu user-systemd 和 Windows SCM 都未取得网页管理资料在停启后按新建项目查询、沿旧有效 ref 读取的原件；Windows另缺服务和防火墙删除后的不存在查询。外部路径 native 缓存重启成功与服务真实身份不能证明网页管理副本同样满足承诺。用户明确“保留缺口，先完成其他验收”，并未修改 SPEC，当前服务项无可授予的完整通过。

实际打开 `work/manual-evidence/cross-machine-resource-v1/resource-observation.json`：不同OS真实机器 HTTPS 业务为 `not executed`，家庭 ESXi 已被排除，替代资源答复“暂时没有，先继续本机与 CI”，未访问排除主机。同机逻辑档案、同宿主服务及普通 CI 无法排除物理跨机 TLS、远端网页上传、版本和断线恢复条件可能改变结果，因此保留资源/证据阻塞，不推断产品失败。

旧26自动+2人工绿灯及包/回归/CI记录仍有历史价值；产品 b7ed 字节未改也不等于新增测试已通过。共用测试和说明 bindings 改变后，当前30项 not_executed表示缺适用正式证据，并非观察到30项产品回归。重新匹配只能登记候选；63份公开选件、36身份及双SHA完整性也不能证明缺失业务。

## 后续边界

两纠正草稿尚未应用，额外一轮授权已按实际失败用尽；本意见不授予新的执行或修改权限。若后续获准，先修测试实现并取得适用设计/执行复审，再补齐当前候选正式证据、完整 E1/用户路径；服务缺口须遵守用户停止决定，真实跨机须有另行获准资源。即使其余自动证据可以复用或重新核实，上述 A9 强制缺口仍独立阻止整项 passed。

**完整 R007：blocked。当前没有核实到有效正式证据证明必测产品行为失败，故不判 failed；也没有足以覆盖完整范围的证据，故不判 passed。**
