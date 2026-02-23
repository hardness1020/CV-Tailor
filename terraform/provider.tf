# AWS Provider Configuration
#
# Configures the AWS provider for Terraform.
# Uses AWS credentials from environment variables or ~/.aws/credentials
#
# Environment Variables:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_REGION (optional, defaults to us-west-1)
#
# Related Documentation:
#   - docs/deployment/production-deployment.md

provider "aws" {
  region = var.aws_region

  # Default tags applied to all resources
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      CostCenter  = "engineering"
      Owner       = "devops-team"
    }
  }
}

# Data source for current AWS account details
data "aws_caller_identity" "current" {}

# Data source for available AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}
