"""Bataa performance pass: every beat has anticipation -> action -> follow-through -> settle.

Keys body / head / legs / wings / eyes on every frame (1-510). Root travel/yaw stays in build_ad3d.py.
Beat sheet (3D frames, 30 fps):
  1-16    forms inside the liquid glass: curled, eyes shut, wings tucked
  16-20   BREAK: eyes pop open, wings burst out, head snaps up
  16-29   flight: fast flaps, legs tucked, body pitched forward
  29-32   braking: wings high, legs reach down
  32-42   landing: squash, head follow-through, wings settle with a flutter
  44-56   shakes off the glass droplets (wet-dog shake)
  56-70   looks around at the clay room, blink
  70-110  waddle to its spot: leg steps, balance wings, counter head bob
  112-130 lamp switches on: looks at it, happy double hop + flaps
  146-170 room lights up: looks up in wonder, wings half open
  172-205 turns to camera: curious head tilt, waves with the right wing
  212-360 idle while the reveal plays: breathing, glances, preen, happy hop, points at the monitor
  360-398 turns to the monitor, walks, crouches (anticipation)
  398-418 jumps: stretch, flaps up to the screen, legs tucked
  418-428 dives into the glass: wings tucked tight, eyes shut, streamlined
"""
import math

import bpy

TAU = 2 * math.pi


def sm(a, b, f):
    t = min(max((f - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def env(f, a, b, c, d):
    """0 before a, ramps to 1 by b, holds, back to 0 from c to d."""
    return sm(a, b, f) * (1 - sm(c, d, f))


def spring(f, f0, amp, freq=0.9, decay=5.0):
    """Damped overshoot that starts at f0 (follow-through / settle)."""
    if f < f0:
        return 0.0
    k = f - f0
    return amp * math.exp(-k / decay) * math.cos(k * freq)


def flap(f, period=5.0):
    return math.sin(TAU * f / period)


BLINKS = [58, 96, 136, 162, 196, 232, 268, 296, 334, 372]


def blink_amount(f):
    if 1 <= f < 16 or 419 <= f:
        return 1.0                                   # shut while forming / diving
    a = 0.0
    for b in BLINKS:
        d = abs(f - b)
        a = max(a, 1.0 if d < 1 else (0.55 if d < 2.5 else 0.0))
    return a


def pose(f):
    """Returns channel values for frame f."""
    P = dict(bz=0.0, bpx=0.0, broll=0.0, byaw=0.0, sx=1.0, sz=1.0,
             hx=0.0, hy=0.0, hz=0.0, lL=0.0, lR=0.0,
             wLo=0.0, wRo=0.0, wLf=0.0, wRf=0.0, wLt=0.0, wRt=0.0, eye=1.0)
    br = math.sin(TAU * f / 52)                       # breathing
    P["sz"] += 0.012 * br
    P["sx"] -= 0.006 * br
    P["hx"] += 1.5 * math.sin(TAU * f / 52 + 0.8)     # head rides the breath
    P["hz"] += 2.0 * math.sin(TAU * f / 97) + 1.2 * math.sin(TAU * f / 41)  # micro life

    # ---- A: forming inside the glass
    a = 1 - sm(14, 17, f)
    P["hx"] += 14 * a; P["wLo"] += -4 * a; P["wRo"] += -4 * a

    # ---- B/C: break + flight
    fl = env(f, 16, 18, 27, 30)
    fo = 72 + 58 * flap(f - 16, 5.0)
    P["wLo"] += fo * fl; P["wRo"] += fo * fl
    P["wLt"] += 18 * flap(f - 17, 5.0) * fl; P["wRt"] += 18 * flap(f - 17, 5.0) * fl
    P["hx"] += -16 * env(f, 16, 18, 24, 30) + spring(f, 16, -8, 1.1, 3)
    P["bpx"] += 12 * env(f, 17, 21, 26, 31)
    tuck = env(f, 16, 19, 27, 30)
    P["lL"] += 48 * tuck; P["lR"] += 44 * tuck
    P["eye"] += 0.18 * env(f, 16, 17, 22, 30)          # eyes wide on the pop

    # ---- D: braking before touchdown
    brake = env(f, 27, 29, 32, 38)
    P["wLo"] += 118 * brake; P["wRo"] += 118 * brake
    P["wLf"] += 20 * brake; P["wRf"] += 20 * brake
    P["bpx"] += -10 * brake; P["hx"] += -8 * brake

    # ---- E: landing squash + follow-through
    if f >= 32:
        k = f - 32
        sq = -0.20 * math.exp(-k / 3.2) * math.cos(k * 0.75)
        P["sz"] += sq; P["sx"] -= sq * 0.55
        P["bz"] += sq * 0.45
        P["hx"] += spring(f, 32, 20, 0.7, 4.5)
        settle = spring(f, 32, 35, 1.3, 3.5) * (1 - sm(40, 46, f))
        P["wLo"] += max(settle, 0) * sm(31, 33, f); P["wRo"] += max(settle, 0) * sm(31, 33, f)

    # ---- F: shake off the droplets
    sh = env(f, 44, 46, 53, 57)
    P["broll"] += 16 * math.sin(TAU * (f - 44) / 4.2) * sh
    P["hz"] += -22 * math.sin(TAU * (f - 44) / 4.2 + 0.9) * sh
    P["wLo"] += (14 + 12 * math.sin(TAU * (f - 44) / 4.2)) * sh
    P["wRo"] += (14 - 12 * math.sin(TAU * (f - 44) / 4.2)) * sh
    P["sz"] += -0.04 * sh

    # ---- G: looks around at the room (anticipate with a tiny counter move)
    P["hz"] += 38 * env(f, 57, 61, 63, 66) - 34 * env(f, 64, 68, 72, 76) - 4 * env(f, 55, 57, 57, 59)
    P["hy"] += 10 * env(f, 57, 61, 63, 66) - 8 * env(f, 64, 68, 72, 76)

    # ---- H: waddle 76-110 (root travels in build_ad3d from 60-110)
    wk = env(f, 60, 64, 106, 110)
    ph = TAU * (f - 60) / 16
    P["lL"] += 26 * max(0, math.sin(ph)) * wk; P["lR"] += 26 * max(0, -math.sin(ph)) * wk
    P["broll"] += 8 * math.sin(ph) * wk
    P["bz"] += 0.025 * abs(math.sin(ph)) * wk
    P["hy"] += -6 * math.sin(ph + 0.5) * wk            # head counters the roll
    P["hx"] += 5 * math.sin(2 * ph + 0.9) * wk
    P["wLo"] += (12 + 8 * math.sin(ph)) * wk; P["wRo"] += (12 - 8 * math.sin(ph)) * wk
    P["hz"] += spring(f, 110, 8, 0.8, 4)               # settle when it stops

    # ---- I: lamp turns on (112): look, then happy double hop with flaps
    look = env(f, 111, 115, 128, 134)
    P["hz"] += 48 * look; P["hx"] += -6 * look
    for h0 in (119, 127):
        hop = env(f, h0, h0 + 3, h0 + 3, h0 + 6)
        pre = env(f, h0 - 3, h0 - 1, h0 - 1, h0)          # crouch before each hop
        P["bz"] += 0.30 * hop - 0.05 * pre
        P["sz"] += 0.10 * hop - 0.10 * pre
        P["wLo"] += 80 * hop * (0.6 + 0.4 * flap(f, 3)); P["wRo"] += 80 * hop * (0.6 + 0.4 * flap(f, 3))
        P["lL"] += 20 * hop; P["lR"] += 20 * hop
        P["sz"] += spring(f, h0 + 6, -0.08, 1.0, 2.5)

    # ---- J: room lights up (150-168): wonder
    won = env(f, 148, 154, 166, 172)
    P["hx"] += -22 * won; P["hz"] += 36 * won; P["hy"] += 8 * won
    P["wLo"] += 26 * won; P["wRo"] += 26 * won
    P["bpx"] += -6 * won

    # ---- K: to camera: curious tilt, then wave with the right wing
    tilt = env(f, 174, 180, 190, 196)
    P["hy"] += -18 * tilt; P["hx"] += -4 * tilt
    wave = env(f, 184, 188, 202, 208)
    P["wRo"] += 110 * wave; P["wRf"] += (10 + 28 * math.sin(TAU * (f - 184) / 7)) * wave
    P["broll"] += -5 * wave
    P["wRo"] += -10 * env(f, 181, 183, 183, 185)       # tiny wind-up before the wave

    # ---- L: idle during the reveal
    P["hz"] += 16 * env(f, 214, 220, 236, 242)                             # glance left
    pre = env(f, 250, 256, 274, 280)                                         # preen the left wing
    P["hz"] += 62 * pre; P["hx"] += 26 * pre; P["hy"] += 10 * pre
    P["wLo"] += (26 + 6 * math.sin(TAU * f / 5)) * pre
    P["hz"] += 5 * math.sin(TAU * f / 5) * env(f, 258, 260, 270, 272)       # little nibbles
    for h0 in (300, 307):                                                    # happy hops
        hop = env(f, h0, h0 + 3, h0 + 3, h0 + 6); prep = env(f, h0 - 3, h0 - 1, h0 - 1, h0)
        P["bz"] += 0.24 * hop - 0.05 * prep; P["sz"] += 0.09 * hop - 0.09 * prep
        P["wLo"] += 70 * hop; P["wRo"] += 70 * hop
    P["sz"] += spring(f, 313, -0.07, 1.0, 2.5)
    pt = env(f, 326, 332, 350, 356)                                         # "look, the screen!"
    P["hz"] += 70 * pt; P["hx"] += -6 * pt
    P["wLo"] += 78 * pt; P["wLf"] += (40 + 6 * math.sin(TAU * f / 9)) * pt
    P["broll"] += 4 * pt

    # ---- M: turn + walk to the monitor, crouch
    tw = env(f, 360, 364, 378, 382)
    ph2 = TAU * (f - 360) / 12
    P["lL"] += 22 * max(0, math.sin(ph2)) * tw; P["lR"] += 22 * max(0, -math.sin(ph2)) * tw
    P["broll"] += 6 * math.sin(ph2) * tw
    cr = env(f, 384, 394, 397, 399)
    P["bz"] += -0.09 * cr; P["sz"] += -0.15 * cr; P["sx"] += 0.06 * cr
    P["hx"] += 16 * cr; P["wLt"] += -30 * cr; P["wRt"] += -30 * cr
    P["wLo"] += 22 * cr; P["wRo"] += 22 * cr

    # ---- N: jump + flaps up to the screen
    st = env(f, 398, 400, 402, 406)
    P["sz"] += 0.16 * st; P["sx"] -= 0.06 * st
    fl2 = env(f, 399, 401, 414, 418)
    fo2 = 76 + 56 * flap(f - 399, 5.0)
    P["wLo"] += fo2 * fl2; P["wRo"] += fo2 * fl2
    P["lL"] += 46 * env(f, 399, 403, 418, 422); P["lR"] += 42 * env(f, 399, 403, 418, 422)
    P["hx"] += -10 * env(f, 399, 403, 412, 417)

    # ---- O: dive: tuck + streamline
    dv = sm(416, 420, f)
    P["wLo"] = P["wLo"] * (1 - dv) - 6 * dv; P["wRo"] = P["wRo"] * (1 - dv) - 6 * dv
    P["hx"] += 18 * dv; P["sz"] += 0.10 * dv; P["sx"] -= 0.08 * dv

    P["eye"] = max(0.0, P["eye"] * (1 - blink_amount(f) * 0.9))
    return P


def animate(duck, frames=range(1, 511)):
    from duck_rig_v2 import wing_pose
    body, head, lL, lR = duck["body"], duck["head"], duck["legL"], duck["legR"]
    eyes = duck["eyes"]
    for o in [body, head, lL, lR, duck["wingL"], duck["wingR"]] + eyes:
        o.animation_data_clear()
    for e in eyes:
        if "rest_scale_z" not in e:
            e["rest_scale_z"] = e.scale.z
    base_bz = 0.12
    r = math.radians
    for f in frames:
        P = pose(f)
        body.location.z = base_bz + P["bz"]
        body.rotation_euler = (r(P["bpx"]), r(P["broll"]), r(P["byaw"]))
        body.scale = (P["sx"], P["sx"], P["sz"])
        head.rotation_euler = (r(P["hx"]), r(P["hy"]), r(P["hz"]))
        lL.rotation_euler = (r(P["lL"]), 0, 0); lR.rotation_euler = (r(P["lR"]), 0, 0)
        wing_pose(duck, "L", P["wLo"], P["wLf"], P["wLt"]); wing_pose(duck, "R", P["wRo"], P["wRf"], P["wRt"])
        for e in eyes:
            e.scale.z = e["rest_scale_z"] * P["eye"]
        for o, paths in ((body, ("location", "rotation_euler", "scale")), (head, ("rotation_euler",)),
                         (lL, ("rotation_euler",)), (lR, ("rotation_euler",)),
                         (duck["wingL"], ("rotation_euler",)), (duck["wingR"], ("rotation_euler",))):
            for p_ in paths:
                o.keyframe_insert(p_, frame=f)
        for e in eyes:
            e.keyframe_insert("scale", frame=f)
