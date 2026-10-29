"""Optional UI validation. Requires Playwright and a running app on port 8000.
Uses intercepted API fixtures only; never inserts synthetic stories into the archive.
Run: python3 tests/browser_smoke.py
"""
from playwright.sync_api import sync_playwright
import datetime as dt
import json
import urllib.request

BASE='http://127.0.0.1:8000'
with urllib.request.urlopen(BASE+'/api/health') as r:
 assert json.load(r)['status']=='ok'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1440,'height':1100})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE,wait_until='networkidle')
 page.get_by_role('heading',name='The latest wire').wait_for()
 page.get_by_role('button',name='Archive',exact=True).click()
 assert page.get_by_role('heading',name='The archive').is_visible()
 page.get_by_role('button',name='Our sources',exact=True).click()
 assert page.get_by_role('heading',name='Anthropic',exact=True).is_visible()
 page.get_by_role('button',name='How we verify',exact=True).click()
 assert page.get_by_role('heading',name='Two sources. One specific claim.').is_visible()
 page.get_by_role('button',name='The wire').click()
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
 # Explicit test data is intercepted in this browser, never persisted in the real app.
 def article(id,title,language,company,edition,reviewed=False):
  return dict(id=id,title=title,url='https://example.org/'+id,summary='Browser test fixture only',published=edition+'T12:00:00Z',discovered=edition+'T12:00:00Z',edition=edition,source='Test publisher',kind='reporting',language=language,countries=['Kenya'],topics=['AI & research','Funding'],companies=[company],verification='reviewed' if reviewed else 'unverified',evidence=[dict(url='https://example.org/primary',publisher='Primary test publisher',role='primary',claim='A test claim',note='Test evidence')] if reviewed else [],reviewed=edition if reviewed else None)
 fixture=dict(articles=[article('one','TEST FIXTURE: Google Kenya AI','en','Google','2026-10-29',True),article('two','TEST FIXTURE: financement intelligence artificielle','fr','Microsoft','2026-10-28'),article('three','TEST FIXTURE: Angola inteligência artificial','pt','Meta','2026-10-28')],editions=[dict(edition='2026-10-29',count=1),dict(edition='2026-10-28',count=2)],sources=[],last_run=None,collecting=False,today='2026-10-29')
 page.route('**/api/news',lambda route:route.fulfill(json=fixture))
 page.reload(wait_until='networkidle')
 assert page.locator('.story').count()==1
 page.get_by_label('Reviewed only').uncheck()
 assert page.locator('.story').count()==3
 page.get_by_label('Filter by language').select_option('fr');assert page.locator('.story').count()==1
 page.get_by_label('Filter by language').select_option('all')
 page.get_by_label('Reviewed only').check();assert page.locator('.story').count()==1
 page.get_by_role('button',name='Source notes').click();assert page.get_by_role('dialog').is_visible()
 assert page.get_by_text('A test claim',exact=False).is_visible()
 page.get_by_role('button',name='Close story details').click()
 page.get_by_label('Reviewed only').uncheck()
 page.get_by_label('Search stories',exact=True).fill('Angola');assert page.locator('.story').count()==1
 page.get_by_label('Search stories',exact=True).fill('')
 page.get_by_role('button',name='Google 1').click();assert page.locator('.story').count()==1
 page.get_by_role('button',name='Clear company filter').click();assert page.locator('.story').count()==3
 page.get_by_role('button',name='Archive',exact=True).click()
 page.locator('[data-edition="2026-10-28"]').click();assert page.locator('.story').count()==2
 assert not errors,errors
 browser.close()
print('PASS: live API; desktop/mobile layout; source/verification/archive navigation; fixture-tested language, company, search, review filters, source notes, historical editions; no JS errors.')
