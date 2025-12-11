import os
import time
import paramiko
import speech_recognition as sr
import asyncio
import pygame
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()

class AudioHandler:
    def __init__(self, robot_ip=None, robot_user="idmind", robot_pass="asdf"):
        self.robot_ip = robot_ip
        self.robot_user = robot_user
        self.robot_pass = robot_pass
        self.ssh = None
        
        # Local paths
        self.local_recording_path = "temp_recording.wav"
        self.local_response_path = "temp_response.mp3" 
        
        # Robot paths
        self.robot_recording_path = "/home/idmind/elmo-v2/src/static/sounds/mic.wav"
        self.robot_sounds_path = "/home/idmind/elmo-v2/src/static/sounds/"
        self.robot_images_path = "/home/idmind/elmo-v2/src/static/images/"

        # Initialize Pygame Mixer for local playback
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"Warning: Pygame mixer init failed: {e}")
        
        # Initial connection
        if self.robot_ip:
            self.connect_ssh()

    def connect_ssh(self):
        if self.ssh and self.ssh.get_transport() and self.ssh.get_transport().is_active():
            return True
            
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.robot_ip, username=self.robot_user, password=self.robot_pass)
            return True
        except Exception as e:
            print(f"SSH Connection failed: {e}")
            self.ssh = None
            return False

    def close(self):
        if self.ssh:
            self.ssh.close()

    def download_recording(self):
        if not self.connect_ssh():
            return False
        try:
            sftp = self.ssh.open_sftp()
            sftp.get(self.robot_recording_path, self.local_recording_path)
            sftp.close()
            return True
        except Exception as e:
            print(f"Failed to download recording: {e}")
            return False

    def upload_response(self, filename="response.mp3", local_file=None):
        if not self.connect_ssh():
            return False
        try:
            sftp = self.ssh.open_sftp()
            if local_file is None:
                local_file = self.local_response_path
            
            remote_file = os.path.join(self.robot_sounds_path, filename)
            sftp.put(local_file, remote_file)
            sftp.close()
            return True
        except Exception as e:
            print(f"Failed to upload response: {e}")
            return False

    def upload_image(self, filename, local_path):
        if not self.connect_ssh():
            return False
        try:
            sftp = self.ssh.open_sftp()
            remote_file = os.path.join(self.robot_images_path, filename)
            sftp.put(local_path, remote_file)
            sftp.close()
            return True
        except Exception as e:
            print(f"Failed to upload image: {e}")
            return False

    def convert_mp3_to_wav(self, filename_mp3, filename_wav):
        """Converts mp3 to wav on the robot using ffmpeg/mpg123"""
        if not self.connect_ssh():
            return False
        try:
            remote_mp3 = os.path.join(self.robot_sounds_path, filename_mp3)
            remote_wav = os.path.join(self.robot_sounds_path, filename_wav)
            
            # Using 24000Hz as base for gTTS. 0.85 factor lowers pitch and speed.
            command = f"/usr/bin/ffmpeg -y -i {remote_mp3} -af \"asetrate=24000*0.85,aresample=24000\" {remote_wav}"
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            return exit_status == 0
        except Exception as e:
            print(f"Failed to convert audio: {e}")
            return False

    def transcribe_audio(self):
        recognizer = sr.Recognizer()
        # Tune for different speeds
        recognizer.pause_threshold = 0.8 # Default is 0.8. Maybe 1.0?
        recognizer.energy_threshold = 300 # Dynamic adjustment is default True
        
        try:
            with sr.AudioFile(self.local_recording_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return text
        except sr.UnknownValueError:
            return None 
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            print(f"Error transcribing: {e}")
            return None

    async def generate_audio_file(self, text, filename=None):
        """Generates audio using gTTS (Irish accent) and saves to filename."""
        if filename is None:
            filename = self.local_response_path
            
        try:
            # tld='ie' gives an Irish accent
            tts = gTTS(text, lang='en', tld='ie')
            await asyncio.to_thread(tts.save, filename)
            return True
        except Exception as e:
            print(f"Error generating audio file: {e}")
            return False

    def play_audio_file(self, file_path):
        """Plays an audio file locally using pygame."""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            return True
        except Exception as e:
            print(f"Error playing audio file: {e}")
            return False

if __name__ == "__main__":
    # Test
    handler = AudioHandler() # Local mode
    # asyncio.run(handler.generate_audio_file("Hello, I am Asterix.", "test_local.mp3"))
    # handler.play_audio_file("test_local.mp3")
