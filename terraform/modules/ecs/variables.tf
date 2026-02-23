# ECS Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# ECS Configuration
variable "cpu" {
  description = "CPU units for the task (256, 512, 1024, 2048, 4096)"
  type        = string
}

variable "memory" {
  description = "Memory for the task in MB (512, 1024, 2048, 4096, 8192, etc.)"
  type        = string
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "container_image" {
  description = "Docker image to run (leave empty to use ECR repository URL)"
  type        = string
  default     = ""
}

variable "container_port" {
  description = "Port on which the container is listening"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Path for health check endpoint"
  type        = string
  default     = "/health/"
}

# Networking
variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "security_group_id" {
  description = "ID of the security group for ECS tasks"
  type        = string
}

# IAM Roles
variable "execution_role_arn" {
  description = "ARN of the ECS execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

# Load Balancer
variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB listener (for dependency)"
  type        = string
}

# Database Configuration
variable "database_host" {
  description = "Database host address"
  type        = string
}

variable "database_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_secret_arn" {
  description = "ARN of Secrets Manager secret containing database credentials"
  type        = string
}

# Redis Configuration
variable "redis_host" {
  description = "Redis host address"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "redis_secret_arn" {
  description = "ARN of Secrets Manager secret containing Redis auth token"
  type        = string
}

# S3 Configuration
variable "s3_media_bucket" {
  description = "Name of the S3 media bucket"
  type        = string
}

variable "s3_static_bucket" {
  description = "Name of the S3 static bucket"
  type        = string
}

# Secrets
variable "app_secrets_arn" {
  description = "ARN of Secrets Manager secret containing application secrets (SECRET_KEY, etc.)"
  type        = string
}

# Additional Environment Variables
variable "additional_environment_variables" {
  description = "Additional environment variables for the container"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_container_insights" {
  description = "Enable Container Insights for the ECS cluster"
  type        = bool
  default     = true
}

# Auto Scaling
variable "enable_autoscaling" {
  description = "Enable auto-scaling for the ECS service"
  type        = bool
  default     = false
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 10
}

variable "autoscaling_cpu_target" {
  description = "Target CPU utilization percentage for auto-scaling"
  type        = number
  default     = 70
}

variable "autoscaling_memory_target" {
  description = "Target memory utilization percentage for auto-scaling"
  type        = number
  default     = 80
}

# Alarms
variable "enable_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "List of ARNs to notify when alarms trigger"
  type        = list(string)
  default     = []
}
