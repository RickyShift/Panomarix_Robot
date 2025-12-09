
from gtts import gTTS

TEXT = "Testing Google Text to Speech."
OUTPUT = "test_gtts.mp3"

try:
    print("Generating gTTS...")
    tts = gTTS(TEXT)
    tts.save(OUTPUT)
    print("Success! gTTS saved.")
except Exception as e:
    print(f"Error: {e}")
