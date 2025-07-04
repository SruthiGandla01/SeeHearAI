# 👁️‍🗨️ SeeHearAI: Multimodal AI Assistant for the Visually Impaired

> Inspired by **BeMyEyes**, SeeHearAI is a **cloud-native**, **event-driven**, LLM-powered AI assistant that helps visually impaired users understand their surroundings in real time through speech, computer vision, and natural language.

---

## 🚀 Project Purpose

**SeeHearAI** provides assistance to visually impaired users by:

- 🔊 Listening for voice triggers using hotword detection.
- 📸 Capturing video frames and generating descriptive captions using vision models.
- 🧠 Supporting real-time voice-based interaction using LLMs (e.g., OpenAI GPT).
- ☁️ Logging every interaction to AWS **Lambda**, **S3**, and **DynamoDB** for analysis.
- 📊 Visualizing session analytics via structured logs.

---

## 💡 Tech Stack

| Category                | Tools & Services                                                                 |
|-------------------------|----------------------------------------------------------------------------------|
| 👁️ Vision               | YOLOv8, BLIP (HuggingFace Transformers)                                         |
| 🔉 Voice & TTS          | Vosk ASR, pyttsx3, WebSocket Audio Streaming                                     |
| 🧠 LLM & NLP            | OpenAI GPT, Transformers (HuggingFace)                                          |
| 🧱 Backend              | FastAPI (Python)                                                                |
| 🎛️ Frontend             | HTML + JavaScript (Minimal camera/mic interface)                                |
| ☁️ Cloud Infrastructure | AWS EC2, Lambda, S3, DynamoDB                                                   |
| 🐳 Containerization     | Docker, Docker Compose                                                          |
| 📈 Analytics            | JSON logs, DynamoDB ETL, session analytics                                      |
| 🛠️ IaC & Automation     | Shell Scripts (`deploy-seehearai.sh`, `create-lambda-infrastructure.sh`, etc.) |

---

## 🛠️ How to Set Up

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/SruthiGandla01/SeeHearAI.git
cd SeeHearAI
```

### 2️⃣ Create and Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # (On Windows: .venv\Scripts\activate)

```
### 3️⃣ Install Required Dependencies

```bash
pip install -r requirements.txt

```

### 4️⃣ Set Up Environment Variables

Create a .env file in the root directory with the following content:

```bash
OPENAI_API_KEY=your-openai-api-key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=seehearai-bucket
DYNAMODB_TABLE_NAME=SeeHearAI-Analytics
LAMBDA_FUNCTION_NAME=SeeHearAI-ETL

```
### 💻 Run the App Locally
▶️ Start the FastAPI Server

```bash
uvicorn app.fastapi_server:app --reload --port 8000

```
Visit: http://127.0.0.1:8000

### ☁️ Deploy to AWS EC2
🔐 SSH into EC2

```bash
ssh -i seehearai-key.pem ec2-user@<your-ec2-ip>

```

### 🚀 Deploy the Application
```bash
bash deploy-seehearai.sh

```
### ⚙️ Trigger ETL Pipeline (AWS Lambda)
Run the following command to manually invoke the Lambda function:

```bash
aws lambda invoke \
  --function-name SeeHearAI-ETL \
  --region us-east-1 \
  --payload '{}' \
  response.json

```
---

## 📊 Analytics Dashboard

- Every interaction is logged to **DynamoDB** & **S3**
- Logs are used to build **analytics dashboards** and **usage reports**
- Each session has its own **uniquely timestamped log record**

---

## 🏁 What I Achieved

- ✅ Full-stack **AI + Cloud Data Engineering** project  
- ✅ **Serverless** real-time data pipeline  
- ✅ **Production-ready** cloud deployment on **AWS**  
- ✅ Built **analytics dashboards** for interaction analysis  
- ✅ Designed **scalable architecture** inspired by **BeMyEyes**  
- ✅ Implemented **event-driven ETL** with real-time logs in **DynamoDB** & **S3**  
- ✅ Proven capability in **speech / vision / NLP integration**

---
  
### 📬 Contact

Built with ❤️ by Sruthi Gandla

⭐ Star this repo if you found it helpful or inspiring!
