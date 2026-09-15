from machine import Pin
import time

motor_pins = [
    Pin(1, Pin.OUT),
    Pin(2, Pin.OUT),
    Pin(3, Pin.OUT),
    Pin(4, Pin.OUT)
]

HAND_RANGE_STEPS = 2048
STEP_DELAY_MS = 5

step_sequence = [
    [1, 1, 1, 0],
    [1, 0, 1, 1],
    [1, 1, 0, 1],
    [0, 1, 1, 1]
]

motor_step_index = 0
hand_position = 0


def set_motor_outputs(sequence):
    for i in range(4):
        motor_pins[i].value(sequence[i])


def motor_off():
    for pin in motor_pins:
        pin.value(0)


def step_motor(direction):
    global motor_step_index
    motor_step_index += direction
    motor_step_index %= 4
    set_motor_outputs(step_sequence[motor_step_index])
    time.sleep_ms(STEP_DELAY_MS)


def move_motor(steps, direction):
    for _ in range(steps):
        step_motor(direction)
    motor_off()


def move_hand_to(target_position):
    global hand_position
    target_position = int(target_position)
    difference = target_position - hand_position
    if difference > 0:
        move_motor(difference, 1)
    elif difference < 0:
        move_motor(abs(difference), -1)
    hand_position = target_position
