#!/bin/bash
# nitrotux uninstaller. Usage: sudo ./uninstall.sh [--dry-run]
# Restores the factory mode (balanced, fans auto) before removing anything.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

PREFIX=/usr/local
HELPER=$PREFIX/sbin/nitrotux-helper
DRY=0
[ "${1:-}" = --dry-run ] && DRY=1
run() { if [ $DRY = 1 ]; then printf '  [dry-run] %s\n' "$*"; else "$@"; fi; }

[ $DRY = 1 ] || [ "$(id -u)" = 0 ] || { echo "run with sudo (or --dry-run)" >&2; exit 1; }

[ -x "$HELPER" ] && run "$HELPER" balanced || true

run rm -f /etc/sudoers.d/nitrotux "$HELPER" "$PREFIX/bin/nitrotux"
run rm -rf "$PREFIX/lib/nitrotux"
if [ -f /etc/udev/hwdb.d/61-nitrotux-an515-58.hwdb ]; then
  run rm -f /etc/udev/hwdb.d/61-nitrotux-an515-58.hwdb
  run systemd-hwdb update
  run udevadm trigger --subsystem-match=input --action=change
fi

U=${SUDO_USER:-}
if [ -n "$U" ] && command -v xfconf-query >/dev/null && [ -S "/run/user/$(id -u "$U")/bus" ]; then
  BUS="unix:path=/run/user/$(id -u "$U")/bus"
  CUR=$(sudo -u "$U" DBUS_SESSION_BUS_ADDRESS="$BUS" \
        xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/XF86Launch1 2>/dev/null || true)
  case "$CUR" in
    *nitrotux*) run sudo -u "$U" DBUS_SESSION_BUS_ADDRESS="$BUS" \
                  xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/XF86Launch1 -r ;;
  esac
fi
[ $DRY = 1 ] && echo "dry-run: nothing changed" || echo "nitrotux removed (mode reset to balanced, fans auto)."
