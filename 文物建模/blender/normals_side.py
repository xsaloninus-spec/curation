# Determine decorated side via face normals; print radial profile of the back surface
import bpy, sys
import numpy as np
from mathutils import Vector

glb = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

objs = [o for o in bpy.data.objects if o.type=='MESH']
deg = bpy.context.evaluated_depsgraph_get()

# gather world-space face centers + normals from one combined mesh
centers = []; normals = []; areas = []
for o in objs:
    oe = o.evaluated_get(deg)
    m = oe.to_mesh()
    mw = oe.matrix_world
    n = len(m.polygons)
    cc = np.empty(n*3); nn = np.empty(n*3); aa = np.empty(n)
    m.polygons.foreach_get("center", cc); m.polygons.foreach_get("normal", nn); m.polygons.foreach_get("area", aa)
    cc = cc.reshape(-1,3).T; nn = nn.reshape(-1,3).T
    R = np.array(mw)[:3,:3]
    # proper normal transform (uniform scale assumed)
    Rn = R / np.linalg.det(R) if abs(np.linalg.det(R))>1e-12 else R
    wc = (np.array(mw) @ np.vstack([cc, np.ones(n)]))[:3]
    wn = R @ nn
    centers.append(wc.T); normals.append(wn.T); areas.append(aa)
    oe.to_mesh_clear()
C = np.vstack(centers); N = np.vstack(normals); A = np.concatenate(areas)

nx = N[:,0]
pos = (nx > 0.3).sum()*A[nx>0.3].sum(); neg = (nx < -0.3).sum()*A[nx<-0.3].sum()
print(f"NORM face area with |nx|>0.3: +X {pos:.3f}, -X {neg:.3f}")

# radial profile: for faces whose normal mostly faces the MINOR side (say -X if decoration is +X)
minor_sign = -1 if pos > neg else 1
mask = nx*minor_sign > 0.5
r = np.sqrt(C[mask,1]**2 + C[mask,2]**2)
x = C[mask,0]*minor_sign  # height outward on minor side
print(f"NORM minor side {'-X' if minor_sign<0 else '+X'}, faces {mask.sum()}")
order = np.argsort(r)
# print deciles
for q in range(0, 101, 10):
    idx = order[min(len(order)-1, int(len(order)*q/100))]
    print(f"NORM r={r[idx]:.4f} x={x[idx]:.5f}")
# overall extremes on minor side
print(f"NORM minor side x range {x.min():.5f}..{x.max():.5f}, r range {r.min():.4f}..{r.max():.4f}")
print("NORM done")
