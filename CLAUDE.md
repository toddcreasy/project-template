# CLAUDE.md

Python project template. Drop this file into a fresh repo, fill in the placeholders, and Claude
Code scaffolds the project in two phases, stopping for review after each.

## Fill these in before first use

Replace every placeholder, then delete this section. A placeholder left in place will be read as a
literal value.

| Placeholder | What it is |
|---|---|
| `<PROJECT_NAME>` | Short kebab-case name for the repo and distribution |
| `<PACKAGE>` | Python package name under `src/`, usually `<PROJECT_NAME>` with underscores |
| `<PYTHON_VERSION>` | Minimum Python, e.g. `3.12`, pinned in `.python-version` |

## How Claude Code must use this file

1. Work through the setup phases in order. Never skip ahead.
2. Complete every checklist item in a phase, then run the STOP gate verification.
3. At each STOP gate: show the evidence (command output), mark the checkboxes done by editing this file, then wait for maintainer approval before starting the next phase.
4. If a phase fails, diagnose before retrying. Read the error, check assumptions, try a focused fix. Ask the maintainer only when genuinely stuck after investigation.
5. Every changed line must trace to a checklist item. No extra features, no speculative abstractions.
6. Once STOP gate 1 passes, delete the "Setup phases" section. The repo itself is the record.

## Operating rules

Direct. Evidence-first. Skip preamble.

### Writing style
- Never use em dashes or en dashes in any written output. Use commas, periods, semicolons, or restructure.
- Write in the maintainer's voice for all prose output. The voice profile is `~/.claude/rules/writing-voice.md`. Read it; do not edit it. No generic LLM prose.
- Keep all prose short and direct. State the point; skip "actually matters" style framing.

### Core protocol
- Evidence: read files before stating facts about them. Verify data claims against source.
- Action: default to implementation. Explain architecture decisions; act on details.
- Output: no trailing summaries after actions. The maintainer reads diffs directly.
- Safety: no force push. No `rm -rf`; use `trash`. Ask before bulk operations. Never commit secrets, API keys, or credentials.
- Comms: never send email, messages, or any external communication without showing a draft and getting explicit approval.
- Parallel: launch independent subagents in a single message when tasks are independent. Delegate mechanical exploration; preserve main context for decisions.

### Python
- Use `uv` for everything: `uv sync`, `uv run <cmd>`, `uv add <pkg>`. Never activate a venv manually; `uv run` handles it. Never use pip with `--break-system-packages`.
- Always `pyproject.toml`. Always a `.env.example` with every variable the app reads.
- Settings load through `pydantic-settings`. Secrets are `SecretStr`. Locally they come from `.env`; deployed they come from the host's secret store. `.env` is gitignored.

### Coding principles
- Don't add features, refactors, or improvements beyond what was asked.
- Don't add comments, docstrings, or type annotations to code you didn't change.
- No helpers or abstractions for one-time operations. Three similar lines beat a premature abstraction.
- Validate only at system boundaries (user input, external APIs). Trust internal code.
- When editing: match existing style, don't touch adjacent code, remove only what YOUR change made unused. Mention unrelated dead code; don't delete it.
- No OWASP top 10 vulnerabilities. Fix insecure code you wrote immediately.

## Toolchain

| Job | Tool | Why |
|---|---|---|
| Installs, envs, lockfile | uv | One fast tool replacing pip, venv, and poetry. Reproducible installs from `uv.lock`. |
| Build backend | `uv_build` | Native src-layout support; no setuptools config. |
| Lint + format | ruff | One binary, milliseconds, so checks never feel optional. |
| Tests | pytest | The standard runner. Every STOP gate needs a runnable proof. |
| Config | pydantic-settings | Typed settings from env vars; bad config fails at startup, not deep in a call. |
| Pre-commit | pre-commit | Runs ruff before each commit so broken code never lands. |
| CI | GitHub Actions | Lives beside the code, free tier covers a personal project. |

## Repository layout

```
.
├── CLAUDE.md              # this file
├── README.md              # what it is and how to run it
├── pyproject.toml         # project definition and tool config
├── uv.lock                # exact versions; commit it
├── .python-version        # pinned interpreter
├── .env.example           # every env var the app reads, no values
├── src/<PACKAGE>/         # application code, the only thing that ships
├── tests/                 # fast tests, no network
├── scripts/               # one-shot operational scripts, never imported
├── docs/                  # long-form docs the README links to
└── .github/workflows/     # CI; GitHub reads this exact path only
```

Add directories only when the project needs them (`migrations/`, `frontend/`, `evals/`). What each
directory is for, which are real conventions, and why `src/` exists at all: see `LAYOUT.md`.

## Conventions

- src layout. `import <PACKAGE>` works only when installed, so tests exercise what users get.
- Tool config lives in `pyproject.toml`. No `setup.cfg`, `pytest.ini`, or `.flake8`.
- Unit tests make no network calls. Anything that does is marked and skipped by default.
- Use `logging` in `src/`, never `print`. Configure handlers once at the entrypoint.
- Pin dependency lower bounds in `pyproject.toml`; `uv.lock` pins exact versions.

---

# Setup phases

## Phase 0: Scaffold

Goal: a clean repo that lints, tests, and installs from lockfile.

- [ ] `uv init --package` with `pyproject.toml`: project metadata, `requires-python = ">=<PYTHON_VERSION>"`, `uv_build` backend, `.python-version`
- [ ] Dev deps via `uv add --dev`: `ruff`, `pytest`, `pre-commit`
- [ ] `[tool.ruff]` config: line length, target version, lint rules (at least `E`, `F`, `I`, `B`, `UP`, `SIM`); format enabled
- [ ] `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, a `network` marker skipped by default
- [ ] `.pre-commit-config.yaml` with ruff lint and format hooks; `uv run pre-commit install`
- [ ] Directory layout created as above, with `src/<PACKAGE>/__init__.py` and one passing test in `tests/`
- [ ] `.gitignore` (Python, `.venv`, `.env`, caches, IDE)
- [ ] `.env.example` created (empty until the app reads a variable)
- [ ] README: project name, one-line purpose, setup commands (`uv sync`, `uv run pytest`)
- [ ] Initial commit pushed

STOP gate 0: show clean output from `uv run ruff check .`, `uv run ruff format --check .`,
and `uv run pytest`.

## Phase 1: CI

Goal: every push and pull request runs the same three checks as the local gate.

- [ ] `.github/workflows/ci.yml`: on pull request and push to main, `astral-sh/setup-uv` with caching, `uv sync --locked`, then ruff check, ruff format check, pytest
- [ ] Concurrency group per ref with `cancel-in-progress: true`
- [ ] Branch protection on main: PR plus passing CI required, `enforce_admins` on or it will not stop the repo owner. Needs GitHub Pro on a private repo; the API returns 403 on the free plan

STOP gate 1: open a trivial PR, show the green CI run, merge it.
