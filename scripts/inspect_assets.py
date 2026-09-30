"""Headless: import each downloaded asset, report size/parts, render a thumbnail."""
import bpy, os, sys, json, math, glob
from mathutils import Vector

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
OUT = f"{ROOT}/review/assets"; os.makedirs(OUT, exist_ok=True)
paths = sorted(glob.glob(f"{ROOT}/assets/sketchfab/*/scene.gltf")) + sorted(glob.glob(f"{ROOT}/assets/ph/*/*.gltf"))
report = {}
for p in paths:
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    try:
        bpy.ops.import_scene.gltf(filepath=p)
    except Exception as e:
        report[p] = str(e); continue
    meshes = [o for o in sc.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    mn = Vector([min(q[i] for q in pts) for i in range(3)]); mx = Vector([max(q[i] for q in pts) for i in range(3)])
    size = mx - mn
    name = p.split("/")[-2]
    report[name] = {"meshes": len(meshes), "size_m": [round(v, 3) for v in size],
                    "tris": sum(len(o.data.polygons) for o in meshes),
                    "parts": sorted({o.name.split(".")[0] for o in meshes})[:25]}
    # thumbnail
    sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 16
    sc.render.resolution_x = sc.render.resolution_y = 480; sc.render.film_transparent = True
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
    c = (mn + mx) / 2; r = size.length
    cam.data.lens = 50
    cam.location = c + Vector((0.7, -1.0, 0.55)).normalized() * r * 1.35
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.clip_end = r * 10
    sc.render.filepath = f"{OUT}/{name}.png"; bpy.ops.render.render(write_still=True)
print("ASSETS " + json.dumps(report))
