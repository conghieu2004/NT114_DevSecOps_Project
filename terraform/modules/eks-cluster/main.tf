module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  bootstrap_self_managed_addons = var.bootstrap_self_managed_addons

  cluster_upgrade_policy = {
    support_type = var.cluster_support_type
  }

  cluster_addons = var.cluster_addons

  cluster_endpoint_public_access           = var.cluster_endpoint_public_access
  cluster_endpoint_private_access          = var.cluster_endpoint_private_access
  enable_cluster_creator_admin_permissions = var.enable_cluster_creator_admin_permissions
  enable_irsa                              = var.enable_irsa

  # Explicitly set the cluster service IPv4 CIDR
  cluster_service_ipv4_cidr = "172.20.0.0/16"

  # Disable custom KMS key creation (use AWS managed key instead - FREE)
  create_kms_key            = false
  cluster_encryption_config = {}

  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  control_plane_subnet_ids = var.control_plane_subnet_ids

  tags = var.tags
}
