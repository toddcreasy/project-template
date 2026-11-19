# CLAUDE.md

This repo is a Copier template, not a project. `template/` is what generated repos get;
`copier.yml` holds the questions and post-generation tasks.

## Rules

- Never use em dashes or en dashes in any written output, including rendered templates.
- Write in the maintainer's voice: `~/.claude/rules/writing-voice.md`. Short and direct.
- Every change to `template/` gets tested: `scripts/test-template.sh` must pass before a commit.
  It runs `bin/install-tools` first, which installs any missing tool (terraform from hashicorp/tap).
- Jinja includes resolve from the repo root: `{% include "template/_includes/..." %}`.
- A file under `template/` with a `.jinja` suffix is rendered; anything else is copied verbatim.
- Generated repos must pass their own pre-commit and CI on the first commit. If a change adds a
  file, check it ends with exactly one newline and contains nothing gitleaks flags.
- Terraform for AWS in generated repos. CDK stays only in glia-nav.
- Copier deletes the destination when a task fails, so tasks that can fail for ordinary reasons
  (hooks, network, gh auth) end in `|| echo ...` instead of failing.
