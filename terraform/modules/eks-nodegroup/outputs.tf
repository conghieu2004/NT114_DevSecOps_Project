output "node_group_id" {
  description = "EKS managed node group ID"
  value       = module.eks_managed_node_group.node_group_id
}

output "node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Node Group"
  value       = module.eks_managed_node_group.node_group_arn
}

output "node_group_status" {
  description = "Status of the EKS Node Group"
  value       = module.eks_managed_node_group.node_group_status
}

output "node_group_resources" {
  description = "Resources associated with the node group"
  value       = module.eks_managed_node_group.node_group_resources
}

output "iam_role_arn" {
  description = "ARN of the IAM role used by the node group"
  value       = module.eks_managed_node_group.iam_role_arn
}

output "iam_role_name" {
  description = "Name of the IAM role used by the node group"
  value       = module.eks_managed_node_group.iam_role_name
}

output "coredns_addon_arn" {
  description = "ARN of the CoreDNS addon"
  value       = var.enable_coredns_addon ? aws_eks_addon.coredns[0].arn : null
}

output "coredns_addon_version" {
  description = "Version of the CoreDNS addon"
  value       = var.enable_coredns_addon ? aws_eks_addon.coredns[0].addon_version : null
}
