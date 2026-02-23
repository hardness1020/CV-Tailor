# CV-Tailor Infrastructure - Main Configuration
#
# This is the root Terraform configuration that orchestrates all modules.
#
# Architecture:
#   - VPC with public/private subnets across 2 AZs
#   - Application Load Balancer (ALB) in public subnets
#   - ECS Fargate tasks in private subnets
#   - RDS PostgreSQL Multi-AZ in private subnets
#   - ElastiCache Redis in private subnets
#   - S3 buckets for media and static files
#   - CloudWatch monitoring and alarms
#
# Related Documentation:
#   - docs/specs/spec-deployment-v1.0.md
#   - terraform/README.md

# ============================================================================
# VPC Module
# ============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = var.enable_nat_gateway
  nat_gateway_count  = var.nat_gateway_count
}

# ============================================================================
# Security Module (IAM Roles & Security Groups)
# ============================================================================

module "security" {
  source = "./modules/security"

  project_name      = var.project_name
  environment       = var.environment
  aws_region        = var.aws_region
  vpc_id            = module.vpc.vpc_id
  s3_media_bucket   = var.s3_media_bucket_name != "" ? var.s3_media_bucket_name : "${var.project_name}-${var.environment}-media"
  s3_static_bucket  = var.s3_static_bucket_name != "" ? var.s3_static_bucket_name : "${var.project_name}-${var.environment}-static"
  secrets_name      = var.secrets_name
}

# ============================================================================
# RDS Module (PostgreSQL Database)
# ============================================================================

module "rds" {
  source = "./modules/rds"

  project_name            = var.project_name
  environment             = var.environment
  database_name           = var.database_name
  database_username       = var.database_username
  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_allocated_storage
  max_allocated_storage   = var.rds_max_allocated_storage
  multi_az                = var.rds_multi_az
  backup_retention_days   = var.rds_backup_retention_days
  deletion_protection     = var.rds_deletion_protection
  enable_performance_insights = var.enable_detailed_monitoring
  private_subnet_ids      = module.vpc.private_subnet_ids
  security_group_id       = module.security.rds_security_group_id
  secrets_name            = var.secrets_name
  enable_alarms           = true
  alarm_actions           = [module.monitoring.sns_topic_arn]

  depends_on = [module.vpc, module.security]
}

# ============================================================================
# ElastiCache Module (Redis)
# ============================================================================

module "elasticache" {
  source = "./modules/elasticache"

  project_name              = var.project_name
  environment               = var.environment
  node_type                 = var.redis_node_type
  num_cache_nodes           = var.redis_num_nodes
  engine_version            = var.redis_engine_version
  snapshot_retention_limit  = 5
  private_subnet_ids        = module.vpc.private_subnet_ids
  security_group_id         = module.security.elasticache_security_group_id
  secrets_name              = var.secrets_name
  enable_alarms             = true
  alarm_actions             = [module.monitoring.sns_topic_arn]

  depends_on = [module.vpc, module.security]
}

# ============================================================================
# S3 Module (Media & Static Files)
# ============================================================================

module "s3" {
  source = "./modules/s3"

  project_name        = var.project_name
  environment         = var.environment
  media_bucket_name   = var.s3_media_bucket_name
  static_bucket_name  = var.s3_static_bucket_name
  allowed_origins     = var.s3_allowed_origins
  enable_alarms       = true
  alarm_actions       = [module.monitoring.sns_topic_arn]
}

# ============================================================================
# CloudFront Module (Frontend CDN)
# ============================================================================

module "cloudfront" {
  source = "./modules/cloudfront"

  project_name            = var.project_name
  environment             = var.environment
  frontend_bucket_name    = var.cloudfront_frontend_bucket_name
  cloudfront_price_class  = var.cloudfront_price_class
  domain_names            = var.cloudfront_domain_names
  acm_certificate_arn     = var.cloudfront_acm_certificate_arn
  enable_alarms           = true
  alarm_actions           = [module.monitoring.sns_topic_arn]

  # Note: depends_on removed - implicit dependency via alarm_actions is sufficient
}

# ============================================================================
# ALB Module (Application Load Balancer)
# ============================================================================

module "alb" {
  source = "./modules/alb"

  project_name               = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  public_subnet_ids          = module.vpc.public_subnet_ids
  security_group_id          = module.security.alb_security_group_id
  container_port             = 8000
  health_check_path          = "/health/"
  certificate_arn            = var.certificate_arn
  enable_deletion_protection = var.alb_deletion_protection
  enable_access_logs         = false  # Disabled for minimal setup
  enable_alarms              = true
  alarm_actions              = [module.monitoring.sns_topic_arn]

  depends_on = [module.vpc, module.security]
}

# ============================================================================
# Application Secrets (SECRET_KEY, etc.)
# ============================================================================

# Generate Django SECRET_KEY
resource "random_password" "django_secret_key" {
  length  = 50
  special = true
}

# Store application secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.secrets_name}/app-secrets"
  description             = "Application secrets for ${var.project_name} ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-app-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    secret_key = random_password.django_secret_key.result
  })
}

# ============================================================================
# ECS Module (Container Orchestration)
# ============================================================================

module "ecs" {
  source = "./modules/ecs"

  project_name        = var.project_name
  environment         = var.environment
  aws_region          = var.aws_region
  cpu                 = var.ecs_cpu
  memory              = var.ecs_memory
  desired_count       = var.desired_count
  container_image     = var.container_image
  container_port      = 8000
  health_check_path   = "/health/"
  # COST OPTIMIZATION: Use public subnets to eliminate NAT Gateway cost
  # ECS tasks get public IPs but are protected by ALB security groups
  private_subnet_ids  = module.vpc.public_subnet_ids
  security_group_id   = module.security.ecs_tasks_security_group_id
  execution_role_arn  = module.security.ecs_execution_role_arn
  task_role_arn       = module.security.ecs_task_role_arn
  target_group_arn    = module.alb.target_group_arn
  alb_listener_arn    = var.certificate_arn != "" ? module.alb.https_listener_arn : module.alb.http_listener_arn

  # Database configuration
  database_host       = module.rds.address
  database_port       = module.rds.port
  database_name       = module.rds.database_name
  database_secret_arn = module.rds.secret_arn

  # Redis configuration
  redis_host       = module.elasticache.primary_endpoint_address
  redis_port       = module.elasticache.port
  redis_secret_arn = module.elasticache.secret_arn

  # S3 configuration
  s3_media_bucket  = module.s3.media_bucket_name
  s3_static_bucket = module.s3.static_bucket_name

  # Application secrets
  app_secrets_arn = aws_secretsmanager_secret.app_secrets.arn

  # Additional environment variables
  additional_environment_variables = var.additional_environment_variables

  # Logging
  log_retention_days         = 7
  enable_container_insights  = var.enable_detailed_monitoring

  # Auto-scaling (disabled for minimal setup)
  enable_autoscaling = false

  # Alarms
  enable_alarms  = true
  alarm_actions  = [module.monitoring.sns_topic_arn]

  depends_on = [
    module.vpc,
    module.security,
    module.rds,
    module.elasticache,
    module.s3,
    module.alb
  ]
}

# ============================================================================
# Monitoring Module (CloudWatch Dashboard & Alarms)
# ============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  alarm_email     = var.alarm_email

  # Disable composite alarm for initial deployment (alarms don't exist yet)
  enable_composite_alarms = false
  critical_alarm_names = []

  # Construct log group name directly to avoid circular dependency
  # NOTE: Log group is created by ECS module, but we can't add depends_on due to circular dependency
  # The log metric filter will be created on next apply after ECS creates the log group
  ecs_log_group_name = ""  # Disabled for initial deployment
}
