#!/bin/bash
# build-and-deploy.sh - Build and deploy containers to AWS ECS
# Save as: build-and-deploy.sh

echo "🐳 Building and Deploying SeeHearAI Containers"
echo "=============================================="

# Load configuration
if [ -f "phase2-config.env" ]; then
    source phase2-config.env
    echo "✅ Configuration loaded"
else
    echo "❌ phase2-config.env not found. Run setup-docker-infrastructure.sh first"
    exit 1
fi

# Step 1: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

if [ $? -eq 0 ]; then
    echo "✅ ECR login successful"
else
    echo "❌ ECR login failed"
    exit 1
fi

# Step 2: Build Docker images
echo "🏗️ Building Docker images..."

# Build API image
echo "Building API service..."
docker build -f Dockerfile.api -t $ECR_API_REPO:latest .
docker tag $ECR_API_REPO:latest $ECR_API_REPO:v1.0

# Build Frontend image
echo "Building Frontend service..."
docker build -f Dockerfile.frontend -t $ECR_FRONTEND_REPO:latest .
docker tag $ECR_FRONTEND_REPO:latest $ECR_FRONTEND_REPO:v1.0

# Build WebSocket image
echo "Building WebSocket service..."
docker build -f Dockerfile.websocket -t $ECR_WEBSOCKET_REPO:latest .
docker tag $ECR_WEBSOCKET_REPO:latest $ECR_WEBSOCKET_REPO:v1.0

echo "✅ All images built successfully"

# Step 3: Push images to ECR
echo "📤 Pushing images to ECR..."

docker push $ECR_API_REPO:latest
docker push $ECR_API_REPO:v1.0

docker push $ECR_FRONTEND_REPO:latest  
docker push $ECR_FRONTEND_REPO:v1.0

docker push $ECR_WEBSOCKET_REPO:latest
docker push $ECR_WEBSOCKET_REPO:v1.0

echo "✅ All images pushed to ECR"

# Step 4: Create ECS Task Definitions
echo "📋 Creating ECS Task Definitions..."

# API Task Definition
cat > api-task-definition.json << EOF
{
  "family": "$PROJECT_NAME-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$TASK_EXECUTION_ROLE",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "$ECR_API_REPO:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "AWS_REGION", "value": "$AWS_REGION"},
        {"name": "S3_BUCKET", "value": "$S3_BUCKET"},
        {"name": "DYNAMODB_TABLE", "value": "$DYNAMODB_TABLE"},
        {"name": "TTS_QUEUE_URL", "value": "$TTS_QUEUE_URL"},
        {"name": "VISION_QUEUE_URL", "value": "$VISION_QUEUE_URL"},
        {"name": "ANALYTICS_QUEUE_URL", "value": "$ANALYTICS_QUEUE_URL"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$PROJECT_NAME/api",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Frontend Task Definition
cat > frontend-task-definition.json << EOF
{
  "family": "$PROJECT_NAME-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$TASK_EXECUTION_ROLE",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "$ECR_FRONTEND_REPO:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$PROJECT_NAME/frontend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# WebSocket Task Definition
cat > websocket-task-definition.json << EOF
{
  "family": "$PROJECT_NAME-websocket",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$TASK_EXECUTION_ROLE",
  "containerDefinitions": [
    {
      "name": "websocket",
      "image": "$ECR_WEBSOCKET_REPO:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "AWS_REGION", "value": "$AWS_REGION"},
        {"name": "TTS_QUEUE_URL", "value": "$TTS_QUEUE_URL"},
        {"name": "VISION_QUEUE_URL", "value": "$VISION_QUEUE_URL"},
        {"name": "ANALYTICS_QUEUE_URL", "value": "$ANALYTICS_QUEUE_URL"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$PROJECT_NAME/websocket",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

# Register task definitions
echo "📝 Registering task definitions..."
aws ecs register-task-definition --cli-input-json file://api-task-definition.json --region $AWS_REGION
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json --region $AWS_REGION
aws ecs register-task-definition --cli-input-json file://websocket-task-definition.json --region $AWS_REGION

echo "✅ Task definitions registered"

# Step 5: Create Target Groups
echo "🎯 Creating Target Groups..."

# API Target Group
API_TG_ARN=$(aws elbv2 create-target-group \
    --name $PROJECT_NAME-api-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null)

# Frontend Target Group
FRONTEND_TG_ARN=$(aws elbv2 create-target-group \
    --name $PROJECT_NAME-frontend-tg \
    --protocol HTTP \
    --port 80 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path / \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $AWS_REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null)

echo "✅ Target groups created"

# Step 6: Create ALB Listeners
echo "👂 Creating ALB Listeners..."

# Default listener (Frontend)
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN \
    --region $AWS_REGION 2>/dev/null

# API listener rule
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --query 'Listeners[0].ListenerArn' \
    --output text \
    --region $AWS_REGION)

aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 100 \
    --conditions Field=path-pattern,Values="/api/*","/health","/ws" \
    --actions Type=forward,TargetGroupArn=$API_TG_ARN \
    --region $AWS_REGION 2>/dev/null

echo "✅ ALB listeners configured"

# Step 7: Create ECS Services
echo "🚀 Creating ECS Services..."

# Get first subnet for service deployment
FIRST_SUBNET=$(echo $SUBNET_IDS | cut -d' ' -f1)

# API Service
aws ecs create-service \
    --cluster $ECS_CLUSTER \
    --service-name $PROJECT_NAME-api \
    --task-definition $PROJECT_NAME-api \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$FIRST_SUBNET],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$API_TG_ARN,containerName=api,containerPort=8000 \
    --region $AWS_REGION 2>/dev/null

# Frontend Service
aws ecs create-service \
    --cluster $ECS_CLUSTER \
    --service-name $PROJECT_NAME-frontend \
    --task-definition $PROJECT_NAME-frontend \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$FIRST_SUBNET],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=80 \
    --region $AWS_REGION 2>/dev/null

# WebSocket Service
aws ecs create-service \
    --cluster $ECS_CLUSTER \
    --service-name $PROJECT_NAME-websocket \
    --task-definition $PROJECT_NAME-websocket \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$FIRST_SUBNET],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION 2>/dev/null

echo "✅ ECS Services created"

# Step 8: Wait for services to be stable
echo "⏳ Waiting for services to be stable..."
echo "This may take 5-10 minutes..."

aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $PROJECT_NAME-api $PROJECT_NAME-frontend $PROJECT_NAME-websocket \
    --region $AWS_REGION

# Cleanup task definition files
rm -f *-task-definition.json

echo ""
echo "🎉 SeeHearAI Container Deployment Complete!"
echo "=========================================="
echo ""
echo "🌐 Your containerized SeeHearAI is available at:"
echo "   http://$ALB_DNS"
echo ""
echo "📊 Service Status:"
echo "   • API Service: Running on ECS Fargate"
echo "   • Frontend Service: Serving static files via nginx"  
echo "   • WebSocket Service: Handling real-time connections"
echo ""
echo "📋 Container Information:"
echo "   • ECR Repositories: $PROJECT_NAME/api, $PROJECT_NAME/frontend, $PROJECT_NAME/websocket"
echo "   • ECS Cluster: $ECS_CLUSTER"
echo "   • Load Balancer: $ALB_DNS"
echo ""
echo "🔄 Next Steps:"
echo "   1. Test your containerized application"
echo "   2. Set up Lambda functions for background processing"
echo "   3. Configure auto-scaling policies"
echo "   4. Set up CI/CD pipeline"
echo ""
echo "📊 Monitor your services:"
echo "   • ECS Console: https://console.aws.amazon.com/ecs/"
echo "   • CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/"
echo "   • Load Balancer: https://console.aws.amazon.com/ec2/v2/home#LoadBalancers"
echo ""
echo "🎊 Congratulations! Your SeeHearAI is now running on containers! 🐳"
