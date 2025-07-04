# SQS Integration for SeeHearAI
# app/sqs_utils.py

import boto3
import json
import logging
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class SQSManager:
    """Manages SQS operations for Lambda communication"""
    
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.sqs = boto3.client('sqs', region_name=self.region)
        
        # Queue URLs (will be set after queue creation)
        self.tts_queue_url = os.getenv("TTS_QUEUE_URL")
        self.vision_queue_url = os.getenv("VISION_QUEUE_URL")
        
        logger.info("SQS Manager initialized")
    
    async def send_tts_request(self, text: str, s3_key: str, session_id: str) -> bool:
        """Send TTS generation request to Lambda via SQS"""
        try:
            message = {
                'text': text,
                's3_key': s3_key,
                'session_id': session_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'request_type': 'tts_generation'
            }
            
            def _send_message():
                return self.sqs.send_message(
                    QueueUrl=self.tts_queue_url,
                    MessageBody=json.dumps(message),
                    MessageAttributes={
                        'session_id': {
                            'StringValue': session_id,
                            'DataType': 'String'
                        }
                    }
                )
            
            # Send asynchronously
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, _send_message)
            
            logger.info(f"TTS request sent to Lambda: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send TTS request: {e}")
            return False
    
    async def send_vision_request(self, frame_s3_key: str, session_id: str) -> bool:
        """Send vision analysis request to Lambda via SQS"""
        try:
            message = {
                'frame_s3_key': frame_s3_key,
                'session_id': session_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'request_type': 'vision_analysis'
            }
            
            def _send_message():
                return self.sqs.send_message(
                    QueueUrl=self.vision_queue_url,
                    MessageBody=json.dumps(message),
                    MessageAttributes={
                        'session_id': {
                            'StringValue': session_id,
                            'DataType': 'String'
                        }
                    }
                )
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, _send_message)
            
            logger.info(f"Vision request sent to Lambda: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send vision request: {e}")
            return False
    
    def create_queues(self) -> Dict[str, str]:
        """Create SQS queues for Lambda communication"""
        try:
            queue_configs = {
                'tts-queue': {
                    'VisibilityTimeoutSeconds': '300',  # 5 minutes
                    'MessageRetentionPeriod': '1209600',  # 14 days
                    'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
                },
                'vision-queue': {
                    'VisibilityTimeoutSeconds': '300',
                    'MessageRetentionPeriod': '1209600', 
                    'ReceiveMessageWaitTimeSeconds': '20'
                }
            }
            
            queue_urls = {}
            
            for queue_name, config in queue_configs.items():
                response = self.sqs.create_queue(
                    QueueName=f"seehearai-{queue_name}",
                    Attributes=config
                )
                queue_urls[queue_name] = response['QueueUrl']
                logger.info(f"Created queue: {queue_name}")
            
            return queue_urls
            
        except Exception as e:
            logger.error(f"Failed to create queues: {e}")
            return {}

# Updated FastAPI server integration
class LambdaIntegratedConversationManager:
    """Enhanced conversation manager with Lambda integration"""
    
    def __init__(self, s3_manager, dynamodb_manager, sqs_manager):
        self.hotwords = ["hey buddy", "hey body", "a buddy", "hey bud", "hey but"]
        self.last_hotword_time = 0
        self.conversation_active = False
        self.last_activity_time = 0
        self.current_frame = None
        self.session_id = None
        
        # AWS managers
        self.s3_manager = s3_manager
        self.dynamodb_manager = dynamodb_manager
        self.sqs_manager = sqs_manager
        
    async def process_question_with_lambda(self, question: str, websocket):
        """Process question using Lambda for heavy lifting"""
        try:
            logger.info(f"Processing question with Lambda: {question}")
            
            # Send processing status
            await websocket.send_text(json.dumps({
                "type": "processing",
                "message": "Processing your question with cloud AI..."
            }))
            
            # Save current frame to S3 for Lambda processing
            frame_s3_key = None
            if self.current_frame is not None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                frame_s3_key = f"video-frames/{self.session_id}/{timestamp}.jpg"
                
                # Convert frame to bytes
                import cv2
                _, buffer = cv2.imencode('.jpg', self.current_frame)
                frame_bytes = buffer.tobytes()
                
                # Upload frame to S3
                await self.s3_manager.upload_file_bytes(frame_bytes, frame_s3_key)
                
                # Send vision analysis request to Lambda
                await self.sqs_manager.send_vision_request(frame_s3_key, self.session_id)
            
            # For now, still do immediate processing on EC2 for real-time response
            # But also trigger Lambda for enhanced processing
            scene_description = "Processing with Lambda..." if frame_s3_key else "No video frame available"
            
            # Quick response for real-time interaction
            from app.chat import ask_gpt
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a friendly assistant helping vision-impaired users. Provide a helpful response while enhanced analysis is being processed in the background."
                },
                {
                    "role": "user", 
                    "content": f"Question: {question}. (Enhanced vision analysis in progress...)"
                }
            ]
            
            answer = ask_gpt(messages)
            
            # Generate TTS via Lambda (async)
            audio_key = f"audio-files/{self.session_id}/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
            await self.sqs_manager.send_tts_request(answer, audio_key, self.session_id)
            
            # Send immediate response
            response_data = {
                "type": "ai_response",
                "question": question,
                "answer": answer,
                "scene_description": scene_description,
                "audio_url": None,  # Will be available after Lambda processing
                "session_id": self.session_id,
                "processing_enhanced": True
            }
            
            await websocket.send_text(json.dumps(response_data))
            
            # Log the interaction
            self.dynamodb_manager.log_session_event(
                session_id=self.session_id,
                event_type="qa_interaction_lambda",
                data={
                    "question": question,
                    "answer": answer,
                    "frame_s3_key": frame_s3_key,
                    "audio_s3_key": audio_key
                }
            )
            
            logger.info("Question processed with Lambda integration")
            
        except Exception as e:
            logger.error(f"Error in Lambda-integrated processing: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error processing question: {str(e)}"
            }))

# Polling service to check for Lambda results
class LambdaResultPoller:
    """Polls DynamoDB for Lambda processing results"""
    
    def __init__(self, dynamodb_manager, websocket_manager):
        self.dynamodb_manager = dynamodb_manager
        self.websocket_manager = websocket_manager
        self.polling = False
    
    async def start_polling(self, session_id: str):
        """Start polling for Lambda results"""
        self.polling = True
        
        while self.polling:
            try:
                # Check for new TTS results
                await self.check_tts_results(session_id)
                
                # Check for new vision results  
                await self.check_vision_results(session_id)
                
                # Wait before next check
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)  # Longer wait on error
    
    async def check_tts_results(self, session_id: str):
        """Check for completed TTS processing"""
        # Implementation would query DynamoDB for new TTS results
        # and notify connected WebSocket clients
        pass
    
    async def check_vision_results(self, session_id: str):
        """Check for completed vision processing"""
        # Implementation would query DynamoDB for new vision results
        # and send enhanced analysis to WebSocket clients
        pass
    
    def stop_polling(self):
        """Stop the polling process"""
        self.polling = False