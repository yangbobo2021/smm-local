# SPDX-License-Identifier: Apache-2.0
"""Forward real MCP stdio unchanged and record the server process exit status."""
import json
from pathlib import Path
import subprocess
import sys

report, database = map(Path, sys.argv[1:])
process = subprocess.Popen([sys.executable, '-m', 'smm_local.mcp_server', '--db', str(database)])
code = process.wait()
report.write_text(json.dumps({'pid':process.pid,'exit_code':code,'transport':'stdio'})+'\n',encoding='utf-8')
raise SystemExit(code)
