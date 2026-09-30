"""Final render: Cycles + OptiX, tuned for quality per second on cloud GPUs (vast.ai RTX 4090 / A6000 / L40S).

blender -b assets/ad_scene.blend --python-exit-code 1 -P scripts/render_final.py -- [--start 1] [--end 510] [--preview]
Several processes (one per GPU) can run on the same range at once: each frame is claimed with a placeholder file,
existing frames are skipped, so a crashed or interrupted run simply resumes.
"""
import bpy, sys, os

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sc = bpy.context.scene
preview = "--preview" in args
fast = "--fast" in args          # < 1 h target: fewer samples, AI denoiser does the rest
sc.frame_start, sc.frame_end = arg("--start", 1), arg("--end", 510)

# ---------------- device: every OptiX GPU visible to this process (CUDA_VISIBLE_DEVICES picks one per process)
cp = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA", "HIP", "METAL"):
    try:
        cp.compute_device_type = backend
        cp.get_devices()
        gpus = [d for d in cp.devices if d.type == backend]
        if gpus:
            for d in cp.devices:
                d.use = d.type == backend
            break
    except TypeError:
        continue
print("RENDER DEVICES:", [(d.name, d.type) for d in cp.devices if d.use])

sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.device = 'GPU'
cy.feature_set = 'SUPPORTED'
# ---------------- sampling: adaptive + AI denoise (OptiX denoiser runs on the same GPU, albedo+normal guided)
cy.use_adaptive_sampling = True
cy.samples = 96 if preview else (160 if fast else 512)
cy.adaptive_threshold = 0.03 if preview else (0.02 if fast else 0.008)
cy.adaptive_min_samples = 16 if preview else (24 if fast else 64)
cy.time_limit = 0
cy.use_denoising = True
cy.denoiser = 'OPTIX'
cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
cy.denoising_prefilter = 'ACCURATE'
cy.denoising_quality = 'HIGH' if hasattr(cy, "denoising_quality") else None
cy.sample_offset = 0
cy.seed = 0
cy.use_animated_seed = True            # grain changes per frame -> denoiser flicker turns into fine film grain, not crawling blotches
# ---------------- light paths: interior + glass + emissive screens
cy.use_light_tree = True
cy.max_bounces = 8 if fast else 10
cy.diffuse_bounces = 2 if fast else 4        # interior GI still reads with 2 + light tree
cy.glossy_bounces = 3 if fast else 4
cy.transmission_bounces = 8 if fast else 10  # glass membrane + droplets need depth
cy.transparent_max_bounces = 16 if fast else 24         # card + membrane + droplets stack up
cy.volume_bounces = 0
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.blur_glossy = 1.0
cy.sample_clamp_direct = 0.0
cy.sample_clamp_indirect = 3.0 if fast else 6.0          # kills fireflies from the window/sun bouncing off glossy desk
cy.light_sampling_threshold = 0.01
# ---------------- performance
sc.render.use_persistent_data = True    # keeps BVH/textures between frames: large win for a 510-frame shot
cy.tile_size = 2048
cy.use_auto_tile = True
sc.render.use_simplify = False
cy.texture_limit_render = 'OFF'
# ---------------- camera / film
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 50 if preview else 100
sc.render.use_motion_blur = True
sc.render.motion_blur_position = 'CENTER'
sc.render.motion_blur_shutter = 0.45
cy.motion_blur_position = 'CENTER' if hasattr(cy, "motion_blur_position") else None
sc.render.film_transparent = False
cy.film_exposure = 1.0
cy.pixel_filter_type = 'BLACKMAN_HARRIS'
cy.filter_width = 1.5
sc.view_settings.view_transform = 'Khronos PBR Neutral'
sc.view_settings.look = 'None'
# ---------------- output: resumable, multi-process safe
out = os.path.join(ROOT, "renders", "3d_preview" if preview else "3d")
os.makedirs(out, exist_ok=True)
sc.render.filepath = os.path.join(out, "f_####")
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '16'
sc.render.image_settings.compression = 15
sc.render.use_overwrite = False
sc.render.use_placeholder = True
sc.render.use_file_extension = True
print(f"RENDER {sc.frame_start}-{sc.frame_end} -> {out}  samples={cy.samples} thr={cy.adaptive_threshold}")
bpy.ops.render.render(animation=True)
print("RENDER DONE")
