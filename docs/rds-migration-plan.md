# PostgreSQL to AWS RDS Migration Implementation Plan

**Date:** 2025-11-13
**Target Environment:** Dev
**Migration Type:** Zero-downtime with bastion host

## Executive Summary

This plan outlines the migration from local PostgreSQL databases (3 separate containers) to a single AWS RDS PostgreSQL 15 instance with 3 databases. The migration uses a bastion host for secure access and follows AWS security best practices with IRSA for EKS integration.

## Current Architecture Analysis

### Current Setup
- **3 separate PostgreSQL 15 databases** running in Docker containers:
  - `user_management_db` (auth_db) - port 5433
  - `exercises_db` - port 5434
  - `scores_db` - port 5435
- **Microservices Architecture:**
  - User Management Service (Flask) - handles authentication and user data
  - Exercises Service (Flask) - stores programming exercises with JSON fields
  - Scores Service (Flask) - tracks user exercise attempts and results
- **Database Schema:**
  - User Management: Auth database with user accounts and passwords
  - Exercises: Exercises table with JSON fields for test_cases and solutions
  - Scores: Scores table linking users to exercises with attempt data

### Current Infrastructure
- Docker Compose local deployment
- Direct database connections via localhost
- No automated backup or replication
- Development credentials (postgres/postgres)

## Target Architecture Design

### RDS Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                        VPC                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   Public Subnets                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│  │  │   ALB       │  │  Bastion    │  │   NAT       │     │ │
│  │  │ (Ingress)   │  │   Host      │  │  Gateway    │     │ │
│  │  │  t3.medium  │  │  t3.small   │  │             │     │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Private Subnets                        │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │                   EKS Cluster                       │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │ │ │
│  │  │  │ User Mgmt   │  │  Exercises  │  │   Scores    │ │ │ │
│  │  │  │  Service    │  │  Service    │  │  Service    │ │ │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │                    RDS Instance                     │ │ │
│  │  │           PostgreSQL 15 (db.t3.micro)              │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │ │ │
│  │  │  │ auth_db     │  │exercises_db │  │ scores_db   │ │ │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### RDS Instance Configuration
- **Instance Type:** `db.t3.micro` (Free tier eligible)
- **Engine:** PostgreSQL 15.7
- **Storage:** 20 GB General Purpose SSD (gp2)
- **Multi-AZ:** No (dev environment cost optimization)
- **Backup Retention:** 7 days
- **Maintenance Window:** Sunday 3:00-4:00 UTC
- **Enhanced Monitoring:** Enabled (5-second granularity)

### Security Configuration

#### Network Security
- **VPC:** Existing EKS VPC with private subnets
- **Subnet Group:** Private subnets for RDS
- **Security Groups:**
  - RDS SG: Allow traffic from EKS node security group (5432)
  - Bastion SG: Allow SSH from specific IP ranges, RDS access (5432)
  - EKS SG: Allow egress to RDS (5432)

#### IAM Configuration
- **IRSA IAM Role:** `rds-access-role` for EKS pods
- **IAM Policy:** Limited RDS access (connect, read/write specific databases)
- **Bastion IAM Role:** `bastion-host-role` with SSM access

### Cost Analysis

#### Monthly Costs (US-East-1)
- **RDS Instance (db.t3.micro):** ~$13.50/month
- **Storage (20GB gp2):** ~$1.80/month
- **Backup Storage:** ~$0.50/month
- **Data Transfer:** Minimal (<$5/month)
- **Bastion Host (t3.small):** ~$15.00/month
- **Total Estimated:** ~$36/month

## Migration Strategy

### Phase 1: Infrastructure Setup (Day 0-1)

#### 1.1 Create RDS Terraform Module
```terraform
# terraform/modules/rds-postgresql/main.tf
resource "aws_db_instance" "postgres" {
  identifier = "${var.project_name}-${var.environment}-postgres"

  engine         = "postgres"
  engine_version = "15.7"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true

  db_name  = "postgres"
  username = var.db_username
  password = var.db_password

  port = 5432

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:03:00-sun:04:00"

  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final-snapshot"

  deletion_protection = false

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-postgres"
  })
}
```

#### 1.2 Create Bastion Host Module
```terraform
# terraform/modules/bastion-host/main.tf
resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = "t3.small"
  subnet_id              = var.public_subnet_id
  vpc_security_group_ids = [aws_security_group.bastion.id]
  iam_instance_profile   = aws_iam_instance_profile.bastion.name

  associate_public_ip_address = true

  user_data = base64encode(templatefile("${path.module}/bastion-setup.sh", {
    rds_endpoint = var.rds_endpoint
  }))

  tags = merge(var.tags, {
    Name = "${var.project_name}-bastion-${var.environment}"
  })
}
```

#### 1.3 Security Group Configuration
```terraform
# terraform/modules/rds-postgresql/security.tf
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id      = var.vpc_id

  # Allow connections from EKS pods
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
  }

  # Allow connections from bastion host
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### Phase 2: Migration Workflow Setup (Day 1-2)

#### 2.1 Create Migration CI Workflow
```yaml
# .github/workflows/rds-migration.yml
name: RDS Migration Workflow

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Migration action'
        required: true
        type: choice
        options: [dry-run, migrate, validate]
      environment:
        description: 'Target environment'
        required: true
        default: 'dev'

jobs:
  migration:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup migration tools
        run: |
          sudo apt-get update
          sudo apt-get install -y postgresql-client postgresql-contrib
          pip install pgdump2aws

      - name: Deploy RDS infrastructure
        run: |
          cd terraform/environments/${{ inputs.environment }}
          terraform init
          terraform apply -auto-approve -target=module.rds_postgresql
          terraform output -json > rds_outputs.json

      - name: Extract RDS connection details
        run: |
          echo "RDS_ENDPOINT=$(jq -r '.rds_endpoint.value' rds_outputs.json)" >> $GITHUB_ENV
          echo "RDS_PASSWORD=$(aws secretsmanager get-secret-value --secret-id rds-password-${{ inputs.environment }} --query SecretString --output text)" >> $GITHUB_ENV

      - name: Migration dry run
        if: inputs.action == 'dry-run'
        run: ./scripts/migration-dry-run.sh

      - name: Execute data migration
        if: inputs.action == 'migrate'
        run: ./scripts/execute-migration.sh

      - name: Validate migration
        if: inputs.action == 'validate'
        run: ./scripts/validate-migration.sh
```

#### 2.2 Migration Script Development
```bash
#!/bin/bash
# scripts/execute-migration.sh
set -euo pipefail

# Environment variables
RDS_ENDPOINT=${RDS_ENDPOINT}
RDS_PASSWORD=${RDS_PASSWORD}
BASTION_IP=${BASTION_IP}

# Local databases
LOCAL_DBS=(
  "user_management_db:5433:postgres:postgres:auth_db"
  "exercises_db:5434:exercises_user:exercises_password:exercises_db"
  "scores_db:5435:scores_user:scores_password:scores_db"
)

echo "Starting migration to RDS: $RDS_ENDPOINT"

# Create bastion SSH tunnel
echo "Creating SSH tunnel to RDS via bastion..."
ssh -f -N -L 5432:$RDS_ENDPOINT:5432 ec2-user@$BASTION_IP -i bastion-key.pem

# Wait for tunnel to be ready
sleep 5

# Migrate each database
for db_config in "${LOCAL_DBS[@]}"; do
  IFS=':' read -r local_name local_port local_user local_pass target_db <<< "$db_config"

  echo "Migrating $local_name to $target_db..."

  # Create target database if not exists
  PGPASSWORD=$RDS_PASSWORD psql -h localhost -U postgres -p 5432 -c "CREATE DATABASE $target_db;" || echo "Database $target_db already exists"

  # Dump and restore data
  PGPASSWORD=$local_pass pg_dump -h localhost -U $local_user -p $local_port $local_name | \
  PGPASSWORD=$RDS_PASSWORD psql -h localhost -U postgres -p 5432 $target_db

  echo "Migration of $local_name completed"
done

# Clean up SSH tunnel
pkill -f "ssh.*$RDS_ENDPOINT"

echo "Migration completed successfully"
```

### Phase 3: Data Migration Execution (Day 3)

#### 3.1 Migration Timeline
- **T-1 Hour:** Backup local databases
- **T-30 Min:** Deploy RDS infrastructure
- **T-15 Min:** Test bastion host connectivity
- **T-5 Min:** Put services in maintenance mode
- **T-0:** Execute migration
- **T+15 Min:** Update application configurations
- **T+30 Min:** Validate migration
- **T+45 Min:** Switch traffic to RDS
- **T+60 Min:** Monitor and validate

#### 3.2 Migration Commands
```bash
# Pre-migration backup
docker exec user_management_postgres_db pg_dump -U postgres user_management_db > backup/auth_db_backup.sql
docker exec exercises_postgres pg_dump -U exercises_user exercises_db > backup/exercises_db_backup.sql
docker exec scores_postgres pg_dump -U scores_user scores_db > backup/scores_db_backup.sql

# Migration execution
./scripts/execute-migration.sh

# Post-migration validation
./scripts/validate-migration.sh
```

### Phase 4: Application Configuration Updates

#### 4.1 Kubernetes ConfigMaps
```yaml
# k8s/configmaps/postgres-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
data:
  RDS_ENDPOINT: "nt114-dev-postgres.cluster-xxxxx.us-east-1.rds.amazonaws.com"
  RDS_PORT: "5432"
  USER_MANAGEMENT_DB: "auth_db"
  EXERCISES_DB: "exercises_db"
  SCORES_DB: "scores_db"
```

#### 4.2 Kubernetes Secrets
```yaml
# k8s/secrets/postgres-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secrets
type: Opaque
data:
  DB_USERNAME: cG9zdGdyZXM=  # postgres (base64)
  DB_PASSWORD: <base64-encoded-password>
```

#### 4.3 Service Account with IRSA
```yaml
# k8s/serviceaccounts/postgres-sa.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: postgres-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/rds-access-role
```

#### 4.4 Updated Helm Values
```yaml
# helm/user-management-service/values.yaml
env:
  - name: DB_HOST
    valueFrom:
      configMapKeyRef:
        name: postgres-config
        key: RDS_ENDPOINT
  - name: DB_PORT
    valueFrom:
      configMapKeyRef:
        name: postgres-config
        key: RDS_PORT
  - name: DB_NAME
    valueFrom:
      configMapKeyRef:
        name: postgres-config
        key: USER_MANAGEMENT_DB
  - name: DB_USER
    valueFrom:
      secretKeyRef:
        name: postgres-secrets
        key: DB_USERNAME
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: postgres-secrets
        key: DB_PASSWORD

serviceAccountName: postgres-sa
```

## Security Implementation

### 5.1 IAM Role for IRSA
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds-db:connect"
      ],
      "Resource": [
        "arn:aws:rds-db:us-east-1:ACCOUNT:dbuser:*/postgres"
      ]
    }
  ]
}
```

### 5.2 RDS Enhanced Monitoring
- Enable CloudWatch detailed monitoring
- Set up CloudWatch alarms for:
  - CPU utilization > 80%
  - Memory utilization > 85%
  - Database connections > 80% of max
  - Storage > 85% utilized
  - Read/write latency spikes

### 5.3 Network Security
- Private subnets only for RDS
- No public IP addresses
- Security group least-privilege access
- VPC flow logs enabled
- Bastion host access limited to corporate IP ranges

## Testing and Validation

### 6.1 Migration Testing Strategy

#### Pre-Migration Tests
```bash
# Test schema compatibility
docker exec exercises_postgres pg_dump -s exercises_db | psql -h $RDS_ENDPOINT -U postgres -d exercises_db

# Test data volume
docker exec user_management_postgres_db psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('user_management_db'))"

# Test connection from EKS pods
kubectl run pg-test --image=postgres:15 --rm -i --tty --restart=Never -- psql -h $RDS_ENDPOINT -U postgres -c "SELECT version()"
```

#### Post-Migration Validation
```bash
#!/bin/bash
# scripts/validate-migration.sh

# Row count validation
validate_row_counts() {
  local db=$1
  local table=$2
  local expected=$3

  actual=$(PGPASSWORD=$RDS_PASSWORD psql -h $RDS_ENDPOINT -U postgres -d $db -t -c "SELECT COUNT(*) FROM $table")

  if [ "$actual" -eq "$expected" ]; then
    echo "✅ Row count validation passed for $db.$table: $actual rows"
  else
    echo "❌ Row count validation failed for $db.$table: expected $expected, got $actual"
    exit 1
  fi
}

# Check data integrity
validate_data_integrity() {
  echo "Validating data integrity..."

  # Check exercises structure
  PGPASSWORD=$RDS_PASSWORD psql -h $RDS_ENDPOINT -U postgres -d exercises_db -c "SELECT COUNT(*) FROM exercises WHERE test_cases IS NULL OR solutions IS NULL" | grep -q "^0$" || {
    echo "❌ Data integrity check failed: NULL test_cases or solutions found"
    exit 1
  }

  # Check user-score relationships
  PGPASSWORD=$RDS_PASSWORD psql -h $RDS_ENDPOINT -U postgres -d scores_db -c "SELECT COUNT(*) FROM scores WHERE user_id NOT IN (SELECT id FROM auth_db.users)" | grep -q "^0$" || {
    echo "❌ Data integrity check failed: Orphaned score records found"
    exit 1
  }

  echo "✅ Data integrity validation passed"
}

# Performance validation
validate_performance() {
  echo "Validating query performance..."

  # Test query response times
  response_time=$(PGPASSWORD=$RDS_PASSWORD psql -h $RDS_ENDPOINT -U postgres -d exercises_db -t -c "SELECT COUNT(*) FROM exercises" | time -p cat 2>&1 | grep "^real" | awk '{print $2}')

  if (( $(echo "$response_time < 1.0" | bc -l) )); then
    echo "✅ Query performance validation passed: ${response_time}s"
  else
    echo "❌ Query performance validation failed: ${response_time}s (threshold: 1.0s)"
    exit 1
  fi
}

# Run all validations
validate_row_counts "exercises_db" "exercises" $(docker exec exercises_postgres psql -U exercises_user -d exercises_db -t -c "SELECT COUNT(*) FROM exercises")
validate_row_counts "scores_db" "scores" $(docker exec scores_postgres psql -U scores_user -d scores_db -t -c "SELECT COUNT(*) FROM scores")
validate_row_counts "auth_db" "users" $(docker exec user_management_postgres_db psql -U postgres -d user_management_db -t -c "SELECT COUNT(*) FROM users")

validate_data_integrity
validate_performance

echo "🎉 All migration validations passed successfully!"
```

### 6.2 Application Testing

#### Smoke Tests
```python
# tests/test_rds_migration.py
import pytest
import psycopg2
from app.config import Config

class TestRDSMigration:
    def test_user_service_connectivity(self):
        """Test user management service can connect to RDS"""
        conn = psycopg2.connect(
            host=Config.RDS_ENDPOINT,
            database=Config.USER_MANAGEMENT_DB,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            assert count > 0, "Users table should have data"

        conn.close()

    def test_exercises_service_data_integrity(self):
        """Test exercises service data integrity"""
        conn = psycopg2.connect(
            host=Config.RDS_ENDPOINT,
            database=Config.EXERCISES_DB,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM exercises WHERE test_cases IS NOT NULL")
            valid_exercises = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM exercises")
            total_exercises = cur.fetchone()[0]

            assert valid_exercises == total_exercises, "All exercises should have test cases"

        conn.close()

    def test_scores_service_relationships(self):
        """Test scores service maintains relationships"""
        conn = psycopg2.connect(
            host=Config.RDS_ENDPOINT,
            database=Config.SCORES_DB,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )

        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM scores s
                LEFT JOIN auth_db.users u ON s.user_id = u.id
                WHERE u.id IS NULL
            """)
            orphaned_scores = cur.fetchone()[0]

            assert orphaned_scores == 0, "No orphaned scores should exist"

        conn.close()
```

## Rollback Procedures

### 7.1 Immediate Rollback (< 1 hour)
```bash
#!/bin/bash
# scripts/rollback-immediate.sh

echo "Executing immediate rollback..."

# Stop services
kubectl scale deployment --replicas=0 user-management-service
kubectl scale deployment --replicas=0 exercises-service
kubectl scale deployment --replicas=0 scores-service

# Restore local databases
docker-compose up -d user-management-db exercises-db scores-db

# Restore from backups
docker exec -i user_management_postgres_db psql -U postgres < backup/auth_db_backup.sql
docker exec -i exercises_postgres psql -U exercises_user < backup/exercises_db_backup.sql
docker exec -i scores_postgres psql -U scores_user < backup/scores_db_backup.sql

# Update configs back to localhost
kubectl patch configmap postgres-config --type merge -p '{"data":{"RDS_ENDPOINT":"localhost"}}'

# Restart services
kubectl scale deployment --replicas=1 user-management-service
kubectl scale deployment --replicas=1 exercises-service
kubectl scale deployment --replicas=1 scores-service

echo "Immediate rollback completed"
```

### 7.2 Full Rollback (< 4 hours)
```bash
#!/bin/bash
# scripts/rollback-full.sh

echo "Executing full rollback to local PostgreSQL..."

# Step 1: Stop all traffic to services
kubectl apply -f k8s/maintenance-mode.yaml

# Step 2: Deploy local database infrastructure
cd ../local-setup
docker-compose up -d

# Step 3: Wait for databases to be ready
./wait-for-databases.sh

# Step 4: Restore latest backups
echo "Restoring database backups..."
docker exec -i user_management_postgres_db psql -U postgres user_management_db < backup/latest/auth_db_backup.sql
docker exec -i exercises_postgres psql -U exercises_user exercises_db < backup/latest/exercises_db_backup.sql
docker exec -i scores_postgres psql -U scores_user scores_db < backup/latest/scores_db_backup.sql

# Step 5: Update application configurations
helm upgrade user-management-service ./helm/user-management-service --set postgres.host=localhost
helm upgrade exercises-service ./helm/exercises-service --set postgres.host=localhost
helm upgrade scores-service ./helm/scores-service --set postgres.host=localhost

# Step 6: Verify local setup
./verify-local-setup.sh

# Step 7: Restore service access
kubectl delete -f k8s/maintenance-mode.yaml

echo "Full rollback completed successfully"
```

## Monitoring and Maintenance

### 8.1 CloudWatch Dashboards
Create custom CloudWatch dashboard with metrics:
- Database connections
- CPU/Memory utilization
- Storage utilization
- Read/Write IOPS
- Network throughput
- Query latency

### 8.2 Alert Configuration
```yaml
# cloudwatch/alarms.yml
Resources:
  HighCPUAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "${ProjectName}-RDS-High-CPU"
      AlarmDescription: "RDS CPU utilization above 80%"
      MetricName: CPUUtilization
      Namespace: AWS/RDS
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn

  StorageAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub "${ProjectName}-RDS-Storage-High"
      AlarmDescription: "RDS storage utilization above 85%"
      MetricName: FreeStorageSpace
      Namespace: AWS/RDS
      Statistic: Average
      Period: 300
      EvaluationPeriods: 1
      Threshold: 3  # GB (assuming 20GB total)
      ComparisonOperator: LessThanThreshold
      AlarmActions:
        - !Ref SNSTopicArn
```

### 8.3 Backup Strategy
- **Automated Backups:** 7-day retention
- **Manual Snapshots:** Weekly, tagged with date
- **Cross-region Backup:** Monthly snapshot to us-west-2
- **Export to S3:** Daily logical backups for 30 days

## Risk Mitigation

### 9.1 Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss during migration | Low | High | Pre-migration backups, dry-run testing |
| Performance degradation | Medium | Medium | Performance testing, monitoring |
| Connection failures | Medium | High | Redundant bastion, retry logic |
| Security vulnerabilities | Low | High | Security groups, IAM least privilege |

### 9.2 Business Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Downtime exceeds window | Medium | High | Rollback procedures, maintenance windows |
| Cost overruns | Low | Medium | Cost monitoring, right-sizing |
| Team readiness | Low | High | Documentation, training sessions |

## Success Criteria

### 10.1 Technical Success
- [ ] All 3 databases migrated successfully to RDS
- [ ] Zero data loss (row count validation)
- [ ] Application connectivity verified
- [ ] Performance within 10% of baseline
- [ ] Security groups properly configured
- [ ] Backup and monitoring operational

### 10.2 Operational Success
- [ ] Migration completed within 2-hour window
- [ ] Rollback procedures tested and documented
- [ ] Team trained on RDS operations
- [ ] Cost estimates validated (<$50/month)
- [ ] Monitoring alerts configured and tested

## Post-Migration Tasks

### 11.1 Week 1
- Monitor performance and errors closely
- Optimize slow queries identified in monitoring
- Document lessons learned and update runbooks
- Validate backup/restore procedures

### 11.2 Week 2-4
- Optimize RDS instance size based on actual usage
- Implement read replicas if needed for performance
- Set up automated scaling for EKS based on database load
- Conduct post-migration security audit

### 11.3 Ongoing
- Monthly cost optimization review
- Quarterly performance tuning
- Annual disaster recovery testing
- Regular security group audits

## Appendix

### A. Migration Checklist
- [ ] Backup all local databases
- [ ] Test bastion host connectivity
- [ ] Validate RDS security groups
- [ ] Prepare migration scripts
- [ ] Schedule maintenance window
- [ ] Prepare rollback procedures
- [ ] Test monitoring alerts
- [ ] Document credentials securely

### B. Contact Information
- **Migration Lead:** [Name], [Email], [Phone]
- **Database Administrator:** [Name], [Email], [Phone]
- **DevOps Engineer:** [Name], [Email], [Phone]
- **Application Owner:** [Name], [Email], [Phone]
- **Emergency Contact:** [Name], [Email], [Phone]

### C. Environment Variables
```bash
# Required environment variables for migration
export RDS_ENDPOINT=""
export RDS_PASSWORD=""
export BASTION_IP=""
export BASTION_KEY_PATH=""
export LOCAL_BACKUP_PATH=""
export AWS_REGION="us-east-1"
export PROJECT_NAME="nt114"
export ENVIRONMENT="dev"
```

### D. Resource Links
- [AWS RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [AWS Database Migration Service Guide](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_GettingStarted.html)
- [EKS IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [PostgreSQL Migration Best Practices](https://www.postgresql.org/docs/current/migration.html)