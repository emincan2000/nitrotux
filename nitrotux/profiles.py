"""Mode definitions and switching via the root helper.

The values here are for display. The root helper (helper/nitrotux-helper) holds
its own copy on purpose, so root never reads anything the user can edit;
tests/test_consistency.py keeps both in sync.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

HELPER = os.environ.get("NITROTUX_HELPER", "/usr/local/sbin/nitrotux-helper")


@dataclass(frozen=True)
class Profile:
    name: str
    pl1_w: int
    pl2_w: int
    fans: str  # auto | max


PROFILES = {
    "quiet": Profile("quiet", 45, 65, "auto"),
    "balanced": Profile("balanced", 115, 115, "auto"),
    "performance": Profile("performance", 115, 115, "max"),
}
ORDER = ("quiet", "balanced", "performance")


def next_profile(current: str | None) -> str:
    """quiet -> balanced -> performance -> quiet; anything else -> quiet."""
    if current in ORDER:
        return ORDER[(ORDER.index(current) + 1) % len(ORDER)]
    return ORDER[0]


class ApplyError(RuntimeError):
    pass


class NotInstalled(ApplyError):
    """Helper missing, or no sudoers rule letting us run it without a password."""


def apply(name: str, helper: str = HELPER) -> None:
    """Switch mode through `sudo -n <helper> <name>` (never prompts)."""
    if name not in PROFILES:
        raise ApplyError(f"unknown mode: {name}")
    if not os.path.isfile(helper):
        raise NotInstalled(f"{helper} not found")
    try:
        res = subprocess.run(
            ["sudo", "-n", helper, name],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ApplyError(str(exc)) from exc
    if res.returncode != 0:
        msg = (res.stderr or res.stdout).strip() or f"exit {res.returncode}"
        if "password is required" in msg or "not allowed" in msg:
            raise NotInstalled(msg)
        raise ApplyError(msg)
