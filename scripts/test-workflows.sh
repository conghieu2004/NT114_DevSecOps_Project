#!/bin/bash

set -e

echo "🚀 Testing GitHub Actions Workflows Locally"
echo "=========================================="

# Check if act is installed (for local GitHub Actions testing)
if ! command -v act &> /dev/null; then
    echo "❌ 'act' is not installed for local GitHub Actions testing"
    echo "Install it with: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    echo ""
    echo "Alternatively, run workflows directly in GitHub:"
    echo "1. Push changes to GitHub"
    echo "2. Run workflows from Actions tab"
    exit 1
fi

echo "✅ Found act installation"

# Check if we have the required secrets file
if [[ ! -f ".secrets" ]]; then
    echo "⚠️  Creating .secrets file for local testing"
    cat > .secrets << EOF
# GitHub Actions Secrets for Local Testing
# Copy your actual values here

AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
BASTION_PUBLIC_KEY=your_public_key_here
BASTION_SSH_PRIVATE_KEY=your_private_key_here
GITHUB_TOKEN=your_github_token_here
SONAR_HOST_URL=your_sonar_url_here
SONAR_TOKEN=your_sonar_token_here
EOF
    echo "📝 Please edit .secrets file with your actual values"
    echo "Then run this script again"
    exit 1
fi

# Load secrets
source .secrets

echo ""
echo "🧪 Testing workflows..."

# Test eks-terraform workflow (plan only)
echo ""
echo "Testing eks-terraform workflow (plan)..."
act -j terraform-plan -s AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -s AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -s BASTION_PUBLIC_KEY="$BASTION_PUBLIC_KEY" -W .github/workflows/eks-terraform.yml

echo ""
echo "✅ Workflow tests completed successfully!"
echo ""
echo "If tests pass, commit and push changes to trigger workflows in GitHub"
echo "Run: git add . && git commit -m 'fix: resolve GitHub Actions workflow issues' && git push"