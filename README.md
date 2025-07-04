# 👁️👂 SeeHearAI — Real-Time Accessibility Assistant (Inspired by BeMyEyes)

SeeHearAI is an intelligent voice-vision assistant designed to help visually impaired users understand their surroundings through real-time image captioning, voice-based Q&A, and audio response. Inspired by *BeMyEyes*, this project combines **computer vision**, **LLMs**, **TTS**, and a **serverless data engineering pipeline** to create a fully scalable, production-grade cloud application.

---

## 🔍 Project Purpose

To empower visually impaired users to:
- Interact via **voice prompts**
- Understand surroundings via **AI-driven image captioning**
- Receive responses in **natural speech**
- Automatically log interactions for **real-time analytics**

It also showcases a full-fledged **serverless data engineering pipeline** capable of:
- Ingesting user interaction data
- Storing structured logs in DynamoDB and S3
- Running scheduled ETL jobs
- Generating live analytics dashboards

---

## 🧠 Features

✅ Real-time **vision captioning** using YOLOv8 + BLIP  
✅ Conversational Q&A via **GPT-based LLM**  
✅ Voice interaction using **VOSK speech recognition**  
✅ TTS audio response with **gTTS**  
✅ Multi-source logging to **DynamoDB** and **Amazon S3**  
✅ **Lambda-based ETL** pipeline for daily processing  
✅ **Interactive dashboard** built with Chart.js  
✅ Hosted on **AWS EC2** with real-time API access

---

## ⚙️ Tech Stack

### 🧠 AI Models:
- **YOLOv8**: Object detection (Ultralytics)
- **BLIP**: Image captioning
- **GPT-4 API**: Visual question answering
- **VOSK**: Speech-to-text
- **gTTS**: Text-to-speech

### 🧰 Backend:
- **FastAPI** for inference server
- **WebSockets** for hotword detection
- **Docker** (dev only, optional)

### ☁️ Data Engineering (Cloud-Native):
- **AWS Lambda**: Serverless ETL pipeline
- **Amazon S3**: Data lake (frames, audio, logs, analytics)
- **Amazon DynamoDB**: NoSQL event log store
- **AWS EventBridge**: Scheduling analytics jobs
- **AWS API Gateway**: Analytics API
- **CloudWatch**: Log monitoring

---

## 📁 Project Structure

.
├── app/ # Core app logic (chat, vision, TTS, speech)
│ ├── fastapi_server.py
│ ├── vision_utils.py
│ ├── chat.py
│ └── ...
├── backend/ # Backend deployment folder
│ ├── app.py
│ └── Dockerfile
├── data_engineering/ # Lambda ETL scripts & configs
│ ├── lambdas/
│ └── config/
├── vosk_model/ # VOSK speech model
├── analytics_report.json # Sample analytics
├── deploy-seehearai.sh # Deployment script
├── requirements.txt # Python dependencies
└── ...

## 🚀 How to Run

### 1️⃣ Local Development

```bash
# Clone and navigate to project
git clone https://github.com/your-username/SeeHearAI.git
cd SeeHearAI

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn app.fastapi_server:app --reload --port 8000

2️⃣ EC2 Deployment (Production)
bash
Copy
Edit
# SSH into EC2
ssh -i seehearai-key.pem ec2-user@<your-ec2-ip>

# Start the app
cd seehearai/
python -m uvicorn app.fastapi_server:app --host 0.0.0.0 --port 8000
Access: http://<your-ec2-ip>:8000

3️⃣ Trigger Analytics Pipeline
Run your AWS Lambda ETL manually:

bash
Copy
Edit
aws lambda invoke \
  --function-name SeeHearAI-ETL-Pipeline \
  --region us-east-1 \
  --payload '{}' \
  response.json


📈 Live Analytics Dashboard
Dashboard	API
🌐 HTML View	📊 JSON API

🏆 What I Achieved
✅ Full-stack AI + Cloud Engineering project
✅ Serverless real-time data pipeline
✅ Production-ready cloud deployment on AWS
✅ Built analytics dashboards for interaction analysis
✅ Developed scalable architecture inspired by BeMyEyes
✅ Implemented event-driven ETL with real-time logs in DynamoDB & S3
✅ Proven capability in speech/vision/NLP integration

👩‍💻 Ideal for Data Engineering Roles
This project demonstrates:

Serverless architecture design

Real-time event logging

S3-based data lake formation

Lambda-based ETL workflows

API development and dashboarding

Infrastructure as code via shell scripts

🔐 Secrets & Security
Secrets like API keys and AWS credentials are never committed and managed through environment variables (.env, not pushed). All secrets are scanned and excluded from the repository.

📬 Contact
Built with ❤️ by Sruthi Gandla

Inspired by BeMyEyes, powered by AI, and engineered for real-world accessibility.

