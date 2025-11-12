output "helm_release_name" {
  description = "Name of the Helm release"
  value       = var.enable_alb_controller ? helm_release.aws_load_balancer_controller[0].name : null
}

output "helm_release_namespace" {
  description = "Namespace of the Helm release"
  value       = var.enable_alb_controller ? helm_release.aws_load_balancer_controller[0].namespace : null
}

output "helm_release_version" {
  description = "Version of the Helm release"
  value       = var.enable_alb_controller ? helm_release.aws_load_balancer_controller[0].version : null
}

output "helm_release_status" {
  description = "Status of the Helm release"
  value       = var.enable_alb_controller ? helm_release.aws_load_balancer_controller[0].status : null
}

output "ebs_csi_controller_role_arn" {
  description = "ARN of the EBS CSI controller IAM role"
  value       = var.enable_ebs_csi_controller ? aws_iam_role.ebs_csi_controller[0].arn : null
}
