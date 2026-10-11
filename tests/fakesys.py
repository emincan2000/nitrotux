"""Builds a fake sysfs tree shaped like the AN515-58's (values from a real machine)."""

from __future__ import annotations

import tempfile
from pathlib import Path

DEFAULTS = {
    "class/dmi/id/product_name": "Nitro AN515-58",
    "firmware/acpi/platform_profile": "balanced",
    "firmware/acpi/platform_profile_choices": "low-power quiet balanced balanced-performance performance",
    "class/powercap/intel-rapl:0/constraint_0_power_limit_uw": "115000000",
    "class/powercap/intel-rapl:0/constraint_1_power_limit_uw": "115000000",
    "class/powercap/intel-rapl-mmio:0/constraint_0_power_limit_uw": "115000000",
    "class/powercap/intel-rapl-mmio:0/constraint_1_power_limit_uw": "115000000",
    "class/hwmon/hwmon3/name": "coretemp",
    "class/hwmon/hwmon3/temp1_input": "52000",
    "class/hwmon/hwmon8/name": "acer",
    "class/hwmon/hwmon8/temp1_input": "53000",
    "class/hwmon/hwmon8/temp2_input": "0",
    "class/hwmon/hwmon8/temp3_input": "47000",
    "class/hwmon/hwmon8/fan1_input": "2752",
    "class/hwmon/hwmon8/fan2_input": "3157",
    "class/hwmon/hwmon8/pwm1_enable": "2",
    "class/hwmon/hwmon8/pwm2_enable": "2",
    "class/hwmon/hwmon9/name": "nvme",
    "class/power_supply/ACAD/type": "Mains",
    "class/power_supply/ACAD/online": "1",
    "class/power_supply/BAT1/type": "Battery",
    "class/power_supply/BAT1/capacity": "100",
    "class/power_supply/BAT1/status": "Full",
    "class/power_supply/ucsi-source-psy-USBC000:001/type": "USB",
    "class/power_supply/ucsi-source-psy-USBC000:001/online": "0",
    "bus/pci/devices/0000:00:02.0/vendor": "0x8086",
    "bus/pci/devices/0000:00:02.0/class": "0x030000",
    "bus/pci/devices/0000:01:00.0/vendor": "0x10de",
    "bus/pci/devices/0000:01:00.0/class": "0x030000",
    "bus/pci/devices/0000:01:00.0/power/runtime_status": "suspended",
    "bus/pci/devices/0000:01:00.1/vendor": "0x10de",
    "bus/pci/devices/0000:01:00.1/class": "0x040300",
}


class FakeSys:
    def __init__(self, overrides: dict[str, str | None] | None = None):
        self._tmp = tempfile.TemporaryDirectory(prefix="nitrotux-sys-")
        self.root = Path(self._tmp.name)
        files = {**DEFAULTS, **(overrides or {})}
        for rel, value in files.items():
            if value is None:
                continue
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value + "\n")

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text().strip()

    def write(self, rel: str, value: str) -> None:
        (self.root / rel).write_text(value + "\n")

    def cleanup(self) -> None:
        self._tmp.cleanup()
