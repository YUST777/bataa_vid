#!/usr/bin/env python3
"""Download Sketchfab models (glTF) into assets/sketchfab/<uid>/.

Token: env SKETCHFAB_TOKEN, or the first line of ~/.sketchfab_token (chmod 600).
Get it at https://sketchfab.com/settings/password  ->  "API Token".
Usage: python3 sk_get.py <uid or model URL> [...]
"""
import io, json, os, re, sys, urllib.request, zipfile

ROOT = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/sketchfab"
tok = os.environ.get("SKETCHFAB_TOKEN") or open(os.path.expanduser("~/.sketchfab_token")).readline().strip()
H = {"Authorization": f"Token {tok}", "User-Agent": "bataa-ad/1.0"}


def req(url, auth=True):
    return urllib.request.urlopen(urllib.request.Request(url, headers=H if auth else {"User-Agent": H["User-Agent"]}),
                                  timeout=120).read()


for arg in sys.argv[1:]:
    uid = re.findall(r"[0-9a-f]{32}", arg)[-1]
    meta = json.loads(req(f"https://api.sketchfab.com/v3/models/{uid}", auth=False))
    dl = json.loads(req(f"https://api.sketchfab.com/v3/models/{uid}/download"))
    src = dl.get("gltf") or dl.get("glb")
    d = os.path.join(ROOT, uid)
    os.makedirs(d, exist_ok=True)
    data = req(src["url"], auth=False)          # pre-signed URL, no auth header
    if src["url"].split("?")[0].endswith(".zip") or data[:2] == b"PK":
        zipfile.ZipFile(io.BytesIO(data)).extractall(d)
    else:
        open(os.path.join(d, "model.glb"), "wb").write(data)
    lic = (meta.get("license") or {}).get("label")
    with open(os.path.join(d, "CREDIT.txt"), "w") as f:
        f.write(f'"{meta["name"]}" by {meta["user"]["username"]} - {meta["viewerUrl"]} - license: {lic}\n')
    print("ok", uid, meta["name"], "|", lic, "|", d)
