"""Record a human editorial review: python3 review.py ARTICLE_ID evidence.json.
Evidence must contain independent reporting, a primary document, and a claim checked against each.
"""
import argparse
import json
from urllib.parse import urlsplit
import aggregator as news

def validate(evidence):
 if not isinstance(evidence,list) or len(evidence)<2:raise ValueError('At least two reviewed sources are required')
 for e in evidence:
  if not all(isinstance(e.get(k),str) and e[k].strip() for k in ['url','publisher','claim','note','role']):raise ValueError('Each evidence record needs url, publisher, claim, note and role')
  if urlsplit(e['url']).scheme!='https' or not urlsplit(e['url']).hostname:raise ValueError('Evidence must link to a public HTTPS source')
  if e['role'] not in ['primary','independent']:raise ValueError('Role must be primary or independent')
 domains={urlsplit(e['url']).hostname.removeprefix('www.') for e in evidence}
 if len(domains)<2 or len({e['publisher'].strip().lower() for e in evidence})<2:raise ValueError('Independent publishers and domains are required')
 if {e['role'] for e in evidence}!={'primary','independent'}:raise ValueError('Review needs both primary evidence and independent reporting')
 if len({e['claim'].strip() for e in evidence})!=1:raise ValueError('Both sources must check the same specific claim')
 return evidence

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('article_id');p.add_argument('evidence_file');args=p.parse_args()
 evidence=validate(json.loads(open(args.evidence_file).read()));news.init()
 with news.connect() as c:
  cur=c.execute('UPDATE articles SET verification=?,evidence=?,reviewed=? WHERE id=?',('reviewed',json.dumps(evidence),news.now(),args.article_id))
  if not cur.rowcount:raise SystemExit('Article not found')
 print('Human review recorded. This is an editorial attestation, not automatic proof of truth.')
