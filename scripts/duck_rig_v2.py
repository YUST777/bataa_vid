"""Shared: load the clean v2 duck into the current scene with a simple control hierarchy.
root > body_ctrl > (Body, head_ctrl > Head/Beak/Eyes), leg_L/leg_R > Leg/Foot.
Returns dict of controls. Duck height ~1.0 at scale 1, forward -Y."""
import bpy
from mathutils import Vector

V2 = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/bataa_v2.blend"


def load_duck(scene, scale=1.0, name="Bataa"):
    with bpy.data.libraries.load(V2) as (src, dst):
        dst.collections = ["Bataa"]
    c = dst.collections[0]
    c.name = name
    scene.collection.children.link(c)
    obs = {o.name.split(".")[0]: o for o in c.objects}
    for o in c.objects:
        for m in [m for m in o.modifiers if m.name == "WireView"]:
            o.modifiers.remove(m)

    def empty(n, loc, parent=None):
        e = bpy.data.objects.new(f"{name}_{n}", None)
        e.empty_display_size = 0.15
        c.objects.link(e)
        e.location = loc
        if parent:
            e.parent = parent
        return e
    root = empty("root", (0, 0, 0))
    body = empty("body", (0, 0.05, 0.12), root)
    head = empty("head", (0, -0.04, 0.58), body)
    legL = empty("legL", (0.12, 0.0, 0.30), root)
    legR = empty("legR", (-0.12, 0.0, 0.30), root)
    bpy.context.view_layer.update()

    def attach(ob, parent):
        mw = ob.matrix_world.copy()
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
        ob.matrix_world = mw
    for n in ("Body",):
        attach(obs[n], body)
    for n in ("Head", "Beak", "Eye_L", "Eye_R"):
        attach(obs[n], head)
    for n in ("Leg_L", "Foot_L"):
        attach(obs[n], legL)
    for n in ("Leg_R", "Foot_R"):
        attach(obs[n], legR)
    wings = {}
    for sgn, sfx in ((1, "L"), (-1, "R")):
        w_ = empty("wing" + sfx, (sgn * 0.285, -0.10, 0.515), body)
        wings[sfx] = w_
        bpy.context.view_layer.update()
        wm = make_wing(f"{name}_Wing_{sfx}", sgn, obs["Body"].data.materials[0])
        c.objects.link(wm)
        wm.parent = w_
    for e in (root, body, head, legL, legR, wings["L"], wings["R"]):
        e.rotation_mode = 'XYZ'
    root.scale = (scale,) * 3
    return {"coll": c, "root": root, "body": body, "head": head, "legL": legL, "legR": legR,
            "wingL": wings["L"], "wingR": wings["R"], "eyes": [obs["Eye_L"], obs["Eye_R"]], "parts": obs}


def make_wing(name, sgn, mat):
    """Soft teardrop wing, origin at the shoulder, lying back along the body side (+Y), editable quads + subsurf."""
    import bmesh, math
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    for v in bm.verts:
        d = v.co.normalized()
        t = (d.y + 1) / 2                                  # 0 front .. 1 tip
        w = 0.115 * (1 - 0.70 * t ** 1.5) * (0.6 + 0.4 * math.sin(math.pi * min(t * 1.3, 1)))
        th = 0.045 * (1 - 0.55 * t)
        y = 0.02 + t * 0.36
        z = d.z * w - 0.15 * t - 0.02
        x = sgn * (d.x * th + 0.03 - 0.06 * t * t)
        v.co = (x, y, z)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    sub = ob.modifiers.new("Subdivision", 'SUBSURF'); sub.levels = sub.render_levels = 2
    return ob


def wing_pose(ctl, sfx, open_deg, fan_deg=0.0, twist_deg=0.0):
    import math
    sgn = 1 if sfx == "L" else -1
    ctl["wing" + sfx].rotation_euler = (math.radians(twist_deg), -sgn * math.radians(open_deg), -sgn * math.radians(fan_deg))


def pose_waddle(ctl, phase, amp=1.0, bob=True):
    """phase 0..1 of a step cycle."""
    import math
    p = 2 * math.pi * phase
    ctl["body"].rotation_euler = (math.radians(3) * math.sin(2 * p) * amp, math.radians(7) * math.sin(p) * amp, 0)
    ctl["head"].rotation_euler = (math.radians(5) * math.sin(2 * p + 0.7) * amp, 0, math.radians(6) * math.sin(p + 0.5) * amp)
    ctl["legL"].rotation_euler = (math.radians(24) * max(0, math.sin(p)) * amp, 0, 0)
    ctl["legR"].rotation_euler = (math.radians(24) * max(0, -math.sin(p)) * amp, 0, 0)
    ctl["body"].location.z = 0.12 + (0.025 * abs(math.sin(p)) * amp if bob else 0)


def pose_idle(ctl, t):
    import math
    ctl["body"].rotation_euler = (0, math.radians(1.5) * math.sin(2 * math.pi * t), 0)
    ctl["head"].rotation_euler = (math.radians(3) * math.sin(2 * math.pi * t + 0.5), 0, math.radians(4) * math.sin(2 * math.pi * t * 0.5))
    ctl["body"].location.z = 0.12 + 0.008 * math.sin(2 * math.pi * t)
    ctl["legL"].rotation_euler = ctl["legR"].rotation_euler = (0, 0, 0)


def blink(ctl, amount):
    for e in ctl["eyes"]:
        if "rest_scale_z" not in e:
            e["rest_scale_z"] = e.scale.z
        e.scale.z = e["rest_scale_z"] * (1 - 0.88 * amount)
