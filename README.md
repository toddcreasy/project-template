# project-template

New-project generator for every repo I start. It asks what the project uses, writes the scaffold,
fills `.env`, and pushes a first commit to a new GitHub repo.

```bash
bin/new-project my-repo              # creates ~/workspace/my-repo
# or, without a clone of this repo:
uvx --from "copier>=9.5,<10" copier copy --trust gh:toddcreasy/project-template ~/workspace/my-repo
```

`bin/new-project` needs Homebrew. Through `bin/install-tools` it installs whatever is missing of `uv`, `gh`, `gitleaks`,
`terraform`, and `tflint` before asking anything. Terraform always comes from
`brew install hashicorp/tap/terraform`; Homebrew core's copy is frozen at 1.5.7, so the script
replaces it if that is what's installed. tflint is no longer in Homebrew, so it comes from the
GitHub release, checksum-verified, into `~/.local/bin`. Log in to `gh` first if you want the
GitHub repo created. The `uvx` route skips the installs, so bring those tools yourself.

## What it asks

| Question | Effect |
|---|---|
| Name, description, license | README, `pyproject.toml`, Apache 2.0 (default) or MIT `LICENSE`, or none |
| Python? version? | uv, ruff, pytest, pre-commit, src layout, `settings.py` built from the env vars |
| GitHub Actions? | `ci.yml` and Dependabot. The secret and personal-info scan job is always in it |
| Create GitHub repo? visibility | `gh repo create --push` after the first commit |
| AWS? region, profile, budget, services | Terraform in `infra/`, and a phased build plan in `CLAUDE.md` with only the chosen services |
| Local Postgres? | `compose.yaml` with pgvector on Postgres 17, a random password in `.env`, Docker Desktop installed if missing |
| Extra env vars | Added to `.env.example`; names with KEY, TOKEN, SECRET, or PASSWORD get hidden input |
| Env store folder | Where every repo's `.env` copy lives (default `~/workspace/envs`) |

Then `scripts/setup_env.py` asks for each `.env` value, writes `.env`, and copies it to
`~/workspace/envs/<repo>.env`. On a fresh clone, `python3 scripts/setup_env.py --pull` restores it.
`--github` pushes secret and private values to GitHub Actions secrets.

## What every generated repo gets

- **Leak protection at commit time.** Pre-commit runs gitleaks (default key rules plus personal
  email, phone, SSN, and street address in `.gitleaks.toml`) and `check_env_leaks.py`, which
  blocks any secret or private value from your actual `.env`, whatever it looks like.
- **The same scan in CI**, over the full history, on every push and PR.
- Large-file guard (1 MB) and a `.gitignore` that keeps FASTQ, BAM, VCF, h5ad, and `data/` out.
- `CLAUDE.md` with the operating rules and a checklist of what is left to set up.
- Python repos get `docs/layout.md`: what each directory is for, and which are real conventions.

## AWS

Terraform for every new project; glia-nav stays on CDK.

**Once per AWS account**, before the first AWS project: enable Cost Explorer in the billing console
(24 hours to ingest), then apply `aws/bootstrap`. It makes the shared state bucket and the GitHub
OIDC provider, and later activates the cost allocation tags. See the comments in
`aws/bootstrap/main.tf`, including what to do if glia-nav already created the OIDC provider.

| File | What it is |
|---|---|
| `aws/SERVICES.md` | **Start here if you are new to AWS.** The ten jobs every deployment fills, which service fills each, the alternatives, and the cost |
| `aws/LAYOUT.md` | Every directory in the AWS layout, and which are real conventions rather than choices |
| `aws/GOTCHAS.md` | Failures from the glia-nav build with their error text, plus the Terraform traps the template avoids |
| `aws/bootstrap/` | One-time account setup |

## Updating

Template fixes reach existing generated repos with `uvx --from "copier>=9.5,<10" copier update --trust`
inside the repo. Copier diffs your answers and merges; review the result like any PR.

## Working on the template

Files under `template/` are rendered; `template/_includes/` holds the CLAUDE.md bodies and the env
var list they share. `scripts/test-template.sh` renders four variants and runs ruff, pytest,
terraform validate, tflint, and the leak checks on each. It runs `bin/install-tools` first, so
missing tools get installed. Run it before pushing.
