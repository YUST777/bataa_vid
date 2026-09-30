"""Headless: build Bataa from scratch as clean quad parts, using the Hyper3D mesh only as a shape reference.

Each part = all-quad cage (quad sphere / cylinder) projected onto the matching region of the reference,
relaxed for even edge flow, then Subdivision Surface (live modifier, fully editable).
Parts: Head, Body, Beak_Upper, Beak_Lower, Leg_L/R, Foot_L/R, Eye_L/R (+highlights). Own materials.
"""
import bpy, bmesh, math, json, os
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
A = f"{ROOT}/assets/ai_duck"
OUT = f"{ROOT}/review/v2"
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------ reference
bpy.ops.wm.open_mainfile(filepath=f"{A}/ai_duck_fixB.blend")
ref = bpy.data.objects["AI_Duck"]
rme = ref.data
co = np.empty(len(rme.vertices) * 3, np.float32); rme.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
tri = np.empty(len(rme.polygons) * 3, np.int32); rme.polygons.foreach_get("vertices", tri); tri = tri.reshape(-1, 3)
# per-vertex colour from the diffuse texture -> orange vs cream
img = bpy.data.images.load(f"{A}/texture_diffuse.png")
W, H = img.size
px = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(H, W, 4)
uv = np.empty(len(rme.loops) * 2, np.float32); rme.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
lv = np.empty(len(rme.loops), np.int32); rme.loops.foreach_get("vertex_index", lv)
col = np.zeros((len(co), 3), np.float32); cnt = np.zeros(len(co), np.float32)
lc = px[np.clip((uv[:, 1] * H).astype(int), 0, H - 1), np.clip((uv[:, 0] * W).astype(int), 0, W - 1), :3]
np.add.at(col, lv, lc); np.add.at(cnt, lv, 1); col /= cnt[:, None]
orange = (col[:, 0] - col[:, 2]) > 0.35
x, y, z = co.T
cream_rgb = np.median(col[~orange & (z > 0.3)], 0); orange_rgb = np.median(col[orange], 0)

# neck = narrowest slice
best = None
for zz in np.arange(0.5, 0.75, 0.005):
    s = (z > zz) & (z < zz + 0.006) & ~orange
    if s.sum() > 30:
        w = np.ptp(x[s]); best = (zz, w) if best is None or w < best[1] else best
NECK = best[0]
beak = orange & (z > 0.55)
# mouth gap: emptiest z bin inside the beak's central band
bz = z[beak & (np.abs(x) < 0.05) & (y < -0.33)]
hist, edges = np.histogram(bz, bins=30)
inner = slice(8, 22)
MOUTH = edges[inner][np.argmin(hist[inner])] + (edges[1] - edges[0]) / 2

regions = {
    "Head": (~orange) & (z >= NECK - 0.03),
    "Body": (~orange) & (z < NECK + 0.03) & (z > 0.10),
    "Beak": beak,
}
for s, sfx in ((1, "L"), (-1, "R")):
    side = orange & (z < 0.45) & (x * s > 0)
    regions["Leg_" + sfx] = side & (z > 0.07)
    regions["Foot_" + sfx] = side & (z <= 0.09)


def bvh_for(mask):
    fm = mask[tri].all(1)
    t = tri[fm]
    used = np.unique(t)
    remap = -np.ones(len(co), np.int64); remap[used] = np.arange(len(used))
    return BVHTree.FromPolygons([tuple(v) for v in co[used].tolist()], (remap[t]).tolist(), all_triangles=True), co[used]


# ------------------------------------------------------------ new file for the clean duck
bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
coll = bpy.data.collections.new("Bataa"); sc.collection.children.link(coll)


def lin(c):
    return tuple(float(v) for v in c) + (1.0,)


def material(name, rgb, rough, sss=0.0, coat=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = rgb
    p.inputs["Roughness"].default_value = rough
    p.inputs["Subsurface Weight"].default_value = sss
    p.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.4)
    p.inputs["Subsurface Scale"].default_value = 0.03
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = 0.04
    if emit:
        p.inputs["Emission Color"].default_value = rgb; p.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = rgb
    return m

def hexlin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)
M_CREAM = material("Bataa_Cream", lin(cream_rgb), 0.5, sss=0.2)
M_ORANGE = material("Bataa_Orange", hexlin("#FF5A00"), 0.35, coat=0.25)
M_EYE = material("Bataa_Eye", (0.004, 0.004, 0.005, 1), 0.2, coat=0.8)
M_HI = material("Bataa_EyeHi", (1, 1, 1, 1), 0.3, emit=2.5)


def quad_sphere(cuts):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized()
    return bm


def cylinder(segs, rings, a, b, r):
    bm = bmesh.new()
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized(); u = ax.orthogonal().normalized(); v = ax.cross(u)
    rows = []
    for i in range(rings + 1):
        c = a.lerp(b, i / rings)
        rows.append([bm.verts.new(c + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * r)
                     for k in range(segs)])
    for i in range(rings):
        for k in range(segs):
            bm.faces.new((rows[i][k], rows[i][(k + 1) % segs], rows[i + 1][(k + 1) % segs], rows[i + 1][k]))
    for row in (rows[0], rows[-1]):
        bm.faces.new(row if row is rows[-1] else row[::-1])
    return bm


def relax(bm, tree, it=4, lam=0.45):
    for _ in range(it):
        new = {}
        for v in bm.verts:
            nb = [e.other_vert(v).co for e in v.link_edges]
            avg = sum(nb, Vector()) / len(nb)
            new[v] = v.co.lerp(avg, lam)
        for v, c in new.items():
            hit = tree.find_nearest(c)
            v.co = hit[0] if hit[0] is not None else c


def project_star(bm, tree, center, fallback_scale=0.85, nearest=False, push=None):
    center = Vector(center); dists = []; miss = []
    for v in bm.verts:
        d = v.co.normalized()
        hit = tree.ray_cast(center, d)
        if hit[0] is not None:
            v.co = hit[0]; dists.append(hit[3])
        else:
            miss.append((v, d))
    med = float(np.median(dists)) if dists else 0.1
    for v, d in miss:
        if nearest:
            v.co = tree.find_nearest(center + d * med)[0] + (Vector(push) if push else Vector())
        else:
            v.co = center + d * med * fallback_scale
    return len(miss)


def to_object(name, bm, mat, levels=2, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if levels:
        s = ob.modifiers.new("Subdivision", 'SUBSURF'); s.levels = levels; s.render_levels = levels
    return ob


report = {"neck": float(NECK), "mouth": float(MOUTH)}
parts = {}
spec = {"Head": (14, M_CREAM), "Body": (14, M_CREAM), "Beak": (10, M_ORANGE),
        "Foot_L": (8, M_ORANGE), "Foot_R": (8, M_ORANGE)}
for name, (cuts, mat) in spec.items():
    tree, pts = bvh_for(regions[name])
    c = pts.mean(0)
    if name == "Head":
        c = np.array([c[0], c[1] + 0.01, max(c[2], NECK + 0.17)])
    if name == "Body":
        c = np.array([0.0, c[1], (pts[:, 2].min() + NECK) / 2])
    if name.startswith("Foot"):
        c[2] = 0.035
    bm = quad_sphere(cuts)
    for v in bm.verts:
        v.co = Vector(c) + v.co * 0.02
    # direction from the centre; initial cage is a tiny sphere at the centre
    for v in bm.verts:
        v.co = (v.co - Vector(c)).normalized()
    if name == "Beak":
        missed = project_star(bm, tree, c, nearest=True, push=(0, 0.05, 0))
        relax(bm, tree, it=2, lam=0.3)
    else:
        missed = project_star(bm, tree, c)
        relax(bm, tree, it=5)
    parts[name] = to_object(name, bm, mat, levels=2)
    report[name] = {"cage_faces": len(parts[name].data.polygons), "missed_rays": missed}

# legs: cylinders along the leg region's axis, radius from the reference
for sfx in ("L", "R"):
    pts = co[regions["Leg_" + sfx]]
    fc = co[regions["Foot_" + sfx]].mean(0)
    core = pts[(pts[:, 2] > 0.1) & (pts[:, 2] < 0.2)]
    cx, cy = np.median(core[:, 0]), np.median(core[:, 1])
    bot = np.array([cx, cy - 0.005, 0.05]); top = np.array([cx, cy + 0.015, 0.30])
    r = float(np.median(np.hypot(core[:, 0] - cx, core[:, 1] - cy)))
    bm = cylinder(12, 6, bot, top, r)
    parts["Leg_" + sfx] = to_object("Leg_" + sfx, bm, M_ORANGE, levels=2)
    report["Leg_" + sfx] = {"radius": r}

# eyes: glossy pills placed on the new head, positions measured from the reference's painted eyes
EYE = {"c": (0.13366, -0.18018, 0.79095), "n": (0.72883, -0.65798, 0.10649), "up": (0.10212, 0.28291, 0.94902),
       "half": (0.0348, 0.0443)}
htree = BVHTree.FromObject(parts["Head"], bpy.context.evaluated_depsgraph_get())
for s, sfx in ((1, "L"), (-1, "R")):
    c = Vector((EYE["c"][0] * s, EYE["c"][1], EYE["c"][2])); n = Vector((EYE["n"][0] * s, EYE["n"][1], EYE["n"][2])).normalized()
    hit = htree.ray_cast(c + n * 0.1, -n)
    if hit[0] is not None:
        c = hit[0]
    up = Vector((EYE["up"][0] * s, EYE["up"][1], EYE["up"][2]))
    side = n.cross(up).normalized(); up = side.cross(n).normalized()
    rot = Matrix((side, n, up)).transposed().to_4x4()
    hw, hh = EYE["half"]
    eye = to_object("Eye_" + sfx, quad_sphere(4), M_EYE, levels=2)
    eye.matrix_world = Matrix.Translation(c) @ rot @ Matrix.Diagonal((hw * 1.1, 0.02, hh * 1.1, 1))
    hi = to_object("EyeHi_" + sfx, quad_sphere(2), M_HI, levels=1)
    fwd = -1 if s > 0 else 1
    hi.matrix_world = Matrix.Translation(c + n * 0.018 + up * hh * 0.42 + side * hw * 0.3 * fwd) @ rot @ Matrix.Diagonal((hw * 0.26, 0.004, hh * 0.22, 1))
    hi.parent = eye; hi.matrix_parent_inverse = eye.matrix_world.inverted()
    parts["Eye_" + sfx] = eye

bpy.ops.wm.save_as_mainfile(filepath=f"{ROOT}/assets/bataa_v2.blend")

# ------------------------------------------------------------ review renders (+ wire overlay pass)
sc.render.engine = 'BLENDER_EEVEE'; sc.eevee.taa_render_samples = 32
sc.render.resolution_x = sc.render.resolution_y = 640; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = -0.6
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for n, loc, e in [("Key", (2, -2.5, 2.5), 400), ("Rim", (-2, 2, 2), 250), ("Fill", (-2.5, -1.5, 1), 100)]:
    L = bpy.data.lights.new(n, 'AREA'); L.energy = e; L.size = 2
    lo = bpy.data.objects.new(n, L); sc.collection.objects.link(lo); lo.location = loc
    lo.rotation_euler = (Vector((0, 0, .5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85
for az in (0, 40, 90, 180):
    a = math.radians(az)
    cam.location = (math.sin(a) * 3.6, -math.cos(a) * 3.6, 1.0)
    cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}/v2_az{az:03d}.png"; bpy.ops.render.render(write_still=True)
# wire view: show the cage topology
wm = material("Wire", (0.05, 0.05, 0.05, 1), 0.5)
for ob in [o for o in coll.objects if o.type == 'MESH']:
    mod = ob.modifiers.new("WireView", 'WIREFRAME'); mod.thickness = 0.0025; mod.use_replace = False
    mod.material_offset = len(ob.data.materials); ob.data.materials.append(wm)
    ob.modifiers.move(len(ob.modifiers) - 1, 0)
a = math.radians(40); cam.location = (math.sin(a) * 3.6, -math.cos(a) * 3.6, 1.0)
cam.rotation_euler = (Vector((0, 0, .5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = f"{OUT}/v2_wire.png"; bpy.ops.render.render(write_still=True)
print("V2 " + json.dumps(report))
