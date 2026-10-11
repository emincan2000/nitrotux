import subprocess
import tempfile
import unittest
from unittest import mock

from nitrotux import profiles


class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.helper = tempfile.NamedTemporaryFile(prefix="nitrotux-helper-")
        self.addCleanup(self.helper.close)

    def test_cycle(self):
        self.assertEqual(profiles.next_profile("quiet"), "balanced")
        self.assertEqual(profiles.next_profile("balanced"), "performance")
        self.assertEqual(profiles.next_profile("performance"), "quiet")
        for other in (None, "", "low-power", "balanced-performance"):
            self.assertEqual(profiles.next_profile(other), "quiet")

    def run_apply(self, name, rc=0, stderr=""):
        done = subprocess.CompletedProcess([], rc, "", stderr)
        with mock.patch("subprocess.run", return_value=done) as run:
            profiles.apply(name, helper=self.helper.name)
        return run

    def test_apply_uses_sudo_non_interactive(self):
        run = self.run_apply("performance")
        self.assertEqual(run.call_args.args[0], ["sudo", "-n", self.helper.name, "performance"])

    def test_unknown_mode_never_runs_anything(self):
        with mock.patch("subprocess.run") as run, self.assertRaises(profiles.ApplyError):
            profiles.apply("low-power", helper=self.helper.name)
        run.assert_not_called()

    def test_missing_helper(self):
        with self.assertRaises(profiles.NotInstalled):
            profiles.apply("quiet", helper="/nonexistent/nitrotux-helper")

    def test_sudo_password_required_means_not_installed(self):
        with self.assertRaises(profiles.NotInstalled):
            self.run_apply("quiet", 1, "sudo: a password is required")

    def test_other_failure(self):
        with self.assertRaises(profiles.ApplyError) as cm:
            self.run_apply("quiet", 1, "write error")
        self.assertNotIsInstance(cm.exception, profiles.NotInstalled)
        self.assertIn("write error", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
