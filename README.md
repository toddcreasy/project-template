# project-template

Starting point for a new personal AWS project. Copy `CLAUDE.md` into a fresh repo and Claude Code
builds the platform in phases, stopping for review at each gate.

| File | What it is |
|---|---|
| `CLAUDE.md` | The build plan: eleven phases, each with a checklist and a STOP gate |
| `aws/SERVICES.md` | Every AWS service in the stack, what it was chosen over, and what it costs |
| `aws/GOTCHAS.md` | Failures found by running the plan once, with the error text that identifies them |

The plan has been executed once end to end. Corrections from that run are folded into `CLAUDE.md`;
`aws/GOTCHAS.md` holds the detail and the error messages.

**Before Phase 0:** enable Cost Explorer in the billing console. It takes up to 24 hours to ingest,
and until it does the budget alarm cannot fire.
