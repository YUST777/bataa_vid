#!/usr/bin/env python3
"""Capture the REAL Blender UI states for the on-screen tutorial (2560x1440 window).
S0 lamp scene | S1 Shift+A menu | S2 Mesh submenu | S3 Cube hovered | S4 cube added as lamp base
"""
import subprocess, sys, time, os, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bx

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
W = subprocess.run(["xdotool", "search", "--class", "blender"], capture_output=True, text=True).stdout.split()[-1]
CAP = f"{ROOT}/ui_caps"


def x(*a):
    subprocess.run(["timeout", "10", "xdotool", *a], check=False)


def shot(name):
    time.sleep(0.9)
    subprocess.run(["timeout", "30", "import", "-window", W, f"{CAP}/{name}.png"], check=True)
    return np.asarray(Image.open(f"{CAP}/{name}.png").convert("RGB")).astype(int)


x("windowactivate", "--sync", W)
x("key", "--window", W, "Escape"); x("key", "--window", W, "Escape")
# fresh tutorial scene
bx.run("import bpy\nfor w in bpy.context.window_manager.windows: w.scene = bpy.data.scenes['Scene']\nRESULT=1")
bx.run(open(f"{ROOT}/scripts/tutorial_scene.py").read())
bx.run(open(f"{ROOT}/scripts/tut_view.py").read())
bx.run("import bpy\nbpy.context.preferences.view.show_tooltips=False\n"
       "[o.select_set(False) for o in bpy.context.scene.objects]\nbpy.context.view_layer.objects.active=None\nRESULT=1")
MX, MY = 1000, 700                      # cursor where the menu opens (window coords)
x("mousemove", "--window", W, str(MX), str(MY))
s0 = shot("S0")
x("key", "--window", W, "shift+a")
s1 = shot("S1")
import cv2
def find_mesh(img):
    tpl = cv2.Canny(cv2.imread(f"{CAP}/tpl_mesh.png", 0), 60, 160)
    e = cv2.Canny(img.astype("uint8")[..., ::-1].copy().mean(2).astype("uint8"), 60, 160)
    r = cv2.matchTemplate(e, tpl, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(r)
    return ml[0] + 20, ml[1] + 13, mv          # label start x, row centre y, score
mx_, my_, score = find_mesh(s1)
menu = [mx_ - 60, my_ - 90, mx_ + 210, my_ + 700]; items = [my_]; mesh_y = my_
x("mousemove", "--window", W, str(mx_ - 10), str(my_))
time.sleep(0.3); x("mousemove", "--window", W, str(mx_ + 20), str(my_))
s2 = shot("S2")
sub = [mx_ + 230, my_ - 15, mx_ + 420, my_ + 320]; cube_y = my_ + 33; sitems = [my_, cube_y]
x("mousemove", "--window", W, str(mx_ + 270), str(my_))
time.sleep(0.35)
x("mousemove", "--window", W, str(mx_ + 290), str(cube_y))
shot("S3")
x("click", "--window", W, "1")
time.sleep(1.0)
# shape the new cube into the lamp base (what the lesson asks for)
bx.run("import bpy\nob=bpy.context.active_object\n[setattr(a.spaces.active,'context','OBJECT') for a in bpy.context.screen.areas if a.type=='PROPERTIES']\nob.name='Lamp_Base'\nob.scale=(0.95,0.95,0.14)\nob.location=(0,0,0.14)\nRESULT=ob.name")
x("mousemove", "--window", W, "1500", "1100")
shot("S4")
json.dump({"menu": menu, "items": items, "sub": sub, "sitems": sitems, "open_at": [MX, MY]},
          open(f"{CAP}/layout.json", "w"))
print(json.dumps({"mesh": [mx_, my_, round(float(score), 3)], "cube_y": cube_y}))
