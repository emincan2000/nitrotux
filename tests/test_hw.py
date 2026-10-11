import unittest

from nitrotux.hw import Sysfs
from tests.fakesys import FakeSys


class HwTest(unittest.TestCase):
    def read(self, **overrides):
        fs = FakeSys(overrides)
        self.addCleanup(fs.cleanup)
        return Sysfs(fs.root).read()

    def test_full_tree(self):
        st = self.read()
        self.assertEqual(st.model, "Nitro AN515-58")
        self.assertEqual(st.profile, "balanced")
        self.assertIn("performance", st.profile_choices)
        self.assertEqual((st.pl1_w, st.pl2_w), (115, 115))
        self.assertEqual(st.cpu_temp_c, 52.0)
        self.assertEqual(st.ec_cpu_temp_c, 53.0)
        self.assertEqual(st.ec_sys_temp_c, 47.0)
        self.assertEqual((st.cpu_fan_rpm, st.gpu_fan_rpm), (2752, 3157))
        self.assertEqual((st.cpu_fan_mode, st.gpu_fan_mode), ("auto", "auto"))
        self.assertTrue(st.on_ac)
        self.assertEqual((st.battery_pct, st.battery_status), (100, "Full"))

    def test_gpu_temp_zero_means_no_reading(self):
        self.assertIsNone(self.read().ec_gpu_temp_c)
        self.assertEqual(self.read(**{"class/hwmon/hwmon8/temp2_input": "61000"}).ec_gpu_temp_c, 61.0)

    def test_gpu_runtime_from_nvidia_vga_only(self):
        self.assertEqual(self.read().gpu_runtime, "suspended")
        st = self.read(**{"bus/pci/devices/0000:01:00.0/vendor": "0x1002"})
        self.assertIsNone(st.gpu_runtime)

    def test_fan_modes(self):
        st = self.read(**{"class/hwmon/hwmon8/pwm1_enable": "0",
                          "class/hwmon/hwmon8/pwm2_enable": "1"})
        self.assertEqual((st.cpu_fan_mode, st.gpu_fan_mode), ("max", "custom"))

    def test_missing_acer_hwmon(self):
        st = self.read(**{"class/hwmon/hwmon8/name": "something-else"})
        self.assertIsNone(st.cpu_fan_rpm)
        self.assertIsNone(st.cpu_fan_mode)
        self.assertIsNone(st.ec_cpu_temp_c)
        self.assertEqual(st.cpu_temp_c, 52.0)  # coretemp still there

    def test_garbage_and_missing_values(self):
        st = self.read(**{"class/hwmon/hwmon8/fan1_input": "abc",
                          "class/powercap/intel-rapl:0/constraint_0_power_limit_uw": None,
                          "firmware/acpi/platform_profile": None})
        self.assertIsNone(st.cpu_fan_rpm)
        self.assertIsNone(st.pl1_w)
        self.assertIsNone(st.profile)

    def test_on_battery(self):
        st = self.read(**{"class/power_supply/ACAD/online": "0",
                          "class/power_supply/BAT1/status": "Discharging"})
        self.assertFalse(st.on_ac)
        self.assertEqual(st.battery_status, "Discharging")

    def test_empty_root(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            st = Sysfs(d).read()
        self.assertIsNone(st.profile)
        self.assertEqual(st.profile_choices, [])


if __name__ == "__main__":
    unittest.main()
