import asyncio
import time
import os
import sys
import argparse
import logging
import pygame
from dotenv import load_dotenv

# Load env before other imports
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import speech_recognition as sr
from llm_client import characterLLM
from LLM_character_prompts import Book_Expert_prompt_model
from ElmoV2API import ElmoV2API
from audio_handler import AudioHandler

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BookExpertElmo:
    def __init__(self, robot_ip):
        self.robot_ip = robot_ip
        self.elmo = ElmoV2API(robot_ip)
        self.audio_handler = AudioHandler(robot_ip)
        self.uploaded_files = []
        
        # Initialize Pygame Mixer for duration calculation (headless)
        try:
            pygame.mixer.init()
        except Exception as e:
            logging.warning(f"Pygame mixer init failed: {e}")

        # Explicitly use Book Expert
        self.prompt_model = Book_Expert_prompt_model
        logging.info(f"Initializing LLM with persona: {self.prompt_model.name}")
        self.llm = characterLLM(prompt_model=self.prompt_model)

    def calculate_audio_duration(self, file_path):
        try:
            sound = pygame.mixer.Sound(file_path)
            return sound.get_length()
        except Exception as e:
            logging.error(f"Error calculating audio duration: {e}")
            return 0

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
                except Exception as e:
                    logging.error(f"Failed to delete {f}: {e}")
            sftp.close()
        self.uploaded_files = []

    async def process_and_speak(self, user_text):
        """
        Sequential processing:
        1. Get full text from LLM.
        2. Generate Audio.
        3. Upload & Convert.
        4. Play.
        """
        logging.info(f"{self.prompt_model.name} is thinking...")
        
        try:
            # 1. Get Response (Blocking/Non-streaming for simplicity in robotic mode)
            response_text = self.llm.get_response(user_text)
            
            # Clean response just in case
            response_text = response_text.replace("\n", " ").strip()
            # Remove any accidentally generated tags
            if "[" in response_text and "]" in response_text:
                import re
                response_text = re.sub(r'\[.*?\]', '', response_text)

            logging.info(f"Response: {response_text}")

            if not response_text:
                return

            # 2. Generate Audio locally
            from gtts import gTTS
            filename = f"response_{int(time.time()*1000)}.mp3"
            local_path = filename
            
            logging.info(f"Generating Audio...")
            # Using Irish accent as per existing setup, or default en? Keeping consistent with fluid_elmo.
            tts = gTTS(response_text, lang='en', tld='ie')
            await asyncio.to_thread(tts.save, local_path)
            
            # 3. Upload to Robot
            logging.info(f"Uploading {filename}...")
            if self.audio_handler.upload_response(filename=filename, local_file=local_path):
                self.uploaded_files.append(filename) 
                
                # Convert to WAV
                filename_wav = filename.replace(".mp3", ".wav")
                logging.info(f"Converting to WAV...")
                if self.audio_handler.convert_mp3_to_wav(filename, filename_wav):
                    self.uploaded_files.append(filename_wav)
                
                    # Calculate Duration (Original / 0.85 due to asetrate)
                    original_duration = self.calculate_audio_duration(local_path)
                    duration = original_duration / 0.85
                    
                    # 4. Play
                    logging.info(f"Playing ({duration:.2f}s)...")
                    # No set_screen call here!
                    self.elmo.set_volume(60)
                    self.elmo.play_sound(filename_wav)
                    
                    # Wait for playback + buffer
                    await asyncio.sleep(duration + 0.5)
                else:
                    logging.error("Failed to convert audio on robot.")
            else:
                logging.error("Failed to upload audio file.")
            
            # Cleanup local
            if os.path.exists(local_path):
                os.remove(local_path)

        except Exception as e:
            logging.error(f"Error in process_and_speak: {e}")

    def run(self):
        print(f"\n--- {self.prompt_model.name} is ready on Robot {self.robot_ip} ---")
        print("Note: This expert is robotic and shows no emotion.")
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
                
                # Download & Transcribe
                print(">> Downloading audio...")
                if self.audio_handler.download_recording():
                    print(">> Transcribing...")
                    user_text = self.audio_handler.transcribe_audio()
                    
                    if user_text:
                        print(f"\nYou said: {user_text}\n")
                        asyncio.run(self.process_and_speak(user_text))
                    else:
                        print(">> Could not understand audio.")
                else:
                    print(">> Failed to download recording.")
            
            except KeyboardInterrupt:
                print("\nGoodbye!")
                try:
                    self.cleanup_remote_files()
                    self.audio_handler.close()
                except: pass
                break
            except Exception as e:
                logging.error(f"Loop Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Book Expert Asterix on Elmo Robot")
    parser.add_argument("robot_ip", help="IP address of the Elmo robot")
    
    args = parser.parse_args()
    
    handler = BookExpertElmo(args.robot_ip)
    handler.run()
