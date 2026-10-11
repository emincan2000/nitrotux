"""NVIDIA GPU power readings over NVML, without keeping the GPU awake.

Measured on the AN515-58 (RTX 4060, driver 615, runtime D3 enabled): a single
NVML query wakes a suspended GPU and keeps it awake for ~15 s, and the first
power sample after a wake-up can be garbage (590 W). So the monitor:

* never touches NVML while the GPU is runtime-suspended (sysfs only),
* backs off for a while once the GPU looks idle, so it can suspend again,
* drops power samples above the board's max limit.
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class GpuSample:
    power_w: Optional[float] = None
    limit_w: Optional[float] = None
    max_limit_w: Optional[float] = None
    util_pct: Optional[int] = None


class _NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


def nvml_sample() -> Optional[GpuSample]:
    """One NVML snapshot of GPU 0 (init + shutdown). None if NVML is unusable."""
    try:
        nvml = ctypes.CDLL("libnvidia-ml.so.1")
    except OSError:
        return None
    if nvml.nvmlInit_v2() != 0:
        return None
    try:
        dev = ctypes.c_void_p()
        if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) != 0:
            return None

        def u32(fn: str) -> Optional[int]:
            v = ctypes.c_uint()
            return v.value if getattr(nvml, fn)(dev, ctypes.byref(v)) == 0 else None

        s = GpuSample()
        p, lim = u32("nvmlDeviceGetPowerUsage"), u32("nvmlDeviceGetEnforcedPowerLimit")
        s.power_w = p / 1000 if p is not None else None
        s.limit_w = lim / 1000 if lim is not None else None
        lo, hi = ctypes.c_uint(), ctypes.c_uint()
        if nvml.nvmlDeviceGetPowerManagementLimitConstraints(dev, ctypes.byref(lo), ctypes.byref(hi)) == 0:
            s.max_limit_w = hi.value / 1000
        util = _NvmlUtilization()
        if nvml.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util)) == 0:
            s.util_pct = util.gpu
        return s
    finally:
        nvml.nvmlShutdown()


class GpuMonitor:
    """Rate-limited, wake-aware wrapper around an NVML sampler."""

    def __init__(
        self,
        sampler: Callable[[], Optional[GpuSample]] = nvml_sample,
        clock: Callable[[], float] = time.monotonic,
        interval: float = 3.0,
        idle_samples: int = 2,
        idle_backoff: float = 30.0,
    ):
        self.sampler = sampler
        self.clock = clock
        self.interval = interval
        self.idle_samples = idle_samples
        self.idle_backoff = idle_backoff
        self._next_at = 0.0
        self._idle = 0
        self._last: Optional[GpuSample] = None

    def backing_off(self) -> bool:
        """True while readings are paused so an idle GPU can suspend."""
        return self._next_at - self.clock() > self.interval

    def poll(self, runtime_status: Optional[str]) -> Optional[GpuSample]:
        """Return the latest sample, or None when the GPU is asleep/unknown."""
        if runtime_status != "active":
            self._last, self._idle = None, 0
            return None
        now = self.clock()
        if now < self._next_at:
            return self._last
        sample = self.sampler()
        if sample is None:
            self._next_at = now + self.idle_backoff
            return self._last
        cap = (sample.max_limit_w or 0) * 1.5
        if cap and sample.power_w is not None and sample.power_w > cap:
            sample.power_w = None  # first sample after a wake-up is often bogus
        if sample.util_pct == 0:
            self._idle += 1
        else:
            self._idle = 0
        if self._idle >= self.idle_samples:
            self._idle = 0
            self._next_at = now + self.idle_backoff  # let the GPU runtime-suspend
        else:
            self._next_at = now + self.interval
        self._last = sample
        return sample
