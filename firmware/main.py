import time
import motor
import led_button
import my_timer

def update():
    """Handle one pass through the existing button/timer/LED state machine."""

    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------
    if my_timer.state == my_timer.STATE_IDLE:

        led_button.show_selected_preset(my_timer.selected_minutes)

        # Button 1 changes preset
        if led_button.button_pressed(led_button.button1):
            time.sleep_ms(led_button.DEBOUNCE_MS)
            if led_button.button_pressed(led_button.button1):
                my_timer.change_preset()
                led_button.wait_for_release(led_button.button1)

        # Button 2 starts timer
        if led_button.button_pressed(led_button.button2):
            time.sleep_ms(led_button.DEBOUNCE_MS)
            if led_button.button_pressed(led_button.button2):
                led_button.wait_for_release(led_button.button2)
                my_timer.start_timer()

    # --------------------------------------------------------
    # RUNNING
    # --------------------------------------------------------
    elif my_timer.state == my_timer.STATE_RUNNING:

        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, my_timer.last_update)

        my_timer.remaining_ms -= elapsed
        my_timer.last_update = now

        if my_timer.remaining_ms <= 0:
            my_timer.remaining_ms = 0
            motor.move_hand_to(0)
            my_timer.state = my_timer.STATE_FINISHED
            print("TIME'S UP!")
            return

        # Update clock hand position
        fraction_remaining = my_timer.remaining_ms / my_timer.timer_duration_ms
        target_position = int(motor.HAND_RANGE_STEPS * fraction_remaining)

        if target_position != motor.hand_position:
            motor.move_hand_to(target_position)

        # LED behavior
        brightness = led_button.pulse_value()

        # Final minute = red pulse
        if my_timer.remaining_ms <= 60_000:
            led_button.set_leds(brightness, 0, 0)
        # Otherwise = blue pulse
        else:
            led_button.set_leds(0, brightness, 0)

    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------
    elif my_timer.state == my_timer.STATE_FINISHED:

        # Solid red
        led_button.set_leds(1, 0, 0)

        # Button 2 resets
        if led_button.button_pressed(led_button.button2):
            time.sleep_ms(led_button.DEBOUNCE_MS)
            if led_button.button_pressed(led_button.button2):
                led_button.wait_for_release(led_button.button2)
                my_timer.reset_timer()


def run():
    try:
        motor.initialize()
        my_timer.reset_timer()
        print("Meeting timer ready")
        print("Set the pointer's zero reference before pressing Start.")
        print("Hand travel:", motor.HAND_RANGE_STEPS, "steps (check calibration)")
        print("Selected:", my_timer.selected_minutes, "minutes")

        while True:
            update()
            time.sleep_ms(10)
    finally:
        # Cleanup also runs when Thonny sends KeyboardInterrupt.
        try:
            motor.motor_off()
        finally:
            led_button.set_leds(0, 0, 0)


if __name__ == "__main__":
    run()
