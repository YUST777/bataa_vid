#!/usr/bin/env python3
"""ElevenLabs: voiceover (with word timestamps), SFX and a music bed -> audio/*.  Key: ~/.elevenlabs_key"""
import base64, json, os, sys, urllib.request, urllib.error

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad"
OUT = f"{ROOT}/audio"; os.makedirs(f"{OUT}/sfx", exist_ok=True)
KEY = open(os.path.expanduser("~/.elevenlabs_key")).read().strip()
VOICE = "TX3LPaxmHKxFdv7VOQHJ"          # Liam - energetic social media creator


def post(path, body, raw=False):
    req = urllib.request.Request("https://api.elevenlabs.io" + path, data=json.dumps(body).encode(),
                                 headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, path, e.read()[:300]); return None
    return r if raw else json.loads(r)


# ---------------- voiceover: start time (s) -> line
VO = [(0.35, "Meet Bataa, your AI mentor inside the apps you learn."),
      (3.2, "It shows you exactly where to click..."),
      (5.3, "and cheers when you get it right."),
      (7.9, "But Bataa doesn't just live on your screen."),
      (10.6, "Every step you take, you build for real."),
      (13.6, "Blender. Unity. Godot."),
      (16.2, "Any app. Learn it by doing."),
      (19.6, "Stop watching tutorials. Start building."),
      (22.3, "bataa dot app.")]
if "vo" in sys.argv or len(sys.argv) == 1:
    words = []
    for i, (t0, line) in enumerate(VO):
        r = post(f"/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
                 {"text": line, "model_id": "eleven_multilingual_v2",
                  "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}})
        if not r: sys.exit(1)
        open(f"{OUT}/vo_{i}.mp3", "wb").write(base64.b64decode(r["audio_base64"]))
        a = r["alignment"]; cur, s = "", None
        for ch, cs, ce in zip(a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]):
            if ch.isspace():
                if cur: words.append({"w": cur, "s": t0 + s, "e": t0 + pe, "line": i}); cur = ""
                continue
            if not cur: s = cs
            cur += ch; pe = ce
        if cur: words.append({"w": cur, "s": t0 + s, "e": t0 + pe, "line": i})
        print("vo", i, round(a["character_end_times_seconds"][-1], 2), "s")
    json.dump({"lines": VO, "words": words}, open(f"{OUT}/vo_words.json", "w"), indent=1)

# ---------------- SFX: name -> (prompt, seconds)
SFX = {
 "click": ("single crisp computer mouse click, close mic, clean", 0.6),
 "menu": ("soft modern UI pop-up menu open sound, subtle airy tick", 0.6),
 "success": ("bright cute success chime, two sparkling notes, modern app notification", 1.2),
 "charge": ("rising magical energy charge-up shimmer, building tension, 1 second", 1.2),
 "glass_stretch": ("thick liquid glass stretching and bulging, gooey wet elastic creak, cinematic", 1.4),
 "glass_pop": ("big wet liquid bubble pop burst with glassy splash and droplets, cinematic impact", 1.5),
 "whoosh": ("fast cartoon whoosh fly-by, air swish", 0.8),
 "land": ("small soft plastic toy landing on a wooden desk, gentle thud with a bounce", 0.7),
 "shake": ("small wet rubber duck shaking off water droplets, quick flappy shake and drips", 1.2),
 "quack": ("cute short happy rubber duck squeak quack", 0.6),
 "lamp": ("desk lamp switch click and soft electric hum turning on", 0.9),
 "build": ("magical shimmering build-up sweep, soft sparkles swelling, objects appearing", 3.0),
 "ripple": ("water surface ripple, gentle liquid wobble, glassy shimmer", 2.0),
 "dive": ("small object diving into water with a bright bloop splash", 1.0),
 "flap": ("small bird wings flapping quickly, soft feathers", 0.9),
}
if "sfx" in sys.argv or len(sys.argv) == 1:
    for n, (p, d) in SFX.items():
        if os.path.exists(f"{OUT}/sfx/{n}.mp3"): continue
        r = post("/v1/sound-generation", {"text": p, "duration_seconds": max(d, 0.5), "prompt_influence": 0.5}, raw=True)
        if r: open(f"{OUT}/sfx/{n}.mp3", "wb").write(r); print("sfx", n)

# ---------------- music bed
if "music" in sys.argv or len(sys.argv) == 1:
    prompt = ("Modern cinematic tech commercial music, 24 seconds, 120 bpm. 0-7s: light playful plucks and soft synth "
              "pad, curious and clean. At 7s: a big drop, punchy drums, warm bass and uplifting synths, confident and "
              "inspiring. 20-24s: resolve softly back to the playful plucks so it loops. No vocals.")
    r = post("/v1/music", {"prompt": prompt, "music_length_ms": 24000}, raw=True)
    if r: open(f"{OUT}/music.mp3", "wb").write(r); print("music ok (compose)")
    else:
        parts = [("upbeat playful tech commercial music intro, light plucks, soft synth pad, 120 bpm, no vocals", 8),
                 ("energetic uplifting cinematic tech commercial music drop, punchy drums, warm bass, bright synths, 120 bpm, no vocals", 16)]
        for i, (p, d) in enumerate(parts):
            r = post("/v1/sound-generation", {"text": p, "duration_seconds": d, "prompt_influence": 0.4}, raw=True)
            if r: open(f"{OUT}/music_{i}.mp3", "wb").write(r); print("music part", i)
