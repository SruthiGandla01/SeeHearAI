#!/bin/bash
# SeeHearAI Environment Setup Helper
# Run this on your EC2 server after deployment

echo "🔧 SeeHearAI Environment Configuration"
echo "====================================="

# Check if we're in the right directory
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Make sure you're in the seehearai directory"
    exit 1
fi

echo "📋 Current directory: $(pwd)"
echo "✅ Found .env file"
echo ""

# Load AWS configuration if available
if [ -f "../seehearai-aws-config.env" ]; then
    source ../seehearai-aws-config.env
    echo "✅ AWS configuration loaded"
else
    echo "⚠️  AWS configuration not found, will use manual entry"
fi

echo ""
echo "🔑 Let's configure your environment variables..."
echo ""

# Function to prompt for input with default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        if [ -z "$input" ]; then
            input="$default"
        fi
    else
        read -p "$prompt: " input
        while [ -z "$input" ]; do
            echo "This field is required!"
            read -p "$prompt: " input
        done
    fi
    
    eval "$var_name='$input'"
}

# Get OpenAI API Key
echo "🤖 OpenAI Configuration"
echo "----------------------"
current_openai_key=$(grep OPENAI_API_KEY .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ "$current_openai_key" == "your_openai_api_key_here" ] || [ -z "$current_openai_key" ]; then
    echo "You need an OpenAI API key to use GPT-4o for vision analysis."
    echo "Get one at: https://platform.openai.com/api-keys"
    prompt_with_default "Enter your OpenAI API key" "" OPENAI_API_KEY
else
    echo "✅ OpenAI API key already configured: ${current_openai_key:0:8}..."
    read -p "Do you want to change it? (y/N): " change_key
    if [[ $change_key =~ ^[Yy]$ ]]; then
        prompt_with_default "Enter your new OpenAI API key" "" OPENAI_API_KEY
    else
        OPENAI_API_KEY="$current_openai_key"
    fi
fi

echo ""
echo "☁️ AWS Configuration"
echo "-------------------"

# AWS Region
prompt_with_default "AWS Region" "$AWS_REGION" AWS_REGION

# S3 Bucket
prompt_with_default "S3 Bucket Name" "$S3_BUCKET" S3_BUCKET

# DynamoDB Table
prompt_with_default "DynamoDB Table Name" "$DYNAMODB_TABLE" DYNAMODB_TABLE

echo ""
echo "🔒 Security Configuration"
echo "------------------------"

# Generate secret key if needed
current_secret=$(grep SECRET_KEY .env | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ "$current_secret" == "your_super_secret_key_here_change_this" ] || [ -z "$current_secret" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    echo "✅ Generated new secret key"
else
    SECRET_KEY="$current_secret"
    echo "✅ Using existing secret key"
fi

echo ""
echo "⚙️ Performance Configuration"
echo "---------------------------"

# Get system info
CPU_COUNT=$(nproc)
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')

echo "System detected: ${CPU_COUNT} CPUs, ${MEMORY_GB}GB RAM"

if [ $CPU_COUNT -ge 4 ] && [ $MEMORY_GB -ge 7 ]; then
    MAX_WORKERS=4
    echo "✅ Setting MAX_WORKERS to 4 (good performance)"
elif [ $CPU_COUNT -ge 2 ] && [ $MEMORY_GB -ge 3 ]; then
    MAX_WORKERS=2
    echo "✅ Setting MAX_WORKERS to 2 (moderate performance)"
else
    MAX_WORKERS=1
    echo "⚠️  Setting MAX_WORKERS to 1 (basic performance)"
fi

echo ""
echo "📄 Updating .env file..."

# Create backup
cp .env .env.backup.$(date +%s)

# Update .env file
cat > .env << EOF
# SeeHearAI Environment Configuration - AWS Production
# ===================================================

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_API_KEY

# AWS Configuration
AWS_REGION=$AWS_REGION
S3_BUCKET=$S3_BUCKET
DYNAMODB_TABLE=$DYNAMODB_TABLE

# Optional: AWS Polly for better TTS (requires additional setup)
USE_AWS_POLLY=false

# Application Configuration
PROJECT_NAME=SeeHearAI
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=$SECRET_KEY

# Model Configuration
YOLO_MODEL_PATH=yolov8n.pt
WHISPER_MODEL=base
VOSK_MODEL_PATH=vosk_model/

# Performance Settings
MAX_WORKERS=$MAX_WORKERS
UPLOAD_MAX_SIZE=10485760
SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
EOF

echo "✅ Environment configuration updated!"
echo ""

# Test AWS connectivity
echo "🧪 Testing AWS connectivity..."
echo ""

# Test AWS CLI
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI available"
    
    # Test S3
    echo -n "Testing S3 access... "
    if aws s3 ls s3://$S3_BUCKET > /dev/null 2>&1; then
        echo "✅ S3 accessible"
    else
        echo "❌ S3 access failed"
        echo "   Make sure your EC2 instance has the right IAM role"
    fi
    
    # Test DynamoDB
    echo -n "Testing DynamoDB access... "
    if aws dynamodb describe-table --table-name $DYNAMODB_TABLE > /dev/null 2>&1; then
        echo "✅ DynamoDB accessible"
    else
        echo "❌ DynamoDB access failed"
        echo "   Make sure your EC2 instance has the right IAM role"
    fi
else
    echo "⚠️  AWS CLI not found, skipping connectivity test"
fi

echo ""
echo "🐍 Testing Python environment..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found"
fi

# Test Python imports
echo -n "Testing Python dependencies... "
python3 -c "
import fastapi
import torch
import transformers
import ultralytics
import boto3
import openai
print('✅ All dependencies available')
" 2>/dev/null || echo "❌ Some dependencies missing"

echo ""
echo "🎉 SeeHearAI Environment Setup Complete!"
echo "======================================="
echo ""
echo "📋 Configuration Summary:"
echo "   • OpenAI API Key: Configured"
echo "   • AWS Region: $AWS_REGION"
echo "   • S3 Bucket: $S3_BUCKET"
echo "   • DynamoDB Table: $DYNAMODB_TABLE"
echo "   • Max Workers: $MAX_WORKERS"
echo "   • Environment: Production"
echo ""
echo "🚀 Ready to start SeeHearAI!"
echo ""
echo "🔄 Next steps:"
echo "   1. Start the application: ./start-seehearai.sh"
echo "   2. Test the health endpoint: curl http://localhost:8000/health"
echo "   3. Open in browser: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
echo ""
echo "📊 Monitor logs with: tail -f logs/seehearai.log"
echo "🛑 Stop the app with: Ctrl+C"
echo ""
echo "💡 Troubleshooting:"
echo "   • Check logs: tail -f logs/*.log"
echo "   • Test AWS: aws s3 ls s3://$S3_BUCKET"
echo "   • Test OpenAI: python3 -c \"import openai; print('OpenAI ready')\""
echo ""
echo "🌐 Your SeeHearAI is ready for the cloud!"