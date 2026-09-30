"""Headless: render review stills of ad_scene.blend. -- f1 f2 ... [--res 960]"""
import bpy, sys
args = sys.argv[sys.argv.index("--") + 1:]
res = 960
if "--res" in args:
    res = int(args[args.index("--res") + 1]); args = args[:args.index("--res")]
bpy.ops.wm.open_mainfile(filepath="/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ad_scene.blend")
sc = bpy.context.scene
sc.render.resolution_x = res; sc.render.resolution_y = res * 9 // 16
sc.eevee.taa_render_samples = 24
sc.render.use_motion_blur = False
for f in args:
    sc.frame_set(int(f))
    sc.render.filepath = f"/home/yousefmsm1/Desktop/blender/bataa_ad/review/ad3d/t_{int(f):03d}.png"
    bpy.ops.render.render(write_still=True)
print("TEST DONE")
