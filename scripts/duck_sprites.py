"""Headless: render Bataa sprite sets (transparent PNG) for the on-screen pet."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from duck_rig_v2 import load_duck, pose_waddle, pose_idle, blink, wing_pose
from mathutils import Vector

OUT = "/home/yousefmsm1/Desktop/blender/bataa_ad/sprites"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
ctl = load_duck(sc)
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 32
sc.render.resolution_x = sc.render.resolution_y = 560
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.view_settings.exposure = -0.5
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.85, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.55
for n, loc, e, s in [("Key", (2.2, -2.6, 3.0), 520, 2.5), ("Rim", (-2.0, 2.2, 2.2), 380, 1.5), ("Fill", (-2.6, -1.8, 0.9), 120, 3)]:
    L = bpy.data.lights.new(n, 'AREA'); L.energy = e; L.size = s
    o = bpy.data.objects.new(n, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, .5)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.35


def view(az, el=0.35):
    a = math.radians(az)
    cam.location = Vector((math.sin(a) * 5, -math.cos(a) * 5, 0.52 + el * 5))
    cam.rotation_euler = (Vector((0, 0, 0.52)) - cam.location).to_track_quat('-Z', 'Y').to_euler()


def shot(name):
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)

# duck faces screen-left in 3/4 when the camera sits at its front-right (az -40)
view(-40, 0.18)
for i in range(16):
    pose_waddle(ctl, i / 16); bpy.context.view_layer.update(); shot(f"walk_{i:02d}")
for i in range(24):
    pose_idle(ctl, i / 24); blink(ctl, 1.0 if i in (11, 12) else (0.5 if i in (10, 13) else 0.0))
    bpy.context.view_layer.update(); shot(f"idle_{i:02d}")
blink(ctl, 0)
view(0, 0.12)
for i in range(24):
    pose_idle(ctl, i / 24); blink(ctl, 1.0 if i in (15, 16) else (0.5 if i in (14, 17) else 0.0))
    bpy.context.view_layer.update(); shot(f"front_{i:02d}")
blink(ctl, 0); pose_idle(ctl, 0)
# point: near-camera (right) wing raised toward the menu, head follows
view(-40, 0.18)
for i in range(12):
    pose_idle(ctl, i / 12); k = min(1, i / 4)
    wing_pose(ctl, "R", 75 * k, 38 * k + 4 * math.sin(i), 0); wing_pose(ctl, "L", 8 * k)
    ctl["head"].rotation_euler.z -= math.radians(18 * k)
    bpy.context.view_layer.update(); shot(f"point_{i:02d}")
# cheer: both wings flap
for i in range(8):
    pose_idle(ctl, 0); o = 70 + 55 * math.sin(2 * math.pi * i / 8)
    wing_pose(ctl, "L", o, 15); wing_pose(ctl, "R", o, 15)
    ctl["head"].rotation_euler = (math.radians(-12), 0, 0); ctl["body"].location.z = 0.12 + 0.05 * abs(math.sin(math.pi * i / 8))
    bpy.context.view_layer.update(); shot(f"cheer_{i:02d}")
wing_pose(ctl, "L", 0); wing_pose(ctl, "R", 0); pose_idle(ctl, 0)
# happy: wings out -> use body squash + head up
ctl["head"].rotation_euler = (math.radians(-14), 0, 0); ctl["body"].scale = (1.04, 1.04, 0.95)
bpy.context.view_layer.update(); view(-40, 0.18); shot("happy")
print("SPRITES DONE")
