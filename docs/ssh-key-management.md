# SSH Key Management Guide

**Project:** NT114 DevSecOps Infrastructure
**Last Updated:** November 14, 2025
**Purpose:** Secure SSH key management for bastion host access

## Overview

This document outlines the procedures for managing SSH keys used to access the bastion host in the NT114 DevSecOps infrastructure. SSH keys are critical for secure access to jump hosts and must be managed according to DevSecOps best practices.

## Key Types and Usage

### Bastion Host Access Keys
- **Purpose**: SSH access to EC2 bastion host instances
- **Algorithm**: ED25519 (recommended for security and performance)
- **Storage**: Private keys stored locally, public keys in GitHub secrets
- **Rotation**: Quarterly or immediately upon compromise

### Current Active Keys
- **Key Name**: `nt114-bastion-devsecops-251114`
- **Algorithm**: ED25519 with 100 KDF rounds
- **Created**: November 14, 2025
- **Fingerprint**: `SHA256:edYlordmWrJ5GmginvuV/VDKrxX+lxNWPGokC1vTxjM`
- **Status**: Active (current)

## Key Generation Procedures

### Standard Bastion Host Key Generation

```bash
# Generate ED25519 key pair with enhanced security
ssh-keygen -t ed25519 -a 100 -f nt114-bastion-devsecops-YYYYMMDD -C "nt114-bastion-devsecops@YYYYMMDD" -N ""

# Example (current key):
ssh-keygen -t ed25519 -a 100 -f nt114-bastion-devsecops-251114 -C "nt114-bastion-devsecops@251114" -N ""

# Verify key generation
ls -la nt114-bastion-devsecops-*
ssh-keygen -lf nt114-bastion-devsecops-*.pub
```

### Key Specifications

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Algorithm | ED25519 | Modern, secure, efficient |
| KDF Rounds | 100 | Enhanced security for passphrase |
| Format | OpenSSH | Standard format compatibility |
| Comment | nt114-bastion-devsecops@YYMMDD | Standardized naming |
| Passphrase | None | Required for automation |

## GitHub Secret Management

### Required Secrets

| Secret Name | Purpose | Content |
|-------------|---------|---------|
| `BASTION_PUBLIC_KEY` | Terraform bastion host module | Public key content |

### Secret Creation Process

#### Method 1: GitHub Web Interface
1. Navigate to: Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Set name: `BASTION_PUBLIC_KEY`
4. Paste public key content
5. Click "Add secret"

#### Method 2: GitHub CLI
```bash
# Set repository secret
gh secret set BASTION_PUBLIC_KEY \
  --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
  --body "$(cat nt114-bastion-devsecops-YYYYMMDD.pub)"

# Verify secret creation
gh secret list --repo NT114DevSecOpsProject/NT114_DevSecOps_Project
```

### Secret Validation

```bash
# Test Terraform with new key
export TF_VAR_bastion_public_key="$(cat nt114-bastion-devsecops-YYYYMMDD.pub)"
cd terraform/environments/dev
terraform plan -var="bastion_public_key=$TF_VAR_bastion_public_key"

# Test GitHub Actions workflow
# Trigger EKS Terraform Deployment workflow with action: plan
```

## Key Rotation Procedures

### Quarterly Rotation Schedule

1. **Preparation** (1 week before rotation):
   ```bash
   # Generate new key
   DATE=$(date +%y%m%d)
   ssh-keygen -t ed25519 -a 100 -f nt114-bastion-devsecops-$DATE -C "nt114-bastion-devsecops@$DATE" -N ""
   ```

2. **Testing** (3 days before rotation):
   ```bash
   # Test new key with Terraform
   export TF_VAR_bastion_public_key="$(cat nt114-bastion-devsecops-$DATE.pub)"
   terraform plan -var="bastion_public_key=$TF_VAR_bastion_public_key"
   ```

3. **Deployment** (Rotation day):
   ```bash
   # Update GitHub secret
   gh secret set BASTION_PUBLIC_KEY \
     --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
     --body "$(cat nt114-bastion-devsecops-$DATE.pub)"

   # Trigger infrastructure update
   # Run Terraform apply with new key
   ```

4. **Cleanup** (After successful deployment):
   ```bash
   # Remove old AWS key pair
   aws ec2 delete-key-pair --key-name old-key-name

   # Archive old private key securely
   # Document rotation in change log
   ```

### Emergency Rotation (Compromise Response)

If a key is compromised or access needs immediate revocation:

1. **Immediate Actions**:
   ```bash
   # Delete compromised AWS key pair
   aws ec2 delete-key-pair --key-name compromised-key-name

   # Remove from GitHub secrets immediately
   gh secret delete BASTION_PUBLIC_KEY --repo NT114DevSecOpsProject/NT114_DevSecOps_Project
   ```

2. **Generate New Key**:
   ```bash
   # Create emergency replacement key
   DATE=$(date +%y%m%d)
   ssh-keygen -t ed25519 -a 100 -f nt114-bastion-devsecops-$DATE-emergency -C "nt114-bastion-devsecops@$DATE-emergency" -N ""
   ```

3. **Deploy Emergency Key**:
   ```bash
   # Update GitHub secret with emergency key
   gh secret set BASTION_PUBLIC_KEY \
     --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
     --body "$(cat nt114-bastion-devsecops-$DATE-emergency.pub)"

   # Re-deploy infrastructure immediately
   ```

4. **Incident Reporting**:
   - Document the compromise incident
   - Review access logs for unauthorized usage
   - Implement additional security measures if needed

## Access Control

### Private Key Storage

- **Location**: Store in secure password manager (1Password, LastPass, etc.)
- **Encryption**: Use encrypted storage if password manager unavailable
- **Backup**: Create encrypted backup with separate storage
- **Access**: Limit to infrastructure team members only

### Team Access Management

1. **Authorization Matrix**:
   | Role | Key Access | GitHub Secret Access |
   |------|------------|---------------------|
   | Infrastructure Lead | Full | Full |
   | DevOps Engineer | Read | Read |
   | Security Engineer | Audit | Audit |
   | Developer | None | None |

2. **Access Requests**:
   - Submit access request via project management tool
   - Include justification and duration
   - Manager approval required
   - Access revoked when no longer needed

### Audit and Monitoring

1. **Key Usage Logs**:
   ```bash
   # Monitor AWS key pair usage
   aws ec2 describe-instances --filters "Name=key-name,Values=nt114-bastion-*" \
     --query "Reservations[*].Instances[*].[InstanceId,LaunchTime,KeyName]"

   # Monitor SSH access attempts (via CloudTrail)
   aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue=nt114-bastion-*
   ```

2. **Quarterly Audits**:
   - Review key inventory and usage
   - Verify team access permissions
   - Check for unused or expired keys
   - Update documentation

## Security Best Practices

### Key Security

1. **Algorithm Selection**:
   - Use ED25519 for new keys (recommended)
   - RSA 4096 acceptable if compatibility required
   - Avoid DSA and ECDSA keys

2. **Key Protection**:
   ```bash
   # Set proper file permissions
   chmod 600 private-key-file
   chmod 644 public-key-file.pub

   # Use SSH agent for temporary access
   ssh-add private-key-file
   ```

3. **Passphrase Policy**:
   - No passphrase for automation keys
   - Strong passphrase for personal access keys
   - Store passphrases securely

### Infrastructure Security

1. **Bastion Host Configuration**:
   - Disable password authentication
   - Use key-based authentication only
   - Implement fail2ban for brute force protection
   - Regular security updates

2. **Network Security**:
   - Limit SSH access to specific IP ranges
   - Use security groups for access control
   - Monitor access logs for unusual activity
   - Implement VPN access for additional security

## Troubleshooting

### Common Issues

1. **"Missing required argument" Error**:
   ```bash
   # Check GitHub secret exists
   gh secret list --repo NT114DevSecOpsProject/NT114_DevSecOps_Project

   # Verify secret content
   gh secret view BASTION_PUBLIC_KEY --repo NT114DevSecOpsProject/NT114_DevSecOps_Project

   # Test local environment variable
   export TF_VAR_bastion_public_key="your-public-key"
   terraform plan -var="bastion_public_key=$TF_VAR_bastion_public_key"
   ```

2. **SSH Connection Failed**:
   ```bash
   # Verify key format
   ssh-keygen -l -f private-key-file

   # Check key permissions
   ls -la private-key-file

   # Test SSH connection
   ssh -v -i private-key-file user@hostname
   ```

3. **Key Pair Not Found in AWS**:
   ```bash
   # List existing key pairs
   aws ec2 describe-key-pairs

   # Delete orphaned key references
   terraform state rm 'module.bastion_host.aws_key_pair.bastion'
   ```

### Recovery Procedures

1. **Lost Private Key**:
   - Generate new key pair immediately
   - Update GitHub secret
   - Re-deploy infrastructure
   - Document incident

2. **Corrupted Key Files**:
   - Restore from encrypted backup
   - Generate new keys if backup unavailable
   - Update all references

3. **Access Lockout**:
   - Use AWS Systems Manager Session Manager for emergency access
   - Generate new access keys
   - Update infrastructure configuration

## Documentation Requirements

### Key Inventory

Maintain current inventory of all SSH keys:
```markdown
## Key Inventory - Last Updated: YYYY-MM-DD

| Key Name | Algorithm | Created | Expires | Purpose | Status |
|----------|-----------|---------|---------|---------|---------|
| nt114-bastion-devsecops-251114 | ED25519 | 2025-11-14 | 2026-02-14 | Bastion Host | Active |
```

### Change Log

Document all key-related changes:
```markdown
## SSH Key Change Log

### 2025-11-14 - Initial Key Setup
- Generated ED25519 key pair for bastion host access
- Created GitHub secret BASTION_PUBLIC_KEY
- CI/CD pipeline unblocked
```

### Runbook Entries

Create quick reference guides:
```markdown
## Emergency Key Rotation

1. Delete compromised key from AWS
2. Remove from GitHub secrets
3. Generate new emergency key
4. Update infrastructure
5. Test access
6. Document incident
```

## Compliance and Standards

### Industry Standards
- **NIST SP 800-57**: Key management guidelines
- **ISO 27001**: Information security management
- **SOC 2**: Security operations and controls

### Internal Policies
- Quarterly key rotation
- Access reviews every 6 months
- Annual security audits
- Immediate revocation on compromise

## Training and Awareness

### Team Training Topics
1. SSH key generation and management
2. Secure storage practices
3. Access control procedures
4. Emergency response protocols

### Security Awareness
- Phishing prevention for credential protection
- Social engineering awareness
- Physical security for key storage devices
- Incident reporting procedures

---

## Contact Information

**Infrastructure Team**: [contact@nt114devsecops.com]
**Security Team**: [security@nt114devsecops.com]
**Emergency Contact**: [emergency@nt114devsecops.com]

---

**Document Version**: 1.0
**Next Review**: February 14, 2026
**Classification**: Internal - Confidential