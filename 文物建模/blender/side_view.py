# Side elevation render: camera on +Y looking -Y, orthographic on XZ profile
# Usage: Blender -b --factory-startup --python side_view.py -- <glb> <out.png>
import bpy, sys, math
from mathutils import Vector

glb, out = sys.argv[sys.argv.index("--")+1], sys.argv[sys.argv.index("--")+2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

mn = Vector((1e18,)*3); mx = Vector((-1e18,)*3)
for o in bpy.data.objects:
    if o.type == 'MESH':
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
center = (mn + mx) / 2
size = mx - mn
diag = size.length
print("SIDE bbox", tuple(round(v,5) for v in mn), tuple(round(v,5) for v in mx))

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.render.resolution_x = 800
scene.render.resolution_y = 500
scene.render.resolution_percentage = 100
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.05,0.05,0.05,1)

key = bpy.data.objects.new("Key", bpy.data.lights.new("K",'AREA'))
key.data.energy = 600*diag; key.data.size = diag
bpy.context.collection.objects.link(key)
key.location = center + Vector((0.3*diag, 0.8*diag, 0.6*diag))
key.rotation_euler = (center - key.location).normalized().to_track_quat('-Z','Y').to_euler()

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("C"))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = max(size.x, size.z) * 1.12
bpy.context.collection.objects.link(cam)
scene.camera = cam
cam.location = center + Vector((0, diag*1.8, 0))
cam.rotation_euler = ((center - cam.location).normalized().to_track_quat('-Z','Y')).to_euler()
# -Y is screen-left? keep default; render both sides not needed
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("SIDE done", out)
