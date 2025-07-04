# AWS-Integrated FastAPI Server for SeeHearAI
# app/fastapi_server.py

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
import os
import cv2
import json
import time
import traceback
import asyncio
import base64
import numpy as np
from PIL import Image
from io import BytesIO
import boto3
from datetime import datetime, timezone
import logging

# AWS Integration
from app.aws_utils import S3Manager, DynamoDBManager
from app.vision_utils import detect_frame_caption
from app.chat import ask_gpt
from app.tts_utils import speak_response_aws

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SeeHearAI",
    description="Cloud-powered AI assistant for vision-impaired users",
    version="2.0"
)

# Initialize AWS services
s3_manager = S3Manager()
dynamodb_manager = DynamoDBManager()

class ConversationManager:
    def __init__(self):
        self.hotwords = ["hey buddy", "hey body", "a buddy", "hey bud", "hey but"]
        self.last_hotword_time = 0
        self.conversation_active = False
        self.last_activity_time = 0
        self.current_frame = None
        self.session_id = None
        
    def start_session(self):
        """Start a new conversation session"""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Started new session: {self.session_id}")
        
        # Log session start in DynamoDB
        dynamodb_manager.log_session_event(
            session_id=self.session_id,
            event_type="session_start",
            data={"timestamp": datetime.now(timezone.utc).isoformat()}
        )
        return self.session_id
        
    def process_speech(self, text):
        """Process speech and return action type and content"""
        import re
        text_clean = re.sub(r'[^\w\s]', '', text.lower().strip())
        current_time = time.time()
        
        logger.info(f"🎤 Processing: '{text}' -> '{text_clean}'")
        
        # Log speech input
        if self.session_id:
            dynamodb_manager.log_session_event(
                session_id=self.session_id,
                event_type="speech_input", 
                data={"text": text, "processed_text": text_clean}
            )
        
        # Check for hotword first
        for hotword in self.hotwords:
            if hotword in text_clean:
                if current_time - self.last_hotword_time > 2:
                    self.last_hotword_time = current_time
                    self.last_activity_time = current_time
                    self.conversation_active = True
                    if not self.session_id:
                        self.start_session()
                    logger.info(f"🟢 HOTWORD DETECTED: '{hotword}'")
                    return "HOTWORD", "Yes, how can I help you?"
                else:
                    logger.info(f"⏰ Hotword in cooldown")
                    return "IGNORE", None
        
        # Check for question in active conversation
        if self.conversation_active:
            time_since_activity = current_time - self.last_activity_time
            
            if time_since_activity < 300:  # 5 minutes
                if len(text_clean.split()) >= 2:
                    self.last_activity_time = current_time
                    logger.info(f"💭 Question detected: '{text_clean}'")
                    return "QUESTION", text_clean
                else:
                    return "UNCLEAR", "I didn't catch that. Could you repeat?"
            else:
                logger.info(f"⏰ Conversation expired after {time_since_activity:.1f}s")
                self.conversation_active = False
        
        return "NONE", None
    
    def update_frame(self, frame_data):
        """Update the current video frame and save to S3"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(frame_data)
            image = Image.open(BytesIO(image_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            self.current_frame = frame
            
            # Save frame to S3 if we have a session
            if self.session_id:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                frame_key = f"video-frames/{self.session_id}/{timestamp}.jpg"
                
                # Convert frame back to bytes for S3 upload
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                # Upload to S3 (async)
                asyncio.create_task(
                    s3_manager.upload_file_bytes(frame_bytes, frame_key)
                )
                
                logger.info(f"📹 Frame updated and saved to S3: {frame_key}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Error updating frame: {e}")
            return False
    
    def get_scene_analysis(self):
        """Get analysis of current frame"""
        if self.current_frame is None:
            return "No video frame available"
        
        try:
            logger.info("🖼️ Analyzing current frame...")
            analysis = detect_frame_caption(self.current_frame)
            
            # Log analysis result
            if self.session_id:
                dynamodb_manager.log_session_event(
                    session_id=self.session_id,
                    event_type="vision_analysis",
                    data={"analysis": analysis}
                )
            
            logger.info(f"🔍 Scene analysis result: {analysis}")
            return analysis
        except Exception as e:
            logger.error(f"❌ Vision analysis error: {e}")
            return f"Error analyzing video frame: {str(e)}"

# Global conversation manager
conversation = ConversationManager()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main application page"""
    try:
        with open("app/static/index.html", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback if static file not found
        return """
        <html><body>
        <h1>SeeHearAI Server Running</h1>
        <p>Upload your static files to app/static/index.html</p>
        </body></html>
        """

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 WebSocket connected")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    continue
                except:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Error receiving message: {e}")
                break
            
            # Handle different message types
            try:
                if message["type"] == "video_frame":
                    frame_data = message.get("data")
                    if frame_data:
                        success = conversation.update_frame(frame_data)
                        
                elif message["type"] == "speech_result":
                    text = message.get("text", "")
                    if text:
                        action_type, content = conversation.process_speech(text)
                        
                        if action_type == "HOTWORD":
                            await websocket.send_text(json.dumps({
                                "type": "hotword_detected",
                                "message": content,
                                "session_id": conversation.session_id
                            }))
                            
                        elif action_type == "QUESTION":
                            await process_question_with_vision(content, websocket)
                            
                        elif action_type == "UNCLEAR":
                            await websocket.send_text(json.dumps({
                                "type": "clarification",
                                "message": content
                            }))
                            
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Server error: {str(e)}"
                    }))
                except:
                    break
                        
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"🔌 WebSocket error: {e}")
    finally:
        logger.info("🔌 WebSocket connection closed")

async def process_question_with_vision(question: str, websocket: WebSocket):
    """Process question with current video frame using AWS services"""
    try:
        logger.info(f"❓ Processing question with vision: '{question}'")
        
        # Send processing status
        await websocket.send_text(json.dumps({
            "type": "processing",
            "message": "Analyzing video and processing your question..."
        }))
        
        # Get scene analysis
        scene_description = conversation.get_scene_analysis()
        
        # Build GPT conversation
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly assistant helping vision-impaired users understand their surroundings. "
                    "You have access to a description of what's currently visible in their video feed. "
                    "Use this visual information to answer their questions accurately and helpfully. "
                    "Be conversational, warm, and specific in your responses."
                )
            },
            {
                "role": "user", 
                "content": f"Question: {question}\n\nWhat I can see in the video: {scene_description}"
            }
        ]
        
        # Get AI response
        try:
            answer = ask_gpt(messages)
            if not answer or answer.strip() == "":
                answer = f"I can see: {scene_description}. But I'm having trouble generating a specific response to your question."
        except Exception as gpt_error:
            logger.error(f"❌ GPT Error: {gpt_error}")
            answer = f"Based on what I can see: {scene_description}. I'm having some technical difficulties right now."
        
        # Log the Q&A interaction
        if conversation.session_id:
            dynamodb_manager.log_session_event(
                session_id=conversation.session_id,
                event_type="qa_interaction",
                data={
                    "question": question,
                    "answer": answer,
                    "scene_description": scene_description
                }
            )
        
        # Generate audio response using AWS
        audio_url = None
        try:
            session_id = conversation.session_id or uuid.uuid4().hex
            audio_key = f"audio-files/{session_id}/{uuid.uuid4().hex}.mp3"
            
            # Generate and upload audio to S3
            audio_url = await speak_response_aws(answer, audio_key, s3_manager)
            logger.info(f"🔊 Audio generated and uploaded to S3: {audio_key}")
            
        except Exception as tts_error:
            logger.error(f"❌ TTS Error: {tts_error}")
            audio_url = None
        
        # Send response
        response_data = {
            "type": "ai_response",
            "question": question,
            "answer": answer,
            "scene_description": scene_description,
            "audio_url": audio_url,
            "session_id": conversation.session_id
        }
        
        await websocket.send_text(json.dumps(response_data))
        logger.info(f"✅ Response sent successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in process_question_with_vision: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error processing question: {str(e)}"
            }))
        except:
            pass

@app.get("/audio/{session_id}/{file_name}")
async def get_audio_from_s3(session_id: str, file_name: str):
    """Serve audio files from S3"""
    try:
        audio_key = f"audio-files/{session_id}/{file_name}"
        
        # Get presigned URL from S3
        presigned_url = s3_manager.get_presigned_url(audio_key)
        
        if presigned_url:
            # Redirect to presigned URL
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url)
        else:
            return JSONResponse({"error": "Audio file not found"}, status_code=404)
            
    except Exception as e:
        logger.error(f"Error serving audio: {e}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test AWS connectivity
        s3_status = s3_manager.test_connection()
        dynamodb_status = dynamodb_manager.test_connection()
        
        return {
            "status": "healthy",
            "aws_services": {
                "s3": "connected" if s3_status else "disconnected",
                "dynamodb": "connected" if dynamodb_status else "disconnected"
            },
            "conversation_active": conversation.conversation_active,
            "session_id": conversation.session_id
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session"""
    try:
        history = dynamodb_manager.get_session_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Mount static files if directory exists
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)