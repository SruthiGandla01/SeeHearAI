import asyncio
import json
import numpy as np
from vosk import Model, KaldiRecognizer
from fastapi import WebSocket
import io
import wave

class HotwordDetector:
    def __init__(self, model_path="vosk_model", sample_rate=16000):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.sample_rate = sample_rate
        self.is_listening = True
        self.hotword_detected = False
        self.audio_buffer = bytearray()
        
    async def process_audio_chunk(self, audio_data: bytes, websocket: WebSocket):
        """Process incoming audio chunk for hotword detection"""
        try:
            # Add audio data to buffer
            self.audio_buffer.extend(audio_data)
            
            # Process in chunks of appropriate size
            chunk_size = 4096
            if len(self.audio_buffer) >= chunk_size:
                # Get chunk to process
                chunk = bytes(self.audio_buffer[:chunk_size])
                self.audio_buffer = self.audio_buffer[chunk_size:]
                
                # Process with VOSK
                if self.recognizer.AcceptWaveform(chunk):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower()
                    
                    print(f"🎤 Detected speech: {text}")
                    
                    # Check for hotword
                    if "hey buddy" in text:
                        await self.handle_hotword_detected(websocket)
                        
                else:
                    # Partial result
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "").lower()
                    
                    if "hey buddy" in partial_text:
                        await self.handle_hotword_detected(websocket)
                        
        except Exception as e:
            print(f"Error processing audio chunk: {e}")
            
    async def handle_hotword_detected(self, websocket: WebSocket):
        """Handle when hotword is detected"""
        print("🟢 Hey Buddy detected!")
        self.hotword_detected = True
        
        # Send hotword detection to client
        await websocket.send_text(json.dumps({
            "type": "hotword_detected",
            "message": "Wake word detected! Listening for your question..."
        }))
        
        # Send audio acknowledgment
        await websocket.send_text(json.dumps({
            "type": "play_acknowledgment",
            "message": "Yes, how can I help?"
        }))
        
        # Reset hotword detection
        self.hotword_detected = False
        
    def stop(self):
        """Stop the hotword detector"""
        self.is_listening = False
        
    def reset_buffer(self):
        """Reset audio buffer"""
        self.audio_buffer.clear()

# Alternative implementation using a different approach
class SimpleHotwordDetector:
    """Simplified hotword detector for better web integration"""
    
    def __init__(self):
        self.hotwords = ["hey buddy", "hey body", "a buddy"]  # Include variations
        self.is_active = True
        
    async def process_text(self, text: str, websocket: WebSocket):
        """Process transcribed text for hotword detection"""
        text_lower = text.lower().strip()
        
        for hotword in self.hotwords:
            if hotword in text_lower:
                await self.trigger_hotword(websocket)
                return True
        return False
        
    async def trigger_hotword(self, websocket: WebSocket):
        """Trigger hotword detection"""
        print("🟢 Hotword detected!")
        
        await websocket.send_text(json.dumps({
            "type": "hotword_detected",
            "message": "I'm listening! What would you like to know?"
        }))
        
    def stop(self):
        self.is_active = False