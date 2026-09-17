#!/usr/bin/env bash
# Warn once when the battery drops to the threshold while discharging.
# Runs from battery-warn.timer every couple of minutes.
THRESHOLD=15
STAMP="${XDG_RUNTIME_DIR:-/tmp}/battery-warned"

bat=$(ls -d /sys/class/power_supply/BAT* 2>/dev/null | head -1)
[ -n "$bat" ] || exit 0

status=$(cat "$bat/status")
level=$(cat "$bat/capacity")

if [ "$status" = "Discharging" ] && [ "$level" -le "$THRESHOLD" ]; then
    if [ ! -e "$STAMP" ]; then
        notify-send -u critical "Battery low" "${level}% remaining — plug in soon"
        touch "$STAMP"
    fi
else
    rm -f "$STAMP"
fi
