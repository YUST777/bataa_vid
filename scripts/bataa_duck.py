"""Procedural Bataa duck (matches bataa.png). Height = 1.0 BU at scale 1.

build_bataa(name="Bataa", scale=1.0) -> root empty.
Forward = -Y, up = +Z, feet at z=0.
Hierarchy: root > body_ctrl > (body, wings, tail, head_ctrl > head parts), legs.
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Euler


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, 1.0)


def get_mat(name, color, rough=0.5, sss=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = srgb(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Subsurface Weight"].default_value = sss
    p.inputs["Subsurface Radius"].default_value = (0.9, 0.6, 0.4)
    p.inputs["Subsurface Scale"].default_value = 0.02
    p.inputs["Specular IOR Level"].default_value = spec
    p.inputs["Coat Weight"].default_value = coat
    m.diffuse_color = srgb(color)
    return m


def _link(obj, coll):
    coll.objects.link(obj)
    return obj


def ellipsoid(name, coll, loc, radii, mat, rot=(0, 0, 0), segs=48, rings=32):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    return _link(ob, coll)


def deform(ob, fn):
    for v in ob.data.vertices:
        v.co = fn(v.co.copy())
    ob.data.update()


def rounded_box(name, coll, size, mat, levels=3, bevel=0.3):
    """Cube -> bevel -> subsurf gives soft pill/box shapes."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.scale = size
    _link(ob, coll)
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width = bevel
    b.segments = 3
    b.affect = 'EDGES'
    s = ob.modifiers.new("Sub", "SUBSURF")
    s.levels = levels
    s.render_levels = levels
    return ob


def empty(name, coll, loc=(0, 0, 0), parent=None, size=0.1):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = loc
    _link(e, coll)
    if parent:
        e.parent = parent
    return e


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def build_bataa(name="Bataa", scale=1.0, coll=None):
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    cream = get_mat("Bataa_Cream", "#F6E8D4", rough=0.6, sss=0.15, spec=0.35)
    orange = get_mat("Bataa_Orange", "#FF5A00", rough=0.4, sss=0.0, spec=0.5)
    orange_dk = get_mat("Bataa_OrangeDark", "#E84600", rough=0.45, sss=0.0)
    black = get_mat("Bataa_Eye", "#0B0B0D", rough=0.18, coat=0.6)
    white = get_mat("Bataa_EyeHi", "#FFFFFF", rough=0.3)
    white.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 1, 1, 1)
    white.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.5

    root = empty(name, coll, size=0.3)
    body_ctrl = empty(name + "_BodyCtrl", coll, (0, 0, 0.22), root)
    # ---- body: egg, fuller at bottom/back
    body = ellipsoid(name + "_Body", coll, (0, 0.03, 0.40), (0.31, 0.34, 0.25), cream)

    def body_shape(c):
        # fuller belly low, slight taper at top
        t = (c.z + 0.27) / 0.54
        k = 1.06 - 0.12 * t
        c.x *= k
        c.y *= k
        if c.z < 0:
            c.z *= 1.05
        return c
    deform(body, body_shape)
    parent_keep(body, body_ctrl)

    # ---- wings: smooth side pads whose back ends sweep up into the tail
    for side in (1, -1):
        w = ellipsoid(f"{name}_Wing_{'L' if side > 0 else 'R'}", coll,
                      (side * 0.25, 0.09, 0.45), (0.075, 0.23, 0.15), cream,
                      rot=(math.radians(-24), 0, math.radians(side * 5)))
        def wing_shape(c, side=side):
            # back end rises and thins, one soft scallop underneath
            if c.y > 0:
                c.z += 0.9 * c.y ** 2
                c.x *= 1.0 - 1.2 * c.y
            return c
        deform(w, wing_shape)
        parent_keep(w, body_ctrl)
    tail = ellipsoid(name + "_Tail", coll, (0, 0.30, 0.60), (0.12, 0.17, 0.075), cream,
                     rot=(math.radians(52), 0, 0))
    deform(tail, lambda c: Vector((c.x * (1.0 - 0.6 * max(0, c.y) / 0.17), c.y, c.z)))
    parent_keep(tail, body_ctrl)

    # ---- legs + feet
    for side in (1, -1):
        sfx = 'L' if side > 0 else 'R'
        leg_ctrl = empty(f"{name}_Leg_{sfx}", coll, (side * 0.12, 0.02, 0.22), root, 0.05)
        leg = ellipsoid(f"{name}_LegMesh_{sfx}", coll, (side * 0.12, 0.02, 0.12), (0.06, 0.06, 0.10),
                        orange_dk, segs=24, rings=16)
        parent_keep(leg, leg_ctrl)
        foot = ellipsoid(f"{name}_Foot_{sfx}", coll, (side * 0.12, -0.05, 0.03), (0.075, 0.11, 0.03),
                         orange, segs=32, rings=16)
        parent_keep(foot, leg_ctrl)
        for i, ang in enumerate((-28, 0, 28)):
            a = math.radians(ang)
            tx = side * 0.12 + math.sin(a) * 0.09
            ty = -0.05 - math.cos(a) * 0.11
            toe = ellipsoid(f"{name}_Toe_{sfx}{i}", coll, (tx, ty, 0.028), (0.042, 0.055, 0.03), orange,
                            rot=(0, 0, a), segs=24, rings=14)
            parent_keep(toe, leg_ctrl)

    # ---- head
    head_ctrl = empty(name + "_HeadCtrl", coll, (0, -0.02, 0.66), body_ctrl, 0.08)
    head = ellipsoid(name + "_Head", coll, (0, -0.06, 0.80), (0.232, 0.228, 0.218), cream)
    parent_keep(head, head_ctrl)
    tuft = ellipsoid(name + "_Tuft", coll, (0, 0.02, 0.99), (0.05, 0.12, 0.05), cream,
                     rot=(math.radians(-18), 0, 0), segs=32, rings=16)
    parent_keep(tuft, head_ctrl)

    # beak: upper + lower bill, wide and flat, bump at base
    upper = rounded_box(name + "_BeakUpper", coll, (0.20, 0.28, 0.10), orange, bevel=0.45)
    upper.location = (0, -0.37, 0.775)
    upper.rotation_euler = (math.radians(-6), 0, 0)
    deform(upper, lambda c: Vector((c.x * (1.0 - 0.25 * (c.y + 0.5)), c.y, c.z + 0.9 * max(0, c.y) ** 2)))
    parent_keep(upper, head_ctrl)
    bump = ellipsoid(name + "_BeakBump", coll, (0, -0.29, 0.80), (0.095, 0.09, 0.06), orange,
                     rot=(math.radians(-25), 0, 0), segs=32, rings=16)
    parent_keep(bump, head_ctrl)
    lower = rounded_box(name + "_BeakLower", coll, (0.17, 0.24, 0.05), orange_dk, bevel=0.45)
    lower.location = (0, -0.355, 0.728)
    lower.rotation_euler = (math.radians(4), 0, 0)
    parent_keep(lower, head_ctrl)

    # eyes: black rounded pills on the head surface + highlight
    hc = Vector((0, -0.06, 0.80))
    HR = (0.232, 0.228, 0.218)
    for side in (1, -1):
        sfx = 'L' if side > 0 else 'R'
        d = Vector((side * math.sin(math.radians(52)), -math.cos(math.radians(52)), 0.16)).normalized()
        pos = hc + Vector((d.x * HR[0], d.y * HR[1], d.z * HR[2])) * 0.975
        eye = rounded_box(f"{name}_Eye_{sfx}", coll, (0.07, 0.03, 0.095), black, bevel=0.48)
        eye.location = pos
        eye.rotation_euler = d.to_track_quat('-Y', 'Z').to_euler()
        parent_keep(eye, head_ctrl)
        hi = ellipsoid(f"{name}_EyeHi_{sfx}", coll, pos + d * 0.017 + Vector((0, 0, 0.018)) +
                       Vector((-d.y, d.x, 0)).normalized() * (0.008 * side),
                       (0.013, 0.006, 0.015), white, segs=16, rings=10)
        parent_keep(hi, head_ctrl)

    root.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    return root
