data "aws_caller_identity" "current" {}

# IAM Group for EKS Admins
resource "aws_iam_group" "admin_group" {
  count = var.create_admin_group ? 1 : 0
  name  = var.admin_group_name
}

# IAM Role for EKS Admins
resource "aws_iam_role" "admin_role" {
  count = var.create_admin_role ? 1 : 0
  name  = var.admin_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

# Attach Admin Policy to Role
resource "aws_iam_role_policy_attachment" "admin_permissions" {
  count      = var.create_admin_role && var.attach_admin_policy ? 1 : 0
  role       = aws_iam_role.admin_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# Try to fetch existing IAM Policy for AssumeRole
data "aws_iam_policy" "eks_assume_role_policy_existing" {
  count = var.create_assume_role_policy ? 1 : 0
  arn   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.assume_role_policy_name}"
}

# IAM Policy for AssumeRole (only create if not using existing)
resource "aws_iam_policy" "eks_assume_role_policy" {
  count       = 0 # Disabled - using existing policy
  name        = var.assume_role_policy_name
  description = "Allows users in the group to assume the EKS admin role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.admin_role[0].arn
      }
    ]
  })

  tags = var.tags
}

# Attach Policy to IAM Group (use existing policy)
resource "aws_iam_group_policy_attachment" "attach_assume_role_policy" {
  count      = var.create_admin_group && var.create_assume_role_policy ? 1 : 0
  group      = aws_iam_group.admin_group[0].name
  policy_arn = data.aws_iam_policy.eks_assume_role_policy_existing[0].arn
}

# EKS Access Entry
resource "aws_eks_access_entry" "admin_access" {
  count         = var.create_eks_access_entry ? 1 : 0
  cluster_name  = var.cluster_name
  principal_arn = aws_iam_role.admin_role[0].arn
  type          = var.access_entry_type

  tags = var.tags
}

# EKS Access Policy Association
resource "aws_eks_access_policy_association" "admin_policy" {
  count         = var.create_eks_access_policy ? 1 : 0
  cluster_name  = var.cluster_name
  policy_arn    = var.eks_access_policy_arn
  principal_arn = aws_iam_role.admin_role[0].arn

  access_scope {
    type       = var.access_scope_type
    namespaces = var.access_scope_namespaces
  }
}
