# SSH Key Pair for Bastion Host Access
resource "aws_key_pair" "bastion" {
  key_name   = var.key_name
  public_key = var.public_key

  tags = merge(
    var.tags,
    {
      Name = var.key_name
    }
  )
}

# IAM Role for Bastion Host
resource "aws_iam_role" "bastion" {
  name = var.iam_role_name

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

  tags = merge(
    var.tags,
    {
      Name = var.iam_role_name
    }
  )
}

# IAM Policy for SSM access
resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# IAM Policy for CloudWatch access
resource "aws_iam_role_policy_attachment" "cloudwatch_policy" {
  role       = aws_iam_role.bastion.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Instance Profile
resource "aws_iam_instance_profile" "bastion" {
  name = "${var.instance_name}-instance-profile"
  role = aws_iam_role.bastion.name
}

# Security Group for Bastion Host
resource "aws_security_group" "bastion" {
  name        = "${var.instance_name}-sg"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  # SSH access from allowed CIDRs
  dynamic "ingress" {
    for_each = var.allowed_ssh_cidrs
    content {
      description = "SSH from ${ingress.value}"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # PostgreSQL access to RDS
  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.rds_security_group_ids
  }

  # HTTP/HTTPS outbound
  egress {
    description = "HTTP/HTTPS outbound (includes S3 access)"
    from_port   = 80
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.instance_name}-sg"
    }
  )
}

# EC2 Instance for Bastion Host
resource "aws_instance" "bastion" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.bastion.key_name
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  iam_instance_profile        = aws_iam_instance_profile.bastion.name
  associate_public_ip_address = true

  # User data for initial setup (simplified)
  user_data = base64encode(<<-EOF
#!/bin/bash

# Update system
yum update -y

# Install required packages
yum install -y postgresql15 postgresql15-server git htop aws-cli

# Create migration directory
mkdir -p /opt/migration
mkdir -p /opt/migration/files

# Log setup completion
echo "Bastion host setup completed at $(date)" > /opt/migration/setup.log
echo "RDS Endpoint: ${var.db_host}" >> /opt/migration/setup.log
echo "RDS Port: ${var.db_port}" >> /opt/migration/setup.log
echo "RDS Username: ${var.db_username}" >> /opt/migration/setup.log
echo "S3 Bucket: ${var.s3_bucket_name}" >> /opt/migration/setup.log
EOF
  )

  # Root volume
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true
  }

  tags = merge(
    var.tags,
    {
      Name        = var.instance_name
      Environment = var.environment
    }
  )

  depends_on = [aws_security_group.bastion]
}

# EIP for Bastion Host (optional)
resource "aws_eip" "bastion" {
  count    = var.allocate_eip ? 1 : 0
  instance = aws_instance.bastion.id
  domain   = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.instance_name}-eip"
    }
  )

  depends_on = [aws_instance.bastion]
}