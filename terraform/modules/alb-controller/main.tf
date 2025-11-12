data "aws_caller_identity" "current" {}

# IAM policy document for EBS CSI controller assume role
data "aws_iam_policy_document" "ebs_controller_assume_role_policy" {
  count = var.enable_ebs_csi_controller ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.oidc_provider}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider}:sub"
      values   = ["system:serviceaccount:kube-system:ebs-csi-controller-sa"]
    }
  }
}

# IAM role for EBS CSI driver
resource "aws_iam_role" "ebs_csi_controller" {
  count = var.enable_ebs_csi_controller ? 1 : 0

  name               = "${var.cluster_name}-ebs-csi-controller"
  assume_role_policy = data.aws_iam_policy_document.ebs_controller_assume_role_policy[0].json

  tags = {
    Name = "${var.cluster_name}-ebs-csi-controller"
  }
}

# Attach AWS managed EBS CSI driver policy
resource "aws_iam_role_policy_attachment" "ebs_csi_controller" {
  count = var.enable_ebs_csi_controller ? 1 : 0

  role       = aws_iam_role.ebs_csi_controller[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

# Helm release for AWS Load Balancer Controller
resource "helm_release" "aws_load_balancer_controller" {
  count = var.enable_alb_controller ? 1 : 0

  depends_on = [var.node_group_id]

  name       = var.helm_release_name
  namespace  = var.helm_namespace
  chart      = var.helm_chart_name
  repository = var.helm_chart_repository
  version    = var.helm_chart_version

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "region"
    value = var.aws_region
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = var.service_account_name
  }

  dynamic "set" {
    for_each = var.additional_helm_values
    content {
      name  = set.key
      value = set.value
    }
  }
}
