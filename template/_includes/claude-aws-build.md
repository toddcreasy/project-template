{%- set svc = aws_services or [] -%}
{%- set agents = "agentcore" in svc -%}
{%- set models = "bedrock" in svc or agents -%}
{%- set ns = namespace(n=-1) -%}
# CLAUDE.md

{{ description or project_name }}

AWS build plan, generated from toddcreasy/project-template. Claude Code reads it and builds the
platform in phases, stopping for review after each one. Functionality comes later; this file only
sets up the platform. `uvx copier update --trust` pulls later template changes into this repo.

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
- Settings load through `pydantic-settings` (`src/{{ package_name }}/settings.py`). Secrets are `SecretStr`. Locally they come from `.env`; deployed they come from AWS Secrets Manager or SSM. `.env` is gitignored.
{%- endif %}

### Coding principles
- Don't add features, refactors, or improvements beyond what was asked.
- Don't add comments, docstrings, or type annotations to code you didn't change.
- No helpers or abstractions for one-time operations. Three similar lines beat a premature abstraction.
- Validate only at system boundaries (user input, external APIs). Trust internal code.
- When editing: match existing style, don't touch adjacent code, remove only what YOUR change made unused. Mention unrelated dead code; don't delete it.
- No OWASP top 10 vulnerabilities. Fix insecure code you wrote immediately.

### Secrets and personal info
- `.env` holds real values and is gitignored. `.env.example` lists every variable with no values; the tags after `#` mark which values must never be committed.
- `python3 scripts/setup_env.py` asks for missing values, writes `.env`, and copies it to `{{ env_store_dir }}/{{ project_name }}.env`. `--pull` restores `.env` from that copy; `--github` pushes secret and private values to GitHub Actions secrets. When something new reads a variable, add it to `.env.example` first, then rerun the script.
- Terraform reads `TF_VAR_*` from the shell. Load `.env` first: `set -a; source .env; set +a`.
- Pre-commit blocks a commit containing a known key format, a personal email, phone number, SSN, or street address (`.gitleaks.toml`), or any secret or private value from `.env` (`scripts/check_env_leaks.py`). CI repeats the gitleaks scan over the full history.
- Never bypass these with `--no-verify`. A real false positive gets `gitleaks:allow` on that line, nothing broader.
{%- if use_github_actions %}
- The CI `secrets` job scans the full history and fails any new commit whose author or committer email is not a GitHub noreply address. Never remove or weaken it.
{%- endif %}

## Stack decisions

AWS-first. Anything not AWS is listed with the reason AWS cannot fill the slot. Rows match the
services chosen when the repo was generated; add a row when a phase adds a service.

| Slot | Tool | AWS? | If not AWS, why |
|---|---|---|---|
| Infrastructure as code | Terraform (`hashicorp/aws` provider) | No | One tool and one language across every project and any client's cloud. State lives in a shared S3 bucket with S3-native locking. |
{%- if models %}
| Models | Amazon Bedrock (Claude family) | Yes | |
{%- endif %}
{%- if agents %}
| Agent framework | Strands Agents SDK | Yes (AWS open source) | |
| Agent runtime | Bedrock AgentCore Runtime | Yes | |
| Tool access (MCP) | AgentCore Gateway | Yes | |
| Agent observability | AgentCore Observability + CloudWatch | Yes | |
| Production evals | AgentCore Evaluations | Yes | |
{%- endif %}
{%- if "aurora" in svc %}
| Relational + vector DB | Aurora Serverless v2 PostgreSQL + pgvector | Yes | |
| Secrets | AWS Secrets Manager | Yes | |
{%- endif %}
{%- if "s3" in svc or "static_site" in svc or "batch" in svc %}
| Object storage | S3 | Yes | |
{%- endif %}
{%- if "frontend" in svc %}
| Auth | Amazon Cognito | Yes | |
| Frontend hosting | AWS Amplify Hosting | Yes | |
{%- endif %}
{%- if "apprunner" in svc %}
| Backend hosting | AWS App Runner | Yes | |
{%- endif %}
{%- if "lambda" in svc %}
| Functions | AWS Lambda | Yes | |
{%- endif %}
{%- if "batch" in svc %}
| Pipeline compute | AWS Batch (Nextflow `-profile aws`) | Yes | |
{%- endif %}
{%- if "static_site" in svc %}
| Static site | S3 + CloudFront | Yes | |
{%- endif %}
| Cost control | AWS Budgets + cost allocation tags | Yes | |
{%- if "apprunner" in svc %}
| Backend framework | FastAPI + Pydantic | No | Language-level tooling. AWS makes no Python web framework. |
{%- endif %}
{%- if use_python %}
| Python toolchain | uv, ruff, pytest | No | Language ecosystem tools. No AWS equivalent exists. |
{%- endif %}
{%- if "aurora" in svc %}
| DB migrations | Alembic | No | AWS has no schema migration tool for application tables. |
{%- endif %}
{%- if models %}
| Dev-loop evals | pydantic-evals golden set in pytest | No | Pre-deploy evals must run locally in seconds. |
{%- endif %}
{%- if "frontend" in svc %}
| Frontend framework | Next.js + React + Tailwind | No | AWS hosts frontends (Amplify) but does not make a frontend framework. |
{%- endif %}
{%- if "batch" in svc %}
| Pipelines | Nextflow + nf-core | No | AWS runs the jobs (Batch); it has no workflow language bioinformatics uses. |
{%- endif %}
| Code host + CI runner | GitHub + GitHub Actions | No | The repo lives on GitHub. Actions assumes an AWS role via OIDC with no stored keys. |
| Secret scanning | gitleaks (pre-commit and CI) | No | Runs before code leaves the laptop. AWS has nothing that scans a git history. |
{%- if "apprunner" in svc or agents or "lambda" in svc %}
| Containers | Docker | No | Open standard. AWS consumes it; it does not replace it. |
{%- endif %}

Excluded on purpose (wrong scale for a personal project): Kubernetes, AWS CDK (glia-nav only),
Snowflake, Databricks, A2A, LiteLLM, dedicated vector databases, WAF-heavy perimeter builds.

## Repository layout

```
.
├── CLAUDE.md              # this file
{%- if use_python %}
├── pyproject.toml         # project definition; uv.lock pins exact versions
{%- endif %}
├── .env.example           # every env var, no values; tags mark what must never be committed
├── .gitleaks.toml         # secret and personal-info rules for pre-commit and CI
{%- if use_python %}
├── src/{{ package_name }}/  # application code, the only thing that ships
├── tests/                 # fast tests, no network
{%- endif %}
├── infra/                 # Terraform: one root module, one file per concern
{%- if "aurora" in svc %}
├── migrations/            # Alembic versioned schema changes
{%- endif %}
{%- if "frontend" in svc %}
├── frontend/              # Next.js app
{%- endif %}
{%- if models %}
├── evals/                 # golden set; hits a real model, so slow and costs money
{%- endif %}
{%- if "batch" in svc %}
├── pipelines/             # Nextflow pipelines; conf/ holds the local, slurm, aws profiles
{%- endif %}
├── scripts/               # setup_env.py, check_env_leaks.py, one-shot operational scripts
├── docs/                  # long-form docs the README links to
└── .github/workflows/     # CI; GitHub reads this exact path only
```

What each directory is for, and which are real conventions rather than choices: `aws/LAYOUT.md` in
the template repo.

## Conventions

- One Terraform root module in `infra/`, one file per concern: `ops.tf`, `github_oidc.tf`{% if "aurora" in svc or "s3" in svc %}, `data.tf`{% endif %}{% if "apprunner" in svc %}, `backend.tf`{% endif %}{% if agents %}, `agent.tf`{% endif %}{% if "frontend" in svc %}, `frontend.tf`{% endif %}{% if "batch" in svc %}, `batch.tf`{% endif %}{% if "static_site" in svc %}, `site.tf`{% endif %}. Split into modules only when a second project needs the same piece.
- State: `s3://{{ tf_state_bucket }}/{{ project_name }}/terraform.tfstate`, S3-native lock file. Never edit state by hand; use `terraform state mv` or a `moved {}` block for renames, `import {}` blocks to adopt existing resources.
- Every resource gets `project={{ project_name }}`, `env=dev`, `managed-by=terraform` through the provider's `default_tags`. Do not repeat them per resource.
- One AWS region: `{{ aws_region }}`. Do not spread resources across regions.
{%- if models %}
- Model tiering: default to the small Bedrock model tier (Haiku class) for extraction, filtering, and routing. Use the large tier only for final synthesis. Prompt caching on for any repeated prefix. Batch API for offline jobs.
{%- endif %}
- Log retention: 30 days on every log group. Create the group in Terraform before the service writes to it; a Lambda or service that creates its own group sets no expiry.
- Show `terraform plan` before every `apply`, and wait for approval on anything that destroys or replaces.

---

# Build phases
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Repo scaffold (done by the generator)

Before any AWS work: **enable Cost Explorer in the billing console.** One click and up to 24 hours
to ingest. Until it has data, `ce:GetCostAndUsage` fails, the budget alarm reads `null` so it
cannot fire, and cost allocation tags cannot be activated.

- [x] Layout, `.gitignore`, `.env.example`, README stub, first commit
{%- if use_python %}
- [x] `pyproject.toml` (Python >= {{ python_version }}), `uv.lock`, ruff and pytest config, one passing test
{%- endif %}
- [x] Pre-commit: gitleaks, `.env` leak check, large-file guard{% if use_python %}, ruff{% endif %}, terraform fmt
- [x] `.env` written and copied to `{{ env_store_dir }}/{{ project_name }}.env`
- [x] `infra/`: provider, S3 backend, budget, alert topic, GitHub OIDC role{% if "s3" in svc %}, data bucket{% endif %}{% if "apprunner" in svc or agents or "lambda" in svc %}, ECR repository{% endif %}
- [ ] Cost Explorer enabled (maintainer, console)
{%- if use_postgres %}
- [ ] Local Postgres: `docker compose up -d --wait`, then show `docker compose exec db psql -U {{ project_name | replace('-', '_') }} -c "select extversion from pg_extension where extname = 'vector'"` returning a version
{%- endif %}
{%- if create_github_repo %}
- [x] GitHub repo created and pushed
{%- else %}
- [ ] GitHub repo created and pushed: `gh repo create {{ github_owner }}/{{ project_name }} --private --source . --remote origin --push`
{%- endif %}

STOP gate {{ ns.n }}: {% if use_python %}`uv run ruff check .` and `uv run pytest` clean, {% endif %}`uvx pre-commit run --all-files` clean. Show the outputs.
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: AWS guardrails before any resources

Goal: spending alarms and deploy identity exist before anything can cost money.

Tools in this phase:
- **Terraform**: you describe AWS resources in `.tf` files; `terraform plan` shows what would change, `terraform apply` makes it so, `terraform destroy` removes it. Why: the infrastructure is versioned in git, reviewable before it happens, and rebuildable. Same tool on every project and every client.
- **S3 backend with lock file**: Terraform's record of what it created lives in a shared bucket, one key per project, with a lock object so two runs cannot collide. Why: CI and the laptop see the same state.
- **AWS Budgets**: a monthly spending limit that emails you at thresholds. Why: the number one risk in a personal cloud project is silent spend.
- **Amazon SNS**: AWS's notification service; topics fan out messages to email or other targets. Why: one topic carries every alert in this project.
- **IAM with GitHub OIDC**: GitHub Actions proves its identity to AWS and assumes a role for minutes. Why: no long-lived AWS keys stored anywhere.
- **Cost allocation tags**: labels on every resource that Cost Explorer can group by. Why: the budget filters on `project`, and the bill can be split by project.

- [ ] Confirm the AWS account ID and `{{ aws_region }}` with the maintainer; `aws sts get-caller-identity --profile {{ aws_profile }}` matches
- [ ] Account bootstrap done once (`aws/bootstrap` in project-template): state bucket `{{ tf_state_bucket }}` and the GitHub OIDC provider exist. If an older CDK project already created the provider, bootstrap runs with `create_github_oidc_provider=false`
- [ ] `TF_VAR_alert_email` and `TF_VAR_monthly_budget` set in `.env`; `set -a; source .env; set +a`
- [ ] `terraform -chdir=infra init`, then `plan`, then `apply` after approval
- [ ] Maintainer confirms the SNS subscription email
- [ ] Cost allocation tags `project` and `env` activated (bootstrap with `activate_cost_tags=true`). Blocked until the keys appear in billing data, so this lands a day or two late. The budget reads $0 until it does
- [ ] `AWS_ROLE_ARN` repo secret set from `terraform output github_actions_role_arn`; `python3 scripts/setup_env.py --github` pushes `TF_VAR_ALERT_EMAIL`
- [ ] README: teardown is `terraform -chdir=infra destroy`; note anything that blocks it (versioned buckets, retained logs)

STOP gate {{ ns.n }}: budget visible in the console, subscription confirmed, `terraform plan` shows no changes.
{%- if "aurora" in svc or "s3" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Data layer

Goal: {% if "aurora" in svc %}a Postgres database with vector search, reachable from a local script, credentials in Secrets Manager{% else %}object storage the app can read and write{% endif %}.

Tools in this phase:
{%- if "aurora" in svc %}
- **Aurora Serverless v2 (PostgreSQL)**: AWS-managed Postgres that scales its compute up and down, including to zero when idle. Why: real Postgres with near-zero cost while you are not using it, and no server patching.
- **pgvector**: a Postgres extension that stores embeddings and runs similarity search. Why: one database handles both normal tables and vector search.
- **AWS Secrets Manager**: stores credentials; apps fetch them at runtime by ARN. Why: passwords never sit in code, `.env` files in git, or CI settings.
- **Alembic**: versioned database schema migrations for Python. Why: schema changes become reviewable files that replay identically in every environment.
- **VPC**: your private network inside AWS. Why: the database gets no public address.
{%- endif %}
{%- if "s3" in svc %}
- **Amazon S3**: durable object storage for files and data. Why: pennies per GB and every AWS service reads from it.
{%- endif %}
{% if "aurora" in svc %}
- [ ] `infra/data.tf`: VPC (2 AZs, isolated subnets plus VPC endpoints, no NAT gateway), Aurora Serverless v2 PostgreSQL
- [ ] Serverless v2 scaling: min capacity 0 ACU (auto-pause) for dev, max 1
- [ ] `manage_master_user_password = true` so RDS generates the credentials into Secrets Manager; no password in Terraform state
- [ ] RDS Data API enabled; the database has no network route from outside the VPC
- [ ] `pgvector` extension enabled (`CREATE EXTENSION vector`)
- [ ] Alembic initialized; migration 001 creates a schema-version table only
- [ ] `scripts/db_check.py`: connects via the secret, runs a vector insert and cosine similarity query
- [ ] `DATABASE_SECRET_ARN` filled in `.env` (rerun `scripts/setup_env.py`)
{%- endif %}
{%- if "s3" in svc %}
- [ ] `infra/s3.tf` (generated): versioned, private, encrypted, Infrequent Access at 30 days. Applied; `S3_BUCKET` in `.env` from `terraform output data_bucket`
- [ ] Round trip: upload and read back one object with the CLI or a script
{%- endif %}

STOP gate {{ ns.n }}: {% if "aurora" in svc %}run `uv run python scripts/db_check.py`; show the round trip including a similarity score. Confirm the cluster pauses to 0 ACU after idle (console check).{% else %}show the object round trip.{% endif %}
{%- endif %}
{%- if "apprunner" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Backend API

Goal: a deployed FastAPI service{% if "aurora" in svc %} that reaches the database{% endif %}.

Tools in this phase:
- **FastAPI**: the standard modern Python web framework. Type hints define request and response shapes; docs generate themselves. Why: it shares Pydantic models with the rest of the system.
- **Docker**: packages the app and its dependencies into an image that runs the same everywhere.
- **Amazon ECR**: AWS's private registry for those images (generated in `infra/ecr.tf`). Why: App Runner deploys straight from it.
- **AWS App Runner**: runs a container image with HTTPS, scaling, and health checks, no servers to manage. Why: the least-effort way to run one small always-on service.
- **Amazon CloudWatch**: logs, metrics, dashboards, and alarms. Why: every App Runner log line lands in it with no setup.

- [ ] `src/{{ package_name }}/api/`: FastAPI app with `GET /health` (static){% if "aurora" in svc %} and `GET /health/db` (runs `SELECT 1`){% endif %}
- [ ] Settings resolve secrets from Secrets Manager when deployed, `.env` locally
- [ ] Dockerfile (multi-stage, uv-based, non-root user)
- [ ] `infra/backend.tf`: App Runner service from the ECR image{% if "aurora" in svc %}, VPC connector to Aurora, secret injected as env{% endif %}; log group with 30-day retention
- [ ] Structured JSON logging
- [ ] Local run documented: `uv run fastapi dev`

STOP gate {{ ns.n }}: `curl` the health endpoints on the deployed URL; show responses and one structured log line in CloudWatch.
{%- endif %}
{%- if "lambda" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Functions

Goal: one deployed Lambda function, invoked and logged.

Tools in this phase:
- **AWS Lambda**: runs a function on demand and bills per invocation. Why: scheduled jobs and glue code with no always-on cost.
- **EventBridge Scheduler**: cron for AWS. Why: scheduled functions without a server.

- [ ] `infra/functions.tf`: function (zip from `uv export` plus source, or the ECR image), execution role with only what it calls, log group created first with 30-day retention
- [ ] Function code under `src/{{ package_name }}/` or `functions/`, tested like the rest
- [ ] Alarm on errors to the Phase 1 alert topic

STOP gate {{ ns.n }}: invoke it with `aws lambda invoke`; show the response and the log line.
{%- endif %}
{%- if models %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: {% if agents %}Agent layer{% else %}Model access{% endif %}

Goal: {% if agents %}one working agent on Bedrock, deployed to AgentCore Runtime, with visible token usage{% else %}typed calls to Bedrock with visible token usage{% endif %}.

Tools in this phase:
- **Amazon Bedrock**: one AWS API in front of many models, billed per token, with IAM auth and no separate API keys. Why: model access stays inside the AWS account, permissions, and bill.
{%- if agents %}
- **Strands Agents SDK**: AWS's open-source Python agent framework. Why: first-class Bedrock and AgentCore support, and small enough to read.
- **Bedrock AgentCore Runtime**: a managed place to run agent code, with per-session isolation and support for long-running work. Terraform: `aws_bedrockagentcore_agent_runtime`.
{%- endif %}
- **Prompt caching**: Bedrock reuses a repeated prompt prefix at a fraction of the token price. Why: the single cheapest cost fix.

- [ ] Probe model access with a real one-token `converse` call for each model. `list-inference-profiles` and `get-foundation-model-availability` read green for models this account cannot invoke
- [ ] Pin exact inference profile IDs as `MODEL_SMALL` and `MODEL_LARGE` in `.env.example` defaults and the settled decisions; record the probe date
{%- if agents %}
- [ ] `src/{{ package_name }}/agents/`: one Strands agent, typed output model, one local tool, prompt caching enabled
- [ ] `infra/agent.tf`: AgentCore runtime from the ECR image, execution role scoped to the pinned model IDs
- [ ] `scripts/agent_smoke.py`: invokes the deployed agent, prints typed output and usage
{%- else %}
- [ ] `src/{{ package_name }}/llm.py`: one typed call through `converse`, prompt caching on the system prompt
- [ ] IAM for the caller scoped to the pinned model IDs
{%- endif %}
- [ ] Token and cost logging per call (structured fields: input_tokens, output_tokens, cache_read, model)

STOP gate {{ ns.n }}: show a typed response and the token usage log line{% if agents %} from the deployed runtime{% endif %}.
{%- endif %}
{%- if agents %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Tools over MCP

Goal: the agent reaches the backend through AgentCore Gateway as MCP tools.

Tools in this phase:
- **MCP (Model Context Protocol)**: the open standard for connecting agents to tools and data. Why: tool integrations written once stay portable across frameworks and models.
- **AgentCore Gateway**: publishes an existing API or Lambda as MCP tools, with IAM auth and per-tool permissions. Terraform: `aws_bedrockagentcore_gateway`, `aws_bedrockagentcore_gateway_target`.

- [ ] Expose one backend endpoint as a Gateway MCP tool
- [ ] Gateway auth wired to IAM; least-privilege policy for the agent identity
- [ ] Agent updated: the MCP tool is in its toolset; system prompt says when to use it
- [ ] Local dev path documented: running the agent against the tool without deploying

STOP gate {{ ns.n }}: smoke script shows the agent calling the Gateway tool. Show the trace of the call.
{%- endif %}
{%- if models %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Observability and evals

Goal: every model call is traceable; quality is measurable before deploys.

Tools in this phase:
{%- if agents %}
- **AgentCore Observability**: records every agent run as a trace of model calls, tool calls, latency, and tokens.
- **AgentCore Evaluations**: managed evaluators that score real production traces. Terraform: `aws_bedrockagentcore_online_evaluation_config`.
{%- endif %}
- **CloudWatch dashboards and alarms**: charts plus alerts to the Phase 1 topic. Why: you hear about error spikes and token spend from an email, not the bill.
- **pydantic-evals**: a golden set of inputs with expected typed outputs, scored under pytest. Why: before a change deploys, you know whether quality moved.
{% if agents %}
- [ ] Observability on the runtime: `aws-opentelemetry-distro` in the image, `opentelemetry-instrument` in front of the entrypoint, tracing enabled on the runtime
- [ ] CloudWatch Transaction Search: needs a CloudWatch Logs resource policy letting `xray.amazonaws.com` write to `aws/spans`, and the traces delivery must `depends_on` it, or Terraform creates both in parallel and the delivery fails
- [ ] Online evaluation config with response-quality and tool-usage evaluators. Set execution status to ENABLED and raise the sampling percentage; the defaults are DISABLED and 10%
{%- endif %}
- [ ] CloudWatch dashboard: invocations, errors, latency, daily token totals
- [ ] Alarms: error rate and daily token spend, both to the Phase 1 topic. Token metrics come from a metric filter over your own structured log line; it only sees deployed calls, not local or CI runs
- [ ] `evals/`: 10 to 15 golden cases with `pydantic-evals`; run with `uv run pytest evals`, marked so fast unit runs skip them

STOP gate {{ ns.n }}: show one full trace, `uv run pytest evals` passing, and the dashboard.
{%- endif %}
{%- if "frontend" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Frontend

Goal: a deployed web UI behind sign-in that calls the backend.

Tools in this phase:
- **Next.js + React + Tailwind**: the standard frontend stack. Why: largest ecosystem, best AI-tool support.
- **Amazon Cognito**: managed sign-up and sign-in that issues JWTs. Why: never hand-build auth; the backend just verifies the token.
- **AWS Amplify Hosting**: builds and serves the frontend on a CDN with HTTPS.

- [ ] `frontend/`: Next.js + Tailwind, one page that calls the backend
- [ ] Cognito user pool and app client in `infra/backend.tf`, not `frontend.tf`: the API verifies the tokens and the frontend needs the API URL, so keep auth upstream of both
- [ ] Backend validates Cognito JWTs on protected routes
- [ ] Amplify app in `infra/frontend.tf`. A Git-connected app needs a stored GitHub token (`access_token`); to avoid one, create the app with no repository and have CI upload the build through the Amplify deployment API
- [ ] Amplify rewrite `/api/<*>` to the backend so the browser stays same-origin; no CORS
- [ ] Disclaimer/footer component slot

STOP gate {{ ns.n }}: maintainer signs up and sees data from an authenticated call on the deployed URL. Unauthenticated calls return 401 (show it).
{%- endif %}
{%- if "batch" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Nextflow on AWS Batch

Goal: a Nextflow pipeline runs locally and on AWS Batch from the same command, switched by `-profile`.

Tools in this phase:
- **Nextflow + nf-core**: the workflow language and community pipelines. Why: the same pipeline runs on a laptop, Slurm, or the cloud.
- **AWS Batch**: queues containerized jobs onto EC2 instances it starts and stops. Why: pay only while tasks run; Spot cuts the price further.
- **S3 work directory**: Nextflow's intermediate files live in S3 when running on Batch.

- [ ] `infra/batch.tf`: Spot compute environment (min vCPU 0), job queue, instance and job roles, S3 work bucket with a 14-day expiry on `work/`, log group with 30-day retention
- [ ] `conf/compute.config` with `local`, `slurm`, and `aws` profiles; `aws` reads `AWS_S3_WORKDIR` and the queue name from env
- [ ] `AWS_S3_WORKDIR` in `.env`
- [ ] Budget alarm covers Batch: confirm instances carry the `project` tag (`propagate_tags` on the job definition, tags on the launch template)
- [ ] `nf-core` test profile runs end to end on `-profile aws`

STOP gate {{ ns.n }}: show the test run completing on Batch, then the compute environment back at 0 vCPU.
{%- endif %}
{%- if "static_site" in svc %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Static site

Goal: a static site served over HTTPS from a private bucket.

- [ ] `infra/site.tf`: private S3 bucket, CloudFront distribution with origin access control, bucket policy that only CloudFront can read
- [ ] Deploy step: `aws s3 sync` then a CloudFront invalidation
- [ ] Custom domain and ACM certificate only if the maintainer asks; the certificate must be in us-east-1

STOP gate {{ ns.n }}: `curl -I` the CloudFront URL shows 200; the bucket URL directly shows 403.
{%- endif %}
{%- if use_github_actions %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: CI/CD

Goal: every merge to main deploys itself; no AWS keys stored anywhere.

Tools in this phase:
- **GitHub Actions**: `ci.yml` already runs the secret scan{% if use_python %}, ruff, pytest{% endif %}, and Terraform fmt, validate, and tflint on every push.
- **Branch protection**: blocks direct pushes to main and requires passing checks.
- **terraform plan in CI**: prints the infrastructure changes a PR would cause, so you review them before they happen.

- [ ] Turn on the plan job: repo variable `TF_PLAN=true` (secrets `AWS_ROLE_ARN` and `TF_VAR_ALERT_EMAIL` are set in Phase 1)
- [ ] `deploy.yml`: on main, run checks, then `terraform apply -auto-approve` from a plan saved in the same job{% if "frontend" in svc %}, then build and upload the frontend{% endif %}. Concurrency group with `cancel-in-progress: false`; a killed apply leaves a stale lock
- [ ] Widen the CI role from read-only to the services this project uses, scoped by the `project` tag or resource name prefix where the service allows it
{%- if "apprunner" in svc or agents %}
- [ ] `docker/setup-qemu-action` and `setup-buildx-action` if any image is arm64. Runners are amd64, and emulated builds dominate the deploy
{%- endif %}
- [ ] Branch protection on main: PR plus passing checks required, `enforce_admins` on. Needs GitHub Pro on a private repo; both APIs return 403 on the free plan

STOP gate {{ ns.n }}: merge a trivial change. Show the green pipeline and the change live.
{%- endif %}
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Hardening and cost review

Goal: safe defaults locked in; spend understood.
{% if agents %}
- [ ] Bedrock Guardrails: PII masking and a denied-topics placeholder attached to agent calls. Three traps: `aws_bedrock_guardrail_version` does not cut a new version when the guardrail changes, so add `lifecycle { replace_triggered_by = [aws_bedrock_guardrail.this] }` or the runtime keeps the old policy; topic definitions cap at 200 characters; streaming must run in `sync` mode, because `async` never masks PII
- [ ] Handle the block path: a guardrail intervention leaves structured output as None. A working safety control should not look like a 500
{%- endif %}
- [ ] Every log group has 30-day retention: `aws logs describe-log-groups --query 'logGroups[?!retentionInDays].logGroupName'` returns nothing
- [ ] IAM review: every role least-privilege; no wildcard resources where avoidable
- [ ] `gitleaks git --config .gitleaks.toml` over the full history is clean
- [ ] Cost Explorer review with maintainer, filtered `RECORD_TYPE=Usage`: actuals vs the table below
- [ ] `terraform destroy` runbook tested with `terraform plan -destroy`

STOP gate {{ ns.n }}: present the cost review table (expected vs actual) and the IAM summary. Maintainer signs off.
{% set ns.n = ns.n + 1 %}
## Phase {{ ns.n }}: Archive the build plan

Goal: CLAUDE.md becomes small again. Claude Code loads it every session, so after the build it
carries only the always-needed rules.

- [ ] Move "Build phases" (with completed checklists) and "Expected monthly cost" into `docs/SETUP.md`
- [ ] Replace this file with `docs/CLAUDE-steady-state.md` (already filled in for this project), then fill its settled-decisions table
- [ ] Commit as its own change, no other edits mixed in

STOP gate {{ ns.n }}: CLAUDE.md under roughly 100 lines, `docs/SETUP.md` holding the full history.

## Expected monthly cost (dev, personal scale)

| Item | Expected |
|---|---|
| Terraform state, budgets, IAM, OIDC, tags | $0 |
| CloudWatch + alarms | $1 to $5 |
{%- if "aurora" in svc %}
| Aurora Serverless v2 (auto-pause) | ~$0 compute idle + ~$0.10/GB storage |
{%- endif %}
{%- if "s3" in svc or "static_site" in svc %}
| S3 | Cents per GB |
{%- endif %}
{%- if "apprunner" in svc %}
| App Runner (1 small instance) | $5 to $15 |
{%- endif %}
{%- if "lambda" in svc %}
| Lambda | ~$0 at personal scale |
{%- endif %}
{%- if "frontend" in svc %}
| Amplify Hosting + Cognito | $0 to $5 |
{%- endif %}
{%- if agents %}
| AgentCore (consumption) | Low single digits at dev usage |
{%- endif %}
{%- if models %}
| Bedrock tokens | Usage-driven; controlled by tiering, caching, batch |
{%- endif %}
{%- if "batch" in svc %}
| Batch (Spot, per run) | Usage-driven; $0 idle |
{%- endif %}
{%- if "static_site" in svc %}
| CloudFront | ~$0 at personal scale |
{%- endif %}
| Budget ceiling | ${{ monthly_budget }} |

If actuals exceed the budget alarm, stop feature work and find the line item first.
