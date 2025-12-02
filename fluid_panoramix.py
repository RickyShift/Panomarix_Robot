import asyncio
import queue
import threading
import time
import re
import os
import speech_recognition as sr
import edge_tts
import pygame
from llm_client import AsterixLLM
from dotenv import load_dotenv

load_dotenv()

# Audio Configuration
VOICE = "en-IE-ConnorNeural"

# Global queues
audio_queue = queue.Queue()
sentence_queue = queue.Queue()

def play_audio_worker():
    """Worker thread to play audio files from the queue."""
    pygame.mixer.init()
    while True:
        file_path = audio_queue.get()
        if file_path is None:
            break
        
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Cleanup
            pygame.mixer.music.unload()
            os.remove(file_path)
        except Exception as e:
            print(f"Error playing audio: {e}")
        
        audio_queue.task_done()

async def generate_audio_worker():
    """Worker to generate audio from sentences."""
    while True:
        text = await asyncio.to_thread(sentence_queue.get)
        if text is None:
            break
        
        try:
            # Generate unique filename
            filename = f"temp_{int(time.time()*1000)}.mp3"
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(filename)
            audio_queue.put(filename)
        except Exception as e:
            print(f"Error generating audio: {e}")
        
        sentence_queue.task_done()

def clean_text_for_speech(text):
    """Removes text within asterisks (actions) for speech generation."""
    return re.sub(r'\*.*?\*', '', text).strip()

async def process_response(llm, user_text):
    """Streams response from LLM and queues sentences for audio generation."""
    print("Asterix is thinking...")
    
    # Start audio generation worker
    gen_task = asyncio.create_task(generate_audio_worker())
    
    buffer = ""
    for chunk in llm.get_streaming_response(user_text):
        buffer += chunk
        # Split by sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', buffer)
        
        # Keep the last incomplete sentence in the buffer
        if len(sentences) > 1:
            for sentence in sentences[:-1]:
                clean_sentence = clean_text_for_speech(sentence)
                if clean_sentence:
                    print(f"Asterix (speaking): {clean_sentence}")
                    sentence_queue.put(clean_sentence)
            buffer = sentences[-1]
    
    # Process remaining buffer
    if buffer:
        clean_sentence = clean_text_for_speech(buffer)
        if clean_sentence:
            print(f"Asterix (speaking): {clean_sentence}")
            sentence_queue.put(clean_sentence)
            
    # Signal end of generation
    sentence_queue.put(None)
    await gen_task

def main():
    print("Initializing Asterix Fluid Chatbot...")
    
    try:
        llm = AsterixLLM()
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return

    # Start audio player thread
    player_thread = threading.Thread(target=play_audio_worker, daemon=True)
    player_thread.start()

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("\n--- Asterix is listening! (Press Ctrl+C to stop) ---\n")

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
            asyncio.run(process_response(llm, user_text))
            
            # Wait for audio to finish playing before listening again
            audio_queue.join()
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
