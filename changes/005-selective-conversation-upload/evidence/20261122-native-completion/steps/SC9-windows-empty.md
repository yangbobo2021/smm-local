# Windows 三入口空查询长轮验证

TC-005-empty-windows；empty-e1-windows。保留原业务判据和身份，kind改人工仅因原生自动命令最长300秒，已试跑实际320.432秒。原debug30超时仍不足，原事件在windows-empty30-recovered保留原时间/包版本/worker退出，不冒充本轮正式操作。

1. 核对已准备的VM76 MAC、当前目标安装模块和任务身份；确认此前任务已结束、task为空，测试只在SmmSelective005任务路径，不改日常SMM。
2. 在本机控制环境直接执行以下外部命令，使用唯一ACCEPTANCE_EVIDENCE_DIR；原生execute不能包装这个长轮。记录启动/结束时间、真实argv、外部退出码、stdout/stderr、远端worker receipt，失败原件也保留，不复制旧passed填空：

`/private/tmp/smm-005-control-env/bin/python scripts/acceptance/selective_upload_empty_recorded.py --target-config .acceptance-local/native-v1/AT-SMM-005/native-targets/empty-windows29.json --probe empty --mode client`

3. 从本次原件核对最终Local25/Hub24完整安装模块/版本、普通身份、loopback HTTPS服务及完整正控local-A/remote-B/vibe-V。读取successful-empty-cli-mcp.json及successful-empty.json：all/project各CLI、实际stdio MCP、Web共六响应均results=[]、coverage local/hub complete、无失败原因。实际打开本次successful-empty-all.png和successful-empty-project.png，画面须有确定不存在查询词、无匹配结果、两端已检索及相符范围；轨迹与原响应/页面断言核对实际点击先后。
4. 核对本次result真实起止与passed、cleanup.failures=[]、ordinary worker实际exit0、外部ssh/包装退出0；原生manual记录实际执行/观察的真实时间、版本、原字节文件及摘要。若外部仍在运行或缺原件，不填通过。

独立准备意见就绪后才开始这次正式运行，结束后交另一位Reviewer真实查看原图、原始响应/代码断言及全部SHA。不以原debug30的worker0覆盖其原自动timeout。
