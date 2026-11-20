# Repo traffic

One email each morning (7:00 New York) with GitHub traffic for every repo in `repos`, as an HTML table: views yesterday, views and unique visitors over 14 days, clones, and views since tracking began, then referrers (the sites visitors came from) and pages.

GitHub keeps traffic for 14 days only. Each run saves a raw snapshot per repo in the S3 bucket and folds the daily counts into `history/<owner>__<repo>.json`, so the history outlasts GitHub's window. A repo the token can't read appears under "Not fetched" in the email instead of stopping the others.

| Piece | Where |
|---|---|
| Lambda | `lambda/index.py` |
| Bucket, secret, SES identity, schedule, roles | `main.tf` |
| Your address and repo list | `terraform.tfvars` (gitignored; see `terraform.tfvars.example`) |

This sits outside `template/`, so generated repos never get it. State stays local (`terraform.tfstate` here, gitignored), like `aws/bootstrap`.

## Set up

```sh
cd ops/traffic
cp terraform.tfvars.example terraform.tfvars    # fill in
terraform init && terraform plan -out=traffic.tfplan && terraform apply traffic.tfplan
```

Then:

1. Click the SES verification link AWS emails to the address. SES sends only to verified addresses while the account is in the SES sandbox, which is enough for mail to yourself.
2. Create a fine-grained GitHub token with Administration: read on every repo in the list (the traffic API needs it; a workflow token can't have it), and store it in Terminal.app, not through a tool without a keyboard:

   ```sh
   read -rs T && aws secretsmanager put-secret-value --secret-id repo-traffic/github-token --secret-string "$T" --region us-east-1 && unset T
   ```

3. Send one now instead of waiting for the morning: `aws lambda invoke --function-name repo-traffic --region us-east-1 /tmp/out.json && cat /tmp/out.json`.

To add a repo, add it to `repos`, give the token access to it, and apply.

Replaced the per-repo traffic jobs in glia-nav and methyl-flow on 2026-11-20; their history was copied into this bucket.
