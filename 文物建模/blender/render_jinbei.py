# -*- coding: utf-8 -*-
"""金背镜 Cycles 渲染组图。Blender -b jinbei_mirror_xian.blend --python render_jinbei.py"""
import bpy, math, os
from math import sin, cos, pi
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_jinbei"
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

# 主体在 z ∈ [-7, 8]，半径 98.5
shot("01_back", (0, 0, 300), (0, 0, 0.5), 55)          # 镜背正视
shot("02_front", (0, 0, -300), (0, 0, -3), 55)          # 镜面正视
shot("03_iso45", (150, -150, 210), (0, 0, 0), 58)      # 45°
shot("04_side", (300, 0, 20), (0, 0, 0), 65)           # 侧视（双层）
shot("05_section", (200, 0, 60), (60, 0, 0), 85)        # 侧近景（胎/壳关系）
shot("06_knob_pair", (0, 0, 80), (0, 0, 3), 68)        # 钮+双兽
shot("07_inner_beasts", (55, -55, 110), (25, -25, 1), 62)  # 内区瑞兽
shot("08_outer_grape", (0, 80, 160), (0, 70, 1), 62)    # 外区葡萄/鸟
shot("09_edge", (0, 0, 200), (60, 60, 0.5), 62)         # 菱花边缘
# 分解：隐藏金壳（含所有金部件）→ 只剩铜胎
def set_gold_visible(v):
    for o in sc.objects:
        if o.name.startswith(("02_金背壳", "03_", "04_", "05_", "06_", "07_", "08_", "09_", "10_")):
            o.hide_render = not v
set_gold_visible(False)
shot("10_explode_bronze_only", (150, -150, 210), (0, 0, 0), 58)
set_gold_visible(True)
shot("11_explode_gold_only", (150, -150, 210), (0, 0, 0), 58)
print("ALL_SHOTS_DONE")
