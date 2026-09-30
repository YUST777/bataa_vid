#!/usr/bin/env python3
"""2D 'screen recording' segment: real Blender UI captures + Bataa 2D course panel + 2D pet + cursor.
Composites at 2560x1440 (native capture), writes 1920x1080 frames.

python3 screen2d.py            -> screen_frames/s_0000..0209.png + screen_start.png / screen_after.png
python3 screen2d.py 0 60 130   -> only those frames (review)
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
CAP, OUT = f"{ROOT}/ui_caps", f"{ROOT}/screen_frames"
os.makedirs(OUT, exist_ok=True)
N = 210
W, H = 2560, 1440

ORANGE = (255, 106, 19); ORANGE_D = (240, 84, 0)
INK = (34, 30, 28); MUTED = (125, 115, 108); CREAM = (255, 249, 243); LINE = (240, 226, 212)

C0 = Image.open(f"{CAP}/C0.png").convert("RGBA")
C4 = Image.open(f"{CAP}/C4.png").convert("RGBA")
ADD = Image.open(f"{CAP}/add_menu.png"); SUB = Image.open(f"{CAP}/mesh_sub.png")
MJ = json.load(open(f"{CAP}/menus.json"))
DUCK = Image.open("/home/yousefmsm1/Desktop/blender/bataa.png").convert("RGBA")
DUCK = DUCK.crop(DUCK.getbbox())


def font(size, wght=400):
    f = ImageFont.truetype(f"{ROOT}/assets/Inter.ttf", size)
    try:
        f.set_variation_by_axes([min(max(size * 0.75, 14), 32), wght])
    except Exception:
        pass
    return f

F = {k: font(*v) for k, v in {"logo": (54, 800), "bub": (31, 500), "title": (35, 700), "step": (31, 650),
                             "body": (30, 450), "chip": (26, 550), "input": (28, 400), "key": (34, 650)}.items()}

# ---------------------------------------------------------------- timing helpers
def ss(a, b, t):
    x = min(max((t - a) / (b - a), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))

# ---------------------------------------------------------------- menu geometry (2560 space)
AO = MJ["add"]["origin"]; AB = MJ["add"]["body"]; MR = MJ["add"]["mesh_row"]
SB = MJ["sub"]["body"]; PR = MJ["sub"]["plane_row"]; CR = MJ["sub"]["cube_row"]
ADD_POS = (AO[0] - 330, AO[1] - 40)                       # where the Add menu pops (under the cursor)
MESH_PT = (ADD_POS[0] + AB[0] + 95, ADD_POS[1] + (MR[0] + MR[1]) // 2)
SUB_POS = (ADD_POS[0] + AB[2] - SB[0] - 3, ADD_POS[1] + MR[0] - PR[0])
CUBE_PT = (SUB_POS[0] + SB[0] + 95, SUB_POS[1] + (CR[0] + CR[1]) // 2)
OPEN_PT = (MESH_PT[0] - 20, MESH_PT[1])

# ---------------------------------------------------------------- panel
PX0, PY0, PX1, PY1 = 1735, 118, 2478, 1010
CARD = (PX0 + 34, PY0 + 360, PX1 - 34, PY0 + 700)


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines


def panel(t, state):
    """state: dict(bubble, chars, step, stepline, body, done_dots)"""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((PX0 + 6, PY0 + 18, PX1 + 6, PY1 + 22), 34, fill=150)
    L.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(26)).point(lambda v: v * 0.55))
    d = ImageDraw.Draw(L)
    d.rounded_rectangle((PX0, PY0, PX1, PY1), 34, fill=CREAM + (255,), outline=LINE + (255,), width=2)
    # header
    d.text((PX0 + 42, PY0 + 34), "bataa", font=F["logo"], fill=ORANGE)
    # pin + close icons
    cx = PX1 - 58; cy = PY0 + 66
    d.line((cx - 16, cy - 16, cx + 16, cy + 16), fill=INK, width=4); d.line((cx - 16, cy + 16, cx + 16, cy - 16), fill=INK, width=4)
    px = PX1 - 138
    d.polygon([(px - 10, cy - 20), (px + 12, cy - 20), (px + 8, cy - 2), (px + 16, cy + 6), (px - 14, cy + 6), (px - 6, cy - 2)], fill=INK)
    d.line((px + 1, cy + 6, px + 1, cy + 24), fill=INK, width=4)
    d.line((PX0, PY0 + 128, PX1, PY0 + 128), fill=LINE, width=2)
    # avatar + bubble
    av = DUCK.resize((150, int(150 * DUCK.height / DUCK.width)), Image.LANCZOS)
    L.alpha_composite(av, (PX0 + 38, PY0 + 160))
    bx0, by0, bx1, by1 = PX0 + 205, PY0 + 162, PX1 - 36, PY0 + 318
    d.rounded_rectangle((bx0, by0, bx1, by1), 26, fill=(255, 255, 255, 255), outline=LINE + (255,), width=2)
    d.polygon([(bx0, by0 + 52), (bx0 - 18, by0 + 66), (bx0, by0 + 80)], fill=(255, 255, 255, 255))
    d.line((bx0, by0 + 52, bx0 - 18, by0 + 66), fill=LINE, width=2); d.line((bx0 - 18, by0 + 66, bx0, by0 + 80), fill=LINE, width=2)
    txt = state["bubble"][: state["chars"]]
    lines = wrap(d, state["bubble"], F["bub"], bx1 - bx0 - 56)
    shown, y, left = [], by0 + 28, len(txt)
    for ln in lines:
        part = ln[:max(0, left)]; left -= len(ln) + 1
        d.text((bx0 + 28, y), part, font=F["bub"], fill=INK); y += 42
    # step card
    x0, y0, x1, y1 = CARD
    d.rounded_rectangle(CARD, 28, fill=(255, 255, 255, 255), outline=LINE + (255,), width=2)
    d.text((x0 + 34, y0 + 34), "Create your first 3D object", font=F["title"], fill=INK)
    # time chip
    d.rounded_rectangle((x1 - 142, y0 + 30, x1 - 26, y0 + 82), 26, outline=LINE + (255,), width=2, fill=(255, 255, 255, 255))
    ccx, ccy = x1 - 122, y0 + 56
    d.ellipse((ccx - 13, ccy - 13, ccx + 13, ccy + 13), outline=INK, width=3); d.line((ccx, ccy, ccx, ccy - 8), fill=INK, width=3)
    d.line((ccx, ccy, ccx + 6, ccy + 4), fill=INK, width=3)
    d.text((x1 - 100, y0 + 40), "8 min", font=F["chip"], fill=INK)
    d.text((x0 + 34, y0 + 104), state["stepline"], font=F["step"], fill=ORANGE)
    d.text((x0 + 34, y0 + 158), state["body"], font=F["body"], fill=(70, 64, 60))
    # progress dots
    dy = y0 + 262; n = 6; sx0, sx1 = x0 + 50, x1 - 50
    d.line((sx0, dy, sx1, dy), fill=LINE, width=4)
    done = state["done_dots"]
    fx = sx0 + (sx1 - sx0) * (done - 1) / (n - 1)
    d.line((sx0, dy, fx, dy), fill=ORANGE, width=4)
    for i in range(n):
        xx = sx0 + (sx1 - sx0) * i / (n - 1)
        if i < done - 1:
            d.ellipse((xx - 11, dy - 11, xx + 11, dy + 11), fill=ORANGE)
        elif i == done - 1:
            r = 17 + 3 * math.sin(t * 0.25)
            d.ellipse((xx - r, dy - r, xx + r, dy + r), fill=ORANGE + (60,))
            d.ellipse((xx - 12, dy - 12, xx + 12, dy + 12), fill=ORANGE)
        else:
            d.ellipse((xx - 10, dy - 10, xx + 10, dy + 10), fill=(226, 216, 206))
    # input bar
    iy0, iy1 = PY1 - 150, PY1 - 46
    av2 = DUCK.resize((78, int(78 * DUCK.height / DUCK.width)), Image.LANCZOS)
    L.alpha_composite(av2, (PX0 + 40, iy0 + 10))
    d.rounded_rectangle((PX0 + 140, iy0 + 6, PX1 - 150, iy1 - 6), 22, fill=(255, 255, 255, 255), outline=LINE + (255,), width=2)
    d.text((PX0 + 170, iy0 + 34), "Type a message...", font=F["input"], fill=(170, 160, 152))
    mx, my = PX1 - 88, (iy0 + iy1) // 2
    d.ellipse((mx - 44, my - 44, mx + 44, my + 44), fill=ORANGE)
    d.rounded_rectangle((mx - 9, my - 24, mx + 9, my + 6), 9, fill="white")
    d.arc((mx - 18, my - 12, mx + 18, my + 16), 0, 180, fill="white", width=4); d.line((mx, my + 16, mx, my + 24), fill="white", width=4)
    return L


def cursor_img(scale=1.35, pressed=False):
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    s = scale * (0.9 if pressed else 1.0)
    im = Image.new("RGBA", (60, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = [(4 + x * s, 4 + y * s) for x, y in pts]
    d.polygon(P, fill="white", outline="black"); d.line(P + [P[0]], fill="black", width=2)
    return im


def guide(L, a, b, alpha):
    if alpha <= 0: return
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    (x0, y0), (x3, y3) = a, b
    c1, c2 = (x0 - 260, y0 + 20), (x3 + 200, y3 - 10)
    pts = []
    for i in range(61):
        t = i / 60
        x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * c1[0] + 3 * (1 - t) * t * t * c2[0] + t ** 3 * x3
        y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * c1[1] + 3 * (1 - t) * t * t * c2[1] + t ** 3 * y3
        pts.append((x, y))
    d.line(pts, fill=ORANGE + (int(120 * alpha),), width=14, joint="curve")
    glow = g.filter(ImageFilter.GaussianBlur(10))
    d2 = ImageDraw.Draw(glow)
    d2.line(pts, fill=ORANGE + (int(255 * alpha),), width=5, joint="curve")
    L.alpha_composite(glow)


def highlight_ring(L, rect, alpha):
    if alpha <= 0: return
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.rounded_rectangle(rect, 10, outline=ORANGE + (int(255 * alpha),), width=4)
    L.alpha_composite(g.filter(ImageFilter.GaussianBlur(1)))


SPR_U = json.load(open(f"{ROOT}/sprites/sprite_box.json"))["U"]
_SPR = {}
def sprite(kind, idx):
    key = (kind, idx)
    if key not in _SPR:
        n = f"{ROOT}/sprites/{kind}.png" if kind == "happy" else f"{ROOT}/sprites/{kind}_{idx:02d}.png"
        _SPR[key] = Image.open(n).convert("RGBA").crop(SPR_U)
    return _SPR[key]


def pet(L, pos, height, rot=0.0, squash=1.0, flip=False, alpha=1.0, shadow=True, kind="front", idx=0, glow=0.0):
    """Premium on-screen pet: frames rendered from the real 3D Bataa + contact shadow + soft rim glow."""
    if alpha <= 0.01 or height < 4: return
    src = sprite(kind, idx)
    w = int(height * src.width / src.height * (1 / squash) ** 0.5); h = int(height * squash)
    im = src.resize((max(w, 2), max(h, 2)), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = pos
    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dsh = ImageDraw.Draw(sh)
        dsh.ellipse((x - w * 0.34, y - 14, x + w * 0.34, y + 12), fill=(0, 0, 0, int(95 * alpha)))
        dsh.ellipse((x - w * 0.18, y - 7, x + w * 0.18, y + 6), fill=(0, 0, 0, int(120 * alpha)))
        L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    px, py = int(x - im.width / 2), int(y - im.height)
    halo = Image.new("RGBA", im.size, ORANGE + (0,)); halo.putalpha(im.getchannel("A").point(lambda v: int(v * (0.35 + glow) * alpha)))
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0)); big.alpha_composite(halo, (px, py))
    L.alpha_composite(big.filter(ImageFilter.GaussianBlur(14 + 30 * glow)))
    L.alpha_composite(im, (px, py))


def pet_old(L, pos, height, rot=0.0, squash=1.0, flip=False, alpha=1.0, shadow=True):
    if alpha <= 0.01 or height < 4: return
    w = int(height * DUCK.width / DUCK.height * (1 / squash) ** 0.5)
    h = int(height * squash)
    im = DUCK.resize((max(w, 2), max(h, 2)), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im.putalpha(a)
    x, y = pos
    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((x - w * 0.36, y - 12, x + w * 0.36, y + 12), fill=(0, 0, 0, int(110 * alpha)))
        L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    L.alpha_composite(im, (int(x - im.width / 2), int(y - im.height)))


def keycast(L, text, alpha):
    if alpha <= 0: return
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    tw = d.textlength(text, font=F["key"]); cx, cy = 1560, 1215
    d.rounded_rectangle((cx - tw / 2 - 34, cy - 42, cx + tw / 2 + 34, cy + 42), 22, fill=(20, 20, 20, int(215 * alpha)),
                        outline=(255, 255, 255, int(60 * alpha)), width=2)
    d.text((cx - tw / 2, cy - 22), text, font=F["key"], fill=(255, 255, 255, int(255 * alpha)))
    L.alpha_composite(g)


# ---------------------------------------------------------------- the script
PET_HOME = (760, 1215)
PET_NEAR = (1040, 1240)
BUB1 = "Nice start! Click Add, then choose Mesh and Cube. I'll wait here."
BUB2 = "Perfect! That's your lamp base."
BUB3 = "Now... wanna see something cool?"


def frame(t, with_pet=True):
    clicked = t >= 128
    im = (C4 if clicked else C0).copy()
    L = im
    # ---- pet (2D Bataa, lives on the screen)
    if with_pet:
        if t < 16:                                   # just landed back on the screen (from 3D)
            sq = 1 - 0.10 * math.sin(math.pi * t / 16) * (1 - t / 16)
            pet(L, PET_HOME, 230, squash=sq, shadow=t > 3, kind="front", idx=0 if t < 4 else (t // 2) % 24)
        elif t < 132:                                # idle, facing the menu; leans toward it while guiding
            bob = 3 * math.sin(t * 0.18)
            lean = 6 * ss(70, 85, t) * (1 - ss(118, 128, t))
            pet(L, (PET_HOME[0], PET_HOME[1] + bob), 230, rot=-lean, flip=True, kind="idle", idx=(t // 2) % 24)
        elif t < 152:                                # waddles to the new cube
            k = ss(132, 150, t)
            pet(L, lerp(PET_HOME, PET_NEAR, k), 230, flip=True, kind="walk", idx=t % 16)
        elif t < 162:
            pet(L, PET_NEAR, 230, flip=True, kind="happy", squash=1 + 0.05 * math.sin((t - 152) * 0.9))
        elif t < 192:                                # turns to the viewer
            pet(L, PET_NEAR, 230, kind="front", idx=(t // 2) % 24)
        else:                                        # anticipation: squash + glow, then 3D takes over
            k = (t - 192) / 17
            pet(L, PET_NEAR, 230, squash=1 - 0.16 * math.sin(math.pi * k), shadow=t < 203, kind="front", idx=0,
                glow=0.9 * math.sin(math.pi * min(k * 1.2, 1)))
    # ---- menus
    menu_on = 80 <= t < 128
    if menu_on:
        L.alpha_composite(ADD, ADD_POS)
        if t >= 98:
            L.alpha_composite(SUB, SUB_POS)
    # ---- panel (slides in at the start of the loop)
    if t < 26: bub, ch = BUB1, int(len(BUB1) * ss(6, 26, t)) if False else 0
    if t < 128: bub, ch = BUB1, int(len(BUB1) * ss(20, 58, t))
    elif t < 160: bub, ch = BUB2, int(len(BUB2) * ss(134, 150, t))
    else: bub, ch = BUB3, int(len(BUB3) * ss(162, 182, t))
    st = dict(bubble=bub, chars=ch, done_dots=2 if t < 140 else 3,
              stepline="Step 2 of 6" if t < 140 else "Step 3 of 6",
              body="Add a cube to begin the lamp base." if t < 140 else "Great! Next: scale it flat and wide.")
    L.alpha_composite(panel(t, st))
    # ---- guide line + ring
    gl_a = ss(62, 72, t) * (1 - ss(126, 132, t))
    target = OPEN_PT if t < 80 else (MESH_PT if t < 98 else CUBE_PT)
    guide(L, (CARD[0] + 2, CARD[1] + 200), (target[0] + 150, target[1]), gl_a)
    if menu_on:
        if t < 98: highlight_ring(L, (ADD_POS[0] + AB[0] + 6, ADD_POS[1] + MR[0] - 2, ADD_POS[0] + AB[2] - 6, ADD_POS[1] + MR[1] + 2), 1)
        else: highlight_ring(L, (SUB_POS[0] + SB[0] + 6, SUB_POS[1] + CR[0] - 2, SUB_POS[0] + SB[2] - 6, SUB_POS[1] + CR[1] + 2), 1)
    # ---- keycast
    keycast(L, "Shift  +  A", ss(74, 78, t) * (1 - ss(96, 102, t)))
    # ---- cursor path
    P_IDLE = (1500, 1150)
    if t < 40: cp = P_IDLE
    elif t < 76: cp = lerp(P_IDLE, OPEN_PT, ss(40, 74, t))
    elif t < 96: cp = lerp(OPEN_PT, MESH_PT, ss(82, 94, t))
    elif t < 104: cp = lerp(MESH_PT, (MESH_PT[0] + 300, MESH_PT[1]), ss(96, 104, t))
    elif t < 124: cp = lerp((MESH_PT[0] + 300, MESH_PT[1]), CUBE_PT, ss(104, 120, t))
    else: cp = lerp(CUBE_PT, (1500, 1150), ss(140, 175, t)) if t >= 140 else CUBE_PT
    pressed = 124 <= t < 128
    if 124 <= t < 142:                                # click ripple
        k = (t - 124) / 18
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g); r = 18 + 70 * k
        d.ellipse((cp[0] - r, cp[1] - r, cp[0] + r, cp[1] + r), outline=ORANGE + (int(230 * (1 - k)),), width=5)
        L.alpha_composite(g)
    if 128 <= t < 150:                                # sparkle on the new cube
        k = (t - 128) / 22
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        cx, cy = 1205, 1030
        for i in range(10):
            a = i * math.pi / 5; rr = 60 + 170 * k
            x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.6
            s = 10 * (1 - k)
            d.polygon([(x, y - s * 2), (x + s * .6, y), (x, y + s * 2), (x - s * .6, y)], fill=(255, 200, 90, int(255 * (1 - k))))
        L.alpha_composite(g)
    L.alpha_composite(cursor_img(pressed=pressed), (int(cp[0]) - 4, int(cp[1]) - 4))
    return L.convert("RGB").resize((1920, 1080), Image.LANCZOS)


if __name__ == "__main__":
    only = [int(a) for a in sys.argv[1:]]
    frames = only or range(N)
    for t in frames:
        frame(t).save(f"{OUT}/s_{t:04d}.png")
    if not only:
        frame(0, with_pet=False).save(f"{OUT}/screen_start.png")
        frame(N - 1, with_pet=False).save(f"{OUT}/screen_after.png")
    print("2D done", len(list(frames)))
