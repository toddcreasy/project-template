# Repository layout, and why

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
├── src/<package>/            the application code
├── tests/                    tests for it
├── scripts/                  one-shot operational scripts
├── docs/                     long-form documentation
└── .github/workflows/        CI: what runs on every push
```

---

## The ones with a real technical reason

### `src/<package>/` and why not just `<package>/`

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

### `tests/` outside `src/`

Tests sit beside the package, not inside it, so they are not shipped to whoever installs your
code. Nobody wants your test fixtures in their site-packages.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Verdict: real convention.** Both parts, the name and the position outside the package.

### `pyproject.toml` and `uv.lock`

`pyproject.toml` is the single file describing the project: dependencies, build system, and
configuration for ruff and pytest. It replaced the older scatter of `setup.py`,
`setup.cfg`, `requirements.txt`, and per-tool config files. Keep tool config here; a stray
`pytest.ini` or `.flake8` splits the truth across two places.

`uv.lock` records the exact resolved version of every dependency, transitive ones included.
`pyproject.toml` says "roughly this"; the lock file says "precisely this". Commit both. CI runs
`uv sync --locked`, which fails if the two disagree instead of quietly re-resolving.

**Verdict: the standard. There is no live alternative.**

### `.python-version`

One line naming the interpreter. uv reads it and installs that version if it is missing, so every
machine and the CI runner test against the same Python. `requires-python` in `pyproject.toml` is
the floor you promise users; `.python-version` is what you develop on.

**Verdict: real convention for applications.** A library tested across several versions leaves
the matrix to CI instead.

### `.github/workflows/`

Not a choice at all. GitHub Actions only reads workflow files from this exact path. Put them
anywhere else and nothing runs.

**Verdict: mandatory.**

---

## The ones that are common convention

### `.env.example`

A list of every environment variable the app reads, with the values blank. The real `.env` is
gitignored, so without this file a new clone has no way to know what configuration it needs
except by reading the settings code.

Keep it in step with the `pydantic-settings` class. A variable the app reads but this file omits
is a setup bug waiting for the next person.

**Verdict: common convention, and cheap enough to always do.**

### `.pre-commit-config.yaml`

Runs ruff before each commit lands. The point is the fast feedback loop: a lint error caught at
commit time costs seconds, the same error caught in CI costs a push and a wait.

It does not replace CI. Hooks can be skipped with `--no-verify`, and CI cannot.

**Verdict: common convention. The filename is fixed by the tool.**

### `scripts/`

One-shot operational tools: seed data, probe an API, run a migration by hand. Things a person
runs occasionally.

The line worth holding: if the application imports it, it belongs in `src/`. If it is only ever
run directly by a person, it belongs here. Scripts that quietly become dependencies are a common
source of mess.

**Verdict: common convention.**

### `docs/`

Long-form documentation that does not belong in the README: architecture decisions, runbooks,
design notes.

A README should be readable in one sitting. Everything that would bloat it past that goes here,
and the README links across.

**Verdict: common convention.**

---

## The ones that are just choices

### `.claude/` and `CLAUDE.md`

Configuration for the AI assistant: permission rules, hooks, project instructions. Tool-specific,
and it would disappear along with the tool.

**Verdict: a choice, and a temporary one.**

---

## Directories to add only when needed

The template leaves these out. Add each one the day the project needs it, not before.

| Directory | When it appears | Why it sits outside `src/` |
|---|---|---|
| `migrations/` | The project gets a database with a schema that changes | Schema history is not application code, and each file replays in order against any environment |
| `frontend/` | There is a web UI | Different language, tooling, and build. Same repo is the right default at small scale |
| `evals/` | The code calls an LLM | Evals hit a real model, so they are slow and cost money. The normal test suite has to stay fast |

---

## The general rule underneath all of this

Directories separate things by **lifecycle**, not by type.

Application code, tests, operational scripts, and documentation change for different reasons, on
different schedules, with different consequences when wrong. Keeping them apart means a change to
one does not force you to reason about the others.

That is also why `src/` contains only what ships. Everything outside it exists to build, test,
run, or explain the thing inside it.
