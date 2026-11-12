# Step 1 drills: tools and teamwork

Do these before building any agents. Each of you does every drill.

## Setup (once)
- Mac: `bash scripts/setup-mac.sh`, then `railway login` and sign in to Cursor.
- Rihanna: accept the invite at https://github.com/campeete/ai-agent-workflow/invitations, then `gh repo clone campeete/ai-agent-workflow`.

## Drill A: see the backend
1. `uv run uvicorn app.main:app --reload`
2. Open http://127.0.0.1:8000/docs and try both endpoints with "Try it out".
3. Watch the terminal: every request prints method, path, status and time.

## Drill B: call it from the editor
1. Open `requests.http` in Cursor.
2. Click "Send Request" above each block.
3. The third request returns 422: the API rejected bad input before your code ran.

## Drill C: review an AI edit
1. Ask Cursor's agent: "Add a GET /time endpoint that returns the server time in ISO format."
2. Read the diff. Accept only what you understand.
3. Add a `/time` call to `requests.http`, test it, then commit and push.

## Drill D: the teammate loop
1. Each of you adds your name under "Team" in `README.md` on your own branch: `git switch -c add-<name>`.
2. Push and open a pull request: `gh pr create --fill`.
3. The other person reviews and merges it on GitHub.
4. `git switch main && git pull`, then use GitLens (File History, inline blame) to see who changed what.

## Drill E: pair live
1. In VS Code (not Cursor), click Live Share and send the link.
2. The other person edits `app/main.py` while you watch; the server reloads on save.

## Done when
- [ ] Both of you can run the API and open `/docs`
- [ ] Both of you sent requests from `requests.http`
- [ ] Each of you merged one pull request the other reviewed
- [ ] You ran one Live Share session
