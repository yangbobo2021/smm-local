# VibeInsight 的可选验收探针

日常回归运行 `pytest`，来源由合成事件夹具控制，无需 PostgreSQL 或 staging 凭据。
设置 `ACCEPTANCE_EVIDENCE_DIR` 可导出选定场景的实际响应；不设置时不产生报告：

```sh
PYTHONPATH=src ACCEPTANCE_EVIDENCE_DIR=/tmp/smm-evidence/pytest python -m pytest -q
```

以下探针验证已安装的独立发行包、真实 SQL 和升级兼容，按需运行，不是默认 CI 的前置依赖。
从仓库根目录运行，需要 Python 3.11+、`uv`、`openssl`，以及本机 PostgreSQL 的
`initdb`、`pg_ctl`、`psql`。PostgreSQL 探针在独立临时目录初始化数据库，仅监听该目录的
Unix socket；造数仅发生于此临时数据库。两个探针都只启动本机 Hub，不接受远端数据库参数。

```sh
python3 scripts/build_packages.py
uv venv /tmp/smm-hub-acceptance
uv venv /tmp/smm-local-acceptance
uv pip install --python /tmp/smm-hub-acceptance/bin/python dist/packages/smm_hub-*.whl
uv pip install --python /tmp/smm-local-acceptance/bin/python dist/packages/smm_local-*.whl
python3 scripts/acceptance/vibeinsight_postgres.py \
  --hub-env /tmp/smm-hub-acceptance --local-env /tmp/smm-local-acceptance \
  --output /tmp/smm-evidence/postgres.json
python3 scripts/acceptance/vibeinsight_upgrade.py \
  --hub-env /tmp/smm-hub-acceptance --local-env /tmp/smm-local-acceptance \
  --output /tmp/smm-evidence/upgrade.json
```

旧客户端和旧数据库由仓库中的 `d2dee18fcc050dcf20bd4108429975477399db8d` 源码生成，
需本地 Git 含该提交。导出时将调用方的当前会话标识替换为 `<current-session>`，
pytest 另将夹具临时路径替换为 `<fixture>`。脚本先核对已安装模块与当前源码的 SHA-256，不一致时拒绝执行。
只有所有断言通过才写出 `status: passed` 的 JSON；非零退出时检查终端异常，不能用旧文件
宣称此次通过。报告记录执行时间、HEAD、源文件及 wheel 哈希和实际响应。临时服务、档案和
数据库在退出时清理。脚本中的口令、Token、事件和项目均为隔离夹具，不使用用户凭据。

探针目前面向 macOS/Linux；Windows 文件 ACL 不在这组探针覆盖范围。
本次执行结果及七项验收映射见[验收证据索引](../../changes/003-search-vibeinsight-conversations/evidence/README.md)。
