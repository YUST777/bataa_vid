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
    for e in (root, body, head, legL, legR):
        e.rotation_mode = 'XYZ'
    root.scale = (scale,) * 3
    return {"coll": c, "root": root, "body": body, "head": head, "legL": legL, "legR": legR,
            "eyes": [obs["Eye_L"], obs["Eye_R"]], "parts": obs}


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
