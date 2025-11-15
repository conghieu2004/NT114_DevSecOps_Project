# VPC Module
# Trigger EKS cluster deployment - 2025-01-07
module "vpc" {
  source = "../../modules/vpc"

  vpc_name           = var.vpc_name
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  private_subnets    = var.private_subnets
  public_subnets     = var.public_subnets

  enable_nat_gateway     = var.enable_nat_gateway
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = var.one_nat_gateway_per_az

  cluster_name = var.cluster_name

  tags = merge(
    var.tags,
    {
      Module = "vpc"
    }
  )
}

# EKS Cluster Module (initial creation without EBS CSI addon)
module "eks_cluster" {
  source = "../../modules/eks-cluster"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  bootstrap_self_managed_addons            = var.bootstrap_self_managed_addons
  cluster_support_type                     = var.cluster_support_type
  cluster_addons                           = var.cluster_addons
  cluster_endpoint_public_access           = var.cluster_endpoint_public_access
  cluster_endpoint_private_access          = var.cluster_endpoint_private_access
  enable_cluster_creator_admin_permissions = var.enable_cluster_creator_admin_permissions
  enable_irsa                              = var.enable_irsa

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  tags = merge(
    var.tags,
    {
      Module = "eks-cluster"
    }
  )

  depends_on = [module.vpc]
}

# EKS Node Group Module
module "eks_nodegroup" {
  source = "../../modules/eks-nodegroup"

  node_group_name      = var.node_group_name
  cluster_name         = module.eks_cluster.cluster_name
  cluster_version      = var.cluster_version
  cluster_service_cidr = "172.20.0.0/16"
  subnet_ids           = module.vpc.private_subnets

  min_size     = var.node_min_size
  max_size     = var.node_max_size
  desired_size = var.node_desired_size

  instance_types = var.node_instance_types
  capacity_type  = var.node_capacity_type

  labels = var.node_labels

  enable_coredns_addon        = var.enable_coredns_addon
  coredns_version             = var.coredns_version
  resolve_conflicts_on_create = var.resolve_conflicts_on_create
  resolve_conflicts_on_update = var.resolve_conflicts_on_update

  tags = merge(
    var.tags,
    {
      Module = "eks-nodegroup"
    }
  )

  depends_on = [module.eks_cluster]
}

# ALB Controller Module
module "alb_controller" {
  source = "../../modules/alb-controller"

  cluster_name  = module.eks_cluster.cluster_name
  aws_region    = var.aws_region
  oidc_provider = module.eks_cluster.oidc_provider
  node_group_id = module.eks_nodegroup.node_group_id

  enable_alb_controller     = var.enable_alb_controller
  enable_ebs_csi_controller = var.enable_ebs_csi_controller

  helm_release_name      = var.helm_release_name
  helm_namespace         = var.helm_namespace
  helm_chart_name        = var.helm_chart_name
  helm_chart_repository  = var.helm_chart_repository
  helm_chart_version     = var.helm_chart_version
  service_account_name   = var.service_account_name
  additional_helm_values = var.additional_helm_values
}

# EBS CSI Driver Addon (added after IAM role is created)
resource "aws_eks_addon" "ebs_csi_driver" {
  count = var.enable_ebs_csi_controller ? 1 : 0

  cluster_name             = module.eks_cluster.cluster_name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = var.ebs_csi_addon_version
  service_account_role_arn = module.alb_controller.ebs_csi_controller_role_arn

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    module.eks_nodegroup,
    module.alb_controller
  ]
}

# RDS PostgreSQL Module
module "rds_postgresql" {
  source = "../../modules/rds-postgresql"

  db_identifier  = var.rds_instance_identifier
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_encrypted     = false  # Disabled for demo

  db_name  = var.rds_initial_database
  username = var.rds_username
  password = var.rds_password
  port     = var.rds_port

  vpc_id                 = module.vpc.vpc_id
  private_subnet_ids     = module.vpc.private_subnets
  eks_security_group_ids = [module.eks_cluster.cluster_security_group_id]

  backup_retention_period = 0  # No backups for demo
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  skip_final_snapshot       = true  # Skip snapshot for demo
  final_snapshot_identifier = var.rds_final_snapshot_identifier
  deletion_protection       = false  # No deletion protection for demo

  monitoring_interval             = 0
  enabled_cloudwatch_logs_exports = []
  log_retention_days              = 1

  tags = merge(var.tags, {
    Name = var.rds_instance_identifier
  })

  depends_on = [
    module.vpc
  ]
}

# S3 Bucket for Migration Files - Simplified for demo
resource "aws_s3_bucket" "migration" {
  bucket = "${var.migration_bucket_name}-${random_id.bucket_suffix.hex}"

  tags = merge(var.tags, {
    Name = var.migration_bucket_name
  })
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Minimal S3 configuration for demo
resource "aws_s3_bucket_versioning" "migration" {
  bucket = aws_s3_bucket.migration.id
  versioning_configuration {
    status = "Disabled"  # Disabled for demo
  }
}

resource "aws_s3_bucket_public_access_block" "migration" {
  bucket = aws_s3_bucket.migration.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bastion Host Module - Simplified for demo
module "bastion_host" {
  source = "../../modules/bastion-host"

  instance_name = var.bastion_instance_name
  environment   = var.environment

  instance_type = var.bastion_instance_type
  ami_id        = var.bastion_ami_id

  key_name   = var.bastion_key_name
  public_key = var.bastion_public_key

  vpc_id            = module.vpc.vpc_id
  public_subnet_id  = module.vpc.public_subnets[0] # Use first public subnet
  allowed_ssh_cidrs = var.bastion_allowed_ssh_cidrs

  rds_security_group_ids = [module.rds_postgresql.security_group_id]

  db_host     = module.rds_postgresql.db_instance_endpoint
  db_port     = module.rds_postgresql.db_instance_port
  db_username = module.rds_postgresql.db_instance_username
  db_password = var.rds_password  # Use variable directly

  s3_bucket_name = aws_s3_bucket.migration.bucket

  root_volume_size = 8  # Smaller for demo
  allocate_eip     = true

  tags = merge(var.tags, {
    Name = var.bastion_instance_name
  })

  depends_on = [
    module.rds_postgresql,
    aws_s3_bucket.migration
  ]
}

# IAM Access Control Module
module "iam_access" {
  source = "../../modules/iam-access"

  cluster_name = module.eks_cluster.cluster_name

  create_admin_group        = var.create_admin_group
  admin_group_name          = var.admin_group_name
  create_admin_role         = var.create_admin_role
  admin_role_name           = var.admin_role_name
  attach_admin_policy       = var.attach_admin_policy
  create_assume_role_policy = var.create_assume_role_policy
  assume_role_policy_name   = var.assume_role_policy_name

  create_eks_access_entry  = var.create_eks_access_entry
  access_entry_type        = var.access_entry_type
  create_eks_access_policy = var.create_eks_access_policy
  eks_access_policy_arn    = var.eks_access_policy_arn
  access_scope_type        = var.access_scope_type
  access_scope_namespaces  = var.access_scope_namespaces

  tags = merge(
    var.tags,
    {
      Module = "iam-access"
    }
  )

  depends_on = [module.eks_cluster]
}

# ECR Module
module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name
  environment  = var.environment

  repository_names = [
    "api-gateway",
    "exercises-service",
    "scores-service",
    "user-management-service",
    "frontend"
  ]

  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  encryption_type      = "AES256"

  image_count_to_keep = 10
  untagged_image_days = 7

  create_github_actions_policy = true
  create_github_actions_user   = true

  tags = merge(
    var.tags,
    {
      Module = "ecr"
    }
  )
}
