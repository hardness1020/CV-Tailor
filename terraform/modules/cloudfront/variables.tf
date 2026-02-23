# CloudFront Module Variables

# ============================================================================
# Required Variables
# ============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
}

# ============================================================================
# Optional Variables
# ============================================================================

variable "frontend_bucket_name" {
  description = "Name for the frontend S3 bucket (auto-generated if empty)"
  type        = string
  default     = ""
}

variable "cloudfront_price_class" {
  description = "CloudFront price class (PriceClass_All, PriceClass_200, PriceClass_100)"
  type        = string
  default     = "PriceClass_100"  # US, Canada, Europe (lowest cost)
}

variable "domain_names" {
  description = "List of domain names for CloudFront (e.g., ['app.example.com'])"
  type        = list(string)
  default     = []
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for custom domain (must be in us-east-1)"
  type        = string
  default     = ""
}

variable "enable_alarms" {
  description = "Enable CloudWatch alarms for CloudFront"
  type        = bool
  default     = true
}

variable "alarm_actions" {
  description = "List of ARNs to notify when alarms trigger (e.g., SNS topics)"
  type        = list(string)
  default     = []
}
