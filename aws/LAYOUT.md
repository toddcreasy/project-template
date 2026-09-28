# Repository layout, and why

Every directory here, what goes in it, and whether it is a real convention or just a choice. That
distinction matters: some of these have a technical reason and breaking them causes real bugs.
Others are habit, and you should feel free to disagree.

```
.
├── CLAUDE.md              instructions the AI assistant reads every session
├── README.md              instructions a human reads
├── pyproject.toml         Python project definition: dependencies, tools, build
├── uv.lock                exact versions, so every machine installs the same thing
├── .env.example           every environment variable the app reads, with no values
├── .python-version        pins the Python version
├── Dockerfile             how the backend is packaged into a container
├── src/<package>/         the application code
├── tests/                 tests for it
├── infra/                 the cloud infrastructure, as code
├── migrations/            database schema changes, versioned
├── frontend/              the web UI
├── evals/                 quality tests for AI behaviour
├── scripts/               one-shot operational scripts
├── docs/                  long-form documentation
└── .github/workflows/     CI: what runs on every push
```

---

## The ones with a real technical reason

### `src/<package>/` and why not just `<package>/`

This is called the **src layout**, and it is the current Python packaging recommendation.

The alternative, putting your package at the top level, has a subtle failure. When you run tests
from the project root, Python finds your package in the current directory and imports it from
there, whether or not the package is correctly installable. Packaging mistakes stay invisible
until someone installs it elsewhere and it breaks.

With `src/`, the current directory contains no importable package. `import myapp` only works if
the package is genuinely installed. Your tests therefore exercise the same thing your users get.

It costs one line of configuration:

```toml
[tool.uv.build-backend]
module-root = "src"
module-name = "myapp"
```

**Verdict: real convention, adopt it.** The failure it prevents is the kind you find at the worst
possible moment.

### `tests/` outside `src/`

Tests sit beside the package, not inside it, so they are not shipped to whoever installs your
code. Nobody wants your test fixtures in their site-packages.

Configure the runner to look there:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Verdict: real convention.** Both parts, the name and the position outside the package.

### `.github/workflows/`

Not a choice at all. GitHub Actions only reads workflow files from this exact path. Put them
anywhere else and nothing runs.

**Verdict: mandatory.**

### `pyproject.toml`

The single file describing the project: dependencies, build system, and configuration for tools
like the linter, the formatter, and the test runner. It replaced the older scatter of `setup.py`,
`setup.cfg`, `requirements.txt`, and per-tool config files.

Paired with a **lock file** (`uv.lock`), which records the exact resolved version of every
dependency including transitive ones. `pyproject.toml` says "roughly this"; the lock file says
"precisely this". Commit both. The lock file is what makes a build reproducible.

**Verdict: the standard. There is no live alternative.**

### `migrations/`

A database has a shape, and that shape changes as the project grows. Editing tables by hand does
not survive contact with a second environment or a second person.

A migration tool records each change as a numbered file, so any database can be brought from any
version to any other by replaying them in order. Each file has an `upgrade` and a `downgrade`.

The name is configured, not fixed:

```ini
script_location = %(here)s/migrations
```

Alembic's own default is `alembic/`. `migrations/` is more descriptive and just as common.

**Verdict: the tool is essential, the directory name is yours.**

---

## The ones that are common convention

### `infra/`

Cloud infrastructure described in code, so that creating it is repeatable and reviewable. Here it
is a CDK app, meaning Python that generates the infrastructure definition.

Two reasons it sits beside `src/` rather than inside it. It is not part of the application, so it
should not ship when the package is installed. And it has different dependencies, which you do not
want in your production container.

Common alternative names: `cdk/`, `terraform/`, `deploy/`, `ops/`.

**Verdict: widely used, not enforced. Keeping infrastructure out of the application package is the
part that matters.**

### `scripts/`

One-shot operational tools. Check a connection, seed data, probe an API, verify a teardown. Things
you run by hand occasionally.

The line worth holding: if something is imported by the application, it belongs in `src/`. If it
is only ever run directly by a person, it belongs here. Scripts that quietly become dependencies
are a common source of mess.

**Verdict: common convention.**

### `docs/`

Long-form documentation that does not belong in the README. Setup history, architecture decisions,
runbooks.

The reason to have it: a README should be readable in one sitting. Everything that would bloat it
past that goes here, and the README links across.

**Verdict: common convention.**

---

## The ones that are just choices

### `frontend/`

The web UI, kept in the same repository as the backend. This is a **monorepo** decision, and it is
genuinely arguable.

**Why together.** One clone, one branch, one pull request when a change spans both sides. An API
change and the UI change that depends on it land at the same moment, so the two are never out of
step. For one or two people, this is almost always right.

**Why separate.** Different languages, different tooling, different deploy cadence, and CI that
rebuilds everything when only one side changed. At a size where separate teams own each side, the
coupling starts to cost more than it saves.

**Verdict: a real fork in the road. Monorepo is the right default for a small project.**

### `evals/`

Tests for AI behaviour, as opposed to tests for code. Ordinary tests assert exact outputs. A model
produces different words each time, so these assert on properties instead: did it call the right
tool, does the answer contain the right substance, did it refuse when it should.

They are separate from `tests/` for a practical reason. They call a real model, so they cost money
and take a minute rather than a second. The normal test suite has to stay fast enough that nobody
avoids running it.

**Verdict: no established convention. This is a young practice and naming has not settled.**

### `.claude/`

Configuration for the AI assistant: permission rules, hooks, project-specific writing rules.
Tool-specific, and it would disappear along with the tool.

**Verdict: a choice, and a temporary one.**

---

## The general rule underneath all of this

Directories separate things by **lifecycle**, not by type.

Application code, infrastructure, database migrations, and operational scripts all change for
different reasons, on different schedules, reviewed by different eyes, with different consequences
when wrong. Keeping them apart means a change to one does not force you to reason about the
others.

That is also why `src/` contains only what ships. Everything outside it exists to build, test,
deploy, or explain the thing inside it.
