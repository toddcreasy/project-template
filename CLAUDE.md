# CLAUDE.md

Project-agnostic infrastructure bootstrap. Drop this file into a fresh repo. Claude Code reads it and builds the full stack in phases, stopping for review after each one. Replace `<PROJECT_NAME>` and `<AWS_REGION>` before starting. Functionality comes later; this file only sets up the platform.

## How Claude Code must use this file

1. Work through the phases in order. Never skip ahead.
2. Complete every checklist item in a phase, then run the STOP gate verification.
3. At each STOP gate: show the evidence (command output, URL, screenshot instruction), mark the checkboxes done by editing this file, then wait for maintainer approval before starting the next phase.
4. If a phase fails, diagnose before retrying. Read the error, check assumptions, try a focused fix. Ask the maintainer only when genuinely stuck after investigation.
5. Every changed line must trace to a checklist item. No extra features, no speculative abstractions.

## Operating rules

Direct. Evidence-first. Skip preamble.

### Writing style
- Never use em dashes or en dashes in any written output. Use commas, periods, semicolons, or restructure.
- Write in the maintainer's voice for all prose output. The voice profile is `.claude/rules/writing-voice.md`. If the file is missing, copy the template from the repo root (`writing-voice.md`) into place and ask the maintainer to review the fill-in sections before writing any external prose. No generic LLM prose.
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
- Settings load through `pydantic-settings`. Secrets are `SecretStr`. Locally they come from `.env`; deployed they come from AWS Secrets Manager or SSM. `.env` is gitignored.

### Coding principles
- Don't add features, refactors, or improvements beyond what was asked.
- Don't add comments, docstrings, or type annotations to code you didn't change.
- No helpers or abstractions for one-time operations. Three similar lines beat a premature abstraction.
- Validate only at system boundaries (user input, external APIs). Trust internal code.
- When editing: match existing style, don't touch adjacent code, remove only what YOUR change made unused. Mention unrelated dead code; don't delete it.
- No OWASP top 10 vulnerabilities. Fix insecure code you wrote immediately.

## Stack decisions

AWS-first. Anything not AWS is listed with the reason AWS cannot fill the slot.

| Slot | Tool | AWS? | If not AWS, why |
|---|---|---|---|
| Infrastructure as code | AWS CDK (Python) | Yes | |
| Models | Amazon Bedrock (Claude family) | Yes | |
| Agent framework | Strands Agents SDK | Yes (AWS open source) | |
| Agent runtime | Bedrock AgentCore Runtime | Yes | |
| Tool access (MCP) | AgentCore Gateway | Yes | |
| Agent observability | AgentCore Observability + CloudWatch | Yes | |
| Production evals | AgentCore Evaluations | Yes | |
| Relational + vector DB | Aurora Serverless v2 PostgreSQL + pgvector | Yes | |
| Object storage | S3 | Yes | |
| Secrets | AWS Secrets Manager | Yes | |
| Auth | Amazon Cognito | Yes | |
| Backend hosting | AWS App Runner (alt: Lambda + API Gateway) | Yes | |
| Frontend hosting | AWS Amplify Hosting | Yes | |
| Cost control | AWS Budgets + cost allocation tags | Yes | |
| Backend framework | FastAPI + Pydantic | No | Language-level tooling. AWS makes no Python web framework. |
| Python toolchain | uv, ruff, pytest | No | Language ecosystem tools. No AWS equivalent exists. |
| DB migrations | Alembic | No | AWS has no schema migration tool for application tables. |
| Dev-loop evals | pydantic-evals golden set in pytest | No | AgentCore Evaluations scores deployed traces. Pre-deploy evals must run locally in seconds. Both are used. |
| Frontend framework | Next.js + React + Tailwind | No | AWS hosts frontends (Amplify) but does not make a frontend framework. |
| Code host + CI runner | GitHub + GitHub Actions | No | The repo lives on GitHub. Actions integrates natively, has a free tier, and assumes an AWS role via OIDC with no stored keys. AWS CodePipeline would add setup and cost for no benefit at this scale. |
| Containers | Docker | No | Open standard. AWS consumes it; it does not replace it. |

Excluded on purpose (wrong scale for a personal project): Kubernetes, Terraform, Snowflake, Databricks, A2A, LiteLLM, dedicated vector databases, WAF-heavy perimeter builds.

## Repository layout

```
.
├── CLAUDE.md              # this file
├── pyproject.toml
├── .env.example
├── src/<PROJECT_NAME>/    # application code (later phases add packages)
├── infra/                 # CDK app: app.py + stacks/
├── frontend/              # Next.js app (Phase 7)
├── evals/                 # golden set + pydantic-evals cases
├── scripts/               # one-shot operational scripts
├── tests/
└── .github/workflows/
```

## Conventions

- One CDK app in `infra/`, one stack per phase concern: `NetworkStack`, `DataStack`, `BackendStack`, `AgentStack`, `FrontendStack`, `OpsStack`.
- Tag every resource: `project=<PROJECT_NAME>`, `env=dev`, `managed-by=cdk`.
- One AWS region: `<AWS_REGION>`. Do not spread resources across regions.
- Model tiering: default to the small Bedrock model tier (Haiku class) for extraction, filtering, and routing. Use the large tier only for final synthesis. Prompt caching on for any repeated prefix. Batch API for offline jobs.
- Log retention: 30 days on every log group. Set it explicitly; the default is forever.

---

# Build phases

## Phase 0: Repo scaffold

Goal: a clean Python repo that lints, tests, and installs from lockfile.

Tools in this phase:
- **uv**: one fast tool for Python installs, environments, and lockfiles. It replaces pip, venv, and poetry. Why: reproducible installs and no manual venv activation.
- **ruff**: linter and formatter in one binary. Why: catches errors and enforces one style in milliseconds, so checks never feel optional.
- **pytest**: the standard Python test runner. Why: every STOP gate in this file needs a runnable proof, and pytest is that proof.
- **pre-commit**: runs ruff and other checks before each commit lands. Why: broken code never enters the repo.

- [ ] `uv init` with `pyproject.toml`: project metadata, Python >= 3.12
- [ ] Add dev deps: `ruff`, `pytest`, `pre-commit`
- [ ] `ruff` config in `pyproject.toml` (lint + format), pre-commit hook wired
- [ ] Directory layout created as above, with placeholder `__init__.py` and one passing placeholder test
- [ ] `.gitignore` (Python, node, `.env`, CDK out, IDE)
- [ ] `.env.example` created (empty vars added as phases introduce them)
- [ ] README stub: project name, one-line purpose, setup commands
- [ ] `.claude/rules/writing-voice.md` in place (copy the template from the repo root; flag the fill-in sections to the maintainer)
- [ ] Initial commit pushed

STOP gate 0: `uv run ruff check .` is clean and `uv run pytest` passes. Show both outputs.

## Phase 1: AWS guardrails before any resources

Goal: spending alarms and deploy identity exist before anything can cost money.

Tools in this phase:
- **AWS CDK**: you describe AWS resources in Python code; `cdk deploy` creates them, `cdk destroy` removes them. Why: the whole infrastructure is versioned in git and rebuildable, and it stays in the language you already use.
- **AWS Budgets**: a monthly spending limit that emails you at thresholds. Why: the number one risk in a personal cloud project is silent spend.
- **Amazon SNS**: AWS's notification service; topics fan out messages to email or other targets. Why: one topic carries every alert in this project.
- **IAM with GitHub OIDC**: IAM is AWS's permission system. OIDC lets GitHub Actions prove its identity to AWS and assume a role for minutes. Why: no long-lived AWS keys stored anywhere, so nothing can leak.
- **Cost allocation tags**: labels on every resource that Cost Explorer can group by. Why: when the bill surprises you, tags tell you which part did it.

- [ ] Confirm AWS account ID and `<AWS_REGION>` with maintainer
- [ ] `infra/` CDK app skeleton (`app.py`, `cdk.json`, stacks package)
- [ ] `cdk bootstrap` the account/region
- [ ] `OpsStack`: AWS Budget with monthly limit (ask maintainer for the number, suggest $30) + SNS email alert at 50/80/100%
- [ ] Cost allocation tags activated for `project` and `env`
- [ ] IAM role for GitHub Actions OIDC (trust policy scoped to this repo), no access keys created
- [ ] Document teardown: `cdk destroy` order in README

STOP gate 1: budget visible in console, maintainer confirms the SNS subscription email arrived, `cdk deploy OpsStack` output shown.

## Phase 2: Data layer

Goal: a Postgres database with vector search, reachable from a local script, credentials in Secrets Manager.

Tools in this phase:
- **Aurora Serverless v2 (PostgreSQL)**: AWS-managed Postgres that scales its compute up and down, including to zero when idle. Why: real Postgres with near-zero cost while you are not using it, and no server patching.
- **pgvector**: a Postgres extension that stores embeddings and runs similarity search. Why: one database handles both normal tables and vector search, so no separate vector product to pay for and operate.
- **AWS Secrets Manager**: stores credentials; apps fetch them at runtime by ARN. Why: passwords never sit in code, `.env` files in git, or CI settings.
- **Amazon S3**: durable object storage for files and documents. Why: pennies per GB and every AWS service reads from it.
- **Alembic**: versioned database schema migrations for Python. Why: schema changes become reviewable files that replay identically in every environment.
- **VPC**: your private network inside AWS. Why: the database gets no public address; only your services can reach it.

- [ ] `DataStack`: VPC (2 AZs, no NAT gateway if avoidable; use isolated subnets + endpoints), Aurora Serverless v2 PostgreSQL
- [ ] Serverless v2 scaling: min capacity 0 ACU (auto-pause) for dev, max 1
- [ ] DB credentials generated into Secrets Manager by CDK
- [ ] `pgvector` extension enabled (`CREATE EXTENSION vector`)
- [ ] S3 bucket for documents (versioned, private, lifecycle rule to Infrequent Access at 30 days)
- [ ] Alembic initialized; migration 001 creates a schema-version table only
- [ ] `scripts/db_check.py`: connects via the secret, runs a vector insert + cosine similarity query
- [ ] `.env.example` updated: `DATABASE_SECRET_ARN`, `AWS_REGION`

STOP gate 2: run `uv run python scripts/db_check.py`; show the round-trip output including a similarity score. Confirm the cluster pauses to 0 ACU after idle (console check).

## Phase 3: Backend API

Goal: a deployed FastAPI service that reaches the database.

Tools in this phase:
- **FastAPI**: the standard modern Python web framework. Type hints define request and response shapes; docs generate themselves. Why: it shares Pydantic models with the agent layer, so one set of types flows through the whole system.
- **Pydantic / pydantic-settings**: data validation from type hints, plus typed config loaded from env vars or Secrets Manager. Why: bad data fails loudly at the boundary instead of deep in a handler.
- **Docker**: packages the app and its dependencies into an image that runs the same everywhere. Why: "works on my machine" becomes "works in App Runner".
- **Amazon ECR**: AWS's private registry that stores those images. Why: App Runner deploys straight from it.
- **AWS App Runner**: give it a container image; it runs it with HTTPS, scaling, and health checks, no servers to manage. Why: the least-effort way to run one small always-on service. (Alternative: Lambda + API Gateway if traffic is rare and cold starts are acceptable.)
- **Amazon CloudWatch**: AWS's built-in logs, metrics, dashboards, and alarms. Why: it is already there; every log line from App Runner lands in it with no setup.

- [ ] `src/<PROJECT_NAME>/api/`: FastAPI app with `GET /health` (static) and `GET /health/db` (runs `SELECT 1`)
- [ ] `pydantic-settings` config module; secrets resolved from Secrets Manager when deployed, `.env` locally
- [ ] Dockerfile (multi-stage, uv-based, non-root user)
- [ ] `BackendStack`: App Runner service from the container image (ECR), VPC connector to Aurora, secret injected as env
- [ ] Structured JSON logging to CloudWatch, retention 30 days
- [ ] Local run documented: `uv run fastapi dev`

STOP gate 3: `curl` both health endpoints on the deployed App Runner URL; show responses. Show one structured log line in CloudWatch.

## Phase 4: Agent layer

Goal: one working agent on Bedrock, deployed to AgentCore Runtime, with visible token usage.

Tools in this phase:
- **Amazon Bedrock**: one AWS API in front of many models (Claude, Nova, Llama, and others), billed per token, with IAM auth and no separate API keys. Why: model access stays inside the AWS account, permissions, and bill.
- **Strands Agents SDK**: AWS's open-source Python agent framework. An agent is a model, a prompt, typed output, and tools; the SDK runs the reasoning loop. Why: first-class Bedrock and AgentCore support, and small enough to read.
- **Bedrock AgentCore Runtime**: a managed place to run agent code, with per-session isolation and support for long-running work. Why: the agent runs server-side with its own identity and scaling, not inside the web backend.
- **Prompt caching**: Bedrock reuses a repeated prompt prefix (system prompt, tool definitions) across calls at a fraction of the token price. Why: agents resend the same prefix constantly; caching is the single cheapest cost fix.

- [ ] Enable Bedrock model access for the chosen Claude models in `<AWS_REGION>` (maintainer action; provide exact console steps)
- [ ] `src/<PROJECT_NAME>/agents/`: one Strands agent, typed output model, one local tool (echo/time), prompt caching enabled
- [ ] Model tiering config: `MODEL_SMALL`, `MODEL_LARGE` env vars; agent defaults to small
- [ ] Token/cost logging per run (structured log fields: input_tokens, output_tokens, cache_read, model)
- [ ] `AgentStack`: deploy the agent to AgentCore Runtime via CDK/CLI
- [ ] `scripts/agent_smoke.py`: invokes the deployed agent, prints typed output + usage

STOP gate 4: run the smoke script; show the typed response and the token usage log line from the deployed runtime.

## Phase 5: Tools over MCP

Goal: the agent reaches the backend through AgentCore Gateway as MCP tools.

Tools in this phase:
- **MCP (Model Context Protocol)**: the open standard for connecting agents to tools and data, adopted by every major AI provider. A tool exposed over MCP works with any compliant agent. Why: tool integrations written once stay portable across frameworks and models.
- **AgentCore Gateway**: takes an existing API or Lambda function and publishes it as MCP tools, with IAM auth and per-tool permissions. Why: the backend stays a plain FastAPI app; the Gateway does the MCP plumbing and enforces who may call what.

- [ ] Expose one backend endpoint (start with `GET /health/db`) as a Gateway MCP tool
- [ ] Gateway auth wired to IAM; least-privilege policy for the agent identity
- [ ] Agent updated: the MCP tool is in its toolset; system prompt mentions when to use it
- [ ] Local dev path documented: how to run the agent against the tool without deploying

STOP gate 5: smoke script shows the agent calling the Gateway tool and returning its result. Show the trace of the tool call.

## Phase 6: Observability and evals

Goal: every agent run is traceable; quality is measurable before deploys.

Tools in this phase:
- **AgentCore Observability**: records every agent run as a trace: each model call, tool call, latency, and token count as spans. Why: without traces, a misbehaving agent is a black box and token waste is invisible.
- **CloudWatch dashboards and alarms**: charts on top of the metrics, plus alerts to the Phase 1 SNS topic. Why: you find out about error spikes and token spend from an email, not from the bill.
- **pydantic-evals**: local eval framework from the Pydantic team. A golden set of inputs with expected typed outputs, scored in seconds under pytest. Why: before any change deploys, you know whether agent quality moved.
- **AgentCore Evaluations**: managed evaluators (response quality, safety, tool usage) that score real production traces continuously. Why: local evals catch regressions before deploy; this catches drift after.

- [ ] AgentCore Observability enabled on the runtime
- [ ] CloudWatch dashboard: agent invocations, errors, latency, daily token totals
- [ ] CloudWatch alarms: error rate and a daily token-spend threshold, both to the Phase 1 SNS topic
- [ ] `evals/`: 10 to 15 golden cases with `pydantic-evals`; assertions on typed output fields
- [ ] Evals run via `uv run pytest evals` and are marked so they can be skipped in fast unit runs
- [ ] AgentCore Evaluations configured with at least response-quality and tool-usage evaluators on production traces

STOP gate 6: show one full trace for an agent run (spans for model calls and tool calls). Show `uv run pytest evals` passing. Show the dashboard.

## Phase 7: Frontend

Goal: a deployed web UI behind sign-in that calls the backend.

Tools in this phase:
- **Next.js + React**: React builds UIs from components; Next.js adds routing, server rendering, and the build system around it. The standard frontend stack. Why: largest ecosystem, best AI-tool support, and non-technical users get a polished app instead of a developer demo.
- **Tailwind CSS**: styling as utility classes in the markup instead of separate CSS files. Why: fast to build, consistent by default, and the style every component library assumes.
- **Amazon Cognito**: managed sign-up, sign-in, and password reset. It issues JWTs, which are signed tokens the frontend attaches to each API call. Why: authentication is a solved problem you should never hand-build; the backend just verifies the token signature.
- **AWS Amplify Hosting**: watches the repo, builds the frontend on every push, and serves it on a CDN with HTTPS. Why: frontend deployment becomes a side effect of `git push`.

- [ ] `frontend/`: Next.js + Tailwind, one page that calls the backend and renders the result
- [ ] Cognito user pool + app client in `FrontendStack`; hosted UI or Amplify Auth components
- [ ] Backend validates Cognito JWTs on protected routes
- [ ] Amplify Hosting connected to the repo (`frontend/` root), env vars set
- [ ] A visible disclaimer/footer component slot (project-specific text comes later)

STOP gate 7: maintainer signs up, logs in on the deployed Amplify URL, and sees data returned from an authenticated backend call. Unauthenticated calls return 401 (show it).

## Phase 8: CI/CD

Goal: every merge to main deploys itself; no AWS keys stored anywhere.

Tools in this phase:
- **GitHub Actions**: workflows defined in YAML that run on every push or pull request: lint, test, deploy. Why: it lives where the code lives, the free tier covers a personal project, and via the Phase 1 OIDC role it deploys to AWS with no stored credentials.
- **Branch protection**: a GitHub setting that blocks direct pushes to main and requires passing checks. Why: the pipeline is only a guarantee if it cannot be bypassed.
- **cdk diff in CI**: prints the infrastructure changes a PR would cause. Why: you review infrastructure changes the same way you review code changes, before they happen.

- [ ] Workflow `ci.yml`: on PR run ruff, pytest (unit), and `cdk diff` via the OIDC role
- [ ] Workflow `deploy.yml`: on main run tests, evals, `cdk deploy --all`, then frontend build (Amplify auto-builds on push)
- [ ] Branch protection on main: PR + passing checks required
- [ ] Concurrency guard so two deploys cannot overlap

STOP gate 8: merge a trivial change (README typo). Show the green pipeline and the change live.

## Phase 9: Hardening and cost review

Goal: safe defaults locked in; spend understood.

Tools in this phase:
- **Bedrock Guardrails**: a filter attached to model calls that masks PII, blocks denied topics, and screens harmful content on the way in and out. Why: policy lives in one managed place instead of scattered through prompts.
- **AWS Cost Explorer**: the console view that breaks the bill down by service, tag, and day. Why: paired with the Phase 1 tags, it answers "what is costing me money" in one screen.
- **IAM least privilege review**: narrowing each role to only the actions and resources it uses. Why: an agent that can call tools is an actor in your account; its blast radius should be as small as its job.

- [ ] Bedrock Guardrails: a basic policy (PII masking, denied topics placeholder) attached to agent calls
- [ ] Verify log retention on every log group is 30 days
- [ ] Review IAM: agent, backend, and CI roles are least-privilege; no wildcards on resources where avoidable
- [ ] Cost Explorer review with maintainer: line-item actuals vs the table below
- [ ] `scripts/teardown_check.py` or documented `cdk destroy` runbook tested against `cdk diff`

STOP gate 9: present the cost review table (expected vs actual) and the IAM summary. Maintainer signs off. Infrastructure is done; feature work starts.

## Phase 10: Archive the build plan

Goal: CLAUDE.md becomes small again. Claude Code loads this file every session, so after the build it must carry only the always-needed rules.

- [ ] Create `docs/SETUP.md` and move into it: the entire "Build phases" section (Phases 0 through 10, with their completed checklists and tool definitions) and the "Expected monthly cost" table
- [ ] Keep in CLAUDE.md: "How Claude Code must use this file" (rewritten for the maintenance era, see next item), "Operating rules", "Stack decisions", "Repository layout", "Conventions"
- [ ] Rewrite the "How Claude Code must use this file" section to two lines: follow the operating rules; the infrastructure history and runbooks live in `docs/SETUP.md`
- [ ] Add one pointer line under the stack table: "How each piece was built, verified, and what it costs: see `docs/SETUP.md`"
- [ ] Commit as its own change, no other edits mixed in

STOP gate 10: show CLAUDE.md under roughly 100 lines, `docs/SETUP.md` containing the full history, and both rendering correctly on GitHub.

## Expected monthly cost (dev, personal scale)

| Item | Expected |
|---|---|
| Aurora Serverless v2 (auto-pause) | ~$0 compute idle + ~$0.10/GB storage |
| App Runner (1 small instance) | $5 to $15 |
| Amplify Hosting | $0 to $5 |
| Cognito | $0 at personal scale |
| CloudWatch + alarms | $1 to $5 |
| AgentCore (consumption) | Low single digits at dev usage |
| Bedrock tokens | Usage-driven; controlled by tiering, caching, batch |
| Budgets, IAM, OIDC, tags | $0 |
| Target total (excluding tokens) | Under $30 |

If actuals exceed the budget alarm, stop feature work and find the line item first.
