# -*- coding: utf-8 -*-
"""
齐家文化七角星纹铜镜 —— 青海贵南尕马台 M25:6（青海省博物馆藏）
直径 90 mm、厚 2.5 mm（贵南县政府公布 M25:6 数据）。

v2（2026-11-17）按权威考据重做几何：
  1. 七角星 = 7 个尖长三角形，以镜钮为轴心辐射，底宽 8–10 mm，尖角 r≈35–37
  2. 斜线纹扇形区移到镜缘 r≈24→39，位于相邻两星角之间，每组 5–6 条平行斜线
  3. 凸弦纹共三圈：钮周双圈 r12.5 / r16 + 镜缘一圈 r39.5
  4. 桥钮 = 两足 + 拱顶的小拱桥，拱下留缝（贯穿桥孔，正面可见），一端残断更低
  5. 镜缘双孔放大至 r≈1.8，位于 r≈40 顶部紧邻，孔间凹形绳痕
镜缘双孔 + 绳痕 + 木质镜柄（推定复原，独立可隐藏部件）。
Blender 4.5 headless: Blender -b --factory-startup --python build_qijia_mirror.py
"""
import bpy
import math, random
from math import sin, cos, pi
from mathutils import Vector

random.seed(25)   # 尕马台 M25

# ---------------- 参数（mm） ----------------
R = 45.0              # 镜体半径（Φ90 考古资料）
T = 2.5               # 镜体厚度（考古资料）
RELIEF_H = 0.6        # 纹饰凸起（推定）
# 七角星：尖长三角形，以钮为轴心辐射
STAR_BASE_R = 9.5     # 三角形底（宽端）半径（钮座外缘）
STAR_BASE_HW = 4.5    # 底半宽 4.5 mm → 底宽 9 mm（考据 8–10 mm）
STAR_TIP_R = (34.5, 36.5)  # 角尖半径 r≈35–37（考据）
# 凸弦纹三圈
RIDGE_IN = 12.5       # 钮周凸弦纹内圈
RIDGE_MID = 16.0      # 钮周凸弦纹外圈（考据：钮周两周）
RIDGE_OUT = 39.5      # 镜缘凸弦纹（照片可见镜缘凸边）
# 桥形钮
KNOB_SPAN = 6.5       # 拱半跨（两足间距 13 mm，推定）
KNOB_RISE = 3.4       # 拱顶高出钮座面（推定）
KNOB_FOOT_R = 1.8     # 桥足半径
SLOT_R = 2.6          # 拱下桥孔半径
SLOT_SX = 1.2         # 桥孔沿 X 拉长系数（胶囊形）
# 镜缘双孔 + 绳痕
HOLE_R = 1.8          # 孔半径（考据 孔径 3–4 mm → r≈1.6–2.0）
HOLE_RD = 40.0        # 双孔所在圆半径 r≈40（考据）
HOLE_DA = math.radians(4.5)  # 双孔相对 +Y 的张角（照片：顶部两孔紧邻）
HANDLE_L = 110.0      # 木柄长（推定）
HANDLE_R = 4.2        # 木柄半径（推定）

BRONZE = None
MIRROR = None
WOOD = None
CORD = None

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

def add_sphere(r, loc, name, mat, scale=(1, 1, 1), seg=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=8, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def add_cylinder(r, depth, loc, name, mat, vertices=48, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=r, depth=depth, location=loc)
    o = bpy.context.object; o.name = name
    if rot: o.rotation_euler = rot
    if mat: o.data.materials.append(mat)
    return o

def mat_corroded_bronze():
    """红褐/橙褐氧化基色 + 局部青绿锈，高粗糙"""
    m = bpy.data.materials.new("Bronze_corroded_Qijia")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.55
    bs.inputs["Roughness"].default_value = 0.72
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.2
    noise.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.32
    ramp.color_ramp.elements[0].color = (0.13, 0.08, 0.04, 1)     # 深褐凹陷
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.40, 0.24, 0.11, 1)     # 橙褐凸起
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = (0.26, 0.15, 0.07, 1)                              # 红褐过渡
    # 第二层高频噪声控制青绿锈斑（斑驳覆盖在褐基调上）
    noise2 = nt.nodes.new("ShaderNodeTexNoise")
    noise2.inputs["Scale"].default_value = 9.0
    noise2.inputs["Detail"].default_value = 4.0
    ramp2 = nt.nodes.new("ShaderNodeValToRGB")
    ramp2.color_ramp.elements[0].position = 0.55
    ramp2.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp2.color_ramp.elements[1].position = 0.72
    ramp2.color_ramp.elements[1].color = (1, 1, 1, 1)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MIX'
    mix.inputs[2].default_value = (0.12, 0.20, 0.13, 1)            # 青绿锈
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(noise2.outputs["Fac"], ramp2.inputs["Fac"])
    nt.links.new(ramp2.outputs["Color"], mix.inputs[0])
    nt.links.new(ramp.outputs["Color"], mix.inputs[1])
    nt.links.new(mix.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_mirror_face():
    m = bpy.data.materials.new("MirrorFace_aged")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.30, 0.28, 0.24, 1)
    bs.inputs["Metallic"].default_value = 0.95
    bs.inputs["Roughness"].default_value = 0.22
    return m

def mat_wood():
    m = bpy.data.materials.new("Wood_handle")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.16, 0.09, 0.04, 1)
    bs.inputs["Roughness"].default_value = 0.8
    return m

def mat_cord():
    m = bpy.data.materials.new("Cord_fiber")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.16, 0.12, 0.06, 1)
    bs.inputs["Roughness"].default_value = 0.9
    return m

# ---------------- 1. 圆形镜体（轻微不规则边缘） ----------------
def build_disc():
    seg = 128
    verts, faces = [], []
    # 背面（z=0，纹饰面）与正面（z=-T），外缘带轻微铸造起伏
    for z in (0.0, -T):
        for i in range(seg):
            th = 2 * pi * i / seg
            rr = R * (1 + 0.004 * sin(3 * th + 0.7) + 0.003 * sin(7 * th))
            verts.append((rr * cos(th), rr * sin(th), z))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((i, ni, seg + ni, seg + i))
    # 背面中心扇面
    ci = len(verts); verts.append((0, 0, 0.0))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((ci, ni, i))
    # 正面中心扇面
    ci2 = len(verts); verts.append((0, 0, -T))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((ci2, seg + i, seg + ni))
    me = bpy.data.meshes.new("disc_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(BRONZE)
    ob = bpy.data.objects.new("01_镜体_Disc", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    return ob

def build_mirror_face():
    o = add_cylinder(R - 0.6, 0.25, (0, 0, -T - 0.05), "02_镜面_MirrorFace", MIRROR)
    for p in o.data.polygons: p.use_smooth = True
    return o

# ---------------- 2. 中央桥形钮（残损现状）：两足 + 拱顶，拱下桥孔贯穿 ----------------
def _apply(obj, mod):
    """确保 modifier_apply 作用于目标对象（后台模式下 active 漂移会导致静默失败）"""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

def _arch_points(broken):
    """拱桥中线采样：t=0 在 +X 端足，t=1 在 -X 端足。
    broken=True 时 +X 端残断更低（现状），False 为完整拱（复原）。"""
    pts = []
    n = 16
    for i in range(n + 1):
        t = i / n
        th = pi * t
        x = KNOB_SPAN * cos(th)
        rise = KNOB_RISE * sin(th)
        if broken:
            # +X 端（t→0）残断：足端只剩约 1/3 高，向拱顶渐变恢复
            rise *= min(1.0, 0.30 + t / 0.30)
        pts.append((x, 0.0, 0.9 + rise))
    return pts

def build_knob(disc):
    # 桥孔：胶囊形长孔贯穿镜体（含镜面），从镜面正面可见透光
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=SLOT_R, depth=T + 2,
                                        location=(0, 0, -T / 2))
    cutter = bpy.context.object; cutter.name = "cut_bridge_slot"
    cutter.scale = (SLOT_SX, 1.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    mod = disc.modifiers.new("桥孔", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'
    mod.object = cutter
    _apply(disc, mod)
    # 钮座（圆形平台，原器已残，简化为低台；桥孔同样贯穿）
    base = add_cylinder(8.5, 0.9, (0, 0, 0.45), "03_钮座_KnobBase", BRONZE)
    mod2 = base.modifiers.new("桥孔", 'BOOLEAN')
    mod2.operation = 'DIFFERENCE'; mod2.solver = 'EXACT'
    mod2.object = cutter
    _apply(base, mod2)
    bpy.data.objects.remove(cutter, do_unlink=True)
    # 两足
    for s, nm in ((1, "足A"), (-1, "足B")):
        add_cylinder(KNOB_FOOT_R, 1.6, (s * KNOB_SPAN, 0, 0.8), f"03_桥足_{nm}", BRONZE, vertices=24)
    # 残存拱顶（+X 端残断更低）
    ob = curve_tube(_arch_points(broken=True), 1.55, "03_残拱桥_DamagedBridge", BRONZE)
    # 复原补全（隐藏）：完整拱桥
    rest = curve_tube(_arch_points(broken=False), 1.55, "03b_钮复原_KnobRestoration", BRONZE)
    rest.hide_render = True
    rest.hide_viewport = True
    return ob

# ---------------- 3. 七角星纹：7 个尖长三角形，以镜钮为轴心辐射 ----------------
def build_star():
    for i in range(7):
        a = pi / 2 + i * 2 * pi / 7 + random.uniform(-0.035, 0.035)
        tip_r = random.uniform(*STAR_TIP_R)
        # 局部坐标：x 沿角向，y 切向。三角形底边在 r≈STAR_BASE_R，宽 2*STAR_BASE_HW
        u = Vector((cos(a), sin(a)))
        v = Vector((-sin(a), cos(a)))
        base_c = u * STAR_BASE_R
        p0 = base_c + v * STAR_BASE_HW     # 底边一端
        p1 = base_c - v * STAR_BASE_HW     # 底边另一端
        p2 = u * tip_r                     # 角尖
        z0, z1 = 0.0, RELIEF_H
        verts = [(p0.x, p0.y, z0), (p1.x, p1.y, z0), (p2.x, p2.y, z0),
                 (p0.x, p0.y, z1), (p1.x, p1.y, z1), (p2.x, p2.y, z1)]
        faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
        me = bpy.data.meshes.new(f"star_tri_mesh_{i}")
        me.from_pydata(verts, [], faces)
        me.materials.append(BRONZE)
        ob = bpy.data.objects.new(f"04_七角星_尖三角_{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        bevel = ob.modifiers.new("cast_soft", 'BEVEL'); bevel.width = 0.3; bevel.segments = 2

# ---------------- 4. 镜缘扇形斜线纹：r≈24→39，相邻两星角之间，每组 6 条平行斜线 ----------------
def build_oblique_lines():
    base = pi / 2
    for i in range(7):
        a = base + (i + 0.5) * 2 * pi / 7          # 扇形区角分线（两星角之间）
        u = Vector((cos(a), sin(a)))                # 径向
        v = Vector((-sin(a), cos(a)))               # 切向
        tilt = math.radians(28)                     # 斜线与径向的夹角（沿扇形斜向）
        d = u * cos(tilt) + v * sin(tilt)           # 线方向
        c = u * 31.5                                # 扇形区中心半径
        half = 6.5                                  # 半长：r 覆盖 25→38
        for j in range(6):
            s = (j - 2.5) * 3.0                     # 切向排布，组宽 15 mm
            p = c + v * s
            x0, y0 = p.x - d.x * half, p.y - d.y * half
            x1, y1 = p.x + d.x * half, p.y + d.y * half
            zl = RELIEF_H * 0.5
            curve_tube([(x0, y0, zl), (x1, y1, zl)], 0.38,
                       f"05_斜线纹_扇形_{i}_{j}", BRONZE)
            # 封口小球，避免管状端头露空
            add_sphere(0.38, (x0, y0, zl), f"05_斜线端_{i}_{j}_a", BRONZE, seg=8)
            add_sphere(0.38, (x1, y1, zl), f"05_斜线端_{i}_{j}_b", BRONZE, seg=8)

# ---------------- 5. 三重凸弦纹：钮周双圈 + 镜缘一圈 ----------------
def build_ridges():
    for r, nm in ((RIDGE_IN, "06_凸弦纹_钮周内圈"),
                  (RIDGE_MID, "06_凸弦纹_钮周外圈"),
                  (RIDGE_OUT, "06_凸弦纹_镜缘")):
        pts = [(r * cos(2 * pi * i / 96), r * sin(2 * pi * i / 96), 0.85)
               for i in range(97)]
        curve_tube(pts, 0.85, nm, BRONZE, cyclic=True)

# ---------------- 6. 镜缘双孔（真实贯穿） + 绳痕凹槽 ----------------
def build_holes_and_cord_trace(disc):
    for s, nm in ((1, "A"), (-1, "B")):
        a = pi / 2 + s * HOLE_DA
        x, y = HOLE_RD * cos(a), HOLE_RD * sin(a)
        cutter = add_cylinder(HOLE_R, T + 2, (x, y, -T / 2), f"cut_hole_{nm}", None)
        mod = disc.modifiers.new(f"孔_{nm}", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'
        mod.object = cutter
        _apply(disc, mod)
        bpy.data.objects.remove(cutter, do_unlink=True)
    # 双孔之间凹形绳痕：浅槽（布尔）沿镜缘连接两孔
    a1 = pi / 2 + HOLE_DA
    a2 = pi / 2 - HOLE_DA
    pts = []
    for i in range(25):
        t = i / 24
        a = a1 + (a2 - a1) * t
        pts.append((HOLE_RD * cos(a), HOLE_RD * sin(a), 0.15))
    groove = curve_tube(pts, 1.0, "cut_groove", None)
    # 曲线转网格做布尔
    bpy.ops.object.select_all(action='DESELECT')
    groove.select_set(True)
    bpy.context.view_layer.objects.active = groove
    bpy.ops.object.convert(target='MESH')
    mod = disc.modifiers.new("绳痕凹槽", 'BOOLEAN')
    mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'
    mod.object = groove
    _apply(disc, mod)
    bpy.data.objects.remove(groove, do_unlink=True)

# ---------------- 7. 木质镜柄 + 系绳（推定复原，独立可隐藏；柄从双孔所在 +Y 侧伸出） ----------------
def build_handle_restoration():
    # 木柄：位于镜背一侧（z<0），上端贴近镜缘顶部双孔，轴线沿 +Y
    y0 = 44.0
    hz = -T / 2 - HANDLE_R + 0.8     # 柄轴高度：上缘贴近镜背平面
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=HANDLE_R * 0.82, radius2=HANDLE_R,
                                    depth=HANDLE_L, location=(0, y0 + HANDLE_L / 2, hz),
                                    rotation=(pi / 2, 0, 0))
    handle = bpy.context.object; handle.name = "09_木质镜柄_推定复原_WoodHandle"
    handle.data.materials.append(WOOD)
    bevel = handle.modifiers.new("soft", 'BEVEL'); bevel.width = 1.0; bevel.segments = 2
    # 系绳：两孔各以平滑曲线（二次贝塞尔采样）连到柄上端
    def hole_pos(s):
        a = pi / 2 + s * HOLE_DA
        return Vector((HOLE_RD * cos(a), HOLE_RD * sin(a), 0))
    def bezier(p0, p1, p2, n=14):
        pts = []
        for i in range(n + 1):
            t = i / n
            p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
            pts.append(tuple(p))
        return pts
    top = Vector((0, y0 + 3, hz + HANDLE_R - 0.4))
    for s, nm in ((1, "A"), (-1, "B")):
        h = hole_pos(s) + Vector((0, 0, 0.4))
        mid = Vector((h.x * 0.55, h.y + 4.5, 1.2))
        curve_tube(bezier(h, mid, top), 0.55, f"10_系绳_{nm}_推定复原_Cord", CORD)
    # 柄上端缠绳：绕柄轴的环（柄轴沿 Y，环在 XZ 平面）
    for k in range(3):
        yy = y0 + 2.5 + k * 2.4
        pts = [((HANDLE_R + 0.25) * cos(2 * pi * i / 24), yy,
                hz + (HANDLE_R + 0.25) * sin(2 * pi * i / 24))
               for i in range(25)]
        curve_tube(pts, 0.5, f"10_柄端缠绳_{k}", CORD, cyclic=True)
    for o in bpy.context.scene.objects:
        if o.name.startswith(("09_", "10_")):
            o.hide_render = True
            o.hide_viewport = True

def main():
    global BRONZE, MIRROR, WOOD, CORD
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    BRONZE = mat_corroded_bronze()
    MIRROR = mat_mirror_face()
    WOOD = mat_wood()
    CORD = mat_cord()
    disc = build_disc()
    build_mirror_face()
    build_knob(disc)
    build_star()
    build_oblique_lines()
    build_ridges()
    build_holes_and_cord_trace(disc)
    build_handle_restoration()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/qijia_mirror.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
