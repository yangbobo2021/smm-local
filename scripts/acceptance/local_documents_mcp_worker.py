"""Forward a real stdio server and record the owned server's actual exit."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


report=Path(sys.argv[1]);argv=json.loads(sys.argv[2]);started=time.time();code=None
process=subprocess.Popen(argv)
try:code=process.wait()
finally:
    if process.poll() is None:
        process.terminate()
        try:code=process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();code=process.wait()
    report.write_text(json.dumps({'wrapper_pid':os.getpid(),'pid':process.pid,'argv':argv,'started_at':started,'finished_at':time.time(),'exit_code':code,'alive':process.poll() is None})+'\n',encoding='utf-8')
raise SystemExit(code)
