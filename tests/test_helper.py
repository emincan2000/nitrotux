"""The root helper, run against a fake sysfs (SYS rewritten in a temp copy)."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.fakesys import FakeSys

HELPER = Path(__file__).resolve().parent.parent / "helper" / "nitrotux-helper"
SHELLS = [s for s in ("/bin/sh", "/bin/bash", "/bin/dash") if os.path.exists(s)]

WATCHED = [
    "firmware/acpi/platform_profile",
    "class/powercap/intel-rapl:0/constraint_0_power_limit_uw",
    "class/powercap/intel-rapl:0/constraint_1_power_limit_uw",
    "class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw",
    "class/powercap/intel-rapl-mmio:0/constraint_1_power_limit_uw",
    "class/hwmon/hwmon8/pwm1_enable",
    "class/hwmon/hwmon8/pwm2_enable",
]


class HelperTest(unittest.TestCase):
    def setUp(self):
        self.fs = FakeSys()
        self.addCleanup(self.fs.cleanup)
        self.tmp = tempfile.mkdtemp(prefix="nitrotux-helper-")
        self.addCleanup(shutil.rmtree, self.tmp)
        src = HELPER.read_text()
        self.assertEqual(src.count("\nSYS=/sys\n"), 1, "helper must hard-code SYS=/sys exactly once")
        self.helper = Path(self.tmp) / "nitrotux-helper"
        self.helper.write_text(src.replace("\nSYS=/sys\n", f"\nSYS={self.fs.root}\n"))

    def run_helper(self, *args, shell="/bin/sh", env=None):
        return subprocess.run([shell, str(self.helper), *args], capture_output=True,
                              text=True, env=env or {"PATH": "/usr/bin:/bin"})

    def snapshot(self):
        return {f: self.fs.read(f) for f in WATCHED}

    def test_modes(self):
        expected = {
            "quiet": ("45000000", "65000000", "2"),
            "balanced": ("115000000", "115000000", "2"),
            "performance": ("115000000", "115000000", "0"),
        }
        for shell in SHELLS:
            for mode, (pl1, pl2, fan) in expected.items():
                with self.subTest(shell=shell, mode=mode):
                    res = self.run_helper(mode, shell=shell)
                    self.assertEqual(res.returncode, 0, res.stderr)
                    self.assertEqual(self.fs.read("firmware/acpi/platform_profile"), mode)
                    for rapl in ("intel-rapl:0", "intel-rapl-mmio:0"):
                        self.assertEqual(self.fs.read(f"class/powercap/{rapl}/constraint_0_power_limit_uw"), pl1)
                        self.assertEqual(self.fs.read(f"class/powercap/{rapl}/constraint_1_power_limit_uw"), pl2)
                    self.assertEqual(self.fs.read("class/hwmon/hwmon8/pwm1_enable"), fan)
                    self.assertEqual(self.fs.read("class/hwmon/hwmon8/pwm2_enable"), fan)

    def test_rejects_anything_else_without_writing(self):
        before = self.snapshot()
        bad = [[], [""], ["Quiet"], ["low-power"], ["balanced-performance"],
               ["quiet;id"], ["quiet extra"], ["quiet", "extra"], ["../../etc/passwd"],
               ["performance\n"], ["$(id)"], ["-h"], ["quiet*"]]
        for args in bad:
            with self.subTest(args=args):
                res = self.run_helper(*args)
                self.assertEqual(res.returncode, 2, (args, res.stdout, res.stderr))
                self.assertEqual(self.snapshot(), before, f"wrote something for {args!r}")

    def test_ignores_environment(self):
        evil = FakeSys({"firmware/acpi/platform_profile": "untouched"})
        self.addCleanup(evil.cleanup)
        env = {"PATH": "/usr/bin:/bin", "SYS": str(evil.root), "IFS": "/"}
        res = self.run_helper("quiet", env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.fs.read("firmware/acpi/platform_profile"), "quiet")
        self.assertEqual(evil.read("firmware/acpi/platform_profile"), "untouched")

    def test_only_touches_acer_hwmon(self):
        self.fs.write("class/hwmon/hwmon3/pwm1_enable", "2")  # coretemp: must stay
        self.run_helper("performance")
        self.assertEqual(self.fs.read("class/hwmon/hwmon3/pwm1_enable"), "2")

    def test_missing_rapl_and_fans_still_sets_profile(self):
        shutil.rmtree(self.fs.root / "class/powercap")
        shutil.rmtree(self.fs.root / "class/hwmon/hwmon8")
        res = self.run_helper("performance")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.fs.read("firmware/acpi/platform_profile"), "performance")

    def test_profile_write_failure_is_reported(self):
        (self.fs.root / "firmware/acpi/platform_profile").unlink()
        (self.fs.root / "firmware/acpi/platform_profile").mkdir()
        res = self.run_helper("quiet")
        self.assertEqual(res.returncode, 1)
        # it must stop before touching limits/fans
        self.assertEqual(self.fs.read("class/hwmon/hwmon8/pwm1_enable"), "2")


if __name__ == "__main__":
    unittest.main()
