# S3 Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
}

variable "media_bucket_name" {
  description = "Name for the media bucket (leave empty for auto-generated)"
  type        = string
  default     = ""
}

variable "static_bucket_name" {
  description = "Name for the static bucket (leave empty for auto-generated)"
  type        = string
  default     = ""
}

variable "allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

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
