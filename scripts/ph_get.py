#!/usr/bin/env python3
"""Download Poly Haven models (glTF, 1k textures) into assets/ph/<id>/. python3 ph_get.py id1 id2 ..."""
import json, os, sys, urllib.request

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ph"
UA = {"User-Agent": "bataa-ad/1.0"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


for aid in sys.argv[1:]:
  try:
      d = os.path.join(ROOT, aid)
      files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
      fmt = "gltf" if "gltf" in files else "blend"
      g = files[fmt]["1k"][fmt]
      os.makedirs(d, exist_ok=True)
      main = os.path.join(d, os.path.basename(g["url"]))
      if not os.path.exists(main):
          open(main, "wb").write(get(g["url"]))
      for rel, info in g.get("include", {}).items():
          p = os.path.join(d, rel)
          os.makedirs(os.path.dirname(p), exist_ok=True)
          if not os.path.exists(p):
              open(p, "wb").write(get(info["url"]))
      print("ok", aid, main)
  except Exception as e:
    print("FAIL", aid, e)
