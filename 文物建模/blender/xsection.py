# Cross-section at plane y=0 -> dump points to CSV
import bpy, sys
import numpy as np
from mathutils import Vector

glb, out = sys.argv[sys.argv.index("--")+1], sys.argv[sys.argv.index("--")+2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.data.objects if o.type=='MESH']
deg = bpy.context.evaluated_depsgraph_get()

pts = []
for o in objs:
    oe = o.evaluated_get(deg); m = oe.to_mesh(); mw = oe.matrix_world
    verts = np.empty(len(m.vertices)*3); m.vertices.foreach_get("co", verts); verts = verts.reshape(-1,3)
    wv = (np.array(mw) @ np.vstack([verts.T, np.ones(len(verts))]))[:3].T
    for p in m.polygons:
        iv = p.vertices; vv = wv[iv]; n = len(iv)
        for i in range(n):
            a = vv[i]; b = vv[(i+1)%n]
            if (a[1] < 0) != (b[1] < 0):
                t = a[1]/(a[1]-b[1])
                pt = a + t*(b-a)
                pts.append((pt[2], pt[0]))
    oe.to_mesh_clear()

pts = np.array(pts)
np.savetxt(out, pts, delimiter=",")
print("XSEC pts", len(pts))
