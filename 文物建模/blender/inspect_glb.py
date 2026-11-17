# -*- coding: utf-8 -*-
"""导入 Tripo GLB，渲染 ±X/±Y/±Z 六个正交视图，用于判断纹饰面/镜面朝向。"""
import bpy, os, math
from mathutils import Vector

ROOT = "/Users/wangyaomin/Desktop/策展/文物建模"
OUT = os.path.join(ROOT, "inspect")
os.makedirs(OUT, exist_ok=True)

MODELS = [
    ("qijia", "qijia_seven_point_tripo.glb"),
    ("met", "met_23_120_5_tripo.glb"),
    ("tlv", "han_tlv_guiju_mirror.glb"),
    ("bm", "bm_xianren_qilu_tripo.glb"),
    ("dpm", "dpm_xizi_bajing_tripo.glb"),
]

AXES = [("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)),
        ("-Y", (0, -1, 0)), ("+Z", (0, 0, 1)), ("-Z", (0, 0, -1))]

for tag, fn in MODELS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    sc.render.resolution_x = 600
    sc.render.resolution_y = 600
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.look = 'AgX - Medium High Contrast'

    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.25, 0.27, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0

    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, fn))

    # 合并包围盒
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    nmesh = 0
    for o in sc.objects:
        if o.type == 'MESH':
            nmesh += 1
            for c in o.bound_box:
                wc = o.matrix_world @ Vector(c)
                lo = Vector(map(min, lo, wc)); hi = Vector(map(max, hi, wc))
    center = (lo + hi) / 2
    size = hi - lo
    maxdim = max(size.x, size.y, size.z)
    print(f"MODEL {tag}: meshes={nmesh} size=({size.x:.3f},{size.y:.3f},{size.z:.3f})")

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data); sc.collection.objects.link(cam)
    sc.camera = cam
    cam_data.type = 'ORTHO'
    cam_data.clip_end = maxdim * 10 + 10

    for aname, ax in AXES:
        d = sun = None
        ld = bpy.data.lights.new("L", 'SUN'); ld.energy = 4.0; ld.angle = 0.2
        lo_ = bpy.data.objects.new("L", ld); sc.collection.objects.link(lo_)
        lo_.rotation_euler = Vector(ax).to_track_quat('-Z', 'Y').to_euler()
        cam_data.ortho_scale = maxdim * 1.15
        cam.location = center + Vector(ax) * (maxdim * 2.0)
        dirv = center - cam.location
        cam.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(OUT, f"{tag}_{aname}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(lo_, do_unlink=True)
        bpy.data.lights.remove(ld, do_unlink=True)
    print("INSPECT_OK", tag)
print("ALL_DONE")
