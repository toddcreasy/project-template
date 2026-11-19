# CLAUDE.md

{{ description or project_name }}

Generated from toddcreasy/project-template. `uvx copier update --trust` pulls later template
changes into this repo.

## How Claude Code must use this file

1. If the "Remaining setup" section below exists, finish it first, one item at a time, showing evidence for each. Delete the section once every box is checked.
2. Every changed line must trace to the request or a checklist item. No extra features, no speculative abstractions.
3. If something fails, diagnose before retrying. Read the error, check assumptions, try a focused fix. Ask the maintainer only when genuinely stuck after investigation.

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

{%- if use_python %}
### Python
- Use `uv` for everything: `uv sync`, `uv run <cmd>`, `uv add <pkg>`. Never activate a venv manually; `uv run` handles it. Never use pip with `--break-system-packages`.
- Always `pyproject.toml`. Always a `.env.example` with every variable the app reads.
- Settings load through `pydantic-settings`. Secrets are `SecretStr`. Locally they come from `.env`; deployed they come from the host's secret store. `.env` is gitignored.
{%- endif %}

### Coding principles
- Don't add features, refactors, or improvements beyond what was asked.
- Don't add comments, docstrings, or type annotations to code you didn't change.
- No helpers or abstractions for one-time operations. Three similar lines beat a premature abstraction.
- Validate only at system boundaries (user input, external APIs). Trust internal code.
- When editing: match existing style, don't touch adjacent code, remove only what YOUR change made unused. Mention unrelated dead code; don't delete it.
- No OWASP top 10 vulnerabilities. Fix insecure code you wrote immediately.

{%- if use_python %}
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

`docs/layout.md` explains every file and directory, and which are real conventions rather than
choices. Read it before adding a top-level directory or moving code between `src/`, `scripts/`,
and `tests/`.

## Conventions

- src layout. `import {{ package_name }}` works only when installed, so tests exercise what users get.
- Tool config lives in `pyproject.toml`. No `setup.cfg`, `pytest.ini`, or `.flake8`.
- Unit tests make no network calls. Anything that does is marked and skipped by default.
- Use `logging` in `src/`, never `print`. Configure handlers once at the entrypoint.
- Pin dependency lower bounds in `pyproject.toml`; `uv.lock` pins exact versions.
{%- endif %}

## Secrets and personal info

- `.env` holds real values and is gitignored. `.env.example` lists every variable with no values; the tags after `#` mark which values must never be committed.
- `python3 scripts/setup_env.py` asks for missing values, writes `.env`, and copies it to `{{ env_store_dir }}/{{ project_name }}.env`. `--pull` restores `.env` from that copy on a fresh clone. When the app starts reading a new variable, add it to `.env.example` first, then rerun the script.
- Pre-commit blocks a commit containing a known key format, a personal email, phone number, SSN, or street address (`.gitleaks.toml`), or any secret or private value from `.env` (`scripts/check_env_leaks.py`). CI repeats the gitleaks scan over the full history.
- Never bypass these with `--no-verify`. A real false positive gets `gitleaks:allow` on that line, nothing broader.
{%- if use_github_actions %}
- The CI `secrets` job scans the full history and fails any new commit whose author or committer email is not a GitHub noreply address. Never remove or weaken it.
{%- endif %}

---

# Remaining setup

The generator already did the scaffold: layout, {% if use_python %}uv lockfile, ruff and pytest config, {% endif %}pre-commit hooks, `.env`, {% if use_github_actions %}CI, {% endif %}and the first commit.

{% if not create_github_repo -%}
- [ ] Create the GitHub repo and push: `gh repo create {{ github_owner }}/{{ project_name }} --private --source . --remote origin --push`
{% endif -%}
{%- if use_python -%}
- [ ] Show clean output from `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`
{% endif -%}
{% if use_postgres -%}
- [ ] Local Postgres: `docker compose up -d --wait`, then show `docker compose exec db psql -U {{ project_name | replace('-', '_') }} -c "select extversion from pg_extension where extname = 'vector'"` returning a version
{% endif -%}
- [ ] Prove the leak checks fire: stage a scratch file containing a fake personal email, show `uvx pre-commit run --files <file>` failing on gitleaks, then delete the file
{% if use_github_actions -%}
- [ ] Open a trivial PR and show every CI job green
- [ ] Branch protection on main: PR plus passing CI required, `enforce_admins` on or it will not stop the repo owner. Needs GitHub Pro on a private repo; the API returns 403 on the free plan
{% endif -%}
- [ ] README: replace the purpose line if it is still the placeholder
