#!/usr/bin/env python3
"""Contact sheet: python3 sheet.py out.png "label" img1 img2 ... [--ref]"""
import sys
from PIL import Image, ImageDraw, ImageFont

out, label, *imgs = sys.argv[1:]
use_ref = "--ref" in imgs
imgs = [i for i in imgs if i != "--ref"]
if use_ref:
    imgs = ["/home/yousefmsm1/Desktop/blender/bataa.png"] + imgs
S = 600
sheet = Image.new("RGB", (S * len(imgs), S + 60), (48, 48, 48))
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
for i, p in enumerate(imgs):
    im = Image.open(p).convert("RGBA").resize((S, S))
    bg = Image.new("RGB", (S, S), (255, 255, 255) if (use_ref and i == 0) else (61, 61, 61))
    bg.paste(im, mask=im)
    sheet.paste(bg, (i * S, 60))
ImageDraw.Draw(sheet).text((16, 10), label, fill=(230, 230, 90), font=font)
sheet.save(out)
