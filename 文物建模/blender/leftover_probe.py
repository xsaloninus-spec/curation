# What remains above x threshold on given side?
import bpy, sys, math
import numpy as np
from mathutils import Vector

glb, side, xth = sys.argv[sys.argv.index("--")+1], float(sys.argv[sys.argv.index("--")+2]), float(sys.argv[sys.argv.index("--")+3])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
o = [o for o in bpy.data.objects if o.type=='MESH' and 'cap' not in o.name][0]
M = o.matrix_world
me = o.data
import bmesh
bm = bmesh.new(); bm.from_mesh(me)
buckets = {}
for f in bm.faces:
    c = M @ f.calc_center_median()
    n = (M.to_3x3() @ f.normal).normalized()
    r = math.hypot(c.y, c.z)
    if c.x * side > xth and r < 0.43:
        key = (round(n.x*side, 1), int(r // 0.05))
        buckets[key] = buckets.get(key, 0) + 1
for k in sorted(buckets):
    print("LEFT side", "+" if side>0 else "-", "x>", xth, "norm_bucket", k[0], "r_bucket", k[1]*0.05, "faces", buckets[k])
print("LEFT done")
