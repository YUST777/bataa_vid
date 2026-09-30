"""Headless: import the AI duck OBJ, PBR material, audit, render review views."""
import bpy, bmesh, os, sys, math, json
from mathutils import Vector

D = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ai_duck"
OUT = "/home/yousefmsm1/Desktop/blender/bataa_ad/review/ai"
os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=f"{D}/base.obj")
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
ob.name = "AI_Duck"
me = ob.data

# ---- audit
bm = bmesh.new(); bm.from_mesh(me)
nonman = sum(1 for e in bm.edges if not e.is_manifold)
boundary = sum(1 for e in bm.edges if e.is_boundary)
bm.verts.ensure_lookup_table()
# loose parts
parts = 0; seen = set()
for v in bm.verts:
    if v.index in seen: continue
    parts += 1; stack = [v]
    while stack:
        x = stack.pop()
        if x.index in seen: continue
        seen.add(x.index)
        stack.extend(e.other_vert(x) for e in x.link_edges if e.other_vert(x).index not in seen)
bm.free()
bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
mn = Vector([min(c[i] for c in bb) for i in range(3)]); mx = Vector([max(c[i] for c in bb) for i in range(3)])
audit = {"verts": len(me.vertices), "tris": len(me.polygons), "uv_layers": len(me.uv_layers),
         "non_manifold_edges": nonman, "boundary_edges": boundary, "loose_parts": parts,
         "bbox_min": list(mn), "bbox_max": list(mx), "rot": list(ob.rotation_euler)}

# ---- material
m = bpy.data.materials.new("AI_Duck_PBR"); m.use_nodes = True
nt = m.node_tree; p = nt.nodes["Principled BSDF"]
def tex(name, non_color=False):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(f"{D}/{name}.png")
    if non_color: n.image.colorspace_settings.name = 'Non-Color'
    return n
nt.links.new(tex("texture_diffuse").outputs["Color"], p.inputs["Base Color"])
nt.links.new(tex("texture_roughness", True).outputs["Color"], p.inputs["Roughness"])
nt.links.new(tex("texture_metallic", True).outputs["Color"], p.inputs["Metallic"])
nm = nt.nodes.new("ShaderNodeNormalMap")
nt.links.new(tex("texture_normal", True).outputs["Color"], nm.inputs["Color"])
nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
me.materials.clear(); me.materials.append(m)
for poly in me.polygons: poly.use_smooth = True

# ---- normalize: feet on floor, centered, height 1
h = mx.z - mn.z
ob.location -= Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
bpy.context.view_layer.update()
s = 1.0 / h
ob.scale = (s, s, s); ob.location *= s
bpy.context.view_layer.update()

# ---- render setup
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 32
sc.render.resolution_x = sc.render.resolution_y = 700
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.6
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for n, loc, e in [("Key", (2, -2.5, 2.5), 400), ("Rim", (-2, 2, 2), 250)]:
    L = bpy.data.lights.new(n, 'AREA'); L.energy = e; L.size = 2
    lo = bpy.data.objects.new(n, L); sc.collection.objects.link(lo); lo.location = loc
    lo.rotation_euler = (Vector((0, 0, .5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam)
sc.camera = cam; cam.data.lens = 85
d = 3.6
for i, az in enumerate((0, 90, 180, 270)):
    a = math.radians(az)
    cam.location = (math.sin(a) * d, -math.cos(a) * d, 0.9)
    cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}/az{az:03d}.png"
    bpy.ops.render.render(write_still=True)
# clay view for topology read
wf = ob.modifiers.new("W", 'WIREFRAME'); wf.thickness = 0.002; wf.use_replace = False
bpy.ops.wm.save_as_mainfile(filepath="/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ai_duck/ai_duck_raw.blend")
print("AUDIT " + json.dumps(audit))
