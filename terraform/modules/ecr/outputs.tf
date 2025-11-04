# ECR Repository URLs
output "repository_urls" {
  description = "Map of repository names to their URLs"
  value = {
    for name, repo in aws_ecr_repository.repositories :
    name => repo.repository_url
  }
}

# ECR Repository ARNs
output "repository_arns" {
  description = "Map of repository names to their ARNs"
  value = {
    for name, repo in aws_ecr_repository.repositories :
    name => repo.arn
  }
}

# ECR Repository names
output "repository_names" {
  description = "Map of repository names"
  value = {
    for name, repo in aws_ecr_repository.repositories :
    name => repo.name
  }
}

# Registry ID
output "registry_id" {
  description = "The registry ID where the repositories were created"
  value       = [for repo in aws_ecr_repository.repositories : repo.registry_id][0]
}

# GitHub Actions IAM Policy ARN
output "github_actions_policy_arn" {
  description = "ARN of the IAM policy for GitHub Actions"
  value       = var.create_github_actions_policy ? aws_iam_policy.github_actions_ecr_policy[0].arn : null
}

# GitHub Actions IAM User
output "github_actions_user_name" {
  description = "Name of the IAM user for GitHub Actions"
  value       = var.create_github_actions_user ? aws_iam_user.github_actions_user[0].name : null
}

output "github_actions_user_arn" {
  description = "ARN of the IAM user for GitHub Actions"
  value       = var.create_github_actions_user ? aws_iam_user.github_actions_user[0].arn : null
}

# GitHub Actions Access Keys (sensitive)
output "github_actions_access_key_id" {
  description = "Access key ID for GitHub Actions user"
  value       = var.create_github_actions_user ? aws_iam_access_key.github_actions_key[0].id : null
  sensitive   = true
}

output "github_actions_secret_access_key" {
  description = "Secret access key for GitHub Actions user"
  value       = var.create_github_actions_user ? aws_iam_access_key.github_actions_key[0].secret : null
  sensitive   = true
}

# ECR Login command
output "ecr_login_command" {
  description = "Command to login to ECR"
  value       = "aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${[for repo in aws_ecr_repository.repositories : repo.registry_id][0]}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

data "aws_region" "current" {}
