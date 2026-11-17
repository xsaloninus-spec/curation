# -*- coding: utf-8 -*-
"""v3 验收渲染：背视、45°、侧视、钮部、缘带、镜面、展示图。"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
RENDERS = ROOT / "renders"
RENDERS.mkdir(exist_ok=True)
BLEND = ROOT / "tlv_1995_301_v3.blend"


def setup_scene():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"

    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.036, 0.038, 1)
    bg.inputs[1].default_value = 1.0

    # 背景板
    bpy.ops.mesh.primitive_plane_add(size=1.6, location=(-0.45, 0, 0))
    plate = bpy.context.object
    plate.rotation_euler = (0, math.radians(90), 0)
    m = bpy.data.materials.new("Backdrop")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.16, 0.16, 0.165, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    plate.data.materials.append(m)

    def area(name, loc, rot, size, energy, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, "AREA")
        d.shape = "RECTANGLE"
        d.size, d.size_y = size
        d.energy = energy
        d.color = color
        ob = bpy.data.objects.new(name, d)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = rot
        return ob

    # 主光：左上
    key = area("Key", (0.55, 0.15, 0.55), (math.radians(-38), math.radians(-28), math.radians(160)), (0.5, 0.5), 60)
    key.rotation_euler = (math.radians(-42), math.radians(-30), math.radians(160))
    area("Fill", (0.45, -0.45, 0.1), (math.radians(-75), 0, math.radians(115)), (0.6, 0.6), 14, (0.85, 0.9, 1.0))
    area("Rim", (0.05, 0.1, 0.65), (math.radians(-110), 0, math.radians(180)), (0.7, 0.25), 24)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return cam


def aim(cam, loc, target=(0, 0, 0), up="Y"):
    cam.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", up).to_euler()


def render(name, loc, target=(0, 0, 0), res=900, samples=128, lens=85):
    scene = bpy.context.scene
    cam = scene.camera
    cam.data.lens = lens
    aim(cam, loc, target)
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.cycles.samples = samples
    scene.render.filepath = str(RENDERS / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)


def main():
    setup_scene()
    # 背视：镜背朝 +X，相机在 +X 侧；世界 +Z 为上
    render("01_back", (0.56, 0.0, 0.0), lens=88, samples=160)
    render("02_iso", (0.42, 0.33, 0.22), lens=90)
    render("03_side", (0.02, 0.58, 0.03), lens=100)
    render("04_knob", (0.115, 0.02, 0.045), target=(0.015, 0.0, 0.0), lens=120, res=900)
    render("05_rim", (0.10, 0.055, 0.03), target=(0.0, 0.04, 0.0), lens=135, res=900)
    render("06_front", (-0.56, 0.0, 0.0), lens=88)
    render("07_hero", (0.38, 0.28, 0.20), lens=80)
    print("RENDERS_OK")


if __name__ == "__main__":
    main()
