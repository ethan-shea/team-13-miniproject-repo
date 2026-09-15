"""Host-side integration checks; simulated GPIO cannot validate real motion.

Run from the repository root: python -B -m unittest discover -s tests -v
"""

import contextlib
import importlib
import io
from pathlib import Path
import sys
import types
import unittest


FIRMWARE = Path(__file__).resolve().parents[1] / "firmware"
MODULE_NAMES = ("machine", "time", "motor", "led_button", "my_timer", "main")


class FirmwareIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.saved_modules = {name: sys.modules.get(name) for name in MODULE_NAMES}
        self.saved_path = sys.path[:]
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        for name in MODULE_NAMES:
            sys.modules.pop(name, None)

        self.levels = {}
        self.pwm = {}
        self.coil_trace = []
        self.now = 0
        self.period = 1 << 30
        self.fail_next_motor_sleep = False
        self.sleep_hook = None
        harness = self

        class Pin:
            IN, OUT, PULL_UP = 0, 1, 2

            def __init__(self, number, mode=None, pull=None, *, value=None):
                self.number = number
                if value is not None:
                    harness.levels[number] = value
                elif number not in harness.levels:
                    harness.levels[number] = 1 if pull == self.PULL_UP else 0

            def value(self, new_value=None):
                if new_value is not None:
                    harness.levels[self.number] = new_value
                return harness.levels[self.number]

        class PWM:
            def __init__(self, pin):
                self.pin = pin
                self.frequency = None
                self.duty = None
                harness.pwm[pin.number] = self

            def freq(self, frequency):
                self.frequency = frequency

            def duty_u16(self, duty):
                if not 0 <= duty <= 65535:
                    raise ValueError("PWM duty out of range")
                self.duty = duty

        machine = types.ModuleType("machine")
        machine.Pin, machine.PWM = Pin, PWM
        fake_time = types.ModuleType("time")
        fake_time.ticks_ms = lambda: self.now % self.period
        fake_time.ticks_diff = lambda a, b: (
            (a - b + self.period // 2) % self.period - self.period // 2
        )
        fake_time.sleep_ms = self.sleep_ms
        sys.modules["machine"] = machine
        sys.modules["time"] = fake_time
        sys.path.insert(0, str(FIRMWARE))
        self.main = importlib.import_module("main")
        self.motor = sys.modules["motor"]
        self.timer = sys.modules["my_timer"]
        self.leds = sys.modules["led_button"]

    def tearDown(self):
        sys.path[:] = self.saved_path
        for name, module in self.saved_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        self.output.__exit__(None, None, None)

    def sleep_ms(self, duration):
        active = [number for number in (1, 2, 3, 4) if self.levels[number] == 0]
        if active:
            self.assertEqual(len(active), 1, "Only one winding may be active")
            self.coil_trace.append(active[0])
            if self.fail_next_motor_sleep:
                self.fail_next_motor_sleep = False
                raise KeyboardInterrupt
        self.now += duration
        if self.sleep_hook:
            self.sleep_hook()

    def assert_outputs_off(self):
        self.assertEqual([self.levels[i] for i in (1, 2, 3, 4)], [1, 1, 1, 1])

    def press_button(self, number, duration=100):
        self.levels[number] = 0
        release_at = self.now + duration

        def release():
            if self.now >= release_at:
                self.levels[number] = 1

        self.sleep_hook = release
        try:
            self.main.update()
        finally:
            self.sleep_hook = None
            self.levels[number] = 1

    def test_import_initializes_inactive_outputs_without_running_motor(self):
        self.assert_outputs_off()
        self.assertEqual(self.coil_trace, [])
        self.assertEqual(self.motor.hand_position, 0)
        self.assertEqual([self.pwm[i].duty for i in (7, 8, 9)], [0, 0, 0])

    def test_incremental_moves_and_reversal_preserve_phase_and_position(self):
        self.motor.initialize()
        self.motor.move_hand_to(1)
        self.motor.move_hand_to(3)
        self.motor.move_hand_to(2)
        self.motor.move_hand_to(0)
        # GPIO4=Blue, GPIO2=Pink, GPIO3=Yellow, GPIO1=Orange.
        self.assertEqual(self.coil_trace, [4, 2, 3, 1, 3, 2, 4])
        self.assertEqual(self.motor.hand_position, 0)
        self.assert_outputs_off()

    def test_forward_direction_setting_reverses_physical_sequence(self):
        self.motor.FORWARD_DIRECTION = -1
        self.motor.initialize()
        self.motor.move_hand_to(2)
        self.motor.move_hand_to(0)
        self.assertEqual(self.coil_trace, [4, 1, 3, 1, 4])
        self.assertEqual(self.motor.hand_position, 0)

    def test_noop_and_invalid_targets_do_not_move(self):
        self.motor.initialize()
        baseline_trace = self.coil_trace[:]
        self.motor.move_hand_to(0)
        for target in (-1, self.motor.HAND_RANGE_STEPS + 1):
            with self.assertRaises(ValueError):
                self.motor.move_hand_to(target)
        with self.assertRaises(TypeError):
            self.motor.move_hand_to(0.5)
        self.assertEqual(self.coil_trace, baseline_trace)
        self.assert_outputs_off()

    def test_interrupted_move_releases_motor_and_requires_new_reference(self):
        self.motor.initialize()
        self.fail_next_motor_sleep = True
        with self.assertRaises(KeyboardInterrupt):
            self.motor.move_hand_to(10)
        self.assert_outputs_off()
        with self.assertRaises(RuntimeError):
            self.motor.move_hand_to(0)
        self.motor.initialize()
        self.motor.move_hand_to(1)
        self.assertEqual(self.motor.hand_position, 1)

    def test_countdown_begins_after_initial_hand_movement(self):
        self.motor.initialize()
        before = self.now
        self.timer.start_timer()
        self.assertEqual(self.now - before, 512 * 5)
        self.assertEqual(self.timer.last_update, self.now)
        self.assertEqual(self.timer.remaining_ms, 15 * 60 * 1000)
        self.main.update()
        self.assertEqual(self.timer.remaining_ms, 15 * 60 * 1000)

    def test_timer_and_main_share_the_motor_range_configuration(self):
        self.motor.HAND_RANGE_STEPS = 12
        self.motor.initialize()
        self.timer.start_timer()
        self.assertEqual(self.motor.hand_position, 12)
        self.now += self.timer.timer_duration_ms // 2
        self.main.update()
        self.assertEqual(self.motor.hand_position, 6)

    def test_all_presets_complete_and_reset_using_actual_modules(self):
        self.motor.initialize()
        for minutes in (15, 20, 25, 30):
            with self.subTest(minutes=minutes):
                self.timer.selected_minutes = minutes
                self.timer.start_timer()
                start = self.now
                self.assertEqual(self.motor.hand_position, 512)
                while self.timer.state == self.timer.STATE_RUNNING:
                    self.now += 1000
                    self.main.update()
                self.main.update()
                self.assertEqual(self.timer.state, self.timer.STATE_FINISHED)
                self.assertEqual(self.timer.remaining_ms, 0)
                self.assertEqual(self.motor.hand_position, 0)
                self.assertGreaterEqual(self.now - start, minutes * 60000)
                self.assertLessEqual(self.now - start, minutes * 60000 + 1005)
                self.assertEqual([self.pwm[i].duty for i in (7, 8, 9)], [65535, 0, 0])
                self.press_button(6)
                self.assertEqual(self.timer.state, self.timer.STATE_IDLE)
                self.assertEqual(self.timer.remaining_ms, minutes * 60000)
                self.assert_outputs_off()

    def test_button_selection_start_and_debounce(self):
        self.motor.initialize()
        self.press_button(5, duration=20)
        self.assertEqual(self.timer.selected_minutes, 15)
        for minutes in (20, 25, 30, 15):
            self.press_button(5)
            self.assertEqual(self.timer.selected_minutes, minutes)
        self.press_button(6)
        self.assertEqual(self.timer.state, self.timer.STATE_RUNNING)
        self.assertEqual(self.motor.hand_position, 512)

    def test_led_channels_and_one_second_pulse(self):
        for milliseconds, expected in ((0, 0), (250, 0.5), (500, 1), (750, 0.5), (1000, 0)):
            self.now = milliseconds
            self.assertEqual(self.leds.pulse_value(), expected)
        self.now = 250
        for minutes, expected in (
            (15, (0, 0, 32767)),
            (20, (0, 32767, 0)),
            (25, (32767, 0, 0)),
            (30, (32767, 32767, 32767)),
        ):
            self.leds.show_selected_preset(minutes)
            self.assertEqual(tuple(self.pwm[i].duty for i in (7, 8, 9)), expected)
        self.motor.initialize()
        self.timer.start_timer()
        self.now += 100
        self.main.update()
        self.assertEqual(self.pwm[7].duty, 0)
        self.assertGreater(self.pwm[8].duty, 0)
        self.now += self.timer.remaining_ms - 59000
        self.main.update()
        self.assertGreater(self.pwm[7].duty, 0)
        self.assertEqual(self.pwm[8].duty, 0)

    def test_countdown_handles_tick_wraparound(self):
        self.motor.initialize()
        self.now = self.period - 100 - 512 * 5
        self.timer.start_timer()
        self.now += 250
        self.main.update()
        self.assertEqual(self.timer.remaining_ms, 900000 - 250)

    def test_main_cleans_up_after_loop_or_initialization_interrupt(self):
        def interrupted_update():
            self.levels[1] = 0
            self.leds.set_leds(1, 1, 1)
            raise KeyboardInterrupt

        self.main.update = interrupted_update
        self.timer.state = self.timer.STATE_RUNNING
        self.timer.remaining_ms = 1
        with self.assertRaises(KeyboardInterrupt):
            self.main.run()
        self.assertEqual(self.timer.state, self.timer.STATE_IDLE)
        self.assertEqual(self.timer.remaining_ms, 900000)
        self.assert_outputs_off()
        self.assertEqual([self.pwm[i].duty for i in (7, 8, 9)], [0, 0, 0])

        self.fail_next_motor_sleep = True
        with self.assertRaises(KeyboardInterrupt):
            self.main.run()
        self.assert_outputs_off()
        self.assertEqual([self.pwm[i].duty for i in (7, 8, 9)], [0, 0, 0])


if __name__ == "__main__":
    unittest.main()
