# ECR Repositories for microservices
resource "aws_ecr_repository" "repositories" {
  for_each = toset(var.repository_names)

  name                 = "${var.project_name}/${each.value}"
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = var.encryption_type
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}/${each.value}"
      Service     = each.value
      Environment = var.environment
    }
  )
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "lifecycle_policy" {
  for_each = aws_ecr_repository.repositories

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.image_count_to_keep} images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = var.image_count_to_keep
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than ${var.untagged_image_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.untagged_image_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# IAM Policy for GitHub Actions to push to ECR
resource "aws_iam_policy" "github_actions_ecr_policy" {
  count = var.create_github_actions_policy ? 1 : 0

  name        = "${var.project_name}-github-actions-ecr-policy"
  description = "Policy for GitHub Actions to push images to ECR"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GetAuthorizationToken"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetRepositoryPolicy",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:DescribeImages",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = [
          for repo in aws_ecr_repository.repositories : repo.arn
        ]
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-github-actions-ecr-policy"
    }
  )
}

# IAM User for GitHub Actions (optional)
resource "aws_iam_user" "github_actions_user" {
  count = var.create_github_actions_user ? 1 : 0

  name = "${var.project_name}-github-actions-user"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-github-actions-user"
    }
  )
}

# Attach ECR policy to GitHub Actions user
resource "aws_iam_user_policy_attachment" "github_actions_user_policy" {
  count = var.create_github_actions_user ? 1 : 0

  user       = aws_iam_user.github_actions_user[0].name
  policy_arn = aws_iam_policy.github_actions_ecr_policy[0].arn
}

# Access keys for GitHub Actions user (will be output securely)
resource "aws_iam_access_key" "github_actions_key" {
  count = var.create_github_actions_user ? 1 : 0

  user = aws_iam_user.github_actions_user[0].name
}
