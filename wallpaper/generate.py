#!/usr/bin/env python3
"""Generate wall.png: layered ridgelines under an accent horizon glow, from
the palette used across the rest of the rice. Deterministic (fixed seed),
so re-running always produces the same image.

    ./generate.py [width height]   # default 1920 1200
"""
import math
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

def hex_rgb(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


# same hex strings as the rest of the rice, so the standalone installer's
# palette substitution rethemes the wallpaper along with everything else
BG = hex_rgb("#101014")
ACCENT = hex_rgb("#7aa2f7")
FG = hex_rgb("#d8d8dc")
MUTED = hex_rgb("#44475a")


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


BG_DEEP = lerp(BG, (0, 0, 0), 0.3)
# ridge layers back (lightest) to front (darkest), derived from bg -> muted
RIDGES = [lerp(BG, MUTED, t) for t in (0.5, 0.3, 0.15, 0.04)]

W, H = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (1920, 1200)
SS = 2  # supersample for anti-aliased edges
w, h = W * SS, H * SS
random.seed(7)



def ridge(y_base, amp, freq, phase, rough):
    """A skyline: two sine octaves for the big shapes, plus a smoothed random
    walk for peaks. Coarse steps keep it angular (low-poly) without jitter."""
    pts, y, step = [], 0.0, w // 48
    for x in range(0, w + step, step):
        t = x / w
        base = (math.sin(t * freq * math.pi + phase) * amp
                + math.sin(t * freq * 2.7 * math.pi + phase * 1.7) * amp * 0.35)
        y = y * 0.6 + random.uniform(-rough, rough)
        pts.append((x, y_base + base + y))
    return [(0, h), *pts, (w, h)]


# background: vertical gradient, a touch deeper toward the bottom
img = Image.new("RGB", (w, h))
draw = ImageDraw.Draw(img)
for y in range(h):
    draw.line([(0, y), (w, y)], fill=lerp(BG, BG_DEEP, (y / h) ** 1.5))

# horizon glow: soft accent light behind the ridges (additive, so it lifts
# the background rather than tinting it toward black)
glow = Image.new("RGB", (w, h), (0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy = int(w * 0.68), int(h * 0.50)
R = int(h * 0.62)
# many thin rings with a smooth falloff = a true radial gradient, no banding
for i in range(60, 0, -1):
    r = R * i / 60
    a = 0.16 * (1 - i / 60) ** 2
    gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=lerp((0, 0, 0), ACCENT, a))
glow = glow.filter(ImageFilter.GaussianBlur(h * 0.05))
img = ImageChops.add(img, glow)

# moon: small, crisp, slightly off the glow's centre
draw = ImageDraw.Draw(img)
mr = int(h * 0.028)
mx, my = int(w * 0.70), int(h * 0.36)
draw.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=lerp(FG, ACCENT, 0.25))

# ridgelines, back to front
layers = [
    (0.56, 0.05, 2.2, 0.4, h * 0.010),
    (0.64, 0.06, 3.1, 2.0, h * 0.012),
    (0.73, 0.05, 2.6, 4.1, h * 0.014),
    (0.83, 0.04, 1.8, 1.1, h * 0.016),
]
for color, (yb, amp, freq, phase, rough) in zip(RIDGES, layers):
    draw.polygon(ridge(h * yb, h * amp, freq, phase, rough), fill=color)

img = img.resize((W, H), Image.LANCZOS)

# faint grain: the sky gradient spans only a handful of 8-bit levels, so
# without dithering it shows visible bands
grain = Image.effect_noise((W, H), 6).convert("RGB")
img = Image.blend(img, ImageChops.add(img, grain, scale=1.0, offset=-128), 0.5)

img.save("wall.png", optimize=True)
print(f"wrote wall.png ({W}x{H})")
