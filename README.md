# dotfiles

Minimal dark i3 setup for Arch Linux (X11). Keyboard-first, one maximized
window at a time, Windows-style Alt+Tab.

![palette](https://img.shields.io/badge/bg-%23101014-101014) ![accent](https://img.shields.io/badge/accent-%237aa2f7-7aa2f7)

## What's in it

| Piece | Notes |
|---|---|
| **i3** | gaps, thin accent borders, every new app window opens maximized |
| **alacritty** | JetBrains Mono Nerd Font, 92% opacity, matching palette |
| **picom** | subtle shadows + fade, rounded corners, no blur |
| **i3status** | wifi / battery / memory / clock with Nerd Font glyphs |
| **dmenu + rofi** | dmenu for launching, rofi for the window picker |
| **dunst** | notifications, plus a systemd timer that warns at 15% battery |
| **ly** | TUI login manager, themed to match, remembers your user |
| **i3lock** | PAM config that skips `pam_faillock`, so a typo can't lock you out for 10 min |
| **focus_history.py** | small daemon giving Alt+Tab real MRU cycling and minimize/restore |
| **touchpad** | libinput tap-to-click |

## Keys (`$mod` = Super)

| Key | Action |
|---|---|
| `$mod+Return` | new terminal (maximized) |
| `$mod+d` | app launcher |
| `Alt+Tab` / `Alt+Shift+Tab` | cycle windows, most-recent first — hold Alt, tap Tab, release to land |
| `$mod+Shift+Tab` | rofi window picker (type to filter) |
| `$mod+minus` | minimize focused window |
| `$mod+Shift+underscore` | restore last minimized window |
| `$mod+m` | minimize everything on the workspace |
| `$mod+f` | toggle fullscreen (see the tiling layout underneath) |
| `$mod+Shift+space` | toggle floating |
| `$mod+1..0` / `$mod+Tab` | workspaces / bounce to previous |
| `$mod+Shift+x` | lock screen |
| `$mod+p` / `$mod+Shift+p` | screenshot / region screenshot → `~/Pictures` |
| `$mod+Shift+q` | close window |
| `$mod+Shift+c` / `$mod+Shift+r` | reload / restart i3 |

## Install

Clone and symlink (keeps the repo as the live config, so edits are tracked):

```sh
git clone https://github.com/thefoulowl/dotfiles ~/dotfiles
~/dotfiles/install.sh
```

Or the single-file version, no clone — same result, files are copied not linked:

```sh
curl -fsSLO https://raw.githubusercontent.com/thefoulowl/dotfiles/main/arch-i3-rice.sh
chmod +x arch-i3-rice.sh && ./arch-i3-rice.sh
```

Both back up anything they'd overwrite as `*.bak-<timestamp>`. Reboot afterwards
for the login manager and touchpad settings to take effect.

To retheme, edit the five colours at the top of `arch-i3-rice.sh` before running
it. It's generated from the repo by `./build-rice.sh` — never edit it by hand.

## Layout

```
config/          -> symlinked into ~/.config by install.sh
  i3/            config + scripts/ (focus_history.py, battery_warn.sh)
  systemd/user/  focus-history daemon, battery-warn timer
etc/             -> copied to / with sudo
  pam.d/i3lock, X11/xorg.conf.d/30-touchpad.conf, ly/config.ini
install.sh       clone-and-link installer
build-rice.sh    generates arch-i3-rice.sh from the above
```

## Two things worth knowing

- `focus_follows_mouse no` is deliberate: with it on (i3's default), the cursor
  merely passing over a window counts as focusing it, which scrambles the
  Alt+Tab history.
- i3 refuses to focus a *new* window while the current one is fullscreen (so
  a video isn't interrupted). Since everything here is fullscreen, the config
  works around it: `$mod+Return` drops fullscreen first, and the `for_window`
  rule explicitly focuses new windows.
