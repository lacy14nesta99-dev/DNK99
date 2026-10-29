import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import aggregator as a
from review import validate

class AggregatorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=a.DB;a.DB=Path(self.temp.name)/'news.sqlite3';a.init()
 def tearDown(self):a.DB=self.old;self.temp.cleanup()
 def test_multilingual_relevance(self):
  for title,country,topic in [('Nigeria AI startup raises seed funding','Nigeria','Funding'),('Sénégal : financement de l’intelligence artificielle','Senegal','Funding'),('Angola investe em inteligência artificial e centro de dados','Angola','Compute & chips')]:
   relevant,countries,topics,_=a.classify(title);self.assertTrue(relevant);self.assertIn(country,countries);self.assertIn(topic,topics)
  self.assertFalse(a.classify('Google launches AI in Canada')[0]);self.assertFalse(a.classify('Nigerian retailer raises funding')[0]);self.assertNotIn('Niger',a.classify('Nigeria AI strategy')[1])
 def test_real_feed_parsing_and_relevance(self):
  rss=b'<rss><channel><item><title>Microsoft expands AI cloud in Kenya</title><link>https://example.org/story</link><pubDate>Wed, 28 Oct 2026 10:00:00 GMT</pubDate><description>Data center announcement</description></item><item><title>AI in Canada</title><link>https://example.org/other</link></item></channel></rss>'
  s=dict(id='test',url='https://example.org/feed',name='Test',kind='reporting')
  with patch.object(a,'fetch',side_effect=lambda url: b'User-agent: *\nAllow: /' if url.endswith('robots.txt') else rss):
   _,items,error=a.collect_source(s)
  self.assertIsNone(error);self.assertEqual(len(items),1);self.assertEqual(items[0]['companies'],['Microsoft']);self.assertTrue(items[0]['published'].startswith('2026-10-28'))
 def test_robots_denial(self):
  with patch.object(a,'fetch',return_value=b'User-agent: *\nDisallow: /'):
   _,items,error=a.collect_source(dict(url='https://example.org/feed'))
  self.assertEqual(items,[]);self.assertIn('disallowed',error)
 def test_archive_and_review_survive_refresh(self):
  s=dict(id='test',name='Publisher',kind='reporting',language='en');item=dict(title='Kenya AI funding',url='https://example.org/story',summary='news',published=None,source='Publisher',countries=['Kenya'],topics=['Funding'],companies=[])
  with patch.object(a,'sources',return_value=[s]),patch.object(a,'collect_source',return_value=(s,[item],None)):
   self.assertEqual(a.refresh()['added'],1)
   with a.connect() as c:c.execute("UPDATE articles SET edition='2025-01-01',verification='reviewed',evidence='[]'")
   self.assertEqual(a.refresh()['added'],0)
  row=a.payload({})['articles'][0];self.assertEqual(row['edition'],'2025-01-01');self.assertEqual(row['verification'],'reviewed')
 def test_failures_visible_and_no_fabrication(self):
  with patch.object(a,'sources',return_value=[{'id':'blocked','name':'Blocked'}]),patch.object(a,'collect_source',return_value=({'id':'blocked','name':'Blocked'},[],'403 Forbidden')):
   self.assertEqual(a.refresh()['status'],'failed')
  self.assertEqual(a.payload({})['articles'],[])
 def test_verification_requires_independent_primary_evidence(self):
  e=[dict(url='https://company.example/release',publisher='Company',claim='A specific announced investment',note='Read the release',role='primary'),dict(url='https://press.example/story',publisher='Press',claim='A specific announced investment',note='Independently checked announcement',role='independent')]
  self.assertEqual(validate(e),e)
  with self.assertRaises(ValueError):validate(e[:1])
  e[1]['url']='https://company.example/another'
  with self.assertRaises(ValueError):validate(e)

if __name__=='__main__':unittest.main()
