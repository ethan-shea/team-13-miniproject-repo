from machine import Pin, PWM
import time

button1 = Pin(5, Pin.IN, Pin.PULL_UP)
button2 = Pin(6, Pin.IN, Pin.PULL_UP)

red_led = PWM(Pin(7))
blue_led = PWM(Pin(8))
green_led = PWM(Pin(9))

red_led.freq(1000)
blue_led.freq(1000)
green_led.freq(1000)

DEBOUNCE_MS = 50


def set_leds(red, blue, green):
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
