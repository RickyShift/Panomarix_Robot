
import pyttsx3
import os

OUTPUT = "test_pyttsx3.wav"

try:
    engine = pyttsx3.init()
    print("Generating WAV...")
    # On Windows, save_to_file uses ffmpeg if available or SAPI5 native save?
    # Actually checking documentation, save_to_file might be async or buggy.
    # Let's try.
    engine.save_to_file("Testing local wav generation", OUTPUT)
    engine.runAndWait()
    
    if os.path.exists(OUTPUT):
        print(f"Success! {OUTPUT} created.")
    else:
        print("File not created.")
except Exception as e:
    print(f"Error: {e}")
