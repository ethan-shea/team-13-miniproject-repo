# ============================================================
# TIMER
# ============================================================

import time
import motor

PRESETS = [15, 20, 25, 30]
preset_index = 0

STATE_IDLE = 0
STATE_RUNNING = 1
STATE_FINISHED = 2

state = STATE_IDLE

selected_minutes = PRESETS[preset_index]

timer_duration_ms = selected_minutes * 60 * 1000
remaining_ms = timer_duration_ms

last_update = time.ticks_ms()


def change_preset():
    global preset_index
    global selected_minutes

    preset_index += 1

    if preset_index >= len(PRESETS):
        preset_index = 0

    selected_minutes = PRESETS[preset_index]

    print("Selected:", selected_minutes, "minutes")


def start_timer():
    global state
    global timer_duration_ms
    global remaining_ms
    global last_update

    timer_duration_ms = selected_minutes * 60 * 1000
    remaining_ms = timer_duration_ms

    # Move hand to full position
    motor.move_hand_to(motor.HAND_RANGE_STEPS)
    last_update = time.ticks_ms()
    state = STATE_RUNNING

    print("Timer started:", selected_minutes, "minutes")


def reset_timer():
    global state, timer_duration_ms, remaining_ms, last_update
    motor.move_hand_to(0)
    timer_duration_ms = selected_minutes * 60 * 1000
    remaining_ms = timer_duration_ms
    last_update = time.ticks_ms()
    state = STATE_IDLE

    print("Timer reset")
