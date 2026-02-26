# Contributing to Pulse

Thanks for your interest in contributing! Here's how to get started.

## Setup

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend (no local server — deploy to AWS for testing)
cd infra && python3 -m venv .venv && source .venv/bin/activate && pip install .

# Formatting
cd backend && pip install ".[dev]" && ruff format . && ruff check .
cd frontend && npx prettier --write "src/**/*.{js,svelte}"
```

## Making Changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Run formatters (`ruff` for Python, `prettier` for frontend)
4. Build the frontend: `cd frontend && npm run build`
5. Test your changes by deploying to your own AWS account
6. Open a pull request with a clear description

## Guidelines

- Keep it minimal — every line of code should earn its place
- Follow existing patterns and naming conventions
- Backend: raw Python + boto3, no frameworks
- Frontend: Svelte 5 runes (`$state`, `$derived`, `$effect`, `$props`)
- One feature per PR

## Reporting Issues

Use GitHub Issues. Include:
- What you expected vs what happened
- Steps to reproduce
- Browser/OS if it's a frontend issue

## Questions?

Open a discussion or issue — happy to help.
