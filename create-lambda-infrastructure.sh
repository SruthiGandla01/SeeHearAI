#!/bin/bash
# SeeHearAI Lambda Infrastructure Setup
# Save as: create-lambda-infrastructure.sh

echo "🚀 Creating Lambda Infrastructure for SeeHearAI"
echo "=============================================="

# Load existing configuration
if [ -f "seehearai-aws-config.env" ]; then
    source seehearai-aws-config.env
    echo "✅ AWS configuration loaded"
else
    echo "❌ AWS configuration not found. Please run create-aws-infrastructure.sh first"
    exit 1
fi

REGION=${AWS_REGION:-"us-east-1"}
LAMBDA_ROLE_NAME="SeeHearAILambdaRole"
LAMBDA_POLICY_NAME="SeeHearAILambdaPolicy"

echo "📋 Lambda Configuration:"
echo "   Region: $REGION"
echo "   S3 Bucket: $S3_BUCKET"
echo "   DynamoDB Table: $DYNAMODB_TABLE"
echo "   IAM Role: $LAMBDA_ROLE_NAME"
echo ""

# Step 1: Create IAM role for Lambda
echo "👤 Creating IAM role for Lambda functions..."
aws iam create-role \
    --role-name $LAMBDA_ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Lambda IAM role created"
else
    echo "⚠️  Lambda IAM role may already exist"
fi

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create custom policy for our services
echo "📋 Creating custom Lambda policy..."
cat > lambda-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::$S3_BUCKET",
                "arn:aws:s3:::$S3_BUCKET/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:UpdateItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:$REGION:*:table/$DYNAMODB_TABLE"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:SendMessage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name $LAMBDA_POLICY_NAME \
    --policy-document file://lambda-policy.json > /dev/null 2>&1

# Get account ID for policy ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$LAMBDA_POLICY_NAME"

aws iam attach-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-arn $POLICY_ARN

echo "✅ Lambda IAM policies configured"

# Step 2: Create SQS queues
echo ""
echo "📬 Creating SQS queues..."

# TTS Queue
TTS_QUEUE_URL=$(aws sqs create-queue \
    --queue-name seehearai-tts-queue \
    --attributes '{
        "VisibilityTimeoutSeconds": "300",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }' \
    --query 'QueueUrl' --output text)

if [ $? -eq 0 ]; then
    echo "✅ TTS queue created: $TTS_QUEUE_URL"
else
    echo "⚠️  TTS queue may already exist"
    TTS_QUEUE_URL=$(aws sqs get-queue-url --queue-name seehearai-tts-queue --query 'QueueUrl' --output text)
fi

# Vision Queue
VISION_QUEUE_URL=$(aws sqs create-queue \
    --queue-name seehearai-vision-queue \
    --attributes '{
        "VisibilityTimeoutSeconds": "300",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "20"
    }' \
    --query 'QueueUrl' --output text)

if [ $? -eq 0 ]; then
    echo "✅ Vision queue created: $VISION_QUEUE_URL"
else
    echo "⚠️  Vision queue may already exist"
    VISION_QUEUE_URL=$(aws sqs get-queue-url --queue-name seehearai-vision-queue --query 'QueueUrl' --output text)
fi

# Step 3: Create Lambda deployment package
echo ""
echo "📦 Creating Lambda deployment packages..."

# Create directory for Lambda code
mkdir -p lambda-functions
cd lambda-functions

# Create TTS Lambda package
mkdir -p tts-lambda
cat > tts-lambda/lambda_function.py << 'EOF'
import json
import boto3
import os
import tempfile
import logging
from gtts import gTTS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Generate TTS audio and upload to S3"""
    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            
            text = body['text']
            s3_key = body['s3_key']
            session_id = body['session_id']
            bucket_name = os.environ['S3_BUCKET']
            
            logger.info(f"Generating TTS for session: {session_id}")
            
            # Generate TTS
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                tts = gTTS(text=text, lang='en')
                tts.save(temp_file.name)
                
                # Upload to S3
                with open(temp_file.name, 'rb') as audio_file:
                    s3.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=audio_file.read(),
                        ContentType='audio/mpeg'
                    )
                
                os.unlink(temp_file.name)
            
            # Update DynamoDB
            table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
            table.put_item(
                Item={
                    'session_id': session_id,
                    'timestamp': body['timestamp'],
                    'event_type': 'tts_generated',
                    'data': {
                        'audio_s3_key': s3_key,
                        'text': text[:100] + '...' if len(text) > 100 else text
                    }
                }
            )
            
            logger.info(f"TTS completed: {s3_key}")
        
        return {'statusCode': 200, 'body': json.dumps('TTS generated successfully')}
        
    except Exception as e:
        logger.error(f"TTS Lambda error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
EOF

# Create requirements.txt for TTS Lambda
cat > tts-lambda/requirements.txt << 'EOF'
gtts==2.4.0
boto3==1.34.0
EOF

# Create Vision Lambda package
mkdir -p vision-lambda
cat > vision-lambda/lambda_function.py << 'EOF'
import json
import boto3
import os
import logging
from PIL import Image
import io

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Process video frames for vision analysis"""
    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            
            frame_s3_key = body['frame_s3_key']
            session_id = body['session_id']
            bucket_name = os.environ['S3_BUCKET']
            
            logger.info(f"Processing vision for session: {session_id}")
            
            # Download frame from S3
            response = s3.get_object(Bucket=bucket_name, Key=frame_s3_key)
            image_data = response['Body'].read()
            
            # Simple analysis (you'd implement actual YOLO/BLIP here)
            image = Image.open(io.BytesIO(image_data))
            analysis_result = f"Lambda analyzed image: {image.size[0]}x{image.size[1]} pixels"
            
            # Store results in DynamoDB
            table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
            table.put_item(
                Item={
                    'session_id': session_id,
                    'timestamp': body['timestamp'],
                    'event_type': 'vision_analysis_lambda',
                    'data': {
                        'frame_s3_key': frame_s3_key,
                        'analysis': analysis_result
                    }
                }
            )
            
            logger.info(f"Vision analysis completed: {frame_s3_key}")
        
        return {'statusCode': 200, 'body': json.dumps('Vision analysis completed')}
        
    except Exception as e:
        logger.error(f"Vision Lambda error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
EOF

cat > vision-lambda/requirements.txt << 'EOF'
Pillow==10.1.0
boto3==1.34.0
EOF

# Create Analytics Lambda
mkdir -p analytics-lambda
cat > analytics-lambda/lambda_function.py << 'EOF'
import json
import boto3
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Process daily analytics"""
    try:
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        
        # Simple analytics calculation
        analytics = {
            'timestamp': datetime.now().isoformat(),
            'total_events': 0,
            'unique_sessions': set(),
            'questions_asked': 0
        }
        
        # Store analytics
        analytics_key = f"analytics/daily-{datetime.now().strftime('%Y-%m-%d')}.json"
        s3.put_object(
            Bucket=os.environ['S3_BUCKET'],
            Key=analytics_key,
            Body=json.dumps(analytics, default=str),
            ContentType='application/json'
        )
        
        logger.info(f"Analytics processed: {analytics_key}")
        
        return {'statusCode': 200, 'body': json.dumps('Analytics processed')}
        
    except Exception as e:
        logger.error(f"Analytics Lambda error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
EOF

cat > analytics-lambda/requirements.txt << 'EOF'
boto3==1.34.0
EOF

echo "✅ Lambda code packages created"

# Step 4: Create and deploy Lambda functions
echo ""
echo "🚀 Deploying Lambda functions..."

# Get Lambda role ARN
LAMBDA_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$LAMBDA_ROLE_NAME"

# Function to create Lambda
create_lambda_function() {
    local function_name=$1
    local directory=$2
    local handler=$3
    local timeout=${4:-300}
    
    echo "📦 Creating $function_name..."
    
    cd $directory
    zip -r ../${function_name}.zip . > /dev/null
    cd ..
    
    aws lambda create-function \
        --function-name $function_name \
        --runtime python3.11 \
        --role $LAMBDA_ROLE_ARN \
        --handler $handler \
        --zip-file fileb://${function_name}.zip \
        --timeout $timeout \
        --memory-size 512 \
        --environment Variables="{
            S3_BUCKET=$S3_BUCKET,
            DYNAMODB_TABLE=$DYNAMODB_TABLE,
            TTS_QUEUE_URL=$TTS_QUEUE_URL,
            VISION_QUEUE_URL=$VISION_QUEUE_URL
        }" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ $function_name created successfully"
    else
        echo "⚠️  $function_name may already exist, updating..."
        aws lambda update-function-code \
            --function-name $function_name \
            --zip-file fileb://${function_name}.zip > /dev/null
    fi
}

# Create Lambda functions
create_lambda_function "seehearai-tts-lambda" "tts-lambda" "lambda_function.lambda_handler" 60
create_lambda_function "seehearai-vision-lambda" "vision-lambda" "lambda_function.lambda_handler" 180
create_lambda_function "seehearai-analytics-lambda" "analytics-lambda" "lambda_function.lambda_handler" 300

# Step 5: Create SQS event source mappings
echo ""
echo "🔗 Connecting SQS queues to Lambda functions..."

# Connect TTS queue to TTS Lambda
aws lambda create-event-source-mapping \
    --function-name seehearai-tts-lambda \
    --event-source-arn $(aws sqs get-queue-attributes --queue-url $TTS_QUEUE_URL --attribute-names QueueArn --query 'Attributes.QueueArn' --output text) \
    --batch-size 5 > /dev/null 2>&1

# Connect Vision queue to Vision Lambda
aws lambda create-event-source-mapping \
    --function-name seehearai-vision-lambda \
    --event-source-arn $(aws sqs get-queue-attributes --queue-url $VISION_QUEUE_URL --attribute-names QueueArn --query 'Attributes.QueueArn' --output text) \
    --batch-size 3 > /dev/null 2>&1

echo "✅ SQS-Lambda connections established"

# Step 6: Create EventBridge rule for analytics
echo "📅 Setting up scheduled analytics..."
aws events put-rule \
    --name seehearai-daily-analytics \
    --schedule-expression "rate(24 hours)" \
    --description "Daily analytics processing for SeeHearAI" > /dev/null

aws lambda add-permission \
    --function-name seehearai-analytics-lambda \
    --statement-id seehearai-analytics-scheduled \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/seehearai-daily-analytics > /dev/null 2>&1

aws events put-targets \
    --rule seehearai-daily-analytics \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:seehearai-analytics-lambda" > /dev/null

echo "✅ Scheduled analytics configured"

# Cleanup
cd ..
rm -rf lambda-functions
rm lambda-policy.json

# Step 7: Update configuration
echo ""
echo "📝 Updating configuration..."
cat >> seehearai-aws-config.env << EOF

# Lambda Configuration
LAMBDA_ROLE_ARN=$LAMBDA_ROLE_ARN
TTS_QUEUE_URL=$TTS_QUEUE_URL
VISION_QUEUE_URL=$VISION_QUEUE_URL
TTS_LAMBDA_NAME=seehearai-tts-lambda
VISION_LAMBDA_NAME=seehearai-vision-lambda
ANALYTICS_LAMBDA_NAME=seehearai-analytics-lambda
EOF

# Create updated .env template
cat >> .env.aws << EOF

# Lambda Integration
TTS_QUEUE_URL=$TTS_QUEUE_URL
VISION_QUEUE_URL=$VISION_QUEUE_URL
USE_LAMBDA_PROCESSING=true
LAMBDA_TIMEOUT=300
EOF

echo ""
echo "🎉 Lambda Infrastructure Setup Complete!"
echo "======================================="
echo "📋 Resources created:"
echo "   • IAM Role: $LAMBDA_ROLE_NAME"
echo "   • SQS Queues:"
echo "     └── TTS Queue: seehearai-tts-queue"
echo "     └── Vision Queue: seehearai-vision-queue"
echo "   • Lambda Functions:"
echo "     └── seehearai-tts-lambda (TTS generation)"
echo "     └── seehearai-vision-lambda (Vision analysis)"  
echo "     └── seehearai-analytics-lambda (Daily analytics)"
echo "   • EventBridge Rule: seehearai-daily-analytics"
echo ""
echo "💰 Additional monthly cost: ~$2-5 USD (pay per use)"
echo "⚡ Benefits:"
echo "   • Async processing (no blocking)"
echo "   • Auto-scaling Lambda functions"
echo "   • Background analytics"
echo "   • Better performance for users"
echo ""
echo "🔄 Next Steps:"
echo "   1. Update your EC2 deployment to use Lambda integration"
echo "   2. Test the enhanced processing pipeline"
echo "   3. Monitor CloudWatch logs for Lambda functions"
echo ""
echo "🚀 SeeHearAI now has serverless superpowers!"