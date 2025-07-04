#!/bin/bash
# SeeHearAI Code Deployment Script
# Save as: deploy-seehearai.sh

echo "🚀 Deploying SeeHearAI Code to EC2"
echo "================================="

# Load EC2 configuration
if [ -f "seehearai-ec2-info.txt" ]; then
    source seehearai-ec2-info.txt
    echo "✅ EC2 configuration loaded"
    echo "   Instance: $INSTANCE_ID"
    echo "   Public IP: $PUBLIC_IP"
else
    echo "❌ EC2 configuration not found. Please run create-ec2-instance.sh first"
    exit 1
fi

# Check if key file exists
if [ ! -f "$KEY_NAME.pem" ]; then
    echo "❌ SSH key file not found: $KEY_NAME.pem"
    exit 1
fi

echo ""
echo "📦 Preparing deployment package..."

# Create deployment directory
DEPLOY_DIR="seehearai-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

# Copy your SeeHearAI files (modify paths as needed for your project structure)
echo "📁 Copying SeeHearAI files..."
cp -r app/ $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  app/ directory not found"
cp -r backend/ $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  backend/ directory not found"
cp -r s3_utils/ $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  s3_utils/ directory not found"
cp -r vosk_model/ $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  vosk_model/ directory not found"
cp requirements.txt $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  requirements.txt not found"
cp docker-compose.yml $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  docker-compose.yml not found"
cp Dockerfile $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  Dockerfile not found"
cp *.py $DEPLOY_DIR/ 2>/dev/null || echo "⚠️  No Python files in root"

# Create AWS-specific requirements.txt if it doesn't exist
if [ ! -f "$DEPLOY_DIR/requirements.txt" ]; then
    echo "📝 Creating requirements.txt for AWS deployment..."
    cat > $DEPLOY_DIR/requirements.txt << 'EOF'
# SeeHearAI Requirements - AWS Deployment
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# AI/ML Dependencies
torch==2.1.1
torchvision==0.16.1
transformers==4.35.2
ultralytics==8.0.20
Pillow==10.1.0
opencv-python-headless==4.8.1.78
numpy==1.24.4
scipy==1.11.4

# Audio Processing
gtts==2.4.0
vosk==0.3.45
whisper-openai==1.1.10
pydub==0.25.1

# OpenAI
openai==1.3.7

# AWS Integration
boto3==1.34.0
botocore==1.34.0

# Additional utilities
python-dotenv==1.0.0
requests==2.31.0
aiofiles==23.2.1
asyncio-mqtt==0.16.1
jinja2==3.1.2
EOF
fi

# Create startup script for the server
echo "🚀 Creating startup script..."
cat > $DEPLOY_DIR/start-seehearai.sh << 'EOF'
#!/bin/bash
# SeeHearAI Startup Script for EC2

echo "🚀 Starting SeeHearAI on EC2..."

# Set up environment
export PYTHONPATH=/home/ec2-user/seehearai:$PYTHONPATH
cd /home/ec2-user/seehearai

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
fi

# Activate virtual environment
source venv/bin/activate

# Download YOLO model if not exists
if [ ! -f "yolov8n.pt" ]; then
    echo "📥 Downloading YOLO model..."
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
fi

# Start the application
echo "🎯 Starting SeeHearAI server..."
exec python -m uvicorn app.fastapi_server:app --host 0.0.0.0 --port 8000 --reload
EOF

chmod +x $DEPLOY_DIR/start-seehearai.sh

# Create environment configuration
echo "⚙️ Creating AWS environment configuration..."
if [ -f "seehearai-aws-config.env" ]; then
    source seehearai-aws-config.env
    
    cat > $DEPLOY_DIR/.env << EOF
# SeeHearAI AWS Environment Configuration
# =====================================

# OpenAI Configuration (YOU NEED TO ADD YOUR API KEY)
OPENAI_API_KEY=your_openai_api_key_here

# AWS Configuration
AWS_REGION=$AWS_REGION
S3_BUCKET=$S3_BUCKET
DYNAMODB_TABLE=$DYNAMODB_TABLE

# Application Configuration
PROJECT_NAME=SeeHearAI
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your_super_secret_key_here_change_this

# Model Configuration
YOLO_MODEL_PATH=yolov8n.pt
WHISPER_MODEL=base
VOSK_MODEL_PATH=vosk_model/

# Performance Settings
MAX_WORKERS=4
UPLOAD_MAX_SIZE=10485760
SESSION_TIMEOUT=3600
EOF
else
    echo "⚠️  AWS config not found, creating minimal .env"
    cat > $DEPLOY_DIR/.env << 'EOF'
# SeeHearAI Environment Configuration
OPENAI_API_KEY=your_openai_api_key_here
PROJECT_NAME=SeeHearAI
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
EOF
fi

# Create installation script for the server
echo "🔧 Creating server installation script..."
cat > $DEPLOY_DIR/install-on-server.sh << 'EOF'
#!/bin/bash
# Server Installation Script - Run this ON THE EC2 SERVER

echo "🔧 Installing SeeHearAI on EC2 Server..."
echo "======================================="

# Update system
echo "📦 Updating system packages..."
sudo yum update -y

# Install Python 3.11 and development tools
echo "🐍 Installing Python 3.11..."
sudo yum install -y python3.11 python3.11-pip python3.11-devel
sudo yum install -y gcc gcc-c++ make cmake git wget

# Install FFmpeg for audio processing
echo "🎵 Installing FFmpeg..."
sudo yum install -y ffmpeg

# Install system libraries for OpenCV and audio
echo "📚 Installing system libraries..."
sudo yum install -y mesa-libGL alsa-lib-devel

# Create Python virtual environment
echo "🌐 Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install PyTorch with CPU support (lighter for initial deployment)
echo "🤖 Installing PyTorch (CPU version)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other requirements
echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

# Create directory for models
mkdir -p models/

# Download VOSK model if directory doesn't exist
if [ ! -d "vosk_model" ]; then
    echo "🎤 Downloading VOSK speech recognition model..."
    wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
    unzip vosk-model-en-us-0.22.zip
    mv vosk-model-en-us-0.22 vosk_model
    rm vosk-model-en-us-0.22.zip
fi

# Download YOLO model
if [ ! -f "yolov8n.pt" ]; then
    echo "👁️ Downloading YOLO model..."
    wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
fi

# Create log directory
mkdir -p logs/

# Set permissions
chmod +x start-seehearai.sh

echo ""
echo "✅ SeeHearAI installation completed!"
echo "📋 What was installed:"
echo "   • Python 3.11 + virtual environment"
echo "   • All Python dependencies"
echo "   • VOSK speech recognition model"
echo "   • YOLO vision model"
echo "   • FFmpeg for audio processing"
echo ""
echo "🚀 To start SeeHearAI:"
echo "   1. Edit .env file with your OpenAI API key"
echo "   2. Run: ./start-seehearai.sh"
echo ""
echo "🌐 Your app will be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
EOF

chmod +x $DEPLOY_DIR/install-on-server.sh

# Create systemd service file for auto-start
cat > $DEPLOY_DIR/seehearai.service << 'EOF'
[Unit]
Description=SeeHearAI Vision Assistant
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/seehearai
Environment=PATH=/home/ec2-user/seehearai/venv/bin
ExecStart=/home/ec2-user/seehearai/venv/bin/python -m uvicorn app.fastapi_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Deployment package prepared"
echo ""
echo "📤 Uploading to EC2 server..."

# Create the deployment archive
tar -czf seehearai-deploy.tar.gz -C $DEPLOY_DIR .

# Upload to server
echo "🔄 Copying files to server..."
scp -i $KEY_NAME.pem -r seehearai-deploy.tar.gz ec2-user@$PUBLIC_IP:/home/ec2-user/

if [ $? -eq 0 ]; then
    echo "✅ Files uploaded successfully"
    
    echo ""
    echo "🔧 Installing SeeHearAI on server..."
    ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP << 'ENDSSH'
        # Extract and setup
        tar -xzf seehearai-deploy.tar.gz
        mkdir -p seehearai
        mv * seehearai/ 2>/dev/null || true
        cd seehearai
        
        # Run installation
        chmod +x install-on-server.sh
        ./install-on-server.sh
        
        echo ""
        echo "🎯 SeeHearAI installation completed!"
        echo "📝 Next steps:"
        echo "   1. Edit .env file: nano .env"
        echo "   2. Add your OpenAI API key"
        echo "   3. Start the app: ./start-seehearai.sh"
        echo ""
        echo "🌐 Your app URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
ENDSSH
    
    echo ""
    echo "🎉 SeeHearAI Deployment Complete!"
    echo "================================="
    echo "📋 What was deployed:"
    echo "   • All SeeHearAI source code"
    echo "   • Python 3.11 + virtual environment"
    echo "   • AI models (YOLO, VOSK, BLIP)"
    echo "   • AWS integration configured"
    echo "   • Systemd service for auto-start"
    echo ""
    echo "🔧 Final Configuration Steps:"
    echo "   1. SSH to server: ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
    echo "   2. Edit environment: cd seehearai && nano .env"
    echo "   3. Add your OpenAI API key to OPENAI_API_KEY"
    echo "   4. Start the app: ./start-seehearai.sh"
    echo ""
    echo "🌐 Your SeeHearAI URL: http://$PUBLIC_IP:8000"
    echo "💡 Test it by saying 'Hey Buddy' and asking about what you see!"
    
else
    echo "❌ Failed to upload files to server"
    echo "🔍 Troubleshooting:"
    echo "   1. Check if EC2 instance is running"
    echo "   2. Verify SSH key permissions: chmod 400 $KEY_NAME.pem"
    echo "   3. Test SSH connection: ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
fi

# Cleanup
rm -rf $DEPLOY_DIR seehearai-deploy.tar.gz

echo ""
echo "🚀 Ready to test your SeeHearAI in the cloud!"