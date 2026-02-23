# TEMPLATE: Replace all <PLACEHOLDER> values with your actual configuration before use.
# Production Environment Configuration for CV-Tailor
#
# This file contains production-specific variable values.
#
# Usage:
#   terraform plan -var-file=environments/production.tfvars
#   terraform apply -var-file=environments/production.tfvars
#
# SECURITY: This file may contain sensitive values. Consider using:
#   - AWS Secrets Manager for secrets
#   - Environment variables for sensitive values
#   - .gitignore to exclude from version control

# ============================================================================
# Global Configuration
# ============================================================================

project_name = "cv-tailor"
environment  = "production"
aws_region   = "<AWS_REGION>"

# ============================================================================
# Networking
# ============================================================================

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["<AWS_REGION>a", "<AWS_REGION>c"]

# NAT Gateway configuration
# DISABLED for cost optimization - ECS tasks use public subnets
enable_nat_gateway = false
nat_gateway_count  = 0  # Saves ~$35-40/month

# ============================================================================
# ECS Configuration
# ============================================================================

ecs_cpu    = "1024"  # 1 vCPU (reduced from 2 for cost savings)
ecs_memory = "2048"  # 2 GB RAM (reduced from 4 for cost savings)

desired_count = 2  # Run 2 tasks for high availability

# Docker image (set after pushing to ECR)
# Example: "<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor:latest"
container_image = "<AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/cv-tailor/production:latest"

# ============================================================================
# RDS Configuration
# ============================================================================

rds_instance_class        = "db.t4g.micro"  # 1 vCPU, 1 GB RAM (Free Tier eligible - 750 hours/month)
rds_allocated_storage     = 20              # 20 GB SSD (Free Tier eligible - 20 GB included)
rds_multi_az              = false           # Single-AZ for cost savings (saves ~$20/month)
rds_backup_retention_days = 7               # 7 days (Free Tier includes automated backups)

database_name     = "cv_tailor"
database_username = "cv_tailor_admin"
# NOTE: Password will be auto-generated and stored in Secrets Manager

# ============================================================================
# ElastiCache Configuration
# ============================================================================

redis_node_type     = "cache.t4g.micro"  # 1 vCPU, 0.5 GB RAM (reduced for cost savings)
redis_num_nodes     = 1                  # 1 node for cost optimization
redis_engine_version = "7.0"

# ============================================================================
# S3 Configuration
# ============================================================================

# Leave empty for auto-generated names based on project_name and environment
s3_media_bucket_name  = ""  # Will be: <YOUR_S3_BUCKET>-media
s3_static_bucket_name = ""  # Will be: <YOUR_S3_BUCKET>-static

# ============================================================================
# CloudFront Configuration (Frontend CDN)
# ============================================================================

# Frontend S3 bucket (auto-generated if empty)
cloudfront_frontend_bucket_name = ""  # Will be: <YOUR_S3_BUCKET>-frontend

# Price class (PriceClass_100 = US/Canada/Europe, lowest cost)
cloudfront_price_class = "PriceClass_100"

# Custom domain names (SKIPPED for quick setup)
# Leave empty to use CloudFront default domain (e.g., d1234567890.cloudfront.net)
cloudfront_domain_names = []

# ACM certificate ARN for custom domain (SKIPPED for quick setup)
# Leave empty to use CloudFront default certificate
cloudfront_acm_certificate_arn = ""

# ============================================================================
# ALB & Domain Configuration
# ============================================================================

# ACM certificate ARN for HTTPS (SKIPPED for quick setup)
# Leave empty to use HTTP on ALB (not recommended for production)
certificate_arn = ""  # Empty = HTTP only

# Domain name for the application (SKIPPED for quick setup)
# Leave empty to use ALB DNS name
domain_name = ""  # Empty = use ALB DNS

# ============================================================================
# Monitoring Configuration
# ============================================================================

# Email for CloudWatch alarm notifications
alarm_email = "<YOUR_EMAIL>"

# Enable detailed monitoring (1-minute metrics vs 5-minute)
enable_detailed_monitoring = true

# ============================================================================
# Secrets Manager
# ============================================================================

secrets_name = "cv-tailor/production"

# ============================================================================
# Cost Estimates (Monthly) - FREE TIER OPTIMIZED CONFIGURATION
# ============================================================================

# AWS FREE TIER (First 12 Months):
# - RDS (db.t4g.micro, 20GB):           $0 (750 hours/month included)
# - ElastiCache (cache.t4g.micro):      $10-13 (NOT included in free tier)
# - ECS Fargate (2 tasks, 1vCPU/2GB):   $18-22
# - ALB:                                $20-25
# - NAT Gateway:                        $0 (REMOVED - saves $35-40)
# - S3 (5 GB storage):                  $0 (5 GB included in free tier)
# - CloudFront (50 GB data transfer):   $0 (50 GB/month included)
# - CloudWatch Logs (5 GB ingestion):   $0 (5 GB included in free tier)
# ------------------------------------------------
# TOTAL (with Free Tier):               ~$48-60/month
# TOTAL (after 12 months):              ~$68-85/month
#
# FREE TIER BENEFITS (12 months):
# - RDS: 750 hours/month (enough for 1 instance 24/7)
# - RDS: 20 GB storage included
# - S3: 5 GB storage, 20,000 GET, 2,000 PUT requests
# - CloudFront: 50 GB data transfer out, 2M HTTP/HTTPS requests
# - CloudWatch: 10 custom metrics, 10 alarms, 5 GB logs
#
# Trade-offs of this configuration:
# - Reduced RDS memory (1 GB vs 2 GB) - adequate for dev/staging
# - Single-AZ RDS (no automatic failover)
# - Limited storage (20 GB vs 50 GB)
#
# Upgrade Path (when needed):
# - Change rds_instance_class to "db.t4g.small" for 2 GB RAM
# - Increase rds_allocated_storage to 50+ GB
# - Enable rds_multi_az for high availability
# - Expected cost after upgrade: ~$75-99/month
