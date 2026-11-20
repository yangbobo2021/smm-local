# SMM 0.4.0 发行前检查

日期：2026-11-20。功能基线为已合并 PR #21 的 `d74801d`。此次发行调整两个包的版本、`smm_local.__version__`、搜索 Skill 安装 pin、当前安装说明及发行检查材料；不改变其他产品 Python 文件及依赖约束。

- 全量回归：Python 3.14.2，**83 passed, 1 skipped**，见 [原始日志](pytest.txt)。跳过的是 Windows 专用项；三平台发行分支 CI 在 PR 检查中另记录，不以本机结果代替。
- `python3 scripts/build_packages.py` 成功，两个独立 wheel 均小于现有可信发布工作流的 90,000 字节传输上限。
- `build_release.py --skill` 和 `--adapter-skill` 成功，两个 ZIP 的目录/必需脚本及搜索 Skill 的 `smm-local==0.4.0` pin 均已核验。
- 两个 wheel 分别安装到全新 Python 3.14.2 环境，从 PyPI 正常解析依赖；Local 环境没有 Hub 包，Hub 环境没有 Local 包。实际公开帮助包含 `serve-hub --state-dir`、`hub vibeinsight configure`、`source batches --before` 和 MCP 入口。
- 本机包在隔离 HOME/显式临时档案中，经过真实 CLI 导入/检索/完整读取，再通过真实 stdio MCP 检索、600 字预览和按位置读取原文，全文与独立合成预期一致。见 [结果及命令退出码](smoke-result.json)。没有连接真实 Hub/VibeInsight 或读取本机私人档案。

可复跑的 [检查脚本](smoke.py) 从已安装 Local 的 Python 启动，另提供已安装 Hub 的 Python；解释器路径不 resolve 为基础 Python，以保持独立环境：

```sh
<local-env>/bin/python -I reports/release-0.4.0/smoke.py \
  --checkout <本仓库路径> \
  --hub-python <hub-env>/bin/python \
  --output <临时结果.json>
```

构建 wheel/两个 Skill ZIP 后运行。Windows 解释器使用 `Scripts/python.exe`；本脚本本轮仅在 macOS 实际执行，三平台 CI 和此前实际服务验收是不同层次的证据。PR #21 的平台结果保留 [原日期、提交和适用边界](../../changes/003-search-vibeinsight-conversations/evidence/platforms-2026-11-17/README.md)，本次版本元数据变化不冒充重新跑过系统服务。

初始 Python 3.12 环境的依赖准备未完成即停止，未计作测试结果；全量测试改用已有依赖的 Python 3.14.2，独立 wheel 环境随后正常下载依赖并安装。首版合成 MCP 检查漏写源 ordinal 却预期位置3，发生 StopIteration；补齐明确的源 ordinal 后重跑，未修改产品代码，成功结果来自修订后的实际脚本。

发布沿用现有 GitHub Actions → PyPI Trusted Publisher；本轮不向 TestPyPI 新增发行。GitHub Release 附带两个 Skill ZIP 和各自 SHA-256。正式发布后还需确认两个 PyPI 版本可下载、GitHub 资产摘要相符，并在本机升级后检查实际安装版本、登录服务、检索原文和旧记录保留。
