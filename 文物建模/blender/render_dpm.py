# -*- coding: utf-8 -*-
"""蓝珐琅喜字把镜 Cycles 渲染组图。Blender -b dpm_xizi_handmirror.blend --python render_dpm.py"""
import bpy, math, os
from mathutils import Vector

OUT = "/Users/wangyaomin/Desktop/策展/文物建模/renders_blender_dpm"
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
sun("Face", (math.pi, 0, math.radians(-25)), 1.8)  # 补镜面一侧（-Z）光照

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

# 镜身中心 (0,0,0) R62.5，柄与流苏沿 -Y 至约 -310
shot("01_front_45", (270, -310, -290), (0, -145, -10), 45)  # 完整器物 45°（镜面朝前，仿馆方角度）
shot("02_mirror_face", (0, -30, -240), (0, -10, -4), 55)   # 镜面正视
shot("03_back_decor", (0, -10, 200), (0, 0, 2), 60)        # 镜背（卍字地/囍/八宝）
shot("04_rim_detail", (70, -70, -120), (45, -30, -4), 62)  # 镜圈描金（正面）
shot("05_neck_detail", (70, -170, 90), (0, -105, 0), 62)   # 染牙+珊瑚珠连接件
shot("06_handle", (90, -255, 85), (0, -235, 0), 58)        # 柄与金箍
shot("07_tassel", (95, -335, 30), (0, -300, -25), 55)      # 流苏与穗尾珊瑚珠
shot("08_side", (470, -200, 15), (0, -150, -5), 40)        # 侧视全形
print("ALL_SHOTS_DONE")
