"""Headless pass B: swap fixed textures, wing flap setup, blink, review renders.
blender -b --factory-startup -P ai_duck_review.py -- <src.blend> <tag>
"""
import bpy, sys, math, os
from mathutils import Vector

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"; A = f"{ROOT}/assets/ai_duck"; OUT = f"{ROOT}/review/ai"
src, tag = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
ob = bpy.data.objects["AI_Duck"]; rig = bpy.data.objects["Bataa_Rig"]
fixed = tag != "before"
if fixed:
    for n in ob.active_material.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            for k in ("diffuse", "normal"):
                if f"texture_{k}.png" in n.image.filepath:
                    n.image = bpy.data.images.load(f"{A}/texture_{k}_fixed.png")
                    if k == "normal": n.image.colorspace_settings.name = 'Non-Color'
    # wings: strengthen wing influence so a flap reads (rotate about bone local Z = outward swing)
    wing_vg = {s: ob.vertex_groups.get("wing." + s) for s in "LR"}

sc.render.resolution_x = sc.render.resolution_y = 640
pb = rig.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
cam = sc.camera


def shot(name, az, el=1.0, d=3.6, tgt=(0, 0, .5), lens=85):
    a = math.radians(az)
    cam.location = (math.sin(a) * d, -math.cos(a) * d, el); cam.data.lens = lens
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}/{tag}_{name}.png"; bpy.ops.render.render(write_still=True)


def pose(p):
    for b in pb: b.rotation_euler = (0, 0, 0)
    for n, r in p.items(): pb[n].rotation_euler = tuple(math.radians(v) for v in r)
    bpy.context.view_layer.update()

pose({})
shot("back", 180, 1.2); shot("back34", 145, 1.4)
shot("face", 40, 0.95, 1.6, (0, -0.15, 0.78), 85)
if fixed:
    eyes = [o for o in bpy.data.objects if o.name.startswith("Bataa_Eye_")]
    for e in eyes: e.scale.z *= 0.12            # blink
    bpy.context.view_layer.update()
    shot("blink", 40, 0.95, 1.6, (0, -0.15, 0.78), 85)
    for e in eyes: e.scale.z /= 0.12
    pose({"wing.L": (0, 0, -40), "wing.R": (0, 0, 40)}); shot("flapZ", 20, 1.2)
    pose({"wing.L": (40, 0, 0), "wing.R": (40, 0, 0)}); shot("flapX", 20, 1.2)
    pose({"head": (-10, 0, 25), "neck": (8, 0, 0), "body": (0, 6, 0), "leg.R": (30, 0, 0), "foot.R": (-25, 0, 0)})
    shot("action", 35, 1.1)
    bpy.ops.wm.save_as_mainfile(filepath=f"{A}/ai_duck_fixB.blend")
print("DONE", tag)
