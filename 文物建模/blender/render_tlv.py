# -*- coding: utf-8 -*-
"""TLV mirror — Cycles render shot set. Run:
Blender -b tlv_mirror_1995_301.blend --python render_tlv.py"""
import bpy, math, sys, os
from math import sin, cos, pi
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender"
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

# 世界：中性灰
w = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.055, 0.055, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

# 灯光
def sun(name, rot, energy=4.0, size=0.15):
    d = bpy.data.lights.new(name, 'SUN'); d.energy = energy; d.angle = size
    o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
    o.rotation_euler = rot
    return o

sun("Key", (math.radians(28), math.radians(-18), math.radians(35)), 3.2)
sun("Fill", (math.radians(50), math.radians(20), math.radians(-140)), 2.4)

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
cam_data.lens = 60

def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def shot(name, pos, target, lens=60):
    import os
    if os.path.exists(f"{OUT}/{name}.png"):
        print("SKIP", name); return
    cam.location = pos
    cam_data.lens = lens
    look_at(cam, target)
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("SHOT_OK", name)

R = 95.0
# 镜背正对（模型背面在 +Z）
shot("01_back_top", (0, 0, 340), (0, 0, 0), 55)
# 8 环绕（背面向镜头，倾角 30°）
for i in range(8):
    a = 2 * pi * i / 8
    d = 330
    shot(f"02_orbit_{i}", (d * sin(a) * 0.5, -d * cos(a) * 0.5, 300), (0, 0, 0), 58)
# 镜面（-Z 微凸面）
shot("03_front", (0, 0, -340), (0, 0, 0), 55)
# 侧视
shot("04_side", (360, 0, 10), (0, 0, 0), 70)
# 特写：镜钮、TLV 象限、纹带、四神
shot("05_knob", (0, 0, 90), (0, 0, 2), 70)
shot("06_tlv_quadrant", (60, -60, 120), (30, -30, 0), 62)
shot("07_bands", (0, 70, 150), (0, 66, 0), 62)
shot("08_spirits", (0, 0, 170), (0, 60, 0), 62)
print("ALL_SHOTS_DONE")
