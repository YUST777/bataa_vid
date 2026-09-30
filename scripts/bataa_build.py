"""Bataa duck, staged build mirroring the reference pipeline.

show(step) rebuilds the scene "BataaDuck" in the live Blender up to `step` and
frames the viewport for the review screenshot.

 1 Block out   2 Guides     3 Signed-distance field   4 Legs & feet
 5 Webbing     6 Refine     7 Surface                  8 Final mesh
 9 Feathers   10 Eyes      11 Textures                12 Rig
13 Render

Units: duck height ~1.0, forward = -Y, up = +Z.
"""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Euler, Matrix
from duck_sdf import smin, ssub, ell, rbox, capsule, rot_x, rot_z, srgb, mesh_field, toy_mat

SCENE = "BataaDuck"
CLAY = "#C79E94"
EYE_CLAY = "#CFC39A"
GUIDE = "#7CCDF5"

# ------------------------------------------------------------------ anatomy
BODY_C, BODY_R = (0.0, 0.05, 0.44), (0.30, 0.36, 0.25)
HEAD_C, HEAD_R = (0.0, -0.105, 0.845), (0.228, 0.222, 0.214)
LEG_X = 0.125
EYE_AZ, EYE_EL = 50.0, 0.10          # degrees from forward, elevation (dir z)


def head_surface_z(y):
    t = 1.0 - ((y - HEAD_C[1]) / HEAD_R[1]) ** 2
    return HEAD_C[2] + HEAD_R[2] * math.sqrt(max(t, 0.0))


TUFT_PTS = []
for i in range(8):
    t = i / 7
    y = -0.175 + 0.16 * t
    r = 0.056 - 0.02 * t
    TUFT_PTS.append(((0.0, y, head_surface_z(y) + 0.012 - 0.01 * t), r))


def eye_frame(side):
    a = math.radians(EYE_AZ)
    d = Vector((side * math.sin(a), -math.cos(a), EYE_EL)).normalized()
    hc = Vector(HEAD_C)
    # point on the ellipsoid along d
    k = 1.0 / math.sqrt((d.x / HEAD_R[0]) ** 2 + (d.y / HEAD_R[1]) ** 2 + (d.z / HEAD_R[2]) ** 2)
    p = hc + d * k
    n = Vector(((p.x - hc.x) / HEAD_R[0] ** 2, (p.y - hc.y) / HEAD_R[1] ** 2,
                (p.z - hc.z) / HEAD_R[2] ** 2)).normalized()
    return p, n


# ------------------------------------------------------------------ SDF fields
def f_body(x, y, z):
    b = ell(x - BODY_C[0], y - BODY_C[1], z - BODY_C[2], BODY_R)
    belly = ell(x, y + 0.02, z - 0.39, (0.285, 0.30, 0.215))
    rump = ell(x, y - 0.20, z - 0.48, (0.24, 0.20, 0.19))
    return smin(smin(b, belly, 0.08), rump, 0.08)


def f_head(x, y, z):
    hx, hy, hz = x - HEAD_C[0], y - HEAD_C[1], z - HEAD_C[2]
    h = ell(hx, hy, hz, HEAD_R)
    cheeks = ell(np.abs(hx) - 0.075, hy + 0.09, hz + 0.075, (0.125, 0.11, 0.105))
    return smin(h, cheeks, 0.06)


def f_tuft(x, y, z):
    d = None
    for (c, r) in TUFT_PTS:
        s = np.sqrt((x * 1.25) ** 2 + (y - c[1]) ** 2 + (z - c[2]) ** 2) - r
        d = s if d is None else smin(d, s, 0.025)
    return d


def f_wing(x, y, z, side, detail):
    lx, ly, lz = x - side * 0.252, y - 0.12, z - 0.50
    lx, ly = rot_z(lx, ly, side * math.radians(-8))
    ly, lz = rot_x(ly, lz, math.radians(22))
    lz = lz - 1.25 * np.maximum(ly, 0) ** 2          # rear sweeps up into a point
    lx = lx * (1.0 + 1.5 * np.maximum(ly, 0))        # thins toward the tip
    d = ell(lx, ly, lz, (0.058, 0.25, 0.15))
    if detail:
        # two rounded feather scallops stacked at the rear, in world space
        for cy, cz, r, ang in [(0.35, 0.53, (0.062, 0.10, 0.075), 18), (0.395, 0.625, (0.052, 0.085, 0.062), 32)]:
            fy, fz = rot_x(y - cy, z - cz, math.radians(ang))
            fx = x - side * (0.205 - 0.25 * (cy - 0.35))
            d = smin(d, ell(fx, fy, fz, r), 0.018)
    return d


def f_tail(x, y, z):
    ly, lz = rot_x(y - 0.40, z - 0.63, math.radians(-48))
    lx = x * (1.0 + 2.6 * np.maximum(ly, 0) / 0.17)
    return ell(lx, ly, lz, (0.10, 0.15, 0.065))


def body_field(stage):
    def fn(x, y, z):
        d = smin(f_body(x, y, z), f_head(x, y, z), 0.045)   # soft crease under the head
        d = smin(d, f_tuft(x, y, z), 0.03)
        if stage >= 5:
            d = smin(d, f_tail(x, y, z), 0.09)
            for s in (1, -1):
                d = smin(d, f_wing(x, y, z, s, stage >= 9), 0.035)
        return d
    return fn


def beak_field(stage):
    def fn(x, y, z):
        # upper bill: rounded spoon tip + neck toward the face + bump into the forehead
        tip = ell(x, y + 0.47, z - 0.808, (0.108, 0.095, 0.044))
        neck = rbox(x, y + 0.36, z - 0.815, (0.062, 0.08, 0.004), 0.036)
        upper = smin(tip, neck, 0.05)
        ridge = ell(x, y + 0.315, z - 0.85, (0.085, 0.085, 0.058))
        upper = smin(upper, ridge, 0.045)
        # lower bill tucked under, shorter
        ltip = ell(x, y + 0.445, z - 0.766, (0.088, 0.08, 0.026))
        lneck = rbox(x, y + 0.35, z - 0.772, (0.055, 0.07, 0.002), 0.026)
        lower = smin(ltip, lneck, 0.04)
        d = smin(upper, lower, 0.012)
        if stage >= 9:
            # smile line between the bills, curving up at the corners
            yy = y + 0.33
            zc = 0.786 + 0.6 * np.maximum(yy, 0) ** 2 + 0.25 * np.maximum(np.abs(x) - 0.05, 0) ** 2
            g = np.abs(z - zc) - 0.0035
            g = np.maximum(g, y + 0.25)
            d = ssub(d, g, 0.004)
        return d
    return fn


def foot_field(side, stage):
    cx = side * LEG_X

    def fn(x, y, z):
        leg = capsule(x, y, z, (cx, 0.03, 0.31), (cx, 0.0, 0.05), 0.056, 0.05)
        ankle = (cx, -0.015, 0.034)
        toes = None
        for ang in (-32, 0, 32):
            a = math.radians(ang + side * 6)
            tip = (cx + math.sin(a) * 0.125, -0.015 - math.cos(a) * 0.15, 0.03)
            t = capsule(x, y, z, ankle, tip, 0.034, 0.036)
            knob = np.sqrt((x - tip[0]) ** 2 + (y - tip[1]) ** 2 + ((z - tip[2]) * 1.25) ** 2) - 0.043
            t = smin(t, knob, 0.02)
            toes = t if toes is None else smin(toes, t, 0.02 if stage < 9 else 0.012)
        if stage >= 5:
            web = rbox(x - cx, y + 0.10, z - 0.024, (0.075, 0.055, 0.004), 0.013)
            toes = smin(toes, web, 0.02)
        d = smin(leg, toes, 0.035)
        return np.maximum(d, -z)
    return fn


# ------------------------------------------------------------------ scene utils
def get_scene():
    sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
    for win in bpy.context.window_manager.windows:
        win.scene = sc
    return sc


def wipe(sc):
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(sc.collection.children):
        bpy.data.collections.remove(c)
    for block in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures, bpy.data.materials,
                  bpy.data.textures, bpy.data.actions):
        for d in list(block):
            if d.users == 0:
                block.remove(d)


def coll(sc, name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in sc.collection.children:
        sc.collection.children.link(c)
    return c


def flat_mat(name, hexcol):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = srgb(hexcol)
    m.roughness = 0.6
    return m


def link(ob, c):
    c.objects.link(ob)
    return ob


def uv_sphere(name, c, loc, radii, mat, rot=(0, 0, 0), segs=32, rings=16, wire=True):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location, ob.scale, ob.rotation_euler = loc, radii, rot
    ob.show_wire = wire
    return link(ob, c)


def uv_cyl(name, c, a, b, r, mat):
    a, b = Vector(a), Vector(b)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1, radius2=1, depth=1)
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = (a + b) / 2
    ob.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    ob.scale = (r, r, (b - a).length)
    ob.show_wire = True
    return link(ob, c)


def guide(name, c, pts, mat, r=0.011):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.materials.append(mat)
    ob = link(bpy.data.objects.new(name, cu), c)
    ob.show_in_front = True
    return ob


# ------------------------------------------------------------------ build stages
def blockout(c, mat, eye_mat, parts):
    made = {}
    if "body" in parts:
        made["body"] = uv_sphere("BO_Body", c, BODY_C, BODY_R, mat)
    if "head" in parts:
        made["head"] = uv_sphere("BO_Head", c, HEAD_C, HEAD_R, mat)
        made["tuft"] = uv_sphere("BO_Tuft", c, (0, -0.10, 1.06), (0.045, 0.09, 0.045), mat, segs=24, rings=12)
    if "eyes" in parts:
        for s, sfx in ((1, "L"), (-1, "R")):
            p, n = eye_frame(s)
            made["eye" + sfx] = uv_sphere("BO_Eye_" + sfx, c, p, (0.05, 0.05, 0.05), eye_mat, segs=24, rings=12)
    if "beak" in parts:
        made["beak"] = uv_sphere("BO_Beak", c, (0, -0.40, 0.795), (0.11, 0.16, 0.05), mat, segs=24, rings=12)
    if "wings" in parts:
        for s, sfx in ((1, "L"), (-1, "R")):
            made["wing" + sfx] = uv_sphere("BO_Wing_" + sfx, c, (s * 0.27, 0.13, 0.51), (0.07, 0.24, 0.15), mat,
                                           rot=(math.radians(-22), 0, math.radians(s * 8)), segs=24, rings=12)
        made["tail"] = uv_sphere("BO_Tail", c, (0, 0.40, 0.64), (0.11, 0.16, 0.07), mat,
                                 rot=(math.radians(48), 0, 0), segs=24, rings=12)
    if "legs" in parts:
        for s, sfx in ((1, "L"), (-1, "R")):
            made["leg" + sfx] = uv_cyl("BO_Leg_" + sfx, c, (s * LEG_X, 0.02, 0.28), (s * LEG_X, 0.0, 0.05), 0.055, mat)
            made["foot" + sfx] = uv_sphere("BO_Foot_" + sfx, c, (s * LEG_X, -0.09, 0.03), (0.13, 0.15, 0.03), mat,
                                           segs=24, rings=10)
    return made


def guides(c, mat, parts):
    if "legs" in parts:
        for s, sfx in ((1, "L"), (-1, "R")):
            cx = s * LEG_X
            guide("G_Leg_" + sfx, c, [(cx, 0.03, 0.34), (cx, 0.012, 0.18), (cx, -0.015, 0.034)], mat)
            for i, ang in enumerate((-32, 0, 32)):
                a = math.radians(ang + s * 6)
                tip = (cx + math.sin(a) * 0.125, -0.015 - math.cos(a) * 0.15, 0.03)
                mid = (cx + math.sin(a) * 0.06, -0.015 - math.cos(a) * 0.075, 0.034)
                guide(f"G_Toe_{sfx}{i}", c, [(cx, -0.015, 0.034), mid, tip], mat)
    if "wings" in parts:
        for s, sfx in ((1, "L"), (-1, "R")):
            x = s * 0.33
            guide("G_Wing_" + sfx, c, [(x, -0.08, 0.46), (x, 0.10, 0.56), (s * 0.27, 0.30, 0.64),
                                       (s * 0.14, 0.44, 0.74)], mat)
        guide("G_Tail", c, [(0, 0.30, 0.58), (0, 0.42, 0.66), (0, 0.50, 0.76)], mat)
    if "tuft" in parts:
        guide("G_Tuft", c, [p for p, r in TUFT_PTS[::2]], mat, r=0.009)
    if "beak" in parts:
        guide("G_Beak", c, [(0, -0.28, 0.87), (0, -0.40, 0.83), (0, -0.56, 0.81)], mat)
        guide("G_BeakW", c, [(-0.11, -0.49, 0.81), (0, -0.57, 0.81), (0.11, -0.49, 0.81)], mat, r=0.008)


def surface(ob, strength):
    tex = bpy.data.textures.get("Bataa_Surface") or bpy.data.textures.new("Bataa_Surface", 'CLOUDS')
    tex.noise_scale = 0.06
    tex.noise_depth = 3
    m = ob.modifiers.new("Surface", 'DISPLACE')
    m.texture = tex
    m.texture_coords = 'OBJECT'
    m.strength = strength
    m.mid_level = 0.5
    return m


def eyes(c, black, white):
    out = []
    for s, sfx in ((1, "L"), (-1, "R")):
        p, n = eye_frame(s)
        me = bpy.data.meshes.new("Bataa_Eye_" + sfx)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
        me.materials.append(black)
        eye = link(bpy.data.objects.new(me.name, me), c)
        rot = n.to_track_quat('Y', 'Z')             # local +Y = outward normal
        eye.rotation_euler = rot.to_euler()
        eye.scale = (0.088, 0.05, 0.118)
        eye.location = p - n * 0.014
        b = eye.modifiers.new("Bevel", 'BEVEL'); b.width = 0.45; b.segments = 5; b.limit_method = 'NONE'
        sub = eye.modifiers.new("Sub", 'SUBSURF'); sub.levels = sub.render_levels = 3
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        # highlight: small flat dot, upper and toward the front
        side_t = rot @ Vector((1, 0, 0))
        up_t = rot @ Vector((0, 0, 1))
        me2 = bpy.data.meshes.new("Bataa_EyeHi_" + sfx)
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
        bm.to_mesh(me2); bm.free()
        me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
        me2.materials.append(white)
        hi = link(bpy.data.objects.new(me2.name, me2), c)
        hi.rotation_euler = eye.rotation_euler
        hi.scale = (0.0095, 0.004, 0.0115)
        fwd = -1 if s > 0 else 1
        hi.location = p + n * 0.0115 + up_t * 0.026 + side_t * 0.017 * fwd
        out += [eye, hi]
    return out


# ------------------------------------------------------------------ rig
def circle_shape(name, r=1.0, axis='Y'):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    me = bpy.data.meshes.new(name)
    n = 32
    v = []
    for i in range(n):
        a = 2 * math.pi * i / n
        if axis == 'Y':
            v.append((math.cos(a) * r, 0, math.sin(a) * r))
        else:
            v.append((math.cos(a) * r, math.sin(a) * r, 0))
    me.from_pydata(v, [(i, (i + 1) % n) for i in range(n)], [])
    return bpy.data.objects.new(name, me)


def smooth01(v):
    v = np.clip(v, 0, 1)
    return v * v * (3 - 2 * v)


def build_rig(c, body, attach):
    arm_d = bpy.data.armatures.new("Bataa_Rig")
    arm_d.display_type = 'OCTAHEDRAL'
    rig = link(bpy.data.objects.new("Bataa_Rig", arm_d), c)
    rig.show_in_front = True
    vl = bpy.context.view_layer
    with bpy.context.temp_override(active_object=rig, object=rig, selected_objects=[rig]):
        vl.objects.active = rig
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm_d.edit_bones

        def bone(n, h, t, parent=None, deform=True):
            b = eb.new(n); b.head, b.tail = h, t; b.use_deform = deform
            if parent:
                b.parent = eb[parent]
            return b
        bone("root", (0, 0, 0), (0, 0.3, 0), deform=False)
        bone("body", (0, 0.04, 0.26), (0, 0.02, 0.64), "root")
        bone("neck", (0, -0.04, 0.64), (0, -0.08, 0.76), "body")
        bone("head", (0, -0.08, 0.76), (0, -0.10, 1.08), "neck")
        bone("tail", (0, 0.30, 0.56), (0, 0.48, 0.74), "body")
        for s, sfx in ((1, "L"), (-1, "R")):
            bone("wing." + sfx, (s * 0.24, -0.02, 0.56), (s * 0.28, 0.32, 0.66), "body")
            bone("leg." + sfx, (s * LEG_X, 0.03, 0.32), (s * LEG_X, 0.0, 0.04), "root")
        bpy.ops.object.mode_set(mode='OBJECT')

    # weights from the SDF parts (smooth, no auto-weight guesswork)
    co = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", co)
    x, y, z = co.reshape(-1, 3).T
    core, head = f_body(x, y, z), np.minimum(f_head(x, y, z), f_tuft(x, y, z))
    w_head = smooth01((core - head) / 0.10 + 0.5)
    w_neck = np.clip(1 - np.abs(core - head) / 0.06, 0, 1) * 0.5
    w_wing = {s: smooth01((np.minimum(core, head) - f_wing(x, y, z, s, True)) / 0.03 + 0.5) for s in (1, -1)}
    w_tail = smooth01((core - f_tail(x, y, z)) / 0.04 + 0.5) * (1 - np.maximum(w_wing[1], w_wing[-1]))
    groups = {"head": w_head, "neck": w_neck, "wing.L": w_wing[1], "wing.R": w_wing[-1], "tail": w_tail}
    total = sum(groups.values())
    groups["body"] = np.clip(1 - total, 0, 1)
    norm = sum(groups.values()) + 1e-6
    for gname, w in groups.items():
        w = w / norm
        vg = body.vertex_groups.new(name=gname)
        q = np.round(w, 2)
        for val in np.unique(q):
            if val <= 0.0:
                continue
            vg.add(np.nonzero(q == val)[0].tolist(), float(val), 'REPLACE')
    mod = body.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig
    # keep the armature before the surface noise
    body.modifiers.move(len(body.modifiers) - 1, 0)
    body.parent = rig

    vl.update()
    for ob, bname in attach:
        mw = ob.matrix_world.copy()
        ob.parent = rig
        ob.parent_type = 'BONE'
        ob.parent_bone = bname
        vl.update()
        ob.matrix_world = mw

    # custom control shapes + colors, like a production rig
    shapes = coll(bpy.context.scene, "WGT")
    shapes.hide_viewport = True
    shapes.hide_render = True
    def wgt(n, r, axis):
        o = circle_shape(n, r, axis)
        if o.name not in shapes.objects:
            shapes.objects.link(o)
        return o
    pb = rig.pose.bones
    spec = {"root": ("WGT_root", 0.55, 'Z', 'THEME01'), "body": ("WGT_body", 0.40, 'Z', 'THEME09'),
            "neck": ("WGT_neck", 0.55, 'Z', 'THEME09'), "head": ("WGT_head", 0.30, 'Y', 'THEME09'),
            "tail": ("WGT_tail", 0.35, 'Y', 'THEME04'), "wing.L": ("WGT_wing", 0.30, 'Y', 'THEME03'),
            "wing.R": ("WGT_wing", 0.30, 'Y', 'THEME04'), "leg.L": ("WGT_leg", 0.45, 'Y', 'THEME03'),
            "leg.R": ("WGT_leg", 0.45, 'Y', 'THEME04')}
    for bname, (wn, r, axis, pal) in spec.items():
        pb[bname].custom_shape = wgt(wn, r, axis)
        pb[bname].color.palette = pal
        arm_d.bones[bname].color.palette = pal
        pb[bname].rotation_mode = 'XYZ'
    return rig


def animate_waddle(rig, frames=32):
    """Seamless waddle loop: body roll, alternating steps, head bob, wing flutter."""
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, frames
    pb = rig.pose.bones
    for f in range(1, frames + 2, 2):
        ph = 2 * math.pi * (f - 1) / frames
        pb["body"].rotation_euler = (math.radians(3) * math.sin(2 * ph), math.radians(7) * math.sin(ph), 0)
        pb["root"].location = (0, 0, 0.018 * abs(math.sin(ph)))
        pb["head"].rotation_euler = (math.radians(6) * math.sin(2 * ph + 0.6), 0, math.radians(8) * math.sin(ph + 0.4))
        pb["neck"].rotation_euler = (math.radians(-4) * math.sin(2 * ph + 0.3), 0, 0)
        pb["tail"].rotation_euler = (0, 0, math.radians(12) * math.sin(ph + 1.2))
        pb["wing.L"].rotation_euler = (0, math.radians(-10 - 8 * math.sin(2 * ph)), 0)
        pb["wing.R"].rotation_euler = (0, math.radians(10 + 8 * math.sin(2 * ph)), 0)
        pb["leg.L"].rotation_euler = (math.radians(22) * max(0, math.sin(ph)), 0, 0)
        pb["leg.R"].rotation_euler = (math.radians(22) * max(0, -math.sin(ph)), 0, 0)
        for b in ("body", "head", "neck", "tail", "wing.L", "wing.R", "leg.L", "leg.R"):
            pb[b].keyframe_insert("rotation_euler", frame=f)
        pb["root"].keyframe_insert("location", frame=f)


# ------------------------------------------------------------------ viewport
VIEWS = {  # az (deg, + = duck's left), tilt (90 = level), distance, target
    1: (35, 76, 2.2, (0, 0, 0.52)), 2: (32, 62, 2.4, (0, -0.02, 0.45)), 3: (58, 72, 2.0, (0, 0, 0.58)),
    4: (28, 62, 2.7, (0, -0.02, 0.40)), 5: (128, 70, 2.6, (0, 0.08, 0.50)), 6: (50, 80, 1.9, (0, -0.2, 0.74)),
    7: (68, 70, 1.9, (0, 0, 0.62)), 8: (55, 76, 2.7, (0, 0, 0.52)), 9: (100, 84, 1.8, (0.1, 0.14, 0.55)),
    10: (58, 86, 1.15, (0, -0.18, 0.80)), 11: (60, 80, 2.6, (0, 0, 0.52)), 12: (48, 76, 3.0, (0, 0, 0.52)),
    13: (56, 86, 2.5, (0, 0, 0.50)),
}


def viewport(step, sc):
    az, tilt, dist, tgt = VIEWS[step]
    full_ui = step >= 12
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            sp = area.spaces.active
            r3d = sp.region_3d
            r3d.view_perspective = 'PERSP'
            r3d.view_location = tgt
            r3d.view_distance = dist
            r3d.view_rotation = Euler((math.radians(tilt), 0, math.radians(az))).to_quaternion()
            sp.lens = 50
            sp.clip_start = 0.01
            sp.show_region_toolbar = full_ui
            sp.show_region_header = full_ui
            sp.show_region_ui = False
            sp.show_gizmo_navigate = full_ui
            ov = sp.overlay
            ov.show_text = full_ui
            ov.show_stats = False


            ov.show_cursor = step < 13
            ov.show_floor = step < 13
            ov.show_axis_x = ov.show_axis_y = step < 13
            ov.show_extras = step == 12
            ov.show_relationship_lines = False
            ov.show_bones = True
            ov.wireframe_opacity = 0.55
            sh = sp.shading
            if step <= 10:
                sh.type = 'SOLID'
                sh.light = 'STUDIO'
                sh.color_type = 'MATERIAL'
                sh.show_cavity = False
                sh.show_specular_highlight = True
                sh.background_type = 'THEME'
            elif step <= 12:
                sh.type = 'MATERIAL'
                sh.use_scene_world = False
                sh.use_scene_lights = False
                sh.studio_light = 'forest.exr' if False else sh.studio_light
                sh.studiolight_intensity = 1.0
                sh.studiolight_background_alpha = 0.0
            else:
                sh.type = 'RENDERED'
            rg = [r for r in area.regions if r.type == 'WINDOW'][0]
            return {"x": rg.x, "y": rg.y, "w": rg.width, "h": rg.height, "win_h": win.height,
                    "area": [area.x, area.y, area.width, area.height]}


# ------------------------------------------------------------------ render setup
def lookdev(sc):
    sc.render.engine = 'CYCLES'
    try:
        cp = bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX', 'CUDA'):
            try:
                cp.compute_device_type = t
                cp.get_devices()
                if any(d.type == t for d in cp.devices):
                    for d in cp.devices:
                        d.use = d.type == t
                    sc.cycles.device = 'GPU'
                    break
            except TypeError:
                continue
    except Exception:
        sc.cycles.device = 'CPU'
    sc.cycles.preview_samples = 64
    sc.cycles.use_preview_denoising = True
    sc.cycles.samples = 256
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = -0.4
    w = bpy.data.worlds.get("Bataa_World") or bpy.data.worlds.new("Bataa_World")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = srgb("#0E2A30")
    bg.inputs[1].default_value = 0.35
    c = coll(sc, "Stage")
    fl = bpy.data.meshes.new("Floor")
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60); bm.to_mesh(fl); bm.free()
    fm = bpy.data.materials.new("Floor_Mat"); fm.use_nodes = True
    fp = fm.node_tree.nodes["Principled BSDF"]
    fp.inputs["Base Color"].default_value = srgb("#5E6A6C"); fp.inputs["Roughness"].default_value = 0.7
    fl.materials.append(fm)
    link(bpy.data.objects.new("Floor", fl), c)

    def area_light(n, loc, e, size, col="#FFFFFF", spot=False):
        d = bpy.data.lights.new(n, 'SPOT' if spot else 'AREA')
        d.energy = e
        d.color = srgb(col)[:3]
        if spot:
            d.spot_size = math.radians(38); d.spot_blend = 0.35; d.shadow_soft_size = 0.25
        else:
            d.size = size
        o = link(bpy.data.objects.new(n, d), c)
        o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.45)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area_light("Key_Spot", (1.8, -2.4, 3.6), 900, 0, "#FFF3E6", spot=True)
    area_light("Fill", (-2.6, -1.6, 1.2), 90, 3.0, "#BFE3FF")
    area_light("Rim", (-1.2, 2.4, 2.2), 420, 1.2, "#FFFFFF")


# ------------------------------------------------------------------ entry
def show(step):
    sc = get_scene()
    wipe(sc)
    sc.render.engine = 'BLENDER_EEVEE'
    sc.unit_settings.system = 'METRIC'
    sc.cursor.location = (0, 0, 0)
    c_bo, c_g, c_m = coll(sc, "01_Blockout"), coll(sc, "02_Guides"), coll(sc, "03_Mesh")
    clay = flat_mat("Clay", CLAY)
    eye_clay = flat_mat("Clay_Eye", EYE_CLAY)
    gmat = flat_mat("Guide", GUIDE)

    # blockout parts still visible at this step
    bo_parts = {1: "body head eyes beak wings legs", 2: "body head eyes beak wings legs",
                3: "eyes beak wings legs", 4: "eyes beak wings", 5: "eyes beak"}.get(step, "")
    blockout(c_bo, clay, eye_clay, bo_parts.split())
    g_parts = {2: "legs wings tuft beak", 3: "legs wings tuft beak", 4: "wings tuft beak", 5: "beak"}.get(step, "")
    guides(c_g, gmat, g_parts.split())

    info = {"step": step}
    final_look = step >= 11
    cream = toy_mat("Bataa_Cream", "#F6E7D2", 0.55, 0.25, 180, 0.06)
    orange = toy_mat("Bataa_Orange", "#FF5A00", 0.38, 0.04, 260, 0.03, coat=0.2)
    black = toy_mat("Bataa_Eye", "#060607", 0.28, 0.0, 0, 0, coat=0.35)
    white = toy_mat("Bataa_EyeHi", "#FFFFFF", 0.3, 0.0, 0, 0)
    wp = white.node_tree.nodes["Principled BSDF"]
    wp.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    wp.inputs["Emission Strength"].default_value = 3.0
    if not final_look:
        for m in (cream, orange):
            m.diffuse_color = srgb(CLAY)
    black.diffuse_color = srgb("#0A0A0C")
    white.diffuse_color = (1, 1, 1, 1)

    body = feet = beak = None
    if step >= 3:
        body = mesh_field("Bataa_Body", body_field(step), (-0.42, -0.42, 0.12), (0.42, 0.62, 1.18), 0.0045, c_m, cream)
        info["body_polys"] = len(body.data.polygons)
    if step >= 4:
        feet = []
        for s, sfx in ((1, "L"), (-1, "R")):
            cx = s * LEG_X
            f = mesh_field("Bataa_Leg_" + sfx, foot_field(s, step), (cx - 0.20, -0.25, -0.01), (cx + 0.20, 0.12, 0.40),
                           0.003, c_m, orange)
            feet.append(f)
    if step >= 6:
        beak = mesh_field("Bataa_Beak", beak_field(step), (-0.17, -0.60, 0.70), (0.17, -0.22, 0.95), 0.0025, c_m, orange)
    if step >= 7:
        surface(body, 0.0018 if step < 11 else 0.0009)
    eye_objs = eyes(c_m, black, white) if step >= 10 else []

    if step >= 12:
        rig = build_rig(c_m, body, [(beak, "head")] + [(o, "head") for o in eye_objs] +
                        [(feet[0], "leg.L"), (feet[1], "leg.R")])
        animate_waddle(rig)
        sc.frame_set(9)
        vl = bpy.context.view_layer
        for o in sc.objects:
            o.select_set(False)
        rig.select_set(True)
        vl.objects.active = rig
        try:
            with bpy.context.temp_override(active_object=rig, object=rig):
                bpy.ops.object.mode_set(mode='POSE')
            rig.data.bones.active = rig.data.bones["head"]
            pbh = rig.pose.bones["head"]
            if hasattr(pbh, "select"):
                pbh.select = True
            else:
                pbh.bone.select = True
        except Exception as e:
            info["pose_err"] = str(e)
        if step >= 13:
            with bpy.context.temp_override(active_object=rig, object=rig):
                bpy.ops.object.mode_set(mode='OBJECT')
            rig.hide_set(True)
            lookdev(sc)
    if step < 12:
        for o in sc.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = None
    info["region"] = viewport(step, sc)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            area.tag_redraw()
    return info
