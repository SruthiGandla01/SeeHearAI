#!/bin/bash
# SeeHearAI EC2 User Data Script - Auto Setup

echo "🚀 Starting SeeHearAI Server Setup..." > /var/log/seehearai-setup.log

# Update system
yum update -y >> /var/log/seehearai-setup.log 2>&1

# Install Python 3.11 and pip
yum install -y python3.11 python3.11-pip git >> /var/log/seehearai-setup.log 2>&1

# Install system dependencies for AI models
yum install -y gcc gcc-c++ make >> /var/log/seehearai-setup.log 2>&1
yum install -y ffmpeg >> /var/log/seehearai-setup.log 2>&1

# Create application directory
mkdir -p /home/ec2-user/seehearai
chown ec2-user:ec2-user /home/ec2-user/seehearai

# Install AWS CLI v2 (if not already installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install >> /var/log/seehearai-setup.log 2>&1

# Create virtual environment
su - ec2-user -c "cd /home/ec2-user/seehearai && python3.11 -m venv venv" >> /var/log/seehearai-setup.log 2>&1

# Create systemd service for SeeHearAI
cat > /etc/systemd/system/seehearai.service << 'EOF'
[Unit]
Description=SeeHearAI Vision Assistant
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/seehearai
Environment=PATH=/home/ec2-user/seehearai/venv/bin
ExecStart=/home/ec2-user/seehearai/venv/bin/uvicorn app.fastapi_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl enable seehearai >> /var/log/seehearai-setup.log 2>&1

# Create deployment script
cat > /home/ec2-user/deploy-seehearai.sh << 'EOF'
#!/bin/bash
# SeeHearAI Deployment Script

echo "📦 Deploying SeeHearAI Application..."

cd /home/ec2-user/seehearai

# Activate virtual environment
source venv/bin/activate

# Install/upgrade requirements
pip install --upgrade pip
pip install fastapi uvicorn websockets python-multipart python-dotenv
pip install openai transformers torch torchvision ultralytics
pip install gtts opencv-python-headless Pillow numpy requests
pip install boto3

# Download AI models (this may take a while)
echo "📥 Downloading AI models..."
python3 -c "
import torch
from ultralytics import YOLO
from transformers import BlipProcessor, BlipForConditionalGeneration

print('Downloading YOLO...')
YOLO('yolov8n.pt')

print('Downloading BLIP...')
BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')

print('Models downloaded successfully!')
"

echo "✅ SeeHearAI deployment ready!"
echo "🔄 Upload your code and start the service"
EOF

chmod +x /home/ec2-user/deploy-seehearai.sh
chown ec2-user:ec2-user /home/ec2-user/deploy-seehearai.sh

echo "✅ SeeHearAI server setup complete!" >> /var/log/seehearai-setup.log
echo "📝 Check /var/log/seehearai-setup.log for details" >> /var/log/seehearai-setup.log

# Create welcome message
cat > /home/ec2-user/README-SEEHEARAI.md << 'EOF'
# 🚀 SeeHearAI Server Ready!

## What's Installed:
- Python 3.11 + pip
- Virtual environment at `/home/ec2-user/seehearai/venv`
- AWS CLI v2
- System dependencies for AI models

## Next Steps:
1. Upload your SeeHearAI code to `/home/ec2-user/seehearai/`
2. Run: `./deploy-seehearai.sh` to install dependencies
3. Start service: `sudo systemctl start seehearai`

## Useful Commands:
- Check logs: `sudo journalctl -u seehearai -f`
- Check setup log: `cat /var/log/seehearai-setup.log`
- Restart service: `sudo systemctl restart seehearai`

## Your SeeHearAI will be available at:
http://YOUR_EC2_PUBLIC_IP:8000
EOF

chown ec2-user:ec2-user /home/ec2-user/README-SEEHEARAI.md