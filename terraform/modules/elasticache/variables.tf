# ElastiCache Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type (e.g., cache.t4g.small)"
  type        = string
}

variable "num_cache_nodes" {
  description = "Number of cache nodes (1 for standalone, 2+ for replication)"
  type        = number
  default     = 1

  validation {
    condition     = var.num_cache_nodes >= 1 && var.num_cache_nodes <= 6
    error_message = "Number of cache nodes must be between 1 and 6."
  }
}

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
}

variable "port" {
  description = "Port for Redis"
  type        = number
  default     = 6379
}

variable "snapshot_retention_limit" {
  description = "Number of days to retain automatic snapshots"
  type        = number
  default     = 5

  validation {
    condition     = var.snapshot_retention_limit >= 0 && var.snapshot_retention_limit <= 35
    error_message = "Snapshot retention must be between 0 and 35 days."
  }
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for cache subnet group"
  type        = list(string)
}

variable "security_group_id" {
  description = "ID of the security group for ElastiCache"
  type        = string
}

variable "secrets_name" {
  description = "Name/prefix of secrets in Secrets Manager"
  type        = string
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
