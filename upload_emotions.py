
from audio_handler import AudioHandler
import os
import glob

# Configuration
ROBOT_IP = "192.168.0.107"
EMOTIONS_DIR = "emotions"

def main():
    handler = AudioHandler(ROBOT_IP)
    
    print(f"Connecting to {ROBOT_IP}...")
    
    # Get all png files in emotions dir
    files = glob.glob(os.path.join(EMOTIONS_DIR, "*.png"))
    
    if not files:
        print(f"No PNG files found in {EMOTIONS_DIR}")
        return

    print(f"Found {len(files)} images to upload.")
    
    for file_path in files:
        filename = os.path.basename(file_path)
        print(f"Uploading {filename}...")
        if handler.upload_image(filename, file_path):
            print("  Success")
        else:
            print("  Failed")

    print("\nDone! You can verify by checking /home/idmind/elmo-v2/src/static/images/ on the robot.")

if __name__ == "__main__":
    main()
