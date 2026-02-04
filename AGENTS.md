# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the entry point for running Inkling.
- `core/` contains the primary Python modules (personality, display, brain, tasks, scheduler, storage).
- `modes/` holds the SSH and web UI implementations.
- `mcp_servers/` contains MCP tool servers (tasks, filesystem, system).
- `tests/` and top-level `test_*.py` files contain pytest suites.
- `docs/` and `reference/` hold user and developer documentation.
- `assets/` stores images and supporting resources; `deployment/` contains service configs.

## Build, Test, and Development Commands
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py --mode ssh
python main.py --mode web  # Web UI at http://localhost:8081
python main.py --mode demo
INKLING_DEBUG=1 python main.py --mode ssh

pytest
pytest tests/test_tasks.py -xvs
pytest --cov=core --cov-report=html
python -m py_compile core/brain.py
```

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indentation and a 100-char line limit.
- Use type hints and concise docstrings for public functions/classes.
- TypeScript (if used) follows 2-space indentation, `const` over `let`, and JSDoc comments.
- Naming: `snake_case` for Python functions/vars, `PascalCase` for classes, `camelCase` for JS/TS.

## Testing Guidelines
- Tests use `pytest` with `pytest-asyncio` for async coverage.
- Name test files `test_*.py` and place them in `tests/` unless they are integration-focused at repo root.
- Target coverage: core modules at ~80%+ (per contributing docs). Add tests for new features.

## Commit & Pull Request Guidelines
- Git history favors short, descriptive subjects (e.g., `Add`, `Fix`, `Update`), often lowercase.
- Prefer a verb-first subject line and add a body when rationale or steps matter.
- Include issue references when relevant (e.g., `Fixes #123`).
- PRs should include: what changed, why, how to test, screenshots for UI changes, and doc updates.
- Branch naming examples: `feature/add-task-stats`, `fix/display-refresh`.

## Configuration & Secrets
- Use `config.local.yml` for local overrides; keep `config.yml` as the base template.
- Store API keys in `.env` or environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `COMPOSIO_API_KEY`, `SERVER_PW`).
- Do not commit secrets or machine-specific configs.

## Agent Notes
- Read `CLAUDE.md` for authoritative commands, ports, and architecture notes.
- Social/cloud features are removed; this repository is local-first.
