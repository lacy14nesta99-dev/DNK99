# Temporary hosting on Render

The included `render.yaml` creates one **free** Python web service. No database add-on, paid disk or cron job is requested. The app has no package dependencies.

1. Open https://render.com/deploy?repo=https://github.com/lacy14nesta99-dev/DNK99 .
2. Sign in to Render and authorize GitHub access to `lacy14nesta99-dev/DNK99` if prompted. For a private repository, use your Render dashboard → New → Blueprint and select this repository if the direct link cannot access it.
3. Review the Blueprint. Confirm that the web service is on the **Free** plan, then deploy it. Do not enable paid services for this preview.
4. Open the `https://…onrender.com` URL that Render assigns. The actual URL is generated after successful deployment; do not assume the name is available.
5. Verify `/api/health` returns `status: ok`, then inspect **Our sources** and the collection status in the app. A healthy web server does not establish that every source is reachable or that collected stories are verified.

If using New → Web Service instead of a Blueprint, choose Python 3, set build command `python3 -m compileall -q aggregator.py server.py review.py`, start command `python3 server.py --host 0.0.0.0 --port $PORT`, health path `/api/health`, Free instance, and the environment variables shown in render.yaml.

## What this preview does and does not preserve

Free instances may sleep, restart, or be replaced. Local SQLite storage is ephemeral. Daily collection only runs while the process is awake, and waking the service triggers catch-up. **This is not a reliable daily collection or permanent archival deployment.** No uptime workaround or paid resource has been configured.

The preview displays this limitation in the interface. Visit **Archive → Download archive** to save a JSON copy of the stories, edition dates, and evidence notes before a restart. The download is a portable record, not a scheduled backup. Keep the original local `data/` folder as well; deployment does not upload your local database.

Manual collection is disabled on the public preview to avoid unauthenticated visitors repeatedly fetching sources. Startup and scheduled collection still run. No API keys are required. Publishers may still reject collection, regardless of hosting; inspect actual source errors rather than interpreting web-server health as collection success.

For reliable daily collection and retained history later, choose an always-on instance with persistent storage and set `DATA_DIR` to the mounted disk directory. This may cost money; it is not enabled by this free preview configuration.

## Verification

All discovered stories begin unverified, and the default feed shows only human-reviewed claims. Turn off **Reviewed only** to inspect discovery leads. A public deployment does not turn feed matching into double fact-checking. See README.md for the editorial review workflow.

## Stop the preview

Delete the web service/Blueprint in your Render dashboard when finished. Export your archive first. Automatic redeployment is disabled; manually deploy new commits when you want to update it.
