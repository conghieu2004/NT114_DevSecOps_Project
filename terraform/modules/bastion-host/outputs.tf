output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.bastion.id
}

output "instance_arn" {
  description = "EC2 instance ARN"
  value       = aws_instance.bastion.arn
}

output "instance_public_ip" {
  description = "Public IP address of the bastion host"
  value       = var.allocate_eip ? aws_eip.bastion[0].public_ip : aws_instance.bastion.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the bastion host"
  value       = var.allocate_eip ? aws_eip.bastion[0].public_dns : aws_instance.bastion.public_dns
}

output "instance_private_ip" {
  description = "Private IP address of the bastion host"
  value       = aws_instance.bastion.private_ip
}

output "security_group_id" {
  description = "Security group ID of the bastion host"
  value       = aws_security_group.bastion.id
}

output "iam_role_arn" {
  description = "IAM role ARN of the bastion host"
  value       = aws_iam_role.bastion.arn
}

output "key_name" {
  description = "SSH key pair name"
  value       = aws_key_pair.bastion.key_name
}

output "instance_state" {
  description = "Current state of the bastion host"
  value       = aws_instance.bastion.instance_state
}

output "instance_type" {
  description = "Instance type of the bastion host"
  value       = aws_instance.bastion.instance_type
}