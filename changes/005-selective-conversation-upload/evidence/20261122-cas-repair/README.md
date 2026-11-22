# CAS对账修复与最终候选验收

产品源码 `ba8c6d5`。已修复独立审查复现的“Hub调用中改版本，拒绝却已保存本机规则”：只登记不授权正文的提交身份，真实Hub CAS接受后，才按原本机代次条件保存规则和准确回执。网络I/O不持有跨进程锁；CAS拒绝保留本机完整规则，新保存不被旧回执覆盖，未知回执先停止自动正文并要求明确处理。

**当前仍待最终平台及交付独立判定，不据本目录提前合并。** 最终macOS/Ubuntu新包规则专项已实际通过；Windows最终普通用户专项正在回收。macOS系统级服务已实际完成，见[前一组实际运行及独立复核](../20261122-reconcile-7c72c92/README.md)。

- [完整最终源码回归](full-pytest.txt)：220 passed、1 skipped；跳过的是Windows专属测试。Local/Hub两个wheel均已重建，干净checkout核对全部模块与HTML。
- [有效红灯](tdd-red/red-remote-race20/result.json)与[同版绿灯](tdd-green/green-remote-race20/result.json)：CLI/Web × local/hub × 首次读取后/第二次读取后/CAS前，共12组合；最终Hub头/正文/无正文派发断言均到达。绿灯另有[80项相关回归](tdd-green/green-remote-race20/regression.stdout)。[红灯独立意见](reviews/review-red-remote-race20.json)、[绿灯独立意见](reviews/review-green-remote-race20.json)均已登记。
- [正式SC1](execute/execute-final20-sc1/result.json)、[SC2](execute/execute-final20-sc2/result.json)、[SC3](execute/execute-final20-sc3/result.json)、[SC11](execute/execute-final20-sc11/result.json)：4组21TC均实际执行并获独立复审。只认领各TC分配项，其余原有测试/实际平台见[完整A/E依据映射](coverage.md)。
- 项目预览在独立复审后补齐：实际完整G集合唯一；assign/map/merge目标允许时首次预览、过期确认、新预览五表快照不变；真实改变合成来源头后处理3个文件，再比全部会话归属，保留普通/global合并拒绝。旧需修订意见保留，不用被跳过的导入冒充重放。
- [最终包变化对照](package-comparison.json)：7c→ba8只有Local upload.py字节改变，Hub全部模块不变；旧服务/其他入口实测保留原版本，不改标为ba8执行。最终新包实际规则运行见[运行索引](run-index.json)。

[此前7c证据](../20261122-reconcile-7c72c92/README.md)与本目录的原18/19记录保留原始版本。初版测试把set回执与status整体比较，后者额外有conflict/restore_pending字段；纠正为实际status基线后，重新在原产品取得红灯。第一次绿灯后新增了同场景在途设计，旧绿灯原生登记被设计版本核验拒绝；定稿设计后已重新执行/复审有效20链，不改写旧记录。所有结论以当前有效链与真实执行为准。

公开文本仅脱敏测试账户、IP、私有绝对路径，合成正文不改。截图为真实任务UI；配置、Token、私钥、数据库和浏览器trace不导出。[provenance](provenance.json)列原件/导出SHA，`SHA256SUMS`用于核对公开文件。005没有连接真实VibeInsight或服务器数据库造数，也未升级日常SMM。
