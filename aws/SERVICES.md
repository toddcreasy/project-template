# How a full AWS deployment fits together

Written for someone learning AWS from scratch. The goal is not to catalogue this project. It is to
show the shape every AWS deployment has, so the next one is recognisable.

AWS sells around 240 services with overlapping names and no obvious ordering. Nobody learns them
as a list. What actually transfers is the set of jobs every deployment has to fill, because they
are always the same ten or so. Once you know the jobs, picking services becomes a short set of
tradeoffs rather than a search.

This project is used as the worked example throughout. Where a choice was close, the alternatives
and the reason are given.

---

## Part 1: How AWS is organised

Four ideas, and everything else sits inside them.

**Account.** The billing and isolation boundary. One account, one bill, and resources in different
accounts cannot see each other unless you deliberately connect them. Companies run many; a
personal project runs one.

**Region.** A geographic cluster of data centres, such as `us-east-1` (Northern Virginia) or
`eu-west-2` (London). Services in different regions are effectively different installations, and
data crossing between them costs money. Pick one region and stay in it until you have a reason not
to.

**Availability Zone.** An isolated data centre within a region, usually three or more. Spreading
across two means one can fail without taking you down. Managed services do this for you.

**IAM.** The permission system, and the single most important thing to understand. By default,
nothing in AWS can do anything. Every action by every person and every program is denied unless a
policy explicitly allows it. Most confusing AWS errors are IAM errors wearing a disguise.

Two IAM ideas matter constantly:

- A **role** is a set of permissions a *program* borrows temporarily, rather than a password a
  person types. Credentials rotate automatically and expire. Everything in a well-built deployment
  uses roles, and stores no passwords at all.
- A **policy** is the document listing allowed actions and the resources they apply to. "Least
  privilege" means listing exactly what is needed, not `*`.

You will also meet **ARNs**, unique ids shaped like `arn:aws:s3:::my-bucket`. You paste a lot of
them.

---

## Part 2: The ten jobs every deployment has to fill

This is the framework. Any deployment, any company, any size.

| # | The job | This project | Common alternatives |
|---|---|---|---|
| 1 | Who is allowed to do what | IAM roles and policies | No alternative; IAM is mandatory |
| 2 | A private network to put things in | VPC with isolated subnets | Default VPC, or none for fully managed services |
| 3 | Somewhere to run your code | App Runner | Lambda, ECS/Fargate, EC2, EKS |
| 4 | Somewhere to keep structured data | Aurora Serverless v2 (PostgreSQL) | RDS, DynamoDB, self-managed on EC2 |
| 5 | Somewhere to keep files | S3 | EFS, FSx |
| 6 | Somewhere to keep secrets | Secrets Manager | SSM Parameter Store, environment variables (bad) |
| 7 | Serving a website to browsers | Amplify Hosting | S3 + CloudFront, App Runner, EC2 + nginx |
| 8 | Knowing who your users are | Cognito | Auth0, Clerk, hand-built (do not) |
| 9 | Seeing what is happening | CloudWatch, X-Ray | Datadog, Grafana, Honeycomb |
| 10 | Getting code from laptop to cloud | CDK plus GitHub Actions | Terraform, CloudFormation by hand, clicking in the console |

Plus two that are easy to skip and expensive to skip: **cost control** and **teardown**.

---

## Part 3: Filling each job

### Job 1: Permissions (IAM)

**What it is.** Covered above. Nothing runs without it.

**How it looks in practice.** Each component gets its own role with its own narrow policy. The
backend may read one database and one secret. The agent may call five named AI models and one
gateway. Neither can touch the other's resources.

**Cost.** $0. IAM is free.

**What to know.** Some AWS actions genuinely cannot be restricted to a specific resource and must
be granted on `*`. Tracing and metric-publishing are the common ones. That is not sloppiness, it
is the API's design, and the correct response is to constrain it another way, such as by requiring
a specific metric namespace.

### Job 2: The network (VPC)

**What it is.** A private network inside AWS. Things inside it can reach each other. Things outside
cannot reach in unless you allow it.

A VPC is divided into **subnets**. A *public* subnet can reach the internet. A *private* or
*isolated* one cannot.

**The cost trap that shapes everything.** For something in a private subnet to reach out to the
internet, you need a **NAT gateway**, which costs about $32 per month. On a $30 budget that is the
whole budget. The alternative, private connection points into your network called **VPC
endpoints**, costs about $7.30 per month each and you usually need several.

**What this project does.** It has no NAT gateway and no VPC endpoints. The database sits in an
isolated subnet with no route anywhere, and everything reaches it a different way (see Job 4).
This one constraint drove several later decisions, which is normal: networking cost shapes
architecture more than people expect.

### Job 3: Running your code (compute)

This is the choice people agonise over. The honest decision tree:

| If | Use | Because |
|---|---|---|
| Code runs occasionally, in short bursts | **Lambda** | Costs nothing when idle. Charged per invocation |
| One small always-on web service | **App Runner** | One resource. HTTPS, scaling, restarts included |
| Several services, custom networking, sidecars | **ECS/Fargate** | More control, more assembly |
| You need the actual machine | **EC2** | A virtual server you patch and manage yourself |
| Dozens of services, a platform team | **EKS** (Kubernetes) | Only above a scale that justifies $73/month before any machines |

**What this project uses.** App Runner, running one container.

**Why not Lambda,** which is cheaper. The API is called by a browser with a person waiting. Lambda
sleeps when idle, and waking up adds a delay on exactly the path where delay is most visible.
Lambda would be the better choice for a backend that is used rarely or asynchronously.

**Cost here.** $5 to $15 per month, and it is the largest fixed line in the bill. It runs whether
anyone uses it or not.

**What bites.** Always cap the maximum number of copies. Uncapped autoscaling is a larger budget
risk than anything else in a project this size.

### Job 4: Structured data (the database)

**What it is.** Aurora Serverless v2 running PostgreSQL, a standard relational database managed by
AWS. "Serverless v2" means the computing power scales automatically, including down to zero when
nothing is using it. Capacity is measured in **ACUs**, roughly 2 GB of memory each.

**Why not plain RDS,** which is the same databases without the scaling. RDS bills for a running
machine 24 hours a day. On a project used a few hours a week, that is mostly waste. Measured here:
0.00 ACU for hours at a time.

**Why not DynamoDB,** which is cheaper and faster. It is not relational. No joins, no SQL, and a
data model you must design around your queries up front.

**Cost.** Roughly $0 while idle, plus about $0.10 per GB per month of storage.

**What bites.** The first query after idling fails while the database wakes, with an error named
`DatabaseResumingException`. It is expected behaviour, not a fault. Both your code and your
user-facing messages need to treat it as such. Waking took about 17 seconds here.

**How anything reaches it.** Remember the database is in an isolated subnet with no network route.
The **RDS Data API** solves this: it is a normal AWS web address that accepts SQL, authorised by
IAM rather than a database password. No NAT gateway, no endpoints, no bastion server.

A second benefit worth copying: the Data API fetches the database password itself, using the
caller's identity. The password never enters your program, so it cannot be logged, leaked, or
committed by accident.

### Job 5: Files (S3)

**What it is.** Storage for files of any size, addressed over the web. One of the oldest AWS
services and the foundation many others are built on.

**Cost.** Pennies per GB. Files here move automatically to a cheaper storage tier after 30 days.

**What bites.** With **versioning** on, deleting every file does not leave the bucket empty. Old
versions and deletion markers remain, and they will block you from tearing the project down later.

### Job 6: Secrets (Secrets Manager)

**What it is.** A store for passwords and keys that programs fetch at runtime, so nothing sensitive
sits in code or a config file.

**Cost.** About $0.40 per secret per month.

**The alternative.** SSM Parameter Store does much the same and has a free tier, but does not
rotate secrets automatically.

**The anti-pattern.** Putting secrets in environment variables in your deployment config. They end
up visible to anyone who can read the configuration.

### Job 7: Serving the website (Amplify Hosting)

**What it is.** You give it the built files of a website. It serves them worldwide over HTTPS with
a real URL and a certificate.

**The alternative.** S3 plus CloudFront is the same thing assembled by hand: a bucket, an access
policy, a distribution, a cache-invalidation strategy, and a certificate. Amplify is those five
preconfigured, with a build pipeline attached.

**A pattern worth stealing.** Amplify forwards `/api/*` to the backend. The browser therefore only
ever talks to one address. This removes the need for **CORS**, the browser rule that blocks a page
from calling a different domain and which causes a great deal of confusion for beginners. If your
frontend and backend appear to be the same origin, the problem does not exist.

**Cost.** Effectively $0 for a static site.

### Job 8: Users (Cognito)

**What it is.** Managed sign-up, sign-in, email verification, password reset, and optional
two-factor. It gives the browser a **JWT**, a signed token proving who the user is, which the
browser sends with each request. Your backend verifies the signature.

**Why managed.** Authentication has a long history of being got subtly wrong. Verifying a signature
is a small, well-defined job. Storing passwords safely is not.

**Cost.** $0 at this scale.

**What bites.** A browser cannot keep a secret, so a browser-facing client must be configured
without a client secret. Also, put the user directory "upstream" of whatever verifies its tokens.
Getting this backwards creates two pieces of infrastructure each waiting on the other, which
CloudFormation refuses to build.

### Job 9: Seeing what is happening (CloudWatch, X-Ray)

**Logs.** Everything writes to **CloudWatch Logs**. Write them as JSON rather than prose, so you
can search on fields instead of guessing at substrings.

**Metrics and alarms.** Numbers over time, and thresholds that email you. Note that alarms cost a
little each, so alarm on things you would act on.

**Traces.** A **trace** records one request as a tree of timed steps: this called that, which took
this long. **X-Ray** collects them, usually via **OpenTelemetry**, an open standard for
instrumenting code.

**Why traces matter more than they sound.** Logs tell you what happened. A trace tells you where
the time went. On this project a trace immediately showed that 83% of one request was spent
waiting on the database, not on the work everyone assumed was slow. No log line said that.

**Cost.** $1 to $5 per month, mostly log storage.

**What bites.** Every log store defaults to keeping data forever, and services that create their
own log stores will not set a limit for you. Audit them directly rather than assuming.

### Job 10: Getting code to the cloud

Two halves.

**Describing the infrastructure.** Clicking in the console does not scale, cannot be reviewed, and
cannot be rebuilt. **CloudFormation** creates resources from a description file. **CDK** writes
that file from real code, here Python, so you get loops, functions, and types.

The payoff is that `cdk destroy` reliably removes what `cdk deploy` created, and a code review can
show infrastructure changes before they happen.

**The alternative.** Terraform does the same job and works across clouds. CDK was chosen here
because the project is already Python.

**Running the deployment.** GitHub Actions runs tests on every proposed change and deploys on
merge. It connects to AWS using **OIDC**, where GitHub proves its identity directly and borrows a
role for a few minutes.

**Why OIDC matters.** The alternative is storing an AWS access key in GitHub. That key does not
expire, works from anywhere, and is one leaked log away from being someone else's. OIDC has no
stored credential at all. It is the highest-value zero-cost decision in the whole stack.

---

## Part 4: The two jobs people skip

### Cost control

Set a **budget** with email alerts before creating anything that costs money. Tag every resource
with a project name so you can later ask which part of the bill is which.

**The trap.** Budgets reads its numbers from **Cost Explorer**, which is switched off on new
accounts and takes 24 hours to gather data. Until it has data, the alarm has nothing to read and
cannot fire. On this project the spending alarm existed for nine build phases and could not have
fired once. Turn Cost Explorer on the day you open the account.

### Teardown

Know how to delete it before you build it. Two things routinely block a clean teardown: buckets
that are not really empty because of versioning, and log stores or other resources that services
created for themselves and CloudFormation does not own.

Write the teardown order down, and check it against reality rather than assuming.

---

## Part 5: The AI-specific layer

Skip this if you are here for the AWS framework. It fills jobs the ten above do not cover.

**Amazon Bedrock** gives you access to AI models through one AWS address, billed per **token**,
roughly three quarters of a word. Model access stays inside your account, permissions, and bill,
with no second vendor and no API key to store.

**Bedrock AgentCore Runtime** runs an *agent*, meaning a program that gives a model a goal and a
set of tools and lets it choose which to call. Running it separately from the API means a stuck
agent cannot take the website down.

**AgentCore Gateway** publishes an existing API as agent-callable tools, so the backend needs no
AI-specific code.

**Bedrock Guardrails** filters model calls: hiding personal data, refusing named topics, blocking
harmful content. Worth knowing that its topic matching is based on meaning rather than keywords,
so it is probabilistic. On this project one phrasing was caught one time in three before the topic
was named explicitly. A guardrail is a strong filter, not a guarantee.

**Cost.** Usage-driven and the least predictable line. Controlled by using a small cheap model by
default, caching the unchanging part of prompts, and batching work nobody is waiting on.

---

## Part 6: What the whole thing costs

| Item | Per month | Note |
|---|---|---|
| App Runner | $5 to $15 | The floor. Runs whether used or not |
| CloudWatch | $1 to $5 | Mostly log storage |
| Secrets Manager | ~$0.40 | Per secret |
| Aurora Serverless v2 | ~$0 idle | Plus ~$0.10/GB storage |
| S3 | pennies | |
| Amplify Hosting | ~$0 | Static files |
| Cognito | $0 | At this scale |
| IAM, Budgets, OIDC | $0 | |
| AI tokens | usage | The unpredictable one |
| **Target** | **under $30** | Excluding tokens |

The lesson generalises: in a small deployment, the bill is dominated by things that run whether or
not anyone uses them. Scale-to-zero services and a hard cap on autoscaling matter more than
per-request efficiency.

---

## Part 7: What is not AWS, and why

| Job | Tool | Why not AWS |
|---|---|---|
| Backend framework | FastAPI | AWS does not make a Python web framework |
| Python tooling | uv, ruff, pytest | Language ecosystem; no AWS equivalent |
| Database migrations | Alembic | AWS has no tool for versioning your own table changes |
| Frontend framework | Next.js, React, Tailwind | AWS hosts websites but does not make a framework |
| Code hosting and CI | GitHub, GitHub Actions | The code already lives there, and it deploys with no stored key. AWS CodePipeline adds setup and cost for no benefit at this size |
| Containers | Docker | An open standard AWS runs rather than replaces |

## Deliberately not used

**Kubernetes (EKS).** Schedules containers across a fleet of machines. Costs $73 per month for the
control plane before a single machine runs. Starts making sense at roughly ten services with
steady traffic, or when you need workloads the simpler services will not run.

**Terraform.** Does CDK's job. CDK won because the project is already Python.

**Snowflake, Databricks.** Data platforms priced for companies.

**Dedicated vector databases.** The Postgres extension is enough well past personal-project scale.

**WAF and heavy perimeter security.** Real monthly cost to protect something nobody is attacking
yet. Revisit when you have users worth attacking.
