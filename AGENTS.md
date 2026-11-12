# Instructions for AI coding agents

Read by Cursor, Codex, Claude Code and other agents working in this repo.

## Project
A reusable hackathon AI agent pipeline. Plan: docs/hackathon-workflow-plan.md.
Backend: Python 3.11+, FastAPI, run with `uv run uvicorn app.main:app --reload`.

## Rules
- Never write secrets (API keys, tokens, passwords) into files. Read them from environment variables. This repo is public.
- Validate all request input with Pydantic models and Field limits.
- Keep endpoints small. Every new endpoint gets a matching request in requests.http.
- Do not run git push, deploy, or delete commands. Leave those to the human.
- Explain each change in plain English: what it does and why.
