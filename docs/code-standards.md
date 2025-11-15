# NT114 DevSecOps Code Standards and Practices

**Version:** 2.0
**Last Updated:** November 14, 2025
**Status:** ✅ Current and Enforced

---

## Overview

This document defines the coding standards, development practices, and security procedures for the NT114 DevSecOps project. Adherence to these standards ensures code quality, maintainability, security, and operational excellence.

---

## Table of Contents

1. [Code Organization and Structure](#code-organization-and-structure)
2. [Coding Standards by Language](#coding-standards-by-language)
3. [Git and Version Control](#git-and-version-control)
4. [Infrastructure as Code Standards](#infrastructure-as-code-standards)
5. [SSH Key Management Procedures](#ssh-key-management-procedures)
6. [Security Standards](#security-standards)
7. [Testing Standards](#testing-standards)
8. [Documentation Standards](#documentation-standards)
9. [CI/CD Pipeline Standards](#cicd-pipeline-standards)
10. [Code Review Process](#code-review-process)

---

## Code Organization and Structure

### 1. Repository Structure

```
NT114_DevSecOps_Project/
├── .github/                    # GitHub workflows and configurations
│   └── workflows/             # CI/CD pipeline definitions
├── .claude/                   # Claude Code configurations
│   └── workflows/             # Development workflows
├── argocd/                    # ArgoCD application manifests
├── devops/                    # DevOps configurations and scripts
├── docs/                      # Project documentation
├── helm/                      # Helm charts for Kubernetes
├── kubernetes/                # Kubernetes manifests
├── microservices/             # Backend service source code
│   ├── user-management/       # Authentication service
│   ├── exercises/             # Exercise management service
│   └── scores/                # Scoring service
├── terraform/                 # Infrastructure as Code
│   └── environments/          # Environment-specific configurations
└── frontend/                  # Frontend React application
```

### 2. Naming Conventions

#### File and Directory Naming
- **Use kebab-case** for directories: `user-management`, `kubernetes-manifests`
- **Use descriptive names** that clearly indicate purpose
- **Avoid abbreviations** unless widely understood
- **Use consistent extensions**: `.py`, `.js`, `.tf`, `.yaml`

#### Service Naming
- **Use kebab-case** for service names: `user-management-service`
- **Include environment suffix**: `user-management-service-dev`
- **Use consistent naming** across all deployment manifests

#### Resource Naming
```yaml
# Kubernetes resources
metadata:
  name: user-management-service
  namespace: dev
  labels:
    app: user-management
    version: v1.0.0

# Terraform resources
resource "aws_eks_cluster" "main" {
  name = "${var.project_name}-${var.environment}-eks-cluster"
  # ...
}
```

### 3. Module and Package Organization

#### Python Services (Flask)
```
microservices/user-management/
├── app/
│   ├── __init__.py
│   ├── models/                # Database models
│   ├── routes/                # API endpoints
│   ├── services/              # Business logic
│   ├── utils/                 # Utility functions
│   └── config.py              # Configuration
├── tests/                     # Unit and integration tests
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
└── run.py                     # Application entry point
```

#### React Frontend
```
frontend/
├── public/                    # Static assets
├── src/
│   ├── components/            # Reusable React components
│   ├── pages/                 # Page components
│   ├── services/              # API service functions
│   ├── utils/                 # Utility functions
│   ├── hooks/                 # Custom React hooks
│   ├── styles/                # CSS/SCSS files
│   └── App.js                 # Main application component
├── package.json               # Node.js dependencies
└── Dockerfile                 # Container configuration
```

---

## Coding Standards by Language

### 1. Python (Flask Services)

#### Code Style
```python
# Use Black for code formatting
# Use flake8 for linting
# Follow PEP 8 style guide

# Imports organization
import os
import logging
from datetime import datetime
from typing import Optional, List

import bcrypt
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

# Constants
DEFAULT_PAGE_SIZE = 20
MAX_LOGIN_ATTEMPTS = 5

# Class definitions
class UserService:
    """Service class for user management operations."""

    def __init__(self, db: SQLAlchemy):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def create_user(self, user_data: dict) -> Optional[dict]:
        """Create a new user with validation and security checks.

        Args:
            user_data: Dictionary containing user information

        Returns:
            User dictionary if successful, None otherwise

        Raises:
            ValueError: If user data is invalid
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate input data
            if not self._validate_user_data(user_data):
                raise ValueError("Invalid user data provided")

            # Hash password securely
            hashed_password = bcrypt.hashpw(
                user_data['password'].encode('utf-8'),
                bcrypt.gensalt()
            )

            # Create user record
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=hashed_password.decode('utf-8'),
                created_at=datetime.utcnow()
            )

            self.db.session.add(user)
            self.db.session.commit()

            self.logger.info(f"User created successfully: {user.username}")
            return self._user_to_dict(user)

        except SQLAlchemyError as e:
            self.db.session.rollback()
            self.logger.error(f"Database error creating user: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error creating user: {str(e)}")
            return None
```

#### Configuration Management
```python
# config.py
import os
from typing import Optional

class Config:
    """Application configuration with environment variable support."""

    # Database configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost/postgres')
    DATABASE_POOL_SIZE: int = int(os.getenv('DATABASE_POOL_SIZE', '10'))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv('DATABASE_POOL_TIMEOUT', '30'))

    # Security configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', os.urandom(32))
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))

    # Service configuration
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'production')
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # API configuration
    API_VERSION: str = os.getenv('API_VERSION', 'v1')
    RATE_LIMIT: str = os.getenv('RATE_LIMIT', '100/hour')

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration parameters."""
        required_vars = ['DATABASE_URL', 'SECRET_KEY']

        for var in required_vars:
            if not getattr(cls, var):
                raise ValueError(f"Required environment variable {var} is not set")

        return True
```

### 2. JavaScript/React (Frontend)

#### Code Style
```javascript
// Use ESLint + Prettier for code formatting
// Follow Airbnb JavaScript Style Guide
// Use functional components with hooks

// Component structure
import React, { useState, useEffect, useCallback } from 'react';
import { PropTypes } from 'prop-types';
import { useNavigate } from 'react-router-dom';
import { fetchExercises, submitSolution } from '../services/exerciseService';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';
import './ExerciseList.css';

const ExerciseList = ({
  difficulty = 'all',
  category = 'all',
  onExerciseSelect
}) => {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  // Memoized fetch function to prevent unnecessary re-renders
  const loadExercises = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = {
        page,
        difficulty: difficulty !== 'all' ? difficulty : undefined,
        category: category !== 'all' ? category : undefined,
      };

      const response = await fetchExercises(params);
      setExercises(response.data);
    } catch (err) {
      setError(err.message || 'Failed to load exercises');
    } finally {
      setLoading(false);
    }
  }, [difficulty, category, page]);

  useEffect(() => {
    loadExercises();
  }, [loadExercises]);

  const handleExerciseClick = useCallback((exerciseId) => {
    if (onExerciseSelect) {
      onExerciseSelect(exerciseId);
    } else {
      navigate(`/exercises/${exerciseId}`);
    }
  }, [onExerciseSelect, navigate]);

  if (loading && exercises.length === 0) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={loadExercises} />;
  }

  return (
    <div className="exercise-list" data-testid="exercise-list">
      <h2>Exercises</h2>
      <div className="exercise-grid">
        {exercises.map((exercise) => (
          <ExerciseCard
            key={exercise.id}
            exercise={exercise}
            onClick={() => handleExerciseClick(exercise.id)}
            data-testid={`exercise-card-${exercise.id}`}
          />
        ))}
      </div>
      {loading && <LoadingSpinner overlay />}
    </div>
  );
};

ExerciseList.propTypes = {
  difficulty: PropTypes.oneOf(['all', 'beginner', 'intermediate', 'advanced']),
  category: PropTypes.string,
  onExerciseSelect: PropTypes.func,
};

export default ExerciseList;
```

#### API Service Functions
```javascript
// services/exerciseService.js
import axios from 'axios';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8080',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle authentication error
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const exerciseService = {
  /**
   * Fetch exercises with optional filtering
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} - Exercises data with pagination
   */
  async fetchExercises(params = {}) {
    const response = await apiClient.get('/api/v1/exercises', { params });
    return response.data;
  },

  /**
   * Submit exercise solution
   * @param {string} exerciseId - Exercise ID
   * @param {Object} solution - Solution data
   * @returns {Promise<Object>} - Submission result
   */
  async submitSolution(exerciseId, solution) {
    const response = await apiClient.post(`/api/v1/exercises/${exerciseId}/submit`, solution);
    return response.data;
  },

  /**
   * Get exercise details
   * @param {string} exerciseId - Exercise ID
   * @returns {Promise<Object>} - Exercise details
   */
  async getExercise(exerciseId) {
    const response = await apiClient.get(`/api/v1/exercises/${exerciseId}`);
    return response.data;
  },
};

export default exerciseService;
```

### 3. YAML (Kubernetes and GitHub Actions)

#### Kubernetes Manifests
```yaml
# Use consistent structure and naming
# Include proper resource limits and requests
# Use labels for resource identification

apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-management-service
  namespace: dev
  labels:
    app: user-management
    version: v1.0.0
    component: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-management
      component: backend
  template:
    metadata:
      labels:
        app: user-management
        version: v1.0.0
        component: backend
    spec:
      containers:
      - name: user-management
        image: nt114/user-management:v1.0.0
        ports:
        - containerPort: 5001
          name: http
          protocol: TCP
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secrets
              key: url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: secret-key
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 5001
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
      securityContext:
        fsGroup: 1000
```

#### GitHub Actions Workflows
```yaml
# Use consistent job and step naming
# Include proper error handling and validation
# Use environment variables for configuration

name: Deploy to EKS

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - staging
          - prod
      action:
        description: 'Deployment action'
        required: true
        default: 'apply'
        type: choice
        options:
          - plan
          - apply

env:
  AWS_REGION: us-east-1
  KUBECTL_VERSION: v1.28.0

jobs:
  deploy:
    name: Deploy Applications to EKS
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Install kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: ${{ env.KUBECTL_VERSION }}

      - name: Configure kubectl for EKS
        run: |
          aws eks update-kubeconfig \
            --region ${{ env.AWS_REGION }} \
            --name eks-1

      - name: Validate cluster connectivity
        run: |
          kubectl get nodes
          kubectl get namespaces

      - name: Deploy application services
        run: |
          echo "Deploying to environment: ${{ inputs.environment }}"
          kubectl apply -f kubernetes/services/ -n ${{ inputs.environment }}

          # Wait for deployments to be ready
          kubectl wait --for=condition=available deployment --all -n ${{ inputs.environment }} --timeout=600s

      - name: Verify deployment
        run: |
          # Check pod status
          kubectl get pods -n ${{ inputs.environment }}

          # Check service endpoints
          kubectl get services -n ${{ inputs.environment }}

          # Run basic connectivity tests
          kubectl run connectivity-test --image=busybox --rm -i --restart=Never -- \
            wget -qO- http://user-management-service.${{ inputs.environment }}.svc.cluster.local:5001/health || exit 1
```

---

## Git and Version Control

### 1. Branch Strategy

#### Branch Naming Conventions
```bash
# Feature branches
feature/user-authentication
feature/exercise-submission-api
feature/scores-dashboard

# Bugfix branches
bugfix/login-validation-error
bugfix/database-connection-leak

# Hotfix branches
hotfix/security-vulnerability-patch
hotfix/critical-production-issue

# Release branches
release/v1.0.0
release/v1.1.0

# Infrastructure branches
infra/add-rds-support
infra/update-kubernetes-version
```

#### Commit Message Format
```bash
# Format: <type>(<scope>): <description>
# Types: feat, fix, docs, style, refactor, test, chore, infra, security

# Examples
feat(auth): add JWT token refresh mechanism
fix(api): resolve user creation validation error
docs(readme): update installation instructions
style(frontend): fix ESLint warnings in ExerciseList component
refactor(database): extract common query logic into service layer
test(user-service): add unit tests for password hashing
chore(deps): update Python dependencies to latest versions
infra(terraform): add RDS PostgreSQL configuration
security(ssh): implement key rotation procedures
```

#### Commit Message Guidelines
```bash
# Good commit messages
feat(user-management): implement OAuth2 authentication
fix(database): resolve connection pool exhaustion issue
docs(deployment): add troubleshooting guide for Kubernetes

# Bad commit messages (avoid)
fixed bug
updates
wip
test changes
```

### 2. Workflow Integration

#### Pull Request Requirements
```yaml
# .github/workflows/pr-checks.yml
name: Pull Request Checks

on:
  pull_request:
    branches: [main, develop]

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r microservices/user-management/requirements.txt
          pip install flake8 black pytest pytest-cov

      - name: Code formatting check
        run: |
          black --check microservices/

      - name: Lint Python code
        run: |
          flake8 microservices/ --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 microservices/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

      - name: Run unit tests
        run: |
          pytest microservices/ --cov=microservices --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Infrastructure as Code Standards

### 1. Terraform Standards

#### Module Structure
```
terraform/
├── modules/                    # Reusable Terraform modules
│   ├── eks-cluster/           # EKS cluster module
│   ├── rds-postgresql/        # RDS PostgreSQL module
│   ├── bastion-host/          # Bastion host module
│   └── vpc/                   # VPC networking module
└── environments/              # Environment-specific configurations
    ├── dev/
    ├── staging/
    └── prod/
```

#### Module Naming and Structure
```hcl
# terraform/modules/eks-cluster/main.tf
module "eks_cluster" {
  source = "terraform-aws-modules/eks/aws"
  version = "19.21.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  subnet_ids      = var.subnet_ids
  vpc_id          = var.vpc_id

  # Control plane configuration
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = false

  # Node group configuration
  node_groups = {
    main = {
      desired_capacity = var.desired_capacity
      max_capacity     = var.max_capacity
      min_capacity     = var.min_capacity
      instance_type    = var.instance_type

      k8s_labels = {
        Environment = var.environment
        Project     = var.project_name
      }
    }
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-eks-cluster"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

#### Variable and Output Standards
```hcl
# terraform/modules/eks-cluster/variables.tf
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.28"
  validation {
    condition     = can(regex("^1\\.[0-9]+$", var.cluster_version))
    error_message = "Cluster version must be in format '1.x' where x is a number."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "nt114"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}
```

#### Resource Naming Standards
```hcl
# terraform/environments/dev/main.tf
locals {
  naming convention = "${var.project_name}-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    Owner       = var.owner
    ManagedBy   = "Terraform"
    CreatedAt   = timestamp()
  }
}

module "vpc" {
  source = "../../modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  cidr_block   = "10.0.0.0/16"

  tags = local.tags
}

module "eks_cluster" {
  source = "../../modules/eks-cluster"

  project_name = var.project_name
  environment  = var.environment
  cluster_name = "${local.naming_convention}-eks-cluster"
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnets

  tags = local.tags
}
```

### 2. Kubernetes Standards

#### Resource Naming Conventions
```yaml
# Consistent naming across all resources
metadata:
  name: user-management-service-${ENVIRONMENT}
  namespace: ${ENVIRONMENT}
  labels:
    app: user-management
    environment: ${ENVIRONMENT}
    version: ${VERSION}
    component: backend
    managed-by: terraform
```

#### Configuration Management
```yaml
# Use ConfigMaps for configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: dev
data:
  LOG_LEVEL: "INFO"
  API_VERSION: "v1"
  RATE_LIMIT: "100/hour"
  DATABASE_POOL_SIZE: "10"
  CACHE_TTL: "3600"

# Use Secrets for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: dev
type: Opaque
data:
  database-url: <base64-encoded>
  jwt-secret: <base64-encoded>
  api-key: <base64-encoded>
```

---

## SSH Key Management Procedures

### 1. SSH Key Generation Standards

#### Key Generation Requirements
```bash
#!/bin/bash
# generate-ssh-key.sh - Standard SSH key generation script

set -euo pipefail

# Configuration
KEY_TYPE="ed25519"
KDF_ROUNDS="100"
PROJECT_PREFIX="nt114-bastion-devsecops"

# Input validation
if [ $# -eq 0 ]; then
    DATE=$(date +%y%m%d)
else
    DATE="$1"
fi

KEY_NAME="${PROJECT_PREFIX}-${DATE}"
KEY_COMMENT="${PROJECT_PREFIX}@${DATE}"

echo "Generating SSH key pair..."
echo "Key Name: ${KEY_NAME}"
echo "Key Type: ${KEY_TYPE}"
echo "KDF Rounds: ${KDF_ROUNDS}"

# Generate key pair
ssh-keygen \
    -t "${KEY_TYPE}" \
    -a "${KDF_ROUNDS}" \
    -f "${KEY_NAME}" \
    -C "${KEY_COMMENT}" \
    -N ""

# Verify key generation
echo "Verifying key generation..."
if [ -f "${KEY_NAME}" ] && [ -f "${KEY_NAME}.pub" ]; then
    echo "✅ SSH key pair generated successfully"
    ssh-keygen -lf "${KEY_NAME}.pub"
    echo "Public key fingerprint: $(ssh-keygen -lf "${KEY_NAME}.pub" | awk '{print $2}')"
else
    echo "❌ SSH key generation failed"
    exit 1
fi

# Set proper permissions
chmod 600 "${KEY_NAME}"
chmod 644 "${KEY_NAME}.pub"

echo "✅ SSH key setup completed"
echo "Private key: ${KEY_NAME} (Permissions: 600)"
echo "Public key: ${KEY_NAME}.pub (Permissions: 644)"
```

#### Key Security Requirements
- **Algorithm**: ED25519 (recommended) or RSA 4096
- **KDF Rounds**: Minimum 100 for enhanced security
- **Passphrase**: None for automation keys, strong passphrase for personal keys
- **File Permissions**: 600 for private keys, 644 for public keys
- **Storage**: Encrypted password manager or secure storage

### 2. SSH Key Distribution

#### GitHub Secret Management
```bash
#!/bin/bash
# deploy-ssh-key-to-github.sh

set -euo pipefail

# Configuration
REPOSITORY="NT114DevSecOpsProject/NT114_DevSecOps_Project"
KEY_NAME="${1:-nt114-bastion-devsecops-251114}"
SECRET_NAME="BASTION_PUBLIC_KEY"

# Validate key file exists
if [ ! -f "${KEY_NAME}.pub" ]; then
    echo "❌ Public key file not found: ${KEY_NAME}.pub"
    exit 1
fi

# Read public key content
PUBLIC_KEY_CONTENT=$(cat "${KEY_NAME}.pub")

echo "Deploying SSH key to GitHub..."
echo "Repository: ${REPOSITORY}"
echo "Secret: ${SECRET_NAME}"
echo "Key: ${KEY_NAME}"

# Check GitHub CLI authentication
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI not authenticated. Run 'gh auth login' first."
    exit 1
fi

# Deploy secret to GitHub
echo "Setting GitHub secret..."
gh secret set "${SECRET_NAME}" \
    --repo "${REPOSITORY}" \
    --body "${PUBLIC_KEY_CONTENT}"

# Verify secret deployment
echo "Verifying secret deployment..."
if gh secret list --repo "${REPOSITORY}" | grep -q "${SECRET_NAME}"; then
    echo "✅ SSH key deployed successfully to GitHub"
    echo "Secret name: ${SECRET_NAME}"
    echo "Repository: ${REPOSITORY}"
else
    echo "❌ Failed to deploy SSH key to GitHub"
    exit 1
fi

# Display key fingerprint for verification
echo "Key fingerprint: $(ssh-keygen -lf "${KEY_NAME}.pub" | awk '{print $2}')"
```

#### Infrastructure Integration
```hcl
# terraform/modules/bastion-host/main.tf
resource "aws_key_pair" "bastion" {
  key_name   = var.key_name
  public_key = var.public_key
  tags = merge(var.tags, {
    Name        = "${var.project_name}-bastion-key-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  key_name               = aws_key_pair.bastion.key_name
  vpc_security_group_ids = [aws_security_group.bastion.id]

  # User data for SSH key setup
  user_data = base64encode(templatefile("${path.module}/bastion-setup.sh", {
    authorized_keys = var.public_key
  }))

  tags = merge(var.tags, {
    Name        = "${var.project_name}-bastion-${var.environment}"
    Environment = var.environment
  }
}
```

### 3. SSH Key Rotation Procedures

#### Quarterly Rotation Script
```bash
#!/bin/bash
# rotate-ssh-key.sh - Quarterly SSH key rotation

set -euo pipefail

# Configuration
REPOSITORY="NT114DevSecOpsProject/NT114_DevSecOps_Project"
SECRET_NAME="BASTION_PUBLIC_KEY"
PROJECT_PREFIX="nt114-bastion-devsecops"

# Backup current key configuration
echo "Creating backup of current SSH key configuration..."
CURRENT_KEY=$(find . -name "${PROJECT_PREFIX}-*.pub" -type f | head -1)
if [ -n "$CURRENT_KEY" ]; then
    BACKUP_DIR="backups/ssh-keys/$(date +%Y%m%d)"
    mkdir -p "$BACKUP_DIR"
    cp "${CURRENT_KEY}" "${CURRENT_KEY%.pub}" "$BACKUP_DIR/"
    echo "✅ Current key backed up to: $BACKUP_DIR"
fi

# Generate new SSH key
NEW_DATE=$(date +%y%m%d)
NEW_KEY_NAME="${PROJECT_PREFIX}-${NEW_DATE}"

echo "Generating new SSH key pair: ${NEW_KEY_NAME}"
ssh-keygen -t ed25519 -a 100 -f "${NEW_KEY_NAME}" -C "${PROJECT_PREFIX}@${NEW_DATE}" -N ""

# Set proper permissions
chmod 600 "${NEW_KEY_NAME}"
chmod 644 "${NEW_KEY_NAME}.pub"

# Display new key information
echo "✅ New SSH key generated:"
echo "Key Name: ${NEW_KEY_NAME}"
echo "Fingerprint: $(ssh-keygen -lf "${NEW_KEY_NAME}.pub" | awk '{print $2}')"

# Deploy to GitHub
echo "Deploying new key to GitHub..."
gh secret set "${SECRET_NAME}" \
    --repo "${REPOSITORY}" \
    --body "$(cat "${NEW_KEY_NAME}.pub")"

# Verify deployment
if gh secret list --repo "${REPOSITORY}" | grep -q "${SECRET_NAME}"; then
    echo "✅ New key deployed to GitHub successfully"
else
    echo "❌ Failed to deploy new key to GitHub"
    exit 1
fi

# Create rotation log
ROTATION_LOG="logs/ssh-key-rotations.log"
mkdir -p logs
echo "$(date -Iseconds) - SSH Key Rotation: OLD_KEY=${CURRENT_KEY%.pub}, NEW_KEY=${NEW_KEY_NAME}, STATUS=SUCCESS" >> "$ROTATION_LOG"

echo "✅ SSH key rotation completed successfully"
echo "New key: ${NEW_KEY_NAME}"
echo "Rotation log: ${ROTATION_LOG}"

# Cleanup old keys (older than 1 year)
echo "Cleaning up old SSH keys..."
find . -name "${PROJECT_PREFIX}-*.pub" -type f -mtime +365 -delete
find . -name "${PROJECT_PREFIX}-*" -type f -mtime +365 ! -name "*.pub" -delete

echo "✅ Rotation process completed"
```

#### Emergency Rotation Procedures
```bash
#!/bin/bash
# emergency-ssh-key-rotation.sh

set -euo pipefail

# Configuration
REPOSITORY="NT114DevSecOpsProject/NT114_DevSecOps_Project"
SECRET_NAME="BASTION_PUBLIC_KEY"
PROJECT_PREFIX="nt114-bastion-devsecops"

echo "🚨 EMERGENCY SSH KEY ROTATION INITIATED 🚨"
echo "Timestamp: $(date -Iseconds)"
echo "Reason: $1"

# Generate emergency key
EMERG_DATE=$(date +%y%m%d)
EMERG_KEY_NAME="${PROJECT_PREFIX}-${EMERG_DATE}-EMERGENCY"

echo "Generating emergency SSH key: ${EMERG_KEY_NAME}"
ssh-keygen -t ed25519 -a 100 -f "${EMERG_KEY_NAME}" -C "${PROJECT_PREFIX}@${EMERG_DATE}-EMERGENCY" -N ""

# Deploy immediately to GitHub
echo "Deploying emergency key to GitHub..."
gh secret set "${SECRET_NAME}" \
    --repo "${REPOSITORY}" \
    --body "$(cat "${EMERG_KEY_NAME}.pub")"

# Trigger infrastructure redeployment
echo "Triggering infrastructure redeployment..."
gh workflow run eks-terraform.yml \
    --field environment=dev \
    --field action=apply

# Log emergency rotation
EMERGENCY_LOG="logs/emergency-rotations.log"
mkdir -p logs
echo "$(date -Iseconds) - EMERGENCY ROTATION: KEY=${EMERG_KEY_NAME}, REASON=$1, TRIGGERED_BY=$(git config user.name)" >> "$EMERGENCY_LOG"

echo "🚨 EMERGENCY ROTATION COMPLETED 🚨"
echo "Emergency key: ${EMERG_KEY_NAME}"
echo "Infrastructure redeployment triggered"
echo "Emergency log: ${EMERGENCY_LOG}"

# Send notification (if configured)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 EMERGENCY SSH KEY ROTATION COMPLETED - Key: ${EMERG_KEY_NAME}, Reason: $1\"}" \
        "$SLACK_WEBHOOK_URL"
fi
```

### 4. SSH Key Audit and Monitoring

#### Monthly Audit Script
```bash
#!/bin/bash
# audit-ssh-keys.sh - Monthly SSH key audit

set -euo pipefail

echo "Starting SSH key audit..."
echo "Timestamp: $(date -Iseconds)"

# Check GitHub secret
echo "Checking GitHub secret..."
REPOSITORY="NT114DevSecOpsProject/NT114_DevSecOps_Project"
SECRET_NAME="BASTION_PUBLIC_KEY"

if gh secret list --repo "$REPOSITORY" | grep -q "$SECRET_NAME"; then
    echo "✅ GitHub secret exists: $SECRET_NAME"
else
    echo "❌ GitHub secret missing: $SECRET_NAME"
    exit 1
fi

# Check local keys
echo "Checking local SSH keys..."
PROJECT_PREFIX="nt114-bastion-devsecops"

for key_file in ${PROJECT_PREFIX}-*.pub; do
    if [ -f "$key_file" ]; then
        key_name=$(basename "$key_file" .pub)
        key_date=$(echo "$key_name" | awk -F'-' '{print $4}')

        echo "Key: $key_name"
        echo "Date: $key_date"
        echo "Fingerprint: $(ssh-keygen -lf "$key_file" | awk '{print $2}')"

        # Check key age (in days)
        key_epoch=$(date -d "${key_date:0:2}-${key_date:2:2}-${key_date:4:2}" +%s 2>/dev/null || echo "0")
        current_epoch=$(date +%s)
        age_days=$(( (current_epoch - key_epoch) / 86400 ))

        if [ $age_days -gt 90 ]; then
            echo "⚠️  Key is older than 90 days (rotation recommended)"
        elif [ $age_days -gt 365 ]; then
            echo "❌ Key is older than 365 days (rotation required)"
        else
            echo "✅ Key age is acceptable"
        fi
        echo ""
    fi
done

# Check AWS key pairs
echo "Checking AWS key pairs..."
aws_key_name=$(aws ec2 describe-key-pairs --filters "Name=key-name,Values=nt114-bastion-devsecops-*" --query "KeyPairs[0].KeyName" --output text 2>/dev/null || echo "None")

if [ "$aws_key_name" != "None" ] && [ "$aws_key_name" != "None" ]; then
    echo "✅ AWS key pair found: $aws_key_name"
else
    echo "❌ No matching AWS key pair found"
fi

# Generate audit report
AUDIT_REPORT="reports/ssh-key-audit-$(date +%Y%m%d).md"
mkdir -p reports

cat > "$AUDIT_REPORT" << EOF
# SSH Key Audit Report

**Date:** $(date -Iseconds)
**Auditor:** $(git config user.name || echo "Unknown")

## Summary

- GitHub Secret Status: $(gh secret list --repo "$REPOSITORY" | grep -q "$SECRET_NAME" && echo "✅ OK" || echo "❌ Missing")
- AWS Key Pair: $aws_key_name
- Local Keys: $(find . -name "${PROJECT_PREFIX}-*.pub" -type f | wc -l)

## Key Inventory

EOF

for key_file in ${PROJECT_PREFIX}-*.pub; do
    if [ -f "$key_file" ]; then
        key_name=$(basename "$key_file" .pub)
        key_date=$(echo "$key_name" | awk -F'-' '{print $4}')

        echo "### $key_name" >> "$AUDIT_REPORT"
        echo "- **Date:** $key_date" >> "$AUDIT_REPORT"
        echo "- **Fingerprint:** $(ssh-keygen -lf "$key_file" | awk '{print $2}')" >> "$AUDIT_REPORT"
        echo "- **Status:** $(ssh-keygen -lf "$key_file" > /dev/null 2>&1 && echo "✅ Valid" || echo "❌ Invalid")" >> "$AUDIT_REPORT"
        echo "" >> "$AUDIT_REPORT"
    fi
done

echo "✅ SSH key audit completed"
echo "Audit report: $AUDIT_REPORT"
```

---

## Security Standards

### 1. Code Security

#### Secure Coding Practices
```python
# Input validation and sanitization
from werkzeug.security import generate_password_hash, check_password_hash
import re

def validate_username(username: str) -> bool:
    """Validate username format and prevent injection."""
    if not username:
        return False

    # Allow only alphanumeric characters, underscores, and hyphens
    pattern = r'^[a-zA-Z0-9_-]{3,20}$'
    return bool(re.match(pattern, username))

def sanitize_input(user_input: str) -> str:
    """Sanitize user input to prevent XSS and injection."""
    if not user_input:
        return ""

    # Remove dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
    sanitized = user_input

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    return sanitized.strip()
```

#### Password Security
```python
import bcrypt
import secrets
import string

class PasswordManager:
    """Secure password management with bcrypt."""

    @staticmethod
    def generate_salt() -> bytes:
        """Generate cryptographically secure salt."""
        return bcrypt.gensalt()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with secure salt."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        salt = PasswordManager.generate_salt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def generate_secure_password(length: int = 12) -> str:
        """Generate cryptographically secure password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
```

#### API Security
```python
from functools import wraps
from flask import request, jsonify, g
import jwt
import time

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Implement rate limiting logic here
            # Use Redis or in-memory storage for tracking requests
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_auth(f):
    """JWT authentication decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token or not token.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401

        try:
            # Remove 'Bearer ' prefix
            token = token[7:]
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])

            # Check token expiration
            if payload['exp'] < time.time():
                return jsonify({'error': 'Token expired'}), 401

            g.user_id = payload['user_id']
            g.username = payload['username']

        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/v1/users', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth
def create_user():
    """Create user with authentication and rate limiting."""
    # Implementation here
    pass
```

### 2. Infrastructure Security

#### Terraform Security Standards
```hcl
# Enable encryption at rest
resource "aws_ebs_volume" "data" {
  availability_zone = "us-east-1a"
  size              = 20
  encrypted         = true  # Always enable encryption
  kms_key_id        = aws_kms_key.data.arn  # Use customer-managed keys

  tags = {
    Name = "data-volume"
  }
}

# Use least-privilege IAM roles
resource "aws_iam_role" "eks_node_role" {
  name = "${var.project_name}-eks-node-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-eks-node-role-${var.environment}"
  }
}

resource "aws_iam_role_policy_attachment" "eks_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_role.name
}

# Network security
resource "aws_security_group" "database" {
  name        = "${var.project_name}-database-sg-${var.environment}"
  description = "Security group for database access"
  vpc_id      = var.vpc_id

  # Allow access only from application security groups
  ingress {
    description     = "Allow database access from application"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-database-sg-${var.environment}"
  }
}
```

#### Kubernetes Security Standards
```yaml
# Security context for pods
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  containers:
  - name: app
    image: nt114/secure-app:v1.0.0
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /var/cache
    - name: logs
      mountPath: /var/log
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
  - name: logs
    emptyDir: {}
```

---

## Testing Standards

### 1. Unit Testing

#### Python Testing Standards
```python
# tests/test_user_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.models.user import User

class TestUserService:
    """Test cases for UserService class."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def user_service(self, mock_db):
        """UserService instance with mocked database."""
        return UserService(mock_db)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePassword123!'
        }

    def test_create_user_success(self, user_service, sample_user_data):
        """Test successful user creation."""
        # Arrange
        user_service._validate_user_data = Mock(return_value=True)
        user_service._user_to_dict = Mock(return_value={'id': 1, 'username': 'testuser'})

        # Act
        result = user_service.create_user(sample_user_data)

        # Assert
        assert result is not None
        assert result['username'] == 'testuser'

    def test_create_user_invalid_data(self, user_service, sample_user_data):
        """Test user creation with invalid data."""
        # Arrange
        user_service._validate_user_data = Mock(side_effect=ValueError("Invalid data"))

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid data"):
            user_service.create_user(sample_user_data)

    @patch('bcrypt.hashpw')
    def test_password_hashing(self, mock_hashpw, user_service, sample_user_data):
        """Test password hashing during user creation."""
        # Arrange
        mock_hashpw.return_value = b'hashed_password'
        user_service._validate_user_data = Mock(return_value=True)

        # Act
        user_service.create_user(sample_user_data)

        # Assert
        mock_hashpw.assert_called_once()
        call_args = mock_hashpw.call_args[0]
        assert call_args[0] == b'SecurePassword123!'

    def test_database_error_handling(self, user_service, sample_user_data):
        """Test database error handling during user creation."""
        # Arrange
        from sqlalchemy.exc import SQLAlchemyError
        user_service._validate_user_data = Mock(return_value=True)
        user_service.db.session.commit = Mock(side_effect=SQLAlchemyError("Database error"))

        # Act & Assert
        with pytest.raises(SQLAlchemyError):
            user_service.create_user(sample_user_data)

        # Verify rollback was called
        user_service.db.session.rollback.assert_called_once()
```

#### JavaScript Testing Standards
```javascript
// __tests__/services/exerciseService.test.js
import { exerciseService } from '../services/exerciseService';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios;

describe('ExerciseService', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Clear localStorage
    localStorage.clear();
  });

  describe('fetchExercises', () => {
    it('should fetch exercises successfully', async () => {
      // Arrange
      const mockResponse = {
        data: {
          exercises: [
            { id: 1, title: 'Exercise 1', difficulty: 'beginner' },
            { id: 2, title: 'Exercise 2', difficulty: 'intermediate' }
          ],
          pagination: { page: 1, total: 2 }
        }
      };

      mockedAxios.get.mockResolvedValue(mockResponse);

      // Act
      const result = await exerciseService.fetchExercises({ page: 1 });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/exercises', {
        params: { page: 1 }
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('should handle API errors gracefully', async () => {
      // Arrange
      const errorMessage = 'Network error';
      mockedAxios.get.mockRejectedValue(new Error(errorMessage));

      // Act & Assert
      await expect(exerciseService.fetchExercises()).rejects.toThrow(errorMessage);
    });

    it('should include auth token in requests', async () => {
      // Arrange
      const token = 'mock-jwt-token';
      localStorage.setItem('authToken', token);

      mockedAxios.get.mockResolvedValue({ data: { exercises: [] } });

      // Act
      await exerciseService.fetchExercises();

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/v1/exercises',
        expect.any(Object)
      );
    });
  });

  describe('submitSolution', () => {
    it('should submit solution successfully', async () => {
      // Arrange
      const exerciseId = '1';
      const solution = { code: 'console.log("Hello, World!");' };
      const mockResponse = {
        data: { id: 1, status: 'passed', score: 100 }
      };

      mockedAxios.post.mockResolvedValue(mockResponse);

      // Act
      const result = await exerciseService.submitSolution(exerciseId, solution);

      // Assert
      expect(mockedAxios.post).toHaveBeenCalledWith(
        `/api/v1/exercises/${exerciseId}/submit`,
        solution
      );
      expect(result).toEqual(mockResponse.data);
    });
  });
});
```

### 2. Integration Testing

#### API Integration Tests
```python
# tests/integration/test_user_api.py
import pytest
import requests
from tests.conftest import API_BASE_URL

class TestUserAPIIntegration:
    """Integration tests for User API endpoints."""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for API tests."""
        response = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json={
            'username': 'testuser',
            'password': 'TestPassword123!'
        })

        assert response.status_code == 200
        return response.json()['access_token']

    def test_create_user_integration(self):
        """Test user creation via API."""
        user_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'NewPassword123!'
        }

        response = requests.post(f"{API_BASE_URL}/api/v1/users", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data['username'] == 'newuser'
        assert data['email'] == 'newuser@example.com'
        assert 'password' not in data  # Password should not be returned

    def test_get_user_profile(self, auth_token):
        """Test getting user profile with authentication."""
        headers = {'Authorization': f'Bearer {auth_token}'}

        response = requests.get(f"{API_BASE_URL}/api/v1/users/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert 'username' in data
        assert 'email' in data

    def test_unauthorized_access(self):
        """Test API access without authentication."""
        response = requests.get(f"{API_BASE_URL}/api/v1/users/profile")

        assert response.status_code == 401
        assert 'error' in response.json()
```

### 3. Infrastructure Testing

#### Terraform Testing
```hcl
# terraform/modules/eks-cluster/tests/eks_cluster_test.tf
module "test_eks_cluster" {
  source = "../../"

  cluster_name    = "test-eks-cluster"
  cluster_version = "1.28"
  project_name    = "test-project"
  environment     = "test"
  vpc_id          = "vpc-12345678"
  subnet_ids      = ["subnet-12345678", "subnet-87654321"]

  tags = {
    Test = true
  }
}

# Validation tests
output "cluster_name_validation" {
  value = module.test_eks_cluster.cluster_name
}

output "cluster_endpoint" {
  value = module.test_eks_cluster.cluster_endpoint
}

output "node_group_name" {
  value = module.test_eks_cluster.node_group_name
}
```

---

## Documentation Standards

### 1. Code Documentation

#### Python Docstring Standards
```python
def calculate_exercise_score(submission_data: dict, test_cases: list) -> dict:
    """Calculate exercise score based on submission and test cases.

    This function evaluates a user's code submission against predefined
    test cases and provides a detailed score breakdown including
    execution time, memory usage, and test case results.

    Args:
        submission_data (dict): Dictionary containing user's code submission
            - code (str): The user's source code
            - language (str): Programming language used
            - user_id (int): ID of the submitting user
            - exercise_id (int): ID of the exercise

        test_cases (list): List of test case dictionaries
            - input (str): Test input data
            - expected_output (str): Expected output
            - timeout (int): Maximum execution time in seconds
            - memory_limit (int): Maximum memory usage in MB

    Returns:
        dict: Score calculation result
            - total_score (int): Overall score (0-100)
            - passed_tests (int): Number of test cases passed
            - total_tests (int): Total number of test cases
            - execution_time (float): Total execution time in seconds
            - memory_usage (float): Peak memory usage in MB
            - test_results (list): Detailed results for each test case
                - test_id (int): Test case identifier
                - passed (bool): Whether test case passed
                - output (str): Actual output from user's code
                - error (str, optional): Error message if test failed

    Raises:
        ValueError: If submission_data or test_cases are invalid
        TimeoutError: If code execution exceeds timeout
        MemoryError: If code exceeds memory limits

    Example:
        >>> submission = {
        ...     'code': 'print("Hello, World!")',
        ...     'language': 'python',
        ...     'user_id': 123,
        ...     'exercise_id': 456
        ... }
        >>> test_cases = [
        ...     {'input': '', 'expected_output': 'Hello, World!', 'timeout': 5, 'memory_limit': 128}
        ... ]
        >>> result = calculate_exercise_score(submission, test_cases)
        >>> print(result['total_score'])
        100
    """
```

#### JavaScript Documentation Standards
```javascript
/**
 * Service class for managing exercise-related API operations.
 *
 * This class provides methods for interacting with the exercise API
 * including fetching exercises, submitting solutions, and retrieving
 * exercise results.
 *
 * @class ExerciseService
 * @since 1.0.0
 * @author NT114 DevSecOps Team
 *
 * @example
 * // Create an instance of ExerciseService
 * const exerciseService = new ExerciseService();
 *
 * // Fetch exercises with filtering
 * const exercises = await exerciseService.fetchExercises({
 *   difficulty: 'beginner',
 *   category: 'algorithms',
 *   page: 1
 * });
 *
 * // Submit a solution
 * const result = await exerciseService.submitSolution('exercise-123', {
 *   code: 'console.log("Hello, World!");',
 *   language: 'javascript'
 * });
 */
class ExerciseService {
  /**
   * Fetches exercises from the API with optional filtering.
   *
   * @param {Object} [params={}] - Query parameters for filtering exercises
   * @param {string} [params.difficulty] - Filter by difficulty level ('beginner', 'intermediate', 'advanced')
   * @param {string} [params.category] - Filter by exercise category
   * @param {number} [params.page=1] - Page number for pagination
   * @param {number} [params.limit=20] - Number of exercises per page
   * @returns {Promise<Object>} Promise resolving to exercise data with pagination
   * @throws {Error} When API request fails or network error occurs
   *
   * @example
   * // Fetch beginner exercises
   * const beginnerExercises = await exerciseService.fetchExercises({
   *   difficulty: 'beginner',
   *   page: 1,
   *   limit: 10
   * });
   *
   * console.log(beginnerExercises.exercises);
   * // Output: [{ id: 1, title: 'Hello World', difficulty: 'beginner', ... }]
   */
  async fetchExercises(params = {}) {
    // Implementation details...
  }

  /**
   * Submits a solution for a specific exercise.
   *
   * @param {string} exerciseId - The ID of the exercise to submit solution for
   * @param {Object} solution - Solution submission data
   * @param {string} solution.code - The source code to be evaluated
   * @param {string} solution.language - Programming language of the code
   * @param {Object} [solution.metadata] - Additional metadata about the submission
   * @returns {Promise<Object>} Promise resolving to submission results
   * @throws {ValidationError} When solution data is invalid
   * @throws {AuthenticationError} When user is not authenticated
   * @throws {APIError} When submission fails on the server
   *
   * @example
   * // Submit a JavaScript solution
   * try {
   *   const result = await exerciseService.submitSolution('exercise-123', {
   *     code: 'function add(a, b) { return a + b; }',
   *     language: 'javascript',
   *     metadata: {
   *       timeComplexity: 'O(1)',
   *       spaceComplexity: 'O(1)'
   *     }
   *   });
   *
   *   console.log('Score:', result.score);
   *   console.log('Status:', result.status);
   * } catch (error) {
   *   console.error('Submission failed:', error.message);
   * }
   */
  async submitSolution(exerciseId, solution) {
    // Implementation details...
  }
}
```

### 2. Infrastructure Documentation

#### Terraform Module Documentation
```hcl
# terraform/modules/rds-postgresql/README.md
# RDS PostgreSQL Module

## Description

This module creates an AWS RDS PostgreSQL instance with enhanced security and performance configurations.

## Usage

```hcl
module "rds_postgresql" {
  source = "./modules/rds-postgresql"

  project_name  = "nt114"
  environment   = "dev"
  db_name       = "app_database"
  db_username   = "app_user"
  db_password   = var.rds_password
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.private_subnets

  tags = {
    Project = "NT114 DevSecOps"
    Environment = "Development"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | Name of the project | `string` | n/a | yes |
| environment | Environment name (dev, staging, prod) | `string` | n/a | yes |
| db_name | Name of the database | `string` | n/a | yes |
| db_username | Database master username | `string` | n/a | yes |
| db_password | Database master password | `string` | n/a | yes |
| vpc_id | VPC ID where RDS will be deployed | `string` | n/a | yes |
| subnet_ids | List of subnet IDs for RDS subnets | `list(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| db_instance_id | RDS instance ID |
| db_instance_arn | RDS instance ARN |
| db_instance_endpoint | RDS instance endpoint |
| db_instance_port | RDS instance port |
| db_subnet_group_name | DB subnet group name |

## Notes

- Always enable encryption at rest using KMS
- Use Enhanced Monitoring for better observability
- Implement proper backup and retention policies
- Configure appropriate security groups for network access
```

---

## CI/CD Pipeline Standards

### 1. Workflow Standards

#### GitHub Actions Workflow Template
```yaml
name: Standard CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'
        type: choice
        options: [dev, staging, prod]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'
  TERRAFORM_VERSION: '1.6.6'

jobs:
  code-quality:
    name: Code Quality Checks
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install Python dependencies
        run: |
          pip install -r requirements.txt
          pip install black flake8 pytest pytest-cov

      - name: Install Node.js dependencies
        run: |
          cd frontend
          npm ci

      - name: Python code formatting
        run: black --check microservices/

      - name: Python linting
        run: flake8 microservices/ --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: JavaScript linting
        run: |
          cd frontend
          npm run lint

      - name: Run Python tests
        run: |
          pytest microservices/ --cov=microservices --cov-report=xml

      - name: Run JavaScript tests
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  build-and-deploy:
    name: Build and Deploy
    needs: [code-quality, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event_name == 'workflow_dispatch'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Build and push Docker images
        run: |
          # Build and push service images
          for service in user-management exercises scores; do
            cd microservices/$service
            docker build -t nt114/$service:${{ github.sha }} .
            docker push nt114/$service:${{ github.sha }}
            cd - > /dev/null
          done

      - name: Deploy to EKS
        run: |
          # Install kubectl
          curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
          sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

          # Configure kubectl
          aws eks update-kubeconfig --region us-east-1 --name eks-1

          # Update deployment with new image
          kubectl set image deployment/user-management-service \
            user-management=nt114/user-management:${{ github.sha }} \
            -n ${{ inputs.environment || 'dev' }}

          # Wait for rollout
          kubectl rollout status deployment/user-management-service \
            -n ${{ inputs.environment || 'dev' }}
```

### 2. Quality Gates

#### Pre-deployment Checklist
```yaml
# .github/workflows/pre-deployment-checks.yml
name: Pre-deployment Validation

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  pre-deployment-checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Check code coverage
        run: |
          # Ensure minimum code coverage (e.g., 80%)
          coverage=$(pytest microservices/ --cov=microservices --cov-report=term-missing | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
          if (( $(echo "$coverage < 80" | bc -l) )); then
            echo "Code coverage ${coverage}% is below required 80%"
            exit 1
          fi

      - name: Security policy check
        run: |
          # Check for hardcoded secrets
          if grep -r "password\|secret\|key" --include="*.py" --include="*.js" --include="*.yaml" --exclude-dir=node_modules --exclude-dir=.git . | grep -v "example\|placeholder"; then
            echo "Potential hardcoded secrets found. Please review and remove."
            exit 1
          fi

      - name: Documentation check
        run: |
          # Ensure documentation is updated
          if [[ $(git diff --name-only origin/main docs/) -eq 0 ]]; then
            echo "Documentation not updated for this feature. Please update relevant documentation."
            exit 1
          fi

      - name: Performance test
        run: |
          # Run basic performance tests
          cd microservices/
          python -m pytest tests/performance/ -v || {
            echo "Performance tests failed. Please review and optimize."
            exit 1
          }
```

---

## Code Review Process

### 1. Pull Request Template

```markdown
## Description
Brief description of changes made in this pull request.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Infrastructure change

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance tests completed (if applicable)

## Security Checklist
- [ ] No hardcoded secrets or credentials
- [ ] Input validation implemented
- [ ] Error handling implemented
- [ ] Least privilege access followed
- [ ] Dependencies updated and scanned

## SSH Key Management (if applicable)
- [ ] New SSH keys generated with proper security (ED25519, 100 KDF rounds)
- [ ] Public key added to GitHub secrets (BASTION_PUBLIC_KEY)
- [ ] Private key stored securely
- [ ] Key rotation procedures documented
- [ ] Access control matrix updated

## Deployment Notes
- [ ] Infrastructure changes documented
- [ ] Environment variables updated
- [ ] Database migrations included (if applicable)
- [ ] Rollback plan documented

## Documentation
- [ ] Code documentation updated
- [ ] API documentation updated
- [ ] User documentation updated
- [ ] Architecture documentation updated

## Checklist
- [ ] My code follows the project's code standards
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
```

### 2. Review Guidelines

#### Code Review Checklist
```markdown
## Security Review
- [ ] No sensitive data in logs or error messages
- [ ] Proper authentication and authorization
- [ ] Input validation and sanitization
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Secure file handling
- [ ] Proper error handling without information disclosure

## Code Quality Review
- [ ] Code follows style guidelines (PEP 8, ESLint rules)
- [ ] Functions are small and focused on single responsibility
- [ ] Proper error handling and logging
- [ ] No hard-coded values (use environment variables)
- [ ] Proper resource cleanup and memory management
- [ ] Efficient algorithms and data structures
- [ ] Meaningful variable and function names
- [ ] Appropriate comments for complex logic

## Testing Review
- [ ] Unit tests cover edge cases
- [ ] Integration tests verify component interactions
- [ ] Test data is appropriate and isolated
- [ ] Test assertions are meaningful
- [ ] Tests are fast and reliable
- [ ] Security tests are included where applicable

## Infrastructure Review
- [ ] Terraform code follows best practices
- [ ] Kubernetes manifests are properly configured
- [ ] Security groups and IAM roles are least-privilege
- [ ] Resources have appropriate tags
- [ ] Scaling and performance considerations
- [ ] Backup and disaster recovery considerations
- [ ] Monitoring and logging configuration
```

---

## Conclusion

This comprehensive code standards document establishes the foundation for maintaining high-quality, secure, and maintainable code across the NT114 DevSecOps project. These standards should be:

1. **Followed consistently** by all team members
2. **Updated regularly** to reflect new best practices
3. **Enforced through** automated tools and code reviews
4. **Trained thoroughly** for new team members

Adherence to these standards ensures:
- **Code Quality**: Consistent, readable, and maintainable code
- **Security**: Secure coding practices throughout the application
- **Reliability**: Robust error handling and testing
- **Performance**: Optimized and efficient implementations
- **Maintainability**: Clear documentation and modular design

---

**Document Version**: 2.0
**Last Updated**: November 14, 2025
**Next Review**: December 14, 2025
**Enforcement**: Automated via CI/CD and manual code reviews

**Classification**: Internal - Team Use
**Distribution**: Development Team, DevOps Team