#!/usr/bin/env bash
# Render every variant of the template into .test-output/ and run the checks a generated repo's
# CI runs. Installs any missing tools first with bin/install-tools.
# Copier tasks are skipped because they prompt and push; setup_env.py and the leak check are
# exercised directly instead.
set -euo pipefail
cd "$(dirname "$0")/.."
bin/install-tools
OUT=.test-output
TF=$(command -v terraform)
rm -rf "$OUT" && mkdir -p "$OUT"

render() {
  local name=$1; shift
  uvx --from "copier>=9.5,<10" copier copy --trust --skip-tasks --defaults --vcs-ref HEAD --quiet "$@" . "$OUT/$name"
}

render plain -d project_name=plain-demo -d description="Plain demo" -d license=MIT
render bare -d project_name=bare-demo -d use_python=false -d use_github_actions=false -d license=none
render aws-min -d project_name=aws-min -d use_aws=true
render aws-all -d project_name=aws-all -d use_aws=true \
  -d 'aws_services=["s3","aurora","apprunner","lambda","bedrock","agentcore","frontend","batch","static_site"]' \
  -d extra_env_vars="NCBI_API_KEY, LOG_LEVEL, CONTACT_NAME"

for d in "$OUT"/*/; do
  name=$(basename "$d")
  echo "== $name"
  (
    cd "$d"
    git init -q -b main
    if grep -rnE '<[A-Z_]{4,}>' --include='*.md' . | grep -vE 'AWS_ACCOUNT_ID|SSO_PORTAL_URL|PERMISSION_SET'; then
      echo "unfilled placeholder"; exit 1
    fi
    if git ls-files -oz --exclude-standard | xargs -0 perl -CSD -ne 'if (/[\x{2013}\x{2014}]/) { print "$ARGV:$.: $_"; $f = 1 } close ARGV if eof; END { exit !$f }'; then
      echo "en or em dash in output"; exit 1
    fi
    for f in $(git ls-files --others --exclude-standard); do
      if [ -s "$f" ] && [ -n "$(tail -c1 "$f")" ]; then echo "$f: no trailing newline"; exit 1; fi
      if [ -s "$f" ] && [ -z "$(tail -c2 "$f" | tr -d '\n')" ]; then echo "$f: extra blank line at end"; exit 1; fi
      if grep -qE '[[:space:]]+$' "$f"; then echo "$f: trailing whitespace"; exit 1; fi
    done
    if [ -f pyproject.toml ]; then
      uv sync -q
      uv run ruff check -q .
      uv run ruff format --check -q .
      uv run pytest -q
    fi
    if [ -d infra ]; then
      "$TF" -chdir=infra fmt -check -recursive
      "$TF" -chdir=infra init -backend=false -input=false >/dev/null
      "$TF" -chdir=infra validate
      (cd infra && { tflint --init >/dev/null 2>&1 || true; } && tflint)
    fi

    # Leak checks: a clean tree passes, a planted email and a planted .env value both fail.
    printf "TF_VAR_alert_email='someone.real@gmail.com'\n" > .env # gitleaks:allow
    git add -A && git -c user.email=t@example.com -c user.name=test commit -qm init
    gitleaks git --config .gitleaks.toml --redact --exit-code 1 . 2>/dev/null
    echo "contact: someone.real@gmail.com" > leak.txt # gitleaks:allow
    if python3 scripts/check_env_leaks.py leak.txt >/dev/null; then
      echo "env leak check missed a value"; exit 1
    fi
    if gitleaks dir --config .gitleaks.toml --redact --exit-code 1 leak.txt >/dev/null 2>&1; then
      echo "gitleaks missed a personal email"; exit 1
    fi
    rm leak.txt .env
    echo "ok"
  )
done
