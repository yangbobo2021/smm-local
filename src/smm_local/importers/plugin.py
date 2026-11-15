# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Protocol and executor for trusted, locally generated Python source adapters."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from . import plugin_scope, zcode_fixture

API_VERSION = 1
MAX_SCRIPT = 256 * 1024
MAX_OUTPUT = 4 * 1024 * 1024
MAX_MESSAGES = 500
MAX_TIMEOUT = 8
MAX_CURSOR = 16 * 1024
MESSAGE_FIELDS = {"session_id", "message_id", "position", "role", "text", "origin",
                  "timestamp", "cwd"}
SOURCE_ID = re.compile(r"[a-z][a-z0-9-]{0,62}")
BOOTSTRAP = """
import os, runpy, sys
if os.name == 'posix':
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (8, 9))
    if sys.platform != 'darwin':
        resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))
runpy.run_path(sys.argv[1], run_name='__main__')
"""


def read_limited(path: Path, max_size: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(max_size + 1)
    if len(data) > max_size:
        raise ValueError(f"文件超过 {max_size} 字节")
    return data


def _text(value, size: int, *, optional: bool = False) -> bool:
    if optional and value is None:
        return True
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    return len(value.encode("utf-8", errors="surrogatepass")) <= size and not any(
        0xD800 <= ord(char) <= 0xDFFF for char in value
    )


def validate_message(message: dict) -> dict:
    if not isinstance(message, dict) or set(message) - MESSAGE_FIELDS:
        raise ValueError("插件返回了无效消息字段")
    for field, size in (("session_id", 1024), ("message_id", 1024), ("text", 1024 * 1024),
                        ("origin", 4096)):
        if not _text(message.get(field), size):
            raise ValueError(f"插件消息缺少或包含无效的 {field}")
    if not Path(message["origin"]).parts or Path(message["origin"]).is_absolute() or any(
        part == ".." for part in re.split(r"[/\\]", message["origin"])
    ) or re.match(r"^[A-Za-z]:|^[/\\]", message["origin"]):
        raise ValueError("插件消息的 origin 必须是来源内相对路径")
    if message.get("role") not in ("user", "assistant") or not message["text"].strip():
        raise ValueError("插件返回了无效消息角色或空白正文")
    position = message.get("position")
    if type(position) is not int or not 0 <= position <= 2**63 - 1:
        raise ValueError("插件返回了无效消息位置")
    if not _text(message.get("timestamp"), 128, optional=True) or not _text(
        message.get("cwd"), 4096, optional=True
    ):
        raise ValueError("插件返回了无效时间或工作目录")
    if timestamp := message.get("timestamp"):
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("插件消息时间必须是 ISO 8601") from exc
    if message.get("cwd") and not Path(message["cwd"]).is_absolute():
        raise ValueError("插件返回的工作目录必须是本机绝对路径")
    return {**message, "timestamp": message.get("timestamp"), "cwd": message.get("cwd")}


def origin_path(root: Path, relative: str) -> Path:
    if not root.exists():
        raise ValueError("来源路径不存在")
    if root.is_dir():
        origin = (root / relative).resolve()
        if origin.is_relative_to(root):
            return origin
    else:
        origin = (root.parent / relative).resolve()
        if origin == root:
            return origin
    raise ValueError("插件报告的来源位置超出已注册范围")


def _run_file(path: Path, request: dict, timeout: float) -> bytes:
    # Isolated Python removes user site and PYTHON* injection. The OS account
    # still determines what this trusted script may access.
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "SYSTEMDRIVE"}}
    process = subprocess.Popen([sys.executable, "-I", "-S", "-B", "-X", "utf8", "-c", BOOTSTRAP, str(path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, cwd=path.parent, env=env,
                               start_new_session=os.name == "posix")
    payload = json.dumps(request).encode("utf-8")
    output = bytearray()
    closed = threading.Event()
    overflow = threading.Event()

    def send():
        try:
            with process.stdin as stream:
                stream.write(payload)
        except OSError:
            pass

    def receive():
        try:
            with process.stdout as stream:
                while chunk := stream.read1(min(65536, MAX_OUTPUT + 1 - len(output))):
                    output.extend(chunk)
                    if len(output) > MAX_OUTPUT:
                        overflow.set()
                        break
        finally:
            closed.set()

    threading.Thread(target=send, daemon=True).start()
    threading.Thread(target=receive, daemon=True).start()
    deadline = time.monotonic() + timeout
    try:
        while True:
            if overflow.is_set():
                raise ValueError("插件输出超过上限")
            code = process.poll()
            if code is not None and closed.is_set():
                if code:
                    raise ValueError(f"插件异常退出（退出码 {code}）")
                return bytes(output)
            if time.monotonic() >= deadline:
                raise ValueError("插件执行超时")
            time.sleep(0.015)
    finally:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                if process.poll() is None:
                    process.kill()
        elif process.poll() is None:
            process.kill()
        process.wait(timeout=2)


def execute(code: bytes, root: Path, cursor: str | None, scope=None, *, timeout: float = MAX_TIMEOUT) -> dict:
    if not root.exists():
        raise ValueError("来源路径不存在")
    request = {"version": API_VERSION, "root": str(root), "cursor": cursor, "limit": MAX_MESSAGES}
    if scope is not None:
        request["scope"] = scope
    with tempfile.TemporaryDirectory(prefix="smm-source-") as workspace:
        script = Path(workspace) / "adapter.py"
        script.write_bytes(code)
        output = _run_file(script, request, timeout)
    try:
        result = json.loads(output.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise ValueError("插件没有返回有效 UTF-8 JSON") from exc
    if (not isinstance(result, dict) or set(result) != {"messages", "cursor", "more"}
            or type(result["more"]) is not bool or not isinstance(result["messages"], list)
            or len(result["messages"]) > MAX_MESSAGES
            or not _text(result["cursor"], MAX_CURSOR, optional=True)):
        raise ValueError("插件返回了无效批次、读取进度或消息数量")
    if (result["more"] or result["messages"]) and result["cursor"] == cursor:
        raise ValueError("插件读取进度没有前进")
    result["messages"] = [validate_message(message) for message in result["messages"]]
    for relative in {m["origin"] for m in result["messages"]}:
        origin_path(root, relative)
    keys = {(m["session_id"], m["message_id"]) for m in result["messages"]}
    if len(keys) != len(result["messages"]):
        raise ValueError("插件批次内包含重复消息身份")
    plugin_scope.check(scope, root, result["messages"])
    return result


def descriptor(path: Path, *, live_root: bool = True) -> tuple[dict, bytes]:
    path = path.resolve(strict=True)
    config = json.loads(read_limited(path, MAX_SCRIPT).decode("utf-8"))
    if (not isinstance(config, dict) or set(config) != {"version", "id", "name", "root", "script"}
            or type(config["version"]) is not int or config["version"] != API_VERSION
            or not isinstance(config["id"], str) or not SOURCE_ID.fullmatch(config["id"])
            or config["id"] in {"all", "codex", "claude-code"}
            or not _text(config["name"], 240) or not _text(config["script"], 4096)
            or not _text(config["root"], 4096)):
        raise ValueError("无效来源清单，需要 version、id、name、root、script")
    root = (path.parent / Path(config["root"]).expanduser()).resolve(strict=live_root)
    script = (path.parent / config["script"]).resolve(strict=True)
    if script.suffix != ".py" or not script.is_file():
        raise ValueError("来源插件必须是一个 Python 脚本")
    code = read_limited(script, MAX_SCRIPT)
    return {**config, "root": str(root), "script": script.name,
            "digest": hashlib.sha256(code).hexdigest()}, code


def _collect(code: bytes, root: Path, cursor=None, *, scope=None,
             rerun: bool = False) -> tuple[list, str | None]:
    messages = []
    seen = set()
    for _ in range(8):
        batch = execute(code, root, cursor, scope)
        for message in batch["messages"]:
            key = (message["session_id"], message["message_id"])
            if key in seen:
                raise ValueError("验收期间出现重复消息身份")
            seen.add(key)
            messages.append(message)
        if rerun and batch["messages"]:
            raise ValueError("用已完成进度重复读取仍返回了消息")
        cursor = batch["cursor"]
        if not batch["more"]:
            return messages, cursor
    raise ValueError("验收样本过大或进度未到达末尾")


@contextmanager
def _validation_stage(stage: str, root: Path):
    try:
        yield
    except (OSError, ValueError, RuntimeError) as exc:
        try:
            kind = "文件" if root.is_file() else "目录" if root.is_dir() else "不存在或不是普通文件/目录"
        except OSError:
            kind = "无法识别类型"
        raise ValueError(f"验收失败：{stage}，root=「{root}」（{kind}）：{exc}") from exc


def _check_fixed_zcode(code: bytes) -> int:
    with tempfile.TemporaryDirectory(prefix="smm-zcode-fixture-") as workspace:
        roots, expected = zcode_fixture.create(Path(workspace).resolve())
        scope = zcode_fixture.SCOPE
        fields = ("session_id", "message_id", "position", "role", "text", "origin")
        cursor = None
        for stage, description in (
            ("before", "固定样本首次读取"),
            ("pending", "固定样本系统事件与空回复"),
            ("after", "固定样本原行完成后的续读"),
        ):
            root = roots[stage]
            with _validation_stage(f"zcode-{stage}（{description}）", root):
                messages, cursor = _collect(code, root, cursor, scope=scope)
                if [{field: m[field] for field in fields} for m in messages] != expected[stage]:
                    raise ValueError(f"{description}与预期不符，应返回消息身份 "
                                     f"{[m['message_id'] for m in expected[stage]]}；实际 "
                                     f"{[m['message_id'] for m in messages]}")
            with _validation_stage(f"zcode-{stage}（固定样本重复轮询）", root):
                _, cursor = _collect(code, root, cursor, scope=scope, rerun=True)
    return sum(map(len, expected.values()))


def validate_candidate(config: dict, code: bytes, fixture: Path) -> tuple[dict, dict]:
    fixture = fixture.resolve(strict=True)
    sample = json.loads(read_limited(fixture, MAX_OUTPUT).decode("utf-8"))
    required = {"before", "after", "expected_before", "expected_added", "scope"}
    if not isinstance(sample, dict) or set(sample) != required:
        raise ValueError("验收样本需要 before、after、expected_before、expected_added 和授权 scope")
    scope = plugin_scope.validate(sample["scope"])
    checks = {"zcode_fixed": _check_fixed_zcode(code)} if scope["kind"] == "zcode" else {}
    roots = []
    for field in ("before", "after"):
        if not _text(sample[field], 4096):
            raise ValueError(f"无效样本路径：{field}")
        path = fixture.parent / sample[field]
        with _validation_stage(f"{field}（解析样本路径）", path):
            root = path.resolve(strict=True)
            if root == Path(config["root"]):
                raise ValueError("验收需要隔离样本和独立的实际来源")
        roots.append(root)
    before, after = roots
    if before == after:
        raise ValueError("首次和追加样本需要是独立快照")
    expected = {}
    for field in ("expected_before", "expected_added"):
        if not isinstance(sample[field], list) or not sample[field]:
            raise ValueError(f"验收需要非空独立预期：{field}")
        expected[field] = [validate_message(value) for value in sample[field]]
    with _validation_stage("before（首次读取）", before):
        initial, cursor = _collect(code, before, scope=scope)
        if initial != expected["expected_before"]:
            raise ValueError("首次读取与独立预期不符")
    with _validation_stage("before（重复读取）", before):
        _collect(code, before, cursor, scope=scope, rerun=True)
    with _validation_stage("after（追加读取）", after):
        added, final_cursor = _collect(code, after, cursor, scope=scope)
        if added != expected["expected_added"]:
            raise ValueError("追加读取与独立预期不符")
    with _validation_stage("after（重复读取）", after):
        _collect(code, after, final_cursor, scope=scope, rerun=True)
    with _validation_stage("after（完整重放）", after):
        replay, _ = _collect(code, after, scope=scope)
        if len(replay) != len(initial) + len(added) or {
            (m["session_id"], m["message_id"]): m for m in replay
        } != {(m["session_id"], m["message_id"]): m for m in initial + added}:
            raise ValueError("完整重放没有保留首次和新增消息的身份及原文")
        for session_id in {message["session_id"] for message in replay}:
            if [m for m in replay if m["session_id"] == session_id] != [
                m for m in initial + added if m["session_id"] == session_id
            ]:
                raise ValueError("完整重放改变了同一会话内的消息顺序")
    live_root = Path(config["root"])
    with _validation_stage("live（实际来源探测）", live_root):
        if scope["kind"] == "all" or scope.get("all_sessions"):
            messages = execute(code, live_root, None, scope)["messages"]
        else:
            messages, _ = _collect(code, live_root, scope=scope)
        if not messages:
            raise ValueError("实际来源未读到授权范围内的可归档对话")
    checks.update(first=len(initial), added=len(added), live_preview=len(messages))
    return checks, scope
