"""Open-loop, active-low control for the XIAO / L293D / 28BYJ-48.

The red common motor wire is connected to +5 V. GPIO HIGH is the
inactive command; GPIO LOW energizes the corresponding winding.
Positions count commanded wave-drive steps, not measured shaft angles.
"""

from machine import Pin
import time

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
HAND_RANGE_STEPS = 512

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
        raise RuntimeError("Call motor.initialize() and establish zero first")

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
