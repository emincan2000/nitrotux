"""The helper's hard-coded values must match profiles.PROFILES."""

import re
import unittest
from pathlib import Path

from nitrotux import profiles

HELPER = Path(__file__).resolve().parent.parent / "helper" / "nitrotux-helper"
FAN = {"2": "auto", "0": "max"}


class ConsistencyTest(unittest.TestCase):
    def test_helper_matches_profiles(self):
        rows = re.findall(r"^\s*(\w+)\)\s+PL1=(\d+);\s+PL2=(\d+);\s+FAN=(\d)\s*;;", HELPER.read_text(), re.M)
        parsed = {n: profiles.Profile(n, int(a), int(b), FAN[f]) for n, a, b, f in rows}
        self.assertEqual(parsed, profiles.PROFILES)
        self.assertEqual(set(profiles.ORDER), set(profiles.PROFILES))


if __name__ == "__main__":
    unittest.main()
