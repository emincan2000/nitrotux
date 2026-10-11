# Nitrotux

Terminal dashboard and mode switcher for the **Acer Nitro AN515-58** on Linux.
It shows temperatures, fan speeds, CPU power limits and GPU power. It switches
between three modes from the keyboard, the command line, or the laptop's
**NitroSense key**.

```
 Nitrotux · Nitro AN515-58   AC · battery 100%

 Mode
    1  Quiet         CPU 45/65 W, fans auto
  ▶ 2  Balanced      CPU 115/115 W, fans auto (factory)   ● active
    3  Performance   CPU 115/115 W, fans full speed

 Sensors
   CPU      52 °C ██████░░░░░░   fan  2752 RPM ███░░░░░░░  auto
   GPU       — °C ············   fan  3157 RPM ████░░░░░░  auto
          Power: asleep (power saving)
   System   47 °C
   CPU limits: PL1 115 W · PL2 115 W

 1/2/3 mode   ↑↓ Enter select   c cycle   q quit
```

> Türkçe açıklama aşağıda — [Türkçe](#türkçe).

## Modes

| Mode | CPU package limit (PL1 / PL2) | Fans |
|---|---|---|
| Quiet | 45 W / 65 W | firmware auto |
| Balanced | 115 W / 115 W (factory default) | firmware auto |
| Performance | 115 W / 115 W | firmware turbo (full speed, ~8000 RPM) |

Each mode also sets the ACPI `platform_profile` of the same name.

**Why not just `platform_profile`?** On the AN515-58 the firmware accepts the
profile but changes nothing you can measure under Linux. CPU limits, GPU limit
and fan behaviour stay the same in all three modes. Nitrotux therefore sets the
CPU limits (Intel RAPL) and the fan mode (acer_wmi) itself.

**GPU power:** the RTX 4060 runs at 80 W base + 25 W Dynamic Boost = 105 W in
every mode, provided `nvidia-powerd` is running. The 140 W that NitroSense
reaches on Windows could not be unlocked on Linux.

## Requirements

* Acer Nitro AN515-58. The installer refuses other models unless you pass `--force`.
* Linux **6.19 or newer**. That is the first kernel whose `acer_wmi` exposes this
  model's fan control (hwmon `pwm1_enable`).
* Python 3.9+, sudo. No other dependencies.
* For GPU readings: the NVIDIA driver (`libnvidia-ml.so.1`).
* For the NitroSense key shortcut: XFCE is set up automatically. On other
  desktops, bind `XF86Launch1` to `nitrotux cycle --notify` yourself.

Tested on Debian 13 with kernel 7.1.13 and the NVIDIA 615 open kernel module.

## Install

```sh
git clone https://github.com/emincan2000/nitrotux && cd nitrotux
python3 -m unittest discover -s tests -t .   # optional, touches nothing
sudo ./install.sh --dry-run                  # shows what would happen
sudo ./install.sh
```

What the installer does:

| Path | What |
|---|---|
| `/usr/local/lib/nitrotux/` | the Python package |
| `/usr/local/bin/nitrotux` | launcher |
| `/usr/local/sbin/nitrotux-helper` | root helper; accepts only `quiet`, `balanced`, `performance` |
| `/etc/sudoers.d/nitrotux` | lets **your** user run exactly those three helper commands without a password |
| `/etc/udev/hwdb.d/61-nitrotux-an515-58.hwdb` | maps the NitroSense key to `XF86Launch1` |
| XFCE shortcut | `XF86Launch1` → `nitrotux cycle --notify` |

Uninstall with `sudo ./uninstall.sh`. It switches back to balanced with auto
fans first, then removes everything listed above.

## Usage

```sh
nitrotux                     # dashboard
nitrotux status [--json]
nitrotux set quiet|balanced|performance [--notify]
nitrotux cycle [--notify]    # what the NitroSense key runs
nitrotux --lang tr           # Turkish UI (or NITROTUX_LANG=tr; auto from LANG=tr_*)
```

Modes are not kept across reboots. The laptop always starts in balanced.

## Notes

* **The dashboard does not keep the GPU awake.** A single NVML query wakes a
  runtime-suspended GPU for ~15 s. Nitrotux never queries NVML while the GPU
  sleeps, and it stops polling when the GPU goes idle. GPU temperature comes from
  the EC, which does not wake it.
* **Why the NitroSense key needs the hwdb file.** The key sends scancode
  `0xf5`. systemd's keyboard database maps it to `prog1` for other Nitro models
  but not for the AN515-58. There it becomes `KEY_PRESENTATION` (425), which is
  above X11's 255 keycode limit, so the desktop never sees it.
* **The root helper.** It is a 30-line shell script with hard-coded paths and
  values. It reads no environment and no config. The test suite checks that it
  rejects every other input without writing anything.

## Tests

```sh
python3 -m unittest discover -s tests -t .
```

The suite runs against a fake sysfs tree and never touches the hardware. It
covers the helper's input validation (sh, bash and dash), helper ↔ Python
consistency, sensor parsing, GPU wake-up avoidance, the screen layout and the
CLI.

Manual checks on the real machine (read-only, except that the GPU gets loaded):

```sh
python3 tests/pty_smoke.py                                  # dashboard starts, draws, quits
NITROTUX_TORCH_PYTHON=/path/to/python-with-torch python3 tests/live_gpu_sleep.py
```

## License

MIT — see [LICENSE](LICENSE).

---

## Türkçe

Linux'ta **Acer Nitro AN515-58** için terminal arayüzü. Sıcaklıkları, fan
hızlarını, CPU güç sınırlarını ve GPU gücünü gösterir. Üç mod arasında klavyeden,
komut satırından ya da laptopun **NitroSense tuşuyla** geçiş yapar.

| Mod | CPU sınırı (PL1 / PL2) | Fanlar |
|---|---|---|
| Sessiz | 45 W / 65 W | otomatik |
| Dengeli | 115 W / 115 W (fabrika) | otomatik |
| Performans | 115 W / 115 W | tam hız (~8000 RPM) |

* **Gereksinimler:** AN515-58, Linux ≥ 6.19, Python 3.9+, sudo.
* **Kurulum:** `sudo ./install.sh --dry-run`, ardından `sudo ./install.sh`.
* **Kaldırma:** `sudo ./uninstall.sh`.
* **Arayüz dili:** `nitrotux --lang tr` ya da `NITROTUX_LANG=tr`.
* **GPU gücü:** Her modda 105 W'tır (80 W + 25 W Dynamic Boost). Windows'taki
  140 W Linux'ta açılamadı.
* **NitroSense tuşu:** Her basışta Sessiz → Dengeli → Performans arasında geçer
  ve bildirim gösterir.
