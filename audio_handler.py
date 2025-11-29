import os
import time
import paramiko
import speech_recognition as sr
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

class AudioHandler:
    def __init__(self, robot_ip, robot_user="idmind", robot_pass="asdf"):
        self.robot_ip = robot_ip
        self.robot_user = robot_user
        self.robot_pass = robot_pass
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Local paths
        self.local_recording_path = "temp_recording.wav"
        self.local_response_path = "temp_response.mp3" # gTTS saves as mp3
        
        # Robot paths (Assumed based on research)
        self.robot_recording_path = "/home/idmind/elmo-v2/recordings/audio.wav" # Needs verification
        self.robot_sounds_path = "/home/idmind/elmo-v2/src/static/sounds/"

    def connect_ssh(self):
        try:
            self.ssh.connect(self.robot_ip, username=self.robot_user, password=self.robot_pass)
            return True
        except Exception as e:
            print(f"SSH Connection failed: {e}")
            return False

    def download_recording(self):
        if not self.connect_ssh():
            return False
        
        try:
            sftp = self.ssh.open_sftp()
            # We need to find the latest recording. 
            # For now, assuming a fixed filename or we list files.
            # Let's try to list files in the recording directory to find the newest one if needed.
            # But for simplicity, let's assume the robot saves to a specific file or we grab the latest.
            
            # TODO: Verify exact path on robot. 
            # If we can't find it, this will fail.
            sftp.get(self.robot_recording_path, self.local_recording_path)
            sftp.close()
            self.ssh.close()
            return True
        except Exception as e:
            print(f"Failed to download recording: {e}")
            self.ssh.close()
            return False

    def upload_response(self, filename="response.mp3"):
        if not self.connect_ssh():
            return False
        
        try:
            sftp = self.ssh.open_sftp()
            local_file = self.local_response_path
            remote_file = os.path.join(self.robot_sounds_path, filename)
            sftp.put(local_file, remote_file)
            sftp.close()
            self.ssh.close()
            return True
        except Exception as e:
            print(f"Failed to upload response: {e}")
            self.ssh.close()
            return False

    def transcribe_audio(self):
        recognizer = sr.Recognizer()
        try:
            # SpeechRecognition expects WAV. gTTS produces MP3. 
            # Recordings from Elmo might be WAV.
            with sr.AudioFile(self.local_recording_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return text
        except sr.UnknownValueError:
            return None # Could not understand
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            print(f"Error transcribing: {e}")
            return None

    def generate_audio(self, text):
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(self.local_response_path)
            return True
        except Exception as e:
            print(f"Error generating audio: {e}")
            return False

if __name__ == "__main__":
    # Test
    handler = AudioHandler("192.168.1.100") # Mock IP
    # handler.generate_audio("Hello, I am Panoramix.")
