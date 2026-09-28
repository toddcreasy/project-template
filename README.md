# project-template

`CLAUDE.md` templates for new projects. Copy the one that fits into a fresh repo as `CLAUDE.md` and
Claude Code scaffolds the project in phases, stopping for review at each gate.

| File | What it is |
|---|---|
| `CLAUDE.md` | Plain Python project: uv, ruff, pytest, pre-commit, GitHub Actions. No cloud assumptions |
| `aws/` | Personal AWS project on Bedrock, AgentCore, Aurora, App Runner, and Amplify |

## `aws/`

| File | What it is |
|---|---|
| `aws/SERVICES.md` | **Start here if you are new to AWS.** How a full AWS deployment fits together: the ten jobs every deployment has to fill, which service fills each, what the alternatives are, and what it all costs |
| `aws/BUILD.md` | The build plan: eleven phases, each with a checklist and a STOP gate. Copy it into a fresh repo as `CLAUDE.md` |
| `aws/CLAUDE.md` | The steady-state operating file. What `BUILD.md` becomes once Phase 10 archives the phases into `docs/SETUP.md`. Drop it into an already-deployed project |
| `aws/LAYOUT.md` | Every directory in the AWS layout, and which are real conventions rather than choices. Adds `infra/`, `migrations/`, `frontend/`, `evals/`, and the Dockerfile |
| `aws/GOTCHAS.md` | Failures found by running the plan once, with the error text that identifies them |

The AWS plan has been executed once end to end. Corrections from that run are folded into
`aws/BUILD.md`; `aws/GOTCHAS.md` holds the detail and the error messages.

**Before AWS Phase 0:** enable Cost Explorer in the billing console. It takes up to 24 hours to
ingest, and until it does the budget alarm cannot fire.
