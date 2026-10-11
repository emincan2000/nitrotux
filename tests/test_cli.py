"""CLI end to end in a subprocess, against a fake sysfs and a fake helper path."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.fakesys import FakeSys

ROOT = Path(__file__).resolve().parent.parent


class CliTest(unittest.TestCase):
    def setUp(self):
        self.fs = FakeSys({"firmware/acpi/platform_profile": "quiet"})
        self.addCleanup(self.fs.cleanup)

    def cli(self, *args, helper="/nonexistent/nitrotux-helper", lang="en"):
        env = {**os.environ, "NITROTUX_SYSFS": str(self.fs.root), "NITROTUX_HELPER": helper,
               "NITROTUX_LANG": lang, "PYTHONPATH": str(ROOT)}
        return subprocess.run([sys.executable, "-m", "nitrotux", *args],
                              capture_output=True, text=True, env=env, cwd=ROOT)

    def test_status_json(self):
        res = self.cli("status", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["profile"], "quiet")
        self.assertEqual(data["cpu_fan_rpm"], 2752)
        self.assertIsNone(data["ec_gpu_temp_c"])

    def test_status_text_both_languages(self):
        self.assertIn("Quiet", self.cli("status").stdout)
        self.assertIn("Sessiz", self.cli("status", lang="tr").stdout)

    def test_not_a_tty_prints_status_instead_of_tui(self):
        res = self.cli()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Quiet", res.stdout)

    def test_set_without_helper_fails_cleanly(self):
        res = self.cli("set", "performance")
        self.assertEqual(res.returncode, 1)
        self.assertIn("install.sh", res.stderr)
        self.assertNotIn("Traceback", res.stderr)

    def test_set_rejects_unknown_mode(self):
        res = self.cli("set", "low-power")
        self.assertEqual(res.returncode, 2)

    def test_version(self):
        self.assertIn("Nitrotux 0.1.0", self.cli("--version").stdout)


if __name__ == "__main__":
    unittest.main()
