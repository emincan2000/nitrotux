"""curses dashboard. `build_screen` is pure (testable); `run` does the I/O."""

from __future__ import annotations

import curses
import time
from typing import Optional

from . import profiles
from .gpu import GpuMonitor, GpuSample
from .hw import Status, Sysfs
from .i18n import T

Segment = tuple[str, str]   # (text, style)
Line = list[Segment]

REFRESH_S = 1.0
FAN_SCALE_RPM = 8000   # performance mode measured ~7900/8000 RPM
TEMP_SCALE_C = 100


def bar(value: Optional[float], scale: float, width: int = 12) -> str:
    if value is None:
        return "·" * width
    filled = max(0, min(width, round(value / scale * width)))
    return "█" * filled + "░" * (width - filled)


def temp_style(c: Optional[float]) -> str:
    if c is None:
        return "dim"
    return "hot" if c >= 85 else "warm" if c >= 70 else "ok"


def fmt(v, unit: str = "", digits: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}{unit}" if isinstance(v, float) else f"{v}{unit}"


def build_screen(st: Status, gpu: Optional[GpuSample], gpu_paused: bool,
                 selected: int, message: Optional[Segment], t: T) -> list[Line]:
    lines: list[Line] = []
    power = []
    if st.on_ac is not None:
        power.append(t("ac") if st.on_ac else t("battery"))
    if st.battery_pct is not None:
        power.append(f"{t('battery')} {st.battery_pct}%")
    lines.append([(f" {t('title')}", "title"), (f" · {st.model or '?'}", "dim"),
                  ("   " + " · ".join(power), "dim")])
    lines.append([])

    lines.append([(f" {t('modes')}", "head")])
    for i, name in enumerate(profiles.ORDER):
        p = profiles.PROFILES[name]
        is_sel, is_active = i == selected, st.profile == name
        row: Line = [("  ▶ " if is_sel else "    ", "sel"),
                     (f"{i + 1}  {t(name):<13}", "sel" if is_sel else "normal"),
                     (t(f"desc_{name}", pl1=p.pl1_w, pl2=p.pl2_w), "dim")]
        if is_active:
            row.append((f"   ● {t('active')}", "active"))
        lines.append(row)
    if st.profile and st.profile not in profiles.ORDER:
        lines.append([(f"    ({st.profile})", "dim")])
    lines.append([])

    lines.append([(f" {t('sensors')}", "head")])
    fan_name = {"auto": t("fan_auto"), "max": t("fan_max"), "custom": t("fan_custom")}
    for label, temp, rpm, mode in (
        (t("cpu"), st.cpu_temp_c if st.cpu_temp_c is not None else st.ec_cpu_temp_c,
         st.cpu_fan_rpm, st.cpu_fan_mode),
        (t("gpu"), st.ec_gpu_temp_c, st.gpu_fan_rpm, st.gpu_fan_mode),
    ):
        lines.append([
            (f"   {label:<7}", "normal"),
            (f"{fmt(temp, ' °C'):>7} ", temp_style(temp)),
            (bar(temp, TEMP_SCALE_C), temp_style(temp)),
            (f"   {t('fan')} {fmt(rpm, ' RPM'):>9} ", "normal"),
            (bar(rpm, FAN_SCALE_RPM, 10), "fan"),
            (f"  {fan_name.get(mode, '?')}", "dim"),
        ])

    if st.gpu_runtime is not None:
        if st.gpu_runtime != "active":
            gtxt, gsty = t("gpu_asleep"), "dim"
        elif gpu_paused or gpu is None:
            gtxt, gsty = t("gpu_idle_paused") if gpu_paused else t("gpu_awake"), "dim"
        else:
            parts = [f"{fmt(gpu.power_w, ' W', 1)} / {fmt(gpu.limit_w, ' W')}"]
            if gpu.util_pct is not None:
                parts.append(f"{gpu.util_pct}%")
            gtxt, gsty = " · ".join(parts), "normal"
        lines.append([(f"   {'':<7}", "normal"), (f"{t('power')}: ", "dim"), (gtxt, gsty)])

    if st.ec_sys_temp_c is not None:
        lines.append([(f"   {t('system'):<7}", "normal"),
                      (f"{fmt(st.ec_sys_temp_c, ' °C'):>7}", temp_style(st.ec_sys_temp_c))])
    lines.append([(f"   {t('limits')}: ", "normal"),
                  (f"PL1 {fmt(st.pl1_w, ' W')} · PL2 {fmt(st.pl2_w, ' W')}", "dim")])
    lines.append([])
    lines.append([(" " + message[0], message[1])] if message else [])
    lines.append([(f" {t('keys')}", "dim")])
    return lines


STYLES = {  # style -> (color pair id, fg, extra attr)
    "normal": (0, -1, 0), "dim": (1, 8, 0), "title": (2, curses.COLOR_CYAN, curses.A_BOLD),
    "head": (3, curses.COLOR_YELLOW, curses.A_BOLD), "sel": (4, curses.COLOR_CYAN, curses.A_BOLD),
    "active": (5, curses.COLOR_GREEN, curses.A_BOLD), "ok": (6, curses.COLOR_GREEN, 0),
    "warm": (7, curses.COLOR_YELLOW, 0), "hot": (8, curses.COLOR_RED, curses.A_BOLD),
    "fan": (9, curses.COLOR_BLUE, 0), "err": (10, curses.COLOR_RED, curses.A_BOLD),
}


def _init_colors() -> dict[str, int]:
    attrs = {k: 0 for k in STYLES}
    if not curses.has_colors():
        attrs.update(title=curses.A_BOLD, head=curses.A_BOLD, sel=curses.A_REVERSE,
                     active=curses.A_BOLD, hot=curses.A_BOLD, err=curses.A_BOLD,
                     dim=curses.A_DIM)
        return attrs
    curses.start_color()
    curses.use_default_colors()
    for name, (pair, fg, extra) in STYLES.items():
        if pair == 0:
            continue
        if fg >= curses.COLORS:   # 8-color terminals: no bright black
            attrs[name] = curses.A_DIM | extra
            continue
        curses.init_pair(pair, fg, -1)
        attrs[name] = curses.color_pair(pair) | extra
    return attrs


def _draw(win, lines: list[Line], attrs: dict[str, int], t: T) -> None:
    win.erase()
    h, w = win.getmaxyx()
    if h < len(lines) or w < 40:
        win.addnstr(0, 0, t("too_small"), max(0, w - 1))
        win.refresh()
        return
    for y, line in enumerate(lines):
        x = 0
        for text, style in line:
            if x >= w - 1:
                break
            win.addnstr(y, x, text, w - 1 - x, attrs.get(style, 0))
            x += len(text)
    win.refresh()


def run(stdscr, sysfs: Sysfs, lang: Optional[str] = None) -> None:
    t = T(lang)
    attrs = _init_colors()
    curses.curs_set(0)
    stdscr.timeout(250)
    monitor = GpuMonitor()
    st = sysfs.read()
    selected = profiles.ORDER.index(st.profile) if st.profile in profiles.ORDER else 1
    message: Optional[Segment] = None
    message_until = 0.0
    next_read = 0.0
    gpu: Optional[GpuSample] = None

    def switch(name: str) -> None:
        nonlocal message, message_until, st
        _draw(stdscr, build_screen(st, gpu, False, selected,
                                   (t("applying", mode=t(name)), "dim"), t), attrs, t)
        try:
            profiles.apply(name)
            st = sysfs.read()
            message = (t("applied", mode=t(name)), "ok")
        except profiles.NotInstalled:
            message = (t("not_installed"), "err")
        except profiles.ApplyError as exc:
            message = (t("failed", err=str(exc)), "err")
        message_until = time.monotonic() + 4

    while True:
        now = time.monotonic()
        if now >= next_read:
            st = sysfs.read()
            gpu = monitor.poll(st.gpu_runtime)
            next_read = now + REFRESH_S
        if message and now >= message_until:
            message = None
        paused = st.gpu_runtime == "active" and monitor.backing_off()
        _draw(stdscr, build_screen(st, gpu, paused, selected, message, t), attrs, t)

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            return
        if key in (curses.KEY_UP, ord("k")):
            selected = (selected - 1) % len(profiles.ORDER)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = (selected + 1) % len(profiles.ORDER)
        elif key in (ord("1"), ord("2"), ord("3")):
            selected = key - ord("1")
            switch(profiles.ORDER[selected])
        elif key in (curses.KEY_ENTER, 10, 13, ord(" ")):
            switch(profiles.ORDER[selected])
        elif key in (ord("c"), ord("C")):
            name = profiles.next_profile(st.profile)
            selected = profiles.ORDER.index(name)
            switch(name)
        elif key == curses.KEY_RESIZE:
            stdscr.clear()
