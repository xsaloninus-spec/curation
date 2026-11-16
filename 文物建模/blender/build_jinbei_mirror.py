# -*- coding: utf-8 -*-
"""
唐代金背瑞兽葡萄镜 —— 西安博物院（2002 西安灞桥马家沟村唐墓出土）
八出菱花形铜胎 + 独立金背壳双层结构。直径 197 mm（馆方/展览资料）。
Blender 4.5 headless: Blender -b --factory-startup --python build_jinbei_mirror.py
"""
import bpy
import math
from math import sin, cos, pi
from mathutils import Vector

# ---------------- 参数（mm） ----------------
RMAX = 98.5            # 最大半径（197 直径）
RMIN = 87.0            # 瓣间内凹半径
BODY_T = 7.0           # 铜胎厚度（推定）
SHELL_T = 1.5          # 金壳厚度（推定）
KNOB_R = 10.0          # 镜钮半径
KNOB_H = 5.0           # 镜钮高（推定）
RELIEF_H = 3.0         # 高浮雕高度（推定）
R_IN_BEAST = 38.0      # 内区瑞兽半径
R_OUT = 72.0           # 外区葡萄/鸟半径
R_BUD = 86.0           # 四叶花苞半径
GOLD = None
BRONZE = None

def outline_r(theta):
    """八出菱花形轮廓：8 个花瓣，自然弧度"""
    return RMIN + (RMAX - RMIN) * ((1 + cos(8 * theta)) / 2) ** 0.8

def petal_angle(i):
    return 2 * pi * i / 8

def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def smooth_bevel(obj, amount=0.3, segments=2):
    b = obj.modifiers.new("soft_edge", 'BEVEL')
    b.width = amount; b.segments = segments

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

def spiral_pts(cx, cy, r0, r1, turns, z, steps=36, phase=0.0):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = phase + 2 * pi * turns * t
        r = r0 + (r1 - r0) * t
        pts.append((cx + r * cos(a), cy + r * sin(a), z))
    return pts

def add_sphere(r, loc, name, mat, scale=(1, 1, 1), seg=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=12, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def mat_gold():
    m = bpy.data.materials.new("Gold_repousse")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Roughness"].default_value = 0.28
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.55, 0.36, 0.10, 1)
    ramp.color_ramp.elements[1].color = (0.95, 0.74, 0.32, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.25
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_bronze_dark():
    m = bpy.data.materials.new("Bronze_body")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = 0.5
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.0
    noise.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.07, 0.055, 0.035, 1)
    ramp.color_ramp.elements[1].color = (0.26, 0.17, 0.08, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    bump.inputs["Distance"].default_value = 0.4
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

# ---------------- 1. 八出菱花形铜胎体 ----------------
def build_body():
    seg, rings = 160, 12
    # 顶面（镜面，微凸）+ 背面 z=0 + 侧壁
    top = []
    for j in range(rings + 1):
        t = j / rings
        row = []
        for i in range(seg):
            th = 2 * pi * i / seg
            r = t * outline_r(th)
            z = -BODY_T + 1.6 * (1 - t ** 2)   # 中心微凸
            row.append((r * cos(th), r * sin(th), z))
        top.append(row)
    verts, faces = [], []
    for row in top: verts += row
    # 背面圈
    back_start = len(verts)
    for i in range(seg):
        th = 2 * pi * i / seg
        r = outline_r(th)
        verts.append((r * cos(th), r * sin(th), 0.0))
    # 顶面格
    for j in range(rings):
        for i in range(seg):
            ni = (i + 1) % seg
            a = j * seg + i; b = j * seg + ni
            c = (j + 1) * seg + ni; d = (j + 1) * seg + i
            faces.append((a, b, c, d))
    # 侧壁（顶面外圈→背面外圈）
    outer_top = rings * seg
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((outer_top + i, back_start + i,
                      back_start + ni, outer_top + ni))
    # 底面扇（z=0 平面，中心点）
    center_idx = len(verts)
    verts.append((0, 0, 0.0))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((center_idx, back_start + ni, back_start + i))
    me = bpy.data.meshes.new("body_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(BRONZE)
    ob = bpy.data.objects.new("01_铜胎体_LobedBronzeBody", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    return ob

# ---------------- 2. 金背壳 ----------------
def build_shell():
    seg, rings = 160, 8
    inset = 2.0
    verts, faces = [], []
    # 壳背（贴合铜胎 z=0→SHELL_T）+ 壳面（纹饰基底 z=SHELL_T）
    for z in (0.0, SHELL_T):
        for j in range(rings + 1):
            t = j / rings
            for i in range(seg):
                th = 2 * pi * i / seg
                r = t * (outline_r(th) - inset)
                verts.append((r * cos(th), r * sin(th), z))
    layer = (rings + 1) * seg
    for j in range(rings):
        for i in range(seg):
            ni = (i + 1) % seg
            a = j * seg + i; b = j * seg + ni
            c = layer + (j + 1) * seg + ni; d = layer + (j + 1) * seg + i
            faces.append((a, b, c, d))          # 底（贴铜胎）
            faces.append((layer + j * seg + i, layer + (j) * seg + ni,
                          layer + (j + 1) * seg + ni, layer + (j + 1) * seg + i))
    outer = rings * seg
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((outer + i, outer + ni, layer + outer + ni, layer + outer + i))
    me = bpy.data.meshes.new("shell_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(GOLD)
    ob = bpy.data.objects.new("02_金背壳_GoldShell", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    return ob

# ---------------- 3. 中央镜钮 + 追尾双兽 ----------------
def build_knob_pair():
    z0 = SHELL_T
    parts = []
    # 镜钮：扁球
    parts.append(add_sphere(KNOB_R, (0, 0, z0 + KNOB_H * 0.55), "03_镜钮_Knob", GOLD,
                            scale=(1, 1, KNOB_H / KNOB_R * 0.62)))
    # 双兽：两条 S 形追逐曲线 + 首尾相衔
    for s, nm in ((1, "A"), (-1, "B")):
        pts = []
        for i in range(30):
            t = i / 29
            a = s * (0.6 + t * 1.55 * pi)         # 环绕约 280°
            r = 16 + 3.5 * sin(t * pi)            # 身长起伏
            pts.append((r * cos(a), r * sin(a), z0 + 2.2 + 1.2 * sin(t * pi)))
        parts.append(curve_tube(pts, 1.5, f"04_追尾双兽_{nm}", GOLD))
        # 兽首（首端）
        hx, hy = pts[-1][0], pts[-1][1]
        parts.append(add_sphere(2.4, (hx, hy, pts[-1][2]), f"04_兽首_{nm}", GOLD,
                                scale=(1.25, 0.9, 0.9)))
        # 角/耳
        parts.append(curve_tube([(hx, hy, pts[-1][2] + 1),
                                   (hx + 1.2 * s, hy + 1.8, pts[-1][2] + 2.2)],
                                  0.5, f"04_兽角_{nm}", GOLD))
        # 尾（尾端卷起）
        tx, ty = pts[0][0], pts[0][1]
        parts.append(curve_tube([(tx, ty, pts[0][2]),
                                 (tx * 0.82, ty * 0.82, pts[0][2] + 1.8)],
                                0.55, f"04_兽尾_{nm}", GOLD))
    return parts

# ---------------- 4. 内区八瑞兽 + 缠枝蔓草 ----------------
def beast_glyph(cx, cy, ang, scale, name, pose):
    """姿态化四足瑞兽：身 + 首 + 四肢 + 尾；pose ∈ walk|crouch|climb|leap"""
    z = SHELL_T + 1.4
    L = 9 * scale
    dx, dy = cos(ang), sin(ang)
    px, py = -dy, dx
    pts = []
    for i in range(16):
        t = i / 15
        along = (t - 0.5) * L
        amp = {'walk': 1.2, 'crouch': 2.2, 'climb': 2.8, 'leap': 3.4}[pose]
        sway = amp * sin(t * pi) * (1 if pose != 'crouch' else 0.5)
        lift = {'walk': 0.3, 'crouch': -0.6, 'climb': 1.8 * t, 'leap': 2.2 * sin(t * pi)}[pose]
        pts.append((cx + dx * along + px * sway,
                    cy + dy * along + py * sway, z + lift))
    parts = [curve_tube(pts, 1.25 * scale, name + "_身", GOLD)]
    hx, hy, hz = pts[-1]
    parts.append(add_sphere(1.9 * scale, (hx, hy, hz + 0.4), name + "_首", GOLD,
                            scale=(1.3, 0.85, 0.85)))
    # 四肢
    for j, t in enumerate((0.25, 0.45, 0.6, 0.8)):
        bx = cx + dx * (t - 0.5) * L + px * 1.0 * scale * (1 if j % 2 else -1)
        by = cy + dy * (t - 0.5) * L + py * 1.0 * scale * (1 if j % 2 else -1)
        parts.append(curve_tube([(bx, by, z), (bx + 0.8 * dx, by + 0.8 * dy, z - 0.9)],
                                0.42 * scale, f"{name}_足{j}", GOLD))
    # 尾
    tx, ty, tz = pts[0]
    parts.append(curve_tube([(tx, ty, tz), (tx - dx * 2.4 * scale, ty - dy * 2.4 * scale, tz + 1.2)],
                            0.45 * scale, name + "_尾", GOLD))
    return parts

def build_inner_zone():
    parts = []
    poses = ('walk', 'crouch', 'climb', 'leap')
    for i in range(8):
        a = petal_angle(i) + pi / 8
        cx, cy = R_IN_BEAST * cos(a), R_IN_BEAST * sin(a)
        parts += beast_glyph(cx, cy, a + pi / 2 + (0.5 if i % 2 else -0.4),
                             0.95 + 0.12 * (i % 3), f"05_瑞兽_{i}", poses[i % 4])
        # 缠枝蔓草：瑞兽间螺旋连接
        a2 = petal_angle(i + 1) + pi / 8
        mx, my = 52 * cos((a + a2) / 2), 52 * sin((a + a2) / 2)
        parts.append(curve_tube(
            spiral_pts(mx, my, 1.0, 5.5, 1.15, SHELL_T + 0.9, phase=i),
            0.62, f"06_蔓草_{i}", GOLD))
    return parts

# ---------------- 5. 外区葡萄 / 鸟禽 / 四叶花苞 ----------------
def grape_bunch(cx, cy, z, name):
    parts = []
    offs = [(0, 0, 0), (1.7, 0.4, -0.5), (-1.6, 0.5, -0.4), (0.8, -1.5, -0.6),
            (-0.8, -1.4, -0.5), (0.2, -2.8, -1.0), (1.2, 1.5, -0.7), (-1.2, 1.4, -0.6)]
    for j, (ox, oy, oz) in enumerate(offs):
        parts.append(add_sphere(1.5, (cx + ox, cy + oy, z + oz),
                                f"{name}_果{j}", GOLD, scale=(1, 1, 0.92), seg=12))
    parts.append(curve_tube([(cx, cy + 1, z + 1.5), (cx, cy + 3.5, z + 3)],
                              0.5, f"{name}_蒂", GOLD))
    return parts

def bird_glyph(cx, cy, ang, name):
    z = SHELL_T + 1.6
    parts = []
    # 身
    parts.append(add_sphere(1.7, (cx, cy, z), name + "_身", GOLD, scale=(1.5, 0.85, 0.8), seg=16))
    # 首 + 喙
    hx, hy = cx + 2.2 * cos(ang), cy + 2.2 * sin(ang)
    parts.append(add_sphere(1.0, (hx, hy, z + 0.5), name + "_首", GOLD, seg=12))
    parts.append(curve_tube([(hx + 0.8 * cos(ang), hy + 0.8 * sin(ang), z + 0.5),
                               (hx + 2.0 * cos(ang), hy + 2.0 * sin(ang), z + 0.3)],
                              0.32, name + "_喙", GOLD))
    # 双翼
    for s in (1, -1):
        wx, wy = cx - 0.4 * cos(ang) - s * 1.4 * -sin(ang), cy - 0.4 * sin(ang) - s * 1.4 * cos(ang)
        pts = [(wx, wy, z + 0.6),
               (wx - 2.6 * sin(ang) * s - 1.2 * cos(ang), wy + 2.6 * cos(ang) * s - 1.2 * sin(ang), z + 1.6),
               (wx - 4.6 * sin(ang) * s - 3.0 * cos(ang), wy + 4.6 * cos(ang) * s - 3.0 * sin(ang), z + 1.2)]
        parts.append(curve_tube(pts, 0.55, f"{name}_翼{s}", GOLD))
    # 尾
    parts.append(curve_tube([(cx - 2.2 * cos(ang), cy - 2.2 * sin(ang), z),
                             (cx - 4.6 * cos(ang), cy - 4.6 * sin(ang), z + 0.9)],
                            0.5, name + "_尾", GOLD))
    return parts

def four_leaf_bud(cx, cy, ang, name):
    z = SHELL_T + 1.0
    parts = []
    for j in range(4):
        a = ang + j * pi / 2
        parts.append(add_sphere(1.6, (cx + 1.5 * cos(a), cy + 1.5 * sin(a), z),
                                f"{name}_瓣{j}", GOLD, scale=(1.5, 0.75, 0.5), seg=12))
    parts.append(add_sphere(0.9, (cx, cy, z + 0.3), name + "_心", GOLD, seg=12))
    return parts

def build_outer_zone():
    parts = []
    for i in range(8):
        a = petal_angle(i)
        # 葡萄串：瓣间偏左
        ga = a + pi / 16
        parts += grape_bunch(R_OUT * cos(ga), R_OUT * sin(ga), SHELL_T + 1.2, f"07_葡萄_{i}")
        # 鸟：瓣间偏右
        ba = a - pi / 16
        parts += bird_glyph((R_OUT + 4) * cos(ba), (R_OUT + 4) * sin(ba), ba + pi, f"08_鸟_{i}")
        # 四叶花苞：花瓣中心
        parts += four_leaf_bud(R_BUD * cos(a), R_BUD * sin(a), a, f"09_花苞_{i}")
        # 主枝蔓（从内区延伸至花苞）：5 点蜿蜒路径，不做直线分割
        pts = []
        for k in range(9):
            t = k / 8
            r = 20 + (R_BUD - 20) * t
            aa = a + 0.13 * sin(t * 2.6 * pi + i * 1.3) * sin(t * pi)
            zz = SHELL_T + 0.8 + 0.9 * sin(t * pi) * (0.6 + 0.4 * sin(i * 2.1))
            pts.append((r * cos(aa), r * sin(aa), zz))
        parts.append(curve_tube(pts, 0.7, f"06_主蔓_{i}", GOLD))
    return parts

# ---------------- 6. 随形边缘装饰 ----------------
def build_edge():
    parts = []
    seg = 160
    # 随形边框线（凸棱）
    pts = []
    for i in range(seg + 1):
        th = 2 * pi * i / seg
        r = outline_r(th) - 3.5
        pts.append((r * cos(th), r * sin(th), SHELL_T + 0.5))
    parts.append(curve_tube(pts, 0.65, "10_随形缘边", GOLD))
    # 缘上云纹勾：每瓣 3 组小卷
    for i in range(8):
        a = petal_angle(i)
        for j, da in enumerate((-0.10, 0, 0.10)):
            aa = a + da
            cx, cy = (RMAX - 8) * cos(aa), (RMAX - 8) * sin(aa)
            parts.append(curve_tube(
                spiral_pts(cx, cy, 0.5, 2.4, 1.05, SHELL_T + 0.7, phase=aa),
                0.5, f"10_缘云_{i}_{j}", GOLD))
    return parts

def main():
    global GOLD, BRONZE
    clean_scene()
    GOLD = mat_gold()
    BRONZE = mat_bronze_dark()
    build_body()
    build_shell()
    build_knob_pair()
    build_inner_zone()
    build_outer_zone()
    build_edge()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/jinbei_mirror_xian.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
