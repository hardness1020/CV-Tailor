# S3 Module Outputs

# Media Bucket Outputs
output "media_bucket_id" {
  description = "ID of the media bucket"
  value       = aws_s3_bucket.media.id
}

output "media_bucket_arn" {
  description = "ARN of the media bucket"
  value       = aws_s3_bucket.media.arn
}

output "media_bucket_name" {
  description = "Name of the media bucket"
  value       = aws_s3_bucket.media.bucket
}

output "media_bucket_domain_name" {
  description = "Domain name of the media bucket"
  value       = aws_s3_bucket.media.bucket_domain_name
}

output "media_bucket_regional_domain_name" {
  description = "Regional domain name of the media bucket"
  value       = aws_s3_bucket.media.bucket_regional_domain_name
}

# Static Bucket Outputs
output "static_bucket_id" {
  description = "ID of the static bucket"
  value       = aws_s3_bucket.static.id
}

output "static_bucket_arn" {
  description = "ARN of the static bucket"
  value       = aws_s3_bucket.static.arn
}

output "static_bucket_name" {
  description = "Name of the static bucket"
  value       = aws_s3_bucket.static.bucket
}

output "static_bucket_domain_name" {
  description = "Domain name of the static bucket"
  value       = aws_s3_bucket.static.bucket_domain_name
}

output "static_bucket_regional_domain_name" {
  description = "Regional domain name of the static bucket"
  value       = aws_s3_bucket.static.bucket_regional_domain_name
}
