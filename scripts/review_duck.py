"""Headless: build duck, render 3 review views. blender -b --factory-startup -P review_duck.py"""
import bpy, sys, math, os
sys.path.append(os.path.dirname(__file__))
import importlib, bataa_duck
importlib.reload(bataa_duck)
from mathutils import Vector

OUT = "/home/yousefmsm1/Desktop/blender/bataa_ad/review"
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
sc = bpy.context.scene
root = bataa_duck.build_bataa()

sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 32
sc.render.resolution_x = sc.render.resolution_y = 700
sc.view_settings.view_transform = 'Standard'; sc.render.film_transparent = True
sc.view_settings.look = 'None'; sc.view_settings.exposure = -1.1
w = sc.world or bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35

def light(name, loc, energy, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.size = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0.5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
light("Key", (2.0, -2.0, 2.5), 450, 2.0)
light("Fill", (-2.5, -2.0, 1.0), 120, 3.0)
light("Rim", (-1.5, 2.0, 2.0), 250, 1.5)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
sc.camera = cam; cam.data.lens = 85
views = {"ref34": (3.2, -1.3, 1.3), "front": (0, -3.6, 1.0), "back34": (-2.6, 2.6, 1.6)}
for n, p in views.items():
    cam.location = p
    cam.rotation_euler = (Vector((0, 0, 0.55)) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}/duck_{n}.png"
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath="/home/yousefmsm1/Desktop/blender/bataa_ad/assets/bataa_duck.blend")
print("DONE")
