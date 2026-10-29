#!/usr/bin/env python3
"""Run: python3 server.py. Scheduled collection runs at 06:00 Africa/Nairobi."""
import argparse
import datetime as dt
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
import threading
import time
from urllib.parse import urlsplit, parse_qs
from zoneinfo import ZoneInfo
import aggregator as news

TZ=ZoneInfo('Africa/Nairobi')

def scheduler():
 while True:
  current=dt.datetime.now(TZ)
  with news.connect() as c:
   last=c.execute("SELECT started FROM runs WHERE status IN ('ok','partial') ORDER BY id DESC LIMIT 1").fetchone()
  # Catch up after downtime; failures retry at most once an hour.
  due=current.replace(hour=6,minute=0,second=0,microsecond=0)
  if current<due:due-=dt.timedelta(days=1)
  if not last or dt.datetime.fromisoformat(last['started'])<due:
   news.refresh()
  time.sleep(3600)

class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(news.ROOT/'static'),**kwargs)
 def json(self,value,code=200):
  body=json.dumps(value,ensure_ascii=False).encode()
  self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/news':
   value=news.payload(parse_qs(urlsplit(self.path).query));value['temporary_host']=os.getenv('TEMPORARY_HOST')=='1';value['manual_refresh_enabled']=os.getenv('ALLOW_MANUAL_REFRESH','1')=='1';return self.json(value)
  if path=='/api/archive':
   payload=news.payload({})
   self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Disposition',f'attachment; filename=africa-ai-wire-{news.now()[:10]}.json');self.send_header('Cache-Control','no-store');self.end_headers()
   self.wfile.write(json.dumps({'version':1,'exported':news.now(),'articles':payload['articles'],'editions':payload['editions']},ensure_ascii=False,indent=2).encode());return
  if path=='/api/health':return self.json({'status':'ok','database':'sqlite','scheduler':not args.no_scheduler})
  if path.startswith('/api/'):return self.json({'error':'Not found'},404)
  super().do_GET()
 def do_POST(self):
  if urlsplit(self.path).path!='/api/refresh':return self.json({'error':'Not found'},404)
  if os.getenv('ALLOW_MANUAL_REFRESH','1')!='1':return self.json({'error':'Manual refresh is disabled on this public preview. Scheduled collection runs while the server is awake.'},403)
  # A custom request header prevents cross-origin form submissions; no CORS is enabled.
  if self.headers.get('X-Requested-With')!='AfricaAIWire':return self.json({'error':'Same-origin app request required'},403)
  origin=self.headers.get('Origin')
  if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return self.json({'error':'Cross-origin request denied'},403)
  if news.LOCK.locked():return self.json({'status':'running'},202)
  with news.connect() as c:last=c.execute('SELECT started FROM runs ORDER BY id DESC LIMIT 1').fetchone()
  if last and (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(last['started'])).total_seconds()<300:
   return self.json({'status':'cooldown','message':'A collection was attempted recently. Try again in five minutes.'},429)
  threading.Thread(target=news.refresh,daemon=True).start();return self.json({'status':'started'},202)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=int(os.getenv('PORT','8000')));parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--no-scheduler',action='store_true');parser.add_argument('--refresh',action='store_true',help='Collect once and exit; useful for cron')
 args=parser.parse_args();news.init()
 if args.refresh:
  print(json.dumps(news.refresh(),indent=2));raise SystemExit()
 server=ThreadingHTTPServer((args.host,args.port),Handler)
 if not args.no_scheduler:threading.Thread(target=scheduler,daemon=True).start()
 print(f'Africa AI Wire · port {args.port} · daily collection at 06:00 Africa/Nairobi',flush=True)
 server.serve_forever()
