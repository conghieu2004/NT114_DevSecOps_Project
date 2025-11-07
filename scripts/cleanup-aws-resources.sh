#!/bin/bash
# Comprehensive AWS Resource Cleanup - Delete resources with tag Project=NT114_DevSecOps
set +e

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_TAG="Project"
PROJECT_VALUE="NT114_DevSecOps"

echo "========================================="
echo "🗑️  AWS RESOURCE CLEANUP SCRIPT"
echo "========================================="
echo "Region: $AWS_REGION"
echo "Deleting resources with tag: $PROJECT_TAG=$PROJECT_VALUE"
echo ""

# Helper function to check if resource has the project tag
has_project_tag() {
    local tags="$1"
    echo "$tags" | grep -q "\"$PROJECT_TAG\"" && echo "$tags" | grep -q "\"$PROJECT_VALUE\""
    return $?
}

# 1. Delete EKS Node Groups & Clusters
echo "1️⃣  Deleting EKS Clusters with project tag..."
CLUSTERS=$(aws eks list-clusters --region $AWS_REGION --query 'clusters[]' --output text 2>/dev/null)
for CLUSTER in $CLUSTERS; do
    TAGS=$(aws eks describe-cluster --name $CLUSTER --region $AWS_REGION --query 'cluster.tags' --output json 2>/dev/null)
    if has_project_tag "$TAGS"; then
        echo "  🗑️  Cluster: $CLUSTER (tagged)"

        # Delete all node groups
        NODEGROUPS=$(aws eks list-nodegroups --cluster-name $CLUSTER --region $AWS_REGION --query 'nodegroups[]' --output text 2>/dev/null)
        for NG in $NODEGROUPS; do
            echo "    - Deleting node group: $NG"
            aws eks delete-nodegroup --cluster-name $CLUSTER --nodegroup-name $NG --region $AWS_REGION 2>/dev/null
        done

        # Wait for node groups
        echo "    - Waiting for node groups to delete..."
        sleep 30

        # Delete cluster
        echo "    - Deleting cluster: $CLUSTER"
        aws eks delete-cluster --name $CLUSTER --region $AWS_REGION 2>/dev/null
    fi
done
echo "  ✅ EKS cleanup initiated"
echo ""

# 2. Delete Load Balancers with project tag
echo "2️⃣  Deleting Load Balancers with project tag..."
LBS=$(aws elbv2 describe-load-balancers --region $AWS_REGION --query 'LoadBalancers[].[LoadBalancerArn,LoadBalancerName]' --output text 2>/dev/null)
while IFS=$'\t' read -r LB_ARN LB_NAME; do
    if [ -n "$LB_ARN" ]; then
        TAGS=$(aws elbv2 describe-tags --resource-arns "$LB_ARN" --region $AWS_REGION --query 'TagDescriptions[0].Tags' --output json 2>/dev/null)
        if has_project_tag "$TAGS"; then
            echo "  🗑️  Deleting ALB: $LB_NAME (tagged)"
            aws elbv2 delete-load-balancer --load-balancer-arn "$LB_ARN" --region $AWS_REGION 2>/dev/null
        fi
    fi
done <<< "$LBS"

# Classic Load Balancers
CLB=$(aws elb describe-load-balancers --region $AWS_REGION --query 'LoadBalancerDescriptions[].LoadBalancerName' --output text 2>/dev/null)
for LB in $CLB; do
    TAGS=$(aws elb describe-tags --load-balancer-names $LB --region $AWS_REGION --query 'TagDescriptions[0].Tags' --output json 2>/dev/null)
    if has_project_tag "$TAGS"; then
        echo "  🗑️  Deleting Classic LB: $LB (tagged)"
        aws elb delete-load-balancer --load-balancer-name $LB --region $AWS_REGION 2>/dev/null
    fi
done
echo "  ✅ Load Balancers deleted"
echo ""

# 3. Terminate EC2 Instances with project tag
echo "3️⃣  Terminating EC2 Instances with project tag..."
INSTANCES=$(aws ec2 describe-instances --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" \
              "Name=instance-state-name,Values=running,stopped,stopping" \
    --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null)
if [ -n "$INSTANCES" ]; then
    echo "  🗑️  Terminating instances: $INSTANCES"
    aws ec2 terminate-instances --instance-ids $INSTANCES --region $AWS_REGION 2>/dev/null
    echo "  ⏳ Waiting for instances to terminate..."
    sleep 60
fi
echo "  ✅ Instances terminated"
echo ""

# 4. Delete Auto Scaling Groups with project tag
echo "4️⃣  Deleting Auto Scaling Groups with project tag..."
ASGS=$(aws autoscaling describe-auto-scaling-groups --region $AWS_REGION --query 'AutoScalingGroups[].[AutoScalingGroupName]' --output text 2>/dev/null)
for ASG in $ASGS; do
    if [ -n "$ASG" ]; then
        TAGS=$(aws autoscaling describe-tags --filters "Name=auto-scaling-group,Values=$ASG" --region $AWS_REGION --query 'Tags' --output json 2>/dev/null)
        if has_project_tag "$TAGS"; then
            echo "  🗑️  Deleting ASG: $ASG (tagged)"
            aws autoscaling delete-auto-scaling-group --auto-scaling-group-name $ASG --force-delete --region $AWS_REGION 2>/dev/null
        fi
    fi
done
echo "  ✅ ASGs deleted"
echo ""

# 5. Delete Launch Templates with project tag
echo "5️⃣  Deleting Launch Templates with project tag..."
LTS=$(aws ec2 describe-launch-templates --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" \
    --query 'LaunchTemplates[].LaunchTemplateId' --output text 2>/dev/null)
for LT in $LTS; do
    echo "  🗑️  Deleting Launch Template: $LT"
    aws ec2 delete-launch-template --launch-template-id $LT --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Launch Templates deleted"
echo ""

# 6. Delete NAT Gateways with project tag
echo "6️⃣  Deleting NAT Gateways with project tag..."
NGWS=$(aws ec2 describe-nat-gateways --region $AWS_REGION \
    --filter "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" "Name=state,Values=available" \
    --query 'NatGateways[].NatGatewayId' --output text 2>/dev/null)
for NGW in $NGWS; do
    echo "  🗑️  Deleting NAT Gateway: $NGW"
    aws ec2 delete-nat-gateway --nat-gateway-id $NGW --region $AWS_REGION 2>/dev/null
done
if [ -n "$NGWS" ]; then
    echo "  ⏳ Waiting for NAT Gateways to delete..."
    sleep 60
fi
echo "  ✅ NAT Gateways deleted"
echo ""

# 7. Release Elastic IPs with project tag
echo "7️⃣  Releasing Elastic IPs with project tag..."
EIPS=$(aws ec2 describe-addresses --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" \
    --query 'Addresses[].AllocationId' --output text 2>/dev/null)
for EIP in $EIPS; do
    echo "  🗑️  Releasing EIP: $EIP"
    aws ec2 release-address --allocation-id $EIP --region $AWS_REGION 2>/dev/null
done
echo "  ✅ EIPs released"
echo ""

# 8. Delete Network Interfaces with project tag
echo "8️⃣  Deleting Network Interfaces with project tag..."
ENIS=$(aws ec2 describe-network-interfaces --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" "Name=status,Values=available" \
    --query 'NetworkInterfaces[].NetworkInterfaceId' --output text 2>/dev/null)
for ENI in $ENIS; do
    echo "  🗑️  Deleting ENI: $ENI"
    aws ec2 delete-network-interface --network-interface-id $ENI --region $AWS_REGION 2>/dev/null
done
echo "  ✅ ENIs deleted"
echo ""

# 9. Delete VPCs with project tag and all dependencies
echo "9️⃣  Deleting VPCs with project tag..."
VPCS=$(aws ec2 describe-vpcs --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" \
    --query 'Vpcs[].VpcId' --output text 2>/dev/null)
for VPC in $VPCS; do
    echo "  🗑️  Processing VPC: $VPC (tagged)"

    # Delete VPC Endpoints
    echo "    - Deleting VPC Endpoints..."
    ENDPOINTS=$(aws ec2 describe-vpc-endpoints --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC" --query 'VpcEndpoints[].VpcEndpointId' --output text 2>/dev/null)
    for EP in $ENDPOINTS; do
        aws ec2 delete-vpc-endpoints --vpc-endpoint-ids $EP --region $AWS_REGION 2>/dev/null
    done

    # Detach and delete Internet Gateways
    echo "    - Deleting Internet Gateways..."
    IGWS=$(aws ec2 describe-internet-gateways --region $AWS_REGION --filters "Name=attachment.vpc-id,Values=$VPC" --query 'InternetGateways[].InternetGatewayId' --output text 2>/dev/null)
    for IGW in $IGWS; do
        aws ec2 detach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC --region $AWS_REGION 2>/dev/null
        aws ec2 delete-internet-gateway --internet-gateway-id $IGW --region $AWS_REGION 2>/dev/null
    done

    # Delete subnets
    echo "    - Deleting Subnets..."
    SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC" --query 'Subnets[].SubnetId' --output text 2>/dev/null)
    for SUBNET in $SUBNETS; do
        aws ec2 delete-subnet --subnet-id $SUBNET --region $AWS_REGION 2>/dev/null
    done

    # Delete route tables (except main)
    echo "    - Deleting Route Tables..."
    RTS=$(aws ec2 describe-route-tables --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC" --query 'RouteTables[?Associations[0].Main==`false`].RouteTableId' --output text 2>/dev/null)
    for RT in $RTS; do
        aws ec2 delete-route-table --route-table-id $RT --region $AWS_REGION 2>/dev/null
    done

    # Delete Security Groups (except default)
    echo "    - Deleting Security Groups..."
    SGS=$(aws ec2 describe-security-groups --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC" --query 'SecurityGroups[?GroupName!=`default`].GroupId' --output text 2>/dev/null)
    # First pass - remove rules
    for SG in $SGS; do
        aws ec2 revoke-security-group-ingress --group-id $SG --ip-permissions "$(aws ec2 describe-security-groups --group-ids $SG --region $AWS_REGION --query 'SecurityGroups[0].IpPermissions' 2>/dev/null)" --region $AWS_REGION 2>/dev/null
        aws ec2 revoke-security-group-egress --group-id $SG --ip-permissions "$(aws ec2 describe-security-groups --group-ids $SG --region $AWS_REGION --query 'SecurityGroups[0].IpPermissionsEgress' 2>/dev/null)" --region $AWS_REGION 2>/dev/null
    done
    # Second pass - delete groups
    for SG in $SGS; do
        aws ec2 delete-security-group --group-id $SG --region $AWS_REGION 2>/dev/null
    done

    # Delete VPC
    echo "    - Deleting VPC: $VPC"
    aws ec2 delete-vpc --vpc-id $VPC --region $AWS_REGION 2>/dev/null
    echo "  ✅ VPC $VPC deleted"
done
echo ""

# 10. Delete IAM Roles with project tag or specific names
echo "🔟 Deleting IAM Roles..."
ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `nt114`) || contains(RoleName, `NT114`)].RoleName' --output text 2>/dev/null)
for ROLE in $ROLES; do
    TAGS=$(aws iam list-role-tags --role-name $ROLE --query 'Tags' --output json 2>/dev/null)
    if has_project_tag "$TAGS" || echo "$ROLE" | grep -qi "nt114"; then
        echo "  🗑️  Deleting Role: $ROLE"

        # Detach managed policies
        POLICIES=$(aws iam list-attached-role-policies --role-name $ROLE --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
        for POLICY in $POLICIES; do
            aws iam detach-role-policy --role-name $ROLE --policy-arn $POLICY 2>/dev/null
        done

        # Delete inline policies
        INLINE=$(aws iam list-role-policies --role-name $ROLE --query 'PolicyNames[]' --output text 2>/dev/null)
        for POL in $INLINE; do
            aws iam delete-role-policy --role-name $ROLE --policy-name $POL 2>/dev/null
        done

        # Delete instance profiles
        PROFILES=$(aws iam list-instance-profiles-for-role --role-name $ROLE --query 'InstanceProfiles[].InstanceProfileName' --output text 2>/dev/null)
        for PROFILE in $PROFILES; do
            aws iam remove-role-from-instance-profile --instance-profile-name $PROFILE --role-name $ROLE 2>/dev/null
            aws iam delete-instance-profile --instance-profile-name $PROFILE 2>/dev/null
        done

        # Delete role
        aws iam delete-role --role-name $ROLE 2>/dev/null
    fi
done
echo "  ✅ IAM Roles deleted"
echo ""

# 11. Delete EBS Volumes with project tag
echo "1️⃣1️⃣  Deleting EBS Volumes with project tag..."
VOLUMES=$(aws ec2 describe-volumes --region $AWS_REGION \
    --filters "Name=tag:$PROJECT_TAG,Values=$PROJECT_VALUE" "Name=status,Values=available" \
    --query 'Volumes[].VolumeId' --output text 2>/dev/null)
for VOL in $VOLUMES; do
    echo "  🗑️  Deleting Volume: $VOL"
    aws ec2 delete-volume --volume-id $VOL --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Volumes deleted"
echo ""

# 12. Delete CloudWatch Log Groups
echo "1️⃣2️⃣  Deleting CloudWatch Log Groups..."
LOG_GROUPS=$(aws logs describe-log-groups --region $AWS_REGION --query 'logGroups[?contains(logGroupName, `/aws/eks`) || contains(logGroupName, `nt114`) || contains(logGroupName, `NT114`)].logGroupName' --output text 2>/dev/null)
for LG in $LOG_GROUPS; do
    echo "  🗑️  Deleting Log Group: $LG"
    aws logs delete-log-group --log-group-name $LG --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Log Groups deleted"
echo ""

# 13. Delete ECR Repositories with project tag or specific names
echo "1️⃣3️⃣  Deleting ECR Repositories..."
ECR_REPOS=$(aws ecr describe-repositories --region $AWS_REGION --query 'repositories[?contains(repositoryName, `nt114`) || contains(repositoryName, `NT114`)].repositoryName' --output text 2>/dev/null)
for REPO in $ECR_REPOS; do
    echo "  🗑️  Deleting ECR Repository: $REPO"
    aws ecr delete-repository --repository-name $REPO --region $AWS_REGION --force 2>/dev/null
done
echo "  ✅ ECR Repositories deleted"
echo ""

# 14. Delete CloudFormation Stacks with project tag
echo "1️⃣4️⃣  Deleting CloudFormation Stacks..."
STACKS=$(aws cloudformation list-stacks --region $AWS_REGION --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output text 2>/dev/null)
for STACK in $STACKS; do
    TAGS=$(aws cloudformation describe-stacks --stack-name $STACK --region $AWS_REGION --query 'Stacks[0].Tags' --output json 2>/dev/null)
    if has_project_tag "$TAGS" || echo "$STACK" | grep -qi "nt114"; then
        echo "  🗑️  Deleting Stack: $STACK"
        aws cloudformation delete-stack --stack-name $STACK --region $AWS_REGION 2>/dev/null
    fi
done
echo "  ✅ Stacks deleted"
echo ""

echo "========================================="
echo "✅ CLEANUP COMPLETED!"
echo "========================================="
echo ""
echo "All AWS resources with tag $PROJECT_TAG=$PROJECT_VALUE have been deleted."
echo "Note: Some resources may take a few minutes to fully delete."
echo ""
echo "Resources deleted:"
echo "  ✅ EKS Clusters & Node Groups"
echo "  ✅ Load Balancers (ALB & Classic)"
echo "  ✅ EC2 Instances"
echo "  ✅ Auto Scaling Groups"
echo "  ✅ Launch Templates"
echo "  ✅ NAT Gateways"
echo "  ✅ Elastic IPs"
echo "  ✅ Network Interfaces"
echo "  ✅ VPCs and all components"
echo "  ✅ IAM Roles"
echo "  ✅ EBS Volumes"
echo "  ✅ CloudWatch Log Groups"
echo "  ✅ ECR Repositories"
echo "  ✅ CloudFormation Stacks"
echo ""
