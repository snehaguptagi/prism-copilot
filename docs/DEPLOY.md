# Deploying PRISM

> Short version: the **frontend deploys to Vercel cleanly**. The **backend does not
> belong on Vercel** as written, for three concrete reasons given below. Put it on a
> host with a writable disk and a long request timeout, then point the frontend at it.

## What has to be true before deploying anything

1. **Rotate the Anthropic key.** Whatever key is in `backend/.env` should be
   replaced before it goes into any hosting provider's environment. Generate a new
   one at <https://console.anthropic.com> and revoke the old one.
2. **Understand that the API has no auth.** `backend/api.py` says so at the top:
   *"No auth — single-PM demo, open API. Add real authentication before this ever
   touches real client data."* Three endpoints spend Anthropic credits per call,
   and `/news/feed?force=true` bypasses the cache every time. Deployed on a public
   URL with no auth, anyone who finds it can run up your bill. Put the backend
   behind auth, an allowlist, or at minimum a rate limit before making it public.
3. **The client data is synthetic**, so there is no real-data exposure — but the
   two points above are about cost and abuse, not privacy.

## Frontend → Vercel

The repo is a monorepo, so the project's **Root Directory must be `frontend`**.
The simplest route is to deploy from inside that directory:

```bash
cd frontend && npx vercel login
```

```bash
cd frontend && npx vercel --prod
```

Set one environment variable in the Vercel project, **before the build**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE` | the public HTTPS URL of your deployed backend |

`NEXT_PUBLIC_*` variables are inlined into the bundle at build time, not read at
runtime. If you set or change it after a build, redeploy — restarting is not enough.
Leave it unset and the deployed site calls `http://localhost:8000`, which resolves
on each *visitor's* machine, so every panel shows a fetch error.

Nothing else is needed: Next.js 16 is detected automatically, `next build` passes,
and all routes are static except `/clients/[id]`.

## Backend → not Vercel

Three blockers, in order of severity:

**1. Vercel's filesystem is read-only.** Every runtime edit — add a client, edit
holdings, edit a profile — calls `save_overlay()`, which writes
`prism_overlay.json`. On Vercel that raises `OSError: [Errno 30] Read-only file
system`. Only `/tmp` is writable, and it is per-invocation, so pointing there
(`PRISM_OVERLAY_PATH=/tmp/prism_overlay.json`) gives you writes that succeed and
then vanish when the instance recycles — arguably worse than failing loudly.

**2. The research pipeline runs long.** A cold `/news/feed` call was measured at
**55 seconds** in development: it makes a real grounded web-search call and then
narrates the result. Vercel's Hobby function ceiling does not comfortably fit that,
so the News Feed and Analysis tabs would time out or be extremely fragile.

**3. The news cache is in-process.** `_NEWS_CACHE` is a module-level dict, so every
cold start loses it and re-runs a billable 55-second call. On serverless, cold
starts are the normal case.

### Where it does work

Any host that gives you a persistent process, a writable disk, and a generous
timeout — Render, Railway, Fly.io, or a plain VM. The service is a standard ASGI
app:

```bash
pip install -r requirements.txt && uvicorn api:app --host 0.0.0.0 --port $PORT
```

Environment variables:

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | Rotate first. Without it, the three research endpoints return 500 and the rest of the app works. |
| `PM_NAME` | no | Display name in the top bar. |
| `PRISM_OVERLAY_PATH` | no | Point at a mounted volume so runtime edits survive a restart. Defaults to `backend/prism_overlay.json`. |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | no | Optional knowledge-graph layer; the app runs identically without it. |

`prism_data.json` is committed, so no build step is required — but if you do run
`python build_dataset.py` on the host, it will not touch the overlay (that
separation is asserted by the test suite).

CORS is currently `allow_origins=["*"]` (`backend/api.py`), which is what makes a
cross-origin Vercel frontend work at all. Narrow it to your Vercel domain before
this is anything more than a demo.

### If you want a Vercel-only deployment anyway

It is possible, with a known and stated loss: run the backend as a Python
serverless function, set `PRISM_OVERLAY_PATH=/tmp/prism_overlay.json`, and accept
that **client editing does not persist** and the two research tabs are unreliable.
The Overview, Clients, Products and Product Fit tabs all read from the committed
`prism_data.json` and would work fine. That is a reasonable read-only showcase; it
is not the working application.
