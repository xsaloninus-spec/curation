# -*- coding: utf-8 -*-
"""蟠螭纹透雕镜 Cycles 渲染组图（含双层分离展示）。Blender -b met_23_120_5.blend --python render_met.py"""
import bpy, math, os
from math import sin, cos, pi
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_met"
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

# 透雕层 z ∈ [0, ~8]，镜体 z ∈ [-6.2, -3]
shot("01_back", (0, 0, 320), (0, 0, 1), 55)               # 镜背正视（透雕层）
shot("02_front", (0, 0, -320), (0, 0, -4.5), 55)          # 镜面正视
shot("03_iso45", (200, -200, 260), (0, 0, -1), 58)         # 45°
shot("04_side", (300, 0, 30), (0, 0, -2.5), 65)            # 侧视（双层间距）
shot("05_openwork_detail", (60, -60, 120), (15, -15, 2), 62)   # 蟠螭透雕近景
shot("06_knob_scroll", (0, 0, 90), (0, 0, 2), 68)          # 中央环钮
shot("07_scroll_band", (0, 95, 190), (0, 62, -2), 62)      # 卷云纹带与外缘
# 双层分离展示：仅古代透雕层
def set_plate_visible(v):
    for o in sc.objects:
        if o.name.startswith(("01_", "02_", "07_", "08_")):
            o.hide_render = not v
set_plate_visible(False)
shot("08_layer_ancient_only", (200, -200, 260), (0, 0, 0), 58)
set_plate_visible(True)
# 仅镜体
for o in sc.objects:
    if not o.name.startswith(("01_", "02_", "07_", "08_")) and o.type not in ('CAMERA', 'LIGHT'):
        o.hide_render = True
shot("09_layer_plate_only", (200, -200, 260), (0, 0, -4), 58)
for o in sc.objects:
    if o.type not in ('CAMERA', 'LIGHT'):
        o.hide_render = False
# 分解：双层拉开（透雕层上移展示）
import bpy as _b
for o in sc.objects:
    if o.name.startswith(("03_", "04_", "05_", "06_")) and o.parent is None:
        o.location.z += 40
shot("10_exploded_layers", (260, -260, 240), (0, 0, 15), 60)
print("ALL_SHOTS_DONE")
