
import shutil
import os

# Hypothesis: First image (Afraid so) has Sprite 1 (Asterix) and Sprite 2 (Dog).
# So all subsequent images effectively shifted by +1 in sprite index.
MAPPING = {
    "asterix_happy.png": "sprite_8.png",      # Image 7: Enthusiastic
    "asterix_sad.png": "sprite_7.png",        # Image 6: Worried
    "asterix_angry.png": "sprite_15.png",     # Image 14: Grumpy (Row 3, item 4. Index 14. +1 = 15)
    "asterix_surprised.png": "sprite_14.png", # Image 13: Romans Crazy. (Index 13. +1 = 14). Wait.
    # Logic Verification:
    # Row 1 (Indices 1-5): Imgs 1, 2, 3, 4, 5. Sprite count: 1+1+1+1+1 = 5? NO.
    # Img 1 is split. So Sprites 1,2 -> Img 1. Sprite 3 -> Img 2. Sprite 4 -> Img 3. Sprite 5 -> Img 4. Sprite 6 -> Img 5.
    # Row 1 Sprites: 1,2,3,4,5,6 (Total 6 from Row 1?)
    # Let's count sprites in Row 1 logic. "sorted by Y then X".
    # All 5 images in Row 1 roughly same Y?
    # Img 1 (Afraid)
    # Img 2 (Hilarious)
    # Img 3 (Sardonic)
    # Img 4 (Puzzled)
    # Img 5 (Perplexed)
    # If Img 1 splits, indices: 1,2 (Img1), 3(Img2), 4(Img3), 5(Img4), 6(Img5).
    # So:
    # THINKING (Sardonic, Img 3) -> Sprite 4.
    # CONFUSED (Puzzled, Img 4) -> Sprite 5.
    
    # Row 2 (Indices 6-10): Imgs 6, 7, 8, 9, 10.
    # Start Index = 7 (Sprite 7 is Img 6 "Worried").
    # SAD (Worried, Img 6) -> Sprite 7.
    # HAPPY (Enthusiastic, Img 7) -> Sprite 8.
    # Neutral (Determined, Img 10) -> Sprite 11.
    
    # Row 3 (Indices 11-14): Imgs 11, 12, 13, 14.
    # Start Index = 12 (Sprite 12 is Img 11 "Champion").
    # Img 13 (Romans Crazy) -> Sprite 14. (SURPRISED)
    # Img 14 (Grumpy) -> Sprite 15. (ANGRY)
    
    "asterix_thinking.png": "sprite_4.png",
    "asterix_confused.png": "sprite_5.png",
    "asterix_sad.png": "sprite_7.png",
    "asterix_happy.png": "sprite_8.png",
    "asterix_neutral.png": "sprite_11.png",
    "asterix_surprised.png": "sprite_14.png", 
    "asterix_angry.png": "sprite_15.png"
}

SRC_DIR = "extracted_emotions"
DST_DIR = "emotions"

if not os.path.exists(DST_DIR):
    os.makedirs(DST_DIR)

for dest, src in MAPPING.items():
    src_path = os.path.join(SRC_DIR, src)
    dst_path = os.path.join(DST_DIR, dest)
    if os.path.exists(src_path):
        shutil.copy(src_path, dst_path)
        print(f"Mapped {src} -> {dest}")
    else:
        print(f"Missing {src}")
