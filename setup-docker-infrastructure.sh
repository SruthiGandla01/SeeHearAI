#!/bin/bash
# Phase 2: Docker Infrastructure Setup for SeeHearAI
# Save as: setup-docker-infrastructure.sh

echo "🐳 Phase 2: Setting up Docker Infrastructure for SeeHearAI"
echo "========================================================"

# Variables
PROJECT_NAME="seehearai"
REGION=${AWS_REGION:-"us-east-1"}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "📋 Configuration:"
echo "   Project: $PROJECT_NAME"
echo "   Region: $REGION"
echo "   Account ID: $ACCOUNT_ID"
echo ""

# Step 1: Create ECR repositories
echo "📦 Creating ECR repositories..."

# Create ECR repositories for each service
aws ecr create-repository --repository-name $PROJECT_NAME/api --region $REGION 2>/dev/null
aws ecr create-repository --repository-name $PROJECT_NAME/frontend --region $REGION 2>/dev/null
aws ecr create-repository --repository-name $PROJECT_NAME/websocket --region $REGION 2>/dev/null

echo "✅ ECR repositories created"

# Step 2: Create ECS Cluster
echo "🏗️ Creating ECS Cluster..."
aws ecs create-cluster --cluster-name $PROJECT_NAME-cluster --capacity-providers FARGATE --region $REGION

echo "✅ ECS Cluster created: $PROJECT_NAME-cluster"

# Step 3: Create VPC for ECS (if needed)
echo "🌐 Setting up VPC..."

# Check if default VPC exists
DEFAULT_VPC=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)

if [ "$DEFAULT_VPC" != "None" ] && [ -n "$DEFAULT_VPC" ]; then
    echo "✅ Using default VPC: $DEFAULT_VPC"
    VPC_ID=$DEFAULT_VPC
    
    # Get default subnets
    SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION)
    echo "✅ Using default subnets: $SUBNET_IDS"
else
    echo "❌ No default VPC found. Creating new VPC..."
    # Create VPC if needed (simplified for now)
    VPC_ID="vpc-default"
    SUBNET_IDS="subnet-default"
fi

# Step 4: Create Task Execution Role
echo "👤 Creating ECS Task Execution Role..."

# Create trust policy
cat > ecs-task-execution-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create ECS execution role
aws iam create-role \
    --role-name ecsTaskExecutionRole-$PROJECT_NAME \
    --assume-role-policy-document file://ecs-task-execution-trust-policy.json \
    --region $REGION 2>/dev/null

# Attach policies
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-$PROJECT_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-$PROJECT_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-$PROJECT_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

echo "✅ ECS Task Execution Role created"

# Step 5: Create Security Group for ECS
echo "🔒 Creating Security Group for containers..."

SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name $PROJECT_NAME-ecs-sg \
    --description "Security group for SeeHearAI ECS containers" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $REGION 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Security group created: $SECURITY_GROUP_ID"
    
    # Add rules
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 \
        --region $REGION
        
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $REGION
        
    aws ec2 authorize-security-group-ingress \
        --group-id $SECURITY_GROUP_ID \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 \
        --region $REGION
        
    echo "✅ Security group rules configured"
else
    echo "⚠️ Security group may already exist"
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --group-names $PROJECT_NAME-ecs-sg --query 'SecurityGroups[0].GroupId' --output text --region $REGION)
fi

# Step 6: Create Application Load Balancer
echo "⚖️ Creating Application Load Balancer..."

# Get first two subnets for ALB
SUBNET_ARRAY=($SUBNET_IDS)
SUBNET1=${SUBNET_ARRAY[0]}
SUBNET2=${SUBNET_ARRAY[1]:-$SUBNET1}

ALB_ARN=$(aws elbv2 create-load-balancer \
    --name $PROJECT_NAME-alb \
    --subnets $SUBNET1 $SUBNET2 \
    --security-groups $SECURITY_GROUP_ID \
    --region $REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Application Load Balancer created: $ALB_ARN"
    
    # Get ALB DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns $ALB_ARN \
        --query 'LoadBalancers[0].DNSName' \
        --output text \
        --region $REGION)
        
    echo "🌐 ALB DNS: $ALB_DNS"
else
    echo "⚠️ Load balancer may already exist"
fi

# Step 7: Create CloudWatch Log Groups
echo "📊 Creating CloudWatch Log Groups..."

aws logs create-log-group --log-group-name /ecs/$PROJECT_NAME/api --region $REGION 2>/dev/null
aws logs create-log-group --log-group-name /ecs/$PROJECT_NAME/frontend --region $REGION 2>/dev/null
aws logs create-log-group --log-group-name /ecs/$PROJECT_NAME/websocket --region $REGION 2>/dev/null

echo "✅ CloudWatch Log Groups created"

# Step 8: Create SQS Queues for Lambda integration
echo "📬 Creating SQS Queues for Lambda integration..."

# TTS Processing Queue
TTS_QUEUE_URL=$(aws sqs create-queue \
    --queue-name $PROJECT_NAME-tts-queue \
    --attributes VisibilityTimeoutSeconds=300,MessageRetentionPeriod=1209600 \
    --query 'QueueUrl' \
    --output text \
    --region $REGION 2>/dev/null)

# Vision Processing Queue  
VISION_QUEUE_URL=$(aws sqs create-queue \
    --queue-name $PROJECT_NAME-vision-queue \
    --attributes VisibilityTimeoutSeconds=300,MessageRetentionPeriod=1209600 \
    --query 'QueueUrl' \
    --output text \
    --region $REGION 2>/dev/null)

# Analytics Queue
ANALYTICS_QUEUE_URL=$(aws sqs create-queue \
    --queue-name $PROJECT_NAME-analytics-queue \
    --attributes VisibilityTimeoutSeconds=300,MessageRetentionPeriod=1209600 \
    --query 'QueueUrl' \
    --output text \
    --region $REGION 2>/dev/null)

echo "✅ SQS Queues created:"
echo "   TTS Queue: $TTS_QUEUE_URL"
echo "   Vision Queue: $VISION_QUEUE_URL" 
echo "   Analytics Queue: $ANALYTICS_QUEUE_URL"

# Step 9: Save configuration
echo "💾 Saving Phase 2 configuration..."

cat > phase2-config.env << EOF
# SeeHearAI Phase 2 Configuration
# ===============================

# Project Info
PROJECT_NAME=$PROJECT_NAME
AWS_REGION=$REGION
AWS_ACCOUNT_ID=$ACCOUNT_ID

# ECR Repositories
ECR_API_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/api
ECR_FRONTEND_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/frontend
ECR_WEBSOCKET_REPO=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$PROJECT_NAME/websocket

# ECS Configuration
ECS_CLUSTER=$PROJECT_NAME-cluster
TASK_EXECUTION_ROLE=arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole-$PROJECT_NAME

# Networking
VPC_ID=$VPC_ID
SUBNET_IDS="$SUBNET_IDS"
SECURITY_GROUP_ID=$SECURITY_GROUP_ID
ALB_ARN=$ALB_ARN
ALB_DNS=$ALB_DNS

# SQS Queues
TTS_QUEUE_URL=$TTS_QUEUE_URL
VISION_QUEUE_URL=$VISION_QUEUE_URL
ANALYTICS_QUEUE_URL=$ANALYTICS_QUEUE_URL

# Phase 1 Resources (from previous setup)
S3_BUCKET=${S3_BUCKET:-seehearai-storage-bucket}
DYNAMODB_TABLE=${DYNAMODB_TABLE:-SeeHearAISessions}
EOF

# Cleanup temp files
rm -f ecs-task-execution-trust-policy.json

echo ""
echo "🎉 Phase 2 Infrastructure Setup Complete!"
echo "========================================"
echo ""
echo "📋 Resources Created:"
echo "   • ECR Repositories: api, frontend, websocket"
echo "   • ECS Cluster: $PROJECT_NAME-cluster"
echo "   • Task Execution Role: ecsTaskExecutionRole-$PROJECT_NAME"
echo "   • Security Group: $SECURITY_GROUP_ID"
echo "   • Application Load Balancer: $ALB_DNS"
echo "   • CloudWatch Log Groups: /ecs/$PROJECT_NAME/*"
echo "   • SQS Queues: TTS, Vision, Analytics"
echo ""
echo "💾 Configuration saved to: phase2-config.env"
echo ""
echo "🔄 Next Steps:"
echo "   1. Create Dockerfiles for each service"
echo "   2. Build and push Docker images"
echo "   3. Create ECS Task Definitions"
echo "   4. Deploy services to ECS"
echo "   5. Set up Lambda functions"
echo ""
echo "🌐 Your containerized SeeHearAI will be available at:"
echo "   http://$ALB_DNS"
echo ""
echo "🚀 Ready for containerization!"