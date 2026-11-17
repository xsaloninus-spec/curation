# Probe X-extreme surfaces: are both faces relief, or one flat?
# Usage: Blender -b --factory-startup --python probe_faces.py -- <glb>
import bpy, sys
from mathutils import Vector

glb = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

mn = Vector((1e18,)*3); mx = Vector((-1e18,)*3)
mesh_objs = [o for o in bpy.data.objects if o.type=='MESH']
for o in mesh_objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
thick = mx.x - mn.x
band = 0.02 * thick
print(f"PROBE thickness {thick:.4f} band {band:.4f}")

deg = bpy.context.evaluated_depsgraph_get()
for side, lo, hi in [("Xmax", mx.x-band, mx.x), ("Xmin", mn.x, mn.x+band)]:
    xs=[]; cnt=0
    nfaces = 0
    for o in mesh_objs:
        oe = o.evaluated_get(deg)
        m = oe.to_mesh()
        mw = oe.matrix_world
        for v in m.vertices:
            wx = (mw @ v.co).x
            if lo <= wx <= hi:
                cnt += 1; xs.append(wx)
        oe.to_mesh_clear()
    if xs:
        xs.sort()
        print(f"PROBE {side}: verts {cnt}, x mean {sum(xs)/len(xs):.5f} "
              f"range {xs[0]:.5f}..{xs[-1]:.5f} spread {xs[-1]-xs[0]:.5f} "
              f"({(xs[-1]-xs[0])/thick*100:.1f}% of thickness)")
    else:
        print(f"PROBE {side}: no verts in band")

# also count faces by dominant normal direction per side
for o in mesh_objs:
    pass
print("PROBE done")
