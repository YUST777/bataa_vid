#!/usr/bin/env python3
"""Search Sketchfab for downloadable, commercially usable models; save candidates + a thumbnail sheet per query.

python3 sk_search.py "desk setup" "office chair" ...   -> review/sk/<query>.png + review/sk/candidates.json
"""
import io, json, os, sys, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFont

OUT = "/home/yousefmsm1/Desktop/blender/bataa_ad/review/sk"
os.makedirs(OUT, exist_ok=True)
def lic_ok(label):
    l = (label or "").lower()
    return not any(b in l for b in ("noncommercial", "noderivs", "editorial"))  # CC0 / BY / BY-SA / Free Standard
UA = {"User-Agent": "bataa-ad/1.0"}
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
fontb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
db_path = f"{OUT}/candidates.json"
db = json.load(open(db_path)) if os.path.exists(db_path) else {}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()


for q in sys.argv[1:]:
    params = {"type": "models", "q": q, "downloadable": "true", "sort_by": "-likeCount", "count": 24,
              "max_face_count": 600000}
    res = json.loads(get("https://api.sketchfab.com/v3/search?" + urllib.parse.urlencode(params)))["results"]
    res = [r for r in res if lic_ok((r.get("license") or {}).get("label"))][:12]
    key = q.replace(" ", "_")
    db[key] = []
    S = 300
    sheet = Image.new("RGB", (4 * S, 3 * (S + 44)), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for i, r in enumerate(res):
        thumbs = sorted(r["thumbnails"]["images"], key=lambda t: abs(t["width"] - 400))
        try:
            im = Image.open(io.BytesIO(get(thumbs[0]["url"]))).convert("RGB")
            im.thumbnail((S, S)); x, y = (i % 4) * S, (i // 4) * (S + 44)
            sheet.paste(im, (x + (S - im.width) // 2, y))
        except Exception:
            x, y = (i % 4) * S, (i // 4) * (S + 44)
        lic = (r["license"]["label"].replace("CC Attribution", "CC-BY").replace("-ShareAlike", "-SA")
               .replace("CC0 Public Domain", "CC0").replace("Free Standard", "FreeStd"))
        d.text((x + 6, y + 4), str(i), fill=(255, 210, 0), font=fontb)
        d.text((x + 4, y + S + 2), r["name"][:32], fill=(235, 235, 235), font=font)
        d.text((x + 4, y + S + 22), f'{lic}  {r["faceCount"] // 1000}k tris  ♥{r["likeCount"]}', fill=(150, 200, 255), font=font)
        db[key].append({"i": i, "uid": r["uid"], "name": r["name"], "license": lic, "faces": r["faceCount"],
                        "likes": r["likeCount"], "author": r["user"]["username"], "url": r["viewerUrl"]})
    sheet.save(f"{OUT}/{key}.png")
    print(q, "->", len(res), "candidates")
json.dump(db, open(db_path, "w"), indent=1)
