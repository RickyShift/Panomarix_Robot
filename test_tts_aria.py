
import asyncio
import edge_tts

VOICE = "en-US-AriaNeural"
TEXT = "Testing internet connection and voice."
OUTPUT = "test_aria.mp3"

async def main():
    print(f"Generating TTS with voice {VOICE}...")
    try:
        communicate = edge_tts.Communicate(TEXT, VOICE)
        await communicate.save(OUTPUT)
        print("Success! Audio saved.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
