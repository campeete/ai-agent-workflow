# Agents

The five agents in the [workflow plan](hackathon-workflow-plan.md). Live agents ask every chosen model at once (`agents/panel.py` holds the shared model checks and the rule that pasted text goes inside data tags); stubs return placeholder data.

| Step | File | Input | Output | Status |
|---|---|---|---|---|
| 1 | `agents/brief_reader.py` | Challenge text (up to 10 sections, 20,000 chars) + chosen models | One breakdown per model: goal, must-haves, judging criteria, ideas, questions, 3-step plan | live (multi-model) |
| 2 | `agents/repo_reader.py` | Pasted code (≤60,000 chars) or a public GitHub repo, optional commits, chosen models | One explanation per model (parts, data flow, endpoints, how to run, risks) + safety report; best one becomes `summary` for Visuals | live (multi-model) |
| 3 | `agents/visuals.py` | Repo summary (≤20,000 chars, auto-filled from the Repo reader's pick) + chosen models | One diagram per model as checked JSON (boxes, arrows, flow steps), drawn by the dashboard; best one as Mermaid text + numbered flow | live (multi-model) |
| 4 | `agents/slides.py` + `agents/deck_builders.py` | Material (challenge breakdown, repo explanation, diagram; auto-gathered on the dashboard) + chosen models | Stage 1: one checked JSON outline per model, judged. Stage 2: `POST /slides/build` sends the chosen outline to Presenton, 2Slides, Gamma and Plus AI, each returning links to its own designed deck | live (multi-model + deck builders) |
| 5 | `agents/progress_reporter.py` | Git commits + chosen models | One plain-English update per model | live (multi-model) |

`POST /pipeline/run` calls steps 1-4 in order. The brief reader and the repo reader use the request body. The repo summary is passed to the visuals agent, and that summary plus the visuals are passed to the slides agent. The progress reporter stays separate: `POST /agents/progress_reporter/run` with a list of commit messages.

Names used in `/agents/{name}/run` are `brief_reader`, `repo_reader`, `visuals`, `slides`, and `progress_reporter`. An unknown name returns 404.

Each live agent also has `POST /agents/{name}/judge`, which the dashboard calls after collecting the answers one model at a time.

## Repo reader safety

Code is the riskiest input, so it goes through three checks before any model sees it:

| Check | File | What it stops |
|---|---|---|
| Secret scrubbing | `agents/code_safety.py` | API keys (NVIDIA, OpenAI, Google, GitHub, AWS, Slack, ElevenLabs), JWTs, private keys and `*_KEY/_TOKEN/_PASSWORD = value` lines are replaced with `[REDACTED]`, so a model provider never receives a credential |
| Injection flags | `agents/code_safety.py` | Comments like "ignore previous instructions" are reported on the dashboard as "Safety check: flagged" |
| GitHub allowlist | `agents/github_fetch.py` | Only `owner/repo` names are accepted and only api.github.com and raw.githubusercontent.com are contacted, with no redirects (blocks SSRF). `.env`, key files, `node_modules`, lock files and binaries are never read. Max 40 files, 30 KB each, 60,000 characters total; cached 10 minutes |

Set `GITHUB_TOKEN` (a read-only, public-repos token) in Railway only if you hit GitHub's anonymous rate limit of 60 requests an hour.

## Visuals safety

Models return diagram **data**, never SVG or HTML. `agents/visuals.py` checks every answer against a strict shape (2-20 boxes with simple ids, 5 known kinds, labels under 40 characters, arrows only between known boxes). Anything else counts as a failed answer. The dashboard draws the boxes itself with `textContent`, so a label like `<script>` shows up as plain text instead of running (XSS prevention). The Mermaid export strips quotes and brackets from labels so a label can't break out of its box.

## Deck builders

| Builder | Key variable | Plan needed | Notes |
|---|---|---|---|
| Presenton | `PRESENTON_API_KEY` | Credits | One call; returns PPTX and an editor link |
| 2Slides | `TWOSLIDES_API_KEY` | Credits | Job + polling; optional `TWOSLIDES_THEME_ID` |
| Gamma | `GAMMA_API_KEY` | Pro or higher | Generation + polling; `textMode: preserve` keeps the outline's wording |
| Plus AI | `PLUSAI_API_KEY` | Pro or Team | Agent session + polling; returns PPTX and PDF |

Safety: keys go only to their own service; polling uses our fixed URLs plus a validated id (never a URL from the response, so no SSRF); only `https://` links reach the page; the server never downloads the decks; `DECK_BUILDS_PER_DAY` (default 40) caps paid credit use. The outline is sent to these companies, so keep private details out of it.
