#!/bin/bash
# nitrotux installer. Usage: sudo ./install.sh [--dry-run] [--force]
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

PREFIX=/usr/local
LIBDIR=$PREFIX/lib/nitrotux
BIN=$PREFIX/bin/nitrotux
HELPER=$PREFIX/sbin/nitrotux-helper
SUDOERS=/etc/sudoers.d/nitrotux
HWDB=/etc/udev/hwdb.d/61-nitrotux-an515-58.hwdb
SRC=$(cd "$(dirname "$0")" && pwd)

DRY=0 FORCE=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --force) FORCE=1 ;;
    -h|--help) echo "usage: sudo $0 [--dry-run] [--force]"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
run()  { if [ $DRY = 1 ]; then printf '  [dry-run] %s\n' "$*"; else "$@"; fi; }

# ---------------------------------------------------------------- checks
[ $DRY = 1 ] || [ "$(id -u)" = 0 ] || die "run with sudo (or --dry-run)"
TARGET_USER=${SUDO_USER:-}
[ $DRY = 1 ] && [ -z "$TARGET_USER" ] && TARGET_USER=$(id -un)
[ -n "$TARGET_USER" ] && [ "$TARGET_USER" != root ] || die "run via sudo from your normal user account"

command -v python3 >/dev/null || die "python3 not found"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "python3 >= 3.9 required"
command -v visudo >/dev/null || die "visudo not found (install sudo)"

MODEL=$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)
case "$MODEL" in
  *AN515-58*) say "model: $MODEL" ;;
  *) [ $FORCE = 1 ] || die "this is '$MODEL', not a Nitro AN515-58 (use --force at your own risk)"
     warn "model '$MODEL' is untested" ;;
esac

CHOICES=$(cat /sys/firmware/acpi/platform_profile_choices 2>/dev/null || true)
for p in quiet balanced performance; do
  case " $CHOICES " in
    *" $p "*) ;;
    *) [ $FORCE = 1 ] || die "platform profile '$p' not offered by the kernel (choices: ${CHOICES:-none})"
       warn "platform profile '$p' missing" ;;
  esac
done

ACER_HWMON=
for h in /sys/class/hwmon/hwmon*; do
  [ "$(cat "$h/name" 2>/dev/null)" = acer ] && ACER_HWMON=$h
done
if [ -z "$ACER_HWMON" ] || [ ! -e "$ACER_HWMON/pwm1_enable" ]; then
  [ $FORCE = 1 ] || die "acer_wmi fan control (hwmon pwm1_enable) not found — needs Linux >= 6.19"
  warn "no acer_wmi fan control: fan part of the modes will do nothing"
fi

# --------------------------------------------- migrate the old hand-made setup
# Only files whose content proves they came from that setup are removed.
BACKUP=/var/backups/nitrotux-migrated-$(date +%Y%m%d-%H%M%S)
migrate() {  # file marker
  [ -f "$1" ] && grep -q "$2" "$1" 2>/dev/null || return 0
  say "migrating old $1"
  run mkdir -p "$BACKUP"
  run mv "$1" "$BACKUP/"
}
migrate /usr/local/sbin/nitro-profile-set "nitro-profile-set\|izin verilen profilleri"
migrate /usr/local/bin/nitro-cycle "nitro-profile-set"
migrate /usr/local/bin/nitro-mode "nitro-profile-set"
migrate /etc/sudoers.d/nitro-profile "nitro-profile-set"
migrate /etc/udev/hwdb.d/61-acer-nitro-an515-58.hwdb "KEYBOARD_KEY_f5=prog1"

# ---------------------------------------------------------------- install
say "installing to $PREFIX"
run install -d -m 755 "$LIBDIR/nitrotux"
for f in "$SRC"/nitrotux/*.py; do
  run install -m 644 "$f" "$LIBDIR/nitrotux/"
done
WRAPPER=$(mktemp)
cat > "$WRAPPER" <<EOF
#!/bin/sh
exec /usr/bin/python3 -I -c 'import sys; sys.path.insert(0, "$LIBDIR"); from nitrotux.cli import main; sys.exit(main())' "\$@"
EOF
run install -m 755 "$WRAPPER" "$BIN"
rm -f "$WRAPPER"
run install -o root -g root -m 755 "$SRC/helper/nitrotux-helper" "$HELPER"

RULE=$(mktemp)
{
  echo "# nitrotux: switch modes without a password (only these three exact commands)"
  printf '%s ALL=(root) NOPASSWD: %s quiet, %s balanced, %s performance\n' \
    "$TARGET_USER" "$HELPER" "$HELPER" "$HELPER"
} > "$RULE"
visudo -cf "$RULE" >/dev/null || { rm -f "$RULE"; die "generated sudoers rule failed visudo check"; }
run install -o root -g root -m 440 "$RULE" "$SUDOERS"
rm -f "$RULE"

case "$MODEL" in
  *AN515-58*)
    run install -m 644 "$SRC/data/61-nitrotux-an515-58.hwdb" "$HWDB"
    run systemd-hwdb update
    run udevadm trigger --subsystem-match=input --action=change ;;
esac

# ------------------------------------------------- NitroSense key (XFCE only)
SHORTCUT="nitrotux cycle --notify"
if command -v xfconf-query >/dev/null; then
  UID_T=$(id -u "$TARGET_USER")
  if [ -S "/run/user/$UID_T/bus" ]; then
    run sudo -u "$TARGET_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$UID_T/bus" \
      xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/XF86Launch1 -n -t string -s "$SHORTCUT" \
      || warn "could not set the XFCE shortcut; add XF86Launch1 -> '$SHORTCUT' by hand"
  else
    warn "no session bus for $TARGET_USER; add XF86Launch1 -> '$SHORTCUT' in XFCE keyboard settings"
  fi
else
  say "not XFCE: bind the NitroSense key (XF86Launch1) to '$SHORTCUT' in your desktop's shortcut settings"
fi

say "done. Try: nitrotux"
[ -d "$BACKUP" ] && say "old setup backed up in $BACKUP"
exit 0
