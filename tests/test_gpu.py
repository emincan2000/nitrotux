import unittest

from nitrotux.gpu import GpuMonitor, GpuSample


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class GpuMonitorTest(unittest.TestCase):
    def make(self, samples):
        self.calls = 0
        it = iter(samples)

        def sampler():
            self.calls += 1
            return next(it)

        self.clock = Clock()
        return GpuMonitor(sampler, self.clock, interval=3, idle_samples=2, idle_backoff=30)

    def test_never_queries_a_sleeping_gpu(self):
        m = self.make([])
        for status in ("suspended", "suspending", None, "error"):
            self.assertIsNone(m.poll(status))
        self.assertEqual(self.calls, 0)

    def test_rate_limited(self):
        m = self.make([GpuSample(50, 105, 140, 80), GpuSample(60, 105, 140, 80)])
        self.assertEqual(m.poll("active").power_w, 50)
        self.clock.t += 1
        self.assertEqual(m.poll("active").power_w, 50)  # cached
        self.assertEqual(self.calls, 1)
        self.clock.t += 3
        self.assertEqual(m.poll("active").power_w, 60)
        self.assertEqual(self.calls, 2)

    def test_backs_off_when_idle_so_gpu_can_suspend(self):
        m = self.make([GpuSample(8, 105, 140, 0), GpuSample(7, 105, 140, 0), GpuSample(9, 105, 140, 50)])
        m.poll("active")
        self.clock.t += 3
        m.poll("active")
        self.assertTrue(m.backing_off())
        for _ in range(9):           # 27 s of polling: no NVML calls
            self.clock.t += 3
            m.poll("active")
        self.assertEqual(self.calls, 2)
        self.clock.t += 4
        self.assertEqual(m.poll("active").power_w, 9)
        self.assertFalse(m.backing_off())

    def test_bogus_wakeup_sample_dropped(self):
        m = self.make([GpuSample(590.0, 105, 140, 10)])
        s = m.poll("active")
        self.assertIsNone(s.power_w)
        self.assertEqual(s.limit_w, 105)

    def test_unusable_nvml_backs_off(self):
        m = self.make([None])
        self.assertIsNone(m.poll("active"))
        self.clock.t += 10
        m.poll("active")
        self.assertEqual(self.calls, 1)

    def test_sleep_clears_cache(self):
        m = self.make([GpuSample(50, 105, 140, 80)])
        m.poll("active")
        self.assertIsNone(m.poll("suspended"))


if __name__ == "__main__":
    unittest.main()
