output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.postgresql.id
}

output "db_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.postgresql.arn
}

output "db_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgresql.endpoint
}

output "db_instance_hosted_zone_id" {
  description = "RDS instance hosted zone ID"
  value       = aws_db_instance.postgresql.hosted_zone_id
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.postgresql.port
}

output "db_instance_status" {
  description = "RDS instance status"
  value       = aws_db_instance.postgresql.status
}

output "db_instance_username" {
  description = "RDS instance master username"
  value       = aws_db_instance.postgresql.username
}

output "db_instance_password" {
  description = "RDS instance master password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "db_instance_database_name" {
  description = "RDS instance database name"
  value       = aws_db_instance.postgresql.db_name
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.rds.name
}

output "db_instance_resource_id" {
  description = "RDS instance resource ID"
  value       = aws_db_instance.postgresql.resource_id
}

output "db_instance_engine" {
  description = "Database engine"
  value       = aws_db_instance.postgresql.engine
}

output "db_instance_engine_version" {
  description = "Database engine version"
  value       = aws_db_instance.postgresql.engine_version
}

output "db_instance_class" {
  description = "RDS instance class"
  value       = aws_db_instance.postgresql.instance_class
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = var.create_kms_key ? aws_kms_key.rds[0].id : null
}

output "kms_key_arn" {
  description = "KMS key ARN for encryption"
  value       = var.create_kms_key ? aws_kms_key.rds[0].arn : null
}