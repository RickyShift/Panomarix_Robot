import asyncio
import queue
import threading
import time
import re
import os
import glob
import speech_recognition as sr
from llm_client import characterLLM
from LLM_character_prompts import Asterix_prompt_model, Book_Expert_prompt_model
from dotenv import load_dotenv
from audio_handler import AudioHandler
from ElmoV2API import ElmoV2API
from find_elmo_ip import get_robot_ip

load_dotenv()

# Global queues
preparation_queue = queue.Queue() # From LLM -> Prep
playback_queue = queue.Queue()    # From Prep -> Playback

class FluidAsterixHybrid:
    EMOTION_MAP = {
        "HAPPY": "asterix_happy.png",
        "SAD": "asterix_sad.png",
        "ANGRY": "asterix_angry.png",
        "SURPRISED": "asterix_surprised.png",
        "THINKING": "asterix_thinking.png",
        "CONFUSED": "asterix_confused.png",
        "NEUTRAL": "asterix_neutral.png"
    }

    def __init__(self, robot_ip, persona="asterix"):
        self.robot_ip = robot_ip
        self.elmo = ElmoV2API(robot_ip)
        self.audio_handler = AudioHandler(robot_ip)
        self.uploaded_files = []
        
        # Initialize Pygame Mixer for duration calculation
        try:
            import pygame
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: Pygame mixer init failed: {e}")

        # Choose Persona
        if persona == "expert":
            self.prompt_model = Book_Expert_prompt_model
        else:
            self.prompt_model = Asterix_prompt_model
            
        print(f"Initializing Fluid Chatbot as {self.prompt_model.name} (Hybrid Mode: Local Mic -> Robot Output)...")
        self.llm = characterLLM(prompt_model=self.prompt_model)

    def upload_emotions(self):
        print("Uploading emotion images to robot...")
        files = glob.glob(os.path.join("emotions", "*.png"))
        for file_path in files:
            filename = os.path.basename(file_path)
            # plain upload without re-connecting every time if possible, but AudioHandler manages connection
            self.audio_handler.upload_image(filename, file_path)
        print("Emotions uploaded.")

    def calculate_audio_duration(self, file_path):
        import pygame
        try:
            sound = pygame.mixer.Sound(file_path)
            return sound.get_length()
        except Exception as e:
            print(f"Error calculating audio duration: {e}")
            return 0

    async def preparation_worker(self):
        """
        Worker 1: Consumes text, generates audio, uploads, converts.
        Puts ready-to-play items into playback_queue.
        """
        while True:
            item = await asyncio.to_thread(preparation_queue.get)
            if item is None:
                playback_queue.put(None) # Signal playback to stop
                break
            
            # Handle tuple (text, emotion_image) or just text
            if isinstance(item, tuple):
                text, emotion_image = item
            else:
                text = item
                emotion_image = None
            
            try:
                # 1. Generate Audio locally
                from gtts import gTTS
                filename = f"response_{int(time.time()*1000)}.mp3"
                local_path = filename
                
                # tld='ie' gives an Irish accent for Asterix
                tts = gTTS(text, lang='en', tld='ie')
                await asyncio.to_thread(tts.save, local_path)
                
                # 2. Upload to Robot
                if self.audio_handler.upload_response(filename=filename, local_file=local_path):
                    self.uploaded_files.append(filename) # Track for cleanup
                    
                    # 3. Convert to WAV on Robot
                    filename_wav = filename.replace(".mp3", ".wav")
                    if self.audio_handler.convert_mp3_to_wav(filename, filename_wav):
                        self.uploaded_files.append(filename_wav) # Track for cleanup
                    
                        # 4. Calculate Duration
                        # CRITICAL: We pitch-shifted by 0.85 (asetrate), making audio Slower/Longer.
                        # Real Duration = Original / 0.85
                        original_duration = self.calculate_audio_duration(local_path)
                        duration = original_duration / 0.85
                        
                        # 5. Push to Playback Queue
                        playback_queue.put({
                            "wav": filename_wav,
                            "duration": duration,
                            "emotion": emotion_image
                        })
                    else:
                        print("Failed to convert audio on robot.")
                else:
                    print("Failed to upload audio file.")
                
                # Cleanup local file
                if os.path.exists(local_path):
                    os.remove(local_path)

            except Exception as e:
                print(f"Error in preparation_worker: {e}")
            
            preparation_queue.task_done()

    async def playback_worker(self):
        """
        Worker 2: Consumes ready audio, sets screen, plays.
        """
        while True:
            item = await asyncio.to_thread(playback_queue.get)
            if item is None:
                break
            
            try:
                wav_file = item["wav"]
                duration = item["duration"]
                emotion = item["emotion"]
                
                if emotion:
                    print(f"[Play] Setting screen to: {emotion}")
                    self.elmo.set_screen(image=emotion)
                
                self.elmo.set_volume(50)
                print(f"[Play] Playing on Robot...")
                self.elmo.play_sound(wav_file)
                
                # Wait for playback to finish
                await asyncio.sleep(duration + 0.2)
                
            except Exception as e:
                print(f"Error in playback_worker: {e}")
                
            playback_queue.task_done()

    def clean_text_for_speech(self, text):
        return re.sub(r'\*.*?\*', '', text).strip()

    async def process_response(self, user_text):
        """Streams response from LLM and queues sentences for audio generation."""
        print(f"{self.prompt_model.name} is thinking...")
        
        # Start workers
        prep_task = asyncio.create_task(self.preparation_worker())
        play_task = asyncio.create_task(self.playback_worker())
        
        buffer = ""
        current_emotion_image = None
        emotion_sent = False 
        
        try:
            for chunk in self.llm.get_streaming_response(user_text):
                buffer += chunk
                
                # Check for emotions in buffer
                # Format: [HAPPY], [SAD], etc.
                if current_emotion_image is None or not emotion_sent:
                    match = re.search(r'\[(HAPPY|SAD|ANGRY|SURPRISED|THINKING|CONFUSED|NEUTRAL)\]', buffer)
                    if match:
                        emotion = match.group(1)
                        current_emotion_image = self.EMOTION_MAP.get(emotion)
                        buffer = buffer.replace(match.group(0), "")
                        print(f"Detected emotion: {emotion} -> {current_emotion_image}")

                # Split by sentence endings
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        clean_sentence = self.clean_text_for_speech(sentence)
                        if clean_sentence:
                            print(f"{self.prompt_model.name} (speaking): {clean_sentence}")
                            
                            # Decide on emotion for this sentence
                            img = current_emotion_image if not emotion_sent else None
                            preparation_queue.put((clean_sentence, img))
                            if img: emotion_sent = True
                            
                    buffer = sentences[-1]
            
            # Process remaining buffer
            if buffer:
                clean_sentence = self.clean_text_for_speech(buffer)
                if clean_sentence:
                    print(f"{self.prompt_model.name} (speaking): {clean_sentence}")
                    img = current_emotion_image if not emotion_sent else None
                    preparation_queue.put((clean_sentence, img))
                    
        except Exception as e:
            print(f"LLM Error: {e}")
            
        # Signal end of generation
        preparation_queue.put(None)
        await prep_task
        await play_task
        
        # Reset to Neutral after full response?
        # self.elmo.set_screen(image="asterix_neutral.png")

    def run(self):
        # 1. Upload emotions first
        # self.upload_emotions() # Only needed once or if changed, can comment out if slow

        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        print(f"\n--- {self.prompt_model.name} is listening! (Press Ctrl+C to stop) ---\n")

        while True:
            try:
                with mic as source:
                    print("Listening... (Speak now)")
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source)

                print("Transcribing...")
                try:
                    user_text = recognizer.recognize_google(audio)
                    print(f"You said: {user_text}")
                except sr.UnknownValueError:
                    print("Could not understand audio.")
                    continue
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    continue

                # Run async processing
                asyncio.run(self.process_response(user_text))
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                try:
                    self.elmo.set_screen(image="normal.png") # Reset robot screen
                except: pass
                break
            except Exception as e:
                print(f"An error occurred: {e}")

def main(persona="asterix"):
    # 1. Find Robot
    robot_ip = get_robot_ip()
    if not robot_ip:
        print("Could not find Elmo robot. Exiting.")
        return

    # 2. Start Hybrid Handler
    bot = FluidAsterixHybrid(robot_ip, persona)
    bot.run()

if __name__ == "__main__":
    # --- CHOOSE YOUR PERSONA ---
    # To run as Asterix, use:
    main(persona="asterix")

    # To run as the Book Expert, use:
    # main(persona="expert")
