
import asyncio
import edge_tts
from gtts import gTTS

async def test_edge():
    print("Testing Edge TTS (Connor - Irish Male)...")
    try:
        communicate = edge_tts.Communicate("Hello, I am Connor.", "en-IE-ConnorNeural")
        await communicate.save("test_edge_connor.mp3")
        print("Edge TTS Success!")
        return True
    except Exception as e:
        print(f"Edge TTS Failed: {e}")
        return False

def test_gtts():
    print("Testing gTTS (IE - Irish)...")
    try:
        tts = gTTS("Hello, I am Google Ireland.", lang='en', tld='ie')
        tts.save("test_gtts_ie.mp3")
        print("gTTS Success!")
        return True
    except Exception as e:
        print(f"gTTS Failed: {e}")
        return False

async def main():
    await test_edge()
    test_gtts()

if __name__ == "__main__":
    asyncio.run(main())
