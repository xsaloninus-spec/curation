# Histogram of vertex x-coords + manifold check
import bpy, sys
from mathutils import Vector
from collections import Counter

glb = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

mn = Vector((1e18,)*3); mx = Vector((-1e18,)*3)
objs = [o for o in bpy.data.objects if o.type=='MESH']
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
thick = mx.x - mn.x
print(f"HIST thickness {thick:.4f}")

import numpy as np
deg = bpy.context.evaluated_depsgraph_get()
allx = []
total_verts = 0
for o in objs:
    oe = o.evaluated_get(deg)
    m = oe.to_mesh()
    mw = oe.matrix_world
    n = len(m.vertices)
    total_verts += n
    co = np.empty(n*3)
    m.vertices.foreach_get("co", co)
    co = co.reshape(-1,3)
    wco = (np.array(mw) @ np.vstack([co.T, np.ones(n)]))[:3].T
    allx.append(wco[:,0])
    oe.to_mesh_clear()
xs = np.concatenate(allx)
print(f"HIST total verts {total_verts}")
hist, edges = np.histogram(xs, bins=20, range=(mn.x, mx.x))
for i,h in enumerate(hist):
    print(f"HIST bin {edges[i]:+.4f}..{edges[i+1]:+.4f}: {h} ({h/len(xs)*100:.1f}%)")

# manifold check on first big mesh
o = max(objs, key=lambda o: len(o.data.vertices))
edge_count = Counter()
for p in o.data.polygons:
    for e in p.edge_keys:
        edge_count[e] += 1
boundaries = sum(1 for v in edge_count.values() if v == 1)
nonmanifold = sum(1 for v in edge_count.values() if v > 2)
print(f"HIST manifold: edges {len(edge_count)}, boundary {boundaries}, nonmanifold {nonmanifold}")
print("HIST done")
