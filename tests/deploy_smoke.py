"""Validate the public-preview configuration with isolated ephemeral storage.
Optional browser check uses the preinstalled Playwright package.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
 with socket.socket() as sock:
  sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 base=f'http://127.0.0.1:{port}'
 config={**os.environ,'DATA_DIR':temp,'TEMPORARY_HOST':'1','ALLOW_MANUAL_REFRESH':'0'}
 proc=subprocess.Popen([sys.executable,'server.py','--port',str(port),'--host','127.0.0.1','--no-scheduler'],cwd=ROOT,env=config,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:
    with urllib.request.urlopen(base+'/api/health',timeout=1) as r:assert json.load(r)['status']=='ok'
    break
   except urllib.error.URLError:time.sleep(.1)
  else:raise AssertionError('Server did not become healthy')
  with urllib.request.urlopen(base+'/api/news') as r:
   data=json.load(r);assert data['temporary_host'];assert not data['manual_refresh_enabled'];assert data['articles']==[]
  req=urllib.request.Request(base+'/api/refresh',method='POST',headers={'X-Requested-With':'AfricaAIWire'})
  try:urllib.request.urlopen(req);raise AssertionError('Public refresh should be disabled')
  except urllib.error.HTTPError as e:assert e.code==403
  with urllib.request.urlopen(base+'/api/archive') as r:
   assert 'attachment;' in r.headers['Content-Disposition'];assert json.load(r)['version']==1
  try:
   urllib.request.urlopen(base+'/news.sqlite3');raise AssertionError('Database should not be served')
  except urllib.error.HTTPError as e:assert e.code==404
 finally:
  proc.terminate();proc.wait(timeout=5)
print('PASS: free-preview health, temporary-storage flag, public refresh disabled, downloadable archive, database not publicly served.')
