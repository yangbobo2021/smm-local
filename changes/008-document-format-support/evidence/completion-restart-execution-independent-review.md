本报告为独立意见的脱敏副本；私有原件SHA见 completion-acceptance-20261128.json。

# 托管上传重启正式执行独立复审

结论：`passed`，仅适用于 `TC-008-managed-upload-restart / managed-restart`。本轮只读项目、冻结测试及原始记录，没有启动业务、运行 pytest 或修改产品/测试。

## 冻结范围与记录

- 项目：`<CHECKOUT>`；验收 `AT-SMM-008`；正式执行 `execute-completion-sc7-restart-v1`。
- 定义：`.acceptance/native-v1/AT-SMM-008/definitions/000003.json`，SHA256 `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。
- 正式目标 SHA256：`c9731a48e6d84f54a29850bf4c26fd5b4058e55415f39b7538e8de0f0fd64f96`。
- SPEC SHA256：`99f0acc008f5be8201c12ff1a620457a17e4e79754131b23e829f76f38fa7986`；读取 B2/B4/B5/B7/B8、A7/A9、C1 与 SC7 对应条款。
- 设计 `design-completion-sc7-restart-v4` 结果 SHA256 `58362a0b0f88484378e3e1b74b3e95da8e5af0d5682f7477ab325c29647edc2b`；已登记候选复审 `review-completion-sc7-restart-candidate-v4`（passed）。
- debug v4 结果 SHA256 `46298e246648076b12144bc4e90fd40873b395182d7474c69a5c0dd1a8a1e701`。87 份正式绑定与 debug、候选复审和 debug/source 冻结文件逐字一致；C1 文件 SHA256 `8c83cd30be8cd234f6678b76a9152726f318091b40993763e578ddaff61248b7`。
- 正式目标只包含本 TC，`case_obligations` 只分配 `managed-restart`；记录内其他 implementation_sha256 或场景 obligations 不构成本次执行的用例或覆盖。

## 正式命令与实际结果

```text
/usr/bin/env SMM_008_OCR_EXECUTABLE=<HOME>/work/smm-008-plan/.acceptance-local/008-plan-probe/ocr-runtime/bin/tesseract SMM_008_OCR_DATA=<HOME>/work/smm-008-plan/.acceptance-local/008-plan-probe/tessdata SMM_008_FONT=<CHECKOUT>/.acceptance-local/008/materials/font/NotoSansCJKsc-Regular.otf PLAYWRIGHT_BROWSERS_PATH=<CHECKOUT>/.acceptance-local/008/materials/playwright-browsers <CHECKOUT>/.venv/bin/python -B -m pytest -q --tb=short tests/test_document_formats_upload_restart_c1.py --basetemp <PRIVATE_EVIDENCE>/c1-native-debug4-tmp
```

- cwd 为项目根；`ACCEPTANCE_EVIDENCE_DIR` 指向本正式 execute 的 attachments。basetemp 名虽带 debug4，本轮环境、请求、输出和事件实际落在 execute 独立目录。
- 正式时间：2026-11-28T00:50:25.525000+00:00 至 00:51:10.509000+00:00；收据墙钟 44.984 秒。
- 原始 `run.stdout`：`4 passed, 1 warning in 44.71s`；exit 0，`run.stderr` 空，无 skip。唯一 warning 为现有 FastAPI/Starlette httpx 弃用提示。
- 1,330 份正式 artifacts 全部存在、逐 SHA256 吻合；1,251 份 gzip 均可无损解读。正式事件 1,219 份，其中 HTTP 1,129 份；未使用摘要代替原始事件。

## 逐阶段停启、状态与清理

| 组 | 阶段 | PID | 退出/强停 | 状态 | stop 原件 |
|---|---:|---:|---|---|---|
| local 首次 | 1 | 70393 | 0/否 | 半传、无资料 | `00015-restart-server-stop.json.gz` |
| local 首次 | 2 | 70416 | -15/是 | pending@0×4 | `00034-restart-server-stop.json.gz` |
| local 首次 | 3 | 70417 | 0/否 | ready@0×4 | `00084-restart-server-stop.json.gz` |
| local 首次 | 4 | 70440 | 0/否 | ready@0×4 | `00128-restart-server-stop.json.gz` |
| hub 首次 | 1 | 70441 | 0/否 | 半传、无资料 | `00145-restart-server-stop.json.gz` |
| hub 首次 | 2 | 70472 | -15/是 | pending@0×4 | `00166-restart-server-stop.json.gz` |
| hub 首次 | 3 | 70602 | 0/否 | ready@0×4 | `00217-restart-server-stop.json.gz` |
| hub 首次 | 4 | 70620 | 0/否 | ready@0×4 | `00263-restart-server-stop.json.gz` |
| local 矩阵 | 1 | 70621 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `00417-restart-server-stop.json.gz` |
| local 矩阵 | 2 | 70665 | -15/是 | empty-success@1×4, partial@1×4, pending@1×4 | `00506-restart-server-stop.json.gz` |
| local 矩阵 | 3 | 70727 | 0/否 | empty-success@1×4, partial@1×4, pending@1×4 | `00590-restart-server-stop.json.gz` |
| local 矩阵 | 4 | 70841 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `00677-restart-server-stop.json.gz` |
| local 矩阵 | 5 | 70855 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `00749-restart-server-stop.json.gz` |
| hub 矩阵 | 1 | 70859 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `00884-restart-server-stop.json.gz` |
| hub 矩阵 | 2 | 70905 | -15/是 | empty-success@1×4, partial@1×4, pending@1×4 | `00975-restart-server-stop.json.gz` |
| hub 矩阵 | 3 | 71068 | 0/否 | empty-success@1×4, partial@1×4, pending@1×4 | `01061-restart-server-stop.json.gz` |
| hub 矩阵 | 4 | 71141 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `01144-restart-server-stop.json.gz` |
| hub 矩阵 | 5 | 71296 | 0/否 | empty-success@1×4, partial@1×4, ready@1×4 | `01218-restart-server-stop.json.gz` |

18 次 stop 中 4 次在真实 run_pending 准备屏障下优雅停止超时，随后按身份核对强停，exit=-15：00034、00166、00506、00975。它们的原始 stderr 保留 CancelledError 或 Cancel 4 running task(s)/timeout graceful shutdown exceeded；并非产品内容任务失败。其余 14 次自然退出 exit=0。矩阵 stage3 持屏障启动后实际正常退出，不能把它写成强停。

冻结 Server helper 在每次 stop 结束时核所有登记成员退出，并实际请求原监听地址得到 transport error；身份含 PID、创建时间、argv、exe/cwd 与 HTTP nonce/档案身份。本轮额外只读查询 26 个去重登记进程身份，均已不存在；没有清理不完整事件。

## 逐目标业务检查

- 原始两端各四份 DOCX：普通/全局项目各两份、同显示名而独立正文/表/字节。首次各传 part0，stage1 无资料；重开保留相同 upload_id、准确 `[0]` 和块大小，再传剩余块。48 次块请求均按保存原字节独立重算 SHA；56 次 commit（含重放）核相同 CID/AID/document_id 及实际终态。
- 首次合法捕获 stage2 的四份均 published=null、V/P=0、pending、无原件资格；默认 config_revision=0，created_at 非空。两端 stage3/4 共16次逐目标身份核对均保留原 CID/AID/config_revision/created_at，终态 ready、finished_at 非空、error=null，首次 V/P=1；正文 profile config_revision=0。
- 新增矩阵每端 12 份：普通/全局各两份 partial PDF、empty-success DOCX、ready DOCX；独立配置 revision=1。保留初始完整 latest_attempt 后，四个 ready 目标分别提交不同新 CID 并处于 pending；旧发布保持可读。stage2/3/4/5 合计96次逐目标状态核对，partial/empty 的 entire latest_attempt 与 published_snapshot 保持；replacement pending 整项保持，恢复/稳定后原 CID/AID/config/created_at 仍相同，ready+finished_at、error=null、发布同候选 CID、V/P=2。
- 对全部 HTTP 原记录离线重核96次完整正文、168次全表（所有单元/行列/合并跨度/部件定位）、40次空文档 original-info、136次 original 响应，均对应独立源真值和保存原件。96次项目召回与96次错项目空结果均逐目标通过。
- 原件输入32份，实际下载保存40组不同字节（含8份新替换版）；40组 SHA/长度全部核对。新替换版真值按已冻结独立 fixture 的 Old→New 标签定义复核，且直接打开下载 DOCX XML：全部32组 DOCX 原件的非空正文单位恰为源定义12单元（空白文件0单元），title首段及顺序一致；文本必须每源单位恰一次且无额外字母/数字，排除修订删除/分隔文字。没有把两个产品输出一致当作独立真值。
- 同一有效 ref 在适用重启前后完整正文、全表响应、coverage/profile/SHA/V/P 均一致；离线共核32个正文 ref 和72个 table ref 的重复响应。empty-success 不构造 [0,0) 读请求，以 text_length=0、资格、原件信息及真实字节核验。
- 原始8条管理副本路径与矩阵24条路径实际删除；恢复仅用已捕获 raw，deny guard 生效期间全部18个 stop 的源 open 事件为0。两个最终稳定启动/查询阶段，先断言禁止处理日志不存在，再真实调用 processing 和 Popen 正控制，两端均恰记录两事件，响应 blocked=[processing,subprocess]；正常阶段没有事件。
- 新替换成功后，每端四目标×六旧引用请求（text、original-info、original、三表）=24次，共48次400，stop stdout 完整保留。冻结 C1 :280–282 对每个请求比较完整业务表前后值，正式全绿证明这些断言均到达且通过。SQL前后值没有另行序列化，因此本轮未声称从独立SQL快照重放；证据为冻结断言、正式退出及逐次原始400日志。

## 原件 SHA256 逐项核对

下表包括保存输入和所有下载形成的40组独立字节；相同字节的输入/下载复本均已逐文件核对正式 artifact 摘要。

| 原件标签 | 字节数 | SHA256 |
|---|---:|---|
| hubrestartalpha.docx | 1105899 | `0736293337aa73c23631e7fed5c6d71d132a0fe121ecb675bf0a309641e4b60d` |
| hubrestartbeta.docx | 1105880 | `a54d3711be0007fc433e62740298902509bc63fcb5819589fab18268ab976c26` |
| hubrestartdelta.docx | 1105899 | `759dba5946ad0ae1475e4a8af5ceac94b12725c2a42d2dcbef1363a79ea669ac` |
| hubrestartgamma.docx | 1105899 | `6e39fbf98bca9dd6bc3621e1bfe2d0c8c26b15b7370865cc8ae16c52d70a6a77` |
| hubstate0emptysuccess1 | 789 | `0e3dd002958fe52185e737f92a7c4b84fa67282aa552324933157f52406386d7` |
| hubstate0emptysuccess2 | 789 | `7d39b9414cbe70ad8370d8afcb04009c9d4da24f5c5ff9886bcbecb274890c92` |
| hubstate0partial1 | 9866 | `bbcf234ed0ccecc7eb837261c0d898fb09c21495acbc50cbf9861da515736d41` |
| hubstate0partial2 | 10147 | `b9eb3ad14f84c3de7b8011d754cc725e07aef044d6e92aaca90324cb443568e4` |
| hubstate0replacement1 | 2601 | `061b6f48e2f5f985c4a515a0994f6f5933a3b02adc37e94ed46fa88a0d353811` |
| hubstate0replacement1New | 2600 | `572487d5521d13408bce192794105ce9054dcecb343085439fc5cd6675785eb9` |
| hubstate0replacement2 | 2600 | `90675b1bd051a3f45f663e1985e1186bfe49bb8ca3bb0bc745a9da29735842fa` |
| hubstate0replacement2New | 2599 | `a6b3979e28830aae88fa7a8dd270db8b1f58a8503daa7128e7c4831cf90ea707` |
| hubstate1emptysuccess1 | 790 | `ff92010d49b162fe4ab685d5d4490164074cbed96407c21bd1c19363c2cb884e` |
| hubstate1emptysuccess2 | 790 | `62b0954e43510580c147447d8d2d3a6b0ef6dfc9a6c2e015f2816e8228754638` |
| hubstate1partial1 | 9465 | `726a67c524b1bf4cfe324c6891a8f9da009be78a952bb1aa634dbfcfaa0d39ef` |
| hubstate1partial2 | 9811 | `8f0afe4b4a92cf247149a213f84317552204aab3329de5149af065fdd0d6ebc4` |
| hubstate1replacement1 | 2601 | `36703efffb79f563935258965eb20c31306d8966295aec0762d2d75d2dd377ba` |
| hubstate1replacement1New | 2601 | `fd6afbaee1929007c0f10b0389f60f5f20ef7fe7e1470bf3cfb672f0fa15fbf2` |
| hubstate1replacement2 | 2601 | `09b3a346e9cd8244f6382fce3c5a049ac06f5c8917817759797c295ee819fc87` |
| hubstate1replacement2New | 2600 | `bf97fa623c8beb14cbea64cc63344899e6d6f7c864dffa56950b00d3cb0924f9` |
| localrestartalpha.docx | 1105937 | `497e22872cdd2f455cd8d6857e12c93ab19724d6e9f1ef8a5b403e63031eb331` |
| localrestartbeta.docx | 1105918 | `3b4789597813ec5efccc65d0d469989d1191e9b3852a77d247d876203fd513a4` |
| localrestartdelta.docx | 1105937 | `1f7c2dfdcec1ab91233e8e45739905e5b509ab2c9bef83b260713c69e5760789` |
| localrestartgamma.docx | 1105937 | `8700c7d11a30e986411c283f08bfee0c4c5eb1963c4b1aab00f6f003c4c54a32` |
| localstate0emptysuccess1 | 790 | `f03e36eba5cce50f408a9e0b5f4f65c3f69b97901c4cfdd01b717fa35a7f271b` |
| localstate0emptysuccess2 | 790 | `ad283f7de0d987ec8af2603ed6472b5c2d82ab6207e2afe98998c8bdff96038b` |
| localstate0partial1 | 10114 | `0770c21686681cc7fd41c95d6d2cd7a564f05285b40058a67ff8439560f04ba3` |
| localstate0partial2 | 10350 | `3f87e3c6bedce1005d93858425adce50fbf775796a79fccb43327d3cfc6021bb` |
| localstate0replacement1 | 2605 | `dcce81be3cd000caff08032eb97eeb84b8081831d94de8e6462f4f11d92ca678` |
| localstate0replacement1New | 2604 | `e1d4c9a52979b97a79bca854829a3bafac03152cba303da3d3cfadac759c3af8` |
| localstate0replacement2 | 2605 | `20d334561dc4984f6d10a663ce05b05d48cd70a6b11d24a53ebbcbabf328b9a6` |
| localstate0replacement2New | 2604 | `df3c47d2d4ac1e0be562c53ba7478b6128e29a1b4cacc8d675cf6c254b68800e` |
| localstate1emptysuccess1 | 791 | `0daf248f31d83c33f0dc30f666f4193c7d6fe090a3c8e5368dbec575dcb67b72` |
| localstate1emptysuccess2 | 791 | `7c7932df4414f5be428c4db7a46b12940f2d301000548ed79f0caf95440f3af2` |
| localstate1partial1 | 9693 | `937e964e8ea9821555e33091a24e03eb1fb4894705a37512da2c61f96e249455` |
| localstate1partial2 | 10012 | `eb28b412b95f7c37e65006034d9fa5eac4dd5197a3f841eb616840b3c70073af` |
| localstate1replacement1 | 2604 | `9fbb2c5677d9f4f25cc0042c4566953d2caaddc7f4ccf7aadce8f91f4ec39244` |
| localstate1replacement1New | 2605 | `1698b74728109aae52e7561feea9fd2608137038c2d3058c081ede54e4883ce2` |
| localstate1replacement2 | 2606 | `0d9eb2b59326c7734b92e16235cacee484d952789bd30038dc6d2dd5b555babd` |
| localstate1replacement2New | 2605 | `5537ea21dea0e36a10cb57a2bb799fc3c015ab0d6a1c74c070b9aa3f82b24b39` |

## 结论边界

唯一分配项 managed-restart 已有本次实际执行证据，无本次产品失败、测试故障或未到达项。当前 passed 不关闭完整 SC7/R008、运行中 worker 终止/恢复、原生 launchd/systemd/SCM 服务、完整预算/恶意输入、HTTP TLS、真实浏览器或 E/H/X；截图不属于本 TC 判据。本轮中离线审查脚本曾因未排除 XML 空合并从单元的空 w:t 触发断言，按实际源结构过滤空文本后完整检查通过；该审查器错误未运行或改变业务，也未改正式日志。

意见 JSON 与本报告由执行 Reviewer 在新上下文独立生成；不自代主 Agent 登记 review。
