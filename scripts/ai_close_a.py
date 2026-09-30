"""Blender: export an inside/outside voxel grid of the AI duck (rest pose, local coords)."""
import bpy, numpy as np, openvdb, json
A = "/home/yousefmsm1/Desktop/blender/bataa_ad/assets/ai_duck"
VS = 0.003
bpy.ops.wm.open_mainfile(filepath=f"{A}/ai_duck_rigged.blend")
me = bpy.data.objects["AI_Duck"].data
co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
tri = np.empty(len(me.polygons) * 3, np.int32); me.polygons.foreach_get("vertices", tri); tri = tri.reshape(-1, 3)
lo = co.min(0) - 0.05
g = openvdb.FloatGrid.createLevelSetFromPolygons(((co - lo) / VS).astype(np.float32), triangles=tri.astype(np.uint32),
                                                 halfWidth=40.0)
shape = tuple(np.ceil((co.max(0) + 0.05 - lo) / VS).astype(int))
arr = np.zeros(shape, np.float32)
g.copyToArray(arr, ijk=(0, 0, 0))
np.save(f"{A}/occ.npy", arr < 0)
json.dump({"lo": lo.tolist(), "vs": VS, "shape": [int(v) for v in shape]}, open(f"{A}/occ.json", "w"))
print("OCC", shape, int((arr < 0).sum()))
