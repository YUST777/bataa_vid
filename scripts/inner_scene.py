# Runs inside the live Blender (via bx.py). Builds the tutorial scene shown on the monitor:
# a low-poly desk lamp that is missing its base (the user adds it with Bataa's help).
import bpy, bmesh, math
from mathutils import Vector

C = bpy.context
sc = C.scene
for o in list(bpy.data.objects):
    if o.type == 'MESH':
        bpy.data.objects.remove(o)

coll = bpy.data.collections["Collection"]


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def cyl(name, r1, r2, depth, segs=16):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r1, radius2=r2, depth=depth)
    return mesh_obj(name, bm)


def aim(ob, a, b):
    """Place a Z-aligned cylinder between points a and b."""
    a, b = Vector(a), Vector(b)
    ob.location = (a + b) / 2
    ob.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()


p0 = Vector((0, 0, 0.16))      # base pivot
p1 = Vector((0.55, 0.0, 1.55))  # elbow
p2 = Vector((-0.15, 0.0, 2.35))  # head joint

stem = cyl("Lamp_Stem", 0.14, 0.14, 0.14, 16); stem.location = (0, 0, 0.23)
j0 = cyl("Lamp_Joint", 0.11, 0.11, 0.26, 12); j0.location = p0 + Vector((0, 0, 0.15)); j0.rotation_euler = (math.pi / 2, 0, 0)
for i, dy in enumerate((0.07, -0.07)):
    a = cyl(f"Lamp_ArmLower.{i:03d}", 0.035, 0.035, 1.0, 8); aim(a, p0 + Vector((0, dy, 0.15)), p1 + Vector((0, dy, 0)))
j1 = cyl("Lamp_Elbow", 0.1, 0.1, 0.24, 12); j1.location = p1; j1.rotation_euler = (math.pi / 2, 0, 0)
for i, dy in enumerate((0.07, -0.07)):
    a = cyl(f"Lamp_ArmUpper.{i:03d}", 0.035, 0.035, 1.0, 8); aim(a, p1 + Vector((0, dy, 0)), p2 + Vector((0, dy, 0)))
j2 = cyl("Lamp_HeadJoint", 0.09, 0.09, 0.22, 12); j2.location = p2; j2.rotation_euler = (math.pi / 2, 0, 0)
# shade: truncated cone pointing down-left
shade = cyl("Lamp_Shade", 0.62, 0.22, 0.85, 16)
shade.location = p2 + Vector((-0.42, 0, -0.18))
shade.rotation_euler = (0, math.radians(-125), 0)
neck = cyl("Lamp_Neck", 0.16, 0.16, 0.25, 12)
neck.location = p2 + Vector((-0.12, 0, -0.02)); neck.rotation_euler = (0, math.radians(-125), 0)

for o in coll.objects:
    if o.type == 'MESH':
        o.data.polygons.foreach_set("use_smooth", [False] * len(o.data.polygons))

# 3D cursor at origin so "Add > Cube" lands where the base goes
sc.cursor.location = (0, 0, 0)
for o in bpy.data.objects:
    o.select_set(False)
C.view_layer.objects.active = None
sc.frame_end = 250

prefs = C.preferences
prefs.view.ui_scale = 0.67
prefs.view.show_splash = False
prefs.view.show_tooltips = False

# frame the viewport like the reference shot
for area in C.screen.areas:
    if area.type == 'VIEW_3D':
        r3d = area.spaces.active.region_3d
        r3d.view_perspective = 'PERSP'
        r3d.view_location = (0.1, 0, 1.15)
        r3d.view_distance = 7.8
        from mathutils import Euler
        r3d.view_rotation = Euler((math.radians(68), 0, math.radians(28))).to_quaternion()
        area.spaces.active.shading.type = 'SOLID'
        area.spaces.active.overlay.show_stats = False
RESULT = [o.name for o in coll.objects]
