# Africa AI Wire

A responsive news desk for AI, funding, compute, chips, and policy across sub-Saharan Africa. Python 3.10+ and its standard library are the only runtime dependencies. The earlier Pong game is preserved as `pong.html`.

## Run

```sh
cd /workspace/DNK99
python3 server.py --port 8000
```

The app collects on startup when a daily edition is due, then checks hourly for the 06:00 Africa/Nairobi collection. It catches up after downtime. The server must stay running for scheduled refreshes. A daily cron job can instead invoke `python3 /workspace/DNK99/server.py --refresh`; use `--no-scheduler` for the web server in that configuration. Don't run duplicate schedulers. No external scheduler or hosting has been provisioned.

## Coverage and access

`sources.json` defines regional RSS feeds, official company feeds, and government listing-page collectors. Additional Google News RSS queries discover English, French, Portuguese, funding, Western press, government, and public social reporting. Links from search feeds may be Google News redirect URLs. Social discovery covers indexed public X, LinkedIn and Bluesky posts only; it is not exhaustive direct social scraping. No private posts, paywall bypasses, or account credentials are used. Robots exclusions are respected; unavailable robots policies fail closed except HTTP 404. Source errors are shown in the app. Keyword relevance can have false positives and false negatives. HTML listing entries without dates explicitly have no publication date.

Required outbound HTTPS hosts: `news.google.com`, `techcabal.com`, `disruptafrica.com`, `www.itweb.co.za`, `www.wearetech.africa`, `blog.google`, `blogs.microsoft.com`, `about.fb.com`, `openai.com`, `www.anthropic.com`, `ict.go.ke`, `www.minict.gov.rw`, `www.gov.za`. Publisher redirects may require additional host permissions; diagnose the specific error and add only needed domains. Optional fonts use `fonts.googleapis.com` and `fonts.gstatic.com`; system fonts work offline.

This environment initially denied news-source access. No real news or verified claims have been seeded. Until network settings are applied and collection succeeds, the app shows its real empty state. Successful access to every configured endpoint has not been established. The Our sources page exposes collection results; endpoint changes may require source configuration updates.

## Archive and verification

SQLite data lives in `data/news.sqlite3`. Back up the **entire data directory** while the app is stopped (or use SQLite's backup API). Store it on persistent storage for deployment; publishing code alone is not a data backup. Articles are identified by source URL; repeat collections preserve first-discovered UTC edition dates, article content and editorial reviews. Different URLs covering the same event remain separate source items; this app does not claim they are independent corroboration.

The wire defaults to reviewed stories only; turn off “Reviewed only” to inspect clearly labelled unverified leads. Nothing is automatically declared double fact-checked. Every collected story starts unverified. To record a human review, open and inspect at least a primary document and independent reporting that support the same specific claim. Prepare a JSON array with at least two records:

```json
[
  {"url":"https://primary-publisher.example/document", "publisher":"Primary publisher", "role":"primary", "claim":"The exact claim you checked", "note":"What the document says, with relevant context"},
  {"url":"https://independent-publisher.example/report", "publisher":"Independent publisher", "role":"independent", "claim":"The exact claim you checked", "note":"What the independently reported evidence establishes"}
]
```

Then run `python3 review.py ARTICLE_ID /path/to/evidence.json`. IDs are available in `/api/news`. The command requires different publisher names and domains, both roles, matching claims and nonempty notes. It cannot establish factual truth or actual publisher independence: those remain human responsibilities. Review applies only to the recorded claim; funding checks should distinguish commitments from disbursements and verify amount, currency, stage, participants and dates. Notes and source links appear in the story detail dialog.

## Validate

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

## Deployment boundary

This is a single-instance research app. Bind locally with `--host 127.0.0.1` if needed. Put authentication and HTTPS at your reverse proxy before exposing collection controls publicly. Refresh requests have same-origin protection and a five-minute cooldown. No subscriptions, email deliveries, translations, external hosting or scheduler service have been configured. Logs and source failures are accessible to app users; do not put credentials in feed URLs.

## Temporary public preview

See [DEPLOY.md](DEPLOY.md) and `render.yaml` for the free Render configuration. This preview has ephemeral storage and can sleep, so it cannot provide reliable daily collection or permanent archives. Download a JSON copy from Archive before a restart. `DATA_DIR` can point to a persistent volume on an upgraded host. `TEMPORARY_HOST=1` shows the hosting limitation in the UI; `ALLOW_MANUAL_REFRESH=0` disables public manual collection.
