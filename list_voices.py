
import pyttsx3

try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print(f"Found {len(voices)} voices:")
    for i, voice in enumerate(voices):
        print(f"[{i}] ID: {voice.id}")
        print(f"    Name: {voice.name}")
        print(f"    Languages: {voice.languages}")
except Exception as e:
    print(f"Error: {e}")
