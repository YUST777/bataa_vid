#!/usr/bin/env python3
"""Mix VO + SFX + music, burn word-by-word captions, write final 16:9 and 9:16 videos."""
import json, os, subprocess

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
A, F = f"{ROOT}/audio", f"{ROOT}/renders/final"
D = json.load(open(f"{A}/vo_words.json"))
DUR = 24.0

# VO lines retimed so none overlap (line 2 dropped: no room before the break-out)
START = {0: 0.25, 1: 3.95, 3: 7.65, 4: 10.45, 5: 13.2, 6: 16.2, 7: 19.3, 8: 22.3}
old = {i: t for i, (t, _) in enumerate(D["lines"])}
words = [dict(w, s=w["s"] - old[w["line"]] + START[w["line"]], e=w["e"] - old[w["line"]] + START[w["line"]])
         for w in D["words"] if w["line"] in START]

SFX = [("menu", 2.66, .6), ("menu", 3.27, .5), ("click", 4.13, .9), ("success", 4.27, .7), ("quack", 5.08, .6),
       ("charge", 6.35, .8), ("glass_stretch", 6.95, 1.0), ("glass_pop", 7.45, 1.0), ("flap", 7.5, .6),
       ("whoosh", 7.55, .7), ("land", 8.03, .9), ("shake", 8.43, .7), ("build", 9.2, .55), ("lamp", 10.7, .8),
       ("quack", 10.93, .5), ("quack", 11.2, .35), ("success", 12.0, .35), ("quack", 16.97, .5), ("flap", 20.27, .5),
       ("glass_stretch", 20.8, .8), ("dive", 21.2, 1.0), ("ripple", 21.3, .7)]

# ---------------- audio mix
inp, fl, n = [], [], 0
def add(path, t, vol, label):
    global n
    inp.extend(["-i", path]); fl.append(f"[{n}:a]aresample=48000,volume={vol},adelay={int(t*1000)}:all=1[{label}]"); n += 1
for i, t in START.items(): add(f"{A}/vo_{i}.mp3", t, 1.0, f"v{i}")
for k, (s, t, v) in enumerate(SFX): add(f"{A}/sfx/{s}.mp3", t, v * 0.8, f"s{k}")
inp += ["-i", f"{A}/music_0.mp3", "-i", f"{A}/music_1.mp3"]
m0, m1 = n, n + 1
fl.append(f"[{m0}:a]aresample=48000,atrim=0:7.4,afade=t=in:d=0.3,afade=t=out:st=7.0:d=0.4,volume=0.55[mA]")
fl.append(f"[{m1}:a]aresample=48000,atrim=0:16.9,afade=t=in:d=0.08,afade=t=out:st=15.9:d=1.0,volume=0.6,adelay=7050:all=1[mB]")
fl.append("[mA][mB]amix=inputs=2:normalize=0[music]")
fl.append("".join(f"[v{i}]" for i in START) + f"amix=inputs={len(START)}:normalize=0,asplit[vo][vokey]")
fl.append("".join(f"[s{k}]" for k in range(len(SFX))) + f"amix=inputs={len(SFX)}:normalize=0[fx]")
fl.append("[music][vokey]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=250[mduck]")
fl.append("[vo][fx][mduck]amix=inputs=3:normalize=0,atrim=0:24,apad=whole_dur=24,"
          "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fl), "-map", "[out]",
                "-ac", "2", f"{A}/mix.wav"], check=True)

# ---------------- captions (ASS, word-by-word pop)
def ts(t):
    t = max(t, 0); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

def chunks(ws, maxw):
    out, cur = [], []
    for w in ws:
        if cur and (len(cur) >= maxw or w["line"] != cur[-1]["line"]): out.append(cur); cur = []
        cur.append(w)
        if w["w"][-1] in ".,?!": out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def ass(path, W, H, size, marg, maxw):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter,{size},&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,-1,0,0,0,100,100,0,0,1,{size*0.09:.1f},{size*0.05:.1f},2,60,60,{marg},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for ch in chunks(words, maxw):
        for j, w in enumerate(ch):
            s = w["s"]; e = ch[j + 1]["s"] if j + 1 < len(ch) else w["e"] + 0.25
            txt = []
            for k, x in enumerate(ch):
                word = x["w"].upper()
                if k == j:
                    txt.append("{\\c&H136AFF&\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}" + word + "{\\c&HFFFFFF&}")
                else:
                    txt.append(word)
            pop = "{\\fad(60,0)}" if j == 0 else ""
            ev.append(f"Dialogue: 0,{ts(s)},{ts(e)},Cap,,0,0,0,,{pop}{' '.join(txt)}")
    open(path, "w").write(head + "\n".join(ev) + "\n")

ass(f"{A}/caps_169.ass", 1920, 1080, 64, 70, 5)
ass(f"{A}/caps_916.ass", 1080, 1920, 78, 420, 3)

# ---------------- final encodes
fontdir = f"{ROOT}/assets"
for src, cap, out in (("bataa_ad.mp4", "caps_169.ass", "bataa_ad_FINAL.mp4"),
                      ("bataa_ad_vertical.mp4", "caps_916.ass", "bataa_ad_vertical_FINAL.mp4")):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{F}/{src}", "-i", f"{A}/mix.wav",
                    "-vf", f"ass={A}/{cap}:fontsdir={fontdir}", "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", f"{F}/{out}"], check=True)
    print("wrote", out)
