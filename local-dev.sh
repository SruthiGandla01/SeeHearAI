# ===================================
#!/bin/bash
# local-dev.sh - Local development with Docker Compose

echo "🐳 Starting SeeHearAI Local Development Environment"
echo "================================================="

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# SeeHearAI Local Development Environment
OPENAI_API_KEY=your_openai_api_key_here
S3_BUCKET=seehearai-local-bucket
DYNAMODB_TABLE=SeeHearAISessions
TTS_QUEUE_URL=http://localstack:4566/000000000000/tts-queue
VISION_QUEUE_URL=http://localstack:4566/000000000000/vision-queue
ANALYTICS_QUEUE_URL=http://localstack:4566/000000000000/analytics-queue
EOF
    echo "⚠️  Please update .env with your actual API keys"
fi

# Start services
echo "🚀 Starting local services..."
docker-compose up -d

echo "✅ Local development environment started!"
echo ""
echo "🌐 Access your app at:"
echo "   • Frontend: http://localhost"
echo "   • API: http://localhost:8000"
echo "   • WebSocket: http://localhost:8001"
echo ""
echo "📊 Development Services:"
echo "   • PostgreSQL: localhost:5432"
echo "   • Redis: localhost:6379"  
echo "   • LocalStack: localhost:4566"
echo ""
echo "🔍 View logs:"
echo "   docker-compose logs -f [service_name]"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"