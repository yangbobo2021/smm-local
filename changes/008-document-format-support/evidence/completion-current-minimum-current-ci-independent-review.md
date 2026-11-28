# Python 3.11 当前三平台 CI 独立执行复审

AT-SMM-008；候选 `e23384869f37c83c7b687e279b311f841b3bca29`；真实 CI run `46101806180`。结论：**passed**。

A11 / TC-008-packages minimum Python3.11 installed CLI business subset. No complete R008, E1, H or X pass.

已读 AGENTS、确认意图/规格/计划及交付验收 Skill 的 Reviewer 规则。独立检查仅在本报告目录写入；未执行产品、未修改产品/测试/历史、未读取或复制私钥。

## 计数与覆盖

Per platform: 208 source text units, 32 source tables, 152 source table cells; 32 full text reads, 64 table reads, 304 cell comparisons across before/after, and 32 byte-exact original downloads. The historical phrase 304 source units conflated source units with table-cell comparisons.

逐端各 8 文档：普通/全局项目各一份 DOCX、XLSX、两页原生 PDF、一页扫描 PDF。DOCX 3 表含嵌套/合并，XLSX 2 sheet/2 表，原生 PDF 2 页/3 表，扫描 PDF 为英文无表单页。逐文档核全部文字及排除文字、原生规定顺序、全部表格单元与跨度/位置、原件字节，源文件移除后使用同一原始引用再次核对完整 text/table/info/原件，前后完整响应相等；与无关/另一类型项目的负控不混入。

## Linux：passed（最低安装子域）

JUnit 7 过，0 failure/error/skip，耗时 25.158 秒；246 条真实业务 CLI；7 准备命令 + 18 包门命令，原始 stdout/stderr 摘要逐项相符。另读 5 条 OCR 材料安装/离线程序/语言命令的真实原件，全部 exit0。实际处理 profile 为 Tesseract 5.5.4、chi_sim+eng、grid3-body11-otsu-connected-v3，逐项核实际语言数据摘要与材料记录。
实际产品均 Python 3.11.18，Local/Hub 分离环境，`-I -X utf8`、非源码 cwd；身份探针逐文件比较安装文件与 wheel，当前 commit 的源码→wheel→安装共 47 Local + 50 Hub = 97 产品文件，另含两份 METADATA；Hub 不能 import Local。错误 wheel SHA 与源码导入负控实际拒绝。
实际身份：`{"pid": 2669, "platform": "linux", "os": "Linux-7.0.0-1018-aws-x86_64-with-glibc2.39", "uid": 1001}`；两端产品实际身份一致。
已重算并读取 573 个清单原件，官方 ZIP 长度 2142090 字节、ID 15245741282。
官方 ZIP SHA256：`f121a62f1a97c9081d45eee79b119f7748dfefb91d8f538a5ff849b994b92020`。
恢复 manifest SHA256：`058536f0fdf83c6177bdb68a077b9bea0426af9b4c6ac70c09b17c7f437bd1b5`；外部 recovery 报告 SHA256：`db0fc377eb8d0341f21c8625490445a4a4cd24f6586143594e4fc54bcf55f224`。
Local wheel SHA256：`8cc546d4674653a43057731bb7c0acc0ef13da656558d741b85f8920940fd6d7`；Hub wheel SHA256：`e8ab6209517fac74bd789ab73b5ad3e8e24cd76052f1f8b6238d5d9bb1c7e795`。
JUnit SHA256：`9fd18dcec18ebf66b57ccdf70ba3f3b99bb58e1b05430f3ac350d0c48a1ee330`；业务 result SHA256：`6e68c1c7e7e396caaa5f850735d7e7de0603f51104c0039d91ae235a58581b9a`。
扫描原件全部实际渲染查看：`Linux-scan-originals.png`；四份均清楚可见 73428 和 12345.67，与实际 OCR 全文一致。
清理：全部 CLI 为同步子进程并实际返回；真实临时目录中外部源文件均已移除，任务档案及证据保留。没有独立最终进程树/端口清扫回执，不认 E1/H5 清理。

## Windows：passed（最低安装子域）

JUnit 7 过，0 failure/error/skip，耗时 48.061 秒；246 条真实业务 CLI；7 准备命令 + 18 包门命令，原始 stdout/stderr 摘要逐项相符。另读 5 条 OCR 材料安装/离线程序/语言命令的真实原件，全部 exit0。实际处理 profile 为 Tesseract 5.5.4、chi_sim+eng、grid3-body11-otsu-connected-v3，逐项核实际语言数据摘要与材料记录。
实际产品均 Python 3.11.9，Local/Hub 分离环境，`-I -X utf8`、非源码 cwd；身份探针逐文件比较安装文件与 wheel，当前 commit 的源码→wheel→安装共 47 Local + 50 Hub = 97 产品文件，另含两份 METADATA；Hub 不能 import Local。错误 wheel SHA 与源码导入负控实际拒绝。 Windows wheel 的源码成员相对 git blob 为精确 LF→CRLF 转换（逐成员清单在 JSON），生成 shim 为 LF；wheel→实际安装摘要始终逐字相同，不声称 Windows wheel 与 LF git blob 原字节相同。
实际身份：`{"pid": 5072, "platform": "win32", "os": "Windows-10-10.0.20348-SP0", "is_admin": false}`；两端产品实际身份一致。
已重算并读取 574 个清单原件，官方 ZIP 长度 2015632 字节、ID 15245622018。
官方 ZIP SHA256：`fbf55002d48bc4588277e5aa369933a14fc0defc48c300714c610b0109ce09d7`。
恢复 manifest SHA256：`87c914f23708ba920b6c18bf8dd15cbd88dc1ee0c77fcbcb73348b003df6636b`；外部 recovery 报告 SHA256：`2d907c93a17eec440d677db23f6be9291047c7c3a0cd12d4418567a22843c950`。
Local wheel SHA256：`23e485fbb1c33b0b521c0b71cdbec6734e8725da1da2b849946821b7f093f10b`；Hub wheel SHA256：`174be0758676d783c13d349acdbef58e6580e660f22767abaf5686309756d9c1`。
JUnit SHA256：`ade07798295a4d990720a7b355d1cc1089bee73a7116339d1a7bf8865158bd47`；业务 result SHA256：`426212788d877b97b564c1367c8f6386839aea1ed20e85b2bb6ebfcfbab8a3d3`。
扫描原件全部实际渲染查看：`Windows-scan-originals.png`；四份均清楚可见 73428 和 12345.67，与实际 OCR 全文一致。
清理：Windows 原始 standard-user-controller.json 明确 unexpected_remaining_pids=[]、account_absent=true、Secondary Logon=Stopped；实际标准账户 SID 无 Administrators 组。任务档案及证据有意保留。

## macOS：passed（最低安装子域）

JUnit 7 过，0 failure/error/skip，耗时 40.012 秒；246 条真实业务 CLI；7 准备命令 + 18 包门命令，原始 stdout/stderr 摘要逐项相符。另读 5 条 OCR 材料安装/离线程序/语言命令的真实原件，全部 exit0。实际处理 profile 为 Tesseract 5.5.4、chi_sim+eng、grid3-body11-otsu-connected-v3，逐项核实际语言数据摘要与材料记录。
实际产品均 Python 3.11.9，Local/Hub 分离环境，`-I -X utf8`、非源码 cwd；身份探针逐文件比较安装文件与 wheel，当前 commit 的源码→wheel→安装共 47 Local + 50 Hub = 97 产品文件，另含两份 METADATA；Hub 不能 import Local。错误 wheel SHA 与源码导入负控实际拒绝。
实际身份：`{"pid": 2340, "platform": "darwin", "os": "macOS-15.8.2-arm64-arm-64bit", "uid": 501}`；两端产品实际身份一致。
已重算并读取 573 个清单原件，官方 ZIP 长度 2132693 字节、ID 15245473438。
官方 ZIP SHA256：`771d60e87bc68284005fbe79b2dd2b50415819745690de14ab9200fd0cb8cb1b`。
恢复 manifest SHA256：`e1256c04752f4f82e7730480f577eaeeb01020a0eb2c5719f39a3984dfc74a84`；外部 recovery 报告 SHA256：`65ac31bd4bad3bafb82e1d45fa291833d288e8c15d8cdcf253ad8a0c0d25b062`。
Local wheel SHA256：`60015c7d06803f04848bb12f8879d337a4adfef2fbd0b3553f8266cbaeae851f`；Hub wheel SHA256：`ad8a8aa980895b3a948f8d971c558e876203e7d124b430539c6775f0de918396`。
JUnit SHA256：`fe1154aede80c3982815b5e7c9caa56cb3c06b477659327e29e23690cf16e0c6`；业务 result SHA256：`2e107aece5a15a414747a599c0030b5b952e0e25985161d00513cff9f6d87320`。
扫描原件全部实际渲染查看：`macOS-scan-originals.png`；四份均清楚可见 73428 和 12345.67，与实际 OCR 全文一致。
清理：全部 CLI 为同步子进程并实际返回；真实临时目录中外部源文件均已移除，任务档案及证据保留。没有独立最终进程树/端口清扫回执，不认 E1/H5 清理。

## 限制

- Actual foreground process completion and absent external source inputs support this minimum subset. POSIX has no separate final tree/port sweep and no cleanup.json; do not re-label as E1 cleanup or H5 service cleanup.
- Windows actual temporary standard identity has no Administrators group and its controller receipt proves empty remaining-owned-process list, account removal, and Secondary Logon restored to Stopped.
- All task-owned state/evidence intentionally retained; no global filesystem cleanup claimed.
- Previously completed authenticated decryption was not repeated. Local official ZIP SHA/length, encrypted public header, recovered manifest and every member are independently rechecked; key private.pem was neither opened nor copied.
- No earlier CI 681 proof was substituted. Current actual outputs alone support current conclusions.

最低安装证明不包含完整 Web/业务 MCP、两本机同步、六方向无依赖接收、受管服务、重启恢复、完整中英 OCR/CER/扫描网格、全部预算和敌意输入。三平台安装补证可单独认 passed；R008 与完整 E/H/X 仍必须另判。

机器可读逐文档、逐原件、身份和报告摘要：`minimum-current-ci-independent-review.json`。
