# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Command line for the aggregation package."""

import argparse
import json
from pathlib import Path

from ._archive import Archive, shared_db_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="smm-hub", description="多机对话汇总服务")
    parser.add_argument("--db", help="手动运行汇总服务时使用的独立数据库")
    sub = parser.add_subparsers(dest="command", required=True)
    hub = sub.add_parser("serve-hub", help="运行独立的多机汇总服务")
    hub.add_argument("--host", default="127.0.0.1")
    hub.add_argument("--port", type=int, default=8770)
    hub.add_argument("--token-file", required=True)
    hub.add_argument("--tls-cert")
    hub.add_argument("--tls-key")
    hub.add_argument("--state-dir", type=Path,
                     help="读取此目录的 VibeInsight 配置和凭据，默认使用其中的 smm-hub.sqlite3")
    from .hub_admin import add_arguments, dispatch

    add_arguments(sub)
    args = parser.parse_args()
    if args.command == "hub":
        try:
            result = dispatch(args)
        except (OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    import uvicorn
    from .hub import create_hub

    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("TLS 证书和私钥必须一起提供")
    if args.host not in {"127.0.0.1", "::1", "localhost"} and not args.tls_cert:
        parser.error("非回环地址必须启用 TLS")
    local_path = shared_db_path().resolve()
    state = args.state_dir.expanduser().resolve() if args.state_dir is not None else None
    configured_db = state / "smm-hub.sqlite3" if state is not None else None
    hub_path = Path(args.db or configured_db or local_path.with_name("smm-hub.sqlite3")).expanduser().resolve()
    if configured_db is not None and hub_path != configured_db and not (
            hub_path.exists() and configured_db.exists() and hub_path.samefile(configured_db)):
        parser.error("--db 与 --state-dir 必须指向同一汇总档案")
    if hub_path == local_path or (hub_path.exists() and local_path.exists() and hub_path.samefile(local_path)):
        parser.error("汇总服务必须使用独立数据库")
    try:
        token = Path(args.token_file).expanduser().read_text(encoding="ascii").strip()
        archive = Archive(hub_path)
        lifespan = None
        if state is not None:
            from .vibeinsight_settings import VibeInsightSettings

            lifespan = VibeInsightSettings(state, archive).lifespan
        uvicorn.run(create_hub(archive, token, lifespan=lifespan), host=args.host, port=args.port,
                    ssl_certfile=args.tls_cert, ssl_keyfile=args.tls_key)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
