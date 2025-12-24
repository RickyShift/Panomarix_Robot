import asyncio
import queue
import threading
import time
import datetime
import re
import os
import speech_recognition as sr
from llm_client import characterLLM
from LLM_character_prompts import Asterix_prompt_model, Book_Expert_prompt_model
from dotenv import load_dotenv
import google.generativeai as genai
from audio_handler import AudioHandler

load_dotenv()

# Global queues
audio_queue = queue.Queue()
sentence_queue = queue.Queue()

# Initialize AudioHandler for local use (robot_ip=None)
audio_handler = AudioHandler(robot_ip=None)

def correct_transcription(text):
    """
    Uses Gemini to correct transcription errors based on Asterix context.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "You are a transcription corrector for a voice assistant acting as Asterix the Gaul. "
            "The user might say things like '12 tasker' instead of '12 tasks', or 'call' instead of 'The'. "
            "Correct the following text to match the context of the Asterix universe (names, places, terms). "
            "If the text seems roughly correct or generic, leave it alone. "
            "Return ONLY the corrected text. "
            f"Input text: '{text}'"
        )
        response = model.generate_content(prompt)
        corrected = response.text.strip()
        return corrected
    except Exception as e:
        print(f"Correction failed: {e}")
        return text

def play_audio_worker():
    """Worker thread to play audio files from the queue using AudioHandler."""
    while True:
        file_path = audio_queue.get()
        if file_path is None:
            break
        
        try:
            # Use AudioHandler to play audio locally
            audio_handler.play_audio_file(file_path)
            
            # Cleanup
            if os.path.exists(file_path):
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
            
            # Use AudioHandler to generate audio
            success = await audio_handler.generate_audio_file(text, filename)
            
            if success:
                audio_queue.put(filename)
            else:
                print(f"Failed to generate audio for: {text}")

        except Exception as e:
            print(f"Error generating audio: {e}")
        
        sentence_queue.task_done()

def clean_text_for_speech(text):
    """Removes text within asterisks (actions) and square brackets (emotions) for speech."""
    text = re.sub(r'\*.*?\*', '', text) # Remove *actions*
    text = re.sub(r'\[.*?\]', '', text) # Remove [EMOTIONS]
    return text.strip()

async def process_response(llm, user_text):
    """Streams response from LLM and queues sentences for audio generation."""
    print(f"{llm.prompt_model.name} is thinking...")
    
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
                    print(f"{llm.prompt_model.name} (speaking): {clean_sentence}")
                    sentence_queue.put(clean_sentence)
            buffer = sentences[-1]
    
    # Process remaining buffer
    if buffer:
        clean_sentence = clean_text_for_speech(buffer)
        if clean_sentence:
            print(f"{llm.prompt_model.name} (speaking): {clean_sentence}")
            sentence_queue.put(clean_sentence)
            
    # Signal end of generation
    sentence_queue.put(None)
    await gen_task

def main(persona="asterix"):
    """
    Main function to run the chatbot.
    :param persona: "asterix" or "expert"
    """
    start_time = time.time()
    
    stt_count = 0
    
    if persona == "expert":
        prompt_model = Book_Expert_prompt_model
    else:
        prompt_model = Asterix_prompt_model

    print(f"Initializing Fluid Chatbot as {prompt_model.name} (Local Mode)...")
    
    try:
        llm = characterLLM(prompt_model=prompt_model)
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return

    # Start audio player thread
    player_thread = threading.Thread(target=play_audio_worker, daemon=True)
    player_thread.start()

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print(f"\n--- {prompt_model.name} is listening! (Press Ctrl+C to stop) ---\n")

    try:
        while True:
            try:
                input(">> Press ENTER to speak...")
                with mic as source:
                    print("Listening... (Speak now)")
                    recognizer.adjust_for_ambient_noise(source)
                    audio = recognizer.listen(source)

                print("Transcribing...")
                try:
                    user_text = recognizer.recognize_google(audio)
                    print(f"Original: {user_text}")
                    
                    # Context Correction
                    print("Adjusting context...")
                    corrected_text = correct_transcription(user_text)
                    if corrected_text.lower() != user_text.lower():
                        print(f"Corrected: {corrected_text}")
                    else:
                        print("No correction needed.")
                    
                    # Use corrected text
                    print(f"You said: {corrected_text}")
                    stt_count += 1

                except sr.UnknownValueError:
                    print("Could not understand audio.")
                    continue
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    continue

                # Run async processing
                asyncio.run(process_response(llm, corrected_text))
                
                # Wait for audio to finish playing before listening again
                audio_queue.join()
                
            except Exception as e:
                print(f"An error occurred in loop: {e}")
                
    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        # Save runtime
        end_time = time.time()
        elapsed_time = end_time - start_time
        runtime_file = "fluid_runtime.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(runtime_file, "a") as f:
                f.write(f"[{timestamp}] Session Duration: {elapsed_time:.2f} seconds | STT Transcriptions: {stt_count}\n")
            print(f"Saved runtime ({elapsed_time:.2f}s) and STT count ({stt_count}) to {runtime_file}")
            
            # Clean exit
            audio_queue.put(None)
        except Exception as e:
            print(f"Error saving runtime: {e}")

if __name__ == "__main__":
    main(persona="asterix")
