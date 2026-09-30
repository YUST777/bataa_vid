#!/usr/bin/env python3
"""Cut the REAL Blender menus out of internal screenshots as RGBA layers (2560x1440 space).
Body = opaque rounded rect; shadow = measured darkening. Highlight moved Curve->Mesh and Plane->Cube."""
import json
import numpy as np
from PIL import Image, ImageDraw

C = "/home/yousefmsm1/Desktop/blender/bataa_ad/ui_caps/"
A = lambda n: np.asarray(Image.open(C + n).convert("RGB")).astype(np.float32)
I0, I1, I2 = A("I0.png"), A("I1.png"), A("I2.png")
MBG = np.array([24, 24, 24], np.float32)


def cut(img, base, x0, x1, pad=14, extra=0):
    d = np.abs(img - base).max(2); d[:, :x0] = 0; d[:, x1:] = 0
    # body: pixels that equal the menu background colour exactly-ish and differ from base
    body = (np.abs(img - MBG).max(2) < 3) & (d > 3)
    ys, xs = np.nonzero(body)
    # robust extents: rows/cols with many body pixels
    cols = np.nonzero(body.sum(0) > 40)[0]; rows = np.nonzero(body.sum(1) > 40)[0]
    bx0, bx1, by0, by1 = cols.min() + 1, cols.max() - 2, rows.min(), min(rows.max() + 1 + extra, img.shape[0] - pad)
    txt = np.nonzero((img[by0:, bx0 + 20:bx1 - 20].max(2) > 150).any(1))[0]
    by1 = max(by1, min(by0 + txt.max() + 15, img.shape[0] - 2))
    X0, Y0, X1, Y1 = bx0 - pad, by0 - pad, bx1 + pad, min(by1 + pad, img.shape[0])
    crop = img[Y0:Y1, X0:X1].copy(); bs = base[Y0:Y1, X0:X1]
    m = Image.new("L", (X1 - X0, Y1 - Y0), 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + bx1 - bx0 - 1, pad + by1 - by0 - 1), 9, fill=255)
    m = np.asarray(m).astype(np.float32) / 255
    lum_i, lum_b = crop.mean(2), np.maximum(bs.mean(2), 1)
    shadow = np.clip(1 - lum_i / lum_b, 0, 0.35) * (m < 0.5) * (lum_b < 75)
    shadow = np.minimum(shadow, np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(__import__('PIL.ImageFilter').ImageFilter.GaussianBlur(6)), np.float32)/255*0.5)
    rgb = crop * m[..., None]                      # shadow pixels are black
    alpha = np.maximum(m, shadow)
    return rgb, alpha, (X0, Y0), (bx0 - X0, by0 - Y0, bx1 - X0, by1 - Y0)


def rows_highlight(rgb, body, hl_ref):
    x0, y0, x1, y1 = body
    band = rgb[y0:y1, x0 + 12:x1 - 12]
    frac = (np.abs(band - hl_ref).max(2) < 8).mean(1)
    idx = np.nonzero(frac > 0.5)[0]
    return y0 + idx.min(), y0 + idx.max() + 1


def swap(rgb, y0, y1, x0, x1, old, new):
    seg = rgb[y0:y1, x0:x1]
    lum = seg.mean(2, keepdims=True)
    t = np.clip((lum - old.mean()) / (225 - old.mean()), 0, 1)
    text = np.where(t > 0, (seg - (1 - t) * old) / np.maximum(t, 1e-3), seg)
    seg[:] = np.clip(t * text + (1 - t) * new, 0, 255)


def rounded_hl(rgb, y0, y1, x0, x1, col):
    seg = rgb[y0:y1, x0:x1]
    m = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), 7, fill=255)
    m = np.asarray(m, np.float32)[..., None] / 255
    lum = seg.mean(2, keepdims=True)
    t = np.clip((lum - MBG.mean()) / (225 - MBG.mean()), 0, 1)        # text coverage
    text = np.where(t > 0, (seg - (1 - t) * MBG) / np.maximum(t, 1e-3), seg)
    newbg = MBG * (1 - m) + col * m
    seg[:] = np.clip(t * text + (1 - t) * newbg, 0, 255)


def save(rgb, a, name):
    Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA").save(C + name)


out = {}
# ---- Add menu from I2 (Curve highlighted); exclude its Curve submenu (x > 1500)
rgb, a, org, body = cut(I2, I0, 1100, 1500, extra=0)
x0, y0, x1, y1 = body
# highlight reference colour: sample the highlighted row centre
probe = rgb[y0:y1, x0 + 40:x0 + 60].reshape(-1, 3)
vals, cnt = np.unique(probe.astype(int), axis=0, return_counts=True)
cands = [(c, v) for v, c in zip(vals, cnt) if 40 < v.mean() < 110]
HL = np.array(max(cands, key=lambda t: t[0])[1], np.float32)
cy0, cy1 = rows_highlight(rgb, body, HL)
pitch = 32
hx0, hx1 = x0 + 4, x1 - 4
swap(rgb, cy0, cy1, hx0, hx1, HL, MBG)                      # un-highlight Curve
rounded_hl(rgb, cy0 - pitch, cy1 - pitch, hx0, hx1, HL)     # highlight Mesh
save(rgb, a, "add_menu.png")
out["add"] = {"origin": list(map(int, org)), "body": list(map(int, body)), "mesh_row": [int(cy0 - pitch), int(cy1 - pitch)],
              "hl": HL.tolist()}

# ---- Mesh popup from I1 (Plane highlighted) -> submenu: drop title row, move highlight to Cube
rgb, a, org, body = cut(I1, I0, 1100, 1700, extra=0)
x0, y0, x1, y1 = body
py0, py1 = rows_highlight(rgb, body, HL)
swap(rgb, py0, py1, x0 + 4, x1 - 4, HL, MBG)
rounded_hl(rgb, py0 + pitch, py1 + pitch, x0 + 4, x1 - 4, HL)
top_keep = y0 + 6                                     # rounded top edge rows
drop0, drop1 = top_keep, py0 - 6                      # title + separator
rgb = np.concatenate([rgb[:top_keep], rgb[drop1:]], 0)
a = np.concatenate([a[:top_keep], a[drop1:]], 0)
shift = drop1 - drop0
save(rgb, a, "mesh_sub.png")
out["sub"] = {"body": [int(x0), int(y0), int(x1), int(y1 - shift)], "plane_row": [int(py0 - shift), int(py1 - shift)],
              "cube_row": [int(py0 - shift + pitch), int(py1 - shift + pitch)]}
json.dump(out, open(C + "menus.json", "w"), indent=1)
print(json.dumps(out))

prev = Image.new("RGB", (1000, 900), (61, 61, 61))
m1 = Image.open(C + "add_menu.png"); m2 = Image.open(C + "mesh_sub.png")
prev.paste(m1, (10, 10), m1)
sx = 10 + out["add"]["body"][2] - out["sub"]["body"][0] - 2
sy = 10 + out["add"]["mesh_row"][0] - out["sub"]["plane_row"][0]
prev.paste(m2, (sx, sy), m2)
prev.save("/home/yousefmsm1/Desktop/blender/bataa_ad/review/menus_b.png")
