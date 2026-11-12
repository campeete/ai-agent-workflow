# Using Cursor (and VS Code)

Cursor is VS Code plus an AI agent. Layout, shortcuts and extensions are the same in both.
If a shortcut below doesn't work in your version, press Cmd+Shift+P and type the action's name.

## Open the project
`cursor ~/ai-agent-workflow` (or `open -a Cursor ~/ai-agent-workflow`). VS Code: `code ~/ai-agent-workflow`.
First time: Cursor asks to install the recommended extensions from `.vscode/extensions.json`. Say yes.

## The screen
| Area | What it shows | Toggle |
|---|---|---|
| Left sidebar | Files, search, Source Control (git), extensions | Cmd+B |
| Middle | Your code; split it with Cmd+\ | |
| Bottom panel | Terminal, problems, debug output | Ctrl+` |
| Right panel (Cursor) | AI chat and agent | Cmd+L / Cmd+I |

## Everyday shortcuts
| Do this | Keys |
|---|---|
| Open any file by name | Cmd+P |
| Run any command | Cmd+Shift+P |
| Search the whole project | Cmd+Shift+F |
| Go to where a function is defined | Cmd+click it |
| Start the API (task "Run API") | Cmd+Shift+B |
| Start the API in the debugger | F5 |
| See your git changes | Cmd+Shift+G |

## The AI features, from smallest to biggest
1. **Tab:** grey suggestions while you type. Tab accepts, Esc ignores.
2. **Cmd+K:** select some code, describe a change, it edits just that part.
3. **Cmd+L (Ask):** chat about the code. Good for "explain this file" without changing anything.
4. **Cmd+I (Agent):** does multi-file work and can run commands. Most powerful, so review the most.

## Reviewing an agent's changes (the important part)
- Red lines are removed, green lines are added. Read every one.
- Accept or reject each change separately; you don't have to take all of it.
- If you don't understand a line, ask in Cmd+L: "why did you add this?"
- Check the Source Control panel (Cmd+Shift+G) before committing: it lists every file that changed.
- The agent follows `AGENTS.md`. If it breaks a rule there, reject the change.

## Safety settings to check once
- **Privacy Mode:** Cursor Settings, General. Turn it on so your code isn't stored by Cursor.
- **Command approval:** in the Agent settings, make sure the agent asks before running terminal commands.
- **.cursorignore:** files listed there (like `.env`) are never read by the AI.

## Practice (15 minutes)
1. Cmd+L: "Explain app/main.py line by line." Compare with what you think it does.
2. Put a breakpoint (click left of the line number) inside `echo`, press F5, send the echo request from `requests.http`. Inspect `body` in the debug panel, then press F5 to continue.
3. Cmd+I: "Add a GET /time endpoint that returns the server time in ISO format, and add a request for it in requests.http." Review, accept, test.
