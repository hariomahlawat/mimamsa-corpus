#!/usr/bin/env python3
"""Crop a region of a full-page render for closer reading (offline).

Usage: python -I crop_png.py <in.png> <out.png> <x0> <y0> <x1> <y1> [--scale 2] [--log crops.csv]
Coordinates are fractions (0..1) of the source image width/height. The crop is
taken from the hashed full-page render and enlarged with Lanczos resampling
(enlargement adds no information; it only helps on-screen reading). The sha256
of the source PNG and of the crop are appended to --log.
"""
import argparse, csv, hashlib, os
from PIL import Image


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('x0', type=float); ap.add_argument('y0', type=float)
ap.add_argument('x1', type=float); ap.add_argument('y1', type=float)
ap.add_argument('--scale', type=float, default=2.0)
ap.add_argument('--log')
a = ap.parse_args()
im = Image.open(a.src)
W, H = im.size
box = (int(a.x0 * W), int(a.y0 * H), int(a.x1 * W), int(a.y1 * H))
c = im.crop(box)
if a.scale != 1:
    c = c.resize((int(c.width * a.scale), int(c.height * a.scale)), Image.LANCZOS)
c.save(a.dst)
if a.log:
    new = not os.path.exists(a.log)
    with open(a.log, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['crop_png', 'crop_sha256', 'source_png', 'source_png_sha256', 'box_px', 'scale'])
        w.writerow([os.path.basename(a.dst), sha(a.dst), os.path.basename(a.src), sha(a.src), '%d,%d,%d,%d' % box, a.scale])
print(a.dst, sha(a.dst))
