# CAS对账修复与最终候选验收

产品源码 `ba8c6d5`。已修复独立审查复现的“Hub调用中改版本，拒绝却已保存本机规则”：只登记不授权正文的提交身份，真实Hub CAS接受后，才按原本机代次条件保存规则和准确回执。网络I/O不持有跨进程锁；CAS拒绝保留本机完整规则，新保存不被旧回执覆盖，未知回执先停止自动正文并要求明确处理。

**独立需求审查已逐A/E判定SPEC验收passed；原生验收登记尚未完成，PR继续草稿。** 最终macOS、Ubuntu、Windows新包规则专项均已实际通过并获独立复核；Windows真实事后查询还确认对应调度任务、进程、Hub监听与服务文件已不存在。macOS系统级服务已实际完成，见[前一组实际运行及独立复核](../20261122-reconcile-7c72c92/README.md)。

- [初轮源码回归](full-pytest.txt)：220 passed、1 skipped；跳过的是Windows专属测试。Local/Hub两个wheel均已重建，干净checkout核对全部模块与HTML。
- [有效红灯](tdd-red/red-remote-race20/result.json)与[同版绿灯](tdd-green/green-remote-race20/result.json)：CLI/Web × local/hub × 首次读取后/第二次读取后/CAS前，共12组合；最终Hub头/正文/无正文派发断言均到达。绿灯另有[80项相关回归](tdd-green/green-remote-race20/regression.stdout)。[红灯独立意见](reviews/review-red-remote-race20.json)、[绿灯独立意见](reviews/review-green-remote-race20.json)均已登记。
- [正式SC1](execute/execute-final20-sc1/result.json)、[SC2](execute/execute-final20-sc2/result.json)、[SC3](execute/execute-final20-sc3/result.json)、[SC11](execute/execute-final20-sc11/result.json)：4组21TC均实际执行并获独立复审。只认领各TC分配项，其余原有测试/实际平台见[完整A/E依据映射](coverage.md)。
- 项目预览在独立复审后补齐：实际完整G集合唯一；assign/map/merge目标允许时首次预览、过期确认、新预览五表快照不变；真实改变合成来源头后处理3个文件，再比全部会话归属，保留普通/global合并拒绝。旧需修订意见保留，不用被跳过的导入冒充重放。
- [最终包变化对照](package-comparison.json)：7c→ba8只有Local upload.py字节改变，Hub全部模块不变；旧服务/其他入口实测保留原版本，不改标为ba8执行。最终新包实际规则运行见[运行索引](run-index.json)。

[此前7c证据](../20261122-reconcile-7c72c92/README.md)与本目录的原18/19记录保留原始版本。初版测试把set回执与status整体比较，后者额外有conflict/restore_pending字段；纠正为实际status基线后，重新在原产品取得红灯。第一次绿灯后新增了同场景在途设计，旧绿灯原生登记被设计版本核验拒绝；定稿设计后已重新执行/复审有效20链，不改写旧记录。所有结论以当前有效链与真实执行为准。

公开文本仅脱敏测试账户、IP、私有绝对路径，合成正文不改。截图为真实任务UI；配置、Token、私钥、数据库和浏览器trace不导出。[provenance](provenance.json)列原件/导出SHA，`SHA256SUMS`用于核对公开文件。005没有连接真实VibeInsight或服务器数据库造数，也未升级日常SMM。

[最终PR审查](reviews/pr30-final-ba8-review.md)无新增已确认产品/导航缺陷；[Mac/Linux最终包复核](reviews/review-platform21-mac-linux.md)、[Windows最终包复核](reviews/review-platform21-windows.md)及[事后清理补充](reviews/review-platform21-windows-cleanup.md)分别列出其实际检查和范围。最终产品[三平台CI](https://github.com/yangbobo2021/smm-local/actions/runs/45002908134)全部成功：Mac/Linux各220 passed、1 skipped，Windows221 passed，三平台均构建两个wheel。

逐条需求审查又要求将原文明写的共用边界落为实际用例，见[新增正式链索引](required-boundaries/execution-manifest.json)：A6查询内关联变更，A8本机/Hub首与非首消息删除、重复position与真实换Hub，A2 all/none/all与3/2/1回执及本机最新ACK，A4未提交整批故障、accepted=1/2无效回执、混批两顺序整体拒绝和允许正控。5个新TC/14参数均在required23正式执行并获独立复审；required22的测试前提/覆盖问题保留原件，第一轮修订后关闭。补齐后的[完整源码回归](full-pytest-required23.txt)为234 passed、1 skipped。[PR增量补审](reviews/pr30-final-required23-supplement.md)通过，没有修改产品字节或扩大产品契约。

[最终独立需求意见](reviews/delivery-r005-final-ba8-v1.json)逐A1–A12/E1–E5给出passed，明确外部实测、历史版本复用、源码推论及新CI边界。尝试把该结论写入原生工具时，[登记器返回blocked](native-registration-blocked.json)：`selected delivery scope lacks required passing scene evidence`。原生仅直接关联了部分TC，外部平台/历史证据单独维护，12场景内部关联未全部补齐；因此没有登记为原生passed。保留独立SPEC结论和工具实际状态，待维护者选择继续补原生关联，或以本PR逐条实测及独立意见交付。
