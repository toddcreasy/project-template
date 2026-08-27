# project-template

Starting point for a new personal AWS project. Copy `CLAUDE.md` into a fresh repo and Claude Code
builds the platform in phases, stopping for review at each gate.

| File | What it is |
|---|---|
| `aws/SERVICES.md` | **Start here if you are new to AWS.** How a full AWS deployment fits together: the ten jobs every deployment has to fill, which service fills each, what the alternatives are, and what it all costs |
| `CLAUDE.md` | The build plan: eleven phases, each with a checklist and a STOP gate |
| `aws/GOTCHAS.md` | Failures found by running the plan once, with the error text that identifies them |

The plan has been executed once end to end. Corrections from that run are folded into `CLAUDE.md`;
`aws/GOTCHAS.md` holds the detail and the error messages.

**Before Phase 0:** enable Cost Explorer in the billing console. It takes up to 24 hours to ingest,
and until it does the budget alarm cannot fire.
