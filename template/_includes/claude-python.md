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

## Repository layout, and why

Every file and directory the Python template creates, what goes in it, and whether it is a real
convention or just a choice. The distinction matters: some of these have a technical reason and
breaking them causes real bugs. Others are habit, and you should feel free to disagree.

```
.
├── CLAUDE.md                 instructions the AI assistant reads every session
├── README.md                 instructions a human reads
├── pyproject.toml            project definition: dependencies, build, tool config
├── uv.lock                   exact versions, so every machine installs the same thing
├── .python-version           pins the interpreter
├── .env.example              every environment variable the app reads, with no values
├── .pre-commit-config.yaml   checks that run before each commit
├── src/{{ package_name }}/            the application code
├── tests/                    tests for it
├── scripts/                  one-shot operational scripts
├── docs/                     long-form documentation
└── .github/workflows/        CI: what runs on every push
```

### The ones with a real technical reason

#### `src/{{ package_name }}/` and why not just `{{ package_name }}/`

This is the **src layout**, and it is the current Python packaging recommendation.

The alternative, putting your package at the top level, has a subtle failure. When you run tests
from the project root, Python finds your package in the current directory and imports it from
there, whether or not the package is correctly installable. Packaging mistakes stay invisible
until someone installs it elsewhere and it breaks.

With `src/`, the current directory contains no importable package. `import myapp` only works if
the package is installed. Your tests therefore exercise the same thing your users get.

The `uv_build` backend expects this layout by default. Configuration is only needed when the
package name differs from the project name:

```toml
[tool.uv.build-backend]
module-name = "myapp"
```

**Verdict: real convention, adopt it.** The failure it prevents shows up at the worst possible
moment.

#### `tests/` outside `src/`

Tests sit beside the package, not inside it, so they are not shipped to whoever installs your
code. Nobody wants your test fixtures in their site-packages.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Verdict: real convention.** Both parts, the name and the position outside the package.

#### `pyproject.toml` and `uv.lock`

`pyproject.toml` is the single file describing the project: dependencies, build system, and
configuration for ruff and pytest. It replaced the older scatter of `setup.py`,
`setup.cfg`, `requirements.txt`, and per-tool config files. Keep tool config here; a stray
`pytest.ini` or `.flake8` splits the truth across two places.

`uv.lock` records the exact resolved version of every dependency, transitive ones included.
`pyproject.toml` says "roughly this"; the lock file says "precisely this". Commit both. CI runs
`uv sync --locked`, which fails if the two disagree instead of quietly re-resolving.

**Verdict: the standard. There is no live alternative.**

#### `.python-version`

One line naming the interpreter. uv reads it and installs that version if it is missing, so every
machine and the CI runner test against the same Python. `requires-python` in `pyproject.toml` is
the floor you promise users; `.python-version` is what you develop on.

**Verdict: real convention for applications.** A library tested across several versions leaves
the matrix to CI instead.

#### `.github/workflows/`

Not a choice at all. GitHub Actions only reads workflow files from this exact path. Put them
anywhere else and nothing runs.

**Verdict: mandatory.**

### The ones that are common convention

#### `.env.example`

A list of every environment variable the app reads, with the values blank. The real `.env` is
gitignored, so without this file a new clone has no way to know what configuration it needs
except by reading the settings code.

Keep it in step with the `pydantic-settings` class. A variable the app reads but this file omits
is a setup bug waiting for the next person.

**Verdict: common convention, and cheap enough to always do.**

#### `.pre-commit-config.yaml`

Runs ruff before each commit lands. The point is the fast feedback loop: a lint error caught at
commit time costs seconds, the same error caught in CI costs a push and a wait.

It does not replace CI. Hooks can be skipped with `--no-verify`, and CI cannot.

**Verdict: common convention. The filename is fixed by the tool.**

#### `scripts/`

One-shot operational tools: seed data, probe an API, run a migration by hand. Things a person
runs occasionally.

The line worth holding: if the application imports it, it belongs in `src/`. If it is only ever
run directly by a person, it belongs here. Scripts that quietly become dependencies are a common
source of mess.

**Verdict: common convention.**

#### `docs/`

Long-form documentation that does not belong in the README: architecture decisions, runbooks,
design notes.

A README should be readable in one sitting. Everything that would bloat it past that goes here,
and the README links across.

**Verdict: common convention.**

### The ones that are just choices

#### `.claude/` and `CLAUDE.md`

Configuration for the AI assistant: permission rules, hooks, project instructions. Tool-specific,
and it would disappear along with the tool.

**Verdict: a choice, and a temporary one.**

### Directories to add only when needed

The template leaves these out. Add each one the day the project needs it, not before.

| Directory | When it appears | Why it sits outside `src/` |
|---|---|---|
| `migrations/` | The project gets a database with a schema that changes | Schema history is not application code, and each file replays in order against any environment |
| `frontend/` | There is a web UI | Different language, tooling, and build. Same repo is the right default at small scale |
| `evals/` | The code calls an LLM | Evals hit a real model, so they are slow and cost money. The normal test suite has to stay fast |

### The general rule underneath all of this

Directories separate things by **lifecycle**, not by type.

Application code, tests, operational scripts, and documentation change for different reasons, on
different schedules, with different consequences when wrong. Keeping them apart means a change to
one does not force you to reason about the others.

That is also why `src/` contains only what ships. Everything outside it exists to build, test,
run, or explain the thing inside it.

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

---

# Remaining setup

The generator already did the scaffold: layout, {% if use_python %}uv lockfile, ruff and pytest config, {% endif %}pre-commit hooks, `.env`, {% if use_github_actions %}CI, {% endif %}and the first commit.

{% if not create_github_repo -%}
- [ ] Create the GitHub repo and push: `gh repo create {{ github_owner }}/{{ project_name }} --private --source . --remote origin --push`
{% endif -%}
{%- if use_python -%}
- [ ] Show clean output from `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`
{% endif -%}
- [ ] Prove the leak checks fire: stage a scratch file containing a fake personal email, show `uvx pre-commit run --files <file>` failing on gitleaks, then delete the file
{% if use_github_actions -%}
- [ ] Open a trivial PR and show every CI job green
- [ ] Branch protection on main: PR plus passing CI required, `enforce_admins` on or it will not stop the repo owner. Needs GitHub Pro on a private repo; the API returns 403 on the free plan
{% endif -%}
- [ ] README: replace the purpose line if it is still the placeholder
