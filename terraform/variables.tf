# TEMPLATE: Default values with <PLACEHOLDER> patterns must be replaced before use.
# Terraform Variables for CV-Tailor Production Infrastructure
#
# This file defines all input variables for the infrastructure.
# Actual values are set in environments/production.tfvars
#
# Usage:
#   terraform plan -var-file=environments/production.tfvars
#   terraform apply -var-file=environments/production.tfvars

# ============================================================================
# Global Configuration
# ============================================================================

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "cv-tailor"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "<AWS_REGION>"
}

# ============================================================================
# Networking
# ============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["<AWS_REGION>a", "<AWS_REGION>b"]
}

# ============================================================================
# ECS Configuration
# ============================================================================

variable "ecs_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = string
  default     = "2048"
}

variable "ecs_memory" {
  description = "Memory (MB) for ECS task"
  type        = string
  default     = "4096"
}

variable "desired_count" {
  description = "Desired number of ECS tasks to run"
  type        = number
  default     = 2

  validation {
    condition     = var.desired_count >= 1
    error_message = "Desired count must be at least 1."
  }
}

variable "container_image" {
  description = "Docker image for backend container (ECR URI)"
  type        = string
  default     = ""  # Will be provided via tfvars or set after ECR creation
}

variable "additional_environment_variables" {
  description = "Additional environment variables for ECS tasks"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

# ============================================================================
# RDS Configuration
# ============================================================================

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.small"
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS (GB)"
  type        = number
  default     = 100

  validation {
    condition     = var.rds_allocated_storage >= 20
    error_message = "RDS storage must be at least 20 GB."
  }
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ deployment for RDS"
  type        = bool
  default     = true
}

variable "rds_backup_retention_days" {
  description = "Number of days to retain RDS backups"
  type        = number
  default     = 30

  validation {
    condition     = var.rds_backup_retention_days >= 7 && var.rds_backup_retention_days <= 35
    error_message = "Backup retention must be between 7 and 35 days."
  }
}

variable "rds_max_allocated_storage" {
  description = "Maximum storage for RDS auto-scaling (GB)"
  type        = number
  default     = 1000

  validation {
    condition     = var.rds_max_allocated_storage >= var.rds_allocated_storage
    error_message = "Max allocated storage must be greater than or equal to allocated storage."
  }
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
  default     = true
}

variable "database_name" {
  description = "Name of the PostgreSQL database"
  type        = string
  default     = "cv_tailor"
}

variable "database_username" {
  description = "Master username for PostgreSQL"
  type        = string
  default     = "cv_tailor_admin"
}

# ============================================================================
# ElastiCache Configuration
# ============================================================================

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.small"
}

variable "redis_num_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1

  validation {
    condition     = var.redis_num_nodes >= 1
    error_message = "Must have at least 1 Redis node."
  }
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

# ============================================================================
# S3 Configuration
# ============================================================================

variable "s3_media_bucket_name" {
  description = "Name for S3 media bucket (leave empty for auto-generated)"
  type        = string
  default     = ""
}

variable "s3_static_bucket_name" {
  description = "Name for S3 static files bucket (leave empty for auto-generated)"
  type        = string
  default     = ""
}

variable "s3_allowed_origins" {
  description = "List of allowed CORS origins for S3 buckets"
  type        = list(string)
  default     = ["*"]
}

# ============================================================================
# CloudFront Configuration (Frontend CDN)
# ============================================================================

variable "cloudfront_frontend_bucket_name" {
  description = "Name for CloudFront frontend S3 bucket (leave empty for auto-generated)"
  type        = string
  default     = ""
}

variable "cloudfront_price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_200, PriceClass_100)"
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_All, PriceClass_200, or PriceClass_100."
  }
}

variable "cloudfront_domain_names" {
  description = "List of domain names for CloudFront (e.g., ['app.example.com'])"
  type        = list(string)
  default     = []
}

variable "cloudfront_acm_certificate_arn" {
  description = "ACM certificate ARN for CloudFront custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

# ============================================================================
# ALB Configuration
# ============================================================================

variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS (optional, can be created manually)"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for the application (e.g., api.cv-tailor.com)"
  type        = string
  default     = ""
}

variable "alb_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = false
}

# ============================================================================
# Monitoring Configuration
# ============================================================================

variable "alarm_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = ""
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring"
  type        = bool
  default     = true
}

# ============================================================================
# Secrets Manager
# ============================================================================

variable "secrets_name" {
  description = "Name of AWS Secrets Manager secret containing application secrets"
  type        = string
  default     = "<YOUR_SECRETS_NAME>"
}

# ============================================================================
# Cost Optimization
# ============================================================================

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway (required for private subnets to access internet)"
  type        = bool
  default     = true
}

variable "nat_gateway_count" {
  description = "Number of NAT Gateways (1 for minimal cost, 2+ for HA, 0 to disable)"
  type        = number
  default     = 1

  validation {
    condition     = var.nat_gateway_count >= 0
    error_message = "NAT Gateway count must be 0 or greater."
  }
}
