
import asyncio
import queue
import threading
import time
import re
import os
import sys
import argparse
import logging
import pygame
from dotenv import load_dotenv

# Load env before other imports that might need it
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import speech_recognition as sr
import edge_tts
from llm_client import characterLLM
from LLM_character_prompts import Asterix_prompt_model, Book_Expert_prompt_model
from ElmoV2API import ElmoV2API
from audio_handler import AudioHandler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Audio Configuration
VOICE = "en-US-AriaNeural" # Changed from en-IE-ConnorNeural which was failing

# Global queues
preparation_queue = queue.Queue() # From LLM -> Prep
playback_queue = queue.Queue()    # From Prep -> Playback

class FluidElmoHandler:
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
        
        # Initialize Pygame Mixer for duration calculation (headless)
        try:
            pygame.mixer.init()
        except Exception as e:
            logging.warning(f"Pygame mixer init failed (non-critical if only checking duration?): {e}")

        # Choose Persona
        if persona == "expert":
            self.prompt_model = Book_Expert_prompt_model
        else:
            self.prompt_model = Asterix_prompt_model
            
        logging.info(f"Initializing LLM with persona: {self.prompt_model.name}")
        self.llm = characterLLM(prompt_model=self.prompt_model)

    def calculate_audio_duration(self, file_path):
        try:
            sound = pygame.mixer.Sound(file_path)
            return sound.get_length()
        except Exception as e:
            logging.error(f"Error calculating audio duration: {e}")
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
                
                logging.info(f"[Prep] Generating Audio for: {text[:20]}...")
                tts = gTTS(text, lang='en', tld='ie')
                await asyncio.to_thread(tts.save, local_path)
                
                # 2. Upload to Robot
                logging.info(f"[Prep] Uploading {filename}...")
                if self.audio_handler.upload_response(filename=filename, local_file=local_path):
                    self.uploaded_files.append(filename) # Track for cleanup
                    
                    # 3. Convert to WAV on Robot
                    filename_wav = filename.replace(".mp3", ".wav")
                    logging.info(f"[Prep] Converting to WAV...")
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
                        logging.error("Failed to convert audio dict on robot.")
                else:
                    logging.error("Failed to upload audio file.")
                
                # Cleanup local file (robot has copy)
                if os.path.exists(local_path):
                    os.remove(local_path)

            except Exception as e:
                logging.error(f"Error in preparation_worker: {e}")
            
            preparation_queue.task_done()
    
    def cleanup_remote_files(self):
        """Deletes all uploaded MP3 and WAV files from the robot."""
        if not self.uploaded_files:
            return
            
        logging.info(f"Cleaning up {len(self.uploaded_files)} files on robot...")
        if self.audio_handler.connect_ssh():
            sftp = self.audio_handler.ssh.open_sftp()
            for f in self.uploaded_files:
                try:
                    remote_path = os.path.join(self.audio_handler.robot_sounds_path, f)
                    sftp.remove(remote_path)
                    # logging.info(f"Deleted {f}")
                except Exception as e:
                    logging.error(f"Failed to delete {f}: {e}")
            sftp.close()
        self.uploaded_files = []

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
                    logging.info(f"[Play] Setting screen to: {emotion}")
                    self.elmo.set_screen(image=emotion)
                
                self.elmo.set_volume(60)
                logging.info(f"[Play] Playing {wav_file} ({duration:.2f}s)...")
                self.elmo.play_sound(wav_file)
                
                # Wait for playback to finish
                # Increased buffer to avoid race conditions on robot audio device
                await asyncio.sleep(duration + 0.5)
                
            except Exception as e:
                logging.error(f"Error in playback_worker: {e}")
                
            playback_queue.task_done()

    def clean_text_for_speech(self, text):
        return re.sub(r'\*.*?\*', '', text).strip()

    async def process_llm_response(self, user_text):
        """Streams response and feeds the prep worker."""
        logging.info(f"{self.prompt_model.name} is thinking...")
        
        # Start workers
        prep_task = asyncio.create_task(self.preparation_worker())
        play_task = asyncio.create_task(self.playback_worker())
        
        buffer = ""
        full_response = ""
        current_emotion_image = None
        
        emotion_sent = False # To ensure we set the screen at least once if tag found
        
        try:
            for chunk in self.llm.get_streaming_response(user_text):
                buffer += chunk
                full_response += chunk
                
                # Check for emotions in buffer
                if current_emotion_image is None:
                    match = re.search(r'\[(HAPPY|SAD|ANGRY|SURPRISED|THINKING|CONFUSED|NEUTRAL)\]', buffer)
                    if match:
                        emotion = match.group(1)
                        current_emotion_image = self.EMOTION_MAP.get(emotion)
                        buffer = buffer.replace(match.group(0), "")
                        logging.info(f"Detected emotion: {emotion} -> {current_emotion_image}")

                # Split by sentence
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        clean = self.clean_text_for_speech(sentence)
                        if clean:
                            logging.info(f"Queueing prep: {clean}")
                            img = current_emotion_image if not emotion_sent else None
                            preparation_queue.put((clean, img))
                            if img: emotion_sent = True
                            
                    buffer = sentences[-1]
            
            if buffer:
                clean = self.clean_text_for_speech(buffer)
                if clean:
                    logging.info(f"Queueing prep: {clean}")
                    img = current_emotion_image if not emotion_sent else None
                    preparation_queue.put((clean, img))
        
        except Exception as e:
            logging.error(f"LLM Error: {e}")

        # Signal end
        logging.info("LLM generation finished. Waiting for playback...")
        preparation_queue.put(None) # Signal prep worker to stop
        await prep_task
        await play_task
        logging.info("All playback finished.")
        
        # Reset to neutral?
        # self.elmo.set_screen(image="asterix_neutral.png")

    def run(self):
        print(f"\n--- {self.prompt_model.name} is ready on Robot {self.robot_ip} ---")
        print("Interaction Guide:")
        print("1. Press ENTER to START RECORDING.")
        print("2. Speak to the robot.")
        print("3. Press ENTER again to STOP RECORDING.")
        print("4. Press Ctrl+C to Exit.\n")

        while True:
            try:
                input(">> Press ENTER to START recording...")
                print(">> [RECORDING] Speaking now...")
                self.elmo.start_recording()
                
                input(">> Press ENTER to STOP recording...")
                self.elmo.stop_recording()
                print(">> [STOPPED] Processing...")
                
                # Download
                print(">> Downloading audio...")
                if self.audio_handler.download_recording():
                    # Transcribe
                    print(">> Transcribing...")
                    user_text = self.audio_handler.transcribe_audio()
                    
                    if user_text:
                        # Common corrections for Asterix
                        replacements = {
                            "aesthetics": "Asterix",
                            "asterisk": "Asterix",
                            "astrix": "Asterix"
                        }
                        for wrong, right in replacements.items():
                            if wrong in user_text.lower():
                                user_text = re.sub(wrong, right, user_text, flags=re.IGNORECASE)

                        print(f"\nYou said: {user_text}\n")
                        # Process
                        asyncio.run(self.process_llm_response(user_text))
                    else:
                        print(">> Could not understand audio.")
                else:
                    print(">> Failed to download recording.")
            
            except KeyboardInterrupt:
                print("\nGoodbye!")
                try:
                    self.elmo.set_screen(image="normal.png")
                    self.cleanup_remote_files()
                    self.audio_handler.close()
                except: pass
                break
            except Exception as e:
                logging.error(f"Loop Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fluid Asterix on Elmo Robot")
    parser.add_argument("robot_ip", help="IP address of the Elmo robot")
    parser.add_argument("--persona", default="asterix", choices=["asterix", "expert"], help="Persona to use")
    
    args = parser.parse_args()
    
    handler = FluidElmoHandler(args.robot_ip, args.persona)
    handler.run()
