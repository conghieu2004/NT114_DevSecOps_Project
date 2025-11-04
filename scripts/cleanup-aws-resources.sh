#!/bin/bash
# Comprehensive AWS Resource Cleanup - Delete EVERYTHING from last 5 hours
set +e

AWS_REGION="${AWS_REGION:-us-east-1}"
CUTOFF_TIME=$(date -u -d '5 hours ago' '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -u -v-5H '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || echo "")

echo "========================================="
echo "🗑️  AWS RESOURCE CLEANUP SCRIPT"
echo "========================================="
echo "Region: $AWS_REGION"
echo "Deleting resources created after: $CUTOFF_TIME"
echo ""

# 1. Delete EKS Node Groups & Clusters
echo "1️⃣  Deleting EKS Clusters..."
CLUSTERS=$(aws eks list-clusters --region $AWS_REGION --query 'clusters[]' --output text 2>/dev/null)
for CLUSTER in $CLUSTERS; do
    echo "  🗑️  Cluster: $CLUSTER"

    # Delete all node groups
    NODEGROUPS=$(aws eks list-nodegroups --cluster-name $CLUSTER --region $AWS_REGION --query 'nodegroups[]' --output text 2>/dev/null)
    for NG in $NODEGROUPS; do
        echo "    - Deleting node group: $NG"
        aws eks delete-nodegroup --cluster-name $CLUSTER --nodegroup-name $NG --region $AWS_REGION 2>/dev/null
    done

    # Wait for node groups
    sleep 30

    # Delete cluster
    echo "    - Deleting cluster: $CLUSTER"
    aws eks delete-cluster --name $CLUSTER --region $AWS_REGION 2>/dev/null
done
echo "  ✅ EKS cleanup initiated"
echo ""

# 2. Delete Load Balancers
echo "2️⃣  Deleting Load Balancers..."
LBS=$(aws elbv2 describe-load-balancers --region $AWS_REGION --query 'LoadBalancers[].LoadBalancerArn' --output text 2>/dev/null)
for LB in $LBS; do
    echo "  🗑️  Deleting LB: $(basename $LB)"
    aws elbv2 delete-load-balancer --load-balancer-arn $LB --region $AWS_REGION 2>/dev/null
done

# Classic Load Balancers
CLB=$(aws elb describe-load-balancers --region $AWS_REGION --query 'LoadBalancerDescriptions[].LoadBalancerName' --output text 2>/dev/null)
for LB in $CLB; do
    echo "  🗑️  Deleting Classic LB: $LB"
    aws elb delete-load-balancer --load-balancer-name $LB --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Load Balancers deleted"
echo ""

# 3. Delete Auto Scaling Groups
echo "3️⃣  Deleting Auto Scaling Groups..."
ASGS=$(aws autoscaling describe-auto-scaling-groups --region $AWS_REGION --query 'AutoScalingGroups[].AutoScalingGroupName' --output text 2>/dev/null)
for ASG in $ASGS; do
    echo "  🗑️  Deleting ASG: $ASG"
    aws autoscaling delete-auto-scaling-group --auto-scaling-group-name $ASG --force-delete --region $AWS_REGION 2>/dev/null
done
echo "  ✅ ASGs deleted"
echo ""

# 4. Delete Launch Templates
echo "4️⃣  Deleting Launch Templates..."
LTS=$(aws ec2 describe-launch-templates --region $AWS_REGION --query 'LaunchTemplates[].LaunchTemplateId' --output text 2>/dev/null)
for LT in $LTS; do
    echo "  🗑️  Deleting Launch Template: $LT"
    aws ec2 delete-launch-template --launch-template-id $LT --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Launch Templates deleted"
echo ""

# 5. Terminate EC2 Instances
echo "5️⃣  Terminating EC2 Instances..."
INSTANCES=$(aws ec2 describe-instances --region $AWS_REGION --filters "Name=instance-state-name,Values=running,stopped,stopping" --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null)
if [ -n "$INSTANCES" ]; then
    echo "  🗑️  Terminating instances: $INSTANCES"
    aws ec2 terminate-instances --instance-ids $INSTANCES --region $AWS_REGION 2>/dev/null
    echo "  ⏳ Waiting for instances to terminate..."
    sleep 60
fi
echo "  ✅ Instances terminated"
echo ""

# 6. Delete NAT Gateways
echo "6️⃣  Deleting NAT Gateways..."
NGWS=$(aws ec2 describe-nat-gateways --region $AWS_REGION --filter "Name=state,Values=available" --query 'NatGateways[].NatGatewayId' --output text 2>/dev/null)
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

# 7. Release Elastic IPs
echo "7️⃣  Releasing Elastic IPs..."
EIPS=$(aws ec2 describe-addresses --region $AWS_REGION --query 'Addresses[].AllocationId' --output text 2>/dev/null)
for EIP in $EIPS; do
    echo "  🗑️  Releasing EIP: $EIP"
    aws ec2 release-address --allocation-id $EIP --region $AWS_REGION 2>/dev/null
done
echo "  ✅ EIPs released"
echo ""

# 8. Delete Network Interfaces
echo "8️⃣  Deleting Network Interfaces..."
ENIS=$(aws ec2 describe-network-interfaces --region $AWS_REGION --query 'NetworkInterfaces[?Status==`available`].NetworkInterfaceId' --output text 2>/dev/null)
for ENI in $ENIS; do
    echo "  🗑️  Deleting ENI: $ENI"
    aws ec2 delete-network-interface --network-interface-id $ENI --region $AWS_REGION 2>/dev/null
done
echo "  ✅ ENIs deleted"
echo ""

# 9. Delete VPCs and all dependencies
echo "9️⃣  Deleting VPCs..."
VPCS=$(aws ec2 describe-vpcs --region $AWS_REGION --query 'Vpcs[?IsDefault==`false`].VpcId' --output text 2>/dev/null)
for VPC in $VPCS; do
    echo "  🗑️  Processing VPC: $VPC"

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

# 10. Delete IAM Roles
echo "🔟 Deleting IAM Roles..."
ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `eks`) || contains(RoleName, `terraform`) || contains(RoleName, `node`)].RoleName' --output text 2>/dev/null)
for ROLE in $ROLES; do
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
done
echo "  ✅ IAM Roles deleted"
echo ""

# 11. Delete EBS Volumes
echo "1️⃣1️⃣  Deleting EBS Volumes..."
VOLUMES=$(aws ec2 describe-volumes --region $AWS_REGION --filters "Name=status,Values=available" --query 'Volumes[].VolumeId' --output text 2>/dev/null)
for VOL in $VOLUMES; do
    echo "  🗑️  Deleting Volume: $VOL"
    aws ec2 delete-volume --volume-id $VOL --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Volumes deleted"
echo ""

# 12. Delete CloudWatch Log Groups
echo "1️⃣2️⃣  Deleting CloudWatch Log Groups..."
LOG_GROUPS=$(aws logs describe-log-groups --region $AWS_REGION --query 'logGroups[?contains(logGroupName, `/aws/eks`) || contains(logGroupName, `eks-`)].logGroupName' --output text 2>/dev/null)
for LG in $LOG_GROUPS; do
    echo "  🗑️  Deleting Log Group: $LG"
    aws logs delete-log-group --log-group-name $LG --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Log Groups deleted"
echo ""

# 13. Delete KMS Aliases and Keys (DISABLED - AWS managed keys cannot be deleted)
# echo "1️⃣3️⃣  Deleting KMS Aliases..."
# KMS_ALIASES=$(aws kms list-aliases --region $AWS_REGION --query 'Aliases[?contains(AliasName, `eks`) || contains(AliasName, `terraform`)].AliasName' --output text 2>/dev/null)
# for ALIAS in $KMS_ALIASES; do
#     echo "  🗑️  Deleting KMS Alias: $ALIAS"
#     aws kms delete-alias --alias-name $ALIAS --region $AWS_REGION 2>/dev/null
# done
# echo "  ✅ KMS Aliases deleted"
echo "  ⏭️  Skipping KMS cleanup (AWS managed keys auto-deleted with services)"
echo ""

# 14. Delete CloudFormation Stacks
echo "1️⃣4️⃣  Deleting CloudFormation Stacks..."
STACKS=$(aws cloudformation list-stacks --region $AWS_REGION --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output text 2>/dev/null)
for STACK in $STACKS; do
    echo "  🗑️  Deleting Stack: $STACK"
    aws cloudformation delete-stack --stack-name $STACK --region $AWS_REGION 2>/dev/null
done
echo "  ✅ Stacks deleted"
echo ""

# 15. Delete ECR Repositories
echo "1️⃣5️⃣  Deleting ECR Repositories..."
ECR_REPOS=$(aws ecr describe-repositories --region $AWS_REGION --query 'repositories[].repositoryName' --output text 2>/dev/null)
for REPO in $ECR_REPOS; do
    echo "  🗑️  Deleting ECR Repository: $REPO"
    aws ecr delete-repository --repository-name $REPO --region $AWS_REGION --force 2>/dev/null
done
echo "  ✅ ECR Repositories deleted"
echo ""

# 16. Delete IAM Users (GitHub Actions users)
echo "1️⃣6️⃣  Deleting IAM Users..."
IAM_USERS=$(aws iam list-users --query 'Users[?contains(UserName, `github-actions`) || contains(UserName, `nt114`)].UserName' --output text 2>/dev/null)
for USER in $IAM_USERS; do
    echo "  🗑️  Deleting IAM User: $USER"

    # Delete access keys
    ACCESS_KEYS=$(aws iam list-access-keys --user-name $USER --query 'AccessKeyMetadata[].AccessKeyId' --output text 2>/dev/null)
    for KEY in $ACCESS_KEYS; do
        echo "    - Deleting access key: $KEY"
        aws iam delete-access-key --user-name $USER --access-key-id $KEY 2>/dev/null
    done

    # Detach user policies
    USER_POLICIES=$(aws iam list-attached-user-policies --user-name $USER --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
    for POLICY in $USER_POLICIES; do
        echo "    - Detaching policy: $POLICY"
        aws iam detach-user-policy --user-name $USER --policy-arn $POLICY 2>/dev/null
    done

    # Delete inline user policies
    INLINE_POLICIES=$(aws iam list-user-policies --user-name $USER --query 'PolicyNames[]' --output text 2>/dev/null)
    for POL in $INLINE_POLICIES; do
        echo "    - Deleting inline policy: $POL"
        aws iam delete-user-policy --user-name $USER --policy-name $POL 2>/dev/null
    done

    # Remove user from groups
    USER_GROUPS=$(aws iam list-groups-for-user --user-name $USER --query 'Groups[].GroupName' --output text 2>/dev/null)
    for GROUP in $USER_GROUPS; do
        echo "    - Removing from group: $GROUP"
        aws iam remove-user-from-group --user-name $USER --group-name $GROUP 2>/dev/null
    done

    # Delete user
    aws iam delete-user --user-name $USER 2>/dev/null
done
echo "  ✅ IAM Users deleted"
echo ""

# 17. Delete IAM Groups
echo "1️⃣7️⃣  Deleting IAM Groups..."
IAM_GROUPS=$(aws iam list-groups --query 'Groups[?contains(GroupName, `eks`) || contains(GroupName, `nt114`)].GroupName' --output text 2>/dev/null)
for GROUP in $IAM_GROUPS; do
    echo "  🗑️  Deleting IAM Group: $GROUP"

    # Detach group policies
    GROUP_POLICIES=$(aws iam list-attached-group-policies --group-name $GROUP --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
    for POLICY in $GROUP_POLICIES; do
        echo "    - Detaching policy: $POLICY"
        aws iam detach-group-policy --group-name $GROUP --policy-arn $POLICY 2>/dev/null
    done

    # Delete inline group policies
    INLINE_POLICIES=$(aws iam list-group-policies --group-name $GROUP --query 'PolicyNames[]' --output text 2>/dev/null)
    for POL in $INLINE_POLICIES; do
        echo "    - Deleting inline policy: $POL"
        aws iam delete-group-policy --group-name $GROUP --policy-name $POL 2>/dev/null
    done

    # Delete group
    aws iam delete-group --group-name $GROUP 2>/dev/null
done
echo "  ✅ IAM Groups deleted"
echo ""

# 18. Delete IAM Policies (Customer Managed)
echo "1️⃣8️⃣  Deleting IAM Policies..."
IAM_POLICIES=$(aws iam list-policies --scope Local --query 'Policies[?contains(PolicyName, `eks`) || contains(PolicyName, `nt114`) || contains(PolicyName, `github-actions`)].Arn' --output text 2>/dev/null)
for POLICY_ARN in $IAM_POLICIES; do
    POLICY_NAME=$(basename $POLICY_ARN)
    echo "  🗑️  Deleting IAM Policy: $POLICY_NAME"

    # Delete all policy versions except default
    VERSIONS=$(aws iam list-policy-versions --policy-arn $POLICY_ARN --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text 2>/dev/null)
    for VERSION in $VERSIONS; do
        echo "    - Deleting policy version: $VERSION"
        aws iam delete-policy-version --policy-arn $POLICY_ARN --version-id $VERSION 2>/dev/null
    done

    # Delete policy
    aws iam delete-policy --policy-arn $POLICY_ARN 2>/dev/null
done
echo "  ✅ IAM Policies deleted"
echo ""

echo "========================================="
echo "✅ CLEANUP COMPLETED!"
echo "========================================="
echo ""
echo "All AWS resources should be deleted."
echo "Note: Some resources may take a few minutes to fully delete."
echo ""
