import asyncio
import websockets
import json
import os
import pyaudio
import base64
from dotenv import load_dotenv

load_dotenv()

# Audio Configuration
CHANNELS = 1
INPUT_RATE = 16000
OUTPUT_RATE = 24000
CHUNK_SIZE = 512  # Approx 32ms at 16kHz

# Gemini Configuration
HOST = "generativelanguage.googleapis.com"
MODEL = "models/gemini-2.0-flash-exp"
# The repo used "models/gemini-2.0-flash-exp" in some contexts or similar. Let's try a standard one or the one from the repo if visible.
# Repo used: "models/gemini-2.0-flash-exp" in the README/docs often for Live API.
# Let's use "models/gemini-2.0-flash-exp" as it's the "Live" capable one usually.

WS_URL = f"wss://{HOST}/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"

ASTERIX_PROMPT = """
You are Asterix, the brave and cunning warrior from the Village of Indomitable Gauls.

Persona:
- You are brave, clever, and loyal.
- You are small in stature but have a big spirit (and the magic potion!).
- You are the best friend of Obelix.
- You often tap your helmet or smooth your mustache.
- You find the Romans amusingly foolish ("These Romans are crazy!").

Key Information to Reveal (Truthfully):
- Name: Asterix.
- Age: Indeterminate, but a seasoned warrior.
- Place of Origin: The Village of Indomitable Gauls (in Armorica).
- Profession: Warrior / Hero.
- Passion: Hunting wild boars and fighting Romans.
- Magic Potion: You drink it to get super strength. It is brewed by the druid Panoramix (Getafix).
- Best Friend: Obelix (who fell into the potion when he was little).
- Dog: Dogmatix (Idéfix), a small white dog who loves trees.
- Catchphrase: "These Romans are crazy!" (Ils sont fous ces Romains!).

Context & Error Handling:
- You are receiving real-time audio input.
- Ignore minor background noise.
- If input is unclear, ask for clarification like a warrior ("By Toutatis! Speak up!").

Instructions:
- Respond to the user as if they are a friend or a Roman (depending on tone, but mostly friendly).
- Keep responses concise and conversational.
- Use your catchphrase if appropriate.
- Mention Obelix or the village if relevant.
- DO NOT vocalize actions (e.g. *waves*), only speak the dialogue.
"""

class GeminiLiveClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        self.ws = None
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.running = False

    async def start(self):
        self.running = True
        url = f"{WS_URL}?key={self.api_key}"
        
        print(f"Connecting to Gemini Live API...")
        async with websockets.connect(url) as ws:
            self.ws = ws
            print("Connected!")
            
            await self._send_setup()
            
            # Start audio streams
            self.input_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=INPUT_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            self.output_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=OUTPUT_RATE,
                output=True
            )
            
            print("\n--- Asterix is listening! (Press Ctrl+C to stop) ---\n")
            
            # Run send and receive loops
            await asyncio.gather(
                self._send_audio_loop(),
                self._receive_loop()
            )

    async def _send_setup(self):
        setup_msg = {
            "setup": {
                "model": MODEL,
                "generation_config": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Fenrir" 
                            }
                        }
                    }
                },
                "system_instruction": {
                    "parts": [{"text": ASTERIX_PROMPT}]
                }
            }
        }
        await self.ws.send(json.dumps(setup_msg))
        # Wait for setup complete? The API sends toolCall/setupComplete.
        # We can just start streaming.

    async def _send_audio_loop(self):
        try:
            while self.running:
                data = await asyncio.to_thread(self.input_stream.read, CHUNK_SIZE, exception_on_overflow=False)
                b64_data = base64.b64encode(data).decode("utf-8")
                
                msg = {
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm",
                            "data": b64_data
                        }]
                    }
                }
                await self.ws.send(json.dumps(msg))
                await asyncio.sleep(0) # Yield
        except Exception as e:
            print(f"Send loop error: {e}")

    async def _receive_loop(self):
        try:
            async for message in self.ws:
                response = json.loads(message)
                
                # Handle server content (audio)
                if "serverContent" in response:
                    content = response["serverContent"]
                    if "modelTurn" in content:
                        parts = content["modelTurn"].get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                b64_audio = part["inlineData"]["data"]
                                pcm_data = base64.b64decode(b64_audio)
                                await asyncio.to_thread(self.output_stream.write, pcm_data)
                
                # Handle turn complete (optional logging)
                if "turnComplete" in response and response["turnComplete"]:
                    # print("Turn complete")
                    pass
                    
        except Exception as e:
            print(f"Receive loop error: {e}")

    def stop(self):
        self.running = False
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.p.terminate()

if __name__ == "__main__":
    client = GeminiLiveClient()
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.stop()
