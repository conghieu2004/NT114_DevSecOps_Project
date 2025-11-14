#!/bin/bash

# Script to import existing AWS resources into Terraform state
# This prevents "already exists" errors

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Detect if we're already in the terraform directory
if [[ $(pwd) == */terraform/environments/dev ]]; then
  TERRAFORM_DIR="."
else
  TERRAFORM_DIR="terraform/environments/dev"
fi

echo "====================================="
echo "Importing Existing AWS Resources"
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Working Directory: $TERRAFORM_DIR"
echo "====================================="

if [ "$TERRAFORM_DIR" != "." ]; then
  cd "$TERRAFORM_DIR"
fi

# Import ECR Repositories
echo ""
echo "Importing ECR Repositories..."
ECR_REPOS=("api-gateway" "auth-service" "exercises-service" "scores-service" "user-management-service" "frontend")

for repo in "${ECR_REPOS[@]}"; do
  REPO_NAME="nt114-devsecops/$repo"
  echo "  - Checking $REPO_NAME..."

  # Check if repository exists
  if aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo "    Repository exists, importing..."
    terraform import "module.ecr.aws_ecr_repository.repositories[\"$repo\"]" "$REPO_NAME" 2>/dev/null || echo "    Already in state or import failed"
  else
    echo "    Repository does not exist, skipping"
  fi
done

# Import IAM User for GitHub Actions
echo ""
echo "Importing IAM User..."
IAM_USER="nt114-devsecops-github-actions-user"
if aws iam get-user --user-name "$IAM_USER" &> /dev/null; then
  echo "  - User $IAM_USER exists, importing..."
  terraform import "module.ecr.aws_iam_user.github_actions_user[0]" "$IAM_USER" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - User $IAM_USER does not exist, skipping"
fi

# Import IAM Policy for GitHub Actions
echo ""
echo "Importing IAM Policy..."
POLICY_NAME="nt114-devsecops-github-actions-ecr-policy"
POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
  echo "  - Policy $POLICY_NAME exists, importing..."
  terraform import "module.ecr.aws_iam_policy.github_actions_ecr_policy[0]" "$POLICY_ARN" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - Policy $POLICY_NAME does not exist, skipping"
fi

# Import CloudWatch Log Group
echo ""
echo "Importing CloudWatch Log Group..."
LOG_GROUP="/aws/eks/eks-1/cluster"
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" | grep -q "$LOG_GROUP"; then
  echo "  - Log group $LOG_GROUP exists, importing..."
  terraform import "module.eks_cluster.module.eks.aws_cloudwatch_log_group.this[0]" "$LOG_GROUP" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - Log group $LOG_GROUP does not exist, skipping"
fi

# Import IAM Role for EKS Admin
echo ""
echo "Importing IAM Role..."
IAM_ROLE="eks-admin-role"
if aws iam get-role --role-name "$IAM_ROLE" &> /dev/null; then
  echo "  - Role $IAM_ROLE exists, importing..."
  terraform import "module.iam_access.aws_iam_role.admin_role[0]" "$IAM_ROLE" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - Role $IAM_ROLE does not exist, skipping"
fi

# Import IAM Policy for AssumeRole
echo ""
echo "Importing IAM AssumeRole Policy..."
ASSUME_POLICY_NAME="eks-assume-role-policy"
ASSUME_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${ASSUME_POLICY_NAME}"

if aws iam get-policy --policy-arn "$ASSUME_POLICY_ARN" &> /dev/null; then
  echo "  - Policy $ASSUME_POLICY_NAME exists, importing..."
  terraform import "module.iam_access.aws_iam_policy.eks_assume_role_policy[0]" "$ASSUME_POLICY_ARN" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - Policy $ASSUME_POLICY_NAME does not exist, skipping"
fi

# Import IAM Group
echo ""
echo "Importing IAM Group..."
IAM_GROUP="eks-admin-group"
if aws iam get-group --group-name "$IAM_GROUP" &> /dev/null; then
  echo "  - Group $IAM_GROUP exists, importing..."
  terraform import "module.iam_access.aws_iam_group.admin_group[0]" "$IAM_GROUP" 2>/dev/null || echo "  Already in state or import failed"
else
  echo "  - Group $IAM_GROUP does not exist, skipping"
fi

echo ""
echo "====================================="
echo "Import Complete!"
echo "====================================="
echo ""
echo "Now run: terraform plan"
