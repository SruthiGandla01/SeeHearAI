#!/usr/bin/env python3
"""
WebSocket Server for SeeHearAI
Handles real-time video streaming and AI processing
"""

import asyncio
import json
import logging
import os
import websockets
from websockets.server import serve
import base64
from datetime import datetime
import sys
import traceback

# Import your existing utilities
sys.path.append('/app')
from app.aws_utils import upload_to_s3, get_from_dynamodb, save_to_dynamodb
from app.sqs_utils import send_to_sqs
from app.vision_utils import process_image_with_ai
from app.tts_utils import text_to_speech_gtts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SeeHearAIWebSocketServer:
    def __init__(self):
        self.connected_clients = set()
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.vision_queue_url = os.getenv('VISION_QUEUE_URL', '')
        self.tts_queue_url = os.getenv('TTS_QUEUE_URL', '')
        self.analytics_queue_url = os.getenv('ANALYTICS_QUEUE_URL', '')
        
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")

    async def handle_video_frame(self, websocket, data):
        """Process incoming video frame"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(data['image'])
            
            # Process with AI vision
            vision_result = await self.process_vision_async(image_data)
            
            # Send response back to client
            response = {
                'type': 'vision_result',
                'timestamp': datetime.now().isoformat(),
                'result': vision_result
            }
            
            await websocket.send(json.dumps(response))
            
            # Queue for background processing if needed
            if self.vision_queue_url:
                await send_to_sqs(self.vision_queue_url, vision_result)
                
        except Exception as e:
            logger.error(f"Error processing video frame: {e}")
            await self.send_error(websocket, str(e))

    async def handle_audio_request(self, websocket, data):
        """Handle text-to-speech requests"""
        try:
            text = data.get('text', '')
            if not text:
                return
                
            # Generate TTS
            audio_data = await self.generate_tts_async(text)
            
            # Send audio back to client
            response = {
                'type': 'audio_response',
                'timestamp': datetime.now().isoformat(),
                'audio': base64.b64encode(audio_data).decode('utf-8') if audio_data else None
            }
            
            await websocket.send(json.dumps(response))
            
            # Queue for background processing
            if self.tts_queue_url:
                await send_to_sqs(self.tts_queue_url, {'text': text})
                
        except Exception as e:
            logger.error(f"Error processing audio request: {e}")
            await self.send_error(websocket, str(e))

    async def process_vision_async(self, image_data):
        """Process image with AI vision models"""
        try:
            # Use your existing vision processing function
            result = process_image_with_ai(image_data)
            return result
        except Exception as e:
            logger.error(f"Vision processing error: {e}")
            return {"error": str(e)}

    async def generate_tts_async(self, text):
        """Generate text-to-speech audio"""
        try:
            # Use your existing TTS function
            audio_data = text_to_speech_gtts(text)
            return audio_data
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None

    async def send_error(self, websocket, error_message):
        """Send error message to client"""
        response = {
            'type': 'error',
            'timestamp': datetime.now().isoformat(),
            'message': error_message
        }
        await websocket.send(json.dumps(response))

    async def handle_message(self, websocket, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'video_frame':
                await self.handle_video_frame(websocket, data)
            elif message_type == 'audio_request':
                await self.handle_audio_request(websocket, data)
            elif message_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error(websocket, "Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, str(e))

    async def client_handler(self, websocket, path):
        """Handle WebSocket client connections"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start_server(self, host='0.0.0.0', port=8001):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {host}:{port}")
        
        server = await serve(
            self.client_handler,
            host,
            port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10
        )
        
        logger.info("WebSocket server started successfully")
        await server.wait_closed()

def main():
    """Main entry point"""
    try:
        # Create server instance
        server = SeeHearAIWebSocketServer()
        
        # Start the server
        asyncio.run(server.start_server())
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()