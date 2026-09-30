"""Headless: build the 3D set for the Bataa ad and animate it.

3D timeline (30 fps, local frames 1..510; final video = 210 frames of 2D screen first):
  1-210   B  pull back out of the monitor, duck hops out, room builds from clay to real
  211-360 C  slow drift (composited into the real Blender UI)
  361-510 D  push back into the monitor, duck hops in; last frame = screen full-frame (loop)
Output: assets/ad_scene.blend
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Euler
sys.path.insert(0, os.path.dirname(__file__))
from duck_rig_v2 import load_duck, pose_waddle, pose_idle, blink

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
A = f"{ROOT}/assets"
bpy.ops.wm.read_homefile(use_empty=True)
sc = bpy.context.scene
sc.name = "Bataa_Ad"
sc.render.fps = 30
sc.frame_start, sc.frame_end = 1, 510


def coll(name):
    c = bpy.data.collections.new(name); sc.collection.children.link(c); return c


def move_to(objs, c):
    for o in objs:
        for uc in list(o.users_collection):
            uc.objects.unlink(o)
        c.objects.link(o)


def import_gltf(path, cname):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    c = coll(cname); move_to(new, c)
    roots = [o for o in new if o.parent is None]
    return c, new, roots


def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(cn) for o in objs if o.type == 'MESH' for cn in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    return mn, mx


def place(new, roots, target_xy, floor_z, height=None, rot_z=0.0, name="Prop"):
    piv = bpy.data.objects.new(name, None); sc.collection.objects.link(piv)
    move_to([piv], new[0].users_collection[0])
    for r in roots:
        r.parent = piv
    mn, mx = bounds(new)
    if height:
        s = height / (mx.z - mn.z); piv.scale = (s, s, s)
    bpy.context.view_layer.update()
    mn, mx = bounds(new)
    c = (mn + mx) / 2
    piv.location += Vector((target_xy[0] - c.x, target_xy[1] - c.y, floor_z - mn.z))
    piv.rotation_euler.z = rot_z
    return piv


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def pbr(name, base, scale, rough_mult=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale,) * 3
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    def img(k, nc):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(f"{A}/ph_tex/{base}_{k}.jpg")
        n.projection = 'BOX'; n.projection_blend = 0.25
        if nc: n.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mp.outputs["Vector"], n.inputs["Vector"]); return n
    nt.links.new(img("Diffuse", False).outputs["Color"], p.inputs["Base Color"])
    r = img("Rough", True)
    if rough_mult != 1.0:
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = rough_mult
        nt.links.new(r.outputs["Color"], mul.inputs[0]); nt.links.new(mul.outputs[0], p.inputs["Roughness"])
    else:
        nt.links.new(r.outputs["Color"], p.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.6
    nt.links.new(img("nor_gl", True).outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    return m


def box(name, c, a, b, mat):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    a, b = Vector(a), Vector(b); o.location = (a + b) / 2; o.scale = b - a
    return o

# ------------------------------------------------------------------ hero desk (Sketchfab, Free Standard)
c_desk, desk_objs, desk_roots = import_gltf(f"{A}/sketchfab/0e5bbf1098aa41fdb1e78b301d7b1d7d/scene.gltf", "Desk_Setup")
screen = [o for o in desk_objs if o.type == 'MESH' and any(m and m.name == "Screen_Final" for m in o.data.materials)][0]
screen.name = "Monitor_Screen"
import numpy as np
mw = screen.matrix_world
V = np.array([list(mw @ v.co) for v in screen.data.vertices])
cen = V.mean(0); _, _, vt = np.linalg.svd(V - cen)
n = Vector(vt[2]).normalized()
if n.y > 0: n = -n                                  # face the room (-Y)
up = (Vector((0, 0, 1)) - n * n.z).normalized(); right = up.cross(n).normalized()
R = (V - cen) @ np.array(right); U = (V - cen) @ np.array(up); Nn = (V - cen) @ np.array(n)
SW, SH = float(np.ptp(R)), float(np.ptp(U))
S = Vector(cen) + right * float((R.max() + R.min()) / 2) + up * float((U.max() + U.min()) / 2) + n * float(Nn.max())
SN = n; SR = right; SU = up
sm = bpy.data.materials.new("Screen_UI"); sm.use_nodes = True
nt = sm.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.name = "SwapMix"
geo = nt.nodes.new("ShaderNodeNewGeometry")
def axis_coord(axis, scale):
    sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = S
    nt.links.new(geo.outputs["Position"], sub.inputs[0])
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = axis
    nt.links.new(sub.outputs[0], dot.inputs[0])
    m = nt.nodes.new("ShaderNodeMath"); m.operation = 'MULTIPLY_ADD'; m.inputs[1].default_value = 1 / scale; m.inputs[2].default_value = 0.5
    nt.links.new(dot.outputs["Value"], m.inputs[0]); return m.outputs[0]
IMG_W = SH * 16 / 9                                  # 16:9 image, centred; sides extend
comb = nt.nodes.new("ShaderNodeCombineXYZ")
nt.links.new(axis_coord(right, IMG_W), comb.inputs[0]); nt.links.new(axis_coord(up, SH), comb.inputs[1])
im_end = nt.nodes.new("ShaderNodeTexImage"); im_end.image = bpy.data.images.load(f"{ROOT}/screen_frames/screen_after.png")
im_st = nt.nodes.new("ShaderNodeTexImage"); im_st.image = bpy.data.images.load(f"{ROOT}/screen_frames/screen_start.png")
for im in (im_end, im_st):
    im.extension = 'EXTEND'; nt.links.new(comb.outputs[0], im.inputs["Vector"])
nt.links.new(im_end.outputs["Color"], mix.inputs["A"]); nt.links.new(im_st.outputs["Color"], mix.inputs["B"])
nt.links.new(mix.outputs["Result"], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
nt.links.new(em.outputs[0], out.inputs["Surface"])
screen.data.materials.clear(); screen.data.materials.append(sm)
fac = mix.inputs["Factor"]
fac.default_value = 0.0; fac.keyframe_insert("default_value", frame=427)
fac.default_value = 1.0; fac.keyframe_insert("default_value", frame=428)

ph_m = bpy.data.materials.get("Phone_Screen_Final")
if ph_m:
    pn = ph_m.node_tree.nodes; pp = [n for n in pn if n.type == 'BSDF_PRINCIPLED'][0]
    tex = [n for n in pn if n.type == 'TEX_IMAGE' and n.outputs["Color"].is_linked and any(l.to_socket == pp.inputs["Base Color"] for l in n.outputs["Color"].links)]
    tt = tex[0] if tex else pn.new("ShaderNodeTexImage")
    tt.image = bpy.data.images.load(f"{ROOT}/assets/tiktok_screen.png")
    ph_m.node_tree.links.new(tt.outputs["Color"], pp.inputs["Base Color"]); ph_m.node_tree.links.new(tt.outputs["Color"], pp.inputs["Emission Color"])
    pp.inputs["Emission Strength"].default_value = 0.9; pp.inputs["Roughness"].default_value = 0.15
# ------------------------------------------------------------------ room shell
c_room = coll("Room")
m_floor = pbr("Floor_Laminate", "laminate_floor_02", 0.8, 0.9)
m_wall = pbr("Wall_Plaster", "beige_wall_001", 0.6)
BW, LW = 0.86, -1.75
floor = box("Floor", c_room, (LW, -4.0, -0.02), (3.2, BW, 0.0), m_floor)
back = box("Wall_Back", c_room, (LW, BW, 0), (3.2, BW + 0.1, 2.8), m_wall)
ceil = box("Ceiling", c_room, (LW, -4.0, 2.8), (3.2, BW + 0.1, 2.9), m_wall)
# left wall with a window opening (y -1.1..0.3, z 0.95..2.2)
wy0, wy1, wz0, wz1 = -1.15, 0.35, 0.95, 2.25
box("Wall_Left_A", c_room, (LW - 0.1, -4.0, 0), (LW, wy0, 2.8), m_wall)
box("Wall_Left_B", c_room, (LW - 0.1, wy1, 0), (LW, BW + 0.1, 2.8), m_wall)
box("Wall_Left_C", c_room, (LW - 0.1, wy0, 0), (LW, wy1, wz0), m_wall)
box("Wall_Left_D", c_room, (LW - 0.1, wy0, wz1), (LW, wy1, 2.8), m_wall)
m_frame = bpy.data.materials.new("Window_Frame"); m_frame.use_nodes = True
m_frame.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = srgb("#EDEAE4")
m_frame.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.35
for n, a, b in [("WinSill", (LW - 0.1, wy0 - 0.03, wz0 - 0.04), (LW + 0.08, wy1 + 0.03, wz0)),
                ("WinTop", (LW - 0.1, wy0, wz1), (LW + 0.03, wy1, wz1 + 0.05)),
                ("WinMid", (LW - 0.08, (wy0 + wy1) / 2 - 0.025, wz0), (LW - 0.02, (wy0 + wy1) / 2 + 0.025, wz1)),
                ("WinL", (LW - 0.1, wy0, wz0), (LW + 0.03, wy0 + 0.05, wz1)), ("WinR", (LW - 0.1, wy1 - 0.05, wz0), (LW + 0.03, wy1, wz1))]:
    box(n, c_room, a, b, m_frame)
m_sky = bpy.data.materials.new("Sky_Outside"); m_sky.use_nodes = True
snt = m_sky.node_tree; snt.nodes.clear()
so = snt.nodes.new("ShaderNodeOutputMaterial"); se = snt.nodes.new("ShaderNodeEmission")
sgeo = snt.nodes.new("ShaderNodeNewGeometry"); sneg = snt.nodes.new("ShaderNodeVectorMath"); sneg.operation = 'SCALE'
sneg.inputs["Scale"].default_value = -1.0; snt.links.new(sgeo.outputs["Incoming"], sneg.inputs[0])
senv = snt.nodes.new("ShaderNodeTexEnvironment"); senv.image = bpy.data.images.load(f"{A}/outdoor_2k.hdr")
snt.links.new(sneg.outputs[0], senv.inputs["Vector"]); snt.links.new(senv.outputs["Color"], se.inputs["Color"])
se.inputs["Strength"].default_value = 1.0
snt.links.new(se.outputs[0], so.inputs["Surface"])
sky = box("Sky_Card", c_room, (LW - 1.2, -2.5, 0.2), (LW - 1.15, 1.6, 3.2), m_sky)
sky.visible_shadow = False
# baseboard
m_base = m_frame
box("Baseboard_Back", c_room, (LW, BW - 0.015, 0), (3.2, BW, 0.09), m_base)
box("Baseboard_Left", c_room, (LW, -4, 0), (LW + 0.015, BW, 0.09), m_base)

# ------------------------------------------------------------------ props (Poly Haven CC0 + Sketchfab CC-BY)
def ph(aid): return f"{A}/ph/{aid}/{aid}_1k.gltf"
c, n, r = import_gltf(f"{A}/sketchfab/1ab9bf841df04c07b1819be596327629/scene.gltf", "Plant_Monstera")
place(n, r, (1.05, 0.45), 0.0, 1.3, name="Monstera")
c, n, r = import_gltf(ph("desk_lamp_arm_01"), "Desk_Lamp")
lamp = place(n, r, (-0.98, 0.5), 0.945, 0.55, rot_z=math.radians(-35), name="DeskLamp")
c, n, r = import_gltf(ph("potted_plant_04"), "Desk_Plant")
place(n, r, (0.46, 0.12), 0.945, 0.2, name="DeskPlant")
c, n, r = import_gltf(ph("wall_clock"), "Wall_Clock")
clk = place(n, r, (-0.35, BW - 0.03), 1.95, None, name="WallClock")
c, n, r = import_gltf(ph("alarm_clock_01"), "Alarm_Clock")
place(n, r, (0.27, 0.07), 0.945, 0.085, rot_z=math.radians(-25), name="AlarmClock")
c, n, r = import_gltf(ph("wooden_display_shelves_01"), "Shelves")
place(n, r, (1.9, BW - 0.25), 0.0, 1.8, name="Shelves")
c, n, r = import_gltf(ph("modern_arm_chair_01"), "Armchair")
place(n, r, (2.2, -0.9), 0.0, None, rot_z=math.radians(-120), name="Armchair")

# ------------------------------------------------------------------ duck
DS = 0.17
duck = load_duck(sc, scale=DS, name="Bataa")
droot = duck["root"]
LAND = Vector((0.13, -0.02, 0.945)); STAND = Vector((0.02, -0.08, 0.945))
droot.location = S; droot.rotation_euler = (0, 0, math.radians(180 + 20))

def kf(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None: obj.location = loc; obj.keyframe_insert("location", frame=frame)
    if rot is not None: obj.rotation_euler = rot; obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None: obj.scale = (scale,) * 3; obj.keyframe_insert("scale", frame=frame)

face_cam = (0, 0, math.radians(-25))
# hop OUT of the screen: frames 18..44 (arc), tiny inside the screen -> full size on the desk
# ---------------- 2D -> 3D pop-out transition
from mathutils import Matrix, Quaternion
import random
def scr(px, py):                      # 2D screen pixel (2560x1440 space) -> world point on the monitor
    return S + SR * ((px / 2560 - 0.5) * IMG_W) + SU * ((0.5 - py / 1440) * SH) + SN * 0.003
CARD_H = 230 / 1440 * SH
_cw, _ch = 1174, 1254
CARD_W = CARD_H * _cw / _ch
P_NEAR, P_HOME = scr(1040, 1240), scr(760, 1215)
FACE = math.atan2(SN.x, -SN.y)
BASE = Matrix((SR, -SN, SU)).transposed()
cme = bpy.data.meshes.new("Bataa_Card")
cme.from_pydata([(-CARD_W / 2, 0, 0), (CARD_W / 2, 0, 0), (CARD_W / 2, 0, CARD_H), (-CARD_W / 2, 0, CARD_H)], [], [(0, 1, 2, 3)])
cme.uv_layers.new(); uvd = cme.uv_layers[0].data
for i, uv in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]): uvd[i].uv = uv
cm = bpy.data.materials.new("Bataa_Card"); cm.use_nodes = True; cnt = cm.node_tree; cnt.nodes.clear()
co_ = cnt.nodes.new("ShaderNodeOutputMaterial"); ce = cnt.nodes.new("ShaderNodeEmission"); ctr = cnt.nodes.new("ShaderNodeBsdfTransparent")
cmx = cnt.nodes.new("ShaderNodeMixShader"); cti = cnt.nodes.new("ShaderNodeTexImage")
cti.image = bpy.data.images.load(f"{ROOT}/sprites/bataa_card.png"); cti.extension = 'CLIP'
cnt.links.new(cti.outputs["Color"], ce.inputs["Color"]); cnt.links.new(cti.outputs["Alpha"], cmx.inputs[0])
cnt.links.new(ctr.outputs[0], cmx.inputs[1]); cnt.links.new(ce.outputs[0], cmx.inputs[2]); cnt.links.new(cmx.outputs[0], co_.inputs["Surface"])
cm.surface_render_method = 'DITHERED'
cme.materials.append(cm)
card = bpy.data.objects.new("Bataa_Card", cme); duck["coll"].objects.link(card); card.rotation_mode = 'XYZ'
card.visible_shadow = False

def key_card(f, pos, spin, sc_):
    card.matrix_world = Matrix.Translation(pos) @ Quaternion(SU, spin).to_matrix().to_4x4() @ BASE.to_4x4() @ Matrix.Diagonal((sc_, sc_, sc_, 1))
    card.keyframe_insert("location", frame=f); card.keyframe_insert("rotation_euler", frame=f); card.keyframe_insert("scale", frame=f)

def key_duck(f, pos, yaw, size, flat=1.0):
    droot.location = pos; droot.rotation_euler = (0, 0, yaw); droot.scale = (size, size * flat, size)
    for a in ("location", "rotation_euler", "scale"): droot.keyframe_insert(a, frame=f)

def ease(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def bez(a, c, b, t): return a * (1 - t) ** 2 + c * 2 * t * (1 - t) + b * t * t

sp_mats = []
for nm, col, st in (("Bataa_Spark_O", "#FF6A13", 12), ("Bataa_Spark_C", "#FFE7C2", 10), ("Bataa_Spark_W", "#FFFFFF", 14)):
    m = bpy.data.materials.new(nm); m.use_nodes = True; mn_ = m.node_tree; mn_.nodes.clear()
    e_ = mn_.nodes.new("ShaderNodeEmission"); e_.inputs["Color"].default_value = srgb(col); e_.inputs["Strength"].default_value = st
    o_ = mn_.nodes.new("ShaderNodeOutputMaterial"); mn_.links.new(e_.outputs[0], o_.inputs["Surface"]); sp_mats.append(m)
spark_me = []
for m in sp_mats:
    me_ = bpy.data.meshes.new("Spark"); bm_ = bmesh.new(); bmesh.ops.create_icosphere(bm_, subdivisions=1, radius=1.0)
    bm_.to_mesh(me_); bm_.free(); me_.materials.append(m); spark_me.append(me_)
ring_me = bpy.data.meshes.new("Bataa_Ring"); bm_ = bmesh.new()
segs = 64
outer = [bm_.verts.new((math.cos(2 * math.pi * i / segs), 0, math.sin(2 * math.pi * i / segs))) for i in range(segs)]
inner = [bm_.verts.new((0.86 * math.cos(2 * math.pi * i / segs), 0, 0.86 * math.sin(2 * math.pi * i / segs))) for i in range(segs)]
for i in range(segs):
    j = (i + 1) % segs; bm_.faces.new((outer[i], outer[j], inner[j], inner[i]))
bm_.to_mesh(ring_me); bm_.free(); ring_me.materials.append(sp_mats[0])
rng = random.Random(7)

def burst(f0, at, n=30, reach=0.26, life=20, ring=True, flash=30):
    for k in range(n):
        o = bpy.data.objects.new(f"Bataa_Spark_{f0}_{k}", spark_me[k % 3]); duck["coll"].objects.link(o); o.visible_shadow = False
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 1))).normalized()
        d = (d + SN * 0.8).normalized(); spd = reach * rng.uniform(0.4, 1.0); r0 = rng.uniform(0.004, 0.011)
        L_ = life + rng.randint(-5, 5)
        for f in (f0 - 1, f0 + L_ + 1):
            o.location = at; o.scale = (1e-5,) * 3; o.keyframe_insert("scale", frame=f)
        for i in range(0, L_ + 1, 2):
            t = i / L_
            o.location = at + d * spd * (1 - (1 - t) ** 3) + Vector((0, 0, -0.12 * t * t))
            o.scale = (r0 * (1 - t) ** 0.7 + 1e-5,) * 3
            o.keyframe_insert("location", frame=f0 + i); o.keyframe_insert("scale", frame=f0 + i)
    if ring:
        rg = bpy.data.objects.new(f"Bataa_Ring_{f0}", ring_me); duck["coll"].objects.link(rg); rg.visible_shadow = False
        rg.matrix_world = Matrix.Translation(at) @ BASE.to_4x4()
        rg.scale = (1e-5,) * 3; rg.keyframe_insert("scale", frame=f0 - 1); rg.keyframe_insert("location", frame=f0 - 1)
        rg.keyframe_insert("rotation_euler", frame=f0 - 1)
        for i in range(0, 13):
            t = i / 12; r_ = 0.02 + 0.11 * (1 - (1 - t) ** 3)
            rg.scale = (r_, r_ * (1 - t) + 1e-4, r_); rg.keyframe_insert("scale", frame=f0 + i)
        rg.scale = (1e-5,) * 3; rg.keyframe_insert("scale", frame=f0 + 13)
    fl = bpy.data.lights.new(f"Bataa_Flash_{f0}", 'POINT'); fl.color = srgb("#FF8A3D")[:3]; fl.shadow_soft_size = 0.05
    fo = bpy.data.objects.new(fl.name, fl); duck["coll"].objects.link(fo); fo.location = at + SN * 0.05
    for f, e_ in ((f0 - 3, 0), (f0, flash), (f0 + 8, 0)): fl.energy = e_; fl.keyframe_insert("energy", frame=f)

# ================= LIQUID GLASS BREAK-OUT (frames 1-50) =================
import json as _json
_U = _json.load(open(f"{ROOT}/sprites/sprite_box.json"))["U"]
CARD_W = CARD_H * (_U[2] - _U[0]) / (_U[3] - _U[1])
cti.image = bpy.data.images.load(f"{ROOT}/sprites/card_front.png")
cme.vertices[0].co = (-CARD_W / 2, 0, 0); cme.vertices[1].co = (CARD_W / 2, 0, 0)
cme.vertices[2].co = (CARD_W / 2, 0, CARD_H); cme.vertices[3].co = (-CARD_W / 2, 0, CARD_H)
# card alpha control
cval = cnt.nodes.new("ShaderNodeValue"); cval.name = "CardAlpha"; cmul = cnt.nodes.new("ShaderNodeMath"); cmul.operation = 'MULTIPLY'
cnt.links.new(cti.outputs["Alpha"], cmul.inputs[0]); cnt.links.new(cval.outputs[0], cmul.inputs[1]); cnt.links.new(cmul.outputs[0], cmx.inputs[0])
def card_alpha(f, v): cval.outputs[0].default_value = v; cval.outputs[0].keyframe_insert("default_value", frame=f)

# glass membrane over the whole screen
gm = bpy.data.materials.new("Bataa_LiquidGlass"); gm.use_nodes = True
gnt = gm.node_tree; gp = gnt.nodes["Principled BSDF"]
gp.inputs["Base Color"].default_value = (0, 0, 0, 1); gp.inputs["Roughness"].default_value = 0.04
gp.inputs["Coat Roughness"].default_value = 0.02
ggeo = gnt.nodes.new("ShaderNodeNewGeometry"); guv = gnt.nodes.new("ShaderNodeUVMap"); guv.uv_map = "RestUV"
def gdot(axis):
    d_ = gnt.nodes.new("ShaderNodeVectorMath"); d_.operation = 'DOT_PRODUCT'; d_.inputs[1].default_value = axis
    gnt.links.new(ggeo.outputs["Normal"], d_.inputs[0]); return d_.outputs["Value"]
off = gnt.nodes.new("ShaderNodeCombineXYZ")
for i_, ax_ in ((0, SR), (1, SU)):
    m_ = gnt.nodes.new("ShaderNodeMath"); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = -0.10
    gnt.links.new(gdot(ax_), m_.inputs[0]); gnt.links.new(m_.outputs[0], off.inputs[i_])
uvo = gnt.nodes.new("ShaderNodeVectorMath"); uvo.operation = 'ADD'
gnt.links.new(guv.outputs["UV"], uvo.inputs[0]); gnt.links.new(off.outputs[0], uvo.inputs[1])
g_end = gnt.nodes.new("ShaderNodeTexImage"); g_end.image = im_end.image
g_st = gnt.nodes.new("ShaderNodeTexImage"); g_st.image = im_st.image
gmix = gnt.nodes.new("ShaderNodeMix"); gmix.data_type = 'RGBA'
for im_ in (g_end, g_st): im_.extension = 'EXTEND'; gnt.links.new(uvo.outputs[0], im_.inputs["Vector"])
gnt.links.new(g_end.outputs["Color"], gmix.inputs["A"]); gnt.links.new(g_st.outputs["Color"], gmix.inputs["B"])
gnt.links.new(gmix.outputs["Result"], gp.inputs["Emission Color"])
gfac = gmix.inputs["Factor"]
gfac.default_value = 0.0; gfac.keyframe_insert("default_value", frame=427)
gfac.default_value = 1.0; gfac.keyframe_insert("default_value", frame=428)
# glass only where the surface bends: mask = clamp((1 - N.SN) * 10)
mk1 = gnt.nodes.new("ShaderNodeMath"); mk1.operation = 'SUBTRACT'; mk1.inputs[0].default_value = 1.0
gnt.links.new(gdot(SN), mk1.inputs[1])
mk = gnt.nodes.new("ShaderNodeMath"); mk.operation = 'MULTIPLY'; mk.inputs[1].default_value = 10.0; mk.use_clamp = True
gnt.links.new(mk1.outputs[0], mk.inputs[0])
for sock, mul_ in (("Specular IOR Level", 0.9), ("Coat Weight", 1.0)):
    m_ = gnt.nodes.new("ShaderNodeMath"); m_.operation = 'MULTIPLY'; m_.inputs[1].default_value = mul_
    gnt.links.new(mk.outputs[0], m_.inputs[0]); gnt.links.new(m_.outputs[0], gp.inputs[sock])
es = gnt.nodes.new("ShaderNodeMath"); es.operation = 'MULTIPLY_ADD'; es.inputs[1].default_value = 0.35; es.inputs[2].default_value = 1.0
gnt.links.new(mk.outputs[0], es.inputs[0]); gnt.links.new(es.outputs[0], gp.inputs["Emission Strength"])
dropm = bpy.data.materials.new("Bataa_DropGlass"); dropm.use_nodes = True
dpp = dropm.node_tree.nodes["Principled BSDF"]
dpp.inputs["Base Color"].default_value = (0.92, 0.96, 1.0, 1); dpp.inputs["Roughness"].default_value = 0.02
dpp.inputs["Coat Weight"].default_value = 1.0; dpp.inputs["Alpha"].default_value = 0.55
dpp.inputs["Emission Color"].default_value = (1, 1, 1, 1); dpp.inputs["Emission Strength"].default_value = 0.35
dropm.surface_render_method = 'DITHERED'
NX, NZ = 190, 100
mem_me = bpy.data.meshes.new("Glass_Membrane"); bm_ = bmesh.new()
vs = [[bm_.verts.new(((i / (NX - 1) - 0.5) * SW, 0, (j / (NZ - 1) - 0.5) * SH)) for i in range(NX)] for j in range(NZ)]
for j in range(NZ - 1):
    for i in range(NX - 1):
        bm_.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
bm_.to_mesh(mem_me); bm_.free()
mem_me.polygons.foreach_set("use_smooth", [True] * len(mem_me.polygons)); mem_me.materials.append(gm)
ruv = mem_me.uv_layers.new(name="RestUV")
for li, lp in enumerate(mem_me.loops):
    v_ = mem_me.vertices[lp.vertex_index].co; ruv.data[li].uv = (v_.x / IMG_W + 0.5, v_.z / SH + 0.5)
mem = bpy.data.objects.new("Glass_Membrane", mem_me); duck["coll"].objects.link(mem)
mem.matrix_world = Matrix.Translation(S + SN * 0.004) @ BASE.to_4x4()
mem.visible_shadow = False
BX = np.array([v.co.x for v in mem_me.vertices]); BZ = np.array([v.co.z for v in mem_me.vertices])
mem.shape_key_add(name="Basis")
def local(pw):
    d_ = pw - S; return float(d_.dot(SR)), float(d_.dot(SU))
def mem_key(f, disp):
    k = mem.shape_key_add(name=f"f{f}", from_mix=False)
    co = np.zeros(len(BX) * 3, np.float32); co[0::3] = BX; co[1::3] = -disp; co[2::3] = BZ
    k.data.foreach_set("co", co)
    for ff, v in ((f - 1, 0.0), (f, 1.0), (f + 1, 0.0)):
        k.value = v; k.keyframe_insert("value", frame=ff)
def ripple(r, k, amp=0.011, speed=0.0065, lam=0.034, decay=13.0):
    R = speed * k
    env = np.exp(-((r - R) / 0.06) ** 2) + 0.35 * np.exp(-((r - R * 0.6) / 0.05) ** 2)
    return amp * math.exp(-k / decay) * env * np.cos(2 * math.pi * (r - R) / lam) / (1 + 6 * r)

Pm = P_NEAR + SU * CARD_H * 0.5; cx0, cz0 = local(Pm); r_out = np.hypot(BX - cx0, BZ - cz0)
def h_out(f):
    if f < 3: return 0.0, 0.05
    if f < 12: e = ease((f - 3) / 9); return 0.10 * e, 0.055 - 0.012 * e
    if f < 16: e = (f - 12) / 4; return 0.10 + 0.05 * e, 0.043 - 0.02 * e
    return 0.0, 0.03
for f in range(1, 52):
    h, sg = h_out(f)
    disp = h * np.exp(-(r_out / sg) ** 2)
    if f < 3: disp = 0.002 * math.sin(f * 2.1) * np.exp(-(r_out / 0.06) ** 2)
    if f >= 16:
        k = f - 16
        disp = -0.022 * math.exp(-k / 4) * math.cos(k * 1.25) * np.exp(-(r_out / 0.05) ** 2) + ripple(r_out, k)
    mem_key(f, disp)
# card rides the bulge tip then melts away
for f in range(1, 13):
    h, _ = h_out(f)
    key_card(f, P_NEAR + SN * (h + 0.003), 0, 1 + 0.12 * ease(f / 12))
    card_alpha(f, 1.0 - ease((f - 5) / 6))
key_card(13, P_NEAR, 0, 1e-4); card_alpha(13, 0.0)
# duck forms inside the bulge, breaks through, flips and lands
for f in range(1, 6): key_duck(f, Pm, FACE, 1e-4)
for f in range(6, 17):
    h, _ = h_out(f); t = (f - 6) / 10
    size = CARD_H * 1.1 + (DS * 0.8 - CARD_H * 1.1) * ease(t)
    key_duck(f, Pm - SU * size * 0.5 + SN * max(h - size * 0.3, 0.0), FACE, size, 0.1 + 0.6 * ease(t))
P16 = droot.location.copy()
Y_START = face_cam[2] - 2 * math.pi
for f in range(16, 33):
    t = (f - 16) / 16
    size = DS * 0.8 + DS * 0.2 * ease(t / 0.4)
    flat = 0.7 + 0.3 * (1 - math.exp(-7 * t) * math.cos(10 * t))
    key_duck(f, bez(P16, P16 + SN * 0.10 + SU * 0.09, LAND, t), FACE - 2 * math.pi * (1 - ease(t)) + (face_cam[2] - FACE) * ease(t), size, flat)
# flip: a full forward somersault while airborne, done through the body control
for f, rx in ():
    duck["body"].rotation_euler.x = rx; duck["body"].keyframe_insert("rotation_euler", index=0, frame=f)
duck["body"].rotation_euler.x = 0.0

def droplets(f0, at, n, reach, life):
    dm = bpy.data.meshes.new("GlassDrop"); b2 = bmesh.new(); bmesh.ops.create_icosphere(b2, subdivisions=2, radius=1.0)
    b2.to_mesh(dm); b2.free(); dm.materials.append(dropm); dm.polygons.foreach_set("use_smooth", [True] * len(dm.polygons))
    for k in range(n):
        o = bpy.data.objects.new(f"Bataa_Spark_drop_{f0}_{k}", dm); duck["coll"].objects.link(o); o.visible_shadow = False
        d = (Vector((rng.uniform(-1, 1), 0, rng.uniform(-0.4, 1))).normalized() * 0.8 + SN * 1.0).normalized()
        d = (d.x * SR + d.z * SU + SN * abs(d.y)).normalized() if False else (SR * rng.uniform(-1, 1) + SU * rng.uniform(-0.3, 1) + SN * rng.uniform(0.6, 1.4)).normalized()
        spd = reach * rng.uniform(0.4, 1.0); r0 = rng.uniform(0.003, 0.009); L_ = life + rng.randint(-4, 4)
        o.location = at; o.scale = (1e-5,) * 3; o.keyframe_insert("scale", frame=f0 - 1); o.keyframe_insert("location", frame=f0 - 1)
        for i in range(0, L_ + 1, 2):
            t = i / L_
            o.location = at + d * spd * (1 - (1 - t) ** 3) + Vector((0, 0, -0.10 * t * t))
            o.scale = (r0 * (1 - t ** 3) + 1e-5, r0 * (1 - t ** 3) * (1.4 - 0.4 * t) + 1e-5, r0 * (1 - t ** 3) + 1e-5)
            o.keyframe_insert("location", frame=f0 + i); o.keyframe_insert("scale", frame=f0 + i)
        o.scale = (1e-5,) * 3; o.keyframe_insert("scale", frame=f0 + L_ + 2)
droplets(16, Pm + SN * 0.12, 14, 0.22, 20)
fl = bpy.data.lights.new("Bataa_Flash", 'POINT'); fl.color = (1, 0.93, 0.85); fl.shadow_soft_size = 0.05
fo = bpy.data.objects.new("Bataa_Flash", fl); duck["coll"].objects.link(fo); fo.location = Pm + SN * 0.08
for f, e_ in ((12, 0), (16, 8), (24, 0), (426, 0), (430, 5), (438, 0)): fl.energy = e_; fl.keyframe_insert("energy", frame=f)
# land squash handled via body scale
for f, s in ((32, (1.14, 1.14, 0.8)), (36, (0.95, 0.95, 1.07)), (40, (1, 1, 1))):
    duck["body"].scale = s; duck["body"].keyframe_insert("scale", frame=f)
# waddle to STAND (frames 60..110), then idle; look at camera 150..200
walk_dir = (STAND - LAND); yaw = math.atan2(walk_dir.x, -walk_dir.y)
for f in range(42, 211, 2):
    if f < 60:
        pose_idle(duck, f / 48)
        kf(droot, f, loc=LAND, rot=face_cam)
    elif f <= 110:
        t = (f - 60) / 50
        kf(droot, f, loc=LAND.lerp(STAND, t), rot=(0, 0, yaw))
        pose_waddle(duck, (f - 60) / 16)
    else:
        rz = yaw + (face_cam[2] - yaw) * min(1, (f - 110) / 14)
        kf(droot, f, loc=STAND, rot=(0, 0, rz))
        pose_idle(duck, f / 48)
        if 150 <= f <= 200:
            duck["head"].rotation_euler.z += math.radians(12) * math.sin(math.pi * (f - 150) / 50)
    for k in ("body", "head", "legL", "legR"):
        duck[k].keyframe_insert("rotation_euler", frame=f)
    duck["body"].keyframe_insert("location", frame=f)
    blink(duck, 1.0 if f in (130, 132, 250, 252, 330) else 0.0)
    for e in duck["eyes"]: e.keyframe_insert("scale", frame=f)
# C: idle & a wave-hop at 300
for f in range(212, 361, 2):
    pose_idle(duck, f / 48)
    for k in ("body", "head", "legL", "legR"):
        duck[k].keyframe_insert("rotation_euler", frame=f)
    duck["body"].keyframe_insert("location", frame=f)
    blink(duck, 1.0 if f in (250, 252, 330) else 0.0)
    for e in duck["eyes"]: e.keyframe_insert("scale", frame=f)
kf(droot, 360, loc=STAND, rot=(0, 0, face_cam[2]))
# D: turn to the screen, hop INTO it (frames 400..432), vanish into the UI
back_yaw = math.atan2((S - STAND).x, -(S - STAND).y)
kf(droot, 380, loc=STAND, rot=(0, 0, back_yaw), scale=DS)
for f, s in ((392, (1.08, 1.08, 0.84)), (398, (1, 1, 1))):
    duck["body"].scale = s; duck["body"].keyframe_insert("scale", frame=f)
# ================= LIQUID GLASS DIVE-IN (398-470) =================
PmH = P_HOME + SU * CARD_H * 0.5; cx1, cz1 = local(PmH); r_in = np.hypot(BX - cx1, BZ - cz1)
Qc = PmH + SN * 0.15
Y_A = back_yaw
for f in range(398, 417):
    t = (f - 398) / 18
    key_duck(f, bez(STAND, STAND.lerp(Qc, 0.5) + SU * 0.26, Qc - SU * DS * 0.5, t), Y_A + (FACE + math.pi - Y_A) * ease(t), DS)
def h_in(f):
    if f < 414: return 0.0, 0.04
    if f < 419: return 0.14 * ease((f - 414) / 5), 0.024            # glass reaches out to catch the duck
    if f < 428: e = ease((f - 419) / 9); return 0.14 * (1 - e), 0.024 + 0.03 * e
    return 0.0, 0.05
for f in range(412, 472):
    h, sg = h_in(f)
    disp = h * np.exp(-(r_in / sg) ** 2)
    if f >= 428:
        k = f - 428
        disp = -0.016 * math.exp(-k / 4) * math.cos(k * 1.25) * np.exp(-(r_in / 0.05) ** 2) + ripple(r_in, k, amp=0.009)
    mem_key(f, disp)
for f in range(417, 429):
    h, _ = h_in(f); t = (f - 417) / 11
    size = DS + (CARD_H * 1.1 - DS) * ease(t)
    key_duck(f, PmH - SU * size * 0.5 + SN * max(h, 0.02 * (1 - t)), FACE + math.pi * (1 - ease(t)) , size, 1 - 0.9 * ease(t))
for f in (429, 510): key_duck(f, PmH, FACE, 1e-4)
key_card(423, P_HOME, 0, 1e-4); card_alpha(423, 0.0)
for f in range(424, 431):
    h, _ = h_in(f); t = (f - 424) / 6
    key_card(f, P_HOME + SN * (h + 0.003), 0, 1.1 - 0.1 * ease(t)); card_alpha(f, ease(t))
key_card(510, P_HOME + SN * 0.003, 0, 1.0); card_alpha(510, 1.0)
droplets(428, PmH + SN * 0.03, 8, 0.10, 14)
# membrane only exists during the transitions
for f, hid in ((1, False), (52, True), (411, True), (412, False), (510, False)):
    mem.hide_render = hid; mem.keyframe_insert("hide_render", frame=f)

# ---- performance pass (overrides all per-part keys above)
import duck_acting
duck_acting.animate(duck)
droplets(46, LAND + Vector((0, 0, 0.09)), 10, 0.16, 16)      # glass flicked off during the shake
# ------------------------------------------------------------------ build-up: clay -> real (per object "build")
clay = bpy.data.materials.new("Clay"); clay.use_nodes = True
cp = clay.node_tree.nodes["Principled BSDF"]
cp.inputs["Base Color"].default_value = srgb("#B9B6B1"); cp.inputs["Roughness"].default_value = 0.62
skip_mats = {"Screen_UI", "Sky_Outside"}
done = set()
for m in list(bpy.data.materials):
    if m.name in skip_mats or m.name.startswith("Bataa_") or m.name == "Clay" or not m.use_nodes:
        continue
    nt = m.node_tree
    outn = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL']
    if not outn or not outn[0].inputs["Surface"].links:
        continue
    o = outn[0]; src = o.inputs["Surface"].links[0].from_socket
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_type = 'OBJECT'; at.attribute_name = "build"
    cb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    cb.inputs["Base Color"].default_value = cp.inputs["Base Color"].default_value; cb.inputs["Roughness"].default_value = 0.62
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(at.outputs["Fac"], ms.inputs[0]); nt.links.new(cb.outputs[0], ms.inputs[1]); nt.links.new(src, ms.inputs[2])
    nt.links.new(ms.outputs[0], o.inputs["Surface"])
    m.surface_render_method = 'DITHERED'

# waves: (collection names or object-name prefixes, frame)
waves = [(["Desk_Setup"], 70), (["Desk_Plant", "Alarm_Clock"], 92), (["Desk_Lamp"], 110), (["Plant_Monstera"], 128),
         (["Room"], 146), (["Shelves", "Wall_Clock", "Armchair"], 164)]
for names, f0 in waves:
    for cn in names:
        cc = bpy.data.collections[cn]
        for i, o in enumerate(cc.all_objects):
            if o.type != 'MESH' or o.name in ("Sky_Card", "Monitor_Screen"):
                continue
            o["build"] = 0.0; o.keyframe_insert('["build"]', frame=f0 + (i % 5))
            o["build"] = 1.0; o.keyframe_insert('["build"]', frame=f0 + (i % 5) + 7)
# pop: small scale bounce on each wave's pivot / meshes (skip room shell)
for names, f0 in waves:
    for cn in names:
        if cn == "Room": continue
        for o in bpy.data.collections[cn].objects:
            if o.parent is None:
                s = o.scale.copy()
                o.scale = s; o.keyframe_insert("scale", frame=f0 - 1)
                o.scale = s * 0.96; o.keyframe_insert("scale", frame=f0 + 2)
                o.scale = s * 1.025; o.keyframe_insert("scale", frame=f0 + 5)
                o.scale = s; o.keyframe_insert("scale", frame=f0 + 10)

# ------------------------------------------------------------------ lighting
c_l = coll("Lights")
def light(n, typ, loc, rot=None, energy=100, color="#FFFFFF", size=1.0, target=None):
    d = bpy.data.lights.new(n, typ); d.energy = energy; d.color = srgb(color)[:3]
    if typ == 'AREA': d.size = size
    if typ == 'SPOT': d.spot_size = math.radians(55); d.spot_blend = 0.6; d.shadow_soft_size = 0.05
    if typ == 'SUN': d.angle = math.radians(1.5)
    o = bpy.data.objects.new(n, d); c_l.objects.link(o); o.location = loc
    if target: o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if rot: o.rotation_euler = rot
    return o
sun = light("Sun_Window", 'SUN', (LW - 1, -0.4, 2.6), rot=Euler((math.radians(55), 0, math.radians(-75))), energy=0.0, color="#FFE9CF")
win = light("Window_Fill", 'AREA', (LW + 0.05, (wy0 + wy1) / 2, (wz0 + wz1) / 2), energy=0.0, color="#DCEBFF", size=1.4,
            target=(0.3, (wy0 + wy1) / 2, 1.0))
key = light("Blockout_Key", 'AREA', (1.2, -1.6, 2.6), energy=260, size=2.5, target=(-0.3, 0.2, 1.0))
lampspot = light("Lamp_Bulb", 'SPOT', (-0.92, 0.38, 1.45), energy=0.0, color="#FFC98A", target=(-0.55, 0.05, 0.95))
ceil_fill = light("Ceiling_Fill", 'AREA', (0.3, -1.0, 2.75), energy=0.0, color="#FFF1E0", size=2.0, target=(0.3, -1.0, 0))
def kl(o, frames_vals, attr="energy"):
    for f, v in frames_vals:
        setattr(o.data, attr, v); o.data.keyframe_insert(attr, frame=f)
kl(key, [(1, 260), (146, 260), (170, 60)])
kl(lampspot, [(1, 0), (112, 0), (116, 45)])
kl(sun, [(1, 0), (150, 0), (168, 4.5)])
kl(win, [(1, 0), (150, 0), (168, 350)])
kl(ceil_fill, [(1, 0), (150, 0), (168, 120)])
sky_em = m_sky.node_tree.nodes["Emission"]
sky_em.inputs["Strength"].default_value = 0.3; sky_em.inputs["Strength"].keyframe_insert("default_value", frame=150)
sky_em.inputs["Strength"].default_value = 1.1; sky_em.inputs["Strength"].keyframe_insert("default_value", frame=168)
w = bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
env = w.node_tree.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(f"{A}/studio_small_09_2k.hdr")
w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
bgs = w.node_tree.nodes["Background"].inputs["Strength"]
bgs.default_value = 0.6; bgs.keyframe_insert("default_value", frame=150)
bgs.default_value = 0.25; bgs.keyframe_insert("default_value", frame=170)

# ------------------------------------------------------------------ camera
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera")); sc.collection.objects.link(cam); sc.camera = cam
tgt = bpy.data.objects.new("Cam_Target", None); sc.collection.objects.link(tgt)
tc_ = cam.constraints.new('TRACK_TO'); tc_.target = tgt; tc_.track_axis = 'TRACK_NEGATIVE_Z'; tc_.up_axis = 'UP_Y'
cd = cam.data; cd.sensor_width = 36; cd.clip_start = 0.01; cd.clip_end = 60
# full-frame distance: screen width fills the 16:9 frame (tiny overscan hides the bezel edge)
fill_d = lambda lens: (SH * 0.99 / 2) / ((18 / lens) * 9 / 16)
LENS0 = 50
P0 = S + SN * fill_d(LENS0)
keys = [  # frame, cam, target, lens
    (1, P0, S, LENS0), (8, P0 + SN * 0.03, S, LENS0), (26, P0 + SN * 0.42 + SU * 0.02 + SR * 0.10, S + SU * -0.12 + SR * 0.12, 42),
    (60, Vector((0.05, -1.05, 1.22)), Vector((-0.1, 0.1, 1.08)), 38),
    (120, Vector((0.62, -0.95, 1.18)), Vector((-0.18, 0.18, 1.02)), 32),
    (210, Vector((0.80, -1.30, 1.30)), Vector((-0.10, 0.02, 1.0)), 30),
    (300, Vector((0.25, -1.18, 1.22)), Vector((-0.02, -0.02, 1.0)), 34), (360, Vector((-0.15, -1.30, 1.28)), Vector((-0.12, 0.08, 1.02)), 32),
    (440, Vector((-0.2, -1.55, 1.36)), S + Vector((0, 0, -0.03)), 40),
    (500, P0 + SN * 0.04, S, LENS0), (510, P0, S, LENS0)]
for f, p, t, l in keys:
    cam.location = p; cam.keyframe_insert("location", frame=f)
    tgt.location = t; tgt.keyframe_insert("location", frame=f)
    cd.lens = l; cd.keyframe_insert("lens", frame=f)
cd.dof.use_dof = True; cd.dof.focus_object = droot; cd.dof.aperture_fstop = 4.0
for f, fs in ((1, 22), (30, 22), (60, 3.2), (200, 5.6), (430, 5.6), (470, 22)):
    cd.dof.aperture_fstop = fs; cd.dof.keyframe_insert("aperture_fstop", frame=f)

# ease everything
from bpy_extras import anim_utils
for idb in list(bpy.data.objects) + list(bpy.data.cameras) + list(bpy.data.lights):
    ad = idb.animation_data
    if not ad or not ad.action: continue
    for slot in ad.action.slots:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, slot)
        if not cb: continue
        for fc in cb.fcurves:
            for k in fc.keyframe_points:
                if idb in (cam, tgt, cd):
                    k.interpolation = 'BEZIER'; k.easing = 'AUTO'
                    k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
            fc.update()
for ob_ in [droot, card] + [o for o in bpy.data.objects if o.name.startswith(("Bataa_Spark", "Bataa_Ring"))]:
    ad_ = ob_.animation_data
    if not (ad_ and ad_.action): continue
    for slot in ad_.action.slots:
        cb_ = anim_utils.action_get_channelbag_for_slot(ad_.action, slot)
        for fc in cb_.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
_ad = duck["body"].animation_data
for slot in _ad.action.slots:
    for fc in anim_utils.action_get_channelbag_for_slot(_ad.action, slot).fcurves:
        if fc.data_path == "rotation_euler" and fc.array_index == 0:
            for k in fc.keyframe_points:
                if abs(k.co.x - 27) < 0.01: k.interpolation = 'CONSTANT'
# screen swap must be a hard cut
ad = sm.node_tree.animation_data
if ad and ad.action:
    for slot in ad.action.slots:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, slot)
        for fc in cb.fcurves:
            for k in fc.keyframe_points: k.interpolation = 'CONSTANT'

# ------------------------------------------------------------------ render settings
sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
ee.taa_render_samples = 48
ee.use_raytracing = True
ee.ray_tracing_options.resolution_scale = '2'
ee.use_shadows = True
ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.4
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = 'Khronos PBR Neutral'; sc.view_settings.look = 'None'
sc.view_settings.exposure = 0.0
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = f"{ROOT}/renders/3d/f_"
bpy.ops.wm.save_as_mainfile(filepath=f"{A}/ad_scene.blend")
print("BUILT", dict(S=list(S), SW=SW, SH=SH, P0=list(P0)))
