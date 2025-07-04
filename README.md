👁️‍🗨️ SeeHearAI: Multimodal AI Assistant for the Visually Impaired
Inspired by BeMyEyes — SeeHearAI is a cloud-native, event-driven, LLM-powered voice assistant that helps visually impaired users understand their surroundings in real time through speech, computer vision, and natural language.

🚀 Project Purpose
SeeHearAI provides assistance to visually impaired users by:

Listening for voice triggers using hotword detection.

Capturing video frames and generating descriptive captions using vision models.

Supporting real-time voice-based interaction using LLMs (e.g., OpenAI GPT).

Logging every interaction to AWS Lambda, S3, and DynamoDB for analysis.

Visualizing session analytics via dashboards.

🧰 Tech Stack
Category	Tools & Services
👁️ Vision	YOLOv8, BLIP (Hugging Face)
🗣️ Voice & TTS	Vosk ASR, pyttsx3, WebSocket Audio Streaming
🧠 LLM & NLP	OpenAI GPT, Transformers (HuggingFace)
🧱 Backend	FastAPI, Python
📦 Frontend	HTML + JS (minimal UI for camera, mic triggers)
☁️ Cloud Infrastructure	AWS EC2, S3, Lambda, DynamoDB
🐳 Containerization	Docker, Docker Compose
📈 Analytics	JSON logs, ETL to DynamoDB, session analytics reports
📁 Infra as Code	Bash Shell Scripts (create-lambda-infra.sh, deploy-seehearai.sh, etc.)

🔧 How to Set Up
1. Clone the Repository
bash
Copy
Edit
git clone https://github.com/SruthiGandla01/SeeHearAI.git
cd SeeHearAI
2. Create and Activate Virtual Environment
bash
Copy
Edit
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
3. Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
4. Set Up Environment Variables
Create a .env file at the root:

env
Copy
Edit
OPENAI_API_KEY=your-openai-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=your-region
S3_BUCKET_NAME=your-bucket
LAMBDA_FUNCTION_NAME=SeeHearAI-ETL
DYNAMODB_TABLE_NAME=SessionAnalytics
🧪 Local Development
Run FastAPI Server
bash
Copy
Edit
uvicorn app.fastapi_server:app --reload --port 8000
Visit: http://127.0.0.1:8000

☁️ Cloud Deployment (Production)
SSH into EC2 Instance
bash
Copy
Edit
ssh -i seehearai-key.pem ec2-user@<your-ec2-ip>
Deploy Application
bash
Copy
Edit
bash deploy-seehearai.sh
🧠 Trigger AWS Analytics (Lambda + S3 + DynamoDB)
Run this from EC2 or AWS CLI to test logging:

bash
Copy
Edit
aws lambda invoke \
  --function-name SeeHearAI-ETL \
  --region us-east-1 \
  --payload '{}' \
  response.json

  
🧩 What I Achieved
✅ End-to-end AI assistant inspired by BeMyEyes
✅ Built fully modular pipeline: hotword → vision → caption → GPT → TTS
✅ Logged each session to S3 and DynamoDB via Lambda ETL
✅ Dockerized APIs for easy deployment (frontend, backend, websocket)
✅ Developed real-time audio stream-to-chat capability via WebSockets
✅ Automated infrastructure setup via shell scripts and config files
✅ Created analytics dashboard using structured logs from DynamoDB



📣 Final Note
SeeHearAI is an effort to empower people with visual impairments using AI. It’s scalable, production-ready, and cloud-native — a perfect full-stack Data/Cloud Engineering showcase.

🌟 Give the project a star if it inspired you!
