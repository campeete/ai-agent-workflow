# Deploy guide (Railway)

Every push to `main` redeploys automatically. Deployment is Cameron's lane.

**Live URL:** https://ai-agent-workflow-production-a63941fd.up.railway.app (Railway project ID `05bbc84a`, service `ai-agent-workflow`, region US East)

## How it runs
- Railway builds with Railpack: it reads `pyproject.toml`, `uv.lock` and `.python-version` (3.12).
- `railpack.json` sets the start command: uvicorn on `0.0.0.0:$PORT` (Railway picks the port).
- `railway.json` sets the health check and restart policy (Railway plans to replace it after 2026-12-01; run `railway config migrate` then).
- Health check: Railway calls `GET /health` and only switches traffic once it returns 200.

## First-time setup (done once)
1. `railway init` then `railway up` from the repo root (or railway.com → New Project → Deploy from GitHub repo).
   Then service → Settings → Source → Connect Repo → `campeete/ai-agent-workflow`, branch `main`, and click **Apply changes** so pushes auto-deploy.
2. Service → Settings → Networking → Generate Domain.
3. Share the URL with the team. Add `/docs` to see every endpoint.

## Secrets
Add them in Railway → service → Variables. Never in the repo. Read them in code with `os.environ["NAME"]`.

## Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| `No start command detected` | Railpack did not find a start command | Keep `railpack.json` at the repo root |
| Health check fails | App not listening on `$PORT` or `0.0.0.0` | Check the `railpack.json` start command |
| `'$PORT' is not a valid integer` | Start command not run through a shell | Keep the `sh -c '...'` wrapper |
| Build picks wrong Python | `.python-version` missing | Keep it at the repo root |
| Logs: `ModuleNotFoundError: agents` | Wrong start directory | Start command must run from repo root |

Logs: `railway logs` (after `railway link`) or the Deployments tab.

## Local CLI link
`railway link` (pick the project) then `railway service` (pick `ai-agent-workflow`). `railway status` should show both.
