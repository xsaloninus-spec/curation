# -*- coding: utf-8 -*-
"""仙人骑鹿镜 Cycles 渲染组图。Blender -b bm_xianren_qilu.blend --python render_bm.py"""
import bpy, math, os
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_bm"
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
sun("Front", (math.radians(180), 0, 0), 1.6, size=0.3)   # 正面补光，照亮镜面正视

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

# 镜体 z ∈ [-5, ~8]，半径 51.5，柄延至 y≈-136
shot("01_back", (0, -20, 300), (0, -8, 0.5), 55)           # 镜背正视
shot("02_front", (0, -20, -300), (0, -8, -1), 55)           # 镜面正视
shot("03_iso45", (160, -120, 220), (0, -30, 0), 58)         # 45°（含柄）
shot("04_side", (250, -40, 40), (0, -40, -1), 60)          # 侧视（柄连接）
shot("05_deity", (-26, 4, 70), (-26, 4, 1), 80)            # 仙人近景（正俯视，充满画面）
shot("06_deer", (0, -35, 85), (-3, -22, 2), 68)            # 鹿近景
shot("07_attendant_scene", (55, -35, 120), (18, -8, 1), 62) # 侍者与山石流水
shot("08_handle", (60, -160, 70), (0, -115, -2), 62)       # 镜柄
shot("09_full_side", (0, -280, 30), (0, -60, -1), 55)      # 全形侧视
print("ALL_SHOTS_DONE")
