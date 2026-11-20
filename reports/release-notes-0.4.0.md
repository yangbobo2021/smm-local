# SMM 0.4.0

## VibeInsight 对话与关联检索

- Hub 自动同步 VibeInsight 中当前只读账户可读取的全部项目。凭据与每项目进度持久保存，服务重启后继续同步新会话和旧会话追加的轮次。
- Hub CLI 统一维护设备项目和 VibeInsight 项目之间的双向关联。在线 CLI/MCP 项目检索包含当前项目与直接关联的一层，并可沿命中引用读取原文；Hub 不可用时返回本机全局范围及原因。
- 自行管理的 Hub 可用 `serve-hub --state-dir` 读取同目录配置，自动同步；配置目录与数据库冲突时会在写入前拒绝启动。
- 本机 `source batches` 支持翻页查找较早的导入批次，`source` 各层帮助补齐参数含义和使用方式。

## 安装和升级

- 新安装：下载 `smm-search-0.4.0.zip`，按 [快速开始](https://github.com/yangbobo2021/smm-local/blob/v0.4.0/README.md#单台电脑快速开始)安装；首次使用从 PyPI 安装本机端。
- 已有本机端：更新整个搜索 Skill，按 [本机端升级步骤](https://github.com/yangbobo2021/smm-local/blob/v0.4.0/TRIAL_GUIDE.md#升级本机端)升级到 `smm-local==0.4.0`，保留原档案。升级后新开 Agent 会话加载新版 MCP。
- Hub：`smm-hub hub upgrade --version 0.4.0`。配置 VibeInsight 的连接信息、只读表权限、psql 和项目关联，见 [使用指南](https://github.com/yangbobo2021/smm-local/blob/v0.4.0/TRIAL_GUIDE.md#从-vibeinsight-同步对话)。管理员应在实际服务身份下检查最近成功时间，并用检索和原文读取确认结果。
- 来源适配 Skill：下载 `smm-source-adapter-0.4.0.zip`；适配器协议保持兼容。
- PyPI：[smm-local 0.4.0](https://pypi.org/project/smm-local/0.4.0/) · [smm-hub 0.4.0](https://pypi.org/project/smm-hub/0.4.0/)。

## 验收及边界

VibeInsight 功能已在 macOS 15.3.1 系统级 launchd、Ubuntu 22.04.5 systemd 用户服务和 Windows 11 LocalService，以及三平台 CLI/stdio MCP 上取得实际证据。15 项正式执行与独立执行复审通过，完整规格和自行管理 Hub 的独立交付判定均通过，详见 [PR #21](https://github.com/yangbobo2021/smm-local/pull/21) 及 [2026-11-17 验收索引](https://github.com/yangbobo2021/smm-local/blob/v0.4.0/changes/003-search-vibeinsight-conversations/evidence/platforms-2026-11-17/README.md)。Linux 凭据保护采用权限/完整 ACL 的 DAC 推论，没有另一 UID 实读；macOS、Windows 有另一身份读取被拒的实测。

本次发行仅更新版本元数据、版本常量、Skill 安装版本、发行说明及发行检查脚本；沿用上述已合并的功能实现和依赖。实机证据保留原日期、提交和环境，不表述为本次发行重新执行了全部服务验收。发行前另运行回归、包构建及独立安装验证。

同步回看以各项目已提交位置向前 24 小时为下界，窗口外迟到事件不保证发现；历史消息原地改写且无新事件时不覆盖旧档案。显示名变化保留项目身份和关联；仓库主机、端口或路径变化按新项目处理，需重新关联。本轮没有重新连接真实 VibeInsight staging，也没有向真实服务器造数。

[本次发行前检查](https://github.com/yangbobo2021/smm-local/blob/v0.4.0/reports/release-0.4.0/README.md)记录回归、包构建和独立 CLI/MCP 原文验证。
