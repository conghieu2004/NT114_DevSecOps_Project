#!/bin/bash

set -e

BUCKET_NAME="nt114-devsecops-terraform-state"
DYNAMODB_TABLE="nt114-devsecops-terraform-locks"
REGION="us-east-1"

echo "Setting up Terraform backend resources..."
echo ""

# Create S3 bucket for state
echo "Creating S3 bucket: $BUCKET_NAME"
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $REGION

    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled

    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'

    # Block public access
    aws s3api put-public-access-block \
        --bucket $BUCKET_NAME \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

    echo "✅ S3 bucket created and configured"
else
    echo "✅ S3 bucket already exists"
fi

echo ""

# Create DynamoDB table for state locking
echo "Creating DynamoDB table: $DYNAMODB_TABLE"
if ! aws dynamodb describe-table --table-name $DYNAMODB_TABLE --region $REGION &> /dev/null; then
    aws dynamodb create-table \
        --table-name $DYNAMODB_TABLE \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
        --region $REGION

    echo "Waiting for table to be active..."
    aws dynamodb wait table-exists --table-name $DYNAMODB_TABLE --region $REGION

    echo "✅ DynamoDB table created"
else
    echo "✅ DynamoDB table already exists"
fi

echo ""
echo "✅ Terraform backend setup complete!"
echo ""
echo "Backend configuration:"
echo "  Bucket: $BUCKET_NAME"
echo "  DynamoDB Table: $DYNAMODB_TABLE"
echo "  Region: $REGION"
