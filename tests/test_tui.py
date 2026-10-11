import unittest

from nitrotux import profiles
from nitrotux.gpu import GpuSample
from nitrotux.hw import Status
from nitrotux.i18n import STRINGS, T, detect_lang
from nitrotux.tui import bar, build_screen


def text(lines):
    return ["".join(s for s, _ in line) for line in lines]


def full_status(**kw):
    st = Status(model="Nitro AN515-58", profile="balanced", pl1_w=115, pl2_w=115,
                cpu_temp_c=52.0, ec_gpu_temp_c=None, ec_sys_temp_c=47.0,
                cpu_fan_rpm=2752, gpu_fan_rpm=3157, cpu_fan_mode="auto",
                gpu_fan_mode="auto", on_ac=True, battery_pct=100, gpu_runtime="suspended")
    st.__dict__.update(kw)
    return st


class TuiTest(unittest.TestCase):
    def test_active_marker_on_current_profile_only(self):
        for name in profiles.ORDER:
            lines = text(build_screen(full_status(profile=name), None, False, 0, None, T("en")))
            marked = [l for l in lines if "● active" in l]
            self.assertEqual(len(marked), 1)
            self.assertIn(T("en")(name), marked[0])

    def test_selection_arrow(self):
        lines = text(build_screen(full_status(), None, False, 2, None, T("en")))
        self.assertTrue(any(l.startswith("  ▶ 3") for l in lines))

    def test_everything_unknown_does_not_crash(self):
        for lang in STRINGS:
            lines = text(build_screen(Status(), None, False, 0, None, T(lang)))
            self.assertTrue(lines)

    def test_gpu_states(self):
        t = T("en")
        asleep = "\n".join(text(build_screen(full_status(), None, False, 0, None, t)))
        self.assertIn(t("gpu_asleep"), asleep)
        busy = "\n".join(text(build_screen(full_status(gpu_runtime="active"),
                                           GpuSample(87.4, 105, 140, 98), False, 0, None, t)))
        self.assertIn("87.4 W / 105 W", busy)
        paused = "\n".join(text(build_screen(full_status(gpu_runtime="active"),
                                             GpuSample(5, 105, 140, 0), True, 0, None, t)))
        self.assertIn(t("gpu_idle_paused"), paused)

    def test_unknown_firmware_profile_shown(self):
        lines = text(build_screen(full_status(profile="low-power"), None, False, 0, None, T("en")))
        self.assertIn("    (low-power)", lines)
        self.assertFalse(any("● active" in l for l in lines))

    def test_message_line(self):
        lines = text(build_screen(full_status(), None, False, 0, ("Mode: Quiet", "ok"), T("en")))
        self.assertIn(" Mode: Quiet", lines)

    def test_bar(self):
        self.assertEqual(bar(None, 100, 4), "····")
        self.assertEqual(bar(0, 100, 4), "░░░░")
        self.assertEqual(bar(50, 100, 4), "██░░")
        self.assertEqual(bar(250, 100, 4), "████")
        self.assertEqual(bar(-5, 100, 4), "░░░░")


class I18nTest(unittest.TestCase):
    def test_same_keys_in_every_language(self):
        keys = {lang: set(s) for lang, s in STRINGS.items()}
        self.assertEqual(keys["en"], keys["tr"])

    def test_detect(self):
        self.assertEqual(detect_lang({"LANG": "tr_TR.UTF-8"}), "tr")
        self.assertEqual(detect_lang({"LANG": "en_US.UTF-8"}), "en")
        self.assertEqual(detect_lang({"LANG": "en_US.UTF-8", "NITROTUX_LANG": "tr"}), "tr")
        self.assertEqual(detect_lang({"LC_ALL": "tr_TR.UTF-8", "LANG": "en_US"}), "tr")
        self.assertEqual(detect_lang({"NITROTUX_LANG": "xx"}), "en")
        self.assertEqual(detect_lang({}), "en")

    def test_placeholders_format_in_every_language(self):
        for lang in STRINGS:
            t = T(lang)
            for name in profiles.ORDER:
                t(f"desc_{name}", pl1=1, pl2=2)
            t("applied", mode="x"), t("applying", mode="x"), t("failed", err="x")


if __name__ == "__main__":
    unittest.main()
