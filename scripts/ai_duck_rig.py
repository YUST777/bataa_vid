"""Headless: rig the AI duck from measured landmarks, auto weights, pose test renders."""
import bpy, math, json, os
import numpy as np
from mathutils import Vector

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
OUT = f"{ROOT}/review/ai"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/assets/ai_duck/ai_duck_raw.blend")
sc = bpy.context.scene
ob = bpy.data.objects["AI_Duck"]
ob.modifiers.clear()
# bake the normalize transform into the mesh
with bpy.context.temp_override(active_object=ob, selected_editable_objects=[ob], object=ob):
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = ob.data
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
x, y, z = co.T

# ---- landmarks
def cen(mask): return co[mask].mean(0)
lm = {}
lm["footL"] = cen((z < 0.06) & (x > 0)); lm["footR"] = cen((z < 0.06) & (x < 0))
lm["hipL"] = cen((z > 0.14) & (z < 0.20) & (x > 0.03) & (np.abs(x) < 0.3)); lm["hipR"] = cen((z > 0.14) & (z < 0.20) & (x < -0.03) & (np.abs(x) < 0.3))
head = z > 0.62
lm["head"] = cen(head); lm["head_top"] = co[head][np.argmax(co[head][:, 2])]
lm["beak_tip"] = co[np.argmin(y)]
body = (z > 0.2) & (z < 0.55)
lm["body"] = cen(body)
lm["tail_tip"] = co[np.argmax(y)]
# neck = narrowest xy slice between body and head
best = None
for zz in np.arange(0.45, 0.75, 0.01):
    s = (z > zz) & (z < zz + 0.01)
    if s.sum() < 20: continue
    w = np.ptp(x[s])
    if best is None or w < best[1]: best = (zz, w)
lm["neck_z"] = best[0]
wing = (np.abs(x) > 0.24) & (z > 0.25) & (z < 0.55)
lm["wingL"] = cen(wing & (x > 0)); lm["wingR"] = cen(wing & (x < 0))

# ---- armature
arm_d = bpy.data.armatures.new("Bataa_Rig"); rig = bpy.data.objects.new("Bataa_Rig", arm_d)
sc.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[rig]):
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_d.edit_bones
    def bone(n, h, t, p=None, deform=True):
        b = eb.new(n); b.head = Vector(h); b.tail = Vector(t); b.use_deform = deform
        if p: b.parent = eb[p]
        return b
    nz = lm["neck_z"]; bc = lm["body"]; hc = lm["head"]
    bone("root", (0, 0, 0), (0, 0.3, 0), deform=False)
    bone("body", (0, bc[1], 0.2), (0, bc[1] - 0.02, nz), "root")
    bone("neck", (0, bc[1] - 0.02, nz), (0, hc[1], nz + 0.08), "body")
    bone("head", (0, hc[1], nz + 0.08), (0, hc[1], lm["head_top"][2]), "neck")
    bone("beak", (0, hc[1] - 0.12, hc[2] - 0.03), (0, lm["beak_tip"][1], lm["beak_tip"][2]), "head")
    tt = lm["tail_tip"]
    bone("tail", (0, bc[1] + 0.18, 0.42), (0, tt[1], tt[2]), "body")
    for s, sfx in ((1, "L"), (-1, "R")):
        wc = lm["wing" + sfx]
        bone("wing." + sfx, (s * 0.2, wc[1] - 0.12, wc[2] + 0.04), (s * (abs(wc[0]) + 0.03), wc[1] + 0.2, wc[2] + 0.02), "body")
        hp, ft = lm["hip" + sfx], lm["foot" + sfx]
        bone("leg." + sfx, (hp[0], hp[1], 0.24), (ft[0], ft[1] + 0.02, 0.06), "root")
        bone("foot." + sfx, (ft[0], ft[1] + 0.02, 0.06), (ft[0], ft[1] - 0.12, 0.02), "leg." + sfx)
    bpy.ops.object.mode_set(mode='OBJECT')

# ---- auto weights
for o in sc.objects: o.select_set(False)
ob.select_set(True); rig.select_set(True)
bpy.context.view_layer.objects.active = rig
with bpy.context.temp_override(active_object=rig, selected_objects=[ob, rig], selected_editable_objects=[ob, rig], object=rig):
    r = bpy.ops.object.parent_set(type='ARMATURE_AUTO')
vg = {g.name: 0 for g in ob.vertex_groups}
for v in me.vertices:
    for g in v.groups:
        if g.weight > 0.01: vg[ob.vertex_groups[g.group].name] += 1
unweighted = sum(1 for v in me.vertices if not any(g.weight > 0.01 for g in v.groups))

# ---- pose test
pb = rig.pose.bones
for b in pb: b.rotation_mode = 'XYZ'
def pose(p):
    for b in pb: b.rotation_euler = (0, 0, 0)
    for n, r in p.items(): pb[n].rotation_euler = tuple(math.radians(a) for a in r)
    bpy.context.view_layer.update()
cam = sc.camera
poses = {"rest": {}, "action": {"head": (-15, 0, 30), "neck": (10, 0, 0), "wing.L": (0, -50, 0), "wing.R": (0, 20, 0),
                                  "leg.R": (35, 0, 0), "foot.R": (-30, 0, 0), "tail": (0, 0, 25), "body": (0, 8, 0)}}
sc.render.resolution_x = sc.render.resolution_y = 700
for pn, p in poses.items():
    pose(p)
    for az in (35, 150):
        a = math.radians(az); cam.location = (math.sin(a) * 3.6, -math.cos(a) * 3.6, 1.1)
        cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{OUT}/pose_{pn}_{az}.png"; bpy.ops.render.render(write_still=True)
pose({})
bpy.ops.wm.save_as_mainfile(filepath=f"{ROOT}/assets/ai_duck/ai_duck_rigged.blend")
print("RIG " + json.dumps({"parent_set": list(r), "groups": vg, "unweighted": unweighted,
                           "lm": {k: (list(map(float, v)) if hasattr(v, '__len__') else float(v)) for k, v in lm.items()}}))
