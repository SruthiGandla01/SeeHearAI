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

### 2️⃣ Create and Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # (On Windows: .venv\Scripts\activate)
