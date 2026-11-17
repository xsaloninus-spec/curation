# -*- coding: utf-8 -*-
"""TLV 镜 1995.301 Cycles 验收组图（8 帧）。机位参照 render_qijia.py。
Blender -b tlv_mirror_1995_301.blend --python render_tlv.py"""
import bpy, math, os
from math import sin, cos, pi
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_tlv"
os.makedirs(OUT, exist_ok=True)

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 96
sc.cycles.use_denoising = True
sc.cycles.device = 'CPU'
sc.render.resolution_x = 900
sc.render.resolution_y = 900
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.look = 'AgX - Medium High Contrast'

w = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

def sun(name, rot, energy=3.2, size=0.15):
    d = bpy.data.lights.new(name, 'SUN'); d.energy = energy; d.angle = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
    o.rotation_euler = rot
    return o

sun("Key", (math.radians(28), math.radians(-18), math.radians(35)), 3.4)
sun("Fill", (math.radians(50), math.radians(20), math.radians(-140)), 2.2)

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam

def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def shot(name, pos, target, lens=60):
    if os.path.exists(f"{OUT}/{name}.png"):
        print("SKIP", name); return
    cam.location = pos
    cam_data.lens = lens
    look_at(cam, target)
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT_OK", name)

# 主体 z∈[-12, 8]，半径 95
shot("01_back", (0, 0, 320), (0, 0, 0), 55)                # 背正视（整镜背）
bl2 = bpy.data.lights.new("FrontFill", 'AREA')
bl2.energy = 90000; bl2.shape = 'DISK'; bl2.size = 150
bl2_ob = bpy.data.objects.new("FrontFill", bl2)
bl2_ob.location = (0, 0, -140); bl2_ob.rotation_euler = (0, pi, 0)
sc.collection.objects.link(bl2_ob)
shot("02_front", (0, 0, -320), (0, 0, 0), 55)              # 镜面正视
bpy.data.objects.remove(bl2_ob, do_unlink=True)
shot("03_iso45", (180, -180, 240), (0, 0, -1), 58)         # 45°
shot("04_side", (340, 0, 20), (0, 0, -2), 65)              # 侧视（薄片）
shot("05_knob", (0, 0, 70), (0, 0, 3), 70)                 # 圆钮近景
shot("06_pattern", (0, 0, 150), (0, 40, 0.5), 62)          # 纹饰近景（方框+八乳+四神）
shot("07_rim", (0, 95, 170), (0, 78, 0.8), 62)             # 缘带三圈近景
shot("08_hero", (140, -110, 230), (0, 0, 0), 55)           # 整镜 45° 展示
print("ALL_SHOTS_DONE")
