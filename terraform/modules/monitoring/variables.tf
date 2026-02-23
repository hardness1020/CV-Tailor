# Monitoring Module Variables

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

variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
  default     = ""
}

variable "enable_composite_alarms" {
  description = "Enable composite alarms for system health"
  type        = bool
  default     = true
}

variable "critical_alarm_names" {
  description = "List of critical alarm names to include in composite alarm"
  type        = list(string)
  default     = []
}

variable "ecs_log_group_name" {
  description = "Name of the ECS CloudWatch log group for metric filters"
  type        = string
  default     = ""
}
