"""Public-feed discovery. No API keys, paywall bypasses, or social login scraping."""
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('DATA_DIR', str(ROOT / 'data'))) / 'news.sqlite3'
LOCK = threading.Lock()
UA = 'AfricaAIWire/1.0 (+public-news-research; respects robots.txt)'
COUNTRIES = {
 'Nigeria':['nigeria','nigerian','lagos','abuja'], 'Kenya':['kenya','kenyan','nairobi'],
 'South Africa':['south africa','south african','johannesburg','cape town'],
 'Rwanda':['rwanda','kigali'], 'Ghana':['ghana','accra'], 'Senegal':['senegal','sénégal','dakar'],
 'Côte d’Ivoire':['ivory coast',"côte d’ivoire","côte d'ivoire",'abidjan'],
 'Cameroon':['cameroon','cameroun','yaoundé'], 'DR Congo':['congo','kinshasa'],
 'Angola':['angola','luanda'], 'Mozambique':['mozambique','moçambique','maputo'],
 'Ethiopia':['ethiopia','éthiopie','addis ababa'], 'Uganda':['uganda','ouganda','kampala'],
 'Tanzania':['tanzania','tanzanie','dar es salaam'], 'Zambia':['zambia','zambie','lusaka'],
 'Zimbabwe':['zimbabwe','harare'], 'Botswana':['botswana','gaborone'],
 'Namibia':['namibia','namibie','windhoek'], 'Mauritius':['mauritius','maurice'],
 'Madagascar':['madagascar','antananarivo'], 'Benin':['benin','bénin','cotonou'],
 'Togo':['togo','lomé'], 'Burkina Faso':['burkina faso','ouagadougou'],
 'Mali':['mali','bamako'], 'Niger':['niger','niamey'], 'Guinea':['guinea','guinée','conakry'],
 'Sierra Leone':['sierra leone','freetown'], 'Liberia':['liberia','libéria','monrovia'],
 'Gabon':['gabon','libreville'], 'Republic of Congo':['brazzaville'],
 'Chad':['chad','tchad'], 'Central African Republic':['central african republic','centrafrique'],
 'South Sudan':['south sudan','soudan du sud','juba'], 'Sudan':['sudan','soudan','khartoum'],
 'Somalia':['somalia','somalie','mogadishu'], 'Djibouti':['djibouti'], 'Eritrea':['eritrea','érythrée'],
 'Malawi':['malawi','lilongwe'], 'Lesotho':['lesotho'], 'Eswatini':['eswatini','swaziland'],
 'Burundi':['burundi','bujumbura'], 'Cape Verde':['cape verde','cabo verde'],
 'Guinea-Bissau':['guinea-bissau','guiné-bissau'], 'São Tomé and Príncipe':['são tomé','sao tome'],
 'Equatorial Guinea':['equatorial guinea','guinée équatoriale'], 'Gambia':['gambia','gambie'],
 'Seychelles':['seychelles'], 'Comoros':['comoros','comores'], 'Mauritania':['mauritania','mauritanie']}
TOPICS = {
 'AI & research':r'\bai\b|artificial intelligence|intelligence artificielle|inteligência artificial|machine learning|language model|llm\b|generative|inteligencia artificial',
 'Funding':r'funding|raises?\b|raised|investment|invests?\b|million|billion|levée|financement|investimento|financiamento|capital-risque',
 'Compute & chips':r'\bgpu|\bchip|semiconductor|data cent[er]+|datacenter|cloud|computing|calcul|centre de données|centro de dados|supercomput',
 'Policy':r'government|minister|regulat|policy|strategy|gouvernement|minist|stratégie|governo|política|legislat',
}
COMPANIES=['Google','Microsoft','Meta','OpenAI','Anthropic']
QUERIES=[
 ('discovery-en','Regional discovery','(AI OR "artificial intelligence" OR GPU OR semiconductor OR "data centre") ("sub-Saharan Africa" OR Kenya OR Nigeria OR Rwanda OR Ghana OR "South Africa")','en-KE','KE','en'),
 ('discovery-fr','Francophone discovery','("intelligence artificielle" OR "centre de données" OR puces OR "levée de fonds") (Sénégal OR Cameroun OR "Côte d’Ivoire" OR Bénin OR Congo OR Madagascar OR Afrique)','fr','SN','fr'),
 ('discovery-pt','Lusophone discovery','("inteligência artificial" OR "centro de dados" OR chips OR financiamento) (Angola OR Moçambique OR "Cabo Verde" OR "Guiné-Bissau")','pt-PT','AO','pt'),
 ('discovery-bigtech','Global companies in Africa','(Google OR Microsoft OR Meta OR OpenAI OR Anthropic) (Africa OR Kenya OR Nigeria OR Senegal) (AI OR cloud OR chips OR investment)','en-KE','KE','en'),
 ('discovery-west','International press','(Africa OR Kenya OR Nigeria OR Rwanda) ("artificial intelligence" OR GPU OR "AI funding") (site:reuters.com OR site:ft.com OR site:bbc.com OR site:theguardian.com OR site:bloomberg.com OR site:restofworld.org OR site:techcrunch.com)','en-GB','GB','en'),
 ('discovery-gov','Government discovery','("artificial intelligence" OR "intelligence artificielle" OR "inteligência artificial") (site:gov.za OR site:go.ke OR site:gov.rw OR site:gouv.sn OR site:gouv.ci OR site:gov.ng OR site:gov.ao OR site:gov.mz)','en-KE','KE','en'),
 ('discovery-social','Public social leads','(AI OR "artificial intelligence" OR "intelligence artificielle") (Kenya OR Nigeria OR Africa OR Senegal) (site:linkedin.com/posts OR site:x.com OR site:bsky.app)','en-KE','KE','en'),
 ('discovery-funding','Funding watch','(AI OR "artificial intelligence" OR "data center") (Africa OR Nigeria OR Kenya OR Senegal OR Ghana) (funding OR raises OR "series A" OR "seed round" OR investment)','en-KE','KE','en'),
]

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def connect():
 DB.parent.mkdir(parents=True, exist_ok=True)
 c=sqlite3.connect(DB, timeout=30);c.row_factory=sqlite3.Row
 c.execute('PRAGMA journal_mode=WAL');return c

def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS articles(
  id TEXT PRIMARY KEY,title TEXT NOT NULL,url TEXT UNIQUE NOT NULL,summary TEXT,
  published TEXT,discovered TEXT NOT NULL,edition TEXT NOT NULL,source_id TEXT,
  source TEXT,kind TEXT,language TEXT,countries TEXT,topics TEXT,companies TEXT,
  verification TEXT NOT NULL DEFAULT 'unverified',evidence TEXT NOT NULL DEFAULT '[]',reviewed TEXT);
  CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,started TEXT,finished TEXT,status TEXT,added INTEGER,details TEXT);
  CREATE TABLE IF NOT EXISTS source_health(id TEXT PRIMARY KEY,checked TEXT,status TEXT,count INTEGER,error TEXT);''')

def sources():
 result=json.loads((ROOT/'sources.json').read_text())
 for sid,name,q,hl,gl,lang in QUERIES:
  query=urllib.parse.urlencode({'q':q+' when:7d','hl':hl,'gl':gl,'ceid':gl+':'+lang})
  result.append(dict(id=sid,name=name,url='https://news.google.com/rss/search?'+query,homepage='https://news.google.com',kind='social' if sid.endswith('social') else 'discovery',language=lang,region='Pan-African'))
 return result

def fetch(url,limit=2_000_000):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/xml, text/html;q=0.8'})
 with urllib.request.urlopen(req,timeout=18) as r:
  data=r.read(limit+1)
  if len(data)>limit: raise ValueError('Response exceeds size limit')
  return data

class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,data):self.parts.append(data)
def plain(s):
 p=Text();p.feed(s or '');return re.sub(r'\s+',' ',' '.join(p.parts)).strip()
def matches(term,text):return bool(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.I))
def classify(title,summary=''):
 text=(title+' '+summary).lower()
 countries=[k for k,terms in COUNTRIES.items() if any(matches(t,text) for t in terms)]
 africa=bool(countries or re.search(r'\bafrica\b|\bafrique\b|\báfrica\b|african|africain|africano',text))
 # Discovery is deliberately conservative: general African funding is not necessarily AI-adjacent.
 topics=[k for k,p in TOPICS.items() if re.search(p,text)]
 north_only=not countries and any(matches(t,text) for t in ['north africa','egypt','morocco','algeria','tunisia','libya','maroc','algérie','tunisie'])
 relevant=africa and not north_only and any(t in topics for t in ['AI & research','Compute & chips'])
 companies=[k for k in COMPANIES if matches(k,text)]
 return relevant,countries,topics,companies

def date(value):
 if not value:return None
 try:
  d=email.utils.parsedate_to_datetime(value)
 except (ValueError,TypeError):
  try:d=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
  except ValueError:return None
 if d.tzinfo is None:d=d.replace(tzinfo=dt.timezone.utc)
 return d.astimezone(dt.timezone.utc).isoformat()

class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.href=None;self.text=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':self.href=dict(attrs).get('href');self.text=[]
 def handle_data(self,data):
  if self.href:self.text.append(data)
 def handle_endtag(self,tag):
  if tag=='a' and self.href:
   self.links.append((self.href,plain(' '.join(self.text))));self.href=None

def collect_source(s):
 # Respect the source's crawl policy for both listing pages and feeds. A failure is visible, not bypassed.
 parts=urllib.parse.urlsplit(s['url']);robots_url=f'{parts.scheme}://{parts.netloc}/robots.txt'
 rp=urllib.robotparser.RobotFileParser()
 try:
  try:rp.parse(fetch(robots_url).decode('utf-8','replace').splitlines())
  except urllib.error.HTTPError as e:
   if e.code==404:rp.parse([])
   else:raise
  if not rp.can_fetch(UA,s['url']):raise ValueError('Collection disallowed by robots.txt')
  data=fetch(s['url']);items=[]
  if s.get('format')=='html':
   parser=Links();parser.feed(data.decode('utf-8','replace'))
   for href,title in parser.links:
    url=urllib.parse.urljoin(s['url'],href)
    if urllib.parse.urlsplit(url).netloc!=parts.netloc or not urllib.parse.urlsplit(url).path.startswith(s['path_prefix']):continue
    if len(title)>35:items.append(dict(title=title,url=url,summary='',published=None))
  else:
   root=ET.fromstring(data)
   nodes=root.findall('.//item') or root.findall('{http://www.w3.org/2005/Atom}entry')
   for item in nodes[:150]:
    def field(*names):
     for name in names:
      el=item.find(name)
      if el is not None:return ''.join(el.itertext())
     return ''
    link=field('link');atom=item.find('{http://www.w3.org/2005/Atom}link')
    if not link and atom is not None:link=atom.get('href','')
    publisher=field('source') or s['name']
    items.append(dict(title=plain(field('title','{http://www.w3.org/2005/Atom}title')),url=link,summary=plain(field('description','{http://www.w3.org/2005/Atom}summary'))[:650],published=date(field('pubDate','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated')),publisher=publisher))
  accepted=[]
  for item in items:
   # RSS search summaries repeat the headline and cannot substantiate a claim.
   relevant,countries,topics,companies=classify(item['title'],item['summary'] if s['kind'] not in ['discovery','social'] else '')
   if not relevant or urllib.parse.urlsplit(item['url']).scheme not in ('http','https'):continue
   item.update(countries=countries,topics=topics,companies=companies,source=item.pop('publisher',s['name']))
   accepted.append(item)
  return s,accepted,None
 except Exception as e:return s,[],f'{type(e).__name__}: {e}'[:350]

def refresh():
 if not LOCK.acquire(blocking=False):return {'status':'running'}
 started=now();added=0;details=[]
 try:
  with connect() as c:
   rid=c.execute('INSERT INTO runs(started,status,added,details) VALUES(?,?,?,?)',(started,'running',0,'[]')).lastrowid
  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
   for s,items,error in pool.map(collect_source,sources()):
    details.append(dict(id=s['id'],name=s['name'],count=len(items),error=error))
    with connect() as c:
     c.execute('INSERT OR REPLACE INTO source_health VALUES(?,?,?,?,?)',(s['id'],now(),'error' if error else 'ok',len(items),error))
     for item in items:
      url=item['url'].split('#')[0]
      aid=hashlib.sha256(url.encode()).hexdigest()[:24]
      # INSERT OR IGNORE preserves the original daily edition and all editorial review.
      cur=c.execute('INSERT OR IGNORE INTO articles(id,title,url,summary,published,discovered,edition,source_id,source,kind,language,countries,topics,companies) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
       (aid,item['title'],url,item['summary'],item['published'],started,started[:10],s['id'],item['source'],s['kind'],s['language'],json.dumps(item['countries']),json.dumps(item['topics']),json.dumps(item['companies'])))
      added+=cur.rowcount
  failures=sum(bool(x['error']) for x in details)
  status='failed' if failures==len(details) else 'partial' if failures else 'ok'
  with connect() as c:c.execute('UPDATE runs SET finished=?,status=?,added=?,details=? WHERE id=?',(now(),status,added,json.dumps(details),rid))
  return dict(status=status,added=added,sources=details)
 finally:LOCK.release()

def payload(query):
 with connect() as c:
  rows=c.execute('SELECT * FROM articles ORDER BY COALESCE(published,discovered) DESC').fetchall()
  articles=[]
  for row in rows:
   a=dict(row)
   for key in ['countries','topics','companies','evidence']:a[key]=json.loads(a[key])
   articles.append(a)
  edition_rows=c.execute('SELECT edition,COUNT(*) AS count FROM articles GROUP BY edition ORDER BY edition DESC').fetchall()
  last=c.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
  health={r['id']:dict(r) for r in c.execute('SELECT * FROM source_health')}
 return dict(articles=articles,editions=[dict(r) for r in edition_rows],last_run=dict(last) if last else None,sources=[{**s,'health':health.get(s['id'])} for s in sources()],collecting=LOCK.locked(),today=now()[:10])
