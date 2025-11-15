#!/bin/bash
set -e

echo "🔧 GitHub Secret Management Setup Script"
echo "========================================"

# Check if we're on GitHub Actions or local
if [[ -n "$GITHUB_ACTIONS" ]]; then
  echo "❌ This script should be run locally, not in GitHub Actions"
  exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
  echo "❌ GitHub CLI (gh) is not installed"
  echo "Please install it from: https://cli.github.com/"
  exit 1
fi

# Check if we're authenticated with gh
if ! gh auth status &> /dev/null; then
  echo "❌ Not authenticated with GitHub CLI"
  echo "Please run: gh auth login"
  exit 1
fi

# Generate new SSH key pair if needed
if [[ ! -f "nt114-bastion-devsecops-251114" ]]; then
  echo "Generating new SSH key pair for Bastion host..."
  ssh-keygen -t ed25519 -a 100 -f nt114-bastion-devsecops-251114 -N "" -C "nt114-bastion-devsecops@$(date +%y%m%d)"
  chmod 400 nt114-bastion-devsecops-251114
  chmod 644 nt114-bastion-devsecops-251114.pub
  echo "✅ SSH key pair generated"
else
  echo "ℹ️  SSH key pair already exists"
fi

# Display public key for GitHub configuration
echo ""
echo "📋 Public Key for BASTION_PUBLIC_KEY secret:"
echo "============================================"
cat nt114-bastion-devsecops-251114.pub
echo ""

# Instructions for private key
echo "📋 Private Key Instructions:"
echo "============================"
echo "Copy the following content for BASTION_SSH_PRIVATE_KEY secret:"
echo "(Including '-----BEGIN OPENSSH PRIVATE KEY-----' and '-----END OPENSSH PRIVATE KEY-----')"
echo ""
cat nt114-bastion-devsecops-251114
echo ""

echo "🚀 Setup Instructions:"
echo "======================"
echo "1. Go to: https://github.com/$(gh repo view --json owner,name | jq -r '.owner.login + "/" + .name')/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Add BASTION_PUBLIC_KEY with the public key above"
echo "4. Add BASTION_SSH_PRIVATE_KEY with the private key content"
echo "5. Run: gh workflow run validate-secrets"

# Ask user if they want to set secrets automatically
read -p "Do you want to set the secrets automatically? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Setting BASTION_PUBLIC_KEY secret..."
  gh secret set BASTION_PUBLIC_KEY --body "$(cat nt114-bastion-devsecops-251114.pub)"

  echo "🔄 Setting BASTION_SSH_PRIVATE_KEY secret..."
  gh secret set BASTION_SSH_PRIVATE_KEY < nt114-bastion-devsecops-251114

  echo "✅ Secrets configured successfully!"
  echo ""
  echo "🧪 Running validation workflow..."
  gh workflow run validate-secrets
  echo "✅ Validation workflow triggered. Check: https://github.com/$(gh repo view --json owner,name | jq -r '.owner.login + "/" + .name')/actions"
else
  echo "⚠️  Please configure secrets manually using the instructions above"
fi

echo ""
echo "🎉 Setup complete! Your GitHub Actions workflows should now work properly."