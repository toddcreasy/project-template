# AWS services, and why each one

Every service in the stack, what it does, what it was chosen over, and what it costs at personal
project scale. Written after building the stack once, so the costs are what was actually observed
or configured, not what the pricing page implies.

The rule the stack follows: AWS-first. Anything not AWS is listed with the reason AWS could not
fill the slot.

---

## Compute and hosting

### AWS App Runner — the backend API

Give it a container image; it runs it with HTTPS, health checks, and scaling, no servers.

**Over Lambda + API Gateway:** Lambda is cheaper when traffic is rare, but the backend holds a
warm connection pattern to the RDS Data API and gets called by both a browser and an agent. App
Runner's always-on instance avoids cold starts on a path a human is waiting on. Lambda is the
right call if the API is genuinely idle most of the day.

**Over ECS/Fargate:** Fargate wants a cluster, a task definition, a load balancer, and a target
group. App Runner is one resource. At one service, that difference is the whole decision.

**Cost:** the floor of the bill. One instance at 0.25 vCPU / 0.5 GB runs continuously. Budget
$5 to $15/month. This is the largest fixed line item in the stack.

**Watch:** cap `maxSize` on the autoscaling config. Uncapped scale-out is the biggest budget risk
in the whole stack, more than tokens.

### AWS Amplify Hosting — the frontend

Builds and serves the frontend on a CDN with HTTPS.

**Over S3 + CloudFront:** Amplify is that, preconfigured, with a build pipeline. Hand-rolling it
means a bucket, an OAC, a distribution, an invalidation strategy, and a cert.

**Cost:** effectively $0 for a static export. Build minutes and GB served, both trivial here.

**Watch:** if the app is a Next.js static export, Amplify serves plain files and there is no SSR
compute to pay for. Leaving SSR on for a client-rendered app buys nothing and costs money.

---

## Data

### Aurora Serverless v2 PostgreSQL + pgvector

Real Postgres that scales compute down to zero when idle.

**Over RDS:** RDS bills a running instance whether or not anyone uses it. Serverless v2 with
`minCapacity: 0` genuinely drops to zero. Observed idle ACU on a dev workload: 0.00 for hours at
a stretch.

**Over DynamoDB:** relational data, plus vector search in the same engine.

**Over a dedicated vector DB (Pinecone, Weaviate, Qdrant):** pgvector puts embeddings in the
database that already holds the rows they describe. One engine, one backup, one bill, and joins
between vectors and metadata are just SQL. A dedicated vector store earns its cost at a scale a
personal project will not reach.

**Cost:** ~$0 compute while idle, plus about $0.10/GB-month storage. The auto-pause is what makes
this affordable; verify it actually pauses rather than assuming.

**Watch:** the first query after a pause fails with `DatabaseResumingException` while the cluster
wakes. That is not an error, and both the API and the agent need to say so. Waking took ~17
seconds in practice.

### RDS Data API — how anything reaches the database

An HTTPS endpoint that runs SQL, authenticated with IAM.

**Over a bastion host or VPC connector:** the cluster sits in isolated subnets with no NAT
gateway, so nothing outside the VPC has a network route. Reaching it conventionally needs either
a NAT gateway (~$32/month) or three interface endpoints (~$7.30/month each). Both exceed a $30
budget on their own. The Data API needs neither: it is a public AWS endpoint reached with IAM
credentials.

**Second benefit:** the Data API resolves the database password from Secrets Manager itself using
the caller's identity. The password never reaches the application process at all.

**Cost:** per request, negligible at this scale.

**Watch:** results are typed per column. A `text` column arrives as `stringValue`, a `float8` as
`doubleValue`. Read the field matching the column type. Also, the SQLAlchemy dialect for it is a
small unmaintained package; if it breaks, run migrations from inside the VPC.

### Amazon S3 — documents

**Cost:** pennies. Lifecycle to Infrequent Access at 30 days.

**Watch:** versioned buckets are not empty when they look empty. Delete markers block a
`cdk destroy` until they are cleared.

---

## AI

### Amazon Bedrock

One API in front of many models, billed per token, IAM-authenticated, no separate API keys.

**Over calling model providers directly:** access stays inside the AWS account, permissions, and
bill. No second vendor relationship, no API key to rotate and leak.

**Cost:** usage-driven and the least predictable line. Controlled by tiering (small model by
default, large only for final synthesis), prompt caching, and the Batch API for offline work.

**Watch:** a model being `ACTIVE` in `list-inference-profiles` does not mean the account can
invoke it. Newer model families can return `AccessDeniedException` with full entitlement and
authorization set, needing an AWS Sales conversation. Probe with a real one-token `converse` call
before designing around a model, and keep a documented fallback.

**Watch:** always set `maxTokens` explicitly. Unset, it reserves the model's maximum against your
quota and causes throttling that looks inexplicable.

### Bedrock AgentCore Runtime

A managed place to run agent code, per-session isolated.

**Over running the agent inside the backend:** the agent gets its own identity, its own scaling,
and its own failure domain. A runaway agent loop does not take down the API.

**Cost:** consumption-based, low single digits at dev usage.

**Watch:** containers must be ARM64. An amd64 image does not start. On an amd64 CI runner this
means emulated builds, which dominate deploy time.

### AgentCore Gateway

Publishes an existing API or Lambda as MCP tools.

**Over hand-writing an MCP server:** the backend stays a plain web app. The Gateway does the MCP
plumbing and enforces auth per tool.

**Watch:** tool names get the target name prefixed (`target___operationId`), so the name the model
sees is not the operationId you wrote. The gateway's default protocol config also adds a semantic
search tool and a placeholder instructions string to every prompt; with few tools that is pure
token overhead.

### Bedrock Guardrails

A filter on model calls: PII masking, denied topics, harmful content.

**Over prompt instructions:** policy lives in one managed place rather than scattered through
prompts, and it applies to input and output. In practice it also blocks in ~450ms versus ~7s for
a model reasoning its way to a refusal.

**Watch:** topic matching is semantic and probabilistic, not keyword. Before a topic was named
explicitly, one phrasing was caught 1 time in 3. A guardrail is a strong filter, never a
guarantee.

---

## Operations

### AWS Budgets + SNS

**Cost:** $0.

**Watch:** the alarm reads Cost Explorer data. With Cost Explorer not enabled it returns `null`
for actual and forecast and cannot fire. Enable Cost Explorer on day one.

### CloudWatch

**Cost:** $1 to $5/month, mostly log ingestion.

**Watch:** every log group defaults to never expiring, and services that create their own groups
will not set retention for you. Neither will CDK's own custom-resource provider Lambdas. Audit
with `describe-log-groups` rather than trusting the stacks.

**Watch:** a health check every 10 seconds is ~8,600 access log lines a day. Cheap to store,
expensive to read past.

### IAM with GitHub OIDC

**Cost:** $0.

**Over stored access keys:** nothing to leak, nothing to rotate. This is the single highest-value
$0 decision in the stack.

### Amazon Cognito

**Cost:** $0 at personal scale.

**Over hand-built auth:** never hand-build auth.

**Watch:** a browser client must have no client secret. Put the pool upstream of whatever verifies
its tokens, or you get cyclic stack dependencies.

---

## Not AWS, and why

| Slot | Tool | Why not AWS |
|---|---|---|
| Backend framework | FastAPI + Pydantic | AWS makes no Python web framework |
| Python toolchain | uv, ruff, pytest | Language ecosystem; no AWS equivalent |
| DB migrations | Alembic | AWS has no schema migration tool for application tables |
| Dev-loop evals | pydantic-evals | AgentCore Evaluations scores deployed traces. Pre-deploy checks must run locally in seconds. Both are used |
| Frontend framework | Next.js + React + Tailwind | AWS hosts frontends but does not make one |
| Code host + CI | GitHub + Actions | The repo lives there; Actions assumes an AWS role via OIDC with no stored keys. CodePipeline adds setup and cost for no benefit at this scale |
| Containers | Docker | Open standard AWS consumes rather than replaces |

## Excluded on purpose

Kubernetes, Terraform, Snowflake, Databricks, A2A, LiteLLM, dedicated vector databases, and
WAF-heavy perimeter builds. All are wrong-scale for a personal project.

On Kubernetes specifically: the EKS control plane alone is $73/month before a single node, more
than double a $30 budget. It starts making sense at roughly ten services with sustained traffic,
where node bin-packing beats per-service managed pricing, or when you need workloads the managed
runtimes will not take (GPU pods, StatefulSets, a sidecar mesh).
