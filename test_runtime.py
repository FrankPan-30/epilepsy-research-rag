"""Real OS tests for locking, shutdown, Unicode storage and Windows MCP launch."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import configure
import rag
from runtime_support import build_lock,child_process_options,stop_process_tree,venv_python


class RuntimeTests(unittest.TestCase):
    def test_build_lock_excludes_another_process_and_releases_after_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'build.lock'
            code="""import sys
from runtime_support import build_lock
try:
    with build_lock(sys.argv[1]): pass
except BlockingIOError: sys.exit(75)
"""
            def attempt():
                return subprocess.run([sys.executable,'-c',code,str(path)],cwd=rag.ROOT,capture_output=True,timeout=10)
            with self.assertRaisesRegex(RuntimeError,'fixture'):
                with build_lock(path):
                    result=attempt()
                    self.assertEqual(result.returncode,75,result.stderr)
                    raise RuntimeError('fixture')
            self.assertEqual(attempt().returncode,0)
            # OS teardown also releases the lock, even without normal context cleanup.
            abrupt="import os,sys; from runtime_support import build_lock; c=build_lock(sys.argv[1]); c.__enter__(); os._exit(0)"
            subprocess.run([sys.executable,'-c',abrupt,str(path)],cwd=rag.ROOT,check=True,timeout=10)
            with build_lock(path):pass

    def test_shutdown_stops_child_and_descendant(self):
        with tempfile.TemporaryDirectory() as temp:
            ready=Path(temp)/'ready.json'
            child="""import json,os,socket,sys,time
from pathlib import Path
sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen()
Path(sys.argv[1]).write_text(json.dumps({'port':sock.getsockname()[1],'pid':os.getpid()}))
time.sleep(120)
"""
            parent="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); time.sleep(120)"
            process=subprocess.Popen([sys.executable,'-c',parent,child,str(ready)],**child_process_options())
            try:
                deadline=time.monotonic()+10
                while not ready.exists() and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue(ready.exists(),'Child process did not start')
                info=json.loads(ready.read_text())
                with socket.create_connection(('127.0.0.1',info['port']),timeout=2):pass
                stop_process_tree(process)
                self.assertIsNotNone(process.poll())
                with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',info['port']),timeout=2)
            finally:
                stop_process_tree(process)
                # Clean up our test child even if the assertion detects a shutdown bug.
                if ready.exists():
                    try:os.kill(json.loads(ready.read_text())['pid'],15)
                    except ProcessLookupError:pass
                    except OSError:pass

    def test_utf8_storage_with_python_utf8_mode_disabled(self):
        with tempfile.TemporaryDirectory(prefix='rag-unicode-') as temp:
            root=Path(temp)/'文献 folder';root.mkdir()
            (root/'config.json').write_text('{"collection_name":"癫痫预测"}',encoding='utf-8')
            code="""from pathlib import Path
import rag
assert rag.CFG['collection_name']=='癫痫预测'
rag.write_json(rag.WORKSPACE/'proof.json',{'title':'中文文献'})
"""
            env={**os.environ,'RAG_WORKSPACE':str(root)}
            result=subprocess.run([sys.executable,'-X','utf8=0','-c',code],cwd=rag.ROOT,env=env,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((root/'proof.json').read_bytes().decode('utf-8'))['title'],'中文文献')

    @unittest.skipUnless(os.name=='nt','Windows PowerShell command execution')
    def test_powershell_mcp_command_preserves_unicode_spaces_and_quotes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"O'Brien 文献 folder"
            output=Path(temp)/'args.json';script=Path(temp)/'invoke.ps1'
            body="function codex { $args | ConvertTo-Json -Compress | Set-Content -Encoding utf8 -LiteralPath '"+str(output).replace("'","''")+"' }\n"
            script.write_text(body+configure.mcp_command(root),encoding='utf-8-sig')
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(script)],capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            args=json.loads(output.read_text(encoding='utf-8-sig'))
            self.assertEqual(args[-2:],[str(venv_python(root)),str(root/'mcp_server.py')])
            self.assertIn('PYTHONUTF8=1',args)


if __name__=='__main__':unittest.main(verbosity=2)
