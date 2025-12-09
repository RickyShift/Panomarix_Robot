
import os
from audio_handler import AudioHandler

handler = AudioHandler("192.168.0.107")
handler.robot_sounds_path = "/home/idmind/elmo-v2/src/static/sounds/" # Verify this matches
with open("TEST_AGENCY.txt", "w") as f:
    f.write("Antigravity was here")

print("Uploading...")
if handler.upload_response(filename="TEST_AGENCY.txt", local_file="TEST_AGENCY.txt"):
    print("Upload returned True")
else:
    print("Upload returned False")
