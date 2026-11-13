# ai-agent-workflow

A reusable AI agent pipeline we bring to any hackathon: it reads the track briefs and our repo, then produces architecture visuals, a slide deck and plain-English progress updates.

## Team

| Name | GitHub | Lane |
|---|---|---|
| Cameron | [@campeete](https://github.com/campeete) | API, integration, security, infrastructure; leads AI and agent |
| Rihanna | [@phantom-rose](https://github.com/phantom-rose) | Data and logic, frontend; shares AI and agent. Goal: build the dashboard that shows our agents' diagrams and decks |

## Live API

- API: https://ai-agent-workflow-production-a63941fd.up.railway.app
- Interactive docs: https://ai-agent-workflow-production-a63941fd.up.railway.app/docs
- Reference docs: https://ai-agent-workflow-production-a63941fd.up.railway.app/redoc

The dashboard and model endpoints need the team password (ask Cameron). Every merge to `main` redeploys automatically ([deploy guide](docs/deploy.md)).

## Start here

1. Setup (Mac): `bash scripts/setup-mac.sh`
2. Run the starter API: `uv run uvicorn app.main:app --reload`, then open http://127.0.0.1:8000/docs
3. Work through [docs/step1-drills.md](docs/step1-drills.md)

## Docs

- [Workflow plan](docs/hackathon-workflow-plan.md)
- [Step 1 drills](docs/step1-drills.md)
- [Using Cursor and VS Code](docs/cursor-guide.md)
- [Agent rules](AGENTS.md)
- [Deploy guide](docs/deploy.md)

## Rules

- Never commit secrets. Keys go in each host's environment variables. This repo is public.
- Change things on a branch and open a pull request; the other person reviews it.
