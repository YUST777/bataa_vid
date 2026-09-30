"""Bataa duck, production pass: SDF-sculpted, OpenVDB-meshed, rigged.

Units: duck height = 1.0 (scale the root afterwards). Forward = -Y, up = +Z.
Public API:
    build(stage=99, coll=None) -> dict of objects (stage limits how far we go)
Stages: 2 body+head SDF, 3 wings+tail feathers, 4 beak, 5 legs+webbed feet,
        6 eyes, 7 materials/surface, 8 rig.
"""
import bpy, bmesh, math
import numpy as np
import openvdb
from mathutils import Vector

VS = 0.0045          # voxel size for the body
VS_FINE = 0.0028     # voxel size for beak / feet


# ----------------------------------------------------------------- SDF helpers
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def ssub(a, b, k):  # a minus b
    h = np.clip(0.5 - 0.5 * (a + b) / k, 0.0, 1.0)
    return a + (-b - a) * h + k * h * (1.0 - h)


def rot_x(y, z, ang):
    c, s = math.cos(ang), math.sin(ang)
    return c * y + s * z, -s * y + c * z


def rot_z(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return c * x + s * y, -s * x + c * y


def ell(x, y, z, r):
    """IQ's ellipsoid bound, x,y,z already in local space."""
    k0 = np.sqrt((x / r[0]) ** 2 + (y / r[1]) ** 2 + (z / r[2]) ** 2)
    k1 = np.sqrt((x / r[0] ** 2) ** 2 + (y / r[1] ** 2) ** 2 + (z / r[2] ** 2) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def rbox(x, y, z, b, r):
    qx, qy, qz = np.abs(x) - b[0], np.abs(y) - b[1], np.abs(z) - b[2]
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    ins = np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0)
    return out + ins - r


def capsule(x, y, z, a, b, ra, rb):
    a, b = np.array(a), np.array(b)
    ba = b - a
    px, py, pz = x - a[0], y - a[1], z - a[2]
    h = np.clip((px * ba[0] + py * ba[1] + pz * ba[2]) / ba.dot(ba), 0, 1)
    d = np.sqrt((px - ba[0] * h) ** 2 + (py - ba[1] * h) ** 2 + (pz - ba[2] * h) ** 2)
    return d - (ra + (rb - ra) * h)


# ----------------------------------------------------------------- duck fields
HEAD_C = (0.0, -0.06, 0.80)
HEAD_R = (0.238, 0.232, 0.222)


def f_body_core(x, y, z):
    body = ell(x, y - 0.03, z - 0.40, (0.31, 0.35, 0.255))
    belly = ell(x, y + 0.03, z - 0.33, (0.285, 0.29, 0.21))       # fuller low front
    rump = ell(x, y - 0.17, z - 0.43, (0.25, 0.22, 0.20))
    d = smin(body, belly, 0.08)
    return smin(d, rump, 0.08)


def f_head(x, y, z):
    hx, hy, hz = x - HEAD_C[0], y - HEAD_C[1], z - HEAD_C[2]
    head = ell(hx, hy, hz, HEAD_R)
    cheeks = ell(np.abs(hx) - 0.085, hy + 0.10, hz + 0.06, (0.12, 0.10, 0.10))
    head = smin(head, cheeks, 0.06)
    # tuft: curved tapered chain on top, sweeping back
    tuft = None
    for i in range(7):
        t = i / 6
        cy = -0.05 + 0.17 * t
        cz = 0.995 + 0.05 * math.sin(t * math.pi * 0.9) - 0.03 * t
        r = 0.052 - 0.022 * t
        s = np.sqrt(x ** 2 * 1.5 + (y - cy) ** 2 + (z - cz) ** 2) - r
        tuft = s if tuft is None else smin(tuft, s, 0.02)
    return smin(head, tuft, 0.035)


def f_wing(x, y, z, side):
    # local frame of the wing pad
    lx, ly, lz = x - side * 0.262, y - 0.085, z - 0.455
    lx, ly = rot_z(lx, ly, side * math.radians(-7))
    ly, lz = rot_x(ly, lz, math.radians(24))
    lz = lz - 1.1 * np.maximum(ly, 0) ** 2          # rear sweeps upward
    pad = ell(lx, ly, lz, (0.07, 0.235, 0.150))
    # layered feather tips along the back edge
    for i, (oy, oz, r) in enumerate([(0.17, -0.07, 0.085), (0.215, -0.005, 0.075), (0.235, 0.065, 0.06)]):
        lobe = ell(lx + side * 0.004 * i, ly - oy, lz - oz, (0.055, r * 1.25, r))
        pad = smin(pad, lobe, 0.018)
    return pad


def f_tail(x, y, z):
    ly, lz = rot_x(y - 0.31, z - 0.60, math.radians(-52))
    lx = x * (1.0 + 2.8 * np.maximum(ly, 0))                  # narrows to a point
    return ell(lx, ly, lz, (0.12, 0.18, 0.075))


def body_field(x, y, z, stage):
    core = f_body_core(x, y, z)
    head = f_head(x, y, z)
    d = smin(core, head, 0.045)          # soft neck crease, like the reference
    if stage >= 3:
        d = smin(d, f_tail(x, y, z), 0.05)
        for side in (1, -1):
            d = smin(d, f_wing(x, y, z, side), 0.012)
    return d


def beak_field(x, y, z):
    # upper bill: wide flat spoon, wider at the tip, raised ridge into the head
    ux, uy, uz = x, y + 0.385, z - 0.772
    uy, uz = rot_x(uy, uz, math.radians(8))
    ux = ux / (1.0 + 0.22 * np.clip(-uy / 0.15, -1, 1))
    uz = uz - 0.35 * (uy + 0.02) ** 2                         # gentle droop at tip
    upper = rbox(ux, uy, uz, (0.10, 0.135, 0.018), 0.036)
    ridge = ell(x, y + 0.285, z - 0.805, (0.092, 0.085, 0.062))
    upper = smin(upper, ridge, 0.05)
    # lower bill tucked under, slightly shorter
    lx, ly, lz = x, y + 0.365, z - 0.716
    ly, lz = rot_x(ly, lz, math.radians(-4))
    lx = lx / (1.0 + 0.15 * np.clip(-ly / 0.13, -1, 1))
    lower = rbox(lx, ly, lz, (0.085, 0.115, 0.008), 0.022)
    d = np.minimum(upper, lower)
    # mouth line: carve a thin smile groove between the bills
    groove = np.abs(z - (0.738 + 0.25 * (y + 0.30) ** 2 * (y > -0.30))) - 0.004
    groove = np.maximum(groove, -(np.abs(x) - 0.16))
    return ssub(d, np.maximum(groove, y + 0.20), 0.004)


def foot_field(x, y, z, side):
    cx = side * 0.125
    leg = capsule(x, y, z, (cx, 0.03, 0.25), (cx, -0.005, 0.055), 0.058, 0.05)
    ankle = (cx, -0.02, 0.035)
    d = leg
    web = None
    for ang in (-30, 0, 30):
        a = math.radians(ang)
        tip = (cx + math.sin(a) * 0.12, -0.02 - math.cos(a) * 0.15, 0.028)
        toe = capsule(x, y, z, ankle, tip, 0.036, 0.038)
        knob = np.sqrt((x - tip[0]) ** 2 + (y - tip[1]) ** 2 + ((z - tip[2]) * 1.3) ** 2) - 0.042
        toe = smin(toe, knob, 0.02)
        web = toe if web is None else smin(web, toe, 0.025)
    # flat webbing between toes
    webpad = rbox(x - cx, y + 0.10, z - 0.026, (0.075, 0.06, 0.004), 0.012)
    web = smin(web, webpad, 0.02)
    d = smin(d, web, 0.035)
    return np.maximum(d, -z)                 # flat sole


# ----------------------------------------------------------------- meshing
def mesh_field(name, fn, bmin, bmax, vs, coll, mat):
    nx, ny, nz = [int(math.ceil((bmax[i] - bmin[i]) / vs)) + 1 for i in range(3)]
    xs = np.linspace(bmin[0], bmin[0] + (nx - 1) * vs, nx, dtype=np.float32)
    ys = np.linspace(bmin[1], bmin[1] + (ny - 1) * vs, ny, dtype=np.float32)
    zs = np.linspace(bmin[2], bmin[2] + (nz - 1) * vs, nz, dtype=np.float32)
    field = np.empty((nx, ny, nz), dtype=np.float32)
    Y, Z = np.meshgrid(ys, zs, indexing='ij')
    for i in range(nx):                      # slab-by-slab keeps memory low
        X = np.full_like(Y, xs[i])
        field[i] = fn(X, Y, Z)
    grid = openvdb.FloatGrid(1.0)
    grid.copyFromArray(np.ascontiguousarray(field))
    pts, tris, quads = grid.convertToPolygons(isovalue=0.0, adaptivity=0.0)
    pts = np.asarray(pts) * vs + np.array(bmin)
    faces = [tuple(q) for q in np.asarray(quads).tolist()] + [tuple(t) for t in np.asarray(tris).tolist()]
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts.tolist(), [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ----------------------------------------------------------------- materials
def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0])


def clay_mat():
    m = bpy.data.materials.get("Stage_Clay") or bpy.data.materials.new("Stage_Clay")
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = srgb("#C9A49A")
    p.inputs["Roughness"].default_value = 0.55
    return m


def toy_mat(name, hexcol, rough, sss, bump_scale, bump_str, coat=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = srgb(hexcol)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Subsurface Weight"].default_value = sss
    p.inputs["Subsurface Radius"].default_value = (1.0, 0.55, 0.35)
    p.inputs["Subsurface Scale"].default_value = 0.03
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = 0.05
    if bump_str > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 6
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump_str
        bp.inputs["Distance"].default_value = 0.002
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], p.inputs["Normal"])
        # subtle warm-to-cool value variation, like soft vinyl
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = 0.92
        mr.inputs["To Max"].default_value = 1.0
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        mul.inputs["A"].default_value = srgb(hexcol)
        nt.links.new(mr.outputs["Result"], mul.inputs["B"])
        nt.links.new(mul.outputs["Result"], p.inputs["Base Color"])
    m.diffuse_color = srgb(hexcol)
    return m


def eye_objects(coll, mat_eye, mat_hi):
    objs = []
    hc = Vector(HEAD_C)
    for side in (1, -1):
        sfx = 'L' if side > 0 else 'R'
        d = Vector((side * math.sin(math.radians(54)), -math.cos(math.radians(54)), 0.14)).normalized()
        pos = hc + Vector((d.x * HEAD_R[0], d.y * HEAD_R[1], d.z * HEAD_R[2])) * 0.985
        me = bpy.data.meshes.new(f"Bataa_Eye_{sfx}")
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
        me.materials.append(mat_eye)
        eye = bpy.data.objects.new(me.name, me); coll.objects.link(eye)
        eye.scale = (0.074, 0.03, 0.098)
        eye.location = pos
        eye.rotation_euler = d.to_track_quat('-Y', 'Z').to_euler()
        b = eye.modifiers.new("Bevel", "BEVEL"); b.width = 0.48; b.segments = 4; b.affect = 'EDGES'
        s = eye.modifiers.new("Sub", "SUBSURF"); s.levels = s.render_levels = 3
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        tangent = Vector((-d.y, d.x, 0)).normalized()
        me2 = bpy.data.meshes.new(f"Bataa_EyeHi_{sfx}")
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0); bm.to_mesh(me2); bm.free()
        me2.materials.append(mat_hi)
        me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
        hi = bpy.data.objects.new(me2.name, me2); coll.objects.link(hi)
        hi.scale = (0.014, 0.006, 0.017)
        hi.location = pos + d * 0.016 + Vector((0, 0, 0.022)) - tangent * 0.012 * side
        hi.rotation_euler = eye.rotation_euler
        objs += [eye, hi]
    return objs


# ----------------------------------------------------------------- rig
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rig(objs, coll):
    arm_d = bpy.data.armatures.new("Bataa_Rig")
    arm = bpy.data.objects.new("Bataa_Rig", arm_d)
    coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_d.edit_bones

    def bone(n, h, t, parent=None):
        b = eb.new(n); b.head = h; b.tail = t
        if parent: b.parent = eb[parent]
        return b
    bone("root", (0, 0, 0), (0, 0.25, 0))
    bone("body", (0, 0.02, 0.18), (0, 0.0, 0.62), "root")
    bone("head", (0, -0.03, 0.63), (0, -0.05, 1.02), "body")
    bone("wing.L", (0.26, -0.02, 0.50), (0.29, 0.30, 0.60), "body")
    bone("wing.R", (-0.26, -0.02, 0.50), (-0.29, 0.30, 0.60), "body")
    bone("leg.L", (0.125, 0.03, 0.26), (0.125, 0.0, 0.03), "root")
    bone("leg.R", (-0.125, 0.03, 0.26), (-0.125, 0.0, 0.03), "root")
    bpy.ops.object.mode_set(mode='OBJECT')

    body = objs["body"]
    co = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    core = f_body_core(x, y, z)
    head = f_head(x, y, z)
    wh = np.clip((core - head) / 0.07 + 0.5, 0, 1)
    wings = {s: np.clip((np.minimum(core, head) - f_wing(x, y, z, s)) / 0.03 + 0.5, 0, 1) for s in (1, -1)}
    groups = {"head": wh * (1 - np.maximum(wings[1], wings[-1])),
              "wing.L": wings[1], "wing.R": wings[-1]}
    groups["body"] = np.clip(1 - groups["head"] - wings[1] - wings[-1], 0, 1)
    for gname, w in groups.items():
        vg = body.vertex_groups.new(name=gname)
        for val in np.unique(np.round(w, 2)):
            if val <= 0: continue
            idx = np.nonzero(np.round(w, 2) == val)[0].tolist()
            vg.add(idx, float(val), 'REPLACE')
    m = body.modifiers.new("Rig", "ARMATURE"); m.object = arm
    body.parent = arm

    def bone_parent(ob, bname):
        mw = ob.matrix_world.copy()
        ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bname
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    for ob in objs["head_parts"]:
        bone_parent(ob, "head")
    bone_parent(objs["foot_L"], "leg.L")
    bone_parent(objs["foot_R"], "leg.R")
    return arm


# ----------------------------------------------------------------- build
def build(stage=99, coll=None, name="Bataa"):
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    final = stage >= 7
    cream = toy_mat("Bataa_Cream", "#F6E7D2", 0.55, 0.25, 180, 0.08) if final else clay_mat()
    orange = toy_mat("Bataa_Orange", "#FF5A00", 0.38, 0.05, 260, 0.04, coat=0.25) if final else clay_mat()
    black = toy_mat("Bataa_Eye", "#060607", 0.12, 0.0, 0, 0, coat=1.0)
    white = toy_mat("Bataa_EyeHi", "#FFFFFF", 0.3, 0.0, 0, 0)
    wp = white.node_tree.nodes["Principled BSDF"]
    wp.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    wp.inputs["Emission Strength"].default_value = 2.0

    objs = {"head_parts": []}
    objs["body"] = mesh_field(name + "_Body", lambda x, y, z: body_field(x, y, z, stage),
                              (-0.40, -0.40, 0.10), (0.40, 0.58, 1.10), VS, coll, cream)
    if stage >= 4:
        objs["beak"] = mesh_field(name + "_Beak", beak_field, (-0.19, -0.60, 0.66), (0.19, -0.18, 0.88),
                                  VS_FINE, coll, orange)
        objs["head_parts"].append(objs["beak"])
    if stage >= 5:
        for side, sfx in ((1, "L"), (-1, "R")):
            cx = side * 0.125
            objs[f"foot_{sfx}"] = mesh_field(f"{name}_Foot_{sfx}", lambda x, y, z, s=side: foot_field(x, y, z, s),
                                             (cx - 0.20, -0.25, -0.01), (cx + 0.20, 0.12, 0.34), VS_FINE, coll, orange)
    if stage >= 6:
        objs["head_parts"] += eye_objects(coll, black, white)
    if stage >= 8:
        objs["rig"] = rig(objs, coll)
    return objs
