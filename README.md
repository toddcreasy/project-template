# project-template

Starting point for a new personal AWS project. Copy `CLAUDE.md` into a fresh repo and Claude Code
builds the platform in phases, stopping for review at each gate. Once the build is done, swap in
`aws/CLAUDE.md`, which carries the operating rules and the AWS lessons without the phases.

| File | What it is |
|---|---|
| `aws/SERVICES.md` | **Start here if you are new to AWS.** How a full AWS deployment fits together: the ten jobs every deployment has to fill, which service fills each, what the alternatives are, and what it all costs |
| `CLAUDE.md` | The build plan: eleven phases, each with a checklist and a STOP gate |
| `aws/CLAUDE.md` | The steady-state operating file. What `CLAUDE.md` becomes once Phase 10 archives the phases into `docs/SETUP.md`. Drop it into an already-deployed project |
| `aws/GOTCHAS.md` | Failures found by running the plan once, with the error text that identifies them |
| `LAYOUT.md` | Every directory, what goes in it, and which of them are real conventions rather than choices |

The plan has been executed once end to end. Corrections from that run are folded into `CLAUDE.md`;
`aws/GOTCHAS.md` holds the detail and the error messages.

**Before Phase 0:** enable Cost Explorer in the billing console. It takes up to 24 hours to ingest,
and until it does the budget alarm cannot fire.
