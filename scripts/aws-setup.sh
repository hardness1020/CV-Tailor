#!/bin/bash

# CV-Tailor AWS Setup Script
# Quick Setup (Option 2) - No Custom Domains
#
# This script creates all AWS prerequisites for CV-Tailor infrastructure:
# - Terraform state backend (S3 + DynamoDB)
# - GitHub Actions IAM role with OIDC
#
# User: <GITHUB_USER>
# Account ID: <AWS_ACCOUNT_ID>
# Region: us-west-1

set -e  # Exit on error

# Load shared configuration
SCRIPT_DIR="$(dirname "$0")"
source "${SCRIPT_DIR}/config.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}CV-Tailor AWS Setup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "GitHub: $GITHUB_USER/$GITHUB_REPO"
echo ""

# Verify AWS CLI is configured
echo -e "${YELLOW}Verifying AWS CLI...${NC}"
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
if [ -z "$CURRENT_ACCOUNT" ]; then
  echo -e "${RED}ERROR: AWS CLI not configured or no credentials found${NC}"
  echo "Please run: aws configure"
  exit 1
fi

if [ "$CURRENT_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
  echo -e "${YELLOW}WARNING: Configured account ($CURRENT_ACCOUNT) doesn't match expected account ($AWS_ACCOUNT_ID)${NC}"
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
  AWS_ACCOUNT_ID=$CURRENT_ACCOUNT
fi

echo -e "${GREEN}✓ AWS CLI configured for account $AWS_ACCOUNT_ID${NC}"
echo ""

# ============================================================================
# Step 1: Create S3 Bucket for Terraform State
# ============================================================================

echo -e "${YELLOW}Step 1: Creating S3 bucket for Terraform state...${NC}"

if aws s3 ls "s3://$STATE_BUCKET" 2>/dev/null; then
  echo -e "${GREEN}✓ Bucket $STATE_BUCKET already exists${NC}"
else
  echo "Creating bucket..."
  aws s3api create-bucket \
    --bucket "$STATE_BUCKET" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION"

  echo "Enabling versioning..."
  aws s3api put-bucket-versioning \
    --bucket "$STATE_BUCKET" \
    --versioning-configuration Status=Enabled

  echo "Enabling encryption..."
  aws s3api put-bucket-encryption \
    --bucket "$STATE_BUCKET" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }]
    }'

  echo "Blocking public access..."
  aws s3api put-public-access-block \
    --bucket "$STATE_BUCKET" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

  echo -e "${GREEN}✓ Created bucket $STATE_BUCKET${NC}"
fi

echo ""

# ============================================================================
# Step 2: Create DynamoDB Table for State Locking
# ============================================================================

echo -e "${YELLOW}Step 2: Creating DynamoDB table for state locking...${NC}"

if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$AWS_REGION" 2>/dev/null >/dev/null; then
  echo -e "${GREEN}✓ Table $LOCK_TABLE already exists${NC}"
else
  echo "Creating table..."
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$AWS_REGION"

  echo "Waiting for table to be active..."
  aws dynamodb wait table-exists \
    --table-name "$LOCK_TABLE" \
    --region "$AWS_REGION"

  echo -e "${GREEN}✓ Created table $LOCK_TABLE${NC}"
fi

echo ""

# ============================================================================
# Step 3: Create OIDC Provider for GitHub Actions
# ============================================================================

echo -e "${YELLOW}Step 3: Creating OIDC provider for GitHub Actions...${NC}"

OIDC_PROVIDER_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$OIDC_PROVIDER_ARN" 2>/dev/null >/dev/null; then
  echo -e "${GREEN}✓ OIDC provider already exists${NC}"
else
  echo "Creating OIDC provider..."
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

  echo -e "${GREEN}✓ Created OIDC provider${NC}"
fi

echo ""

# ============================================================================
# Step 4: Create IAM Role for GitHub Actions
# ============================================================================

echo -e "${YELLOW}Step 4: Creating IAM role for GitHub Actions...${NC}"

# Create trust policy
cat > /tmp/github-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_USER}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

if aws iam get-role --role-name "$IAM_ROLE_NAME" 2>/dev/null >/dev/null; then
  echo -e "${YELLOW}Role $IAM_ROLE_NAME already exists, updating trust policy...${NC}"
  aws iam update-assume-role-policy \
    --role-name "$IAM_ROLE_NAME" \
    --policy-document file:///tmp/github-trust-policy.json
  echo -e "${GREEN}✓ Updated role trust policy${NC}"
else
  echo "Creating IAM role..."
  aws iam create-role \
    --role-name "$IAM_ROLE_NAME" \
    --assume-role-policy-document file:///tmp/github-trust-policy.json \
    --description "Role for GitHub Actions to deploy CV-Tailor"

  echo "Attaching AdministratorAccess policy..."
  aws iam attach-role-policy \
    --role-name "$IAM_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

  echo -e "${GREEN}✓ Created IAM role $IAM_ROLE_NAME${NC}"
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name "$IAM_ROLE_NAME" --query 'Role.Arn' --output text)

# Clean up temp file
rm /tmp/github-trust-policy.json

echo ""

# ============================================================================
# Summary
# ============================================================================

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Resources Created:${NC}"
echo "  ✓ S3 Bucket: $STATE_BUCKET"
echo "  ✓ DynamoDB Table: $LOCK_TABLE"
echo "  ✓ OIDC Provider: token.actions.githubusercontent.com"
echo "  ✓ IAM Role: $IAM_ROLE_NAME"
echo ""
echo -e "${YELLOW}IAM Role ARN (save this for GitHub secrets):${NC}"
echo -e "${GREEN}$ROLE_ARN${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Copy the IAM Role ARN above"
echo "2. Run Terraform:"
echo "   cd terraform"
echo "   terraform init \\"
echo "     -backend-config=\"bucket=$STATE_BUCKET\" \\"
echo "     -backend-config=\"key=production/terraform.tfstate\" \\"
echo "     -backend-config=\"region=$AWS_REGION\" \\"
echo "     -backend-config=\"encrypt=true\" \\"
echo "     -backend-config=\"dynamodb_table=$LOCK_TABLE\""
echo "   terraform plan -var-file=environments/production.tfvars -out=tfplan"
echo "   terraform apply tfplan"
echo ""
echo "3. Save Terraform outputs:"
echo "   terraform output > ../terraform_outputs.txt"
echo ""
echo "4. Configure GitHub (see docs/deployment/github-setup.md)"
echo ""
echo -e "${GREEN}Setup script completed successfully!${NC}"
