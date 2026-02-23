#!/bin/bash
# TEMPLATE: Replace all <PLACEHOLDER> values with your actual AWS/deployment configuration.
# CV Tailor Production Configuration
# Shared configuration for all deployment and management scripts

# AWS Configuration
export AWS_REGION="<AWS_REGION>"
export AWS_ACCOUNT_ID="<AWS_ACCOUNT_ID>"

# GitHub Configuration
export GITHUB_USER="<GITHUB_USER>"
export GITHUB_REPO="CV-Tailor"

# ECS Configuration
export CLUSTER_NAME="<YOUR_ECS_CLUSTER>"
export SERVICE_NAME="<YOUR_ECS_SERVICE>"

# Database Configuration
export DB_INSTANCE="<YOUR_RDS_INSTANCE>"

# Cache Configuration
export REDIS_GROUP="<YOUR_REDIS_GROUP>"

# Load Balancer Configuration
export ALB_NAME="<YOUR_ALB_NAME>"
export TG_NAME="<YOUR_TARGET_GROUP>"

# ECR Configuration
export ECR_REPOSITORY="<YOUR_ECR_REPOSITORY>"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# S3 Configuration
export S3_BUCKET="<YOUR_S3_BUCKET>"

# CloudFront Configuration
export CLOUDFRONT_ID="<YOUR_CLOUDFRONT_ID>"

# CloudWatch Logs Configuration
export LOG_GROUP="<YOUR_LOG_GROUP>"

# Terraform State Configuration
export STATE_BUCKET="<YOUR_STATE_BUCKET>"
export LOCK_TABLE="<YOUR_LOCK_TABLE>"

# IAM Configuration
export IAM_ROLE_NAME="GitHubActionsRole"

# Production URLs (Custom Domains)
export FRONTEND_URL="https://<YOUR_DOMAIN>"
export API_URL="https://api.<YOUR_DOMAIN>"

