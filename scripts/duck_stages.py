"""Headless: build the duck stage by stage, render a review per stage.
blender -b --factory-startup --python-exit-code 1 -P duck_stages.py -- 2 3 4 ...
"""
import bpy, sys, os, math, time
sys.path.append(os.path.dirname(__file__))
import importlib, duck_sdf
from mathutils import Vector

OUT = "/home/yousefmsm1/Desktop/blender/bataa_ad/review/duck_stages"
os.makedirs(OUT, exist_ok=True)
stages = [int(a) for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else [8]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 48
sc.render.resolution_x = sc.render.resolution_y = 900
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = -1.0


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def rig_scene():
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    for n, loc, e, s in [("Key", (2.0, -2.0, 2.5), 450, 2.0), ("Fill", (-2.5, -2.0, 1.0), 120, 3.0),
                         ("Rim", (-1.5, 2.0, 2.0), 250, 1.5)]:
        d = bpy.data.lights.new(n, 'AREA'); d.energy = e; d.size = s
        o = bpy.data.objects.new(n, d); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.lens = 85
    return cam


views = {"ref34": (3.2, -1.3, 1.3), "front": (0, -3.6, 1.0), "back34": (-2.6, 2.6, 1.6), "low": (1.6, -2.8, 0.25)}
for st in stages:
    importlib.reload(duck_sdf)
    clear()
    t = time.time()
    objs = duck_sdf.build(stage=st)
    build_t = time.time() - t
    cam = rig_scene()
    body = objs["body"]
    info = {k: len(v.data.polygons) for k, v in objs.items() if hasattr(v, "data") and hasattr(v.data, "polygons")}
    if st >= 8:
        # pose test: head tilt + wing flap + step, to prove the rig deforms cleanly
        rig = objs["rig"]
        pb = rig.pose.bones
        pb["head"].rotation_mode = 'XYZ'; pb["head"].rotation_euler = (math.radians(-12), 0, math.radians(18))
        pb["wing.L"].rotation_mode = 'XYZ'; pb["wing.L"].rotation_euler = (0, math.radians(-35), 0)
        pb["leg.R"].rotation_mode = 'XYZ'; pb["leg.R"].rotation_euler = (math.radians(25), 0, 0)
        pb["body"].rotation_mode = 'XYZ'; pb["body"].rotation_euler = (0, math.radians(6), 0)
    for n, p in views.items():
        cam.location = p
        cam.rotation_euler = (Vector((0, 0, 0.55)) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{OUT}/s{st}_{n}.png"
        bpy.ops.render.render(write_still=True)
    print(f"STAGE {st} build {build_t:.1f}s polys {info}")
    if st >= 8:
        bpy.ops.wm.save_as_mainfile(filepath="/home/yousefmsm1/Desktop/blender/bataa_ad/assets/bataa_duck.blend")
print("DONE")
