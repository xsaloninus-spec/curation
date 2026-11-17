# Fine radial profile of the +X outer surface (max x per r bin) for cap seating
import bpy, sys
import numpy as np
from mathutils import Vector

glb, sign = sys.argv[sys.argv.index("--")+1], float(sys.argv[sys.argv.index("--")+2])
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
mask = N[:,0]*sign > 0.3
rr = r[mask]; xx = C[mask,0]; wA = A[mask]
print(f"FINE side {'+' if sign>0 else '-'}X faces {mask.sum()}")
for i in range(0, 50):
    lo = i*0.01
    m2 = (rr>=lo)&(rr<lo+0.01)
    if m2.sum()>5:
        print(f"FINE r {lo:.2f}-{lo+0.01:.2f}: max_x {xx[m2].max():+.5f} mean_x {np.average(xx[m2],weights=wA[m2]):+.5f} min_x {xx[m2].min():+.5f} n={m2.sum()}")
print("FINE done")
