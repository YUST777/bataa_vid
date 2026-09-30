#!/usr/bin/env python3
"""Build a step in live Blender, screenshot the viewport, add the step label.
python3 step.py N [wait_seconds]
"""
import json, subprocess, sys, time, os
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bx

LABELS = {1: "Block out", 2: "Guides", 3: "Signed-distance field", 4: "Legs & feet", 5: "Webbing",
          6: "Refine", 7: "Surface", 8: "Final mesh", 9: "Feathers", 10: "Eyes", 11: "Textures",
          12: "Rig", 13: "Render"}
ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
WIN = "67108866"
step = int(sys.argv[1])
wait = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0

code = f"""
import sys, importlib
sys.path.insert(0, '{ROOT}/scripts')
import duck_sdf, bataa_build
importlib.reload(duck_sdf); importlib.reload(bataa_build)
RESULT = bataa_build.show({step})
"""
out = bx.run(code)
res = out.get("result", out)
text = res.get("result", "") if isinstance(res, dict) else str(res)
if "<<RESULT>>" not in str(text):
    print(json.dumps(out, indent=1)[-3000:]); sys.exit(1)
info = json.loads(text.split("<<RESULT>>", 1)[1].strip())
time.sleep(wait)
raw = f"{ROOT}/review/steps/raw_{step:02d}.png"
os.makedirs(os.path.dirname(raw), exist_ok=True)
subprocess.run(["import", "-window", WIN, raw], check=True, timeout=60)
im = Image.open(raw).convert("RGB")
r = info["region"]
if step < 12:   # clean viewport crop, like the reference steps
    top = r["win_h"] - (r["y"] + r["h"])
    m = 30
    im = im.crop((r["x"] + m, top + m, r["x"] + r["w"] - m, top + r["h"] - m))
W = 1920
im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
d = ImageDraw.Draw(im)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 64)
fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
ly = im.height - 120 if step < 12 else int(im.height * 0.80)
lx = 52 if step < 12 else 130
d.text((lx, ly), f"{step}. {LABELS[step]}", fill=(255, 120, 30), font=f)
bx0 = im.width - 300 if step < 12 else int(im.width * 0.80) - 300
by0 = 36 if step < 12 else 150
d.rounded_rectangle((bx0, by0, bx0 + 256, by0 + 64), 14, fill=(255, 90, 0))
d.text((bx0 + 38, by0 + 8), "bataa", fill=(255, 255, 255), font=fb)
dst = f"{ROOT}/review/steps/step_{step:02d}.png"
im.save(dst)
im.resize((960, int(im.height * 960 / im.width))).save(dst.replace(".png", "_sm.png"))
info.pop("region", None)
print(json.dumps(info), dst)
