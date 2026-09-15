"""Run the firmware behavior checks against the standalone entry point."""

import ast
import importlib
from pathlib import Path
import sys
import test_firmware_integration as integration


class StandaloneIntegrationTests(integration.FirmwareIntegrationTests):
    def setUp(self):
        self.previous_standalone = sys.modules.get("meeting_timer_standalone")
        super().setUp()
        # Remove the project modules before loading the standalone file.
        # Only the simulated MicroPython machine/time modules remain needed.
        for name in ("motor", "led_button", "my_timer", "main", "meeting_timer_standalone"):
            sys.modules.pop(name, None)
        self.main = importlib.import_module("meeting_timer_standalone")
        self.motor = self.timer = self.leds = self.main

    def tearDown(self):
        if self.previous_standalone is None:
            sys.modules.pop("meeting_timer_standalone", None)
        else:
            sys.modules["meeting_timer_standalone"] = self.previous_standalone
        super().tearDown()

    def test_standalone_has_only_builtin_micropython_imports(self):
        source = Path(self.main.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertEqual(imported, {"machine", "time"})
        for name in ("motor", "led_button", "my_timer", "main"):
            self.assertNotIn(name, sys.modules)

    def test_direct_file_execution_runs_and_cleans_up(self):
        source = Path(self.main.__file__).read_text(encoding="utf-8")
        namespace = {"__name__": "__main__"}

        def interrupt_after_first_loop():
            if self.now >= 15:
                raise KeyboardInterrupt

        self.sleep_hook = interrupt_after_first_loop
        with self.assertRaises(KeyboardInterrupt):
            exec(compile(source, "meeting_timer_standalone.py", "exec"), namespace)
        self.assertEqual(namespace["state"], namespace["STATE_IDLE"])
        self.assertEqual(self.coil_trace, [4])
        self.assert_outputs_off()
        self.assertEqual([self.pwm[i].duty for i in (7, 8, 9)], [0, 0, 0])
