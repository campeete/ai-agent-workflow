# Hackathon AI Agent Workflow

> Source: Claude Doc "Hackathon AI Agent Workflow" (https://claude.ai/artifact/SNwc8zyjU5nnbvm38YFL8H), last updated 2026-11-11.

A plan for a reusable agent pipeline Cameron can bring to any hackathon, anywhere. **Status:** planning only. The build happens in a later session.

## Agents

| Step | Agent | Input | Output |
|---|---|---|---|
| 1 | Brief reader | Track challenge statements | Requirements, judging criteria, track fit |
| 2 | Repo reader | Code and commits | Summary of the parts, data flow and endpoints |
| 3 | Visuals agent | Repo summary | Architecture diagram, flow visual |
| 4 | Slides agent | Summary plus visuals | Presentation deck |
| 5 | Progress reporter | Git commits | Plain-English updates for teammates |

## Where it runs

| Part | Choice | Why |
|---|---|---|
| Main machine | MacBook | Works at any venue, in any country |
| Mac mini via Tailscale | Optional extra only | Venue Wi-Fi may block it, and nobody is home to restart it |
| Orchestration | To decide in the build session | Must run on the laptop or in the cloud |

## Lessons from HackUTD 2026 that shape this

- Setup and Git problems cost more time than coding: have everything installed and signed in before the event.
- Agree the API contract in the first hour.
- Lock the concept early.
- Make the backend visible: FastAPI /docs, agent step logs, architecture diagram, a live security check.
- Work in VS Code (REST Client, Pylance, GitLens, Live Share), not a bare terminal.

## Tools

| Tool | Use | Why |
|---|---|---|
| Claude | Talking ideas through at length, planning, feature lists, specs | Best for long, detailed thinking out loud |
| Cursor | Main editor: code, AI agent edits, colour-coded diffs | VS Code base, so teammates can see exactly what changed |
| Handoff | Claude turns each plan into a written brief (requirements, API contract, tasks) | Any teammate's agent can pick it up: Cursor, Codex, Claude Code or others |

## Hosting: deploy first

In hour 1, put a near-empty skeleton live with every piece connected and share one link. Every push updates it, so the team always tests the same version. Don't rely on same-Wi-Fi sharing: venue networks usually block laptop-to-laptop traffic, and that's what broke at HackUTD.

| Piece | Host | Note |
|---|---|---|
| Frontend | Railway | One tool keeps it simple; use Vercel only if many people push UI and need preview links |
| Agent (always running) | Railway | Keeps working when every laptop is closed |
| Database | Hosted SpacetimeDB (Maincloud), when using that track | Never a teammate's laptop |
| Secrets | Each host's environment variables | Never in the repo |

Deployment and infrastructure are Cameron's lane (he owned them at HackUTD too).

## Practice project (hypothetical)

Tracks: Toyota "The Smartest Next Move", Capital One "Best Use of Nessie", NVIDIA "Nemotron Beyond a Chatbot". A Nemotron agent uses Nessie banking data, public data (NHTSA, fueleconomy.gov, Federal Reserve rates) and live answers from judges to recommend a customer's smartest next move.

| Role | Owner |
|---|---|
| API and integration | Cameron |
| Security and infrastructure | Cameron |
| AI and agent | Shared, Cameron leads |
| Data and logic | Rihanna |
| Frontend (AI-built) | Rihanna |

## Open for the build session

- Which tool connects the agents
- Which models, local or cloud
- What each agent's output looks like
- Testing it end to end before the next hackathon
