import bpy, math
from mathutils import Euler
C = bpy.context
sc = bpy.data.scenes["Scene"]
lamp = sc.objects["Lamp"]
C.view_layer.objects.active = lamp
for o in sc.objects: o.select_set(False)
sc.render.fps = 30
out = []
for win in C.window_manager.windows:
    out.append(win.screen.name)
    for area in win.screen.areas:
        if area.type == 'VIEW_3D':
            sp = area.spaces.active
            sp.show_region_toolbar = True; sp.show_region_header = True
            sp.show_region_tool_header = True; sp.show_region_ui = False
            sp.show_gizmo = True; sp.show_gizmo_navigate = True
            ov = sp.overlay
            ov.show_text = True; ov.show_floor = True; ov.show_axis_x = ov.show_axis_y = True
            ov.show_cursor = True; ov.show_extras = True; ov.show_overlays = True
            r3d = sp.region_3d
            r3d.view_perspective = 'PERSP'
            r3d.view_location = (-0.55, 0, 1.3)
            r3d.view_distance = 6.2
            r3d.view_rotation = Euler((math.radians(74), 0, math.radians(-22))).to_quaternion()
        if area.type == 'PROPERTIES':
            try: area.spaces.active.context = 'OBJECT'
            except Exception as e: out.append(str(e))
        area.tag_redraw()
RESULT = out
