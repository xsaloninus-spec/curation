# -*- coding: utf-8 -*-
"""
齐家文化七角星纹铜镜 —— 青海贵南尕马台 M25:6（青海省博物馆藏）
直径 90 mm、厚 2.5 mm（贵南县政府公布 M25:6 数据）。
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
STAR_TIP_R = (33.0, 36.5)   # 七角星角尖半径范围（照片描摹，推定）
STAR_VALLEY_R = (14.0, 16.5) # 角间谷底半径（推定）
RELIEF_H = 0.6        # 纹饰凸起（推定）
RIDGE_IN = 12.5       # 钮周围凸弦纹半径（照片描摹）
RIDGE_OUT = 39.5      # 镜缘内侧凸弦纹半径（照片描摹）
KNOB_W = 12.0         # 桥形钮宽度（推定）
KNOB_H = 3.0          # 桥形钮高（推定）
HOLE_R = 1.4          # 镜缘双孔半径（推定）
HOLE_RD = 40.8        # 双孔所在圆半径（照片：近镜缘）
HOLE_DA = math.radians(13.5)  # 双孔相对 +Y 的张角（照片描摹）
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

# ---------------- 2. 中央桥形钮（残损现状） + 可隐藏复原补全 ----------------
def build_knob():
    # 残存拱钮：低矮半拱，一端残断
    seg = 24
    verts, faces = [], []
    w = KNOB_W / 2
    for i in range(seg + 1):
        t = i / seg
        a = pi * t
        x = w * cos(a)
        zh = KNOB_H * sin(a) * (0.75 if t > 0.8 else 1.0)   # 一端残低
        for y in (-2.6, 2.6):
            verts.append((x, y, zh))
    for i in range(seg):
        a = i * 2; b = a + 1; c = a + 3; d = a + 2
        faces.append((a, b, c, d))
    # 端封
    faces.append((0, 1, 1, 0))
    me = bpy.data.meshes.new("knob_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(BRONZE)
    ob = bpy.data.objects.new("03_残钮_DamagedBridgeKnob", me)
    bpy.context.scene.collection.objects.link(ob)
    bevel = ob.modifiers.new("soft", 'BEVEL'); bevel.width = 0.5; bevel.segments = 2
    # 钮座（圆形平台）
    base = add_cylinder(8.5, 0.9, (0, 0, 0.45), "03_钮座_KnobBase", BRONZE)
    # 复原补全（隐藏）：把拱补到完整高度
    pts = []
    for i in range(13):
        t = i / 12
        a = pi * (0.8 + 0.2 * t)
        pts.append((w * cos(a), 0, KNOB_H * sin(a) + 0.55))
    rest = curve_tube(pts, 2.5, "03b_钮复原_KnobRestoration", BRONZE)
    rest.hide_render = True
    rest.hide_viewport = True
    return ob

# ---------------- 3. 七角星纹（不规则，阳铸浅浮雕） ----------------
def build_star():
    # 7 个宽角：每个角给出"角尖两侧"两点 → 臂身宽、侧边内凹的手工星形
    STAR_TIP_R = (30.5, 33.5)      # 角尖不超过外凸弦纹（39.5）内缘
    tips = []
    for i in range(7):
        a = pi / 2 + i * 2 * pi / 7 + random.uniform(-0.05, 0.05)
        r = random.uniform(*STAR_TIP_R)
        w = math.radians(random.uniform(4.5, 6.5))   # 角尖半宽
        tips.append((a, r, w))
    pts2d = []
    for i in range(7):
        a1, r1, w1 = tips[i]
        a2, r2, w2 = tips[(i + 1) % 7]
        pts2d.append((a1 - w1, r1 * 0.985))
        pts2d.append((a1 + w1, r1))
        # 谷底（两角之间）
        va = a1 + (a2 - a1) * random.uniform(0.40, 0.52)
        vr = random.uniform(*STAR_VALLEY_R)
        pts2d.append((va, vr))
    n = len(pts2d)
    z0, z1 = 0.0, RELIEF_H
    verts = [(r * cos(a), r * sin(a), z0) for a, r in pts2d] + \
            [(r * cos(a), r * sin(a), z1) for a, r in pts2d]
    faces = []
    for i in range(n):
        ni = (i + 1) % n
        faces.append((i, ni, n + ni, n + i))
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    me = bpy.data.meshes.new("star_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(BRONZE)
    ob = bpy.data.objects.new("04_七角星纹_SevenPointStar", me)
    bpy.context.scene.collection.objects.link(ob)
    bevel = ob.modifiers.new("cast_soft", 'BEVEL'); bevel.width = 0.35; bevel.segments = 2
    return ob

# ---------------- 4. 角间斜线纹（每组平行短线，方向各组不同） ----------------
def build_oblique_lines():
    base = pi / 2
    for i in range(7):
        a = base + (i + 0.5) * 2 * pi / 7
        # 每组 5 条，平行于过该角分线方向偏转 35° 的轴线
        tilt = math.radians(35)
        dx, dy = cos(a + tilt), sin(a + tilt)
        px, py = -dy, dx
        for j in range(5):
            off = (j - 2) * 2.3
            cx, cy = 27.5 * cos(a), 27.5 * sin(a)
            x0, y0 = cx + px * off - dx * 6.0, cy + py * off - dy * 6.0
            x1, y1 = cx + px * off + dx * 6.0, cy + py * off + dy * 6.0
            zl = RELIEF_H * 0.5
            curve_tube([(x0, y0, zl), (x1, y1, zl)], 0.38,
                       f"05_斜线纹_{i}_{j}", BRONZE)
            # 封口小球，避免管状端头露空
            add_sphere(0.38, (x0, y0, zl), f"05_斜线端_{i}_{j}_a", BRONZE, seg=8)
            add_sphere(0.38, (x1, y1, zl), f"05_斜线端_{i}_{j}_b", BRONZE, seg=8)

# ---------------- 5. 双重凸弦纹 ----------------
def build_ridges():
    for r, nm in ((RIDGE_IN, "06_内凸弦纹"), (RIDGE_OUT, "06_外凸弦纹")):
        pts = [(r * cos(2 * pi * i / 96), r * sin(2 * pi * i / 96), 0.85)
               for i in range(97)]
        curve_tube(pts, 0.85, nm, BRONZE, cyclic=True)

# ---------------- 6. 镜缘双孔（真实贯穿） + 绳痕凹槽 ----------------
def _apply(obj, mod):
    """确保 modifier_apply 作用于目标对象（后台模式下 active 漂移会导致静默失败）"""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

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

# ---------------- 7. 木质镜柄 + 系绳（推定复原，独立可隐藏） ----------------
def build_handle_restoration():
    # 木柄：位于镜背一侧（z<0），上端贴近镜背、双孔之间，轴线沿 +Y
    y0 = 42.0
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
    build_knob()
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
