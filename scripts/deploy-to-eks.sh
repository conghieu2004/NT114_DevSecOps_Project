#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-nt114-devsecops-dev}"
NAMESPACE="${NAMESPACE:-dev}"

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   NT114 DevSecOps - Deploy to EKS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo -e "${RED}❌ helm not found. Please install helm.${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ aws cli not found. Please install AWS CLI.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Get AWS Account ID
echo -e "${YELLOW}Getting AWS Account ID...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account ID: $ACCOUNT_ID${NC}"
echo ""

# Configure kubectl
echo -e "${YELLOW}Configuring kubectl for EKS cluster...${NC}"
aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to configure kubectl. Is the EKS cluster created?${NC}"
    echo -e "${YELLOW}💡 Run the Terraform workflow first to create the cluster.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ kubectl configured${NC}"
echo ""

# Show cluster info
echo -e "${YELLOW}Cluster Information:${NC}"
kubectl cluster-info
kubectl get nodes
echo ""

# Create namespace
echo -e "${YELLOW}Creating namespace: $NAMESPACE${NC}"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✅ Namespace created/updated${NC}"
echo ""

# Create ECR secret
echo -e "${YELLOW}Creating ECR pull secret...${NC}"
ECR_PASSWORD=$(aws ecr get-login-password --region $REGION)
kubectl create secret docker-registry ecr-secret \
    --docker-server=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com \
    --docker-username=AWS \
    --docker-password=$ECR_PASSWORD \
    --namespace=$NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

echo -e "${GREEN}✅ ECR secret created${NC}"
echo ""

# Deploy PostgreSQL
echo -e "${YELLOW}Deploying PostgreSQL database...${NC}"
kubectl apply -f kubernetes/local/postgres-deployment.yaml -n $NAMESPACE

echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
echo -e "${GREEN}✅ PostgreSQL deployed and ready${NC}"
echo ""

# Function to deploy a service using Helm
deploy_service() {
    local service_name=$1
    local chart_path=$2
    local image_name=$3

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Deploying $service_name...${NC}"

    helm upgrade --install $service_name $chart_path \
        --namespace $NAMESPACE \
        --set image.repository=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nt114-devsecops/$image_name \
        --set image.tag=latest \
        --set imagePullSecrets[0].name=ecr-secret \
        --wait --timeout 10m

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $service_name deployed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to deploy $service_name${NC}"
        return 1
    fi
    echo ""
}

# Deploy all services
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Deploying Microservices${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

deploy_service "user-management-service" "./helm/user-management-service" "user-management-service"
deploy_service "exercises-service" "./helm/exercises-service" "exercises-service"
deploy_service "scores-service" "./helm/scores-service" "scores-service"
deploy_service "api-gateway" "./helm/api-gateway" "api-gateway"
deploy_service "frontend" "./helm/frontend" "frontend"

# Wait for all pods to be ready
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Waiting for all pods to be ready...${NC}"
kubectl wait --for=condition=ready pod --all -n $NAMESPACE --timeout=600s
echo -e "${GREEN}✅ All pods are ready${NC}"
echo ""

# Show deployment status
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Deployment Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}📋 Deployments:${NC}"
kubectl get deployments -n $NAMESPACE
echo ""

echo -e "${YELLOW}🔧 Services:${NC}"
kubectl get services -n $NAMESPACE
echo ""

echo -e "${YELLOW}📦 Pods:${NC}"
kubectl get pods -n $NAMESPACE -o wide
echo ""

echo -e "${YELLOW}🌐 Ingresses:${NC}"
kubectl get ingress -n $NAMESPACE
echo ""

# Get Load Balancer URLs
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Access Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

API_GATEWAY_LB=$(kubectl get service api-gateway -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
FRONTEND_LB=$(kubectl get service frontend -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

if [ ! -z "$API_GATEWAY_LB" ]; then
    echo -e "${GREEN}🔗 API Gateway: http://$API_GATEWAY_LB${NC}"
fi

if [ ! -z "$FRONTEND_LB" ]; then
    echo -e "${GREEN}🔗 Frontend: http://$FRONTEND_LB${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✅ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}💡 Useful commands:${NC}"
echo -e "  - View logs: ${BLUE}kubectl logs -f <pod-name> -n $NAMESPACE${NC}"
echo -e "  - Port forward: ${BLUE}kubectl port-forward svc/<service-name> 8080:8080 -n $NAMESPACE${NC}"
echo -e "  - Get pods: ${BLUE}kubectl get pods -n $NAMESPACE${NC}"
echo -e "  - Describe pod: ${BLUE}kubectl describe pod <pod-name> -n $NAMESPACE${NC}"
echo ""
