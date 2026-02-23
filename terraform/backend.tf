# Terraform Backend Configuration
#
# Stores Terraform state in S3 with DynamoDB locking for team collaboration.
#
# Prerequisites:
#   1. Create S3 bucket: <YOUR_STATE_BUCKET>
#   2. Create DynamoDB table: <YOUR_LOCK_TABLE>
#      - Partition key: LockID (String)
#
# Setup:
#   aws s3 mb s3://<YOUR_STATE_BUCKET> --region <AWS_REGION>
#   aws s3api put-bucket-versioning \
#     --bucket <YOUR_STATE_BUCKET> \
#     --versioning-configuration Status=Enabled
#
#   aws dynamodb create-table \
#     --table-name <YOUR_LOCK_TABLE> \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region <AWS_REGION>
#
# Related Documentation:
#   - docs/deployment/production-deployment.md
#   - docs/specs/spec-deployment-v1.0.md

terraform {
  # Require Terraform 1.5 or higher
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # S3 backend for state management
  # NOTE: Comment this out for initial setup, then uncomment after creating the bucket
  backend "s3" {
    bucket         = "<YOUR_STATE_BUCKET>"
    key            = "production/terraform.tfstate"
    region         = "<AWS_REGION>"
    encrypt        = true
    dynamodb_table = "<YOUR_LOCK_TABLE>"

    # Tags for the state file
    # Note: These are applied to the S3 object, not the bucket
  }
}
