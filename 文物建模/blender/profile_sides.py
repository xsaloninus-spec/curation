# Radial mean profile (by area-weighted bins) of outward-facing surfaces on BOTH sides
import bpy, sys
import numpy as np
from mathutils import Vector

glb = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.data.objects if o.type=='MESH']
deg = bpy.context.evaluated_depsgraph_get()
centers=[]; normals=[]; areas=[]
for o in objs:
    oe = o.evaluated_get(deg); m = oe.to_mesh(); mw = oe.matrix_world
    n = len(m.polygons)
    cc = np.empty(n*3); nn = np.empty(n*3); aa = np.empty(n)
    m.polygons.foreach_get("center", cc); m.polygons.foreach_get("normal", nn); m.polygons.foreach_get("area", aa)
    cc = cc.reshape(-1,3).T; nn = nn.reshape(-1,3).T
    R = np.array(mw)[:3,:3]
    wc = (np.array(mw) @ np.vstack([cc, np.ones(n)]))[:3]
    wn = R @ nn
    centers.append(wc.T); normals.append(wn.T); areas.append(aa)
    oe.to_mesh_clear()
C = np.vstack(centers); N = np.vstack(normals); A = np.concatenate(areas)
r = np.sqrt(C[:,1]**2 + C[:,2]**2)

for sign, label in [(1, "+X"), (-1, "-X")]:
    mask = N[:,0]*sign > 0.5
    print(f"PROF side {label}: faces {mask.sum()}, area {A[mask].sum():.1f}")
    rr = r[mask]; xx = C[mask,0]; wA = A[mask]
    for lo, hi in [(0,0.1),(0.1,0.2),(0.2,0.3),(0.3,0.4),(0.4,0.5),(0.5,0.6)]:
        m2 = (rr>=lo)&(rr<hi)
        if m2.sum()>10:
            amean = np.average(xx[m2], weights=wA[m2])
            amin, amax = xx[m2].min(), xx[m2].max()
            print(f"PROF  r {lo:.1f}-{hi:.1f}: mean_x {amean:+.5f} range [{amin:+.5f},{amax:+.5f}] n={m2.sum()}")
print("PROF done")
