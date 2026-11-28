# AT-SMM-008 OCR 正文绿灯独立复审

结论：**passed**。仅 TC-008-pdf-ocr 的本次质量修复及指定回归，不认完整 SC5/C1/E/H/X。

## 源码及红绿版本

目标 result SHA `fbf82ba2949083440d19d4dc6968868a46bfeac955d83668cd48a3e8d55c0390`；75 绑定、90 证据均逐 SHA 通过。原 red 84 证据均通过。7 份测试字节和命令相同，共同产品绑定仅 ocr.py 改变。原 `4077d0d00a30299e6d2fdca3b138f4338539cf40b825a5c42f2faa02ff0f550e`，现 `76f69f3f604228a99e06e177be5171542c0399785a913ac4a6488553c22842fd`。

固定 180 改为 L 灰度图固定 256 桶的类间方差阈值。profile v3 与 coverage 实际阈值一致；无样本标签特判。保留渲染尺寸、PSM、次数、30 秒及任务预算、本地绝对路径。已有保存结果读取/重用路径未改，此项属于源码判断。并行观察器测试改动不计本产品修补。

## 原件、全文及关键字检查

独立使用冻结字体重绘，四原件逐字等于本轮 inputs/downloads 和原 red inputs；真值逐值一致。实际查看 Poppler 六页渲染图，源 73428 的 7 清晰，12345.67 正确，中英网格和全部金额对应。所有 PDF 无原生文字层。

| 文件 | 页 / 表 / 格 | 独立全文 CER | 实际阈值 |
|---|---|---|---|
| alpha | 2 / 2 / 12 | 0 | 144、143 |
| beta | 2 / 2 / 12 | 0 | 144、144 |
| LOCALSCANGAMMA | 1 / 0 / 0 | 0 | 138 |
| HUBSCANGAMMA | 1 / 0 / 0 | 0 | 138 |

四份完整内容、每页每格及正文位置与独立真值逐项核对。两正文关键编号/金额实际项目查询均准确命中自己 ID。原 red LOCAL 为 RETRY/3428，1/48=2.083333%；现同原件得到 RETRY 73428。原失败后的关键检索、无表、逐行位置、原件下载、最终 fingerprint 断言此次全部到达。四份正式源路径在独立复跑前实读 SHA/bytes/mtime 与 before 相符。LOCAL/HUB 仅材料标签，不是 Hub 身份证明。

## 质量执行与指定回归检查

正式质量 4 passed / 8.02s；正式回归 13 passed / 13.03s，无 skip。独立按同命令复跑质量 4 passed / 4.59s、回归 13 passed / 7.07s，无 skip。

回归包含两原生 PDF 零 OCR；两混合 PDF 仅需识别的页1/2真实 OCR，页3原生；两份首次无OCR配置失败的保存CID重试成功，错CID/过期V/P拒绝且控制文档保留。独立复跑保留两混合资料各5次真实OCR输入/TSV，逐SHA核输出且不重复原生页眉。

## 正负控制与清理检查

实际执行了真值金额突变拒绝、源读取守卫的允许/拒绝子进程、native 子进程禁止自检、mixed 未验证材料拒绝及真实已验证PDF允许。13份 cleanup 证明相同 PID/create_time worker 已退出；6业务档案无 active lease、无OCR临时图。正式两PID已退出，当前无document_worker/document_supervisor。证据见 assets 下 verification、controls-verification、cleanup-verification 及逐份副本。

## 依据与限制

依据 AGENTS、008意图/规格/计划、定义000003、同版设计匹配/runtime及已登记red_review。B3、A5、C1支持此质量判据。完整SC5故障/无网、完整C1三OS、E/H/X仍分开验收；本复审不作包构建、存量迁移矩阵、安装或服务身份结论。原件与所有原始结果未修改，历史失败保留。

全部源码、收据、正式及独立证据SHA清单见同名JSON；独立意见文件只含实际TC且covers为空。
