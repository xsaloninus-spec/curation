# -*- coding: utf-8 -*-
"""
汉代 TLV 规矩镜 —— Cleveland Museum of Art 1995.301 结构化解构重建
Procedural 8-part layered model, dimensions from museum data:
  D=190mm, center thickness 12mm, rim thickness 7mm.
Blender 4.5 headless:  Blender -b --factory-startup --python build_tlv_mirror.py
"""
import bpy
import math
from math import sin, cos, pi
from mathutils import Vector

# ---------------- 参数（mm） ----------------
R = 95.0                 # 半径
CENTER_T = 12.0          # 中心总厚
RIM_T = 7.0              # 缘厚
BACK_Z = 0.0             # 镜背基准面
RELIEF_H = 2.0           # 主纹饰凸起高度
R_KNOB = 11.0            # 镜钮半径
H_KNOB = 6.0             # 镜钮高
SQ_HALF = 24.0           # 内方框半边长
SQ_W = 4.0               # 方框边宽
R_TLV = 42.0             # TLV 符号分布半径
BAR_W = 3.6              # TLV 条宽
R_NIPPLE_RING1 = SQ_HALF * math.sqrt(2)   # 角钉半径
NIPPLE_R = 3.0
R_SPIRIT = 66.0          # 四神分布半径
R_SERR_IN, R_SERR_OUT = 80.0, 84.0   # 三角纹带
R_CLOUD_IN, R_CLOUD_OUT = 84.5, 92.0 # 卷云纹带
R_RIM_PLAIN = 92.0       # 平缘起点

BRONZE = None
PATINA = None

# ---------------- 基础工具 ----------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        pass

def mat_bronze():
    """青铜 + 绿锈：Principled 金属 + Noise 锈斑"""
    m = bpy.data.materials.new("Bronze_patina")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = 0.42
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.7
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.10, 0.13, 0.09, 1)    # 绿锈暗部
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = (0.30, 0.21, 0.11, 1)    # 青铜亮部
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    bump.inputs["Distance"].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_dark():
    m = bpy.data.materials.new("Bronze_recess")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.10, 0.075, 0.04, 1)
    bs.inputs["Metallic"].default_value = 0.8
    bs.inputs["Roughness"].default_value = 0.55
    return m

def smooth_bevel(obj, amount=0.35, segments=2):
    bev = obj.modifiers.new("soft_edge", 'BEVEL')
    bev.width = amount; bev.segments = segments

def add_cyl(r, h, z, name, mat, verts=128):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h,
                                       location=(0, 0, z + h / 2))
    o = bpy.context.object; o.name = name
    if mat: o.data.materials.append(mat)
    return o

def add_box(loc, scale, name, mat, bevel=0.3):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name
    o.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    if bevel: smooth_bevel(o, bevel, 2)
    return o

def add_sphere(r, loc, name, mat, scale_z=1.0, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=16, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    o.scale.z = scale_z
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def curve_tube(points, bevel, name, mat, cyclic=False, res=2):
    """折线/样条凸起：矩形断面用 bevel_depth 圆形近似，加 bevel 分辨率"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.resolution_u = res
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1)
    sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    if mat: cu.materials.append(mat)
    return ob

def rect_bar(p0, p1, w, h, z, name, mat, bevel=0.3):
    """任意方向的矩形凸条：显式世界坐标顶点，避免 transform_apply 原点陷阱"""
    x0, y0 = p0; x1, y1 = p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    L = math.hypot(x1 - x0, y1 - y0) + w
    a = math.atan2(y1 - y0, x1 - x0)
    ca, sa = cos(a), sin(a)
    hl, hw = L / 2, w / 2
    # 局部角点（含 bevel 由倒角修改器处理，这里先建矩形）
    corners = [(-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw)]
    verts = []
    for zz in (z, z + h):
        for (lx, ly) in corners:
            verts.append((mx + lx * ca - ly * sa,
                          my + lx * sa + ly * ca, zz))
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if bevel:
        smooth_bevel(ob, min(bevel, h * 0.4, w * 0.4), 2)
    return ob

def spiral(cx, cy, r0, r1, turns, z, name, mat, bevel=0.8, steps=40):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = 2 * pi * turns * t
        r = r0 + (r1 - r0) * t
        pts.append((cx + r * cos(a), cy + r * sin(a), z))
    return curve_tube(pts, bevel, name, mat)

def polar(angle_deg, r):
    a = math.radians(angle_deg)
    return (r * cos(a), r * sin(a))

# ---------------- 1. 镜体（车削剖面） ----------------
def build_body():
    # 绕 Z 旋转剖面：背面 z=0 平；正面中心 -12、缘部 -7（微凸镜面）
    seg = 96
    prof = [(0, -CENTER_T), (R * 0.55, -CENTER_T + 1.2),
            (R * 0.85, -RIM_T - 1.2), (R, -RIM_T), (R, 0), (0, 0)]
    # 中心背面下沉 1.5mm 容纳钮座
    verts = []
    for i in range(len(prof)):
        verts.append(prof[i])
    mesh = bpy.data.meshes.new("body_mesh")
    mesh.from_pydata([(x, y, z) for x, z in verts for y in (0.0,)], [], [])
    # 用 screw 方式更简单：直接旋转剖面
    bpy.ops.object.select_all(action='DESELECT')
    # 用 lathe：构造 (r, z) 对
    pairs = prof
    rings = len(pairs)
    verts = []
    for i in range(seg):
        a = 2 * pi * i / seg
        for (r, z) in pairs:
            verts.append((r * cos(a), r * sin(a), z))
    faces = []
    for i in range(seg):
        ni = (i + 1) % seg
        for j in range(rings - 1):
            faces.append((i * rings + j, ni * rings + j,
                          ni * rings + j + 1, i * rings + j + 1))
    mesh = bpy.data.meshes.new("body_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(PATINA)
    ob = bpy.data.objects.new("01_镜体_MirrorBody", mesh)
    bpy.context.scene.collection.objects.link(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob

# ---------------- 2. 镜钮 ----------------
def build_knob():
    # 半球钮 + 横穿穿孔（boolean；刀具用显式世界坐标网格）
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24,
        radius=R_KNOB, location=(0, 0, BACK_Z + 1))
    knob = bpy.context.object
    knob.name = "02_镜钮_Knob"
    knob.scale.z = H_KNOB / R_KNOB
    bpy.ops.object.transform_apply(scale=True)
    knob.data.materials.append(PATINA)
    # 切掉 z<0 的下半：刀具显式网格 span z[-22, 0]
    cut = add_box((0, 0, -11), (44, 44, 22), "knob_cut", None, bevel=0)
    bpy.context.view_layer.objects.active = knob
    mod = knob.modifiers.new("cut_base", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'; mod.object = cut
    bpy.ops.object.modifier_apply(modifier="cut_base")
    bpy.data.objects.remove(cut, do_unlink=True)
    # 穿孔 Ø4（沿 X，显式圆柱刀具）
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=2.0, depth=44,
        location=(0, 0, BACK_Z + H_KNOB * 0.5), rotation=(0, pi / 2, 0))
    hole = bpy.context.object
    bpy.context.view_layer.objects.active = knob
    mod = knob.modifiers.new("pierce", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'; mod.object = hole
    bpy.ops.object.modifier_apply(modifier="pierce")
    bpy.data.objects.remove(hole, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    knob.select_set(True)
    bpy.context.view_layer.objects.active = knob
    bpy.ops.object.shade_smooth()
    return knob

# ---------------- 3. 内方框 + 4. 十二乳钉 ----------------
def build_square_nipples():
    z = BACK_Z; h = RELIEF_H
    parts = []
    # 方框四边（边长 48）
    s = SQ_HALF
    edges = [((-s, -s), ( s, -s)), (( s, -s), ( s,  s)),
             (( s,  s), (-s,  s)), ((-s,  s), (-s, -s))]
    for i, (p0, p1) in enumerate(edges):
        parts.append(rect_bar(p0, p1, SQ_W, h, z, f"03_方框_edge{i}", PATINA))
    # 十二乳钉：4 角 + 8 边点（每边三等分）
    n = 0
    corner = SQ_HALF
    for (x, y) in [(corner, corner), (corner, -corner),
                   (-corner, -corner), (-corner, corner)]:
        parts.append(add_sphere(NIPPLE_R, (x, y, z + h * 0.55),
                                f"04_乳钉_{n:02d}", PATINA, scale_z=0.75)); n += 1
    for side in range(4):
        for t in (1 / 3, 2 / 3):
            if side == 0:   p = (-SQ_HALF + 2 * SQ_HALF * t, -SQ_HALF)
            elif side == 1: p = ( SQ_HALF, -SQ_HALF + 2 * SQ_HALF * t)
            elif side == 2: p = ( SQ_HALF - 2 * SQ_HALF * t,  SQ_HALF)
            else:           p = (-SQ_HALF,  SQ_HALF - 2 * SQ_HALF * t)
            parts.append(add_sphere(NIPPLE_R, (p[0], p[1], z + h * 0.55),
                                    f"04_乳钉_{n:02d}", PATINA, scale_z=0.75)); n += 1
    return parts

# ---------------- 5. TLV 符号 ----------------
def build_tlv():
    z = BACK_Z; h = RELIEF_H * 0.9
    g = []
    # T ×4：N/E/S/W，横杠朝外，柄朝心
    for k, ang in enumerate((90, 0, 270, 180)):
        a = math.radians(ang)
        cx, cy = R_TLV * cos(a), R_TLV * sin(a)
        # 柄：从 r=36 到 r=48（沿径向）
        p_in = (36 * cos(a), 36 * sin(a))
        p_out = (48 * cos(a), 48 * sin(a))
        g.append(rect_bar(p_in, p_out, BAR_W, h, z, f"05_T{k}_stem", PATINA))
        # 横杠：在 r=48 处垂直于径向，半长 6.5
        tx, ty = p_out
        perp = (-sin(a), cos(a))
        g.append(rect_bar((tx - 6.5 * perp[0], ty - 6.5 * perp[1]),
                          (tx + 6.5 * perp[0], ty + 6.5 * perp[1]),
                          BAR_W, h, z, f"05_T{k}_bar", PATINA))
    # L ×4：对角（45/135/225/315），象限角内
    for k, ang in enumerate((45, 135, 225, 315)):
        a = math.radians(ang)
        cx, cy = R_TLV * cos(a), R_TLV * sin(a)
        # L 沿径向臂（朝心）+ 切向臂（顺时针向）
        p_c = (cx, cy)
        p_in = ((R_TLV - 12) * cos(a), (R_TLV - 12) * sin(a))
        g.append(rect_bar(p_in, p_c, BAR_W, h, z, f"06_L{k}_a", PATINA))
        b = a - pi / 2  # 切向
        p_t = (cx + 9 * cos(b), cy + 9 * sin(b))
        g.append(rect_bar(p_c, p_t, BAR_W, h, z, f"06_L{k}_b", PATINA))
    # V ×4：位于 T 与 L 之间（0/90/180/270 偏 22.5°×2？标准取 8 方位中点）
    for k, ang in enumerate((22.5, 112.5, 202.5, 292.5)):
        a = math.radians(ang)
        cx, cy = R_TLV * cos(a), R_TLV * sin(a)
        # V 尖朝心：两臂从尖点张开，夹角 ~90°，臂长 11
        tip = ((R_TLV - 8) * cos(a), (R_TLV - 8) * sin(a))
        for j, da in enumerate((pi / 4, -pi / 4)):
            p = (tip[0] + 11 * cos(a + pi / 2 + da * 2) * 1,
                 tip[1] + 11 * sin(a + pi / 2 + da * 2) * 1)
            # 直接：臂方向为 尖点 → 外张 ±45° 相对径向
            d = a + pi / 2 + (pi / 4 if j == 0 else -pi / 4)
            p = (tip[0] + 11 * cos(d), tip[1] + 11 * sin(d))
            g.append(rect_bar(tip, p, BAR_W, h, z, f"07_V{k}_{j}", PATINA))
    return g

# ---------------- 6. 四神（曲线浮雕） ----------------
def spirit_dragon(cx, cy):
    """青龙：S 形躯（开放曲线，不闭环）+ 首 + 角 + 四肢"""
    pts = []
    for i in range(30):
        t = i / 29
        # 横向 S：x 从 -10 到 +10，y 正弦摆动
        x = -10 + 20 * t
        y = 4.2 * sin(t * 1.7 * pi)
        pts.append((cx + x, cy + y, BACK_Z + RELIEF_H))
    parts = [curve_tube(pts, 1.3, "08_四神_青龙", PATINA)]
    # 首（外端）
    hx, hy = pts[-1][0], pts[-1][1]
    parts.append(add_sphere(2.5, (hx + 1.2, hy, BACK_Z + RELIEF_H), "08_龙首", PATINA, scale_z=0.85))
    # 双角后卷
    parts.append(curve_tube([(hx + 1, hy + 1.2, BACK_Z + RELIEF_H + 1),
                           (hx + 0.2, hy + 3.4, BACK_Z + RELIEF_H + 1.8),
                           (hx - 1.6, hy + 4.2, BACK_Z + RELIEF_H + 1.5)],
                          0.55, "08_龙角", PATINA))
    # 四肢短折线
    for j, (lx, ly) in enumerate(((cx - 5, 2.8), (cx + 1, -3.4), (cx + 5, 3.0))):
        s = 1 if ly > 0 else -1
        parts.append(curve_tube([(lx, ly, BACK_Z + RELIEF_H),
                                 (lx + 1.5, ly + 2.4 * s, BACK_Z + RELIEF_H),
                                 (lx + 3.6, ly + 2.8 * s, BACK_Z + RELIEF_H)],
                                0.7, f"08_龙足{j}", PATINA))
    return parts

def spirit_tiger(cx, cy):
    """白虎：伏身 + 巨头"""
    parts = []
    # 身：椭圆盘
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=5.5,
        location=(cx, cy, BACK_Z + RELIEF_H * 0.8))
    body = bpy.context.object; body.name = "08_四神_白虎身"
    body.scale = (1.35, 0.72, 0.45)
    bpy.ops.object.transform_apply(scale=True)
    body.data.materials.append(PATINA); bpy.ops.object.shade_smooth()
    parts.append(body)
    parts.append(add_sphere(3.0, (cx + 5.5, cy + 1.2, BACK_Z + RELIEF_H),
                            "08_虎首", PATINA, scale_z=0.85))
    # 尾
    parts.append(curve_tube([(cx - 6.5, cy - 1, BACK_Z + RELIEF_H),
                             (cx - 9.5, cy - 3.5, BACK_Z + RELIEF_H),
                             (cx - 10.5, cy - 6.5, BACK_Z + RELIEF_H + 1)],
                            0.9, "08_虎尾", PATINA))
    return parts

def spirit_bird(cx, cy):
    """朱雀：展翅"""
    z = BACK_Z + RELIEF_H
    parts = []
    # 身
    parts.append(add_sphere(2.2, (cx, cy, z), "08_四神_朱雀身", PATINA, scale_z=1.15))
    # 双翼曲线
    for s in (1, -1):
        pts = [(cx, cy + 1, z),
               (cx + s * 4.5, cy + 4.5, z),
               (cx + s * 9, cy + 5.5, z + 0.5),
               (cx + s * 11.5, cy + 3.0, z + 0.8)]
        parts.append(curve_tube(pts, 1.0, f"08_朱雀翼{'L' if s<0 else 'R'}", PATINA))
    # 尾羽
    for s in (0.6, -0.6):
        parts.append(curve_tube([(cx, cy - 1.5, z),
                                 (cx + s * 4, cy - 6.5, z - 0.2)],
                                0.8, f"08_朱雀尾{s}", PATINA))
    return parts

def spirit_tortoise(cx, cy):
    """玄武：龟 + 蛇"""
    z = BACK_Z + RELIEF_H
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=4.5,
        location=(cx, cy, z))
    t = bpy.context.object; t.name = "08_四神_玄武龟"
    t.scale = (1.25, 0.95, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    t.data.materials.append(PATINA); bpy.ops.object.shade_smooth()
    parts.append(t)
    # 蛇：缠绕 S
    pts = []
    for i in range(20):
        tt = i / 19
        pts.append((cx - 4 + 8 * tt, cy + 3.5 * sin(tt * 2.5 * pi), z + 1.2 + tt))
    parts.append(curve_tube(pts, 0.75, "08_玄武蛇", PATINA))
    return parts

def build_spirits():
    parts = []
    parts += spirit_tortoise(*polar(90, R_SPIRIT))   # 北
    parts += spirit_dragon(*polar(0, R_SPIRIT))    # 东
    parts += spirit_bird(*polar(270, R_SPIRIT))     # 南
    parts += spirit_tiger(*polar(180, R_SPIRIT))    # 西
    return parts

# ---------------- 7. 三角纹带 ----------------
def build_serrated():
    parts = []
    n = 64
    r_mid = (R_SERR_IN + R_SERR_OUT) / 2
    depth = (R_SERR_OUT - R_SERR_IN) / 2
    for i in range(n):
        a = 2 * pi * i / n
        # 三角形剖面（径向），朝内尖
        verts = [(R_SERR_IN, 0), (R_SERR_OUT, depth * 0.9), (R_SERR_OUT, -depth * 0.9)]
        # 用楔形：简单小方块旋转即可（省时且远看一致）——改用真三角
        bm = bpy.data.meshes.new(f"serr_mesh{i}")
        # 三角截面绕 Z 旋转成棱柱
        seg_t = [(R_SERR_IN, 0.0), (R_SERR_OUT, depth), (R_SERR_OUT, -depth)]
        vs = []
        for zz in (BACK_Z, BACK_Z + RELIEF_H * 0.8):
            for (rr, yy) in seg_t:
                vs.append((rr * cos(a) - yy * sin(a),
                           rr * sin(a) + yy * cos(a), zz))
        fs = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
        bm.from_pydata(vs, [], fs)
        bm.materials.append(PATINA)
        ob = bpy.data.objects.new(f"09_三角纹_{i:02d}", bm)
        bpy.context.scene.collection.objects.link(ob)
        parts.append(ob)
    return parts

# ---------------- 8. 卷云纹带 ----------------
def build_clouds():
    parts = []
    n = 24
    r_mid = (R_CLOUD_IN + R_CLOUD_OUT) / 2
    for i in range(n):
        a = 2 * pi * i / n
        cx, cy = r_mid * cos(a), r_mid * sin(a)
        # 每格：主螺旋 + 侧勾
        parts.append(spiral(cx, cy, 0.9, 3.1, 1.05, BACK_Z + RELIEF_H * 0.8,
                            f"10_卷云_{i:02d}", PATINA, bevel=0.7))
        b = a + pi / 2
        p0 = (cx + 2.4 * cos(b), cy + 2.4 * sin(b))
        p1 = (cx + 3.4 * cos(b) + 1.8 * cos(a), cy + 3.4 * sin(b) + 1.8 * sin(a))
        parts.append(curve_tube([(*p0, BACK_Z + RELIEF_H * 0.8),
                                 (*p1, BACK_Z + RELIEF_H * 0.8)],
                                0.6, f"10_卷勾_{i:02d}", PATINA))
    return parts

# ---------------- 组装 ----------------
def main():
    global PATINA
    clean_scene()
    PATINA = mat_bronze()
    DARK = mat_dark()
    build_body()
    build_knob()
    build_square_nipples()
    build_tlv()
    build_spirits()
    build_serrated()
    build_clouds()
    # 单位：mm
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    # 保存
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/tlv_mirror_1995_301.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
