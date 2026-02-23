# Security Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resource ARNs"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "s3_media_bucket" {
  description = "Name of the S3 media bucket"
  type        = string
}

variable "s3_static_bucket" {
  description = "Name of the S3 static bucket"
  type        = string
}

variable "secrets_name" {
  description = "Name/prefix of secrets in Secrets Manager"
  type        = string
}
