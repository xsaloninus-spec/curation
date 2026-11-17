# -*- coding: utf-8 -*-
"""七角星纹镜 Cycles 渲染组图。Blender -b qijia_mirror.blend --python render_qijia.py"""
import bpy, math, os
from math import sin, cos, pi
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_qijia"
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

def sun(name, rot, energy=3.2, size=0.12):
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

# 主体 z ∈ [-2.75, 3.5]，半径 45
shot("01_back", (0, 0, 260), (0, 0, 0.3), 55)              # 镜背正视（七角星）
shot("02_front", (0, 0, -260), (0, 0, -0.3), 55)           # 镜面正视
shot("03_iso45", (130, -130, 190), (0, 0, 0), 58)          # 45°
shot("04_side", (220, 0, 12), (0, 0, -0.5), 65)             # 侧视（薄片）
shot("05_knob", (0, 0, 55), (0, 0, 1), 70)                  # 残钮近景
shot("06_star", (0, 0, 140), (0, 0, 0.3), 62)              # 七角星+斜线纹
shot("07_holes_cord", (0, 82, 46), (0, 41, -0.5), 70)     # 镜缘双孔与绳痕
# 展示状态 B：打开木柄+系绳
for o in sc.objects:
    if o.name.startswith(("09_", "10_")):
        o.hide_render = False
# 镜背(-Z)无光，临时加一盏从 -Z 方向打来的补光
bl = sun("BackFill", (math.radians(180), 0, math.radians(20)), 3.2)
shot("08_restoration_handle", (140, 90, -170), (0, 50, -3), 58)
bpy.data.objects.remove(bl, do_unlink=True)
for o in sc.objects:
    if o.name.startswith(("09_", "10_")):
        o.hide_render = True
# 状态 A：仅铜镜本体（默认即此状态，已拍 01–07）
print("ALL_SHOTS_DONE")
