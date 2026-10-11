"""Tiny English/Turkish string table. NITROTUX_LANG wins over LANG."""

from __future__ import annotations

import os

STRINGS = {
    "en": {
        "title": "Nitrotux",
        "modes": "Mode",
        "sensors": "Sensors",
        "quiet": "Quiet",
        "balanced": "Balanced",
        "performance": "Performance",
        "desc_quiet": "CPU {pl1}/{pl2} W, fans auto",
        "desc_balanced": "CPU {pl1}/{pl2} W, fans auto (factory)",
        "desc_performance": "CPU {pl1}/{pl2} W, fans full speed",
        "active": "active",
        "cpu": "CPU",
        "gpu": "GPU",
        "system": "System",
        "fan": "fan",
        "limits": "CPU limits",
        "power": "Power",
        "ac": "AC",
        "battery": "battery",
        "gpu_asleep": "asleep (power saving)",
        "gpu_awake": "awake",
        "gpu_idle_paused": "awake, readings paused so it can sleep",
        "fan_auto": "auto",
        "fan_max": "full speed",
        "fan_custom": "custom",
        "keys": "1/2/3 mode   ↑↓ Enter select   c cycle   q quit",
        "applying": "Switching to {mode}…",
        "applied": "Mode: {mode}",
        "failed": "Failed: {err}",
        "too_small": "Terminal too small",
        "unknown": "?",
        "not_installed": "Helper not installed or sudo rule missing — run install.sh",
    },
    "tr": {
        "title": "Nitrotux",
        "modes": "Mod",
        "sensors": "Sensörler",
        "quiet": "Sessiz",
        "balanced": "Dengeli",
        "performance": "Performans",
        "desc_quiet": "CPU {pl1}/{pl2} W, fanlar otomatik",
        "desc_balanced": "CPU {pl1}/{pl2} W, fanlar otomatik (fabrika)",
        "desc_performance": "CPU {pl1}/{pl2} W, fanlar tam hız",
        "active": "aktif",
        "cpu": "CPU",
        "gpu": "GPU",
        "system": "Sistem",
        "fan": "fan",
        "limits": "CPU sınırı",
        "power": "Güç",
        "ac": "Adaptör",
        "battery": "pil",
        "gpu_asleep": "uykuda (güç tasarrufu)",
        "gpu_awake": "uyanık",
        "gpu_idle_paused": "uyanık, uyuyabilmesi için okuma durduruldu",
        "fan_auto": "otomatik",
        "fan_max": "tam hız",
        "fan_custom": "özel",
        "keys": "1/2/3 mod   ↑↓ Enter seç   c sıradaki   q çıkış",
        "applying": "{mode} moduna geçiliyor…",
        "applied": "Mod: {mode}",
        "failed": "Başarısız: {err}",
        "too_small": "Terminal çok küçük",
        "unknown": "?",
        "not_installed": "Yardımcı kurulu değil ya da sudo kuralı yok — install.sh çalıştır",
    },
}


def detect_lang(env: dict | None = None) -> str:
    env = os.environ if env is None else env
    explicit = env.get("NITROTUX_LANG", "")
    if explicit in STRINGS:
        return explicit
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if env.get(var, "").lower().startswith("tr"):
            return "tr"
    return "en"


class T:
    def __init__(self, lang: str | None = None):
        self.lang = lang if lang in STRINGS else detect_lang()
        self._s = STRINGS[self.lang]

    def __call__(self, key: str, **kw) -> str:
        return self._s.get(key, STRINGS["en"].get(key, key)).format(**kw)
