# -*- coding: utf-8 -*-
"""
宋代仙人骑鹿铜镜 —— 大英博物馆 1990,0531.8
镜面直径 103 mm、连柄总长 188 mm、291 g（馆方）。
镜柄无官方侧面照，柄形为简洁直柄推定；人物身份不定名（馆方仅称 a deity mounted on a deer）。
构图按照片：左侧有背光仙人、右侧侍者、下方鹿、上方松枝、右下山石流水。
Blender 4.5 headless: Blender -b --factory-startup --python build_bm_mirror.py
"""
import bpy
import math, random
from math import sin, cos, pi

random.seed(1990)

# ---------------- 参数（mm） ----------------
R = 51.5                 # 镜体半径（馆方 Φ103）
T = 4.5                  # 镜体厚（推定）
RIM_W = 3.0              # 镜缘宽（照片描摹）
KNOB_R = 5.5             # 中央钮半径（照片描摹）
HANDLE_W = 11.0          # 柄宽（推定）
HANDLE_T = 4.0           # 柄厚（推定）
HANDLE_L = 188 - 103     # 柄长 = 85（总长馆方 − 直径馆方）
RELIEF = 1.2             # 浮雕基准高

BRONZE = None
MIRROR = None

def curve_tube(points, bevel, name, mat, cyclic=False):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'; cu.resolution_u = 2
    cu.bevel_depth = bevel; cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1)
    sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    if mat: cu.materials.append(mat)
    return ob

def add_sphere(r, loc, name, mat, scale=(1, 1, 1), seg=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=10, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def mat_bronze():
    m = bpy.data.materials.new("Bronze_Song_graybrown")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.7
    bs.inputs["Roughness"].default_value = 0.55
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.11, 0.095, 0.075, 1)   # 暗灰褐
    ramp.color_ramp.elements[1].color = (0.30, 0.26, 0.20, 1)    # 浅褐凸起
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.35
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_mirror_face():
    m = bpy.data.materials.new("MirrorFace_Song")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.42, 0.41, 0.38, 1)
    bs.inputs["Metallic"].default_value = 0.92
    bs.inputs["Roughness"].default_value = 0.35
    return m

# ---------------- 1. 镜体 / 镜面 / 镜缘 ----------------
def build_disc():
    seg = 128
    verts, faces = [], []
    for z in (0.0, -T):
        for i in range(seg):
            th = 2 * pi * i / seg
            verts.append((R * cos(th), R * sin(th), z))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((i, ni, seg + ni, seg + i))
    c1 = len(verts); verts.append((0, 0, 0))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((c1, ni, i))
    c2 = len(verts); verts.append((0, 0, -T))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((c2, seg + i, seg + ni))
    me = bpy.data.meshes.new("disc_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(BRONZE)
    ob = bpy.data.objects.new("01_镜体_Disc", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    # 镜面
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R - 0.8, depth=0.25,
                                        location=(0, 0, -T - 0.02))
    mf = bpy.context.object; mf.name = "02_镜面_MirrorFace"
    mf.data.materials.append(MIRROR)
    for p in mf.data.polygons: p.use_smooth = True
    # 镜缘（凸缘）
    bpy.ops.mesh.primitive_torus_add(major_radius=R - RIM_W / 2, minor_radius=RIM_W / 2 + 0.4,
        major_segments=96, minor_segments=12, location=(0, 0, 0.4))
    rim = bpy.context.object; rim.name = "03_镜缘_Rim"
    rim.scale.z = 0.75
    bpy.ops.object.transform_apply(scale=True)
    rim.data.materials.append(BRONZE)
    bpy.ops.object.shade_smooth()

def build_knob():
    add_sphere(KNOB_R, (0, 0, KNOB_R * 0.55), "04_中央钮_Knob", BRONZE,
                scale=(1, 1, 0.72))

# ---------------- 2. 仙人（左，有背光，坐姿） ----------------
def build_deity():
    x0, y0 = -26.0, 4.0
    z = RELIEF
    # 背光环
    pts = [(x0 + 10 * cos(2 * pi * i / 48), y0 + 2 + 10 * sin(2 * pi * i / 48), z + 2.2)
           for i in range(49)]
    curve_tube(pts, 0.7, "05_仙人背光_Halo", BRONZE)
    # 头 + 高髻
    add_sphere(2.6, (x0, y0 + 2, z + 2.6), "05_仙人首", BRONZE, scale=(0.9, 0.9, 1.05))
    add_sphere(1.2, (x0, y0 + 2, z + 5.2), "05_仙人髻", BRONZE)
    # 身（宽袍，坐姿）：躯干椭圆 + 下摆展开
    add_sphere(4.6, (x0, y0, z + 1.2), "05_仙人袍身", BRONZE, scale=(1.05, 0.8, 0.9))
    add_sphere(3.4, (x0 - 1.5, y0 - 2.6, z + 0.7), "05_仙人袍摆", BRONZE, scale=(1.5, 0.75, 0.6))
    # 双臂前伸（捧物姿态，袖口以曲线概括）
    curve_tube([(x0 + 2.5, y0 + 0.5, z + 2.2), (x0 + 6.5, y0 + 1.5, z + 1.6)],
               1.1, "05_仙人臂", BRONZE)
    # 衣纹
    for k in range(3):
        curve_tube([(x0 - 2.5 + k * 2.2, y0 - 1.5, z + 2.2),
                    (x0 - 3.2 + k * 2.2, y0 - 3.4, z + 0.6)],
                   0.45, f"05_仙人衣纹{k}", BRONZE)

# ---------------- 3. 侍者（右，立姿拱手） ----------------
def build_attendant():
    x0, y0 = 26.0, 3.0
    z = RELIEF
    add_sphere(2.2, (x0, y0 + 1, z + 6.2), "07_侍者首", BRONZE)
    add_sphere(3.6, (x0, y0, z + 3.4), "07_侍者袍身", BRONZE, scale=(0.9, 0.75, 1.15))
    add_sphere(2.6, (x0, y0 - 0.6, z + 0.8), "07_侍者袍摆", BRONZE, scale=(1.15, 0.8, 0.55))
    # 拱手前伸
    curve_tube([(x0 - 1.8, y0 + 0.5, z + 4.6), (x0 - 6.0, y0 + 0.9, z + 4.2)],
               0.95, "07_侍者臂上", BRONZE)
    curve_tube([(x0 - 1.2, y0 - 0.6, z + 3.6), (x0 - 5.4, y0 + 0.3, z + 4.0)],
               0.95, "07_侍者臂下", BRONZE)
    for k in range(2):
        curve_tube([(x0 - 1.2 + k * 1.6, y0 - 1.2, z + 2.6),
                    (x0 - 1.8 + k * 1.6, y0 - 2.2, z + 0.7)],
                   0.42, f"07_侍者衣纹{k}", BRONZE)

# ---------------- 4. 鹿（中下，立姿面向左，有鞍鞯与双角） ----------------
def build_deer():
    x0, y0 = -2.0, -22.0
    z = RELIEF
    # 躯干（水平）
    add_sphere(4.6, (x0, y0, z + 3.0), "06_鹿身", BRONZE, scale=(1.45, 0.72, 0.85))
    # 颈 + 首（向左）
    curve_tube([(x0 - 4.6, y0 + 0.2, z + 3.6), (x0 - 7.2, y0 + 0.8, z + 6.2)],
               1.5, "06_鹿颈", BRONZE)
    add_sphere(1.9, (x0 - 8.0, y0 + 1.0, z + 6.6), "06_鹿首", BRONZE, scale=(1.35, 0.8, 0.9))
    curve_tube([(x0 - 9.4, y0 + 0.9, z + 6.3), (x0 - 10.6, y0 + 0.6, z + 6.0)],
               0.55, "06_鹿吻", BRONZE)
    # 双角（分叉）
    for s in (1, -1):
        base = (x0 - 7.6, y0 + 1.0 + s * 0.8, z + 7.6)
        tip = (x0 - 8.4 + s * 1.2, y0 + 1.2 + s * 2.6, z + 11.4)
        curve_tube([base, tip], 0.5, f"06_鹿角干{s}", BRONZE)
        for j, t in enumerate((0.35, 0.65)):
            bx = base[0] + (tip[0] - base[0]) * t
            by = base[1] + (tip[1] - base[1]) * t
            bz = base[2] + (tip[2] - base[2]) * t
            curve_tube([(bx, by, bz), (bx - 1.6, by + s * 0.6, bz + 1.4)],
                       0.35, f"06_鹿角杈{s}_{j}", BRONZE)
    # 四肢
    for j, (lx, ly) in enumerate(((-3.2, -1.4), (-1.4, 1.5), (2.6, -1.4), (4.0, 1.3))):
        curve_tube([(x0 + lx, y0 + ly, z + 2.2), (x0 + lx + 0.4, y0 + ly, z)],
                   0.62, f"06_鹿足{j}", BRONZE)
    # 尾
    curve_tube([(x0 + 6.4, y0, z + 3.4), (x0 + 7.8, y0 - 0.4, z + 2.2)],
               0.55, "06_鹿尾", BRONZE)
    # 鞍鞯（背上方块毯）
    add_sphere(2.2, (x0 + 0.6, y0, z + 5.6), "06_鹿鞍", BRONZE, scale=(1.5, 0.95, 0.4))
    # 缰绳（首至鞍）
    curve_tube([(x0 - 8.6, y0 + 0.8, z + 6.0), (x0 - 4.0, y0 + 1.6, z + 5.4),
                (x0 + 0.2, y0 + 1.4, z + 5.6)], 0.3, "06_缰绳", BRONZE)

# ---------------- 5. 松枝（上方） ----------------
def build_pine():
    # 主干斜伸
    trunk = [(-16, 40, RELIEF), (-10, 36, RELIEF + 1.2), (-2, 33, RELIEF + 2.0),
             (8, 32, RELIEF + 2.2), (16, 33, RELIEF + 1.8)]
    curve_tube(trunk, 1.1, "08_松干", BRONZE)
    # 枝 + 针叶簇（小球排布）
    branches = [((-10, 36, RELIEF + 1.6), (-16, 30, RELIEF + 2.2)),
                ((-2, 33, RELIEF + 2.4), (2, 27, RELIEF + 2.8)),
                ((8, 32, RELIEF + 2.6), (15, 27, RELIEF + 3.0)),
                ((14, 33, RELIEF + 2.2), (22, 29, RELIEF + 2.6))]
    for j, (p0, p1) in enumerate(branches):
        curve_tube([p0, p1], 0.6, f"08_松枝{j}", BRONZE)
        for k in range(5):
            t = 0.3 + 0.16 * k
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t - 0.8
            zz = p0[2] + (p1[2] - p0[2]) * t
            add_sphere(0.85, (x, y, zz), f"08_针叶{j}_{k}", BRONZE, scale=(1.4, 0.7, 0.5), seg=10)

# ---------------- 6. 山石与流水（右下） ----------------
def build_rock_wave():
    # 山岩（多面体块）
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=4.4,
                                          location=(30, -26, RELIEF + 1.4))
    rock = bpy.context.object; rock.name = "09_山岩_Rock"
    rock.scale = (1.15, 0.9, 0.75)
    bpy.ops.object.transform_apply(scale=True)
    rock.data.materials.append(BRONZE)
    # 岩棱
    curve_tube([(27, -23, RELIEF + 3.2), (30, -26, RELIEF + 4.2), (33.5, -28, RELIEF + 2.6)],
               0.5, "09_岩棱", BRONZE)
    # 流水（右下三组波纹弧线，收在镜缘内：极端点 r≈46.6 < 48.5）
    for j in range(3):
        yy = -30 - j * 2.4
        pts = []
        for i in range(17):
            t = i / 16
            pts.append((10 + 20 * t, yy + 1.2 * sin(t * 3 * pi + j), RELIEF - 0.2))
        curve_tube(pts, 0.5, f"09_流水{j}", BRONZE)
    # 左下小石
    add_sphere(2.2, (-24, -30, RELIEF + 0.4), "09_小石", BRONZE, scale=(1.3, 0.9, 0.55), seg=12)

# ---------------- 7. 镜柄（推定：简洁直柄，与镜体相接） ----------------
def build_handle():
    y0 = -R - HANDLE_L / 2 + 1.5
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y0, -T / 2))
    h = bpy.context.object; h.name = "10_镜柄_推定_Handle"
    h.dimensions = (HANDLE_W, HANDLE_L, HANDLE_T)
    bpy.ops.object.transform_apply(scale=True)
    bevel = h.modifiers.new("soft", 'BEVEL'); bevel.width = 1.4; bevel.segments = 3
    h.data.materials.append(BRONZE)
    # 柄端收圆
    add_sphere(HANDLE_W / 2 - 0.6, (0, y0 - HANDLE_L / 2 + 1.2, -T / 2), "10_柄端", BRONZE,
               scale=(1.0, 0.8, HANDLE_T / HANDLE_W))
    # 柄上 simple 纹饰线（推定，两道弦纹）
    for k in range(2):
        yy = y0 + 18 + k * 26
        curve_tube([(-HANDLE_W / 2 + 1.2, yy, -T / 2 + HANDLE_T / 2 + 0.05),
                    (HANDLE_W / 2 - 1.2, yy, -T / 2 + HANDLE_T / 2 + 0.05)],
                   0.5, f"10_柄饰线{k}", BRONZE)

def main():
    global BRONZE, MIRROR
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    BRONZE = mat_bronze()
    MIRROR = mat_mirror_face()
    build_disc()
    build_knob()
    build_deity()
    build_deer()
    build_attendant()
    build_pine()
    build_rock_wave()
    build_handle()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/bm_xianren_qilu.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
