# Agents

Stubs for the five agents in the [workflow plan](hackathon-workflow-plan.md). Each `run()` returns placeholder data.

| Step | File | Input | Output | Status |
|---|---|---|---|---|
| 1 | `agents/brief_reader.py` | Track challenge statements | Requirements, judging criteria, track fit | stub |
| 2 | `agents/repo_reader.py` | Code and commits | Summary of the parts, data flow and endpoints | stub |
| 3 | `agents/visuals.py` | Repo summary | Architecture diagram, flow visual | stub |
| 4 | `agents/slides.py` | Summary plus visuals | Presentation deck | stub |
| 5 | `agents/progress_reporter.py` | Git commits + chosen models | One plain-English update per model | live (multi-model) |

`POST /pipeline/run` calls steps 1-4 in order. The brief reader and the repo reader use the request body. The repo summary is passed to the visuals agent, and that summary plus the visuals are passed to the slides agent. The progress reporter stays separate: `POST /agents/progress_reporter/run` with a list of commit messages.

Names used in `/agents/{name}/run` are `brief_reader`, `repo_reader`, `visuals`, `slides`, and `progress_reporter`. An unknown name returns 404.
