module "eks_managed_node_group" {
  source  = "terraform-aws-modules/eks/aws//modules/eks-managed-node-group"
  version = "~> 20.0"

  name                  = var.node_group_name
  cluster_name          = var.cluster_name
  cluster_version       = var.cluster_version
  cluster_service_cidr  = var.cluster_service_cidr
  subnet_ids            = var.subnet_ids

  min_size     = var.min_size
  max_size     = var.max_size
  desired_size = var.desired_size

  instance_types = var.instance_types
  capacity_type  = var.capacity_type

  labels = var.labels

  # IAM role configuration
  create_iam_role = true
  iam_role_name   = "${var.node_group_name}-role"
  iam_role_additional_policies = {
    AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }

  # Enable launch template
  use_custom_launch_template = false

  tags = var.tags
}

# CoreDNS addon
resource "aws_eks_addon" "coredns" {
  count = var.enable_coredns_addon ? 1 : 0

  depends_on   = [module.eks_managed_node_group]
  cluster_name = var.cluster_name
  addon_name   = "coredns"

  addon_version = var.coredns_version

  resolve_conflicts_on_create = var.resolve_conflicts_on_create
  resolve_conflicts_on_update = var.resolve_conflicts_on_update

  tags = var.tags
}
