# ElastiCache Module Outputs

output "replication_group_id" {
  description = "ID of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.main.id
}

output "replication_group_arn" {
  description = "ARN of the ElastiCache replication group"
  value       = aws_elasticache_replication_group.main.arn
}

output "primary_endpoint_address" {
  description = "Address of the primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
  sensitive   = true
}

output "reader_endpoint_address" {
  description = "Address of the reader endpoint (for read replicas)"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
  sensitive   = true
}

output "port" {
  description = "Port the Redis cluster is listening on"
  value       = var.port
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret containing Redis auth token"
  value       = aws_secretsmanager_secret.redis_auth_token.arn
}

output "secret_name" {
  description = "Name of the Secrets Manager secret containing Redis auth token"
  value       = aws_secretsmanager_secret.redis_auth_token.name
}
