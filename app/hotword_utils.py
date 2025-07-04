from vosk import Model, KaldiRecognizer
import pyaudio
import json
from tts_utils import speak_response
import wave

def wait_for_hotword_and_record():
    model = Model("vosk_model")
    rec = KaldiRecognizer(model, 16000)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()

    print("🔊 Listening for 'hey buddy'...")

    # Hotword detection
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()
            if "hey buddy" in text:
                print("🟢 Wake word detected!")
                break

    stream.stop_stream()
    stream.close()

    # Respond "Yes, how can I help?"
    speak_response("Yes, how can I help?")

    # Now record the question
    print("🎙️ Listening for your question...")

    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
    stream.start_stream()

    frames = []
    seconds = 5  # Adjust duration if you want
    for _ in range(0, int(16000 / 8192 * seconds)):
        data = stream.read(4096, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save to WAV
    wav_path = "question.wav"
    wf = wave.open(wav_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Transcribe
    from audio_utils import transcribe_audio
    return transcribe_audio(wav_path)
