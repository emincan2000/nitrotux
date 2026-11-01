"""Command line entry point: `nitrotux [tui|status|set|cycle]`."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

from . import __version__, profiles
from .hw import Sysfs
from .i18n import T


def _notify(title: str, body: str, urgent: bool = False) -> None:
    exe = shutil.which("notify-send")
    if not exe:
        return
    cmd = [exe, "-t", "2000", "-h", "string:x-canonical-private-synchronous:nitrotux"]
    if urgent:
        cmd += ["-u", "critical"]
    subprocess.run(cmd + [title, body], check=False)


def _switch(name: str, t: T, notify: bool) -> int:
    try:
        profiles.apply(name)
    except profiles.NotInstalled:
        msg = t("not_installed")
    except profiles.ApplyError as exc:
        msg = t("failed", err=str(exc))
    else:
        p = profiles.PROFILES[name]
        desc = t(f"desc_{name}", pl1=p.pl1_w, pl2=p.pl2_w)
        print(f"{t('applied', mode=t(name))} — {desc}")
        if notify:
            _notify("Nitrotux", f"{t('applied', mode=t(name))}\n{desc}")
        return 0
    print(msg, file=sys.stderr)
    if notify:
        _notify("Nitrotux", msg, urgent=True)
    return 1


def _fan(rpm: int | None, mode: str | None) -> str | None:
    if rpm is None:
        return None
    return f"{rpm} RPM ({mode})" if mode else f"{rpm} RPM"


def _limits(pl1: int | None, pl2: int | None) -> str | None:
    if pl1 is None and pl2 is None:
        return None
    pairs = (("PL1", pl1), ("PL2", pl2))
    return " · ".join(f"{name} {'—' if w is None else w} W" for name, w in pairs)


def _gpu_power(runtime: str | None, t: T) -> str | None:
    if runtime is None:
        return None
    return t("gpu_awake") if runtime == "active" else t("gpu_asleep")


def _status(sysfs: Sysfs, as_json: bool, t: T) -> int:
    st = sysfs.read()
    if as_json:
        print(json.dumps(st.as_dict(), indent=2, ensure_ascii=False))
        return 0
    rows = [
        (t("modes"), t(st.profile) if st.profile in profiles.PROFILES else (st.profile or "?")),
        (f"{t('cpu')} °C", st.cpu_temp_c),
        (f"{t('gpu')} °C", st.ec_gpu_temp_c),
        (f"{t('cpu')} {t('fan')}", _fan(st.cpu_fan_rpm, st.cpu_fan_mode)),
        (f"{t('gpu')} {t('fan')}", _fan(st.gpu_fan_rpm, st.gpu_fan_mode)),
        (t("limits"), _limits(st.pl1_w, st.pl2_w)),
        (t("gpu"), _gpu_power(st.gpu_runtime, t)),
    ]
    for k, v in rows:
        print(f"{k:<14} {v if v is not None else '—'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nitrotux",
                                 description="Mode switching and fan/thermal dashboard "
                                             "for the Acer Nitro AN515-58 on Linux.")
    ap.add_argument("--lang", choices=("en", "tr"), help="interface language")
    ap.add_argument("--version", action="version", version=f"Nitrotux {__version__}")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("tui", help="interactive dashboard (default)")
    s = sub.add_parser("status", help="print current state")
    s.add_argument("--json", action="store_true")
    m = sub.add_parser("set", help="switch mode")
    m.add_argument("mode", choices=profiles.ORDER)
    m.add_argument("--notify", action="store_true", help="desktop notification")
    c = sub.add_parser("cycle", help="quiet -> balanced -> performance -> quiet")
    c.add_argument("--notify", action="store_true", help="desktop notification")
    args = ap.parse_args(argv)

    t = T(args.lang)
    sysfs = Sysfs()
    if args.cmd == "status":
        return _status(sysfs, args.json, t)
    if args.cmd == "set":
        return _switch(args.mode, t, args.notify)
    if args.cmd == "cycle":
        return _switch(profiles.next_profile(sysfs.read().profile), t, args.notify)

    if not sys.stdout.isatty():
        return _status(sysfs, False, t)
    import curses
    from . import tui
    curses.wrapper(tui.run, sysfs, args.lang)
    return 0
