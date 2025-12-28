import asyncio
import time
import datetime
import os
import sys
import logging
import pyttsx3
import threading
import speech_recognition as sr
from dotenv import load_dotenv

# Load env variables (for GEMINI_API_KEY)
load_dotenv()

# Add current directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_client import characterLLM
from LLM_character_prompts import Book_Expert_prompt_model

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LocalBookExpert:
    def __init__(self):
        self.start_time = time.time()
        
        # Initialize LLM
        self.prompt_model = Book_Expert_prompt_model
        logging.info(f"Initializing LLM with persona: {self.prompt_model.name}")
        self.llm = characterLLM(prompt_model=self.prompt_model)
        
        # Initialize Reconizer
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.energy_threshold = 300
        
        # Runtime file
        self.runtime_file = "runtime.txt"
        
        # Statistics
        self.stt_count = 0

    def setup_voice(self, engine):
        """Configures the TTS voice to sound somewhat robotic or male."""
        try:
            voices = engine.getProperty('voices')
            desired_voice = None
            for v in voices:
                if "david" in v.name.lower():
                    desired_voice = v.id
                    break
            if not desired_voice and len(voices) > 0:
                desired_voice = voices[0].id
            
            if desired_voice:
                engine.setProperty('voice', desired_voice)
            
            engine.setProperty('rate', 130) # Slightly slower
            engine.setProperty('volume', 1.0)
        except Exception as e:
            logging.error(f"Error setting up voice: {e}")

    def speak(self, text):
        """Speaks the text using pyttsx3."""
        if not text or not text.strip():
            return

        logging.info(f"Speaking: {text}")
        try:
            # Re-initialize engine for each speak call to prevent loop issues
            engine = pyttsx3.init()
            self.setup_voice(engine)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            logging.error(f"Error in TTS: {e}")

    def listen(self):
        """Listens to the microphone and transcribes."""
        with sr.Microphone() as source:
            print("\n>> Listening... (Speak now)")
            try:
                # Adjust for ambient noise briefly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
                print(">> Processing audio...")
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.WaitTimeoutError:
                logging.info("Listening timed out (no speech detected).")
                return None
            except sr.UnknownValueError:
                logging.info("Could not understand audio.")
                return None
            except sr.RequestError as e:
                logging.error(f"Could not request results; {e}")
                return None
            except Exception as e:
                logging.error(f"Error listening: {e}")
                return None

    def save_runtime(self):
        """Calculates and saves the total run time to a file."""
        elapsed = time.time() - self.start_time
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.runtime_file, "a") as f:
                f.write(f"[{timestamp}] Session Duration: {elapsed:.2f} seconds | STT Transcriptions: {self.stt_count}\n")
            logging.info(f"Saved runtime ({elapsed:.2f}s) and STT count ({self.stt_count}) to {self.runtime_file}")
        except Exception as e:
            logging.error(f"Failed to save runtime: {e}")

    def run(self):
        print(f"\n--- {self.prompt_model.name} (Local Version) ---")
        print("1. Press ENTER to start listening cycle.")
        print("2. Speak your query.")
        print("3. Press Ctrl+C to Exit.\n")

        while True:
            try:
                input(">> Press ENTER to speak...")
                user_text = self.listen()
                
                if user_text:
                    self.stt_count += 1
                    print(f"\nYou said: {user_text}\n")
                    
                    # Get LLM Response
                    logging.info("Thinking...")
                    response = self.llm.get_response(user_text)
                    
                    # Clean response
                    if response:
                        import re
                        response = response.replace("\n", " ").strip()
                        response = re.sub(r'\[.*?\]', '', response).strip() # Remove staging instructions and strip again
                        
                        if response:
                            print(f"Bot: {response}")
                            self.speak(response)
                else:
                    print(">> Didn't catch that. Try again.")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                break
        
        self.save_runtime()

if __name__ == "__main__":
    bot = LocalBookExpert()
    bot.run()
