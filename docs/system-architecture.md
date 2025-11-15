# NT114 DevSecOps System Architecture

**Version:** 2.0
**Last Updated:** November 14, 2025
**Architecture Status:** ✅ Production Ready

---

## Executive Overview

The NT114 DevSecOps system architecture implements a modern cloud-native microservices pattern on AWS EKS with comprehensive security practices. The architecture emphasizes scalability, reliability, and security through proper separation of concerns, automated deployments, and robust access controls.

---

## High-Level Architecture

### Cloud Infrastructure Overview

```mermaid
graph TB
    subgraph "Internet"
        USERS[End Users]
        DEVS[Developers]
    end

    subgraph "AWS Cloud - US-East-1"
        subgraph "VPC (10.0.0.0/16)"
            subgraph "Public Subnets (10.0.1.0/24, 10.0.2.0/24)"
                ALB[Application Load Balancer<br/>t3.medium]
                BASTION[Bastion Host<br/>t3.small<br/>SSH: 22]
                NAT[NAT Gateway<br/>Internet Egress]
            end

            subgraph "Private Subnets (10.0.11.0/24, 10.0.12.0/24)"
                subgraph "EKS Cluster"
                    subgraph "Kubernetes Pods"
                        UM[User Management<br/>Flask Service<br/>Port: 5001]
                        ES[Exercises Service<br/>Flask Service<br/>Port: 5002]
                        SS[Scores Service<br/>Flask Service<br/>Port: 5003]
                        FE[Frontend<br/>React Application<br/>Port: 3000]
                    end
                end

                subgraph "Database Layer"
                    RDS[(RDS PostgreSQL 15<br/>db.t3.micro<br/>Multi-DB Instance)]
                end

                subgraph "Storage Layer"
                    EBS[EBS Volumes<br/>gp3-encrypted]
                    S3[S3 Bucket<br/>Static Assets]
                end
            end
        end
    end

    USERS --> ALB
    ALB --> FE
    ALB --> UM
    ALB --> ES
    ALB --> SS

    DEVS --> BASTION
    BASTION --> RDS

    UM --> RDS
    ES --> RDS
    SS --> RDS

    EKS --> EBS
    FE --> S3
```

### Network Architecture

```mermaid
graph LR
    subgraph "Network Layers"
        INTERNET[Internet]
        IGW[Internet Gateway]

        subgraph "Public Tier"
            ALB_SG[ALB Security Group<br/>Port: 80, 443]
            BASTION_SG[Bastion Security Group<br/>Port: 22<br/>Limited IPs]
        end

        subgraph "Private Tier"
            EKS_SG[EKS Security Group<br/>App Ports: 5001-5003]
            RDS_SG[RDS Security Group<br/>Port: 5432]
        end

        NAT[NAT Gateway]
    end

    INTERNET --> IGW
    IGW --> ALB_SG
    IGW --> BASTION_SG
    ALB_SG --> EKS_SG
    BASTION_SG --> RDS_SG
    EKS_SG --> NAT
```

---

## Component Architecture

### 1. Kubernetes (EKS) Architecture

#### Cluster Configuration
- **Cluster Name**: `eks-1`
- **Kubernetes Version**: 1.28
- **Node Groups**: Managed node groups with auto-scaling
- **Networking**: AWS VPC CNI with Calico for network policies

#### Pod Architecture

```mermaid
graph TB
    subgraph "EKS Cluster Namespace: dev"
        subgraph "Frontend Tier"
            FE_POD[Frontend Pod<br/>React:3000<br/>Replicas: 2]
            FE_SVC[frontend-service<br/>LoadBalancer<br/>Port: 80]
        end

        subgraph "API Gateway Tier"
            GW_POD[API Gateway Pod<br/>Nginx:80<br/>Replicas: 2]
            GW_SVC[api-gateway-service<br/>LoadBalancer<br/>Port: 80]
        end

        subgraph "Service Tier"
            UM_POD[User Management Pod<br/>Flask:5001<br/>Replicas: 3]
            ES_POD[Exercises Pod<br/>Flask:5002<br/>Replicas: 3]
            SS_POD[Scores Pod<br/>Flask:5003<br/>Replicas: 3]

            UM_SVC[user-management-service<br/>ClusterIP<br/>Port: 5001]
            ES_SVC[exercises-service<br/>ClusterIP<br/>Port: 5002]
            SS_SVC[scores-service<br/>ClusterIP<br/>Port: 5003]
        end

        subgraph "Data Tier"
            PG_POD[PostgreSQL Pod<br/>PostgreSQL:15<br/>Replicas: 1]
            PG_SVC[postgres-service<br/>ClusterIP<br/>Port: 5432]

            AUTH_DB[auth-db-service<br/>ClusterIP<br/>Port: 5433]
            EX_DB[exercises-db-service<br/>ClusterIP<br/>Port: 5434]
            SCORE_DB[scores-db-service<br/>ClusterIP<br/>Port: 5435]
        end
    end

    FE_POD --> FE_SVC
    GW_POD --> GW_SVC
    GW_POD --> UM_SVC
    GW_POD --> ES_SVC
    GW_POD --> SS_SVC
    UM_POD --> UM_SVC
    ES_POD --> ES_SVC
    SS_POD --> SS_SVC
    UM_POD --> AUTH_DB
    ES_POD --> EX_DB
    SS_POD --> SCORE_DB
    PG_POD --> PG_SVC
```

### 2. Microservices Architecture

#### Service Communication Pattern

```mermaid
sequenceDiagram
    participant User as End User
    participant Gateway as API Gateway
    participant Auth as User Management
    participant Exercises as Exercises Service
    participant Scores as Scores Service
    participant DB as PostgreSQL

    User->>Gateway: HTTP Request
    Gateway->>Gateway: Authentication Check

    alt Auth Required
        Gateway->>Auth: Validate Token
        Auth-->>Gateway: User Info
    end

    alt Get Exercises
        Gateway->>Exercises: Fetch Exercises
        Exercises->>DB: Query Exercises
        DB-->>Exercises: Exercise Data
        Exercises-->>Gateway: Exercises List
    end

    alt Submit Score
        Gateway->>Scores: Submit Attempt
        Scores->>DB: Store Score
        DB-->>Scores: Confirmation
        Scores-->>Gateway: Score Result
    end

    Gateway-->>User: HTTP Response
```

#### Service Dependencies

```mermaid
graph TB
    subgraph "External Services"
        GITHUB[GitHub Actions<br/>CI/CD Pipeline]
        AWS[AWS Services<br/>EKS, RDS, S3]
    end

    subgraph "Application Layer"
        FRONTEND[Frontend<br/>React Application]
        GATEWAY[API Gateway<br/>Nginx/Flask]

        subgraph "Microservices"
            USER_MGMT[User Management<br/>Authentication]
            EXERCISES[Exercises<br/>Content Management]
            SCORES[Scores<br/>Performance Tracking]
        end
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Multi-Database)]
        REDIS[(Redis<br/>Caching)]
        STORAGE[(S3<br/>Static Assets)]
    end

    GITHUB --> GATEWAY
    GITHUB --> USER_MGMT
    GITHUB --> EXERCISES
    GITHUB --> SCORES

    FRONTEND --> GATEWAY
    GATEWAY --> USER_MGMT
    GATEWAY --> EXERCISES
    GATEWAY --> SCORES

    USER_MGMT --> POSTGRES
    EXERCISES --> POSTGRES
    SCORES --> POSTGRES

    EXERCISES --> REDIS
    FRONTEND --> STORAGE

    USER_MGMT --> AWS
    EXERCISES --> AWS
    SCORES --> AWS
```

### 3. Database Architecture

#### Current Database Structure

```mermaid
erDiagram
    USER_MGMT_DB ||--o{ USERS : contains
    EXERCISES_DB ||--o{ EXERCISES : contains
    SCORES_DB ||--o{ SCORES : contains
    SCORES_DB ||--o{ USER_EXERCISES : tracks

    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        timestamp created_at
        timestamp updated_at
        boolean is_active
    }

    EXERCISES {
        int id PK
        string title
        text description
        text difficulty_level
        json test_cases
        json solutions
        string category
        timestamp created_at
        timestamp updated_at
        boolean is_active
    }

    SCORES {
        int id PK
        int user_id FK
        int exercise_id FK
        int attempt_number
        json submission_data
        string result_status
        int score_points
        float execution_time_ms
        timestamp submitted_at
        text feedback_message
    }

    USER_EXERCISES {
        int user_id FK
        int exercise_id FK
        timestamp first_attempt
        timestamp last_attempt
        int total_attempts
        int best_score
        string best_status
    }
```

#### Planned RDS Migration Architecture

```mermaid
graph TB
    subgraph "Database Migration Path"
        subgraph "Current Architecture"
            LOCAL_PG[(Local PostgreSQL<br/>3 Separate Containers)]
            DOCKER[Docker Compose]
        end

        subgraph "Migration Process"
            BASTION_MIGRATION[Bastion Host<br/>Migration Scripts]
            SSH_TUNNEL[SSH Tunnel<br/>Secure Transfer]
            DUMP_RESTORE[pg_dump/pg_restore<br/>Data Transfer]
        end

        subgraph "Target Architecture"
            RDS[(AWS RDS PostgreSQL 15<br/>Single Instance, 3 Databases)]
            IRSA[IRSA Role<br/>EKS Pod Access]
            SECURITY_GROUP[RDS Security Group<br/>Private Access Only]
        end
    end

    LOCAL_PG --> DUMP_RESTORE
    DOCKER --> DUMP_RESTORE
    DUMP_RESTORE --> SSH_TUNNEL
    SSH_TUNNEL --> BASTION_MIGRATION
    BASTION_MIGRATION --> RDS

    EKS_PODS[EKS Pods] --> IRSA
    IRSA --> SECURITY_GROUP
    SECURITY_GROUP --> RDS
```

---

## Security Architecture

### 1. SSH Key Management System

#### Current SSH Infrastructure

```mermaid
graph TB
    subgraph "SSH Key Management"
        subgraph "Key Generation"
            LOCAL_KEY[Local Key Generation<br/>ssh-keygen ed25519]
            KEY_SPEC[Key Specifications<br/>100 KDF rounds]
        end

        subgraph "Distribution"
            GITHUB_SECRET[GitHub Secret<br/>BASTION_PUBLIC_KEY]
            TERRAFORM_VAR[Terraform Variable<br/>bastion_public_key]
        end

        subgraph "Infrastructure Integration"
            BASTION_EC2[EC2 Bastion Host<br/>Authorized Keys]
            AWS_KEY_PAIR[AWS Key Pair<br/>ssh-ed25519]
        end

        subgraph "Access Control"
            PRIVATE_KEY[Private Key Storage<br/>Password Manager]
            TEAM_ACCESS[Team Authorization<br/>Role-Based Access]
        end
    end

    LOCAL_KEY --> GITHUB_SECRET
    KEY_SPEC --> TERRAFORM_VAR
    GITHUB_SECRET --> BASTION_EC2
    TERRAFORM_VAR --> AWS_KEY_PAIR
    PRIVATE_KEY --> TEAM_ACCESS
```

#### SSH Key Rotation Procedures

```mermaid
stateDiagram-v2
    [*] --> KeyGeneration: Quarterly Schedule
    KeyGeneration --> Testing: New Key Created
    Testing --> GitHubUpdate: Validation Complete
    GitHubUpdate --> Deployment: Secret Updated
    Deployment --> Verification: Infrastructure Applied
    Verification --> KeyRotationComplete: Access Confirmed
    KeyRotationComplete --> [*]: Documentation Updated

    KeyGeneration --> EmergencyGeneration: Compromise Detected
    EmergencyGeneration --> EmergencyDeployment: Immediate Key
    EmergencyDeployment --> EmergencyVerification: Critical Update
    EmergencyVerification --> [*]: Incident Report
```

### 2. Network Security Architecture

#### VPC Security Design

```mermaid
graph TB
    subgraph "VPC Security Layers"
        subgraph "Layer 1: Network ACLs"
            NACL_IN[Inbound Rules<br/>Stateless Filtering]
            NACL_OUT[Outbound Rules<br/>Stateless Filtering]
        end

        subgraph "Layer 2: Security Groups"
            ALB_SG[ALB SG<br/>HTTP/HTTPS from 0.0.0.0/0]
            BASTION_SG[Bastion SG<br/>SSH from Corporate IPs]
            EKS_SG[EKS SG<br/>From ALB only]
            RDS_SG[RDS SG<br/>From EKS & Bastion]
        end

        subgraph "Layer 3: IAM Roles"
            EKS_ROLE[EKS Node Role<br/>EC2, EBS, EKS permissions]
            POD_ROLE[Pod IRSA Roles<br/>Service-specific permissions]
            BASTION_ROLE[Bastion Role<br/>SSM, RDS access]
        end

        subgraph "Layer 4: Encryption"
            EBS_ENCRYPTION[EBS Encryption<br/>AWS Managed KMS]
            RDS_ENCRYPTION[RDS Encryption<br/>AWS Managed KMS]
            TRANSIT_ENCRYPTION[Transit Encryption<br/>TLS 1.3]
        end
    end

    NACL_IN --> ALB_SG
    ALB_SG --> EKS_SG
    BASTION_SG --> RDS_SG
    EKS_SG --> EKS_ROLE
    RDS_SG --> POD_ROLE
    BASTION_SG --> BASTION_ROLE
    EBS_ENCRYPTION --> TRANSIT_ENCRYPTION
    RDS_ENCRYPTION --> TRANSIT_ENCRYPTION
```

### 3. Identity and Access Management

#### IAM Architecture

```mermaid
graph TB
    subgraph "IAM Architecture"
        subgraph "GitHub Actions Access"
            GITHUB_USER[GitHub Actions User<br/>nt114-devsecops-github-actions]
            GITHUB_POLICY[GitHub Actions Policy<br/>EKS, EC2, ECR permissions]
        end

        subgraph "EKS Service Accounts"
            EKS_SA[EKS Service Accounts<br/>IRSA Integration]
            POD_POLICIES[Pod IAM Policies<br/>Least Privilege]
        end

        subgraph "Resource Roles"
            EKS_NODE_ROLE[EKS Node Role<br/>EC2, EBS, S3]
            RDS_ROLE[RDS Access Role<br/>Database permissions]
            BASTION_ROLE_SERVER[Bastion Role<br/>SSM, Systems Manager]
        end

        subgraph "Audit and Monitoring"
            CLOUDTRAIL[CloudTrail<br/>API Audit Logging]
            ACCESS_ANALYZER[IAM Access Analyzer<br/>Resource Access Analysis]
        end
    end

    GITHUB_USER --> GITHUB_POLICY
    GITHUB_POLICY --> EKS_SA
    EKS_SA --> POD_POLICIES
    POD_POLICIES --> EKS_NODE_ROLE
    EKS_NODE_ROLE --> RDS_ROLE
    RDS_ROLE --> BASTION_ROLE_SERVER
    BASTION_ROLE_SERVER --> CLOUDTRAIL
    CLOUDTRAIL --> ACCESS_ANALYZER
```

---

## CI/CD Pipeline Architecture

### 1. GitHub Actions Workflow Architecture

```mermaid
graph TB
    subgraph "GitHub Actions Workflows"
        subgraph "Infrastructure Pipeline"
            EKS_TERRAFORM[eks-terraform.yml<br/>EKS Cluster Deployment]
            TERRAFORM_PLAN[Terraform Plan<br/>Infrastructure Validation]
            TERRAFORM_APPLY[Terraform Apply<br/>Resource Creation]
        end

        subgraph "Application Pipeline"
            DEPLOY_EKS[deploy-to-eks.yml<br/>Application Deployment]
            DOCKER_BUILD[Docker Build<br/>Container Images]
            K8S_DEPLOY[Kubernetes Deploy<br/>Service Updates]
        end

        subgraph "Quality Gates"
            SECURITY_SCAN[Security Scans<br/>Vulnerability Detection]
            UNIT_TESTS[Unit Tests<br/>Code Validation]
            INFRA_VALIDATE[Infrastructure Validation<br/>EBS CSI, PostgreSQL]
        end
    end

    EKS_TERRAFORM --> TERRAFORM_PLAN
    TERRAFORM_PLAN --> TERRAFORM_APPLY
    TERRAFORM_APPLY --> DEPLOY_EKS
    DEPLOY_EKS --> DOCKER_BUILD
    DOCKER_BUILD --> K8S_DEPLOY

    TERRAFORM_PLAN --> SECURITY_SCAN
    DOCKER_BUILD --> UNIT_TESTS
    K8S_DEPLOY --> INFRA_VALIDATE
```

### 2. GitOps Architecture

```mermaid
graph TB
    subgraph "GitOps Flow"
        subgraph "Source Control"
            MAIN_BRANCH[Main Branch<br/>Production Code]
            FEATURE_BRANCHES[Feature Branches<br/>Development Code]
        end

        subgraph "CI/CD Automation"
            GITHUB_ACTIONS[GitHub Actions<br/>Build & Test]
            ARGOCD[ArgoCD<br/>Continuous Deployment]
            HELM[Helm Charts<br/>Application Configuration]
        end

        subgraph "Runtime Environment"
            EKS_CLUSTER[EKS Cluster<br/>Running Applications]
            K8S_MANIFESTS[Kubernetes Manifests<br/>Desired State]
        end
    end

    MAIN_BRANCH --> GITHUB_ACTIONS
    FEATURE_BRANCHES --> GITHUB_ACTIONS
    GITHUB_ACTIONS --> ARGOCD
    ARGOCD --> HELM
    HELM --> K8S_MANIFESTS
    K8S_MANIFESTS --> EKS_CLUSTER
```

---

## Monitoring and Observability Architecture

### 1. CloudWatch Integration

```mermaid
graph TB
    subgraph "Monitoring Stack"
        subgraph "Application Metrics"
            APP_METRICS[Application Performance<br/>Response Time, Error Rate]
            BUSINESS_METRICS[Business Metrics<br/>User Activity, Exercise Completion]
            CUSTOM_METRICS[Custom Metrics<br/>Service-Specific KPIs]
        end

        subgraph "Infrastructure Metrics"
            EKS_METRICS[EKS Metrics<br/>Pod/Node Health, Resource Usage]
            RDS_METRICS[RDS Metrics<br/>Database Performance, Connections]
            ALB_METRICS[ALB Metrics<br/>Request Count, Latency]
        end

        subgraph "Log Management"
            APP_LOGS[Application Logs<br/>Structured JSON Logs]
            INFRA_LOGS[Infrastructure Logs<br/>Kubernetes, AWS Events]
            AUDIT_LOGS[Audit Logs<br/>Security Events, API Calls]
        end

        subgraph "Alerting"
            CLOUDWATCH_ALARMS[CloudWatch Alarms<br/>Threshold-Based Alerts]
            SNS_NOTIFICATIONS[SNS Notifications<br/>Email, Slack Integration]
            DASHBOARD[CloudWatch Dashboard<br/>Visualization & Analytics]
        end
    end

    APP_METRICS --> CLOUDWATCH_ALARMS
    BUSINESS_METRICS --> DASHBOARD
    INFRA_METRICS --> SNS_NOTIFICATIONS
    APP_LOGS --> DASHBOARD
    AUDIT_LOGS --> CLOUDWATCH_ALARMS
    CLOUDWATCH_ALARMS --> SNS_NOTIFICATIONS
```

### 2. Health Check Architecture

```mermaid
graph TB
    subgraph "Health Check System"
        subgraph "Application Health"
            LIVENESS_PROBES[Liveness Probes<br/>Container Health]
            READINESS_PROBES[Readiness Probes<br/>Service Availability]
            STARTUP_PROBES[Startup Probes<br/>Initialization Status]
        end

        subgraph "Infrastructure Health"
            NODE_HEALTH[Node Health<br/>EC2 Instance Status]
            POD_HEALTH[Pod Health<br/>Kubernetes Pod Status]
            VOLUME_HEALTH[Volume Health<br/>EBS Volume Status]
        end

        subgraph "Dependency Health"
            DB_HEALTH[Database Health<br/>PostgreSQL Connectivity]
            CACHE_HEALTH[Cache Health<br/>Redis Connectivity]
            EXTERNAL_HEALTH[External Service Health<br/>Third-Party APIs]
        end

        subgraph "Monitoring Integration"
            HEALTH_ENDPOINTS[Health Endpoints<br/>/health, /ready]
            STATUS_PAGES[Status Pages<br/>System Overview]
            ALERT_ROUTING[Alert Routing<br/>PagerDuty, Slack]
        end
    end

    LIVENESS_PROBES --> HEALTH_ENDPOINTS
    READINESS_PROBES --> HEALTH_ENDPOINTS
    NODE_HEALTH --> STATUS_PAGES
    DB_HEALTH --> ALERT_ROUTING
    POD_HEALTH --> HEALTH_ENDPOINTS
    VOLUME_HEALTH --> STATUS_PAGES
```

---

## Disaster Recovery and High Availability

### 1. High Availability Design

```mermaid
graph TB
    subgraph "Availability Zones"
        AZ1[AZ: us-east-1a<br/>Primary Zone]
        AZ2[AZ: us-east-1b<br/>Secondary Zone]
        AZ3[AZ: us-east-1c<br/>Tertiary Zone]
    end

    subgraph "EKS High Availability"
        CONTROL_PLANE[EKS Control Plane<br/>Multi-AZ Managed]
        NODE_GROUPS[Managed Node Groups<br/>Cross-AZ Distribution]
        AUTO_SCALING[Auto Scaling Groups<br/>Automatic Recovery]
    end

    subgraph "Data Persistence"
        RDS_MULTI_AZ[RDS Multi-AZ<br/>Automatic Failover]
        EBS_REPLICATION[EBS Replication<br/>Within AZ]
        S3_BACKUPS[S3 Backups<br/>Cross-Region Replication]
    end

    subgraph "Load Distribution"
        ALB_NLB[Application Load Balancer<br/>Multi-AZ Targets]
            DNS_FAILOVER[Route 53 Failover<br/>Health Checks]
        end
    end

    CONTROL_PLANE --> AZ1
    CONTROL_PLANE --> AZ2
    CONTROL_PLANE --> AZ3
    NODE_GROUPS --> AUTO_SCALING
    AUTO_SCALING --> RDS_MULTI_AZ
    RDS_MULTI_AZ --> EBS_REPLICATION
    EBS_REPLICATION --> S3_BACKUPS
    S3_BACKUPS --> ALB_NLB
    ALB_NLB --> DNS_FAILOVER
```

### 2. Backup and Recovery Strategy

```mermaid
graph TB
    subgraph "Backup Strategy"
        subgraph "Automated Backups"
            RDS_BACKUPS[RDS Automated Backups<br/>7-Day Retention]
            EBS_SNAPSHOTS[EBS Snapshots<br/>Daily Backups]
            S3_VERSIONING[S3 Versioning<br/>Object History]
        end

        subgraph "Application Backups"
            DB_EXPORTS[Database Exports<br/>pg_dump Automation]
            CONFIG_BACKUPS[Configuration Backups<br/>K8s Manifests]
            STATE_BACKUPS[Terraform State<br/>Remote State Backup]
        end

        subgraph "Recovery Procedures"
            RDS_RESTORE[RDS Point-in-Time Restore<br/>1-Second Recovery]
            VOLUME_RESTORE[EBS Volume Restore<br/>From Snapshots]
            CLUSTER_REBUILD[EKS Cluster Rebuild<br/>Infrastructure as Code]
        end
    end

    RDS_BACKUPS --> RDS_RESTORE
    EBS_SNAPSHOTS --> VOLUME_RESTORE
    DB_EXPORTS --> RDS_RESTORE
    CONFIG_BACKUPS --> CLUSTER_REBUILD
    STATE_BACKUPS --> CLUSTER_REBUILD
```

---

## Performance and Scaling Architecture

### 1. Auto Scaling Design

```mermaid
graph TB
    subgraph "Auto Scaling Components"
        subgraph "Horizontal Pod Autoscaler"
            HPA_METRICS[CPU/Memory Metrics<br/>Resource Utilization]
            HPA_CUSTOM[Custom Metrics<br/>Application-Specific]
            POD_SCALING[Pod Scaling<br/>2-10 Replicas]
        end

        subgraph "Cluster Autoscaler"
            NODE_METRICS[Node Metrics<br/>Pod Pressure]
            INSTANCE_TYPES[Instance Types<br/>Optimized Selection]
            NODE_SCALING[Node Scaling<br/>Group Management]
        end

        subgraph "Application Scaling"
            CONNECTION_POOLING[Connection Pooling<br/>Database Efficiency]
            CACHING_STRATEGY[Caching Strategy<br/>Redis Integration]
            CDN_DISTRIBUTION[CDN Distribution<br/>Static Assets]
        end
    end

    HPA_METRICS --> POD_SCALING
    HPA_CUSTOM --> POD_SCALING
    POD_SCALING --> NODE_METRICS
    NODE_METRICS --> NODE_SCALING
    INSTANCE_TYPES --> NODE_SCALING
    POD_SCALING --> CONNECTION_POOLING
    CONNECTION_POOLING --> CACHING_STRATEGY
    CACHING_STRATEGY --> CDN_DISTRIBUTION
```

### 2. Performance Optimization Architecture

```mermaid
graph TB
    subgraph "Performance Layers"
        subgraph "Frontend Optimization"
            STATIC_ASSETS[Static Assets<br/>CDN Caching]
            BUNDLE_OPTIMIZATION[Bundle Optimization<br/>Code Splitting]
            LAZY_LOADING[Lazy Loading<br/>Progressive Enhancement]
        end

        subgraph "API Optimization"
            RESPONSE_CACHING[Response Caching<br/>API Gateway Cache]
            RATE_LIMITING[Rate Limiting<br/>DDoS Protection]
            COMPRESSION[Compression<br/>Gzip/Brotli]
        end

        subgraph "Database Optimization"
            QUERY_OPTIMIZATION[Query Optimization<br/>Index Strategy]
            CONNECTION_POOLING_DB[Connection Pooling<br/>PgBouncer]
            READ_REPLICAS[Read Replicas<br/>Load Distribution]
        end

        subgraph "Infrastructure Optimization"
            INSTANCE_TYPES_OPT[Instance Types<br/>Right-Sizing]
            STORAGE_OPTIMIZATION[Storage Optimization<br/>gp3/IO2]
            NETWORK_OPTIMIZATION[Network Optimization<br/>Enhanced Networking]
        end
    end

    STATIC_ASSETS --> RESPONSE_CACHING
    BUNDLE_OPTIMIZATION --> RATE_LIMITING
    LAZY_LOADING --> COMPRESSION
    RESPONSE_CACHING --> QUERY_OPTIMIZATION
    RATE_LIMITING --> CONNECTION_POOLING_DB
    COMPRESSION --> READ_REPLICAS
    QUERY_OPTIMIZATION --> INSTANCE_TYPES_OPT
    CONNECTION_POOLING_DB --> STORAGE_OPTIMIZATION
    READ_REPLICAS --> NETWORK_OPTIMIZATION
```

---

## Technology Stack Summary

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Container Runtime** | Docker | Latest | Containerization |
| **Orchestration** | Kubernetes (EKS) | 1.28 | Container orchestration |
| **Infrastructure** | Terraform | Latest | IaC management |
| **CI/CD** | GitHub Actions | Latest | Automation pipeline |
| **Load Balancer** | AWS ALB | Latest | Traffic distribution |
| **Database** | PostgreSQL | 15.7 | Primary data store |
| **Frontend** | React | Latest | User interface |
| **Backend** | Python Flask | Latest | API services |
| **Monitoring** | CloudWatch | Latest | Observability |
| **Security** | IAM/KMS | Latest | Access control |

### Security Tools

| Tool | Purpose | Implementation |
|------|---------|----------------|
| **SSH Key Management** | Bastion host access | ED25519 keys with rotation |
| **IAM Roles** | Service permissions | IRSA for EKS pods |
| **Security Groups** | Network security | Layer 4 filtering |
| **KMS** | Encryption | Data at rest |
| **TLS** | Transit encryption | End-to-end encryption |
| **Network ACLs** | Network security | Stateless filtering |

---

## Architecture Decision Records (ADRs)

### ADR-001: Microservices Architecture
**Status**: Implemented ✅
**Decision**: Adopt microservices architecture with separate services for user management, exercises, and scores.
**Rationale**: Better scalability, independent deployment, and technology flexibility.

### ADR-002: EKS over ECS
**Status**: Implemented ✅
**Decision**: Use Amazon EKS for container orchestration instead of ECS.
**Rationale**: Kubernetes ecosystem, better community support, and advanced networking capabilities.

### ADR-003: GitHub Actions CI/CD
**Status**: Implemented ✅
**Decision**: Use GitHub Actions for CI/CD pipeline instead of Jenkins or other tools.
**Rationale**: Native GitHub integration, better YAML configuration, and managed service.

### ADR-004: SSH Key Bastion Access
**Status**: Implemented ✅
**Decision**: Implement SSH key-based access through bastion host for database management.
**Rationale**: Enhanced security, audit trail, and centralized access control.

### ADR-005: RDS Migration Strategy
**Status**: Planned 📋
**Decision**: Migrate from local PostgreSQL to AWS RDS with zero-downtime approach.
**Rationale**: Managed service, better reliability, and automated backups.

---

## Future Architecture Enhancements

### Planned Improvements

#### 1. Enhanced Security (Q1 2026)
- **OIDC Authentication**: Replace static AWS credentials with GitHub OIDC
- **Secrets Manager**: Integrate AWS Secrets Manager for application secrets
- **Advanced Monitoring**: Implement security monitoring and threat detection

#### 2. Performance Optimizations (Q2 2026)
- **Read Replicas**: Implement RDS read replicas for query performance
- **CDN Integration**: Deploy CloudFront for global content delivery
- **Database Optimization**: Advanced PostgreSQL tuning and indexing

#### 3. Multi-Environment Support (Q3 2026)
- **Staging Environment**: Full staging environment for production testing
- **Environment Promotion**: Automated environment promotion workflows
- **Configuration Management**: Advanced configuration management strategies

---

## Conclusion

The NT114 DevSecOps system architecture represents a modern, secure, and scalable cloud-native implementation. The current architecture successfully demonstrates:

- **Operational Excellence**: Automated CI/CD pipeline with comprehensive error handling
- **Security**: Defense-in-depth approach with SSH key management and network isolation
- **Reliability**: High availability design with proper backup and disaster recovery
- **Performance**: Scalable architecture with auto-scaling capabilities
- **Cost Optimization**: Right-sized resources with efficient resource utilization

The architecture is production-ready with a clear roadmap for future enhancements and optimizations.

---

**Document Version**: 2.0
**Last Updated**: November 14, 2025
**Next Review**: December 14, 2025
**Architecture Status**: ✅ Production Ready