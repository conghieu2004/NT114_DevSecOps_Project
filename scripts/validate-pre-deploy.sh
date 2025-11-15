#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
echo "🔍 Pre-Deployment Validation for Environment: $ENVIRONMENT"
echo "========================================================="

# Check if required files exist
required_files=(
  "terraform/environments/$ENVIRONMENT/main.tf"
  "terraform/environments/$ENVIRONMENT/variables.tf"
  "nt114-bastion-devsecops-251114"
  "nt114-bastion-devsecops-251114.pub"
)

for file in "${required_files[@]}"; do
  if [[ -f "$file" ]]; then
    echo "✅ $file exists"
  else
    echo "❌ $file missing"
    exit 1
  fi
done

# Validate SSH key format
echo ""
echo "🔑 Validating SSH key format..."

public_key_content=$(cat nt114-bastion-devsecops-251114.pub)
if [[ $public_key_content =~ ^ssh-(ed25519|rsa|ecdsa) ]]; then
  echo "✅ Public key format valid"
else
  echo "❌ Invalid public key format"
  exit 1
fi

# Check if private key format is valid
if ssh-keygen -l -f nt114-bastion-devsecops-251114 > /dev/null 2>&1; then
  echo "✅ Private key format valid"
else
  echo "❌ Invalid private key format"
  exit 1
fi

# Check if Terraform configuration references bastion_public_key
if grep -q "bastion_public_key" terraform/environments/$ENVIRONMENT/main.tf; then
  echo "✅ Terraform configuration uses bastion_public_key"
else
  echo "⚠️  Terraform configuration may not reference bastion_public_key"
fi

# Check if workflows reference the secrets correctly
echo ""
echo "🔧 Validating GitHub workflow configurations..."

if grep -q "BASTION_PUBLIC_KEY" .github/workflows/eks-terraform.yml; then
  echo "✅ eks-terraform.yml references BASTION_PUBLIC_KEY"
else
  echo "❌ eks-terraform.yml missing BASTION_PUBLIC_KEY reference"
  exit 1
fi

if grep -q "BASTION_SSH_PRIVATE_KEY" .github/workflows/database-migration.yml; then
  echo "✅ database-migration.yml references BASTION_SSH_PRIVATE_KEY"
else
  echo "❌ database-migration.yml missing BASTION_SSH_PRIVATE_KEY reference"
  exit 1
fi

echo ""
echo "✅ Pre-deployment validation complete"
echo ""
echo "📋 Next Steps:"
echo "=============="
echo "1. Ensure GitHub secrets are configured:"
echo "   - BASTION_PUBLIC_KEY"
echo "   - BASTION_SSH_PRIVATE_KEY"
echo "2. Run: gh workflow run validate-secrets"
echo "3. Run: gh workflow run test-secrets"
echo "4. Trigger deployment workflow"