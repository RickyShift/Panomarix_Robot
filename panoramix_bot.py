import re
import os
import time
import sys
from dotenv import load_dotenv
from ElmoV2API import ElmoV2API
from llm_client import AsterixLLM
from audio_handler import AudioHandler

load_dotenv()

def clean_text_for_speech(text):
    """Removes text within asterisks (actions) for speech generation."""
    return re.sub(r'\*.*?\*', '', text).strip()

def main():
    # Configuration
    robot_ip = os.getenv("ROBOT_IP")
    if len(sys.argv) > 1:
        robot_ip = sys.argv[1]
    
    if not robot_ip:
        print("Error: ROBOT_IP not found in environment or arguments.")
        print("Usage: python panoramix_bot.py <ROBOT_IP>")
        return

    print(f"Connecting to Elmo at {robot_ip}...")
    
    # Initialize components
    try:
        robot = ElmoV2API(robot_ip)
        llm = AsterixLLM()
        audio = AudioHandler(robot_ip)
        
        # Verify connection
        status = robot.status()
        print(f"Robot Status: {status}")
        robot.set_screen(text="Asterix Online")
        
    except Exception as e:
        print(f"Initialization failed: {e}")
        return

    print("Asterix Chatbot Started. Press Ctrl+C to exit.")
    
    while True:
        try:
            print("\nWaiting for user input...")
            # 1. Start Recording
            print("Recording... (Speak now)")
            robot.set_screen(text="Listening...")
            robot.start_recording()
            time.sleep(5) # Record for 5 seconds (Adjustable)
            robot.stop_recording()
            robot.set_screen(text="Processing...")
            
            # 2. Download Audio
            print("Downloading audio...")
            if not audio.download_recording():
                print("Failed to download audio.")
                robot.set_screen(text="Error: Audio Download")
                continue
                
            # 3. Transcribe
            print("Transcribing...")
            user_text = audio.transcribe_audio()
            if not user_text:
                print("Could not understand audio.")
                robot.set_screen(text="I didn't hear you.")
                continue
            
            print(f"User said: {user_text}")
            robot.set_screen(text=f"You: {user_text[:20]}...") # Show partial text
            
            # 4. Get LLM Response
            print("Consulting the warrior (LLM)...")
            response_text = llm.get_response(user_text)
            print(f"Asterix: {response_text}")
            
            # 5. Generate Audio Response
            print("Generating voice...")
            speech_text = clean_text_for_speech(response_text)
            if audio.generate_audio(speech_text):
                # 6. Upload Audio
                print("Uploading response...")
                response_filename = "panoramix_response.mp3"
                if audio.upload_response(response_filename):
                    # 7. Play Audio & Show Text
                    print("Playing response...")
                    robot.set_screen(text=response_text)
                    robot.play_sound(response_filename)
                    
                    # Optional: Add movement
                    # robot.set_pan(10)
                    # time.sleep(0.5)
                    # robot.set_pan(-10)
                else:
                    print("Failed to upload response.")
            else:
                print("Failed to generate audio.")
                
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
