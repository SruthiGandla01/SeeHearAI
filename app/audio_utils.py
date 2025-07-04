import sounddevice as sd
import wavio
import whisper

model = whisper.load_model("base")

def record_audio(duration=5, fs=44100, filename="user.wav"):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    wavio.write(filename, recording, fs, sampwidth=2)
    print("Recording complete.")
    return filename

def transcribe_audio(filename):
    result = model.transcribe(filename)
    return result["text"]

def record_and_transcribe():
    filename = record_audio()
    return transcribe_audio(filename)
