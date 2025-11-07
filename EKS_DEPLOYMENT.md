# 🚀 Deployment Guide - AWS EKS

This guide explains how to deploy the NT114 DevSecOps application to AWS EKS.

## 📋 Prerequisites

Before deploying to EKS, ensure you have:

- ✅ AWS Account with appropriate permissions
- ✅ AWS CLI installed and configured
- ✅ kubectl installed (v1.28+)
- ✅ Helm installed (v3.12+)
- ✅ Docker images pushed to ECR (done automatically via GitHub Actions)
- ✅ EKS cluster created (via Terraform)

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   AWS EKS Cluster                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐    ┌──────────────────────────┐  │
│  │   Frontend   │◄───┤   Application Load       │  │
│  │   (React)    │    │   Balancer (ALB)         │  │
│  └──────┬───────┘    └──────────────────────────┘  │
│         │                                           │
│         ▼                                           │
│  ┌──────────────┐                                   │
│  │ API Gateway  │                                   │
│  │   (Node.js)  │                                   │
│  └──────┬───────┘                                   │
│         │                                           │
│    ┌────┴────┬─────────┬──────────┐                │
│    ▼         ▼         ▼          ▼                │
│  ┌────┐  ┌─────┐  ┌──────┐  ┌──────┐              │
│  │User│  │Exer-│  │Scores│  │More  │              │
│  │Mgmt│  │cises│  │      │  │      │              │
│  └──┬─┘  └──┬──┘  └───┬──┘  └───┬──┘              │
│     │       │         │         │                  │
│     └───────┴─────────┴─────────┘                  │
│                    ▼                                │
│            ┌──────────────┐                         │
│            │  PostgreSQL  │                         │
│            └──────────────┘                         │
└─────────────────────────────────────────────────────┘
```

## 🔄 Deployment Flow

### Step 1: Create EKS Infrastructure

The infrastructure is managed by Terraform and deployed via GitHub Actions.

**Option A: Automatic (via GitHub Actions)**

1. Any push to `main` branch that modifies `terraform/**` triggers the workflow
2. Or manually trigger via GitHub Actions:
   - Go to **Actions** → **EKS Terraform Deployment**
   - Click **Run workflow**
   - Select:
     - Action: `apply`
     - Environment: `dev`

**Option B: Manual (via local Terraform)**

```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply -auto-approve
```

**What gets created:**
- ✅ VPC with public and private subnets
- ✅ EKS Control Plane
- ✅ EKS Node Group (t3.medium instances)
- ✅ ECR Repositories for each service
- ✅ IAM Roles and Policies
- ✅ Security Groups
- ✅ NAT Gateways and Internet Gateway

**Wait time:** ~15-20 minutes for cluster creation

---

### Step 2: Build and Push Docker Images to ECR

This is done automatically via GitHub Actions when code is pushed.

**Workflows:**
- `backend-build.yml` - Builds and pushes microservices
- `frontend-build.yml` - Builds and pushes frontend

**Triggered by:**
- Changes to `microservices/**` (backend)
- Changes to `frontend/**` (frontend)

**Manual trigger:**
```bash
# Go to GitHub Actions → Backend/Frontend Build → Run workflow
```

**Images pushed to:**
```
<account-id>.dkr.ecr.us-east-1.amazonaws.com/nt114-devsecops/api-gateway:latest
<account-id>.dkr.ecr.us-east-1.amazonaws.com/nt114-devsecops/user-management-service:latest
<account-id>.dkr.ecr.us-east-1.amazonaws.com/nt114-devsecops/exercises-service:latest
<account-id>.dkr.ecr.us-east-1.amazonaws.com/nt114-devsecops/scores-service:latest
<account-id>.dkr.ecr.us-east-1.amazonaws.com/nt114-devsecops/frontend:latest
```

---

### Step 3: Deploy Applications to EKS

Once the cluster is ready and images are in ECR:

**Option A: Via GitHub Actions (Recommended)**

1. Go to **Actions** → **Deploy Applications to EKS**
2. Click **Run workflow**
3. Select:
   - Environment: `dev`
   - Services: `all` (or specific services)
4. Click **Run workflow**

**Option B: Via Local Script**

```bash
# From project root
./scripts/deploy-to-eks.sh
```

**Option C: Manual Helm Deployment**

```bash
# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

# Configure kubectl
aws eks update-kubeconfig --region $REGION --name nt114-devsecops-dev

# Create namespace
kubectl create namespace dev

# Create ECR secret
kubectl create secret docker-registry ecr-secret \
  --docker-server=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region $REGION) \
  --namespace=dev

# Deploy PostgreSQL
kubectl apply -f kubernetes/local/postgres-deployment.yaml -n dev

# Deploy services using Helm
helm upgrade --install user-management-service ./helm/user-management-service \
  --namespace dev \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/user-management-service \
  --set image.tag=latest \
  --set imagePullSecrets[0].name=ecr-secret

helm upgrade --install exercises-service ./helm/exercises-service \
  --namespace dev \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/exercises-service \
  --set image.tag=latest \
  --set imagePullSecrets[0].name=ecr-secret

helm upgrade --install scores-service ./helm/scores-service \
  --namespace dev \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/scores-service \
  --set image.tag=latest \
  --set imagePullSecrets[0].name=ecr-secret

helm upgrade --install api-gateway ./helm/api-gateway \
  --namespace dev \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/api-gateway \
  --set image.tag=latest \
  --set imagePullSecrets[0].name=ecr-secret

helm upgrade --install frontend ./helm/frontend \
  --namespace dev \
  --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/frontend \
  --set image.tag=latest \
  --set imagePullSecrets[0].name=ecr-secret
```

---

### Step 4: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n dev

# Check services
kubectl get svc -n dev

# Check ingress (ALB)
kubectl get ingress -n dev

# Check logs of a specific pod
kubectl logs -f <pod-name> -n dev

# Get load balancer URLs
kubectl get svc api-gateway -n dev
kubectl get svc frontend -n dev
```

---

## 🔍 Monitoring & Troubleshooting

### View Application Logs

```bash
# API Gateway logs
kubectl logs -f deployment/api-gateway -n dev

# User Management Service logs
kubectl logs -f deployment/user-management-service -n dev

# Frontend logs
kubectl logs -f deployment/frontend -n dev
```

### Port Forward for Local Testing

```bash
# Forward API Gateway
kubectl port-forward svc/api-gateway 8080:8080 -n dev

# Forward Frontend
kubectl port-forward svc/frontend 3000:80 -n dev

# Forward PostgreSQL
kubectl port-forward svc/postgres 5432:5432 -n dev
```

### Common Issues

#### 1. ImagePullBackOff

**Cause:** ECR credentials expired or images not found

**Solution:**
```bash
# Recreate ECR secret
kubectl delete secret ecr-secret -n dev
kubectl create secret docker-registry ecr-secret \
  --docker-server=$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com \
  --docker-username=AWS \
  --docker-password=$(aws ecr get-login-password --region us-east-1) \
  --namespace=dev
```

#### 2. CrashLoopBackOff

**Cause:** Application crashes on startup

**Solution:**
```bash
# Check logs
kubectl logs <pod-name> -n dev

# Check events
kubectl describe pod <pod-name> -n dev

# Common fixes:
# - Database not ready → wait for postgres pod
# - Wrong environment variables → check Helm values
# - Application bug → check application logs
```

#### 3. Pods Pending

**Cause:** Insufficient resources or node not ready

**Solution:**
```bash
# Check node status
kubectl get nodes

# Check pod events
kubectl describe pod <pod-name> -n dev

# Scale node group if needed (via Terraform or AWS Console)
```

---

## 🎯 Access Your Application

After successful deployment:

1. **Get Load Balancer URLs:**
```bash
kubectl get svc -n dev
```

2. **API Gateway:**
```
http://<api-gateway-load-balancer-url>:8080
```

3. **Frontend:**
```
http://<frontend-load-balancer-url>
```

4. **Health Check Endpoints:**
```bash
curl http://<api-gateway-lb>:8080/health
```

---

## 🧹 Cleanup Resources

**Option A: Destroy Everything (via GitHub Actions)**

1. Go to **Actions** → **EKS Terraform Deployment**
2. Click **Run workflow**
3. Select:
   - Action: `destroy`
   - Environment: `dev`

**Option B: Manual Cleanup**

```bash
# Delete Helm releases
helm uninstall api-gateway -n dev
helm uninstall frontend -n dev
helm uninstall user-management-service -n dev
helm uninstall exercises-service -n dev
helm uninstall scores-service -n dev

# Delete Kubernetes resources
kubectl delete -f kubernetes/local/postgres-deployment.yaml -n dev
kubectl delete namespace dev

# Destroy EKS infrastructure
cd terraform/environments/dev
terraform destroy -auto-approve
```

**⚠️ Warning:** This will delete all resources and data. Make sure to backup important data first!

---

## 📊 Cost Optimization

**Estimated Monthly Cost (dev environment):**
- EKS Control Plane: $73/month
- EC2 Instances (2x t3.medium): ~$60/month
- NAT Gateway: ~$33/month
- Data Transfer: Varies
- **Total: ~$165-200/month**

**Cost Saving Tips:**
1. Stop node groups when not in use
2. Use Spot Instances for non-production
3. Auto-destroy dev environment after hours
4. Use smaller instance types for testing

---

## 🔐 Security Best Practices

- ✅ All services run in private subnets
- ✅ ECR images scanned for vulnerabilities
- ✅ Secrets managed via Kubernetes Secrets
- ✅ HTTPS enabled via ALB (configure SSL certificate)
- ✅ Pod security policies enforced
- ✅ Network policies for service isolation
- ✅ IAM roles with least privilege

---

## 📚 Additional Resources

- [Terraform Configuration](./terraform/README.md)
- [Local Development Guide](./LOCAL_DEPLOYMENT.md)
- [Troubleshooting Guide](./terraform/TROUBLESHOOTING.md)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Helm Documentation](https://helm.sh/docs/)

---

## 🆘 Support

If you encounter issues:

1. Check the [Troubleshooting Guide](./terraform/TROUBLESHOOTING.md)
2. Review workflow logs in GitHub Actions
3. Check pod logs: `kubectl logs <pod> -n dev`
4. Review EKS cluster events: `kubectl get events -n dev --sort-by='.lastTimestamp'`

---

**Last Updated:** 2025-01-07
**Version:** 1.0.0
