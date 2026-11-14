#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
probe_python='import ensurepip, sqlite3, sys, venv; assert sys.version_info >= (3, 11); sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(body)")'
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$probe_python" 2>/dev/null; then
        exec "$candidate" "$script_dir/first_use.py" "$@"
    fi
done
runtime_dir="$HOME/.local/share/smm-local/bootstrap"
mkdir -p "$runtime_dir"
if [ ! -x "$runtime_dir/uv" ]; then
    installer=$(mktemp)
    trap 'rm -f "$installer"' EXIT
    curl -fsSL --connect-timeout 15 --max-time 60 --retry 2 https://astral.sh/uv/0.13.8/install.sh -o "$installer"
    UV_UNMANAGED_INSTALL="$runtime_dir" sh "$installer" >&2
    rm -f "$installer"
    trap - EXIT
fi
export UV_PYTHON_INSTALL_DIR="$runtime_dir/python"
python_path=$("$runtime_dir/uv" python find --managed-python 3.13 2>/dev/null) || {
    "$runtime_dir/uv" python install 3.13 >&2
    python_path=$("$runtime_dir/uv" python find --managed-python 3.13)
}
exec "$python_path" "$script_dir/first_use.py" "$@"
