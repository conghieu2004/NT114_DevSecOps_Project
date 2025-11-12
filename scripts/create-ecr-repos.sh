#!/bin/bash

set -e

echo "====================================="
echo "Creating ECR Repositories"
echo "====================================="

AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME=${PROJECT_NAME:-nt114-devsecops}

REPOSITORIES=(
  "api-gateway"
  "exercises-service"
  "scores-service"
  "user-management-service"
  "frontend"
)

for repo in "${REPOSITORIES[@]}"; do
  REPO_NAME="${PROJECT_NAME}/${repo}"

  echo ""
  echo "Checking repository: $REPO_NAME"

  if aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "✅ Repository already exists: $REPO_NAME"
  else
    echo "📦 Creating repository: $REPO_NAME"
    aws ecr create-repository \
      --repository-name "$REPO_NAME" \
      --region "$AWS_REGION" \
      --image-scanning-configuration scanOnPush=true \
      --encryption-configuration encryptionType=AES256 \
      --tags "Key=Project,Value=NT114_DevSecOps" "Key=ManagedBy,Value=Script"

    echo "✅ Repository created: $REPO_NAME"
  fi
done

echo ""
echo "====================================="
echo "All ECR Repositories Ready!"
echo "====================================="
echo ""
echo "List of repositories:"
aws ecr describe-repositories --region "$AWS_REGION" --query 'repositories[].repositoryName' --output table
