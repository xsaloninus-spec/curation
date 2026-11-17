# -*- coding: utf-8 -*-
"""Tripo 参照用干净正交图：镜背 / 镜面正视。
Cycles 64 采样，方形 900px，深灰中性背景，均匀柔光，无地面无阴影杂物。
Blender -b tlv_mirror_1995_301.blend --python render_tlv_clean.py"""
import bpy, math, os
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/references"

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 64
sc.cycles.use_denoising = True
sc.cycles.device = 'CPU'
sc.render.resolution_x = 900
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.film_transparent = False
sc.view_settings.look = 'AgX - Medium High Contrast'

w = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.09, 0.09, 0.10, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

def sun(name, rot, energy=2.6, size=0.6):
    d = bpy.data.lights.new(name, 'SUN'); d.energy = energy; d.angle = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
    o.rotation_euler = rot
    return o

sun("SoftKey", (math.radians(20), math.radians(-12), math.radians(30)), 2.6, 0.6)
sun("SoftFill", (math.radians(-35), math.radians(25), math.radians(160)), 1.4, 0.8)

cam_data = bpy.data.cameras.new("CleanCam")
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 200.0   # Φ190 镜体 + 边距
cam = bpy.data.objects.new("CleanCam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

def clean_shot(name, cam_z, target_z, world_color=None):
    if world_color:
        w.node_tree.nodes["Background"].inputs[0].default_value = world_color
    cam.location = (0, 0, cam_z)
    d = Vector((0, 0, target_z)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("CLEAN_OK", name)

# 镜背纹饰正视（+Z 方向看）
clean_shot("tlv_clean_back", 260, 0.0)
# 镜面正视（-Z 方向看）：提亮世界 + 正面大片柔光
soft = bpy.data.lights.new("FrontSoft", 'AREA')
soft.energy = 120000; soft.shape = 'DISK'; soft.size = 180
soft_ob = bpy.data.objects.new("FrontSoft", soft)
soft_ob.location = (0, 0, -90); soft_ob.rotation_euler = (0, math.pi, 0)
sc.collection.objects.link(soft_ob)
clean_shot("tlv_clean_front", -260, -1.0, world_color=(0.50, 0.50, 0.53, 1))
print("ALL_CLEAN_DONE")
