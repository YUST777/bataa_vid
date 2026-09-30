#!/usr/bin/env python3
"""Recreate the bataa.app TikTok profile as a 1024x2048 phone-screen texture."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
W, H = 1024, 2048
F = lambda s, w=400: _f(s, w)


def _f(size, wght):
    f = ImageFont.truetype(f"{ROOT}/assets/Inter.ttf", size)
    try: f.set_variation_by_axes([min(max(size * 0.75, 14), 32), wght])
    except Exception: pass
    return f


im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
INK, GREY, LIGHT = (22, 24, 35), (120, 122, 130), (241, 241, 242)
# status bar
d.text((44, 30), "3:05", font=F(40, 600), fill=INK)
d.rounded_rectangle((900, 36, 980, 76), 16, fill=(90, 90, 90)); d.text((922, 38), "17", font=F(30, 600), fill="white")
# nav
d.line((50, 165, 100, 165), fill=INK, width=6); d.line((50, 165, 72, 143), fill=INK, width=6); d.line((50, 165, 72, 187), fill=INK, width=6)
d.arc((800, 135, 850, 190), 200, 340, fill=INK, width=6); d.line((800, 178, 850, 178), fill=INK, width=6)
d.polygon([(900, 150), (940, 150), (940, 130), (978, 165), (940, 200), (940, 180), (900, 180)], outline=INK, width=5)
# name + avatar
d.text((44, 250), "bataa.app", font=F(92, 800), fill=INK)
d.text((44, 360), "@bataa_app", font=F(34, 400), fill=GREY)
cx, cy, r = 855, 330, 125
av = Image.new("RGBA", (2 * r, 2 * r)); ImageDraw.Draw(av).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=(252, 232, 196))
duck = Image.open("/home/yousefmsm1/Desktop/blender/bataa.png").convert("RGBA"); duck = duck.crop(duck.getbbox())
duck = duck.resize((int(2 * r * 1.15), int(2 * r * 1.15 * duck.height / duck.width)), Image.LANCZOS)
av.alpha_composite(duck, (-20, 30))
mask = Image.new("L", (2 * r, 2 * r)); ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
im.paste(av, (cx - r, cy - r), mask)
d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(236, 225, 210), width=4)
# stats
for x, n, lab in ((44, "0", "Following"), (270, "37", "Followers"), (470, "88", "Likes")):
    d.text((x, 440), n, font=F(52, 800), fill=INK); d.text((x, 505), lab, font=F(34, 400), fill=GREY)
# buttons
d.rounded_rectangle((44, 590, 505, 690), 50, fill=LIGHT); d.text((190, 616), "Message", font=F(40, 650), fill=INK)
d.rounded_rectangle((525, 590, 855, 690), 50, fill=LIGHT); d.text((570, 616), "Following", font=F(40, 650), fill=INK)
d.polygon([(800, 632), (830, 632), (815, 650)], fill=INK)
d.ellipse((875, 590, 975, 690), fill=LIGHT); d.ellipse((905, 612, 935, 642), fill=INK); d.pieslice((892, 640, 948, 690), 180, 360, fill=INK)
# bio
d.text((44, 730), "bataa.app | Your AI Mentor for Learning by Doing.", font=F(34, 450), fill=INK)
# tab
for i in range(3): d.line((440 + i * 22, 810, 440 + i * 22, 850), fill=INK, width=6)
d.polygon([(518, 822), (540, 822), (529, 836)], fill=INK)
d.line((410, 870, 600, 870), fill=INK, width=5); d.line((0, 874, W, 874), fill=(230, 230, 232), width=2)


def thumb(src, box, crop_frac, views):
    x0, y0, x1, y1 = box
    t = Image.open(src).convert("RGB")
    w, h = t.size; cw = int(h * (x1 - x0) / (y1 - y0))
    cxp = int(w * crop_frac); t = t.crop((max(0, cxp - cw // 2), 0, max(0, cxp - cw // 2) + cw, h)).resize((x1 - x0, y1 - y0), Image.LANCZOS)
    g = Image.new("L", t.size, 0); ImageDraw.Draw(g).rectangle((0, t.height - 140, t.width, t.height), fill=160)
    t.paste((0, 0, 0), (0, 0), g.filter(ImageFilter.GaussianBlur(40)))
    im.paste(t, (x0, y0)); dd = ImageDraw.Draw(im)
    dd.polygon([(x0 + 22, y1 - 62), (x0 + 22, y1 - 26), (x0 + 50, y1 - 44)], outline="white", width=5)
    dd.text((x0 + 66, y1 - 70), views, font=F(38, 650), fill="white")

thumb(f"{ROOT}/review/ad3d/t_090.png", (0, 878, 338, 1330), 0.55, "1,938")
thumb(f"{ROOT}/review/ad3d/t_300.png", (342, 878, 680, 1330), 0.45, "980")
# android nav bar
for i in range(3): d.line((200 + i * 18, 1970, 200 + i * 18, 2010), fill=GREY, width=5)
d.rounded_rectangle((487, 1968, 537, 2012), 14, outline=GREY, width=5)
d.line((800, 1990, 822, 1968), fill=GREY, width=5); d.line((800, 1990, 822, 2012), fill=GREY, width=5)
im.save(f"{ROOT}/assets/tiktok_screen.png"); im.resize((256, 512)).save(f"{ROOT}/review/tiktok_a.png")
print("ok")
