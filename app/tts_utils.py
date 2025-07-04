# AWS-Integrated Text-to-Speech Utilities
# app/tts_utils.py

import os
import tempfile
import logging
from gtts import gTTS
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def speak_response(text: str, save_path: str = "response.mp3") -> str:
    """Original TTS function for local development"""
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(save_path)
        logger.info(f"TTS audio saved locally: {save_path}")
        return save_path
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise

async def speak_response_aws(text: str, s3_key: str, s3_manager) -> Optional[str]:
    """Generate TTS audio and upload to S3, return presigned URL"""
    try:
        def _generate_tts():
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate TTS
            tts = gTTS(text=text, lang='en')
            tts.save(temp_path)
            
            # Read file bytes
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Cleanup temp file
            os.unlink(temp_path)
            
            return audio_bytes
        
        # Run TTS generation in thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            audio_bytes = await loop.run_in_executor(executor, _generate_tts)
        
        # Upload to S3
        success = await s3_manager.upload_file_bytes(
            audio_bytes, 
            s3_key, 
            content_type='audio/mpeg'
        )
        
        if success:
            # Return presigned URL for immediate access
            presigned_url = s3_manager.get_presigned_url(s3_key)
            logger.info(f"TTS audio uploaded to S3: {s3_key}")
            return presigned_url
        else:
            logger.error("Failed to upload TTS audio to S3")
            return None
            
    except Exception as e:
        logger.error(f"AWS TTS error: {e}")
        return None

class AWSTTSManager:
    """Advanced TTS manager with AWS Polly integration"""
    
    def __init__(self):
        self.use_polly = os.getenv("USE_AWS_POLLY", "false").lower() == "true"
        
        if self.use_polly:
            try:
                import boto3
                self.polly_client = boto3.client('polly', region_name=os.getenv("AWS_REGION", "us-east-1"))
                logger.info("AWS Polly TTS initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Polly, falling back to gTTS: {e}")
                self.use_polly = False
    
    async def generate_speech(self, text: str, s3_key: str, s3_manager, voice_id: str = "Joanna") -> Optional[str]:
        """Generate speech using AWS Polly or gTTS fallback"""
        try:
            if self.use_polly:
                return await self._generate_with_polly(text, s3_key, s3_manager, voice_id)
            else:
                return await speak_response_aws(text, s3_key, s3_manager)
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            return None
    
    async def _generate_with_polly(self, text: str, s3_key: str, s3_manager, voice_id: str) -> Optional[str]:
        """Generate speech using AWS Polly"""
        try:
            def _polly_synthesis():
                response = self.polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat='mp3',
                    VoiceId=voice_id,
                    Engine='neural'  # Use neural engine for better quality
                )
                return response['AudioStream'].read()
            
            # Run Polly synthesis in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                audio_bytes = await loop.run_in_executor(executor, _polly_synthesis)
            
            # Upload to S3
            success = await s3_manager.upload_file_bytes(
                audio_bytes, 
                s3_key, 
                content_type='audio/mpeg'
            )
            
            if success:
                presigned_url = s3_manager.get_presigned_url(s3_key)
                logger.info(f"Polly TTS audio uploaded to S3: {s3_key}")
                return presigned_url
            else:
                return None
                
        except Exception as e:
            logger.error(f"AWS Polly TTS error: {e}")
            # Fallback to gTTS
            return await speak_response_aws(text, s3_key, s3_manager)
    
    def get_available_voices(self) -> list:
        """Get list of available Polly voices"""
        if not self.use_polly:
            return []
        
        try:
            response = self.polly_client.describe_voices()
            return [
                {
                    'Id': voice['Id'],
                    'Name': voice['Name'],
                    'Gender': voice['Gender'],
                    'LanguageCode': voice['LanguageCode']
                }
                for voice in response['Voices']
                if voice['LanguageCode'].startswith('en')
            ]
        except Exception as e:
            logger.error(f"Failed to get Polly voices: {e}")
            return []

# Global TTS manager instance
tts_manager = AWSTTSManager()

# Convenience function for backward compatibility
async def generate_tts_aws(text: str, s3_key: str, s3_manager, voice_id: str = "Joanna") -> Optional[str]:
    """Generate TTS using AWS services"""
    return await tts_manager.generate_speech(text, s3_key, s3_manager, voice_id)