# -*- coding: utf-8 -*-
"""检测 Tripo GLB 纹饰面朝 ±X 哪一侧，输出对照渲染图。
Blender -b --factory-startup --python check_faces.py"""
import bpy, os, sys
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/face_checks"
os.makedirs(OUT, exist_ok=True)
MODELS = ["qijia_seven_point_tripo", "met_23_120_5_tripo", "bm_xianren_qilu_tripo"]

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 420
sc.render.resolution_y = 420
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'

w = bpy.data.worlds.new("W") if not bpy.data.worlds else bpy.data.worlds[0]
sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.4, 0.42, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

for name in MODELS:
    path = f"/Users/wangyaomin/Desktop/策展/文物建模/{name}.glb"
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in imported if o.type == 'MESH']
    # 世界包围盒
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in meshes:
        for c in o.bound_box:
            wc = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, wc)); mx = Vector(map(max, mx, wc))
    center = (mn + mx) / 2
    size = max((mx - mn).length, 1e-6)
    for tag, pos in (("posX", (center.x + size * 0.9, center.y, center.z)),
                     ("negX", (center.x - size * 0.9, center.y, center.z))):
        d = center - Vector(pos)
        cam.location = pos
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam_data.clip_end = size * 4
        sc.render.filepath = f"{OUT}/{name}_{tag}.png"
        bpy.ops.render.render(write_still=True)
        print("CHECK_SHOT", name, tag)
    # 删除导入的对象
    for o in imported:
        bpy.data.objects.remove(o, do_unlink=True)
print("ALL_CHECKS_DONE")
