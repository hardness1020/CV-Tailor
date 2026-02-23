# Terraform Outputs for CV-Tailor Production Infrastructure
#
# These outputs provide important information about the deployed infrastructure.
# Use: terraform output <output_name>
#
# Example:
#   terraform output alb_dns_name
#   terraform output rds_endpoint

# ============================================================================
# Networking Outputs
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

# ============================================================================
# Load Balancer Outputs
# ============================================================================

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "alb_zone_id" {
  description = "Route53 Zone ID of the ALB"
  value       = module.alb.alb_zone_id
}

output "alb_url" {
  description = "Full HTTPS URL of the application"
  value       = "https://${module.alb.alb_dns_name}"
}

# ============================================================================
# ECS Outputs
# ============================================================================

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecs.ecr_repository_url
}

# ============================================================================
# Database Outputs
# ============================================================================

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "Name of the PostgreSQL database"
  value       = module.rds.database_name
}

output "rds_port" {
  description = "Port of the RDS instance"
  value       = module.rds.port
}

# ============================================================================
# Cache Outputs
# ============================================================================

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.elasticache.primary_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Port of the Redis cluster"
  value       = module.elasticache.port
}

# ============================================================================
# Storage Outputs
# ============================================================================

output "s3_media_bucket" {
  description = "Name of the S3 media bucket"
  value       = module.s3.media_bucket_name
}

output "s3_static_bucket" {
  description = "Name of the S3 static files bucket"
  value       = module.s3.static_bucket_name
}

output "s3_media_bucket_arn" {
  description = "ARN of the S3 media bucket"
  value       = module.s3.media_bucket_arn
}

# ============================================================================
# CloudFront Outputs (Frontend CDN)
# ============================================================================

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution for frontend"
  value       = module.cloudfront.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = module.cloudfront.cloudfront_domain_name
}

output "frontend_url" {
  description = "Frontend application URL (CloudFront)"
  value       = "https://${module.cloudfront.cloudfront_domain_name}"
}

output "frontend_bucket_name" {
  description = "Name of the S3 bucket for frontend static files"
  value       = module.cloudfront.frontend_bucket_name
}

# ============================================================================
# Monitoring Outputs
# ============================================================================

output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

output "sns_topic_arn" {
  description = "ARN of SNS topic for alarms"
  value       = module.monitoring.sns_topic_arn
}

# ============================================================================
# Security Outputs
# ============================================================================

output "ecs_task_role_arn" {
  description = "ARN of the ECS task IAM role"
  value       = module.security.ecs_task_role_arn
}

output "ecs_execution_role_arn" {
  description = "ARN of the ECS execution IAM role"
  value       = module.security.ecs_execution_role_arn
}

# ============================================================================
# Deployment Information
# ============================================================================

output "deployment_info" {
  description = "Important deployment information"
  value = {
    environment          = var.environment
    region               = var.aws_region
    account_id          = data.aws_caller_identity.current.account_id
    application_url     = "https://${module.alb.alb_dns_name}"
    ecr_repository      = module.ecs.ecr_repository_url
    secrets_name        = var.secrets_name
  }
}

# ============================================================================
# Next Steps
# ============================================================================

output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value = <<-EOT

    ✅ Infrastructure deployed successfully!

    Next steps:

    1. Configure DNS:
       Point your domain to: ${module.alb.alb_dns_name}

    2. Create secrets in AWS Secrets Manager:
       aws secretsmanager create-secret \
         --name ${var.secrets_name} \
         --secret-string file://secrets-production.json \
         --region ${var.aws_region}

    3. Push Docker image to ECR:
       aws ecr get-login-password --region ${var.aws_region} | \
         docker login --username AWS --password-stdin ${module.ecs.ecr_repository_url}

       docker build -t cv-tailor-backend:latest backend/
       docker tag cv-tailor-backend:latest ${module.ecs.ecr_repository_url}:latest
       docker push ${module.ecs.ecr_repository_url}:latest

    4. Run database migrations:
       aws ecs execute-command \
         --cluster ${module.ecs.cluster_name} \
         --task <TASK_ID> \
         --container backend \
         --command "uv run python manage.py migrate" \
         --interactive

    5. Monitor deployment:
       CloudWatch Dashboard: ${module.monitoring.dashboard_url}

    6. Test the application:
       curl -I https://${module.alb.alb_dns_name}/health/

    For detailed deployment instructions, see:
    docs/deployment/production-deployment.md
  EOT
}
