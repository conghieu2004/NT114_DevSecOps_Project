# RDS PostgreSQL Instance
resource "aws_db_instance" "postgresql" {
  identifier = var.db_identifier

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = var.storage_encrypted

  db_name  = var.db_name
  username = var.username
  password = random_password.db_password.result

  port = var.port

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.rds.name

  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window

  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.final_snapshot_identifier

  deletion_protection = var.deletion_protection

  # Performance monitoring
  monitoring_interval = var.monitoring_interval
  monitoring_role_arn = var.monitoring_interval > 0 ? aws_iam_role.rds_enhanced_monitoring[0].arn : null

  # CloudWatch logs
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports

  tags = merge(
    var.tags,
    {
      Name = var.db_identifier
    }
  )

  depends_on = [aws_security_group.rds]
}

# Random password for RDS
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# KMS key for encryption (if needed)
resource "aws_kms_key" "rds" {
  count               = var.create_kms_key ? 1 : 0
  description         = "KMS key for RDS encryption"
  enable_key_rotation = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableIAMUserPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.db_identifier}-kms"
    }
  )
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name        = "${var.db_identifier}-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  # PostgreSQL access from EKS
  ingress {
    description     = "PostgreSQL from EKS"
    from_port       = var.port
    to_port         = var.port
    protocol        = "tcp"
    security_groups = var.eks_security_group_ids
  }

  # PostgreSQL access from Bastion Host
  ingress {
    description     = "PostgreSQL from Bastion Host"
    from_port       = var.port
    to_port         = var.port
    protocol        = "tcp"
    security_groups = var.bastion_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.db_identifier}-sg"
    }
  )
}

# RDS Subnet Group
resource "aws_db_subnet_group" "rds" {
  name       = "${var.db_identifier}-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(
    var.tags,
    {
      Name = "${var.db_identifier}-subnet-group"
    }
  )
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_enhanced_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "${var.db_identifier}-enhanced-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.db_identifier}-enhanced-monitoring"
    }
  )
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  count      = var.monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.rds_enhanced_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "postgresql" {
  count             = length(var.enabled_cloudwatch_logs_exports) > 0 ? 1 : 0
  name              = "/aws/rds/instance/${var.db_identifier}/postgresql"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}