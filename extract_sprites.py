
import cv2
import numpy as np
import os

# Configuration
INPUT_IMAGE = r"C:/Users/shueb/.gemini/antigravity/brain/7ba848d2-08c0-4220-bcdc-e72f04b01293/uploaded_image_1765449021917.jpg"
OUTPUT_DIR = "extracted_emotions"

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 1. Load Image
    img = cv2.imread(INPUT_IMAGE)
    if img is None:
        print("Failed to load image.")
        return

    # 2. Preprocess (Gray -> Threshold)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Invert since background is white
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # 3. Find Contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 4. Filter and sort
    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w > 50 and h > 50: # Filter noise
            boxes.append((x, y, w, h))

    # Sort logic: Top to bottom, then Left to Right (Row by Row)
    # We allow a Y tolerance to group items in the same row
    boxes.sort(key=lambda b: b[1]) # Sort by Y first
    
    rows = []
    current_row = []
    last_y = -100
    
    for b in boxes:
        if b[1] > last_y + 100: # New row (approx height trigger)
            if current_row:
                current_row.sort(key=lambda b: b[0]) # Sort row by X
                rows.extend(current_row)
            current_row = [b]
            last_y = b[1]
        else:
            current_row.append(b)
    
    if current_row:
        current_row.sort(key=lambda b: b[0])
        rows.extend(current_row)

    # 5. Save Crops
    print(f"Found {len(rows)} sprites.")
    for i, (x, y, w, h) in enumerate(rows):
        # Add padding
        pad = 10
        x = max(0, x - pad)
        y = max(0, y - pad)
        w += pad * 2
        h += pad * 2
        
        crop = img[y:y+h, x:x+w]
        
        # Upscale by 3x
        crop = cv2.resize(crop, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        
        out_path = os.path.join(OUTPUT_DIR, f"sprite_{i+1}.png")
        cv2.imwrite(out_path, crop)
        print(f"Saved {out_path}")

if __name__ == "__main__":
    main()
