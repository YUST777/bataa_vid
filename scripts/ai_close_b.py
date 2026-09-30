"""System python (scipy): morphological closing of the duck volume -> signed distance of the closed shape."""
import numpy as np, json
from scipy import ndimage
A = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ai_duck"
occ = np.load(f"{A}/occ.npy"); meta = json.load(open(f"{A}/occ.json"))
R = int(round(0.035 / meta["vs"]))                 # fills gaps up to ~3 cm wide
r = np.arange(-R, R + 1)
ball = (r[:, None, None] ** 2 + r[None, :, None] ** 2 + r[None, None, :] ** 2) <= R * R
closed = ndimage.binary_closing(np.pad(occ, R + 2), structure=ball)[R + 2:-(R + 2), R + 2:-(R + 2), R + 2:-(R + 2)]
closed = ndimage.binary_fill_holes(closed)
sd = (ndimage.distance_transform_edt(~closed) - ndimage.distance_transform_edt(closed)) * meta["vs"]
np.save(f"{A}/closed_sdf.npy", sd.astype(np.float32))
print("closed: added voxels", int(closed.sum() - occ.sum()))
