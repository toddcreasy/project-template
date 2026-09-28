# CLAUDE.md

Steady-state operating file for a deployed AWS project. This is what `CLAUDE.md` becomes after the
build plan finishes and Phase 10 archives the phases into `docs/SETUP.md`. Claude Code loads this
file every session, so it carries only the rules that are always needed.

Use `aws/BUILD.md` to build a project. Use this one to run it.

## Fill these in before first use

Replace every placeholder, then delete this section. A placeholder left in place will be read as a
literal value.

| Placeholder | What it is |
|---|---|
| `<PROJECT_NAME>` | Short kebab-case name, used for tags and resource prefixes |
| `<PACKAGE>` | Python package name under `src/`, usually `<PROJECT_NAME>` with underscores |
| `<AWS_ACCOUNT_ID>` | 12-digit account number |
| `<AWS_REGION>` | The one region everything lives in |
| `<AWS_PROFILE>` | CLI profile name |
| `<SSO_PORTAL_URL>` | Identity Center access portal, if using SSO |
| `<PERMISSION_SET>` | Identity Center permission set, if using SSO |
| `<MONTHLY_BUDGET>` | Budget ceiling in dollars |
| `<ALERT_EMAIL>` | Where budget alarms go |
| `<PYTHON_VERSION>` | Pinned in `.python-version` |

Delete any section that does not apply. A project with no agent should not carry agent rows; a
project with no frontend should not carry frontend rows.

## How Claude Code must use this file

Follow the operating rules below. The infrastructure history, the build phases that produced it,
and the runbooks all live in `docs/SETUP.md`.

## Operating rules

Direct. Evidence-first. Skip preamble.

### Writing style
- Never use em dashes or en dashes in any written output. Use commas, periods, semicolons, or restructure.
- Write in the maintainer's voice for all prose output. The voice profile is `.claude/rules/writing-voice.md`. This repo-local copy overrides any global one. Never write to the global copy. No generic LLM prose.
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

AWS-first. Anything not AWS is listed with the reason AWS cannot fill the slot. Drop the rows that
do not apply to this project.

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

Excluded on purpose (wrong scale for a personal project): Kubernetes, Terraform, Snowflake,
Databricks, A2A, LiteLLM, dedicated vector databases, WAF-heavy perimeter builds.

How each piece was built, verified, and what it costs: see `docs/SETUP.md`.

## Repository layout

```
.
├── CLAUDE.md              # this file
├── pyproject.toml         # project definition; uv.lock pins exact versions
├── .env.example           # every env var the app reads, no values
├── src/<PACKAGE>/         # application code, the only thing that ships
├── tests/                 # fast tests, no network
├── infra/                 # CDK app: app.py + stacks/
├── migrations/            # Alembic versioned schema changes
├── frontend/              # Next.js app
├── evals/                 # golden set; hits a real model, so slow and costs money
├── scripts/               # one-shot operational scripts, never imported
├── docs/                  # SETUP.md: identity, tooling, and the full build history
└── .github/workflows/     # CI; GitHub reads this exact path only
```

What each directory is for, and which of these are real conventions rather than choices: see
`LAYOUT.md` in the template repo.

## Conventions

- One CDK app in `infra/`, one stack per concern: `NetworkStack`, `DataStack`, `BackendStack`, `AgentStack`, `FrontendStack`, `OpsStack`.
- Tag every resource: `project=<PROJECT_NAME>`, `env=dev`, `managed-by=cdk`.
- One AWS region: `<AWS_REGION>`. Do not spread resources across regions.
- Model tiering: default to the small Bedrock model tier (Haiku class) for extraction, filtering, and routing. Use the large tier only for final synthesis. Prompt caching on for any repeated prefix. Batch API for offline jobs.
- Log retention: 30 days on every log group. Set it explicitly; the default is forever, and services that create their own groups will not do it for you.
- Databases have no network route from outside the VPC. Reach Aurora through the RDS Data API over HTTPS, authenticated with IAM. See `docs/SETUP.md`.

## AWS environment

- Account `<AWS_ACCOUNT_ID>`, Region `<AWS_REGION>`, CLI profile `<AWS_PROFILE>`.
- If the profile is IAM Identity Center rather than a static key, sessions expire. On `ExpiredToken` or `Unable to locate credentials`, ask the maintainer to run `aws sso login --profile <AWS_PROFILE>`. Do not try to re-authenticate non-interactively.
- Access portal `<SSO_PORTAL_URL>`, permission set `<PERMISSION_SET>`.
- How identity and the Organization were set up: see `docs/SETUP.md`.

## AWS guidance

- Prefer the AWS MCP Server for AWS interactions. It gives sandboxed execution, observability, and audit logging. Fall back to the AWS CLI only when it is unavailable.
- Before starting a task, check whether a relevant AWS skill exists. Load it with `retrieve_skill` and prefer its guidance over general knowledge.
- When uncertain about an AWS detail (API parameters, permissions, limits, error codes), verify against documentation rather than guessing. State uncertainty explicitly if you cannot confirm.
- Create infrastructure as code (CDK or CloudFormation), not with one-off CLI commands.
- Follow AWS Well-Architected principles when the choice is not already settled below.
- No em dashes in AWS resource names or descriptions. Use hyphens.

## Secret safety

- Load the `aws-secrets-manager` skill first for any secret, credential, API key, token, or password task.
- Never call `secretsmanager get-secret-value` or `batch-get-secret-value`, and never hit the Secrets Manager Agent daemon directly. Each of those pulls the plaintext secret into the transcript.
- Use `{{resolve:secretsmanager:secret-id:SecretString:json-key}}` with `asm-exec` so the secret resolves at runtime and never enters context.

## Bedrock model access

Model availability is per account, not per region, and the APIs that look like they answer the
question do not.

- The only valid entitlement probe is a real one-token `converse` call. `list-inference-profiles` and `get-foundation-model-availability` report the model in the region, not this account's right to invoke it, and both read green for models that refuse.
- Pin exact model IDs in the settled-decisions table below. Record which ones were probed and when. Re-probe before relying on a model you have not called recently.
- A newer model returning `AccessDeniedException: <model> is not available for this account` is usually an account entitlement gate, not an IAM or Marketplace problem. Check the tokens-per-minute service quota for that model before chasing permissions: a value of 0 against a positive AWS default is an account-level override, and it rejects the request before it reaches the model.
- Service Quotas cannot lift a zero override. It refuses any requested value at or below the AWS default, so the only submittable request is an absurd one. The remaining route is AWS Sales, which treats frontier model access as a commercial qualification conversation and weighs account age, billing history, and a stated business case.
- Do not spend a session re-running the console model-access flow to fix this. Agreement accepted, entitlement `AVAILABLE`, authorization `AUTHORIZED`, and admin IAM can all be true while the invoke still fails.

## Settled decisions

Do not re-ask. Rationale and history in `docs/SETUP.md`. Fill this table in as decisions land, and
record the date on anything that can change underneath you.

| Decision | Value |
|---|---|
| Monthly budget | `$<MONTHLY_BUDGET>`, alerts to `<ALERT_EMAIL>` |
| Python | `<PYTHON_VERSION>`, pinned in `.python-version` |
| `MODEL_SMALL` | fill in the exact inference profile ID |
| `MODEL_LARGE` | fill in the exact inference profile ID |
| Models allowed | list the exact IDs that have been probed and work. No other IDs. |

Cost readings need care once credits are involved. Promotional credits offset usage
dollar-for-dollar, so an unfiltered Cost Explorer total reads near zero regardless of real spend.
Filter `RECORD_TYPE=Usage` for the number that matters, and create budgets with
`include_credit=False` or they can never cross a threshold.
