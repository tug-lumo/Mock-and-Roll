"""Make a 360° calibration frame (equirectangular, 2:1) for checking how Mock & Roll maps
environments onto the LED surfaces.

    python tools/make-test-equirect.py  [out.png]  [width]

Grid every 15° (bold every 45°), horizon in seafoam, labelled directions:
FRONT (0°, straight into the volume), RIGHT (+90°), LEFT (-90°), BACK (180°), UP and DOWN.
Each 90° quadrant has its own tint so seams/orientation are obvious at a glance.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "environments", "source", "calibration-grid.png")
W = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
H = W // 2
img = Image.new("RGB", (W, H), (19, 25, 26))
d = ImageDraw.Draw(img)


def x_of(lon):  # lon -180..180 -> x
    return (lon + 180.0) / 360.0 * W


def y_of(lat):  # lat 90..-90 -> y
    return (90.0 - lat) / 180.0 * H


# Quadrant tints (front = blue, right = salmon, back = grey, left = green)
tints = [(-45, 45, (14, 44, 92)), (45, 135, (92, 34, 38)), (-135, -45, (20, 70, 52))]
for a, b, c in tints:
    d.rectangle([x_of(a), 0, x_of(b), H], fill=c)
d.rectangle([x_of(135), 0, W, H], fill=(48, 50, 56))
d.rectangle([0, 0, x_of(-135), H], fill=(48, 50, 56))
grid = (200, 210, 215)
for lon in range(-180, 181, 15):
    w = 5 if lon % 45 == 0 else 1
    d.line([(x_of(lon), 0), (x_of(lon), H)], fill=grid, width=w)
for lat in range(-90, 91, 15):
    w = 5 if lat % 45 == 0 else 1
    d.line([(0, y_of(lat)), (W, y_of(lat))], fill=grid, width=w)
d.line([(0, y_of(0)), (W, y_of(0))], fill=(0, 239, 234), width=9)   # horizon

try:
    big = ImageFont.truetype("arialbd.ttf", W // 34)
    small = ImageFont.truetype("arial.ttf", W // 110)
except OSError:
    big = small = ImageFont.load_default()


def label(text, lon, lat, font, fill=(255, 255, 255)):
    x, y = x_of(lon), y_of(lat)
    bb = d.textbbox((0, 0), text, font=font)
    d.text((x - (bb[2] - bb[0]) / 2, y - (bb[3] - bb[1]) / 2), text, font=font, fill=fill, stroke_width=3, stroke_fill=(0, 0, 0))


label("FRONT", 0, 12, big)
label("RIGHT", 90, 12, big)
label("LEFT", -90, 12, big)
label("BACK", 180 - 0.01, 12, big)
label("BACK", -180 + 0.01, 12, big)
label("UP", 0, 70, big, (255, 220, 120))
label("DOWN", 0, -70, big, (255, 220, 120))
for lon in range(-180, 181, 45):
    for lat in (-45, 0, 45):
        label(f"{lon}°,{lat}°", lon + 4, lat + 3, small, (230, 235, 240))

os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
img.save(out)
print("wrote", os.path.abspath(out), img.size)
