# Live Blender: the "user's" tutorial file shown on the monitor.
# Default-looking scene "Scene": Camera, Light, Lamp (missing its base). Layout workspace.
import bpy, bmesh, math
from mathutils import Vector, Euler

C = bpy.context
sc = bpy.data.scenes["Scene"]
for win in C.window_manager.windows:
    win.scene = sc
    ws = bpy.data.workspaces.get("Layout")
    if ws:
        win.workspace = ws
for o in list(sc.objects):
    if o.type == 'MESH':
        bpy.data.objects.remove(o, do_unlink=True)
coll = bpy.data.collections["Collection"]

bm = bmesh.new()


def cyl(r1, r2, depth, segs, mat):
    tmp = bmesh.new()
    bmesh.ops.create_cone(tmp, cap_ends=True, segments=segs, radius1=r1, radius2=r2, depth=depth)
    bmesh.ops.transform(tmp, matrix=mat, verts=tmp.verts)
    me = bpy.data.meshes.new("tmp"); tmp.to_mesh(me); tmp.free()
    bm.from_mesh(me); bpy.data.meshes.remove(me)


def M(loc, rot=(0, 0, 0)):
    from mathutils import Matrix
    return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()


def between(a, b, r, segs=8):
    a, b = Vector(a), Vector(b)
    q = (b - a).to_track_quat('Z', 'Y')
    from mathutils import Matrix
    cyl(r, r, (b - a).length, segs, Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4())


p0 = Vector((0, 0, 0.42)); p1 = Vector((0.62, 0, 1.75)); p2 = Vector((-0.2, 0, 2.55))
cyl(0.13, 0.13, 0.22, 16, M((0, 0, 0.30)))                     # stem socket
cyl(0.11, 0.11, 0.26, 16, M(p0, (math.pi / 2, 0, 0)))          # base joint
for dy in (0.07, -0.07):
    between(p0 + Vector((0, dy, 0)), p1 + Vector((0, dy, 0)), 0.035)
    between(p1 + Vector((0, dy, 0)), p2 + Vector((0, dy, 0)), 0.035)
cyl(0.10, 0.10, 0.24, 16, M(p1, (math.pi / 2, 0, 0)))
cyl(0.09, 0.09, 0.22, 16, M(p2, (math.pi / 2, 0, 0)))
rot = (0, math.radians(37), 0)
cyl(0.16, 0.16, 0.3, 16, M(p2 + Vector((-0.10, 0, -0.13)), rot))
cyl(0.62, 0.22, 0.85, 16, M(p2 + Vector((-0.30, 0, -0.40)), rot))
me = bpy.data.meshes.new("Lamp"); bm.to_mesh(me); bm.free()
lamp = bpy.data.objects.new("Lamp", me); coll.objects.link(lamp)

cam = sc.objects.get("Camera"); light = sc.objects.get("Light")
for o in sc.objects:
    o.select_set(False)
C.view_layer.objects.active = None
sc.cursor.location = (0, 0, 0)
sc.frame_current = 1
sc.frame_end = 250

prefs = C.preferences
prefs.view.ui_scale = 0.82
prefs.view.show_splash = False
prefs.view.show_tooltips = False
prefs.view.show_statusbar_stats = False

for win in C.window_manager.windows:
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces.active
            sp.show_region_toolbar = True
            sp.show_region_header = True
            sp.show_region_tool_header = True
            sp.show_region_ui = False
            sp.show_gizmo_navigate = True
            sp.lens = 50
            ov = sp.overlay
            ov.show_text = True; ov.show_stats = False; ov.show_floor = True
            ov.show_axis_x = ov.show_axis_y = True; ov.show_cursor = True
            ov.show_extras = True; ov.show_relationship_lines = True
            sp.shading.type = 'SOLID'
            sp.shading.light = 'STUDIO'
            sp.shading.color_type = 'MATERIAL'
            sp.shading.background_type = 'THEME'
            r3d = sp.region_3d
            r3d.view_perspective = 'PERSP'
            r3d.view_location = (0.05, 0, 1.2)
            r3d.view_distance = 8.2
            r3d.view_rotation = Euler((math.radians(70), 0, math.radians(32))).to_quaternion()
        if area.type == 'PROPERTIES':
            pass
        area.tag_redraw()
RESULT = sorted(o.name for o in sc.objects)
