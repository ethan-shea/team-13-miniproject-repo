"""Standalone MicroPython meeting timer for the Seeed XIAO ESP32-S3.

Open and run this file in Thonny with the XIAO MicroPython interpreter.
It contains the motor, buttons, LED, timer, and main loop in one file.
No other project Python files are required on the device.

HAND_RANGE_STEPS is currently a 512-step bench-test travel, not a calibrated
pointer angle. Startup establishes a phase reference, not automatic homing.
Button 1 selects 15/20/25/30 minutes while idle. Button 2 starts the timer
and resets it after completion. Stop/interrupt releases the outputs.
"""

from machine import Pin, PWM
import time



# ==================================================================
# MOTOR CONFIGURATION AND POSITION CONTROL
# ==================================================================

# GPIO numbers, not the D labels printed on the XIAO.
MOTOR_GPIO = (1, 2, 3, 4)  # Orange, Pink, Yellow, Blue; XIAO D0-D3
STEP_SEQUENCE = (
    (1, 1, 1, 0),  # Blue
    (1, 0, 1, 1),  # Pink
    (1, 1, 0, 1),  # Yellow
    (0, 1, 1, 1),  # Orange
)
STEP_DELAY_MS = 5

# Temporary bench-test travel. No pointer is installed or calibrated yet.
# Replace this with the measured zero-to-full-scale step count later.
HAND_RANGE_STEPS = 2048

# Flip this to -1 if increasing position moves the pointer the wrong way.
FORWARD_DIRECTION = 1

motor_pins = [Pin(number, Pin.OUT, value=1) for number in MOTOR_GPIO]
hand_position = 0
_phase_index = 0
_initialized = False


def motor_off():
    """Release the windings using the tested all-HIGH inactive pattern."""
    for pin in motor_pins:
        pin.value(1)


def _set_phase(index):
    # Release the old winding before energizing the next one.
    motor_off()
    for pin, value in zip(motor_pins, STEP_SEQUENCE[index]):
        pin.value(value)


def initialize():
    """Align to the first phase and establish a software zero.

    This can make a small alignment movement; it is NOT automatic homing.
    After startup, set the pointer's zero reference before pressing Start.
    """
    global hand_position, _phase_index, _initialized
    _initialized = False
    _phase_index = 0
    try:
        _set_phase(_phase_index)
        time.sleep_ms(STEP_DELAY_MS)
        hand_position = 0
        _initialized = True
    finally:
        motor_off()


def move_hand_to(target_steps):
    """Move to an absolute position in 0..HAND_RANGE_STEPS, then release.

    The phase index survives separate calls and direction changes. This
    function blocks while moving; countdown timing accounts for that time.
    After an interrupted move, restart and establish the zero again.
    """
    global hand_position, _phase_index, _initialized
    if not isinstance(target_steps, int):
        raise TypeError("target_steps must be an integer")
    if not 0 <= target_steps <= HAND_RANGE_STEPS:
        raise ValueError("target_steps is outside the configured hand range")
    if FORWARD_DIRECTION not in (1, -1):
        raise ValueError("FORWARD_DIRECTION must be 1 or -1")
    if not _initialized:
        raise RuntimeError("Call initialize() and establish zero first")

    direction = 1 if target_steps > hand_position else -1
    try:
        while hand_position != target_steps:
            _phase_index = (
                _phase_index + direction * FORWARD_DIRECTION
            ) % len(STEP_SEQUENCE)
            _set_phase(_phase_index)
            time.sleep_ms(STEP_DELAY_MS)
            hand_position += direction
    except BaseException:
        # A partial step cannot be located without position feedback.
        _initialized = False
        raise
    finally:
        motor_off()


# ==================================================================
# BUTTONS AND LED OUTPUT
# ==================================================================

button1 = Pin(5, Pin.IN, Pin.PULL_UP)  # XIAO D4; switch to GND
button2 = Pin(6, Pin.IN, Pin.PULL_UP)  # XIAO D5; switch to GND

red_led = PWM(Pin(7))    # XIAO D8
blue_led = PWM(Pin(8))   # XIAO D9
green_led = PWM(Pin(9))  # XIAO D10

red_led.freq(1000)
blue_led.freq(1000)
green_led.freq(1000)

DEBOUNCE_MS = 50


def set_leds(red, blue, green):
    # Argument order is RED, BLUE, GREEN to match the existing callers.
    red_led.duty_u16(int(red * 65535))
    blue_led.duty_u16(int(blue * 65535))
    green_led.duty_u16(int(green * 65535))


def pulse_value():
    position = time.ticks_ms() % 1000
    if position < 500:
        return position / 500
    else:
        return (1000 - position) / 500


def show_selected_preset(selected_minutes):
    brightness = pulse_value()
    if selected_minutes == 15:
        set_leds(0, 0, brightness)
    elif selected_minutes == 20:
        set_leds(0, brightness, 0)
    elif selected_minutes == 25:
        set_leds(brightness, 0, 0)
    elif selected_minutes == 30:
        set_leds(brightness, brightness, brightness)


def button_pressed(button):
    return button.value() == 0


def wait_for_release(button):
    while button_pressed(button):
        time.sleep_ms(10)
    time.sleep_ms(DEBOUNCE_MS)


# Start with a defined PWM state when the module is imported.
set_leds(0, 0, 0)


# ==================================================================
# TIMER STATE
# ==================================================================

# ============================================================
# TIMER
# ============================================================


PRESETS = [2, 20, 25, 30]
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
    move_hand_to(HAND_RANGE_STEPS)
    last_update = time.ticks_ms()
    state = STATE_RUNNING

    print("Timer started:", selected_minutes, "minutes")


def reset_timer():
    global state, timer_duration_ms, remaining_ms, last_update
    move_hand_to(0)
    timer_duration_ms = selected_minutes * 60 * 1000
    remaining_ms = timer_duration_ms
    last_update = time.ticks_ms()
    state = STATE_IDLE

    print("Timer reset")


# ==================================================================
# MAIN LOOP
# ==================================================================

def update():
    """Handle one pass through the existing button/timer/LED state machine."""
    global state, remaining_ms, last_update

    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------
    if state == STATE_IDLE:

        show_selected_preset(selected_minutes)

        # Button 1 changes preset
        if button_pressed(button1):
            time.sleep_ms(DEBOUNCE_MS)
            if button_pressed(button1):
                change_preset()
                wait_for_release(button1)

        # Button 2 starts timer
        if button_pressed(button2):
            time.sleep_ms(DEBOUNCE_MS)
            if button_pressed(button2):
                wait_for_release(button2)
                start_timer()

    # --------------------------------------------------------
    # RUNNING
    # --------------------------------------------------------
    elif state == STATE_RUNNING:

        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, last_update)

        remaining_ms -= elapsed
        last_update = now

        if remaining_ms <= 0:
            remaining_ms = 0
            move_hand_to(0)
            state = STATE_FINISHED
            print("TIME'S UP!")
            return

        # Update clock hand position
        fraction_remaining = remaining_ms / timer_duration_ms
        target_position = int(HAND_RANGE_STEPS * fraction_remaining)

        if target_position != hand_position:
            move_hand_to(target_position)

        # LED behavior
        brightness = pulse_value()

        # Final minute = red pulse
        if remaining_ms <= 60_000:
            set_leds(brightness, 0, 0)
        # Otherwise = blue pulse
        else:
            set_leds(0, brightness, 0)

    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------
    elif state == STATE_FINISHED:

        # Solid red
        set_leds(1, 0, 0)

        # Button 2 resets
        if button_pressed(button2):
            time.sleep_ms(DEBOUNCE_MS)
            if button_pressed(button2):
                wait_for_release(button2)
                reset_timer()


def run():
    try:
        initialize()
        reset_timer()
        print("Meeting timer ready")
        print("Set the pointer's zero reference before pressing Start.")
        print("Hand travel:", HAND_RANGE_STEPS, "steps (check calibration)")
        print("Selected:", selected_minutes, "minutes")

        while True:
            update()
            time.sleep_ms(10)
    finally:
        # Cleanup also runs when Thonny sends KeyboardInterrupt.
        try:
            motor_off()
        finally:
            set_leds(0, 0, 0)


if __name__ == "__main__":
    run()
