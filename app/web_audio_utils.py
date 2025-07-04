import io
import wave
import numpy as np
import whisper
from scipy.io import wavfile
import tempfile
import os

class WebAudioProcessor:
    """Audio processor optimized for web-based real-time processing"""
    
    def __init__(self):
        self.whisper_model = whisper.load_model("base")
        self.sample_rate = 16000
        
    def process_audio_blob(self, audio_data: bytes) -> str:
        """Process audio blob from web interface"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(tmp_path)
            
            # Cleanup
            os.unlink(tmp_path)
            
            return result["text"].strip()
            
        except Exception as e:
            print(f"Audio processing error: {e}")
            return ""
    
    def convert_js_audio_to_wav(self, float32_array: bytes, sample_rate: int = 16000) -> bytes:
        """Convert JavaScript Float32Array audio data to WAV format"""
        try:
            # Convert bytes back to float32 array
            audio_data = np.frombuffer(float32_array, dtype=np.float32)
            
            # Convert to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Create WAV in memory
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Audio conversion error: {e}")
            return b""
    
    def detect_speech_activity(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """Simple voice activity detection"""
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > threshold
    
    def preprocess_for_hotword(self, audio_chunk: bytes) -> bytes:
        """Preprocess audio chunk for hotword detection"""
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Normalize
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Apply simple noise reduction (optional)
            # You can add more sophisticated preprocessing here
            
            # Convert back to int16
            processed_data = (audio_data * 32768.0).astype(np.int16)
            
            return processed_data.tobytes()
            
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return audio_chunk

# Global instance for web app
web_audio_processor = WebAudioProcessor()

def transcribe_web_audio(audio_data: bytes) -> str:
    """Main function for transcribing audio from web interface"""
    return web_audio_processor.process_audio_blob(audio_data)