# One-time, per AWS account: the shared Terraform state bucket, the GitHub OIDC provider, and
# cost allocation tag activation. Every generated project depends on all three.
#
#   cd aws/bootstrap
#   terraform init
#   terraform apply -var state_bucket=<name> -var aws_region=<region>
#
# State for this stack stays local (terraform.tfstate here, gitignored). It holds three long-lived
# resources; losing it only means re-importing them.

terraform {
  required_version = ">= 1.11"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket" {
  description = "Must match tf_state_bucket in each project's Copier answers"
  type        = string
}

variable "create_github_oidc_provider" {
  description = <<-EOT
    Only one GitHub OIDC provider can exist per account. If a CDK project (glia-nav) already made
    one, set false. Check with: aws iam list-open-id-connect-providers
  EOT
  type        = bool
  default     = true
}

variable "activate_cost_tags" {
  description = "Fails until the tag keys have appeared in a day of billing data. Apply once with false, then flip to true."
  type        = bool
  default     = false
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      project    = "account-bootstrap"
      managed-by = "terraform"
    }
  }
}

resource "aws_s3_bucket" "state" {
  bucket = var.state_bucket
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_openid_connect_provider" "github" {
  count          = var.create_github_oidc_provider ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_ce_cost_allocation_tag" "this" {
  for_each = var.activate_cost_tags ? toset(["project", "env"]) : toset([])
  tag_key  = each.value
  status   = "Active"
}

output "state_bucket" {
  value = aws_s3_bucket.state.bucket
}
