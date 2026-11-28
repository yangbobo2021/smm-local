# AT-SMM-008 installed protocols v3 独立候选复审

结论：`passed`，仅限本轮 **Mac普通UID、独立安装、32份ready资料、无待办正常重启的协议读取/上传子域**。F1–F7在此范围内已可复用，可继续下一E验收子域。没有未解决的本轮阻塞意见；不是完整E1-mac、H/X或R008通过，也不替代另一位正式执行Reviewer或需求级判定。v1/v2意见、旧失败和旧源快照保留。

## 判据与合法schema边界

沿用已读取的AGENTS、008 intent/spec/plan和交付验收技能Reviewer规则；本轮再次核SPEC B2、B8、A2/A9和C1原文。B2要求Word源部件、段落/表格/单元格序号，没有要求每个table cell自身必须带字符start/end。因此v3允许Word cell缺省无span是正确边界，不能因其cell path与普通全文paragraph path层级不同而判产品失败。若实际提供span，必须对应同一段已校验文字，不能给出错误区间。

## F4 精确位置修订

已解决v2具体漏项。table_positions现以独立part_positions中对应文字的anchor确定part，并去掉末尾paragraph层得到**精确源cell path**，不再只startswith到该行。FormatProbe.table随后按已校验snapshot中的文字及page/part/coordinate等寻找唯一loc；已提供的start/end必须与其一致，其余已提供的位置元数据也逐项对应。DOCX排除path直接相等的原因是合法cell/paragraph层级不同，而精确cell路径已经由独立源anchor核过；PDF/XLSX位置继续保留本来存在的span及源框/坐标桥接。

针对v2反例逐实际断言推演：同排第二格借第一格location先在独立精确cell path拒绝；正确path但table-only start=0/错误end，先在提供span与唯一全文loc的比较处拒绝；所有第二页定位变page1会在逐页正文/格文字loc查找拒绝；整页框冒充精确格框会在独立bbox检查拒绝。完整origin仍由expected_origin独立检查，不因两个端共同同错而过。第二文档误用第一文档会先在id/SHA拒绝，漏/重复表或格仍由完整真值集合、计数及唯一性拒绝。

## 316个原响应控制的独立复核

实际阅读verify_protocol_positions_v4.py及原stdout/stderr/report。它使用debug15实际commands及冻结真值，恢复JSON读回的tuple形态，再对32份完整text和72份完整FormatProbe.table正控运行；316负控包括三origin字段、第二页/框/offset、Word部件、XLSX坐标、每表table-only区间及同排第二格借第一格location。代码与控制报告的主候选/positions SHA与debug16相同。

我另以**debug16 source-snapshot代码和测试helper**独立重放该控制脚本，仅移除最终报告写盘语句以免覆盖原件。实际得到32 text、72完整table正控、316负控全部符合预期；没有运行产品或浏览器、修改样本或旧结果。v2控制失败是误将cell path强制等于paragraph path，v3控制失败是JSON list转原tuple问题，原stderr均保留；最终v4正控先通过，避免“错误oracle拒一切”伪成功。

## 新运行源码与独立wheel检查

采用debug16/attachments/source-snapshot，285份保存源字节与execution-source-bindings逐项一致，当前三核心文件仍相同。main在写passed前assert结束时version_bindings全集等于开始全集；这是实际成功执行的断言，不冒称另有结束manifest。配置SHA `0df77a31daa0d9a4c09b842fe216c575418002428ac33ede9a11b4e4319409b7`对应protocols-mac-guard-config-v2-ocr.json。JSON意见保存全部源和已核证据SHA。

本轮换用minimum-mac-prep-v2-ocr的新独立3.11轮子。Local47、Hub50个产品资产按实际wheel、任务私有安装、source-snapshot共享模块映射/shim逐字核对，97项全一致；两wheel ZIP CRC正常。Local SHA `45c67d2be003583d7d44a928f8824caeb026854d54af35c1dff0e68de5e11d26`，Hub SHA `d05836b5b23abc7361ba4112a5595a06dbb9c9a94e6001cd8b88f394d8da0d3b`；两端OCR成员都等于新源 `76f69f3f604228a99e06e177be5171542c0399785a913ac4a6488553c22842fd`。本报告只核新OCR包字节及当前pilot业务，不替代独立质量修复TC的红绿/复审，也不改判debug8旧失败。

## 真实入口、MCP批量与旧ref检查

debug16实际passed32身份，32身份对应30种不同原字节；路径/chooser/drop、普通/全局、独立全文/所有表及原件真值仍沿用前版。1703条commands，128个实际原件流；Local CLI Hub根逐16目标、MCP原件信息和同ref交Local CLI/API下载、Hub CLI/认证HTTP及两端Web各路径均实际重跑。

MCP现在是6个真实stdio连接，不是6个工具调用。两阶段各3连接：32 search、32完整text、104 details（72 table+32 original-info），总336工具调用，即64 search、64 text、144 table、64 original-info。源码对各批结果数量及tags/请求全集相等作显式断言，details按tag还原目标，每目标完整表集合/唯一ID/独立内容和位置仍逐一核对；未因批量减少请求或断言。6个实际server进程均exit0、alive=false。

MCP保留旧mcp_hit且重搜ref先比较，Local CLI/Hub根CLI也用各自旧ref；Web保存角色各自web_hit并比较ref。正常停止两端、删除全部外部及managed源路径后，前后全部text/table/info/原件再次核对。不是在途任务或故障恢复证据。

## 身份、只读守卫与清理

业务入口guard记录Local788个、Hub517个包含实际smm模块的解释器身份：UID501、isolated=1、PATH=/usr/bin:/bin，cwd均为任务non-source-cwd。内容worker自身监督cwd/解释器属性单列，不声称所有子进程-I。

protected-source-paths登记32项，包括网页managed路径。每owner真实external与managed源各做允许/拒绝控制；允许缓存与process/child拒绝仍执行，stdout/stderr原件保留。两段只读观察645/647事件只有identity及3个精确stdio transport-start，无源open/content-processing/非transport child-start。调用监测只对所列入口和Python审计事件认领，未扩成任意原生代码/所有通信的完备安全证明。

cleanup保存4次两端服务真实终止、PID不存活及当前端口关闭；MCP退出另逐6进程核对。此处不是H5服务注册/防火墙清理证明。

## 浏览器原件检查

6个trace均实际打开ZIP并解析原.trace，CRC正确，无after error：前/后读取各Local2032动作、Hub1020动作；上传Local314、Hub240动作。Local Web每阶段实际32唯一目标、16次Hub根请求；Hub Web每阶段16目标。web-a汇总ids仍只列Local16项，属于可改进的汇总范围文案，真实事件/trace证实远端16份已执行，不据这个汇总单独推断覆盖。

实际查看本轮重启后Local→Hub全局扫描PDF截图，能见Hub只读项目、双页BETA中英及关键金额、Hub自有origin和完整reader正文；查看Hub chooser截图，四份资料均ready/版本1/处理版本1且列表身份一致。截图在table动作前，表格覆盖依赖后续真实trace/响应/DOM及原件断言，不能用空表截图冒称所有格已经显示。

## 可继续的范围与仍未完成的完整E义务

本候选可复用并继续下一子域。ready/V=P1、无待办普通重启是本次已覆盖的动作前状态；只有首目标正确、第二页/第二表漏失、两边共同错文档/位置的相关反例已有独立全集与负控。没有据此认领首次/替换失败retry、partial/empty、更新/暂停/撤回/晚到、在途重启、深表243行/第10列后默认窗/表头、同项目第二Local身份与完整同步/关联范围、隐藏/公式/日期/混合PDF等完整格式细分、资源权限/其他平台E、所有H1–H5和X六方向。

debug8原73428→/3428/CER2.0833%的失败原件与v1/v2报告保留；另一个质量TC是否关闭它应由该TC证据决定，本pilot不代判。这里不制造新的自然语言设计/native执行收据或R008完整passed。未修改核心候选/产品/测试，除本轮意见两个文件外未改原件；仅做只读核查和轻量oracle回放。
