"""Headless pass A on the rigged AI duck:
 1. find high-frequency ridges on the back half and smooth them (masked Laplacian)
 2. locate the painted eyes via UVs -> add 3D glossy eyes + highlights parented to head
 3. export the smoothed faces' UVs so the texture pass can clean the same area
"""
import bpy, bmesh, math, json
import numpy as np
from mathutils import Vector, Matrix

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
A = f"{ROOT}/assets/ai_duck"
bpy.ops.wm.open_mainfile(filepath=f"{A}/ai_duck_rigged.blend")
ob = bpy.data.objects["AI_Duck"]; rig = bpy.data.objects["Bataa_Rig"]
me = ob.data
nv = len(me.vertices)
co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
ed = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get("vertices", ed); ed = ed.reshape(-1, 2)


def neighbor_mean(p):
    s = np.zeros_like(p); c = np.zeros(nv, np.float32)
    np.add.at(s, ed[:, 0], p[ed[:, 1]]); np.add.at(s, ed[:, 1], p[ed[:, 0]])
    np.add.at(c, ed[:, 0], 1); np.add.at(c, ed[:, 1], 1)
    return s / c[:, None]


def spread(val, it):
    for _ in range(it):
        s = np.zeros(nv, np.float32); c = np.zeros(nv, np.float32)
        np.add.at(s, ed[:, 0], val[ed[:, 1]]); np.add.at(s, ed[:, 1], val[ed[:, 0]])
        np.add.at(c, ed[:, 0], 1); np.add.at(c, ed[:, 1], 1)
        val = 0.5 * val + 0.5 * s / c
    return val

# ---- 1. region mask: tail comb + rear wing ridges (from the review renders)
x, y, z = co.T
def box(v, lo, hi, soft):
    return np.clip((v - lo) / soft, 0, 1) * np.clip((hi - v) / soft, 0, 1)
tail = box(y, 0.16, 1.0, 0.06) * box(z, 0.24, 0.62, 0.05) * box(np.abs(x), -1, 0.26, 0.05)
wing = box(y, -0.02, 1.0, 0.08) * box(z, 0.26, 0.56, 0.05) * box(np.abs(x), 0.17, 1.0, 0.05)
w = np.clip(spread(np.maximum(tail, wing), 10) * 1.6, 0, 1)
stats = {"masked_verts": int((w > 0.2).sum())}
# fill the comb grooves: pull masked verts onto the morphologically closed surface
import json as _json
sd = np.load(f"{A}/closed_sdf.npy"); meta = _json.load(open(f"{A}/occ.json"))
lo = np.array(meta["lo"], np.float32); vs = meta["vs"]
gx, gy, gz = np.gradient(sd)
def samp(field, pts):
    g = (pts - lo) / vs - 0.5
    i0 = np.clip(np.floor(g).astype(int), 0, np.array(field.shape) - 2); f = g - i0
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                wgt = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + wgt * field[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz]
    return out
p = co.copy()
m = w > 0.01
for _ in range(12):
    q = p[m]
    d = samp(sd, q)
    n = np.stack([samp(gx, q), samp(gy, q), samp(gz, q)], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    p[m] = q - n * (d * np.clip(w[m] * 1.5, 0, 1))[:, None]
# membrane fill: comb slats under the tail + wing-rear ridges -> harmonic surface (boundary pinned)
comb = box(y, 0.24, 1.0, 0.03) * box(z, 0.22, 0.47, 0.03) * box(np.abs(x), -1, 0.20, 0.03)
wr = box(y, 0.02, 0.30, 0.04) * box(z, 0.28, 0.54, 0.04) * box(np.abs(x), 0.22, 1.0, 0.03)
EYE_C = np.array([0.1337, -0.1802, 0.7910])
eyezone = np.zeros(nv, np.float32)
for sgn in (1, -1):
    dd = np.linalg.norm(co - EYE_C * np.array([sgn, 1, 1]), axis=1)
    eyezone = np.maximum(eyezone, np.clip((0.075 - dd) / 0.015, 0, 1))
hard = np.clip(spread(np.maximum(np.maximum(comb, wr), eyezone), 3) * 1.4, 0, 1)
for _ in range(350):
    p = p + (neighbor_mean(p) - p) * hard[:, None]
# puff it back out a little so the filled area isn't flatter than its surroundings
nrm = p - neighbor_mean(neighbor_mean(p))
lam, mu = 0.5, -0.53
for _ in range(20):
    p = p + (neighbor_mean(p) - p) * (lam * w[:, None])
    p = p + (neighbor_mean(p) - p) * (mu * w[:, None])
w = np.maximum(w, hard)
me.vertices.foreach_set("co", p.ravel()); me.update()
stats["had_custom_normals"] = bool(me.has_custom_normals)
with bpy.context.temp_override(object=ob, active_object=ob, selected_editable_objects=[ob]):
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
me.update()
stats["max_move"] = float(np.linalg.norm(p - co, axis=1).max())

# ---- export UV faces touched by smoothing (for the texture pass)
uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
np.save(f"{A}/ridge_uv.npy", uv.reshape(-1, 3, 2))            # all tris are triangles
np.save(f"{A}/ridge_w.npy", w[lv].reshape(-1, 3).mean(1))

# ---- 2. eyes from the painted texture
im = bpy.data.images.load(f"{A}/eye_mask.png")
W, H = im.size
px = np.empty(W * H * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(H, W, 4)[..., 0]
u = np.clip((uv[:, 0] * W).astype(int), 0, W - 1); v = np.clip((uv[:, 1] * H).astype(int), 0, H - 1)
eye_loop = px[v, u] > 0.5
eye_v = np.unique(lv[eye_loop])
pts = p[eye_v]
eyes = []
for s in (1, -1):
    sel = pts[(pts[:, 0] * s) > 0]
    c = sel.mean(0)
    # surface normal = direction from the head centre, refined by PCA smallest axis
    q = sel - c; _, sv, vt = np.linalg.svd(q, full_matrices=False)
    n = vt[2]
    hc = np.array([0, -0.13, 0.78])
    if np.dot(n, c - hc) < 0: n = -n
    ext = sv[:2] / math.sqrt(len(sel)) * 2.2                   # ~ half extents
    up_axis = vt[0] if abs(vt[0][2]) > abs(vt[1][2]) else vt[1]
    if up_axis[2] < 0: up_axis = -up_axis
    eyes.append({"c": c.tolist(), "n": n.tolist(), "up": up_axis.tolist(),
                 "half": [float(np.ptp(q @ vt[1]) / 2), float(np.ptp(q @ vt[0]) / 2)]})
mir = lambda a: [-a[0], a[1], a[2]]
avg = lambda a, b: [(a[i] + b[i]) / 2 for i in range(3)]
L, R = eyes
c = avg(L["c"], mir(R["c"])); n = avg(L["n"], mir(R["n"])); up = avg(L["up"], mir(R["up"]))
half = [(L["half"][0] + R["half"][0]) / 2, (L["half"][1] + R["half"][1]) / 2]
eyes = [{"c": c, "n": n, "up": up, "half": half}, {"c": mir(c), "n": mir(n), "up": mir(up), "half": half}]
stats["eyes"] = eyes

black = bpy.data.materials.new("Bataa_EyeGloss"); black.use_nodes = True
bp = black.node_tree.nodes["Principled BSDF"]
bp.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1); bp.inputs["Roughness"].default_value = 0.22
bp.inputs["Coat Weight"].default_value = 0.8; bp.inputs["Coat Roughness"].default_value = 0.03
white = bpy.data.materials.new("Bataa_EyeHi"); white.use_nodes = True
wp = white.node_tree.nodes["Principled BSDF"]
wp.inputs["Base Color"].default_value = (1, 1, 1, 1)
wp.inputs["Emission Color"].default_value = (1, 1, 1, 1); wp.inputs["Emission Strength"].default_value = 2.5

coll = ob.users_collection[0]
for e, sfx in zip(eyes, ("L", "R")):
    c, n, up = Vector(e["c"]), Vector(e["n"]).normalized(), Vector(e["up"])
    side = n.cross(up).normalized(); up = side.cross(n).normalized()
    rot = Matrix((side, n, up)).transposed()                 # local X=side, Y=out, Z=up
    mesh = bpy.data.meshes.new("Bataa_Eye_" + sfx)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0); bm.to_mesh(mesh); bm.free()
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons)); mesh.materials.append(black)
    eo = bpy.data.objects.new(mesh.name, mesh); coll.objects.link(eo)
    hw, hh = e["half"]
    eo.matrix_world = Matrix.Translation(c + n * 0.004) @ rot.to_4x4() @ Matrix.Diagonal((hw * 1.08, 0.018, hh * 1.08, 1))
    m2 = bpy.data.meshes.new("Bataa_EyeHi_" + sfx)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0); bm.to_mesh(m2); bm.free()
    m2.polygons.foreach_set("use_smooth", [True] * len(m2.polygons)); m2.materials.append(white)
    ho = bpy.data.objects.new(m2.name, m2); coll.objects.link(ho)
    fwd = -1 if sfx == "L" else 1
    ho.matrix_world = Matrix.Translation(c + n * 0.021 + up * hh * 0.42 + side * hw * 0.3 * fwd) @ rot.to_4x4() @ Matrix.Diagonal((hw * 0.26, 0.004, hh * 0.22, 1))
    ho.parent = eo; ho.matrix_parent_inverse = eo.matrix_world.inverted()
    bpy.context.view_layer.update()
    mw = eo.matrix_world.copy()
    eo.parent = rig; eo.parent_type = 'BONE'; eo.parent_bone = "head"
    bpy.context.view_layer.update(); eo.matrix_world = mw
    eo["blink_axis_scale"] = hh * 1.08

bpy.ops.wm.save_as_mainfile(filepath=f"{A}/ai_duck_fixA.blend")
print("FIX " + json.dumps(stats))
