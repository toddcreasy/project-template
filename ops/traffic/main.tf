# One daily email with GitHub traffic for every repo in var.repos, as an HTML table (SES).
# Outside template/, so generated repos never get it. State stays local (terraform.tfstate here,
# gitignored), like aws/bootstrap: losing it only means re-importing a few resources.
#
#   cd ops/traffic
#   cp terraform.tfvars.example terraform.tfvars   # your address and repos
#   terraform init && terraform plan -out=traffic.tfplan && terraform apply traffic.tfplan
#
# Then: click the SES verification link AWS emails you, and put a fine-grained GitHub token with
# Administration: read on every repo into the secret (see README.md).

terraform {
  required_version = "~> 1.17"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.73"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      project    = "repo-traffic"
      managed-by = "terraform"
    }
  }
}

variable "email" {
  description = "Where the daily email goes; also the SES sender, so it must be verified."
  type        = string
}

variable "repos" {
  description = "owner/name of every repo in the email."
  type        = list(string)
}

variable "log_groups" {
  description = "CloudWatch log groups of apps whose page views log the visitor's address (a client field); the email lists those visitors."
  type        = list(string)
  default     = []
}

variable "my_ips" {
  description = "Your own addresses, left out of the visitor table."
  type        = list(string)
  default     = []
}

data "aws_caller_identity" "current" {}

locals {
  name = "repo-traffic"
}

resource "aws_s3_bucket" "history" {
  bucket = "${local.name}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "history" {
  bucket                  = aws_s3_bucket.history.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "history" {
  bucket = aws_s3_bucket.history.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Created without a value: put the GitHub token in by hand (README.md), so it never touches
# Terraform state or this public repo.
resource "aws_secretsmanager_secret" "token" {
  name        = "${local.name}/github-token"
  description = "Fine-grained GitHub token with Administration: read on every repo in the email"
}

resource "aws_sesv2_email_identity" "email" {
  email_identity = var.email
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 30
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = local.name
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "lambda" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.history.arn}/*"]
  }
  statement {
    # GetObject on a missing key returns NoSuchKey only with ListBucket; AccessDenied otherwise.
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.history.arn]
  }
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.token.arn]
  }
  statement {
    actions   = ["ses:SendEmail"]
    resources = [aws_sesv2_email_identity.email.arn]
  }
  dynamic "statement" {
    for_each = length(var.log_groups) > 0 ? [1] : []
    content {
      actions   = ["logs:StartQuery"]
      resources = [for g in var.log_groups : "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:${g}:*"]
    }
  }
  statement {
    # GetQueryResults has no resource to scope to; it reads only queries this role started.
    actions   = ["logs:GetQueryResults"]
    resources = ["*"]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_lambda_function" "traffic" {
  function_name    = local.name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.14"
  architectures    = ["arm64"]
  handler          = "index.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 120
  memory_size      = 256

  environment {
    variables = {
      REPOS            = jsonencode(var.repos)
      BUCKET           = aws_s3_bucket.history.bucket
      EMAIL            = var.email
      TOKEN_SECRET_ARN = aws_secretsmanager_secret.token.arn
      LOG_GROUPS       = jsonencode(var.log_groups)
      MY_IPS           = jsonencode(var.my_ips)
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy.lambda]
}

data "aws_iam_policy_document" "scheduler_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_trust.json
}

resource "aws_iam_role_policy" "scheduler" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.traffic.arn }]
  })
}

resource "aws_scheduler_schedule" "daily" {
  name                         = local.name
  schedule_expression          = "cron(0 7 * * ? *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.traffic.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

output "bucket" {
  value = aws_s3_bucket.history.bucket
}

output "token_secret_arn" {
  value = aws_secretsmanager_secret.token.arn
}

# A failed run (an expired token, a GitHub outage) sends no traffic email, so its absence would go
# unnoticed. This alarm emails the same address instead; confirm the SNS subscription once.
resource "aws_sns_topic" "alarm" {
  name = "${local.name}-alarm"
}

resource "aws_sns_topic_subscription" "alarm" {
  topic_arn = aws_sns_topic.alarm.arn
  protocol  = "email"
  endpoint  = var.email
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${local.name}-errors"
  alarm_description   = "The daily repo traffic run failed. Check the GitHub token first (README.md)."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.traffic.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarm.arn]
}
