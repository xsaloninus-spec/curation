# Where is the -X extreme? Profile of -X-facing surface by radius on the ORIGINAL
import bpy, sys, math
import numpy as np
from mathutils import Vector

glb = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
o = [o for o in bpy.data.objects if o.type=='MESH'][0]
M = o.matrix_world
me = o.data
import bmesh
bm = bmesh.new(); bm.from_mesh(me)

# collect world face data
data = []
for f in bm.faces:
    c = M @ f.calc_center_median()
    n = (M.to_3x3() @ f.normal).normalized()
    r = math.hypot(c.y, c.z)
    data.append((c.x, n.x, r, c.y, c.z))
bm.free()
d = np.array(data)
x, nx, r = d[:,0], d[:,1], d[:,2]

print(f"PROBE2 global x range {x.min():.5f}..{x.max():.5f}")
ext = d[x < -0.19]
print(f"PROBE2 faces with x<-0.19: {len(ext)}")
if len(ext):
    print(f"PROBE2   their r range {ext[:,2].min():.4f}..{ext[:,2].max():.4f}, "
          f"nx range {ext[:,1].min():.3f}..{ext[:,1].max():.3f}")
    # r histogram of these extreme faces
    for lo in np.arange(0, 0.51, 0.05):
        m2 = (ext[:,2]>=lo)&(ext[:,2]<lo+0.05)
        if m2.sum(): print(f"PROBE2   r {lo:.2f}-{lo+0.05:.2f}: {int(m2.sum())} faces, x min {ext[m2,0].min():.5f}")

# -X-facing surface profile (nx < -0.5), min x per r bin -> rim shape
mask = nx < -0.5
print("PROBE2 -X-facing (nx<-0.5) profile:")
for i in range(0, 50):
    lo = i*0.01
    m2 = mask & (r>=lo) & (r<lo+0.01)
    if m2.sum() > 5:
        print(f"PROBE2 r {lo:.2f}-{lo+0.01:.2f}: min_x {x[m2].min():+.5f} mean_x {x[m2].mean():+.5f} max_x {x[m2].max():+.5f} n={int(m2.sum())}")
print("PROBE2 done")
