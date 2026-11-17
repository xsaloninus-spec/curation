# -*- coding: utf-8 -*-
"""
战国蟠螭纹透雕铜镜 —— The Metropolitan Museum of Art 23.120.5
直径 133 mm（馆方）。透雕背饰 = 战国原物（馆方确认）；
后方镜体/镜盘可能为现代替换件（馆方声明）——双层分离建模，间距可调。
Blender 4.5 headless: Blender -b --factory-startup --python build_met_mirror.py
"""
import bpy
import math, random
from math import sin, cos, pi
from mathutils import Vector

random.seed(1205)   # 23.120.5

# ---------------- 参数（mm） ----------------
R = 66.5               # 半径（Φ133 馆方）
PLATE_T = 3.0          # 后方镜体厚（推定）
GAP = 3.0              # 透雕层与镜体间距（可调参数，非考古结论）
OW_T = 2.2             # 透雕层板厚（推定）
OW_R_IN = 17.0         # 透雕区内径（照片描摹）
OW_R_OUT = 55.0        # 透雕区外径 = 内侧边框内缘（照片描摹）
RIM_IN = 61.0          # 外缘内径（照片描摹）
BODY_R = 2.2           # 蟠螭身粗基准（照片描摹）
KNOB_R = 4.0           # 中央环钮半径（照片描摹）
KNOB_T = 1.8

ANCIENT = None   # 战国青铜（绿锈）
PLATE = None     # 镜体（可能现代替换，色感区分）
DARK = None      # 镂空阴影区

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

def ring_band(r_in, r_out, z0, z1, name, mat, seg=128):
    verts, faces = [], []
    for z in (z0, z1):
        for r in (r_in, r_out):
            for i in range(seg):
                th = 2 * pi * i / seg
                verts.append((r * cos(th), r * sin(th), z))
    # 层布局: 0 z0内 1 z0外 | 2 z1内 3 z1外
    for i in range(seg):
        ni = (i + 1) % seg
        a, b = i, ni
        faces += [(a, b, 2 * seg + b, 2 * seg + a),
                  (seg + ni, seg + i, 3 * seg + i, 3 * seg + ni),
                  (2 * seg + i, 2 * seg + ni, 3 * seg + ni, 3 * seg + i),
                  (ni, i, seg + i, seg + ni)]
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    return ob

def mat_ancient_bronze():
    """深灰褐 + 青绿氧化（战国青铜）"""
    m = bpy.data.materials.new("Bronze_ancient_WarringStates")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.55
    bs.inputs["Roughness"].default_value = 0.72
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.5
    noise.inputs["Detail"].default_value = 5.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.055, 0.075, 0.05, 1)  # 深灰绿
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.22, 0.17, 0.09, 1)    # 暗铜
    mid = ramp.color_ramp.elements.new(0.5)
    mid.color = (0.10, 0.19, 0.12, 1)                             # 青绿锈
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.3
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_plate_bronze():
    """镜体：偏灰褐、较均匀（存疑现代替换，质感略异于古代层）"""
    m = bpy.data.materials.new("Bronze_plate_suspected_modern")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.75
    bs.inputs["Roughness"].default_value = 0.45
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 7.0
    noise.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.10, 0.09, 0.08, 1)
    ramp.color_ramp.elements[1].color = (0.24, 0.20, 0.14, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_mirror_face():
    m = bpy.data.materials.new("MirrorFace")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.42, 0.40, 0.36, 1)
    bs.inputs["Metallic"].default_value = 0.95
    bs.inputs["Roughness"].default_value = 0.3
    return m

# ---------------- 1. 后方镜体 / 镜盘（可能现代替换件） ----------------
def build_plate():
    seg = 128
    verts, faces = [], []
    z_front, z_back = -GAP - PLATE_T, -GAP   # 正面（镜面）在下
    for z in (z_back, z_front):
        for i in range(seg):
            th = 2 * pi * i / seg
            verts.append((R * cos(th), R * sin(th), z))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((i, ni, seg + ni, seg + i))
    ci = len(verts); verts.append((0, 0, z_back))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((ci, ni, i))
    ci2 = len(verts); verts.append((0, 0, z_front))
    for i in range(seg):
        ni = (i + 1) % seg
        faces.append((ci2, seg + i, seg + ni))
    me = bpy.data.meshes.new("plate_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(PLATE)
    ob = bpy.data.objects.new("01_后方镜体_推定替换_MirrorPlate", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    # 镜面（贴附镜体正面）
    ring_band(0.5, R - 0.5, z_front - 0.15, z_front, "02_镜面_MirrorFace",
              mat_mirror_face(), seg=96)
    return ob

# ---------------- 2. 古代透雕层（独立网格） ----------------
def build_openwork_base():
    # 透雕层基板：薄环板（镂空主体立于此板上，板本身即"透雕底"）
    ob = ring_band(OW_R_IN, OW_R_OUT, 0, OW_T, "03_透雕层基板_OpenworkPlate", ANCIENT)
    # 内缘立边
    ring_band(OW_R_IN - 1.2, OW_R_IN, 0, OW_T + 1.2, "05_内侧环形边框_InnerRing", ANCIENT)
    return ob

# ---------------- 3. 蟠螭交缠主体（粗细变化、上下交叠） ----------------
def dragon_paths():
    """生成相互穿插的蟠螭身路径。层叠：z 基准 OW_T，跨越时抬升。"""
    paths = []
    n_dragon = 11
    for d in range(n_dragon):
        base_a = 2 * pi * d / n_dragon + random.uniform(-0.2, 0.2)
        handed = 1 if d % 2 else -1
        pts = []
        steps = 42
        for i in range(steps):
            t = i / (steps - 1)
            # 大回旋：角向扫过约 300°，径向在中带摆动
            a = base_a + handed * (0.4 + 2.4 * pi * t)
            r = 36 + 13 * sin(2.3 * pi * t + d * 1.1) + random.uniform(-1.2, 1.2)
            r = max(OW_R_IN + 4, min(OW_R_OUT - 4, r))
            # 交叠抬升更高，让镂空缝隙投下真实阴影
            lift = 2.2 * (0.5 + 0.5 * sin(5 * pi * t + d))
            z = OW_T + 1.2 + lift
            pts.append((r * cos(a), r * sin(a), z))
        paths.append((pts, d))
    return paths

def build_dragons():
    for pts, d in dragon_paths():
        n = len(pts)
        # 分段变径：相邻段重叠 2 点，避免竹节状断差
        i = 0
        while i < n - 1:
            j = min(i + 7, n - 1)
            w = BODY_R * (0.82 + 0.36 * random.random())
            curve_tube(pts[i:j + 1], w, f"04_蟠螭身_{d}_{i}", ANCIENT)
            i = j - 2 if j < n - 1 else j
        # 蟠首：路径一端，简化兽首（椭球 + 卷鼻）
        hx, hy, hz = pts[-1]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10,
            radius=BODY_R * 1.25, location=(hx, hy, hz + 0.6))
        head = bpy.context.object
        head.name = f"04_蟠首_{d}"
        head.scale = (1.35, 0.95, 0.9)
        bpy.ops.object.transform_apply(scale=True)
        head.data.materials.append(ANCIENT)
        bpy.ops.object.shade_smooth()
        # 卷鼻角
        curve_tube([(hx, hy, hz + 1.2), (hx + 2.2, hy + 1.5, hz + 2.6)],
                   0.8, f"04_蟠角_{d}", ANCIENT)
        # 尾卷
        tx, ty, tz = pts[0]
        curve_tube([(tx, ty, tz), (tx - 3.0, ty - 3.0, tz + 1.8)],
                   BODY_R * 0.5, f"04_蟠尾_{d}", ANCIENT)

# ---------------- 4. 中央环钮 ----------------
def build_knob():
    bpy.ops.mesh.primitive_torus_add(major_radius=KNOB_R, minor_radius=KNOB_T,
        major_segments=32, minor_segments=12,
        location=(0, 0, OW_T + KNOB_R + 1.2), rotation=(pi / 2, 0, 0))
    o = bpy.context.object; o.name = "06_中央环钮_LoopKnob"
    o.data.materials.append(ANCIENT)
    bpy.ops.object.shade_smooth()
    # 钮座
    ring_band(2.0, KNOB_R + 2.2, OW_T, OW_T + 1.0, "06_钮座", ANCIENT, seg=48)

# ---------------- 5. 外侧卷云纹带 + 外缘 ----------------
def build_scroll_band():
    # 卷云带基环（位于镜体背面上，随镜体存疑）
    ring_band(OW_R_OUT + 1.5, RIM_IN, -GAP + 0.4, -GAP + 1.6, "07_卷云纹带底", PLATE)
    # 连续卷云浅浮雕：S 形回卷单元绕环一周（随镜体质感，暗色浅浮雕）
    n = 20
    for i in range(n):
        a0 = 2 * pi * i / n
        rc = (OW_R_OUT + 1.5 + RIM_IN) / 2
        cx, cy = rc * cos(a0), rc * sin(a0)
        tang = a0 + pi / 2
        pts = []
        for k in range(17):
            t = k / 16
            s = (t - 0.5) * 4.4
            rr = 2.0 * sin(t * 2 * pi)
            pts.append((cx + cos(tang) * s - cos(a0) * rr,
                        cy + sin(tang) * s - sin(a0) * rr,
                        -GAP + 1.7 + 0.25 * sin(t * pi)))
        curve_tube(pts, 0.62, f"07_卷云纹_{i}", PLATE)

def build_outer_rim():
    ring_band(RIM_IN, R, -GAP, -GAP + 2.2, "08_外缘边框_OuterRim", PLATE)
    ring_band(RIM_IN - 0.8, RIM_IN, -GAP, -GAP + 2.8, "08_缘内棱", PLATE)

def main():
    global ANCIENT, PLATE, DARK
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    ANCIENT = mat_ancient_bronze()
    PLATE = mat_plate_bronze()
    build_plate()
    build_openwork_base()
    build_dragons()
    build_knob()
    build_scroll_band()
    build_outer_rim()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/met_23_120_5.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
