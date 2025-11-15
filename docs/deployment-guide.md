# NT114 DevSecOps Deployment Guide

**Version:** 2.0
**Last Updated:** November 14, 2025
**Deployment Status:** ✅ Production Ready

---

## Overview

This guide provides comprehensive instructions for deploying the NT114 DevSecOps infrastructure on AWS. The deployment uses Infrastructure as Code (IaC) with Terraform and automated CI/CD pipelines via GitHub Actions.

**Prerequisites:**
- AWS Account with appropriate permissions
- GitHub repository access
- Basic knowledge of AWS, Kubernetes, and Terraform
- Local development environment with required tools

---

## Table of Contents

1. [Prerequisites and Setup](#prerequisites-and-setup)
2. [SSH Key Management](#ssh-key-management)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Application Deployment](#application-deployment)
5. [Database Migration](#database-migration)
6. [Monitoring and Validation](#monitoring-and-validation)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance and Updates](#maintenance-and-updates)

---

## Prerequisites and Setup

### 1. Required Tools and Accounts

#### AWS Account Setup
```bash
# Verify AWS account
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDA...",
#     "Account": "039612870452",
#     "Arn": "arn:aws:iam::039612870452:user/your-username"
# }
```

#### Local Development Tools
```bash
# Install required tools
# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform
wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
unzip terraform_1.6.6_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# GitHub CLI
sudo apt update && sudo apt install gh -y
```

#### Verification
```bash
# Verify tool installations
aws --version
terraform --version
kubectl version --client
gh --version
```

### 2. AWS IAM Configuration

#### GitHub Actions IAM User
Create IAM user `nt114-devsecops-github-actions-user` with the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "eks:*",
                "ec2:*",
                "ecr:*",
                "iam:*",
                "elasticloadbalancing:*",
                "autoscaling:*",
                "cloudwatch:*",
                "logs:*",
                "ssm:*",
                "kms:*",
                "rds:*",
                "s3:*"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Generate Access Keys
```bash
# Using AWS CLI
aws iam create-access-key --user-name nt114-devsecops-github-actions-user
```

---

## SSH Key Management

### 1. Generate SSH Key Pair for Bastion Host

#### Create ED25519 SSH Key
```bash
# Generate new SSH key pair
DATE=$(date +%y%m%d)
KEY_NAME="nt114-bastion-devsecops-$DATE"

ssh-keygen -t ed25519 -a 100 -f $KEY_NAME -C "nt114-bastion-devsecops@$DATE" -N ""

# Verify key generation
ls -la $KEY_NAME*
ssh-keygen -lf $KEY_NAME.pub
```

#### Current Active Key
The current active SSH key (already implemented):
- **Key Name**: `nt114-bastion-devsecops-251114`
- **Fingerprint**: `SHA256:edYlordmWrJ5GmginvuV/VDKrxX+lxNWPGokC1vTxjM`
- **Public Key**: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGZqGfDpgsV81imXTwMHylKPckIQyoa1Acu4pQOJ/jzB nt114-bastion-devsecops@251114`

### 2. Configure GitHub Secrets

#### Method 1: GitHub CLI (Recommended)
```bash
# Authenticate with GitHub CLI
gh auth login

# Set repository secrets
gh secret set BASTION_PUBLIC_KEY \
  --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
  --body "$(cat nt114-bastion-devsecops-251114.pub)"

# Verify secret creation
gh secret list --repo NT114DevSecOpsProject/NT114_DevSecOps_Project
```

#### Method 2: GitHub Web UI
1. Navigate to repository settings
2. Go to "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Set name: `BASTION_PUBLIC_KEY`
5. Paste the public key content
6. Click "Add secret"

### 3. SSH Key Rotation Procedures

#### Quarterly Rotation Schedule
```bash
#!/bin/bash
# ssh-key-rotation.sh

# Generate new key
NEW_DATE=$(date +%y%m%d)
NEW_KEY_NAME="nt114-bastion-devsecops-$NEW_DATE"

ssh-keygen -t ed25519 -a 100 -f $NEW_KEY_NAME -C "nt114-bastion-devsecops@$NEW_DATE" -N ""

# Test new key locally
ssh-keygen -lf $NEW_KEY_NAME.pub

# Update GitHub secret
gh secret set BASTION_PUBLIC_KEY \
  --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
  --body "$(cat $NEW_KEY_NAME.pub)"

echo "SSH key rotation completed. New key: $NEW_KEY_NAME"
echo "Remember to update infrastructure deployment to use new key."
```

#### Emergency Rotation (Compromise Response)
```bash
#!/bin/bash
# emergency-key-rotation.sh

# Generate emergency key
EMERG_DATE=$(date +%y%m%d)
EMERG_KEY_NAME="nt114-bastion-devsecops-$EMERG_DATE-emergency"

ssh-keygen -t ed25519 -a 100 -f $EMERG_KEY_NAME -C "nt114-bastion-devsecops@$EMERG_DATE-emergency" -N ""

# Immediate GitHub secret update
gh secret set BASTION_PUBLIC_KEY \
  --repo NT114DevSecOpsProject/NT114_DevSecOps_Project \
  --body "$(cat $EMERG_KEY_NAME.pub)"

# Trigger infrastructure redeployment
gh workflow run eks-terraform.yml --field environment=dev --field action=apply

echo "Emergency key rotation completed. Infrastructure redeployment triggered."
```

---

## Infrastructure Deployment

### 1. Repository Setup

#### Clone and Configure Repository
```bash
# Clone repository
git clone https://github.com/NT114DevSecOpsProject/NT114_DevSecOps_Project.git
cd NT114_DevSecOps_Project

# Configure Git
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

#### Set Up GitHub Secrets
```bash
# AWS credentials for GitHub Actions
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_ACCESS_KEY_ID"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET_ACCESS_KEY"

# SSH key for bastion host (already configured)
gh secret set BASTION_PUBLIC_KEY --body "$(cat nt114-bastion-devsecops-251114.pub)"
```

### 2. Terraform Configuration

#### Environment Setup
```bash
cd terraform/environments/dev

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Review execution plan
terraform plan
```

#### Key Configuration Files

**variables.tf (Updated Values)**
```hcl
variable "enable_ebs_csi_controller" {
  description = "Enable EBS CSI Controller IAM role"
  type        = bool
  default     = true  # Updated for storage support
}

variable "enable_alb_controller" {
  description = "Enable ALB Controller IAM role"
  type        = bool
  default     = true  # Updated for load balancing
}
```

### 3. Deploy Infrastructure via GitHub Actions

#### Method 1: Automated Deployment (Recommended)
```bash
# Trigger infrastructure deployment
gh workflow run eks-terraform.yml \
  --field environment=dev \
  --field action=apply

# Monitor deployment
gh run watch --last
```

#### Method 2: Manual Local Deployment
```bash
cd terraform/environments/dev

# Apply infrastructure changes
terraform apply -auto-approve

# Get outputs for Kubernetes configuration
terraform output -json > ../outputs.json
```

### 4. Kubernetes Cluster Configuration

#### Configure kubectl
```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name $(terraform output -raw cluster_name)

# Verify cluster access
kubectl get nodes
kubectl get namespaces
```

#### Verify EBS CSI Driver
```bash
# Check EBS CSI driver status
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver

# Check storage class
kubectl get storageclass ebs-gp3-encrypted
```

---

## Application Deployment

### 1. GitHub Actions Application Deployment

#### Trigger Application Deployment
```bash
# Deploy applications to EKS
gh workflow run deploy-to-eks.yml \
  --field environment=dev

# Monitor deployment
gh run watch --last
```

#### Deployment Steps (Automated)
1. **Configure AWS Credentials**
2. **Install kubectl**
3. **Configure kubectl for EKS**
4. **Enable EBS CSI Driver Addon**
5. **Validate EBS CSI Driver**
6. **Create StorageClass**
7. **Deploy PostgreSQL**
8. **Deploy Application Services**
9. **Verify Deployment**

### 2. Manual Deployment (Optional)

#### Deploy PostgreSQL
```bash
# Apply PostgreSQL configuration
kubectl apply -f kubernetes/local/postgres-deployment.yaml -n dev

# Wait for StatefulSet to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n dev --timeout=600s

# Verify services
kubectl get services -n dev -l app=postgres
```

#### Deploy Application Services
```bash
# Deploy all services
kubectl apply -f kubernetes/services/ -n dev

# Wait for deployments
kubectl wait --for=condition=available deployment --all -n dev --timeout=600s

# Check pod status
kubectl get pods -n dev
```

### 3. Service Verification

#### Verify Service Connectivity
```bash
# Check service endpoints
kubectl get endpoints -n dev

# Test database connectivity
kubectl run postgres-test --image=postgres:15-alpine --rm -i --restart=Never -- \
  psql "postgresql://postgres:postgres@auth-db.dev.svc.cluster.local:5432/postgres" \
  -c "SELECT version();"

# Test API endpoints
kubectl port-forward service/api-gateway-service 8080:80 -n dev &
curl http://localhost:8080/health
```

---

## Database Migration

### 1. Preparation

#### Backup Current Data
```bash
#!/bin/bash
# backup-local-databases.sh

# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup each database
docker exec user_management_postgres_db pg_dump -U postgres user_management_db > backups/$(date +%Y%m%d)/auth_db_backup.sql
docker exec exercises_postgres pg_dump -U exercises_user exercises_db > backups/$(date +%Y%m%d)/exercises_db_backup.sql
docker exec scores_postgres pg_dump -U scores_user scores_db > backups/$(date +%Y%m%d)/scores_db_backup.sql

echo "Database backups completed in backups/$(date +%Y%m%d)/"
```

### 2. RDS Migration Execution

#### Deploy RDS Infrastructure
```bash
# Trigger RDS migration workflow
gh workflow run rds-migration.yml \
  --field environment=dev \
  --field action=migrate

# Monitor migration
gh run watch --last
```

#### Manual Migration (Optional)
```bash
# Deploy RDS via Terraform
cd terraform/environments/dev
terraform apply -target=module.rds_postgresql -auto-approve

# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
RDS_PASSWORD=$(aws secretsmanager get-secret-value --secret-id rds-password-dev --query SecretString --output text)

# Create SSH tunnel for migration
ssh -i nt114-bastion-devsecops-251114 \
  -f -N -L 5432:$RDS_ENDPOINT:5432 \
  ec2-user@$(terraform output -raw bastion_public_ip)

# Execute migration
./scripts/execute-migration.sh
```

### 3. Migration Validation

#### Data Integrity Checks
```bash
#!/bin/bash
# validate-migration.sh

# Row count validation
for db in auth_db exercises_db scores_db; do
    local_count=$(docker exec ${db}_postgres psql -U postgres -d $db -t -c "SELECT COUNT(*) FROM $(echo $db | sed 's/_db//' | sed 's/auth_db/users/');")
    rds_count=$(PGPASSWORD=$RDS_PASSWORD psql -h localhost -U postgres -d $db -t -c "SELECT COUNT(*) FROM $(echo $db | sed 's/_db//' | sed 's/auth_db/users/');")

    if [ "$local_count" = "$rds_count" ]; then
        echo "✅ $db: $local_count rows match"
    else
        echo "❌ $db: mismatch ($local_count vs $rds_count)"
        exit 1
    fi
done

echo "✅ All data integrity checks passed"
```

---

## Monitoring and Validation

### 1. Infrastructure Health Checks

#### Kubernetes Cluster Health
```bash
# Check cluster health
kubectl get nodes -o wide
kubectl get pods --all-namespaces
kubectl get services --all-namespaces

# Check resource usage
kubectl top nodes
kubectl top pods --all-namespaces
```

#### AWS Resource Health
```bash
# Check EKS cluster status
aws eks describe-cluster --name eks-1 --query 'cluster.status'

# Check RDS instance status
aws rds describe-db-instances --db-instance-identifier nt114-dev-postgres

# Check EC2 instances
aws ec2 describe-instances --filters "Name=tag:Name,Values=*nt114*" --query 'Reservations[*].Instances[*].[InstanceId,State.Name,Tags[?Key==`Name`].Value]'
```

### 2. Application Health Checks

#### Service Endpoints
```bash
# Set up port forwarding
kubectl port-forward service/api-gateway-service 8080:80 -n dev &
API_PID=$!

kubectl port-forward service/frontend-service 3000:3000 -n dev &
FE_PID=$!

# Test endpoints
sleep 5
curl -f http://localhost:8080/health || echo "API Gateway health check failed"
curl -f http://localhost:3000 || echo "Frontend health check failed"

# Clean up
kill $API_PID $FE_PID 2>/dev/null
```

#### Database Connectivity
```bash
# Test database connections
kubectl run db-test --image=postgres:15-alpine --rm -i --restart=Never -- \
  bash -c "
for db in auth_db exercises_db scores_db; do
    PGPASSWORD=\$POSTGRES_PASSWORD psql -h \$DB_HOST -U postgres -d \$db -c 'SELECT 1;'
    echo \"✅ Connected to \$db\"
done
"
```

### 3. Performance Monitoring

#### CloudWatch Metrics
```bash
# Get recent CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EKS \
  --metric-name ClusterResourceUsage \
  --dimensions Name=ClusterName,Value=eks-1 \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

#### Application Performance
```bash
# Deploy monitoring stack (optional)
kubectl apply -f kubernetes/monitoring/ -n monitoring

# Check monitoring dashboards
kubectl get pods -n monitoring
kubectl get services -n monitoring
```

---

## Troubleshooting

### 1. Common Issues and Solutions

#### GitHub Actions Failures
```bash
# Check workflow logs
gh run list --limit 10
gh run view --log <run-id>

# Common fixes:
# 1. Check AWS credentials in GitHub secrets
# 2. Verify BASTION_PUBLIC_KEY is correctly set
# 3. Check Terraform backend configuration
# 4. Validate IAM permissions
```

#### EKS Cluster Issues
```bash
# Check cluster status
aws eks describe-cluster --name eks-1

# Get node diagnostics
kubectl describe nodes

# Check pod issues
kubectl describe pod <pod-name> -n dev
kubectl logs <pod-name> -n dev --tail=100
```

#### PostgreSQL Deployment Issues
```bash
# Check StatefulSet status
kubectl get statefulset postgres -n dev -o wide
kubectl describe statefulset postgres -n dev

# Check PVC status
kubectl get pvc -n dev
kubectl describe pvc <pvc-name> -n dev

# Check storage class
kubectl get storageclass
kubectl describe storageclass ebs-gp3-encrypted
```

#### SSH Connection Issues
```bash
# Test SSH to bastion host
ssh -i nt114-bastion-devsecops-251114 -v ec2-user@<bastion-ip>

# Check security groups
aws ec2 describe-security-groups --filters "Name=group-name,Values=*bastion*"

# Verify key pair in AWS
aws ec2 describe-key-pairs --key-names nt114-bastion-devsecops-251114
```

### 2. Recovery Procedures

#### Infrastructure Rollback
```bash
cd terraform/environments/dev

# Destroy specific resources
terraform destroy -target=module.eks_cluster -auto-approve
terraform destroy -target=module.vpc -auto-approve

# Re-deploy
terraform apply -auto-approve
```

#### Application Recovery
```bash
# Scale down services
kubectl scale deployment --all --replicas=0 -n dev

# Reset PVCs (if needed)
kubectl delete pvc --all -n dev

# Re-deploy applications
kubectl apply -f kubernetes/ -n dev
```

#### Database Recovery
```bash
# Connect to bastion host
ssh -i nt114-bastion-devsecops-251114 ec2-user@<bastion-ip>

# Access PostgreSQL and restore from backup
psql -h $RDS_ENDPOINT -U postgres -d postgres -f backup.sql
```

---

## Maintenance and Updates

### 1. Regular Maintenance Tasks

#### Weekly Tasks
```bash
#!/bin/bash
# weekly-maintenance.sh

echo "Starting weekly maintenance..."

# Update Kubernetes packages
kubectl get pods --all-namespaces -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u

# Check for security updates
aws eks describe-cluster --name eks-1 --query 'cluster.version'
kubectl version --short

# Review CloudWatch metrics and alerts
aws cloudwatch describe-alarms --state-value ALARM

echo "Weekly maintenance completed"
```

#### Monthly Tasks
```bash
#!/bin/bash
# monthly-maintenance.sh

echo "Starting monthly maintenance..."

# Rotate SSH keys (quarterly, check if needed)
KEY_DATE=$(ssh-keygen -lf nt114-bastion-devsecops-*.pub | head -1 | awk '{print $2}')
echo "Current key date: $KEY_DATE"

# Update Terraform modules
cd terraform
terraform get -update

# Review IAM policies and access
aws iam list-policies --scope Local --max-items 100

echo "Monthly maintenance completed"
```

### 2. Update Procedures

#### Application Updates
```bash
# Update application images
# 1. Update image tags in deployment files
# 2. Commit changes
git add kubernetes/
git commit -m "feat: update application images to latest versions"
git push origin main

# 3. Trigger deployment
gh workflow run deploy-to-eks.yml --field environment=dev
```

#### Infrastructure Updates
```bash
# Update Terraform configuration
cd terraform/environments/dev

# Check for updates
terraform plan

# Apply updates
terraform apply -auto-approve
```

#### Kubernetes Version Updates
```bash
# Check available versions
aws eks describe-cluster --name eks-1 --query 'cluster.version'
aws eks list-addon-versions --kubernetes-version 1.28

# Update cluster (carefully planned)
aws eks update-cluster-version \
  --name eks-1 \
  --kubernetes-version 1.29 \
  --no-cli-paginate
```

---

## Security Best Practices

### 1. Access Control

#### SSH Key Management
- **Store private keys** in encrypted password managers
- **Rotate keys quarterly** or immediately upon compromise
- **Limit key access** to authorized team members only
- **Audit key usage** through AWS CloudTrail

#### IAM Security
- **Use least privilege** access for all IAM roles
- **Rotate access keys** every 90 days
- **Enable MFA** for all IAM users
- **Regular access reviews** for permissions

### 2. Network Security

#### Security Group Rules
```bash
# Review current security groups
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=<vpc-id>"

# Example bastion security group (should be restrictive)
aws ec2 authorize-security-group-ingress \
  --group-id <bastion-sg-id> \
  --protocol tcp \
  --port 22 \
  --cidr 203.0.113.0/24  # Your corporate IP range
```

#### VPC Monitoring
```bash
# Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids <vpc-id> \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name VPCFlowLogs
```

### 3. Application Security

#### Container Security
```bash
# Scan images for vulnerabilities
trivy image nt114/user-management:latest
trivy image nt114/exercises-service:latest
trivy image nt114/scores-service:latest

# Update base images regularly
# Use non-root users in containers
# Implement runtime security monitoring
```

---

## Cost Optimization

### 1. Resource Rightsizing

#### Monitoring Resource Usage
```bash
# Check EKS node utilization
kubectl top nodes
kubectl describe nodes

# Review RDS performance
aws rds describe-db-log-files \
  --db-instance-identifier nt114-dev-postgres \
  --filename-prefix error/postgresql.log.
```

#### Optimization Recommendations
- **EKS**: Use right-sized node instances based on actual usage
- **RDS**: Consider serverless or smaller instances for dev environments
- **Storage**: Use gp3 volumes with appropriate IOPS and throughput
- **Load Balancer**: Ensure proper load balancer type and configuration

### 2. Cost Monitoring

#### Set Up Billing Alerts
```bash
# Create billing alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "AWS-Billing-Alarm" \
  --alarm-description "Alarm when AWS billing exceeds $100" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Conclusion

This deployment guide provides comprehensive instructions for deploying and maintaining the NT114 DevSecOps infrastructure. The deployment process emphasizes:

- **Automation**: Use of GitHub Actions for CI/CD
- **Security**: SSH key management and least-privilege access
- **Reliability**: Proper error handling and recovery procedures
- **Scalability**: Auto-scaling and performance optimization
- **Maintainability**: Clear documentation and monitoring

**Key Success Factors:**
1. Proper SSH key configuration and GitHub secret management
2. Complete AWS IAM permissions for GitHub Actions
3. Regular monitoring and maintenance procedures
4. Comprehensive backup and disaster recovery plans
5. Security best practices throughout the deployment

The infrastructure is production-ready with proper observability, security controls, and operational procedures in place.

---

**Document Version**: 2.0
**Last Updated**: November 14, 2025
**Next Review**: December 14, 2025
**Deployment Status**: ✅ Production Ready

## Support and Contact

For deployment issues or questions:
- **Documentation**: Refer to project docs folder
- **GitHub Issues**: Create issues for specific problems
- **Team Contacts**: Refer to project team communication channels
- **Emergency**: Follow incident response procedures in security documentation

---

**Classification**: Internal - Confidential
**Distribution**: DevOps Team, System Administrators