# General Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "nt114-devsecops"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Terraform   = "true"
    Project     = "NT114_DevSecOps"
  }
}

# VPC Variables
variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "eks-vpc1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "11.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnets" {
  description = "List of private subnet CIDR blocks"
  type        = list(string)
  default     = ["11.0.1.0/24", "11.0.2.0/24", "11.0.3.0/24"]
}

variable "public_subnets" {
  description = "List of public subnet CIDR blocks"
  type        = list(string)
  default     = ["11.0.101.0/24", "11.0.102.0/24", "11.0.103.0/24"]
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway for all private subnets"
  type        = bool
  default     = true
}

variable "one_nat_gateway_per_az" {
  description = "Create one NAT Gateway per availability zone"
  type        = bool
  default     = false
}

# EKS Cluster Variables
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "eks-1"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "bootstrap_self_managed_addons" {
  description = "Bootstrap self-managed addons"
  type        = bool
  default     = true
}

variable "cluster_support_type" {
  description = "Cluster support type (STANDARD or EXTENDED)"
  type        = string
  default     = "STANDARD"
}

variable "cluster_addons" {
  description = "Map of cluster addon configurations"
  type        = any
  default = {
    eks-pod-identity-agent = {}
    kube-proxy             = {}
    vpc-cni                = {}
  }
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to cluster endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_private_access" {
  description = "Enable private access to cluster endpoint"
  type        = bool
  default     = true
}

variable "enable_cluster_creator_admin_permissions" {
  description = "Enable cluster creator admin permissions"
  type        = bool
  default     = true
}

variable "enable_irsa" {
  description = "Enable IAM Roles for Service Accounts"
  type        = bool
  default     = true
}

# Node Group Variables
variable "node_group_name" {
  description = "Name of the EKS managed node group"
  type        = string
  default     = "eks-node"
}

variable "node_instance_types" {
  description = "List of instance types for the node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "node_capacity_type" {
  description = "Capacity type for node group (ON_DEMAND or SPOT)"
  type        = string
  default     = "SPOT"
}

variable "node_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 2
}

variable "node_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 1
}

variable "node_labels" {
  description = "Key-value map of Kubernetes labels for nodes"
  type        = map(string)
  default = {
    Environment = "dev"
    GithubRepo  = "terraform-aws-eks"
    GithubOrg   = "terraform-aws-modules"
  }
}

variable "enable_coredns_addon" {
  description = "Enable CoreDNS addon"
  type        = bool
  default     = true
}

variable "coredns_version" {
  description = "Version of CoreDNS addon (leave null for latest)"
  type        = string
  default     = null
}

variable "resolve_conflicts_on_create" {
  description = "How to resolve conflicts on create"
  type        = string
  default     = "OVERWRITE"
}

variable "resolve_conflicts_on_update" {
  description = "How to resolve conflicts on update"
  type        = string
  default     = "OVERWRITE"
}

# ALB Controller Variables
variable "enable_alb_controller" {
  description = "Enable AWS Load Balancer Controller (set to false for first apply, then true)"
  type        = bool
  default     = true
}

variable "enable_ebs_csi_controller" {
  description = "Enable EBS CSI Controller IAM role"
  type        = bool
  default     = true
}

variable "ebs_csi_addon_version" {
  description = "Version of the EBS CSI driver addon (leave null for latest)"
  type        = string
  default     = "v1.36.0-eksbuild.1"
}

variable "helm_release_name" {
  description = "Name of the Helm release"
  type        = string
  default     = "aws-load-balancer-controller"
}

variable "helm_namespace" {
  description = "Kubernetes namespace for the Helm release"
  type        = string
  default     = "kube-system"
}

variable "helm_chart_name" {
  description = "Name of the Helm chart"
  type        = string
  default     = "aws-load-balancer-controller"
}

variable "helm_chart_repository" {
  description = "Helm chart repository URL"
  type        = string
  default     = "https://aws.github.io/eks-charts"
}

variable "helm_chart_version" {
  description = "Version of the Helm chart (leave null for latest)"
  type        = string
  default     = null
}

variable "service_account_name" {
  description = "Name of the Kubernetes service account"
  type        = string
  default     = "aws-load-balancer-controller"
}

variable "additional_helm_values" {
  description = "Additional Helm values to set"
  type        = map(string)
  default     = {}
}

# IAM Access Control Variables
variable "create_admin_group" {
  description = "Whether to create the admin IAM group"
  type        = bool
  default     = true
}

variable "admin_group_name" {
  description = "Name of the admin IAM group"
  type        = string
  default     = "eks-admin-group"
}

variable "create_admin_role" {
  description = "Whether to create the admin IAM role"
  type        = bool
  default     = true
}

variable "admin_role_name" {
  description = "Name of the admin IAM role"
  type        = string
  default     = "eks-admin-role"
}

variable "attach_admin_policy" {
  description = "Whether to attach the AdministratorAccess policy to the admin role"
  type        = bool
  default     = true
}

variable "create_assume_role_policy" {
  description = "Whether to create the assume role policy"
  type        = bool
  default     = true
}

variable "assume_role_policy_name" {
  description = "Name of the assume role policy"
  type        = string
  default     = "eks-assume-role-policy"
}

variable "create_eks_access_entry" {
  description = "Whether to create the EKS access entry"
  type        = bool
  default     = true
}

variable "access_entry_type" {
  description = "Type of access entry"
  type        = string
  default     = "STANDARD"
}

variable "create_eks_access_policy" {
  description = "Whether to create the EKS access policy association"
  type        = bool
  default     = true
}

variable "eks_access_policy_arn" {
  description = "ARN of the EKS access policy"
  type        = string
  default     = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
}

variable "access_scope_type" {
  description = "Type of access scope (cluster or namespace)"
  type        = string
  default     = "cluster"
}

variable "access_scope_namespaces" {
  description = "List of namespaces for access scope (only if type is namespace)"
  type        = list(string)
  default     = []
}

# RDS PostgreSQL Variables
variable "rds_instance_identifier" {
  description = "RDS PostgreSQL instance identifier"
  type        = string
  default     = "nt114-postgres-dev"
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB"
  type        = number
  default     = 100
}

variable "rds_storage_encrypted" {
  description = "RDS storage encryption"
  type        = bool
  default     = true
}

variable "rds_initial_database" {
  description = "Initial database name"
  type        = string
  default     = "postgres"
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "postgres"
}

variable "rds_port" {
  description = "RDS port"
  type        = number
  default     = 5432
}

variable "rds_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

variable "rds_backup_window" {
  description = "RDS backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "rds_maintenance_window" {
  description = "RDS maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "rds_skip_final_snapshot" {
  description = "Skip RDS final snapshot"
  type        = bool
  default     = false
}

variable "rds_final_snapshot_identifier" {
  description = "RDS final snapshot identifier"
  type        = string
  default     = "nt114-postgres-dev-final-snapshot"
}

variable "rds_deletion_protection" {
  description = "RDS deletion protection"
  type        = bool
  default     = false
}

variable "rds_monitoring_interval" {
  description = "RDS enhanced monitoring interval"
  type        = number
  default     = 0
}

variable "rds_enabled_cloudwatch_logs_exports" {
  description = "RDS CloudWatch logs exports"
  type        = list(string)
  default     = ["postgresql"]
}

variable "rds_log_retention_days" {
  description = "RDS log retention days"
  type        = number
  default     = 7
}

# S3 Migration Variables
variable "migration_bucket_name" {
  description = "S3 bucket name for migration files"
  type        = string
  default     = "nt114-migration-bucket-dev"
}

# Bastion Host Variables
variable "bastion_instance_name" {
  description = "Bastion host instance name"
  type        = string
  default     = "nt114-bastion-dev"
}

variable "bastion_instance_type" {
  description = "Bastion host instance type"
  type        = string
  default     = "t3.small"
}

variable "bastion_ami_id" {
  description = "Bastion host AMI ID"
  type        = string
  default     = "ami-0c02fb55956c7d316"
}

variable "bastion_key_name" {
  description = "Bastion host SSH key name"
  type        = string
  default     = "nt114-bastion-key"
}

variable "bastion_public_key" {
  description = "Bastion host public key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "bastion_allowed_ssh_cidrs" {
  description = "Bastion host allowed SSH CIDRs"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "bastion_root_volume_size" {
  description = "Bastion host root volume size in GB"
  type        = number
  default     = 20
}

variable "bastion_allocate_eip" {
  description = "Allocate EIP for bastion host"
  type        = bool
  default     = true
}
