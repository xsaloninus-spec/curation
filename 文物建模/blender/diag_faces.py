# Diagnose GLB: bounding box + orthographic renders of both X faces
# Usage: Blender -b --factory-startup --python diag_faces.py -- <glb_path> <out_prefix>
import bpy, sys, math, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path, out_prefix = argv[0], argv[1]

# wipe default scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

# combined world bbox
mn = Vector((1e18, 1e18, 1e18)); mx = Vector((-1e18, -1e18, -1e18))
tris = 0
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
        tris += len(o.data.polygons)
print("DIAG bbox_min", tuple(round(v,6) for v in mn))
print("DIAG bbox_max", tuple(round(v,6) for v in mx))
print("DIAG size", tuple(round(v,6) for v in (mx-mn)))
print("DIAG volume", round((mx.x-mn.x)*(mx.y-mn.y)*(mx.z-mn.z), 8))
print("DIAG npoly", tris)
print("DIAG nmat", len(bpy.data.materials), "nimg", len(bpy.data.images), "nobj", len(bpy.data.objects))
for o in bpy.data.objects:
    print("DIAG obj", o.name, o.type, tuple(round(v,4) for v in o.dimensions))

center = (mn + mx) / 2
size = mx - mn
diag = size.length

# camera looking down +X (sees the -X face) and down -X (sees +X face)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = 600
scene.render.resolution_y = 600
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
world = bpy.data.worlds.new("W"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05,0.05,0.05,1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# big area lights for readable face
key = bpy.data.objects.new("Key", bpy.data.lights.new("Key",'AREA'))
key.data.energy = 800*diag; key.data.shape='DISK'; key.data.size = diag*0.8
bpy.context.collection.objects.link(key)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill",'AREA'))
fill.data.energy = 400*diag; fill.data.size = diag*1.5
bpy.context.collection.objects.link(fill)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = max(size.y, size.z) * 1.15
bpy.context.collection.objects.link(cam)
scene.camera = cam

# view +X: camera at +X side looking toward -X  (this shows +X face)
def shoot(sign, suffix):
    off = diag * 1.6
    cam.location = center + Vector((sign*off, 0, 0))
    # look toward center: -Z of camera to direction (center - cam.location)
    d = (center - cam.location).normalized()
    q = d.to_track_quat('-Z','Y')
    cam.rotation_euler = q.to_euler()
    key.location = center + Vector((sign*off*0.9, off*0.6, off*0.5))
    key.rotation_euler = (center - key.location).normalized().to_track_quat('-Z','Y').to_euler()
    fill.location = center + Vector((-sign*off*0.5, -off*0.7, off*0.3))
    fill.rotation_euler = (center - fill.location).normalized().to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = f"{out_prefix}_{suffix}.png"
    bpy.ops.render.render(write_still=True)

shoot(1, "posX")   # camera on +X side
shoot(-1, "negX")
print("DIAG done")
