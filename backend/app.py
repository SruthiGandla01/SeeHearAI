# backend/app.py

from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.vision_utils import detect_frame_caption
from app.chat import ask_gpt
from app.log_to_lambda import log_to_dynamodb
from s3_utils.s3_client import upload_file, log_event

from gtts import gTTS
import shutil
import uuid
import os

app = FastAPI(title="VisionStream AI", description="Vision Assistant", version="1.0")

# 👇 Serve static frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")


# 🏠 Root route → index.html
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


# 🎯 Handle /favicon.ico
@app.get("/favicon.ico")
async def favicon():
    if os.path.exists("static/favicon.ico"):
        return FileResponse("static/favicon.ico")
    return {"detail": "Favicon not found"}


# 🔍 Main analysis endpoint
@app.post("/analyze/")
async def analyze_scene(image: UploadFile, question: str = Form(...)):
    session_id = str(uuid.uuid4())[:8]

    # Save image
    image_path = f"input_{session_id}.jpg"
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # Detect scene + answer question
    caption = detect_frame_caption(image_path)
    answer = ask_gpt(caption, question)

    # Save TTS
    audio_path = f"response_{session_id}.mp3"
    tts = gTTS(text=answer)
    tts.save(audio_path)

    # 📤 Upload to S3
    upload_file(image_path, f"sessions/{session_id}/frame.jpg")
    upload_file(audio_path, f"sessions/{session_id}/response.mp3")
    log_event(f"Session {session_id}: {question} -> {answer}")

    # 🔁 Lambda → DynamoDB
    log_to_dynamodb(session_id, question, answer, caption)

    return {
        "caption": caption,
        "question": question,
        "answer": answer,
        "audio_url": f"/audio/{audio_path}"
    }


# 🔊 Serve generated TTS file
@app.get("/audio/{filename}")
def get_audio(filename: str):
    return FileResponse(filename, media_type="audio/mpeg")
