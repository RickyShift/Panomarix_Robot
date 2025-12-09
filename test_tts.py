
import asyncio
import edge_tts

VOICE = "en-IE-ConnorNeural"
TEXT = "Hello, this is a test."
OUTPUT = "test_tts.mp3"

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
