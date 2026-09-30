"""Headless: import each Sketchfab asset, measure it, render 2 views with the Bataa v2 duck for scale."""
import bpy, glob, json, math, os
from mathutils import Vector

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
OUT = f"{ROOT}/review/sk/render"; os.makedirs(OUT, exist_ok=True)
report = {}
for p in sorted(glob.glob(f"{ROOT}/assets/sketchfab/*/scene.gltf")):
    uid = p.split("/")[-2]
    credit = open(os.path.join(os.path.dirname(p), "CREDIT.txt")).read().split('"')[1][:28]
    tag = f"{uid[:6]}_{credit.replace(' ', '_').replace('/', '')}"
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=p)
    bpy.context.view_layer.update()
    meshes = [o for o in sc.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    mn = Vector([min(q[i] for q in pts) for i in range(3)]); mx = Vector([max(q[i] for q in pts) for i in range(3)])
    size = mx - mn
    # duck for scale: 0.30 m tall, standing at the floor centre
    with bpy.data.libraries.load(f"{ROOT}/assets/bataa_v2.blend") as (src, dst):
        dst.collections = ["Bataa"]
    dc = dst.collections[0]; sc.collection.children.link(dc)
    root = bpy.data.objects.new("DuckRoot", None); sc.collection.objects.link(root)
    for o in dc.objects:
        for m in [m for m in o.modifiers if m.name == "WireView"]: o.modifiers.remove(m)
        if o.parent is None: o.parent = root
    root.scale = (0.3,) * 3
    root.location = ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)
    sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 24
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
    c = (mn + mx) / 2; r = size.length; cam.data.clip_end = r * 20; cam.data.clip_start = r * 0.002
    for vn, d in (("wide", Vector((0.75, -1.0, 0.6))), ("low", Vector((0.3, -1.0, 0.22)))):
        cam.data.lens = 28 if vn == "wide" else 35
        cam.location = c + d.normalized() * r * (0.95 if vn == "wide" else 0.8)
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{OUT}/{tag}_{vn}.png"; bpy.ops.render.render(write_still=True)
    report[tag] = {"size_m": [round(v, 2) for v in size], "tris": sum(len(o.data.polygons) for o in meshes),
                   "objects": len(meshes)}
print("SKR " + json.dumps(report))
