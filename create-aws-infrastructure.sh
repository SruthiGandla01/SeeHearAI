#!/bin/bash
# SeeHearAI AWS Infrastructure Setup - Phase 1
# Save as: create-aws-infrastructure.sh

echo "🏗️ Creating AWS Infrastructure for SeeHearAI Phase 1"
echo "=================================================="

# Variables
TIMESTAMP=$(date +%s)
BUCKET_NAME="seehearai-storage-$TIMESTAMP"
TABLE_NAME="SeeHearAISessions"
REGION="us-east-1"
KEY_NAME="seeherai-key"

echo "📋 Configuration:"
echo "   Project: SeeHearAI"
echo "   Region: $REGION"
echo "   S3 Bucket: $BUCKET_NAME"
echo "   DynamoDB Table: $TABLE_NAME"
echo ""

# Step 1: Create S3 Bucket for file storage
echo "🪣 Creating S3 bucket: $BUCKET_NAME"
aws s3 mb s3://$BUCKET_NAME --region $REGION

if [ $? -eq 0 ]; then
    echo "✅ S3 bucket created successfully"
    
    # Configure bucket for web access
    aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration '{
      "CORSRules": [
        {
          "AllowedOrigins": ["*"],
          "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
          "AllowedHeaders": ["*"],
          "MaxAgeSeconds": 3000
        }
      ]
    }'
    echo "✅ S3 CORS configured"
else
    echo "❌ Failed to create S3 bucket"
    exit 1
fi

# Step 2: Create DynamoDB table for session logs
echo ""
echo "🗃️ Creating DynamoDB table: $TABLE_NAME"
aws dynamodb create-table \
    --table-name $TABLE_NAME \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ DynamoDB table created successfully"
else
    echo "❌ Failed to create DynamoDB table (may already exist)"
fi

# Step 3: Create Key Pair for EC2 access
echo ""
echo "🔑 Creating EC2 Key Pair: $KEY_NAME"
aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text > $KEY_NAME.pem

if [ $? -eq 0 ]; then
    chmod 400 $KEY_NAME.pem
    echo "✅ Key pair created: $KEY_NAME.pem"
    echo "⚠️  IMPORTANT: Save $KEY_NAME.pem file - you'll need it for SSH access"
else
    echo "❌ Failed to create key pair (may already exist)"
fi

# Step 4: Create Security Group
echo ""
echo "🔒 Creating security group..."
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name SeeHearAISG \
    --description "Security group for SeeHearAI application" \
    --query 'GroupId' \
    --output text)

if [ $? -eq 0 ]; then
    echo "✅ Security group created: $SECURITY_GROUP_ID"
    
    # Allow SSH (port 22)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0
    
    # Allow HTTP (port 80)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0
    
    # Allow HTTPS (port 443)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0
    
    # Allow FastAPI (port 8000)
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0
    
    echo "✅ Security group rules configured"
else
    echo "❌ Failed to create security group (may already exist)"
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --group-names SeeHearAISG --query 'SecurityGroups[0].GroupId' --output text)
fi

# Step 5: Create IAM role for EC2
echo ""
echo "👤 Creating IAM role for EC2..."
aws iam create-role --role-name SeeHearAIEC2Role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}' > /dev/null

# Attach policies to the role
aws iam attach-role-policy --role-name SeeHearAIEC2Role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-role-policy --role-name SeeHearAIEC2Role --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Create instance profile
aws iam create-instance-profile --instance-profile-name SeeHearAIProfile > /dev/null
aws iam add-role-to-instance-profile --instance-profile-name SeeHearAIProfile --role-name SeeHearAIEC2Role

echo "✅ IAM role and instance profile created"

# Step 6: Create additional S3 folders for organization
echo ""
echo "📁 Creating S3 folder structure..."
aws s3api put-object --bucket $BUCKET_NAME --key audio-files/
aws s3api put-object --bucket $BUCKET_NAME --key video-frames/
aws s3api put-object --bucket $BUCKET_NAME --key models/
aws s3api put-object --bucket $BUCKET_NAME --key logs/
aws s3api put-object --bucket $BUCKET_NAME --key sessions/
echo "✅ S3 folder structure created"

# Step 7: Save configuration
echo ""
echo "📝 Saving configuration..."
cat > seehearai-aws-config.env << EOF
# SeeHearAI AWS Configuration - Phase 1
# ======================================
# Add these to your .env file:

S3_BUCKET=$BUCKET_NAME
DYNAMODB_TABLE=$TABLE_NAME
AWS_REGION=$REGION
SECURITY_GROUP_ID=$SECURITY_GROUP_ID
KEY_NAME=$KEY_NAME
IAM_INSTANCE_PROFILE=SeeHearAIProfile

# For deployment:
export S3_BUCKET=$BUCKET_NAME
export DYNAMODB_TABLE=$TABLE_NAME
export AWS_REGION=$REGION
export PROJECT_NAME=SeeHearAI
EOF

# Also create updated .env template
cat > .env.aws << EOF
# SeeHearAI Environment Variables - AWS Configuration
# ===================================================

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# AWS Configuration
AWS_REGION=$REGION
S3_BUCKET=$BUCKET_NAME
DYNAMODB_TABLE=$TABLE_NAME

# Lambda Configuration (for later phases)
LAMBDA_LOG_URL=your_lambda_url_here

# Application Configuration
PROJECT_NAME=SeeHearAI
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET=your_jwt_secret_here

# Model Configuration
YOLO_MODEL_PATH=/app/models/yolov8n.pt
BLIP_MODEL_PATH=/app/models/blip
WHISPER_MODEL=base
VOSK_MODEL_PATH=/app/vosk_model

# Performance Settings
MAX_WORKERS=4
UPLOAD_MAX_SIZE=10485760  # 10MB
SESSION_TIMEOUT=3600      # 1 hour
EOF

# Step 8: Test the setup
echo ""
echo "🧪 Testing AWS setup..."
echo "   Testing S3 access..."
aws s3 ls s3://$BUCKET_NAME > /dev/null && echo "   ✅ S3 access confirmed"

echo "   Testing DynamoDB access..."
aws dynamodb describe-table --table-name $TABLE_NAME > /dev/null && echo "   ✅ DynamoDB access confirmed"

echo "   Testing IAM role..."
aws iam get-role --role-name SeeHearAIEC2Role > /dev/null && echo "   ✅ IAM role confirmed"

echo ""
echo "🎉 SeeHearAI AWS Infrastructure Setup Complete!"
echo "=============================================="
echo "📋 Resources created:"
echo "   • S3 Bucket: $BUCKET_NAME"
echo "     └── Folders: audio-files/, video-frames/, models/, logs/, sessions/"
echo "   • DynamoDB Table: $TABLE_NAME"
echo "   • Security Group: $SECURITY_GROUP_ID (SeeHearAISG)"
echo "   • IAM Role: SeeHearAIEC2Role"
echo "   • Instance Profile: SeeHearAIProfile"
echo "   • Key Pair: $KEY_NAME.pem"
echo ""
echo "💾 Configuration files created:"
echo "   • seehearai-aws-config.env (deployment config)"
echo "   • .env.aws (application environment template)"
echo "🔑 SSH Key: $KEY_NAME.pem"
echo ""
echo "🔄 Next Steps:"
echo "   1. Copy your OpenAI API key to .env.aws"
echo "   2. Create EC2 instance for SeeHearAI"
echo "   3. Deploy your application code"
echo ""
echo "💰 Estimated monthly cost: $10-20 USD (Free tier eligible for 12 months)"
echo "🎯 SeeHearAI infrastructure ready for EC2 deployment!"
echo ""
echo "📊 Resource Summary:"
echo "   Project: SeeHearAI"
echo "   Bucket: s3://$BUCKET_NAME"
echo "   Table: $TABLE_NAME"
echo "   Region: $REGION"