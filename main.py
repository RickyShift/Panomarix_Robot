import whisper
import sounddevice as sd
from scipy.io.wavfile import write

model = whisper.load_model("base")  # or tiny, small, medium, large

def record_audio(filename="input.wav", duration=5, fs=44100):
    print("Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    write(filename, fs, audio)
    print("Saved:", filename)

record_audio()

result = model.transcribe("input.wav", language = "pt")
print("\nTranscription:")
print(result["text"])