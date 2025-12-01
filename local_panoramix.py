import os
import time
import speech_recognition as sr
from gtts import gTTS
from llm_client import PanoramixLLM
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

def play_audio(filename):
    """Plays an audio file using the default system player."""
    if os.name == 'nt':  # Windows
        os.startfile(filename)
        # Wait a bit for the player to open, but we can't easily know when it finishes
        # A better approach for a loop is to use a library like playsound or pygame,
        # but os.startfile is simplest for now without extra heavy deps.
        # Let's try to use playsound if available, or fallback.
        time.sleep(1) 
    else:
        # Mac/Linux
        os.system(f"open {filename}" if os.name == 'posix' else f"xdg-open {filename}")

def main():
    print("Initializing Panoramix Local Chatbot...")
    
    try:
        llm = PanoramixLLM()
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        print("Make sure you have a .env file with GEMINI_API_KEY.")
        return

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("\n--- Panoramix is listening! (Press Ctrl+C to stop) ---\n")

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

            print("Consulting the spirits...")
            response_text = llm.get_response(user_text)
            print(f"Panoramix: {response_text}")

            print("Generating voice...")
            tts = gTTS(text=response_text, lang='en', slow=False)
            
            # Save to a temporary file to avoid permission issues or conflicts
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_filename = fp.name
            
            tts.save(temp_filename)
            
            print("Playing response...")
            play_audio(temp_filename)
            
            # Wait a bit before listening again to avoid picking up the robot's voice
            # This is a simple heuristic.
            time.sleep(len(response_text) / 10) 

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
