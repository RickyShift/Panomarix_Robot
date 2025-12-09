
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
sentence_queue = queue.Queue()

class FluidElmoHandler:
    def __init__(self, robot_ip, persona="asterix"):
        self.robot_ip = robot_ip
        self.elmo = ElmoV2API(robot_ip)
        self.audio_handler = AudioHandler(robot_ip)
        
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

    async def generate_and_play_worker(self):
        """
        Worker that monitors the sentence queue, generates audio, 
        uploads to robot, and plays it.
        """
        while True:
            text = await asyncio.to_thread(sentence_queue.get)
            if text is None:
                break

            try:
                # 1. Generate Audio locally
                # Switching to gTTS with UK accent for better Asterix persona
                from gtts import gTTS
                
                filename = f"response_{int(time.time()*1000)}.mp3"
                local_path = filename
                
                logging.info(f"Generating Audio (gTTS Irish) locally for: {text[:20]}...")
                # tld='ie' gives an Irish accent (Celtic-ish)
                # Note: This is usually female, but EdgeTTS (Male) is blocked.
                tts = gTTS(text, lang='en', tld='ie')
                await asyncio.to_thread(tts.save, local_path)
                
                # 2. Upload to Robot
                logging.info(f"Uploading {filename} to robot...")
                if self.audio_handler.upload_response(filename=filename, local_file=local_path):
                    
                    # 3. Convert to WAV on Robot (Since play_sound needs WAV)
                    filename_wav = filename.replace(".mp3", ".wav")
                    logging.info(f"Converting to WAV on robot...")
                    if self.audio_handler.convert_mp3_to_wav(filename, filename_wav):
                    
                        # 4. Calculate Duration
                        # Duration calculation might be tricky for MP3 if pygame mixer expects WAV?
                        # But pygame supports MP3 commonly.
                        duration = self.calculate_audio_duration(local_path)
                        
                        # 5. Play on Robot
                        self.elmo.set_volume(60) # User requested +10% (so 60%)
                        logging.info(f"Playing {filename_wav} on robot ({duration:.2f}s)...")
                        self.elmo.play_sound(filename_wav)
                                            
                        # 6. Wait for playback to finish
                        await asyncio.sleep(duration + 0.2)
                    else:
                        logging.error("Failed to convert audio dict on robot.")
                else:
                    logging.error("Failed to upload audio file.")
                
                # Cleanup
                if os.path.exists(local_path):
                    os.remove(local_path)

            except Exception as e:
                logging.error(f"Error in generate_and_play_worker: {e}")
            
            sentence_queue.task_done()

    def clean_text_for_speech(self, text):
        return re.sub(r'\*.*?\*', '', text).strip()

    async def process_llm_response(self, user_text):
        """Streams response and feeds the audio worker."""
        logging.info(f"{self.prompt_model.name} is thinking...")
        
        # Start audio worker
        worker_task = asyncio.create_task(self.generate_and_play_worker())
        
        buffer = ""
        full_response = ""
        
        try:
            for chunk in self.llm.get_streaming_response(user_text):
                buffer += chunk
                full_response += chunk
                
                # Split by sentence
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        clean = self.clean_text_for_speech(sentence)
                        if clean:
                            logging.info(f"Queueing speech: {clean}")
                            sentence_queue.put(clean)
                    buffer = sentences[-1]
            
            # Flush buffer
            if buffer:
                clean = self.clean_text_for_speech(buffer)
                if clean:
                    logging.info(f"Queueing speech: {clean}")
                    sentence_queue.put(clean)
        
        except Exception as e:
            logging.error(f"LLM Error: {e}")

        # Setup cleanup
        logging.info("LLM generation finished. Waiting for audio playback...")
        sentence_queue.put(None) # Signal worker to stop
        await worker_task
        logging.info("Audio playback finished.")

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
                    # Note: download_recording saves to self.audio_handler.local_recording_path
                    print(">> Transcribing...")
                    # Hack: The AudioHandler class in audio_handler.py has local_recording_path hardcoded
                    # We need to make sure we use the same one.
                    user_text = self.audio_handler.transcribe_audio()
                    
                    if user_text:
                        print(f"\nYou said: {user_text}\n")
                        # Process
                        asyncio.run(self.process_llm_response(user_text))
                    else:
                        print(">> Could not understand audio.")
                else:
                    print(">> Failed to download recording.")
            
            except KeyboardInterrupt:
                print("\nGoodbye!")
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
