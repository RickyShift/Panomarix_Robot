
import asyncio
import queue
import time
import re
import os
import speech_recognition as sr
import edge_tts
from llm_client import characterLLM
from LLM_character_prompts import Asterix_prompt_model, Book_Expert_prompt_model
from dotenv import load_dotenv
from ElmoV2API import ElmoV2API

load_dotenv()

# --- Configuration ---
VOICE = "en-IE-ConnorNeural"
ROBOT_IP = "localhost"  # Running on the robot itself

# Paths for audio files on the robot's filesystem
# Verified from audio_handler.py
ROBOT_SOUNDS_PATH = "/home/idmind/elmo-v2/src/static/sounds/"
ROBOT_RECORDING_PATH = "/home/idmind/elmo-v2/recordings/audio.wav"

# Global queues
sentence_queue = queue.Queue()

# --- Main Application Logic ---

def clean_text_for_speech(text):
    """Removes text within asterisks (actions) for speech generation."""
    return re.sub(r'*.*?*', '', text).strip()

async def generate_and_play_audio_worker(elmo: ElmoV2API):
    """Worker to generate audio from sentences and play them via the robot's API."""
    # This worker will now also handle playing the audio.
    # It replaces the 'play_audio_worker' from the original script.
    pass # TODO: Implement this worker

async def process_response(llm, user_text, elmo: ElmoV2API):
    """Streams response from LLM and queues sentences for audio generation."""
    print(f"{llm.prompt_model.name} is thinking...")

    # Start audio generation and playback worker
    audio_task = asyncio.create_task(generate_and_play_audio_worker(elmo))

    buffer = ""
    full_response = ""
    for chunk in llm.get_streaming_response(user_text):
        buffer += chunk
        full_response += chunk
        sentences = re.split(r'(?<=[.!?])\s+', buffer)

        if len(sentences) > 1:
            for sentence in sentences[:-1]:
                clean_sentence = clean_text_for_speech(sentence)
                if clean_sentence:
                    print(f"{llm.prompt_model.name} (speaking): {clean_sentence}")
                    sentence_queue.put(clean_sentence)
            buffer = sentences[-1]

    if buffer:
        clean_sentence = clean_text_for_speech(buffer)
        if clean_sentence:
            print(f"{llm.prompt_model.name} (speaking): {clean_sentence}")
            sentence_queue.put(clean_sentence)
    
    print(f"\n--- Full Response ---\n{full_response}\n--- End of Response ---\\n")

    # Signal end of generation
    sentence_queue.put(None)
    await audio_task

def main(persona="asterix"):
    """
    Main function to run the chatbot on the robot.
    """
    if persona == "expert":
        prompt_model = Book_Expert_prompt_model
    else:
        prompt_model = Asterix_prompt_model

    print(f"Initializing On-Robot Chatbot as {prompt_model.name}...")

    try:
        llm = characterLLM(prompt_model=prompt_model)
        elmo = ElmoV2API(robot_ip=ROBOT_IP)
    except Exception as e:
        print(f"Error initializing services: {e}")
        return

    recognizer = sr.Recognizer()

    print(f"\n--- {prompt_model.name} is ready! (Press Ctrl+C to stop) ---\n")

    while True:
        try:
            # TODO: Replace this with Elmo's recording API
            # 1. Start recording
            # 2. Wait for speech
            # 3. Stop recording
            # 4. Transcribe the saved file
            
            # Placeholder for user input for now
            user_text = input("You: ")
            if not user_text:
                continue

            # Run async processing
            asyncio.run(process_response(llm, user_text, elmo))

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # --- CHOOSE YOUR PERSONA ---
    main(persona="asterix")
