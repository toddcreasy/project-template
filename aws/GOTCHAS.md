# Gotchas

Failures from building this stack once, with the error text that identifies them. Every one of
these deployed cleanly or looked correct before it bit.

The theme worth internalising: **`cdk deploy` reporting success means CloudFormation converged on
your template, not that the behaviour you intended is live.** Three separate failures below were
reported as successful deploys. The check that caught each was comparing the deployed artifact
against the source, never the deploy log.

---

## Billing

**Cost Explorer is off by default, and nothing works without it.**

```
DataUnavailableException: Data is not available. Please try to adjust the time period.
```

`ce:GetCostAndUsage` fails, `describe-budget` returns `null` for actual and forecast so the budget
alarm cannot fire, and cost allocation tag keys cannot be activated because they only become
activatable after appearing in billing data. Enabling is one console click and up to 24 hours of
ingestion. Do it on day one, not when you reach the cost review, or the whole build runs with an
inert spend guard.

---

## CloudFormation and CDK

**Cyclic stack exports are rejected, and auth placement causes them.**

If the backend verifies Cognito tokens and the frontend needs the backend's URL, putting Cognito
in the frontend stack makes each stack import the other. Put the pool upstream. Routing the API
through a frontend rewrite (`/api/<*>`) breaks the other half of the cycle and removes the need
for CORS entirely.

**Removing a resource from one stack and adding it to another fails while the first still owns it.**

```
Resource X created successfully, but it is managed by stack arn:...:stack/OtherStack/...
```

Account-singleton resources make this worse: the physical id is the account number, so there is no
way to have two. Move it out of the first stack and deploy before adding it to the second.

**Custom-resource provider Lambdas have generated names and never-expiring log groups.**

Find the provider construct by id, then its `Handler` child, and build the group name from
`handler.ref`.

**A rolled-back stack still owns resources whose delete was skipped.**

`UPDATE_ROLLBACK_COMPLETE` is a stable state that accepts updates, but a subsequent no-op deploy
will not clear the status because CDK finds no changes to make.

---

## Observability

**Transaction Search needs a log-group policy it does not create.**

```
XRay does not have permission to call PutLogEvents on the aws/spans Log Group.
```

Add a CloudWatch Logs resource policy for `xray.amazonaws.com` scoped to `aws/spans` and
`/aws/application-signals/data`, with `aws:SourceArn` and `aws:SourceAccount` conditions.

**Then it races the traces delivery.**

```
X-Ray Delivery Destination is supported with CloudWatch Logs as a Trace Segment Destination.
```

`tracingEnabled` creates a delivery requiring CloudWatch Logs to *already* be the trace
destination. CloudFormation builds both in parallel unless you add an explicit dependency. The
destination flip is a slow account-level transition in both directions, so each retry costs
minutes.

**Managed evaluations deploy disabled.**

`executionStatus` defaults to DISABLED and `samplingPercentage` to 10. The config reports `ACTIVE`
while scoring nothing. Set both explicitly.

**Token metrics are not published.** Derive them from your own structured log line. Know the blind
spot: a metric filter on the runtime's log group sees only the deployed agent, not local runs or
CI eval runs, so a token-spend alarm built on it will not catch a runaway loop in CI.

---

## Guardrails

**Versions are immutable and CDK does not cut new ones.**

Changing the guardrail updates `DRAFT`. The version resource stays as-is, and anything pinned to a
version number keeps the old policy. Every future edit deploys cleanly and changes nothing. Pin a
hash of the policy config into the version construct's logical id so a change forces a new
version.

Hash the *whole* policy, not just topic names. Hashing names alone means a definition change still
goes unnoticed, which is the same bug one layer up.

**Topic definitions cap at 200 characters.**

```
One or more of your guardrail topic definitions exceeds the maximum allowed length.
```

**A block leaves structured output as None.**

```
AttributeError: 'NoneType' object has no attribute 'model_dump'
```

The intervention ends the agent loop before the model can call the structured-output tool. Handle
it, or a working safety control presents to the user as a 500.

**Streaming must be `sync`.** `async` delivers chunks before the guardrail sees them and does not
mask PII at all.

---

## GitHub Actions

**The OIDC subject claim now embeds numeric ids.**

```
AccessDenied: Not authorized to perform sts:AssumeRoleWithWebIdentity
sub presented: repo:owner@5910177/repo@1346345827:ref:refs/heads/main
```

A trust policy matching only `repo:owner/repo:*` is denied. The action retries, so the job hangs
instead of failing, and CloudTrail is the only place the reason appears.

**Branch protection needs GitHub Pro on a private repo.** Both the classic protection API and
rulesets return 403 on the free plan.

**`enforce_admins: false` means it does not stop you.** On a solo repo that means it stops nobody.
GitHub prints the rules and allows the push anyway.

**Emulated arm64 builds dominate deploy time.** Runners are amd64; add `setup-qemu-action` and
`setup-buildx-action`, and expect 15 to 20 minutes.

---

## Language and tooling

**Required settings with no defaults mean tests only pass where a gitignored `.env` exists.**
Add a test conftest supplying placeholders, or CI fails the first time it runs.

**Next.js generates types during a build.** `tsc --noEmit` on a clean checkout fails on
`LayoutProps` and friends. Run `next typegen` first.

**Frameworks newer than your training data ship their own docs.** Read `node_modules/<pkg>/dist/docs`
before writing code against a major version you have not seen.
