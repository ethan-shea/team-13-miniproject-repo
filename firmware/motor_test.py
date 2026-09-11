from machine import Pin
import time

pins = [
    Pin(1, Pin.OUT),  # Orange
    Pin(2, Pin.OUT),  # Pink
    Pin(3, Pin.OUT),  # Yellow
    Pin(4, Pin.OUT)   # Blue
]

# LOW = coil energized
# Correct phase order:
# Blue -> Pink -> Yellow -> Orange
sequence = [
    [1, 1, 1, 0],  # Blue
    [1, 0, 1, 1],  # Pink
    [1, 1, 0, 1],  # Yellow
    [0, 1, 1, 1]   # Orange
]

STEP_DELAY_MS = 5

for _ in range(300):
    for state in sequence:

        for i in range(4):
            pins[i].value(state[i])

        time.sleep_ms(STEP_DELAY_MS)

# Turn all coils off
for pin in pins:
    pin.value(1)

print("Done")