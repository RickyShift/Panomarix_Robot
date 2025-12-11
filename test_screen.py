
from ElmoV2API import ElmoV2API
import time

elmo = ElmoV2API("192.168.0.107")

print("Setting screen to 'normal.png'...")
elmo.set_screen(image="normal.png")
time.sleep(3)

print("Setting screen to 'thinking.png'...")
elmo.set_screen(image="thinking.png")
time.sleep(3)

print("Setting screen to 'tears.png'...")
elmo.set_screen(image="tears.png")
