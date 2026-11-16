# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import sys

import pytest

from smm_local.cli import main


@pytest.mark.parametrize(
    ("args", "expected_text"),
    [
        pytest.param(
            ["source", "--help"],
            (
                "list 列出本机对话来源及其状态",
                "validate 验收候选来源适配器",
                "register 验收并注册来源适配器",
                "enable 启用指定来源的导入",
                "disable 停用指定来源的导入，保留已导入的记录",
                "rollback 将指定插件来源的适配器切回上一版",
                "batches 查看指定插件来源的导入批次",
                "purge-batch 从本机档案删除指定批次已导入的记录。"
                "清理批次前须先停用对应的插件来源",
            ),
            id="source",
        ),
        pytest.param(
            ["source", "purge-batch", "--help"],
            ("source_id batch", "清理批次前须先停用对应的插件来源"),
            id="purge-batch",
        ),
    ],
)
def test_source_help(args, expected_text, monkeypatch, capsys, tmp_path):
    database = tmp_path / "archive.sqlite3"
    monkeypatch.setattr(sys, "argv", ["smm", "--db", str(database), *args])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    output = capsys.readouterr()
    assert not output.err
    assert not database.exists()
    help_text = "".join(output.out.split())
    for expected in expected_text:
        assert "".join(expected.split()) in help_text
