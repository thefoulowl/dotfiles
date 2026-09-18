#!/usr/bin/env bash
#
# Install these dotfiles on an Arch + i3 (X11) machine.
# Symlinks config/* into ~/.config, installs the system files under etc/
# with sudo, and enables the systemd user units + ly login manager.
# Existing configs are moved aside as *.bak-<timestamp>.
#
# For a single self-contained script instead (no clone needed) see
# arch-i3-rice.sh, which build-rice.sh generates from this repo.

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"

backup() { [ -e "$1" ] && [ ! -L "$1" ] && mv "$1" "$1.bak-$TS" && echo "  backed up $1"; return 0; }

echo "==> Installing packages"
sudo pacman -S --needed --noconfirm \
    i3-wm i3status dmenu alacritty xorg-server xorg-xinit \
    picom ttf-jetbrains-mono-nerd \
    i3lock xss-lock maim brightnessctl rofi dunst libnotify xcape \
    feh python python-pillow fastfetch \
    ly

echo "==> Linking ~/.config"
mkdir -p ~/.config ~/.config/systemd/user ~/Pictures
for c in i3 alacritty picom rofi i3status dunst wireplumber; do
    backup ~/.config/$c
    ln -sfn "$REPO/config/$c" ~/.config/$c
done
for u in "$REPO"/config/systemd/user/*; do
    backup ~/.config/systemd/user/"$(basename "$u")"
    ln -sfn "$u" ~/.config/systemd/user/"$(basename "$u")"
done
backup ~/.inputrc
ln -sfn "$REPO/inputrc" ~/.inputrc
backup ~/.bashrc
ln -sfn "$REPO/bashrc" ~/.bashrc
backup ~/.config/wallpaper
ln -sfn "$REPO/wallpaper" ~/.config/wallpaper
mkdir -p ~/.local/bin && ln -sfn "$REPO/bin/osd" ~/.local/bin/osd

echo "==> Generating wallpaper"
(cd "$REPO/wallpaper" && python3 generate.py)

echo "==> Installing system files (sudo)"
sudo install -Dm644 "$REPO/etc/pam.d/i3lock" /etc/pam.d/i3lock
sudo install -Dm644 "$REPO/etc/X11/xorg.conf.d/30-touchpad.conf" /etc/X11/xorg.conf.d/30-touchpad.conf
sudo install -Dm644 "$REPO/etc/ly/config.ini" /etc/ly/config.ini
# ly battery id is machine-specific
BAT="$(basename "$(ls -d /sys/class/power_supply/BAT* 2>/dev/null | head -1)" 2>/dev/null || true)"
sudo sed -i "s|^battery_id = .*|battery_id = ${BAT:-null}|" /etc/ly/config.ini

echo "==> Enabling services"
systemctl --user daemon-reload
systemctl --user enable --now i3-focus-history.service battery-warn.timer xcape.service xss-lock.service
sudo systemctl enable ly@tty1.service

echo
echo "Done. Reboot for ly + touchpad tap-to-click. \$mod = Super, or tap it"
echo "alone for the launcher too. Alt+Tab cycles windows, \$mod+minus minimizes,"
echo "\$mod+Shift+underscore restores, \$mod+m minimizes all, \$mod+Shift+Tab"
echo "is the rofi window picker."
