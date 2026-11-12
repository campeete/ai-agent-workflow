# Deploy guide (Railway)

Every push to `main` redeploys automatically. Deployment is Cameron's lane.

## How it runs
- Railway builds with Railpack: it reads `pyproject.toml`, `uv.lock` and `.python-version` (3.12).
- `railway.json` sets the start command: uvicorn on `0.0.0.0:$PORT` (Railway picks the port).
- Health check: Railway calls `GET /health` and only switches traffic once it returns 200.

## First-time setup (done once)
1. railway.com → New Project → Deploy from GitHub repo → `campeete/ai-agent-workflow`.
2. Service → Settings → Networking → Generate Domain.
3. Share the URL with the team. Add `/docs` to see every endpoint.

## Secrets
Add them in Railway → service → Variables. Never in the repo. Read them in code with `os.environ["NAME"]`.

## Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| Health check fails | App not listening on `$PORT` or `0.0.0.0` | Check `railway.json` start command |
| `'$PORT' is not a valid integer` | Start command not run through a shell | Keep the `sh -c '...'` wrapper |
| Build picks wrong Python | `.python-version` missing | Keep it at the repo root |
| Logs: `ModuleNotFoundError: agents` | Wrong start directory | Start command must run from repo root |

Logs: `railway logs` (after `railway link`) or the Deployments tab.
