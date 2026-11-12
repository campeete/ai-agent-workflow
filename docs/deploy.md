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

| Variable | Used by | Get it at |
|---|---|---|
| `NVIDIA_API_KEY` | Nemotron models | build.nvidia.com → model page → Get API Key |
| `GEMINI_API_KEY` | Gemini models | aistudio.google.com → Get API key |
| `OPENAI_API_KEY` | GPT models (optional, prepaid) | platform.openai.com → API Keys |
| `ELEVENLABS_API_KEY` | British voice for the Judge (needs only the Text to Speech permission) | elevenlabs.io → Developers → API Keys |
| `ELEVENLABS_VOICE_ID` | Which voice reads the verdict (not secret) | ElevenLabs → Voices → copy Voice ID |
| `PRESENTON_API_KEY` | Presenton deck builder | presenton.ai/api-key |
| `TWOSLIDES_API_KEY` | 2Slides deck builder | 2slides.com/api |
| `GAMMA_API_KEY` | Gamma deck builder (Pro plan or higher) | gamma.app → Settings and Members → API key |
| `PLUSAI_API_KEY` | Plus AI deck builder (Pro or Team plan) | Plus AI account → API key |
| `GITHUB_TOKEN` | Optional: higher GitHub rate limit for the Repo reader | github.com → Settings → Developer settings → fine-grained token, public repos read-only |
| `DASHBOARD_PASSWORD` | Login for the dashboard and every model endpoint | Make one up: long and random; share it only with teammates |

A model whose key is missing shows as "Key not set" on `/dashboard` and is skipped; nothing crashes.
Without `DASHBOARD_PASSWORD` on Railway the site refuses every request except `/health` (fails closed). Locally it runs open if unset.
After 10 wrong passwords from one address in 5 minutes, that address is blocked for the rest of the window.
If a key is ever pasted anywhere public (chat, commit, screenshot), revoke it and create a new one.

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
