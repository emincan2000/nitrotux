"""Read-only access to the sysfs files nitrotux uses.

Nothing in this module writes to the system. All paths are resolved against a
configurable root so the test suite can point it at a fake sysfs tree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_ROOT = Path(os.environ.get("NITROTUX_SYSFS", "/sys"))


def _read(path: Path) -> Optional[str]:
    try:
        return path.read_text().strip()
    except (OSError, ValueError):
        return None


def _read_int(path: Path) -> Optional[int]:
    raw = _read(path)
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


@dataclass
class Status:
    model: Optional[str] = None
    profile: Optional[str] = None
    profile_choices: list[str] = field(default_factory=list)
    pl1_w: Optional[int] = None
    pl2_w: Optional[int] = None
    cpu_temp_c: Optional[float] = None       # coretemp package (silicon)
    ec_cpu_temp_c: Optional[float] = None    # acer_wmi temp1
    ec_gpu_temp_c: Optional[float] = None    # acer_wmi temp2 (does not wake the GPU)
    ec_sys_temp_c: Optional[float] = None    # acer_wmi temp3
    cpu_fan_rpm: Optional[int] = None
    gpu_fan_rpm: Optional[int] = None
    cpu_fan_mode: Optional[str] = None       # auto | max | custom
    gpu_fan_mode: Optional[str] = None
    on_ac: Optional[bool] = None
    battery_pct: Optional[int] = None
    battery_status: Optional[str] = None
    gpu_runtime: Optional[str] = None        # active | suspended | ... (no wake-up)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


# acer_wmi hwmon pwmN_enable: 0 = firmware turbo, 1 = custom, 2 = firmware auto
FAN_MODES = {0: "max", 1: "custom", 2: "auto"}


class Sysfs:
    def __init__(self, root: Path = DEFAULT_ROOT):
        self.root = Path(root)

    def _hwmon(self, name: str) -> Optional[Path]:
        base = self.root / "class/hwmon"
        try:
            entries = sorted(base.iterdir())
        except OSError:
            return None
        for h in entries:
            if _read(h / "name") == name:
                return h
        return None

    def _temp(self, hwmon: Optional[Path], n: int) -> Optional[float]:
        if hwmon is None:
            return None
        v = _read_int(hwmon / f"temp{n}_input")
        return v / 1000 if v is not None else None

    def _nvidia_gpu(self) -> Optional[Path]:
        base = self.root / "bus/pci/devices"
        try:
            entries = sorted(base.iterdir())
        except OSError:
            return None
        for d in entries:
            cls = _read(d / "class") or ""
            if _read(d / "vendor") == "0x10de" and cls.startswith(("0x0300", "0x0302")):
                return d
        return None

    def _power_supply(self, st: Status) -> None:
        base = self.root / "class/power_supply"
        try:
            entries = sorted(base.iterdir())
        except OSError:
            return
        for p in entries:
            kind = _read(p / "type")
            if kind == "Mains":
                online = _read_int(p / "online")
                if online is not None:
                    st.on_ac = bool(online) or bool(st.on_ac)
            elif kind == "Battery" and st.battery_pct is None:
                st.battery_pct = _read_int(p / "capacity")
                st.battery_status = _read(p / "status")

    def read(self) -> Status:
        r = self.root
        st = Status()
        st.model = _read(r / "class/dmi/id/product_name")
        st.profile = _read(r / "firmware/acpi/platform_profile")
        st.profile_choices = (_read(r / "firmware/acpi/platform_profile_choices") or "").split()

        rapl = r / "class/powercap/intel-rapl:0"
        pl1 = _read_int(rapl / "constraint_0_power_limit_uw")
        pl2 = _read_int(rapl / "constraint_1_power_limit_uw")
        st.pl1_w = round(pl1 / 1_000_000) if pl1 is not None else None
        st.pl2_w = round(pl2 / 1_000_000) if pl2 is not None else None

        st.cpu_temp_c = self._temp(self._hwmon("coretemp"), 1)

        acer = self._hwmon("acer")
        st.ec_cpu_temp_c = self._temp(acer, 1)
        # The EC reports 0 while the dGPU is powered down; that is "no reading", not 0 °C.
        st.ec_gpu_temp_c = self._temp(acer, 2) or None
        st.ec_sys_temp_c = self._temp(acer, 3)
        if acer is not None:
            st.cpu_fan_rpm = _read_int(acer / "fan1_input")
            st.gpu_fan_rpm = _read_int(acer / "fan2_input")
            st.cpu_fan_mode = FAN_MODES.get(_read_int(acer / "pwm1_enable"))
            st.gpu_fan_mode = FAN_MODES.get(_read_int(acer / "pwm2_enable"))

        self._power_supply(st)

        gpu = self._nvidia_gpu()
        if gpu is not None:
            st.gpu_runtime = _read(gpu / "power/runtime_status")
        return st
