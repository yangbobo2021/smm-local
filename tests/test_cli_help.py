# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import sys

import pytest

from smm_local.cli import main
from smm_local.core import Archive


@pytest.mark.parametrize("existing_archive", [False, True], ids=["new-path", "existing-archive"])
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
            ["source", "batches", "--help"],
            (
                "source_id 插件来源 ID。用 smm source list 查找对应来源。",
                "默认显示最近 100 批",
                "按导入时间 (imported_at)、版本 (revision) 和消息数 (messages) 辨认批次，取记录的 id。",
                "--before 批次ID 填当前页最后一条记录的 id，查询更早的批次。返回 [] 表示已查到末尾。",
                "清理前的停用要求见 smm source purge-batch --help。",
            ),
            id="batches",
        ),
        pytest.param(
            ["source", "purge-batch", "--help"],
            (
                "source_id batch",
                "source_id 待清理批次所属的插件来源 ID。用 smm source list 查找对应来源。",
                "batch 要删除的导入批次 ID。用 smm source batches <来源ID> 查询同一来源，"
                "取目标批次记录的 id。默认只显示最近 100 批。用 --before 查询更早的批次，"
                "详见 smm source batches --help。",
                "从本机档案删除指定批次已导入的记录。清理批次前须先停用对应的插件来源。",
                "使用 smm source disable <来源ID> 停用该来源。",
            ),
            id="purge-batch",
        ),
    ],
)
def test_source_help(args, expected_text, existing_archive, monkeypatch, capsys, tmp_path):
    database = tmp_path / "archive.sqlite3"
    if existing_archive:
        Archive(database)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    monkeypatch.setattr(sys, "argv", ["smm", "--db", str(database), *args])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    output = capsys.readouterr()
    assert not output.err
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
    help_text = "".join(output.out.split())
    for expected in expected_text:
        assert "".join(expected.split()) in help_text
