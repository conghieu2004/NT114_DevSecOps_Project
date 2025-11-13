variable "instance_name" {
  description = "Name of the bastion host instance"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI ID for the bastion host"
  type        = string
  default     = "ami-0c02fb55956c7d316" # Amazon Linux 2023
}

variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
}

variable "public_key" {
  description = "Public key content for SSH access"
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "VPC ID where the bastion host will be deployed"
  type        = string
}

variable "public_subnet_id" {
  description = "Public subnet ID for the bastion host"
  type        = string
}

variable "allowed_ssh_cidrs" {
  description = "List of CIDR blocks allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "rds_security_group_ids" {
  description = "List of RDS security group IDs for PostgreSQL access"
  type        = list(string)
  default     = []
}

variable "db_host" {
  description = "RDS PostgreSQL host"
  type        = string
  sensitive   = true
}

variable "db_port" {
  description = "RDS PostgreSQL port"
  type        = number
  default     = 5432
}

variable "db_username" {
  description = "RDS PostgreSQL username"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "RDS PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "s3_bucket_name" {
  description = "S3 bucket name for migration files"
  type        = string
}

variable "iam_role_name" {
  description = "IAM role name for bastion host"
  type        = string
  default     = "bastion-host-role"
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 20
}

variable "allocate_eip" {
  description = "Whether to allocate Elastic IP for the bastion host"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}