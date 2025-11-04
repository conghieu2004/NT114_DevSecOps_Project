# VPC Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "The CIDR block of the VPC"
  value       = module.vpc.vpc_cidr
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

# EKS Cluster Outputs
output "cluster_id" {
  description = "The ID of the EKS cluster"
  value       = module.eks_cluster.cluster_id
}

output "cluster_name" {
  description = "The name of the EKS cluster"
  value       = module.eks_cluster.cluster_name
}

output "cluster_arn" {
  description = "The ARN of the EKS cluster"
  value       = module.eks_cluster.cluster_arn
}

output "cluster_endpoint" {
  description = "Endpoint for the EKS cluster API server"
  value       = module.eks_cluster.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks_cluster.cluster_security_group_id
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = module.eks_cluster.cluster_oidc_issuer_url
}

output "oidc_provider" {
  description = "The OpenID Connect identity provider (without https://)"
  value       = module.eks_cluster.oidc_provider
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for EKS"
  value       = module.eks_cluster.oidc_provider_arn
}

output "cluster_status" {
  description = "The status of the EKS cluster"
  value       = module.eks_cluster.cluster_status
}

# Node Group Outputs
output "node_group_id" {
  description = "EKS managed node group ID"
  value       = module.eks_nodegroup.node_group_id
}

output "node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Node Group"
  value       = module.eks_nodegroup.node_group_arn
}

output "node_group_status" {
  description = "Status of the EKS Node Group"
  value       = module.eks_nodegroup.node_group_status
}

# ALB Controller Outputs
output "alb_controller_helm_release_name" {
  description = "Name of the ALB controller Helm release"
  value       = module.alb_controller.helm_release_name
}

output "alb_controller_helm_release_status" {
  description = "Status of the ALB controller Helm release"
  value       = module.alb_controller.helm_release_status
}

# IAM Access Outputs
output "admin_group_name" {
  description = "Name of the admin IAM group"
  value       = module.iam_access.admin_group_name
}

output "admin_role_name" {
  description = "Name of the admin IAM role"
  value       = module.iam_access.admin_role_name
}

output "admin_role_arn" {
  description = "ARN of the admin IAM role"
  value       = module.iam_access.admin_role_arn
}

# kubectl Configuration
output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks_cluster.cluster_name}"
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "Map of ECR repository URLs"
  value       = module.ecr.repository_urls
}

output "ecr_repository_arns" {
  description = "Map of ECR repository ARNs"
  value       = module.ecr.repository_arns
}

output "ecr_registry_id" {
  description = "ECR Registry ID"
  value       = module.ecr.registry_id
}

output "ecr_login_command" {
  description = "Command to login to ECR"
  value       = module.ecr.ecr_login_command
}

output "github_actions_user_name" {
  description = "IAM user name for GitHub Actions"
  value       = module.ecr.github_actions_user_name
}

output "github_actions_access_key_id" {
  description = "Access key ID for GitHub Actions (sensitive)"
  value       = module.ecr.github_actions_access_key_id
  sensitive   = true
}

output "github_actions_secret_access_key" {
  description = "Secret access key for GitHub Actions (sensitive)"
  value       = module.ecr.github_actions_secret_access_key
  sensitive   = true
}
