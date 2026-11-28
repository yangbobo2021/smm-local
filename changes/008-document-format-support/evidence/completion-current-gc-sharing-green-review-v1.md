# GC 元信息并发绿灯独立复审

结论：passed，仅适用于 AT-SMM-008 / SC8 / TC-008-gc-read-sharing 的 C1 共享组件，不代表完整 008。

## 同版与原件检查

基线 000003 / `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`。目标 `green-completion-sc8-gc-read-sharing-v1` result SHA256 `322fbcd1542c9eaf576f15821dde09898d10aa53548c069f588cd7e321bf5f27`。

红绿 163 项测试绑定、controller、命令一致；实际输入 226 文件及 Windows 执行前后哈希一致；64 产品绑定仅 document_snapshots.py 改变。runtime v3/v4 分别对应红绿，match v4 对应冻结测试，当前 bindings 一致。全部红 287/绿 293 artifact 重新核验。红/绿 output tar 分别 75167/75000 字节，transfer 摘要吻合；102/105 普通成员与 verified 逐字相同，2 个 current 符号链接只记录、未重建或跟随。

## 真实红绿检查

红 v2 三参数首次失败均为第 137 行真实 WinError5；旧代读取成功，后续断言当时未到达。正式绿灯 Windows Python3.14.10 管理员环境 4 passed / 12.95s，无 skip。三 reader 的 PID/ctime/argv/exe/目标 descriptor 在门内绑定真实启动器后代树，0.2 秒门自动释放，不改实际共享 flags。

实际绿灯继续至 138–143：新旧代不同，archives 1→2、owners 4→5、retired 各 1→2 CID/AID；独立重读持久 JSON 也匹配 packet 独立预期。全部旧成员与其他 JSON 保留，源 fingerprint 和无关文件字节/mtime 不变。独立预期由冻结磁盘旧集合、known archive/CID/AID/原 SHA 构造，不以两个产品读取相等排除错误。外部不合作句柄正控仍 WinError5，保留旧值并在关闭句柄后成功替换。

## 回归检查

保留原 stdout/stderr 与退出码：Mac 22 passed、2 Windows-only skipped / 46.67s。已读冻结测试中的共享最后用途与双顺序、真实 pin/owner exit/任务树清理、未知/复用/复制身份、拒绝删除计费、Local 私有/同步及 Hub 备份复制恢复全路径断言。skip 不计通过；该回归命令未持久化逐用例 observe 附件，结论限原 pytest 退出与冻结实际断言。

## 实现风险检查

metadata.lock 只围绕短 JSON 读或 atomic_json，不扩展 capacity 锁；写者仍由共目录 capacity 锁串行，metadata 内不再取 capacity/DB、不跑解析或网络、无重入；控制锁 finally 释放。兄弟档案共用同一根和锁。目录、JSON、锁文件拒绝链接/reparse。缺旧目录直接返回默认，不创建查询存储。prepare_restore 已排除整个 reclamation。无新增处理库，Hub 无处理依赖接收边界保持。

独立临时目录 5 项控制全部通过：缺目录无落盘；坏 JSON 异常后可立即写读；兄弟档案共享锁根；锁符号链接拒绝；JSON/目录符号链接拒绝。未改产品、测试或历史，未操作日常服务。

## 范围与待办

本轮没有阻塞问题。Windows 普通身份 E/H、真实 Web 更新、最终三 OS CI、完整 008 仍待各自证据；不改变旧 red-v1 的测试故障结论。
