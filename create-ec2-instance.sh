#!/bin/bash
# SeeHearAI EC2 Instance Creation Script - Base64 Version
# Save as: create-ec2-instance.sh

echo "🖥️ Creating EC2 Instance for SeeHearAI (Base64 Method)"
echo "===================================================="

# Load configuration from previous step
if [ -f "seehearai-aws-config.env" ]; then
    source seehearai-aws-config.env
    echo "✅ Configuration loaded"
else
    echo "❌ Configuration file not found. Please run create-aws-infrastructure.sh first"
    exit 1
fi

# Check if user-data.sh exists
if [ ! -f "user-data.sh" ]; then
    echo "❌ user-data.sh file not found. Please create it first."
    exit 1
fi

# Variables
INSTANCE_TYPE="t3.medium"  # Good for AI workloads, 2 vCPU, 4GB RAM
AMI_ID="ami-0c02fb55956c7d316"  # Amazon Linux 2023 (latest)
REGION="us-east-1"

echo "📋 EC2 Configuration:"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   AMI: $AMI_ID (Amazon Linux 2023)"
echo "   Security Group: $SECURITY_GROUP_ID"
echo "   Key Pair: $KEY_NAME"
echo "   IAM Profile: $IAM_INSTANCE_PROFILE"
echo "   User Data: user-data.sh (base64 encoded)"
echo ""

# Verify user-data.sh content
if head -1 user-data.sh | grep -q "#!/bin/bash"; then
    echo "✅ user-data.sh appears valid"
else
    echo "⚠️  Warning: user-data.sh may not have proper shebang"
fi

# Create base64 encoded user data
echo "🔄 Encoding user-data.sh as base64..."
USER_DATA_B64=$(base64 -w 0 user-data.sh)

if [ $? -eq 0 ] && [ -n "$USER_DATA_B64" ]; then
    echo "✅ Base64 encoding successful"
    echo "📊 Encoded size: ${#USER_DATA_B64} characters"
else
    echo "❌ Failed to encode user-data.sh"
    exit 1
fi

# Create the EC2 instance using base64 encoded user data
echo "🏗️ Creating EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SECURITY_GROUP_ID \
    --iam-instance-profile Name=$IAM_INSTANCE_PROFILE \
    --user-data "$USER_DATA_B64" \
    --tag-specifications \
        'ResourceType=instance,Tags=[{Key=Name,Value=SeeHearAI-Server},{Key=Project,Value=SeeHearAI}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

if [ $? -eq 0 ] && [ "$INSTANCE_ID" != "None" ] && [ -n "$INSTANCE_ID" ]; then
    echo "✅ EC2 instance created: $INSTANCE_ID"
    
    # Wait for instance to be running
    echo "⏳ Waiting for instance to start..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID
    
    # Get public IP
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo "✅ Instance is running!"
    echo "📍 Public IP: $PUBLIC_IP"
    
    # Save instance info
    cat > seehearai-ec2-info.txt << EOF
# SeeHearAI EC2 Instance Information
# ==================================
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
INSTANCE_TYPE=$INSTANCE_TYPE
KEY_NAME=$KEY_NAME
SECURITY_GROUP_ID=$SECURITY_GROUP_ID

# SSH Connection:
ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP

# SeeHearAI URL (after deployment):
http://$PUBLIC_IP:8000
EOF
    
    echo ""
    echo "🎉 SeeHearAI EC2 Instance Created Successfully!"
    echo "============================================="
    echo "📋 Instance Details:"
    echo "   Instance ID: $INSTANCE_ID"
    echo "   Public IP: $PUBLIC_IP"
    echo "   Instance Type: $INSTANCE_TYPE"
    echo "   SSH Key: $KEY_NAME.pem"
    echo ""
    echo "🔗 SSH Connection Command:"
    echo "   ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
    echo ""
    echo "🌐 SeeHearAI URL (after code deployment):"
    echo "   http://$PUBLIC_IP:8000"
    echo ""
    echo "💾 Instance info saved to: seehearai-ec2-info.txt"
    echo ""
    echo "⏳ The instance is setting up automatically (5-10 minutes)"
    echo "📝 Setup progress: ssh in and run 'tail -f /var/log/seehearai-setup.log'"
    echo ""
    echo "🔄 Next Step: Upload your SeeHearAI code to the server"
    echo "💰 Estimated cost: ~$25/month (can stop when not in use)"
    
else
    echo "❌ Failed to create EC2 instance"
    echo "Instance ID returned: '$INSTANCE_ID'"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check AWS CLI configuration: aws configure list"
    echo "2. Verify IAM permissions"
    echo "3. Check if the AMI ID is available in your region"
    echo "4. Verify security group and key pair exist"
    exit 1
fi

echo ""
echo "🚀 Ready for code deployment!"