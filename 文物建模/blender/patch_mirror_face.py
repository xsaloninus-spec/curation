# Patch a Tripo mirror GLB: remove duplicated decoration on one face, add a
# shallow spherical-cap polished mirror surface seated inside the raised rim.
# Usage:
#   Blender -b --factory-startup --python patch_mirror_face.py -- <glb> <side> <a> <x_edge> <h> <mode>
#   side: +1 cover +X face, -1 cover -X face
#   a: cap chord radius (world units), x_edge: cap rim plane x (on mirror side),
#   h: cap sagitta (center height above rim plane)
#   mode: "cut" = delete mirror-side decoration field, then seat cap;
#         "over" = keep geometry, cap hovers above it (needs h large enough
#         to clear the highest bump under the cap)
#   optional x_deep: if given, the cap's back disk extends to this depth on the
#         mirror side (deep bowl), e.g. to preserve the bbox after deleting a
#         knob that used to be the extreme. Signed like x_edge (magnitude).
#   optional seal_r seal_x: build a sealing cone frustum from the cap rim
#         (radius a, at the cap rim plane) out to (seal_r, seal_x) on the
#         mirror side, to close the gap between cap edge and rim inner wall.
import bpy, bmesh, sys, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:]
glb, side, a, x_edge, h, mode = argv[0], float(argv[1]), float(argv[2]), float(argv[3]), float(argv[4]), argv[5]
x_deep = float(argv[6]) if len(argv) > 6 else None
seal_r = float(argv[7]) if len(argv) > 7 else None
seal_x = float(argv[8]) if len(argv) > 8 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
scene = bpy.context.scene

mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
assert len(mesh_objs) == 1, f"expected 1 mesh, got {len(mesh_objs)}"
obj = mesh_objs[0]
M = obj.matrix_world.copy()
print("PATCH obj", obj.name, "matrix", [round(v,4) for v in M.translation],
      "scale", [round(v,4) for v in M.to_scale()])

# ---------- 1. optionally delete decoration on mirror side ----------
me = obj.data
if mode == "cut":
    bm = bmesh.new()
    bm.from_mesh(me)
    r_thresh = a + 0.015   # delete field inside rim, keep rim annulus
    to_del = []
    for f in bm.faces:
        c = M @ f.calc_center_median()
        n = (M.to_3x3() @ f.normal).normalized()
        r = math.hypot(c.y, c.z)
        if n.x * side > 0.3 and c.x * side > -0.02 and r < r_thresh:
            to_del.append(f)
    print("PATCH deleting faces:", len(to_del))
    bmesh.ops.delete(bm, geom=to_del, context='FACES')
    # drop orphaned verts
    orph = [v for v in bm.verts if not v.link_faces]
    if orph:
        bmesh.ops.delete(bm, geom=orph, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
else:
    print("PATCH mode=over: keeping all geometry")

# ---------- 2. aged polished bronze material ----------
# small baked roughness/patina variation texture so it survives glTF export
rng = np.random.default_rng(7)
N = 256
yy, zz = np.mgrid[0:N, 0:N] / N
# low-frequency blotches via summed sines + fine grain
blotch = (np.sin(yy*23.7+1.3)*np.sin(zz*19.1+4.2) + np.sin(yy*9.3+0.5)*np.sin(zz*7.7+2.9)
          + np.sin((yy+zz)*31.1)) / 3.0   # -1..1
fine = rng.standard_normal((N, N)) * 0.5
rough = 0.155 + 0.045 * blotch + 0.018 * fine
rough = np.clip(rough, 0.10, 0.22)
patina = np.clip(0.5 + 0.5 * blotch + 0.15 * fine, 0, 1)

img_r = bpy.data.images.new("mirror_rough", width=N, height=N, alpha=False, float_buffer=False)
img_r.colorspace_settings.name = 'Non-Color'
px = np.repeat(rough[..., None], 3, axis=2).astype(np.float32)
px = np.dstack([px, np.ones((N, N, 1), dtype=np.float32)])
img_r.pixels.foreach_set(px.ravel())

# base color: warm grey bronze, darker in patina pits
lo = np.array([0.235, 0.215, 0.185]); hi = np.array([0.36, 0.335, 0.295])
col = lo[None, None, :] + (hi - lo)[None, None, :] * (1 - patina[..., None])
col = np.dstack([col, np.ones((N, N, 1), dtype=np.float32)])
img_c = bpy.data.images.new("mirror_patina", width=N, height=N, alpha=False)
img_c.pixels.foreach_set(col.astype(np.float32).ravel())

mat = bpy.data.materials.new("aged_polished_bronze_mirror")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Metallic"].default_value = 0.97
tex_r = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex_r.image = img_r
mat.node_tree.links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])
tex_c = mat.node_tree.nodes.new("ShaderNodeTexImage"); tex_c.image = img_c
mat.node_tree.links.new(tex_c.outputs["Color"], bsdf.inputs["Base Color"])
# textures read the cap's UV layer (YZ projection created below)
uv = mat.node_tree.nodes.new("ShaderNodeTexCoord")
mat.node_tree.links.new(uv.outputs["UV"], tex_r.inputs["Vector"])
mat.node_tree.links.new(uv.outputs["UV"], tex_c.inputs["Vector"])
mat.use_backface_culling = False

# ---------- 3. build cap (closed lens) ----------
s = side
Rs = (a*a + h*h) / (2*h)          # sphere radius
x_top = (x_edge + h) * s          # apex plane
x_back = (x_deep if x_deep is not None else x_edge - 0.004) * s   # back disk plane
RINGS, SEG = 64, 160

bm = bmesh.new()
front_rings = []
for i in range(1, RINGS + 1):
    r = a * i / RINGS
    sag = Rs - math.sqrt(max(Rs*Rs - r*r, 0.0))
    x = (x_edge + h - sag) * s
    ring = []
    for j in range(SEG):
        th = 2 * math.pi * j / SEG
        ring.append(bm.verts.new((x, r * math.cos(th), r * math.sin(th))))
    front_rings.append(ring)
fc = bm.verts.new((x_top * s, 0.0, 0.0))          # apex
bc = bm.verts.new((x_back, 0.0, 0.0))             # back center
back_rings = []
for i in range(1, RINGS + 1):
    r = a * i / RINGS
    ring = []
    for j in range(SEG):
        th = 2 * math.pi * j / SEG
        ring.append(bm.verts.new((x_back, r * math.cos(th), r * math.sin(th))))
    back_rings.append(ring)

# front faces (apex + between rings)
for j in range(SEG):
    bm.faces.new((fc, front_rings[0][j], front_rings[0][(j+1) % SEG]))
for i in range(RINGS - 1):
    r1, r2 = front_rings[i], front_rings[i+1]
    for j in range(SEG):
        bm.faces.new((r1[j], r2[j], r2[(j+1) % SEG], r1[(j+1) % SEG]))
# back faces
for j in range(SEG):
    bm.faces.new((bc, back_rings[0][(j+1) % SEG], back_rings[0][j]))
for i in range(RINGS - 1):
    r1, r2 = back_rings[i], back_rings[i+1]
    for j in range(SEG):
        bm.faces.new((r1[(j+1) % SEG], r2[(j+1) % SEG], r2[j], r1[j]))
# outer wall
for j in range(SEG):
    bm.faces.new((front_rings[-1][j], back_rings[-1][j],
                  back_rings[-1][(j+1) % SEG], front_rings[-1][(j+1) % SEG]))

# optional sealing cone from cap rim to rim inner wall
if seal_r is not None and seal_x is not None:
    sx = seal_x * s
    outer = []
    for j in range(SEG):
        th = 2 * math.pi * j / SEG
        outer.append(bm.verts.new((sx, seal_r * math.cos(th), seal_r * math.sin(th))))
    for j in range(SEG):
        bm.faces.new((front_rings[-1][j], outer[j],
                      outer[(j+1) % SEG], front_rings[-1][(j+1) % SEG]))
    print(f"PATCH seal cone r {a}->{seal_r}, x {x_edge*s:+.5f}->{sx:+.5f}")

bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
cap_me = bpy.data.meshes.new("mirror_cap")
bm.to_mesh(cap_me)
bm.free()
# UV layer: project (y,z)/a*0.5+0.5 so textures have stable coords
uvl = cap_me.uv_layers.new(name="UVMap")
for poly in cap_me.polygons:
    for li in poly.loop_indices:
        v = cap_me.vertices[cap_me.loops[li].vertex_index].co
        uvl.data[li].uv = (v.y / (2*a) + 0.5, v.z / (2*a) + 0.5)
cap_me.materials.append(mat)
for p in cap_me.polygons:
    p.use_smooth = True
cap = bpy.data.objects.new("mirror_cap", cap_me)
scene.collection.objects.link(cap)

# quick sanity: cap apex/rim x
print(f"PATCH cap a={a} rim_x={x_edge*s:+.5f} apex_x={x_top*s:+.5f} back_x={x_back:+.5f}")

# ---------- 4. export ----------
bpy.ops.export_scene.gltf(
    filepath=glb,
    export_format='GLB',
    export_image_format='AUTO',
    export_animations=False,
    export_yup=True,
)
print("PATCH exported", glb)
