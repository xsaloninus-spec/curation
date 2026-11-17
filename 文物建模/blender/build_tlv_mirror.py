# -*- coding: utf-8 -*-
"""
东汉 TLV 四神博局镜 —— Cleveland Museum of Art 1995.301 重建 v2
按馆方照片与数据重做（v1 回退）：半球大圆钮、双线方框压 12 乳、
方框外八乳圈座、四神 + 云气 + 细线 TLV、栉齿 / 锯齿 / 宽缘卷云三圈边带。
数据：D=190mm，中心厚 12mm，缘厚 7mm，R=95mm。
Blender 4.5 headless:  Blender -b --factory-startup --python build_tlv_mirror.py
"""
import bpy
import math
from math import sin, cos, pi
from mathutils import Vector

# ---------------- 参数（mm） ----------------
R = 95.0
CENTER_T = 12.0          # 中心总厚
RIM_T = 7.0              # 缘厚
BACK_Z = 0.0             # 镜背基准面（+Z 为纹饰面）
RELIEF_H = 1.0           # 主纹饰凸起
R_KNOB = 14.0            # 圆钮半径
H_KNOB = 8.0             # 圆钮高（扁半球）
SQ_HALF = 33.0           # 方框中心半边长
SQ_LINE_W = 1.5          # 单线宽
SQ_GAP = 2.0             # 双线间距
SQ_H = 1.0               # 方框凸起
NIP_R = 3.0              # 方框边乳钉半径
R_8NIP = 52.0            # 八乳圈座分布半径
SEAT_R = 7.0             # 圆圈座半径
SEAT_NIP_R = 3.5         # 圈座内乳钉半径
R_HATCH_IN, R_HATCH_OUT = 62.0, 68.0   # 栉齿纹带
R_ZIG_IN, R_ZIG_OUT = 68.0, 74.0       # 锯齿纹带
R_CLOUD_IN = 74.0                     # 缘云气带内径
R_LIP = 92.5                          # 缘唇

MAT_BRONZE = None   # 黑漆古青铜（主体纹饰）
MAT_RELIEF = None   # 棱线亮青铜（细线铸纹）
MAT_PATINA = None   # 重锈青铜（镜钮、镜缘）
MAT_POLISH = None   # 抛光镜面（-Z 面）

# ---------------- 基础工具 ----------------
def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def mat_bronze(name, patina=0.0, rough=0.42):
    """黑漆古包浆青铜：Noise 混合深灰黑包浆 + 少量孔雀石绿（patina 控制绿的比例）"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0 if patina > 0.5 else 4.5
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.7
    noise.inputs["Distortion"].default_value = 0.25
    nt.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    if patina > 0.5:
        # 重锈材质（镜钮/镜缘）：暗绿与青铜斑驳相间
        e0 = ramp.color_ramp.elements[0]; e0.position = 0.30
        e0.color = (0.026, 0.028, 0.034, 1)      # 包浆暗部（近黑）
        e1 = ramp.color_ramp.elements.new(0.50)
        e1.color = (0.075, 0.072, 0.070, 1)      # 深灰
        e2 = ramp.color_ramp.elements.new(0.58)
        e2.color = (0.155, 0.135, 0.105, 1)      # 青铜暖灰亮部
        e3 = ramp.color_ramp.elements.new(0.64)
        e3.color = (0.045, 0.115, 0.060, 1)      # 暗绿锈底
        e4 = ramp.color_ramp.elements.new(0.74)
        e4.color = (0.080, 0.220, 0.115, 1)      # 孔雀石绿锈
    else:
        e0 = ramp.color_ramp.elements[0]; e0.position = 0.30
        e0.color = (0.026, 0.028, 0.034, 1)      # 包浆暗部（近黑）
        e1 = ramp.color_ramp.elements.new(0.60)
        e1.color = (0.075, 0.072, 0.070, 1)      # 深灰
        e2 = ramp.color_ramp.elements.new(0.78)
        e2.color = (0.155, 0.135, 0.105, 1)      # 青铜暖灰亮部
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.35
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_relief():
    """棱线亮青铜：细线铸纹的高光面（对应照片抛光棱线）"""
    m = bpy.data.materials.new("Bronze_relief_bright")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.88
    bs.inputs["Roughness"].default_value = 0.30
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.5
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.65
    nt.links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.06, 0.055, 0.05, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.33, 0.27, 0.19, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.3
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_polish():
    m = bpy.data.materials.new("Bronze_mirror_polished")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.085, 0.08, 0.07, 1)
    bs.inputs["Metallic"].default_value = 0.9
    bs.inputs["Roughness"].default_value = 0.22
    return m

def smooth_bevel(obj, amount=0.3, segments=2):
    bev = obj.modifiers.new("soft_edge", 'BEVEL')
    bev.width = amount; bev.segments = segments

def add_cyl(r, h, z, name, mat, verts=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h,
                                       location=(0, 0, z + h / 2))
    o = bpy.context.object; o.name = name
    if mat: o.data.materials.append(mat)
    return o

def add_sphere(r, loc, name, mat, scale_z=1.0, seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=16, radius=r, location=loc)
    o = bpy.context.object; o.name = name
    if scale_z != 1.0:
        o.scale.z = scale_z
        bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

def rect_bar(p0, p1, w, h, z, name, mat, bevel=0.25):
    """任意方向矩形凸条（显式世界坐标顶点）"""
    x0, y0 = p0; x1, y1 = p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    L = math.hypot(x1 - x0, y1 - y0) + w
    a = math.atan2(y1 - y0, x1 - x0)
    ca, sa = cos(a), sin(a)
    hl, hw = L / 2, w / 2
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

def curve_tube(points, bevel, name, mat, cyclic=False, res=2):
    """圆断面细线凸起（细线铸感）"""
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

def spiral_pts(cx, cy, r0, r1, turns, z, steps=26, phase=0.0):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = phase + 2 * pi * turns * t
        r = r0 + (r1 - r0) * t
        pts.append((cx + r * cos(a), cy + r * sin(a), z))
    return pts

def polar(angle_deg, r):
    a = math.radians(angle_deg)
    return (r * cos(a), r * sin(a))

def mesh_object(name, verts, faces, mat):
    me = bpy.data.meshes.new(name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

# ---------------- 1. 镜体（车削剖面） ----------------
def build_body():
    seg = 160
    # 剖面 (r, z)：镜面微凸（中心 -12 → 缘 -7）→ 缘侧 → 背面 z=0
    prof = [(0.0, -CENTER_T), (50.0, -CENTER_T + 1.0), (74.0, -RIM_T - 1.4),
            (88.0, -RIM_T - 0.4), (R, -RIM_T), (R, 0.0), (0.0, 0.0)]
    rings = len(prof)
    verts = []
    for i in range(seg):
        a = 2 * pi * i / seg
        for (r, z) in prof:
            verts.append((r * cos(a), r * sin(a), z))
    faces = []
    for i in range(seg):
        ni = (i + 1) % seg
        for j in range(rings - 1):
            faces.append((i * rings + j, ni * rings + j,
                          ni * rings + j + 1, i * rings + j + 1))
    me = bpy.data.meshes.new("body_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(MAT_BRONZE)
    me.materials.append(MAT_POLISH)
    ob = bpy.data.objects.new("01_镜体_MirrorBody", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
        # 镜面段（前两个剖面区间）指抛光材质
        cz = sum(me.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        p.material_index = 1 if cz < -2.0 else 0
    return ob

# ---------------- 2. 圆钮（扁半球车削 + 基部锈环） ----------------
def build_knob():
    seg = 96
    # 扁半球剖面：顶 (0,8) → 底缘 (14,0)
    arc = 32
    prof = []
    for i in range(arc + 1):
        t = i / arc
        a = t * pi / 2
        prof.append((R_KNOB * sin(a), H_KNOB * cos(a)))
    prof += [(R_KNOB, -1.2), (0.0, -1.2)]   # 下沉嵌入镜体
    rings = len(prof)
    verts = []
    for i in range(seg):
        a = 2 * pi * i / seg
        for (r, z) in prof:
            verts.append((r * cos(a), r * sin(a), z))
    faces = []
    for i in range(seg):
        ni = (i + 1) % seg
        for j in range(rings - 1):
            faces.append((i * rings + j, ni * rings + j,
                          ni * rings + j + 1, i * rings + j + 1))
    me = bpy.data.meshes.new("knob_mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(MAT_PATINA)
    ob = bpy.data.objects.new("02_镜钮_KnobHemisphere", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    # 基部锈环（照片上钮座周围的锈 collar）
    bpy.ops.mesh.primitive_torus_add(major_radius=R_KNOB + 1.2, minor_radius=1.6,
                                    major_segments=64, minor_segments=12,
                                    location=(0, 0, 0.4))
    collar = bpy.context.object; collar.name = "02b_钮座锈环"
    collar.data.materials.append(MAT_PATINA)
    return ob

# ---------------- 3. 双线方框 + 十二乳钉 ----------------
def build_square():
    parts = []
    a_in = SQ_HALF - SQ_GAP / 2 - SQ_LINE_W / 2     # 内线中心 31.75
    a_out = SQ_HALF + SQ_GAP / 2 + SQ_LINE_W / 2    # 外线中心 34.25
    for k, s in (("内", a_in), ("外", a_out)):
        edges = [((-s, -s), (s, -s)), ((s, -s), (s, s)),
                 ((s, s), (-s, s)), ((-s, s), (-s, -s))]
        for i, (p0, p1) in enumerate(edges):
            parts.append(rect_bar(p0, p1, SQ_LINE_W, SQ_H, BACK_Z,
                                  f"03_方框{k}_edge{i}", MAT_BRONZE, bevel=0.2))
    # 十二乳钉：顶 4、底 4、左右各 2（均不含角）
    n = 0
    for x in (-24.75, -8.25, 8.25, 24.75):          # 顶边
        parts.append(add_sphere(NIP_R, (x, SQ_HALF, BACK_Z + SQ_H), f"03_乳钉_{n:02d}",
                                MAT_BRONZE, scale_z=0.7)); n += 1
    for x in (-24.75, -8.25, 8.25, 24.75):          # 底边
        parts.append(add_sphere(NIP_R, (x, -SQ_HALF, BACK_Z + SQ_H), f"03_乳钉_{n:02d}",
                                MAT_BRONZE, scale_z=0.7)); n += 1
    for y in (-11.0, 11.0):                          # 左边
        parts.append(add_sphere(NIP_R, (-SQ_HALF, y, BACK_Z + SQ_H), f"03_乳钉_{n:02d}",
                                MAT_BRONZE, scale_z=0.7)); n += 1
    for y in (-11.0, 11.0):                          # 右边
        parts.append(add_sphere(NIP_R, (SQ_HALF, y, BACK_Z + SQ_H), f"03_乳钉_{n:02d}",
                                MAT_BRONZE, scale_z=0.7)); n += 1
    return parts

# ---------------- 4. 方框内地纹：云气涡纹 + 小型笔画 ----------------
def build_inner_field():
    parts = []
    # 钮周云气涡纹（r 17–29 环形散布，避开钮）
    spots = [(20, 20), (30, 55), (22, 100), (28, 145), (19, 195),
             (30, 240), (22, 285), (26, 330),
             (-30, 15), (-25, 165), (-28, 255), (-20, 75)]
    for i, (rr, ad) in enumerate(spots):
        cx, cy = polar(ad, rr)
        parts.append(curve_tube(
            spiral_pts(cx, cy, 0.5, 2.1, 1.15, BACK_Z + 0.8, steps=20),
            0.42, f"04_内地纹_云涡{i:02d}", MAT_BRONZE))
    # 方框四边内侧的小型 T 形笔画（对应照片上框内缘的小横画组）
    for i, ad in enumerate((0, 90, 180, 270)):
        a = math.radians(ad)
        bx, by = 29.5 * cos(a), 29.5 * sin(a)
        tx, ty = -sin(a), cos(a)
        pts = [(bx + 3.2 * tx, by + 3.2 * ty, BACK_Z + 0.8),
               (bx, by, BACK_Z + 0.8),
               (bx - 3.2 * tx, by - 3.2 * ty, BACK_Z + 0.8)]
        parts.append(curve_tube(pts, 0.4, f"04_内地纹_横画{i}", MAT_BRONZE))
        stem = [(bx, by, BACK_Z + 0.8), (bx - 3.5 * cos(a), by - 3.5 * sin(a), BACK_Z + 0.8)]
        parts.append(curve_tube(stem, 0.4, f"04_内地纹_竖画{i}", MAT_BRONZE))
    return parts

# ---------------- 5. 八乳圆圈座（r=52，22.5°+45°k） ----------------
def build_eight_nipples():
    parts = []
    for i in range(8):
        ad = 22.5 + 45 * i
        cx, cy = polar(ad, R_8NIP)
        # 圆座底盘 + 凸起圆环（torus）+ 半球乳钉
        parts.append(add_cyl(SEAT_R, 0.4, BACK_Z, f"05_乳座{i}_盘", MAT_BRONZE, verts=64))
        bpy.ops.mesh.primitive_torus_add(major_radius=5.6, minor_radius=0.9,
                                        major_segments=48, minor_segments=10,
                                        location=(cx, cy, 0.9))
        ring = bpy.context.object; ring.name = f"05_乳座{i}_环"
        ring.data.materials.append(MAT_BRONZE)
        parts.append(ring)
        parts.append(add_sphere(SEAT_NIP_R, (cx, cy, BACK_Z + 0.4),
                                f"05_乳座{i}_乳", MAT_BRONZE, scale_z=0.72))
    return parts

# ---------------- 6. 细线 TLV（细线铸感，圆断面 tube） ----------------
def build_tlv():
    parts = []
    z = BACK_Z + 0.85
    w = 0.62   # 线径
    # T ×4：四方，柄朝心、横杠朝外
    for k, ad in enumerate((90, 0, 270, 180)):    # N E S W
        a = math.radians(ad)
        ux, uy = cos(a), sin(a)          # 径向（外）
        tx, ty = -sin(a), cos(a)         # 切向
        stem = [(38 * ux, 38 * uy, z), (45 * ux, 45 * uy, z)]
        parts.append(curve_tube(stem, w, f"06_T{k}_柄", MAT_RELIEF))
        bar = [(45 * ux + 3.6 * tx, 45 * uy + 3.6 * ty, z),
               (45 * ux - 3.6 * tx, 45 * uy - 3.6 * ty, z)]
        parts.append(curve_tube(bar, w, f"06_T{k}_杠", MAT_RELIEF))
        # 根部短横（照片上 T 靠内还有一小杠）
        bar2 = [(40.5 * ux + 2.4 * tx, 40.5 * uy + 2.4 * ty, z),
                (40.5 * ux - 2.4 * tx, 40.5 * uy - 2.4 * ty, z)]
        parts.append(curve_tube(bar2, w * 0.85, f"06_T{k}_内杠", MAT_RELIEF))
    # L ×4：对角，径向臂 + 端部切向钩（顺时针）
    for k, ad in enumerate((45, 135, 225, 315)):
        a = math.radians(ad)
        ux, uy = cos(a), sin(a)
        tx, ty = -sin(a), cos(a)
        arm = [(38.5 * ux, 38.5 * uy, z), (45.5 * ux, 45.5 * uy, z)]
        parts.append(curve_tube(arm, w, f"06_L{k}_臂", MAT_RELIEF))
        p = (45.5 * ux, 45.5 * uy)
        hook = [(p[0], p[1], z), (p[0] + 5.5 * tx, p[1] + 5.5 * ty, z)]
        parts.append(curve_tube(hook, w, f"06_L{k}_钩", MAT_RELIEF))
    # V ×4：位于 T 与 L 之间（22.5°+90°k），尖朝外
    for k, ad in enumerate((22.5, 112.5, 202.5, 292.5)):
        a = math.radians(ad)
        ux, uy = cos(a), sin(a)
        tx, ty = -sin(a), cos(a)
        tipx, tipy = 41.5 * ux, 41.5 * uy
        for j, s in ((0, 1), (1, -1)):
            arm = [(tipx, tipy, z),
                   (tipx - 6.0 * ux + 3.6 * s * tx, tipy - 6.0 * uy + 3.6 * s * ty, z)]
            parts.append(curve_tube(arm, w * 0.9, f"06_V{k}_{j}", MAT_RELIEF))
    return parts

# ---------------- 7. 四神（细线高浮雕） ----------------
def spirit_dragon(cx, cy):
    """青龙：S 躯 + 首 + 双角 + 四肢 + 卷尾（东，头朝北）"""
    z = BACK_Z + 1.15
    parts = []
    pts = []
    for i in range(30):
        t = i / 29
        x = -9.5 + 19 * t
        y = 3.6 * sin(t * 1.8 * pi)
        pts.append((cx + x, cy + y, z))
    parts.append(curve_tube(pts, 1.35, "07_四神_青龙躯", MAT_RELIEF))
    hx, hy = pts[-1][0], pts[-1][1]
    parts.append(add_sphere(2.5, (hx + 1.0, hy + 0.6, z + 0.4), "07_龙首",
                            MAT_BRONZE, scale_z=0.85))
    parts.append(curve_tube([(hx + 0.6, hy + 1.8, z + 1.2),
                             (hx - 0.4, hy + 3.6, z + 1.9),
                             (hx - 2.0, hy + 4.4, z + 1.5)],
                            0.65, "07_龙角", MAT_RELIEF))
    for j, (lx, ly, s) in enumerate(((cx - 5.5, 2.6, 1), (cx - 1, -2.6, -1), (cx + 4.5, 2.8, 1))):
        parts.append(curve_tube([(lx, ly, z), (lx + 1.4, ly + 2.2 * s, z),
                                 (lx + 3.4, ly + 2.6 * s, z)],
                                0.75, f"07_龙足{j}", MAT_RELIEF))
    t0 = pts[0]
    parts.append(curve_tube([(t0[0], t0[1], z), (t0[0] - 2.6, t0[1] - 2.4, z)],
                            0.7, "07_龙尾", MAT_RELIEF))
    return parts

def spirit_tiger(cx, cy):
    """白虎：伏身 + 巨头 + 卷尾 + 斑条（西，头朝南）"""
    z = BACK_Z + 1.15
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=5.2,
                                        location=(cx, cy, z))
    body = bpy.context.object; body.name = "07_四神_白虎身"
    body.scale = (1.15, 1.45, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    body.data.materials.append(MAT_RELIEF); bpy.ops.object.shade_smooth()
    parts.append(body)
    parts.append(add_sphere(3.0, (cx, cy - 6.4, z + 0.5), "07_虎首",
                            MAT_BRONZE, scale_z=0.85))
    parts.append(curve_tube([(cx - 1.4, cy + 5.6, z),
                             (cx - 3.4, cy + 8.0, z + 0.6),
                             (cx - 2.6, cy + 10.2, z + 1.2)],
                            1.0, "07_虎尾", MAT_RELIEF))
    for j, (lx, s) in enumerate(((-2.2, 1), (2.2, 1))):
        parts.append(curve_tube([(cx + lx, cy + 1.5, z + 1.2), (cx + lx + 1.6 * s, cy + 1.8, z + 1.2)],
                                0.4, f"07_虎斑{j}", MAT_RELIEF))
    return parts

def spirit_bird(cx, cy):
    """朱雀：立身 + 双翼展 + 三尾羽（南，头朝东）"""
    z = BACK_Z + 1.15
    parts = []
    parts.append(add_sphere(2.3, (cx, cy, z + 0.6), "07_四神_朱雀身",
                            MAT_BRONZE, scale_z=1.25))
    parts.append(add_sphere(1.3, (cx + 1.4, cy + 1.6, z + 1.6), "07_雀首",
                            MAT_BRONZE, scale_z=0.9))
    for s in (1, -1):
        pts = [(cx + 0.6, cy + 1.2 * s * 0.4, z + 1.2),
               (cx + 3.5, cy + 4.0 * s, z + 1.4),
               (cx + 7.5, cy + 4.8 * s, z + 1.6),
               (cx + 9.5, cy + 2.4 * s, z + 1.5)]
        parts.append(curve_tube(pts, 1.05, f"07_雀翼{'L' if s < 0 else 'R'}", MAT_RELIEF))
    for j, s in enumerate((0.5, 0.0, -0.5)):
        parts.append(curve_tube([(cx - 0.6, cy + s * 1.2, z + 0.4),
                                 (cx - 5.5, cy + s * 4.5, z + 0.3)],
                                0.7, f"07_雀尾{j}", MAT_RELIEF))
    return parts

def spirit_tortoise(cx, cy):
    """玄武：龟 + 蛇缠（北，龟头朝南）"""
    z = BACK_Z + 1.15
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=4.2,
                                        location=(cx, cy, z))
    t = bpy.context.object; t.name = "07_四神_玄武龟"
    t.scale = (1.05, 1.3, 0.6)
    bpy.ops.object.transform_apply(scale=True)
    t.data.materials.append(MAT_RELIEF); bpy.ops.object.shade_smooth()
    parts.append(t)
    parts.append(add_sphere(1.5, (cx, cy - 5.6, z + 0.4), "07_龟头",
                            MAT_BRONZE, scale_z=0.8))
    parts.append(curve_tube([(cx, cy - 6.8, z), (cx, cy - 8.2, z)], 0.5, "07_龟尾", MAT_RELIEF))
    pts = []
    for i in range(22):
        tt = i / 21
        pts.append((cx - 3.4 + 6.8 * tt, cy + 2.8 * sin(tt * 2.4 * pi), z + 1.8 + 0.8 * sin(tt * pi)))
    parts.append(curve_tube(pts, 0.9, "07_玄武蛇", MAT_RELIEF))
    return parts

def build_spirits():
    parts = []
    parts += spirit_tortoise(*polar(90, 56))    # 北
    parts += spirit_dragon(*polar(0, 56))       # 东
    parts += spirit_bird(*polar(270, 56))       # 南
    parts += spirit_tiger(*polar(180, 56))      # 西
    return parts

# ---------------- 8. 四神区间云气 ----------------
def build_cloud_scrolls():
    parts = []
    spots = []
    # 对角区间（L 两侧）主涡卷
    for ad in (45, 135, 225, 315):
        spots += [(ad - 13, 55.5), (ad + 13, 49.5)]
    # T 两侧填空小涡
    for ad in (0, 90, 180, 270):
        spots += [(ad - 14, 47.0), (ad + 14, 58.5)]
    for i, (ad, rr) in enumerate(spots):
        cx, cy = polar(ad, rr)
        parts.append(curve_tube(
            spiral_pts(cx, cy, 0.5, 2.3, 1.15, BACK_Z + 0.85, steps=22),
            0.55, f"08_云气_涡{i:02d}", MAT_RELIEF))
        # 每涡配一小勾
        a = math.radians(ad)
        p0 = (cx + 1.8 * cos(a + 1.2), cy + 1.8 * sin(a + 1.2), BACK_Z + 0.85)
        p1 = (cx + 3.6 * cos(a + 1.0), cy + 3.6 * sin(a + 1.0), BACK_Z + 0.85)
        parts.append(curve_tube([p0, p1], 0.45, f"08_云气_勾{i:02d}", MAT_RELIEF))
    return parts

# ---------------- 9. 栉齿纹带（细密放射直线，合并单网格） ----------------
def build_hatch():
    n = 190
    verts, faces = [], []
    w = 0.45
    h = 0.7
    for i in range(n):
        a = 2 * pi * i / n
        ca, sa = cos(a), sin(a)
        tx, ty = -sa, ca
        base = len(verts)
        for zz in (BACK_Z, BACK_Z + h):
            for (rr, ss) in ((R_HATCH_IN, -w), (R_HATCH_IN, w),
                             (R_HATCH_OUT, w), (R_HATCH_OUT, -w)):
                verts.append(((rr) * ca + ss * tx, rr * sa + ss * ty, zz))
        faces += [(base + 0, base + 1, base + 2, base + 3),
                  (base + 7, base + 6, base + 5, base + 4),
                  (base + 0, base + 4, base + 5, base + 1),
                  (base + 1, base + 5, base + 6, base + 2),
                  (base + 2, base + 6, base + 7, base + 3),
                  (base + 3, base + 7, base + 4, base + 0)]
    return [mesh_object("09_栉齿纹带_HatchBand", verts, faces, MAT_BRONZE)]

# ---------------- 10. 锯齿纹带（三角齿环，合并单网格） ----------------
def build_zigzag():
    n = 96
    verts, faces = [], []
    h = 0.9
    for i in range(n):
        a = 2 * pi * i / n
        ca, sa = cos(a), sin(a)
        tx, ty = -sa, ca
        hw = 1.7
        base = len(verts)
        # 三角截面：内缘两点 + 外尖
        for zz in (BACK_Z, BACK_Z + h):
            verts.append((R_ZIG_IN * ca - hw * tx, R_ZIG_IN * sa - hw * ty, zz))
            verts.append((R_ZIG_IN * ca + hw * tx, R_ZIG_IN * sa + hw * ty, zz))
            verts.append(((R_ZIG_OUT + 0.3) * ca, (R_ZIG_OUT + 0.3) * sa, zz))
        faces += [(base + 0, base + 1, base + 2),
                  (base + 5, base + 4, base + 3),
                  (base + 0, base + 3, base + 4, base + 1),
                  (base + 1, base + 4, base + 5, base + 2),
                  (base + 2, base + 5, base + 3, base + 0)]
    return [mesh_object("10_锯齿纹带_ZigzagBand", verts, faces, MAT_BRONZE)]

# ---------------- 11. 镜缘云气纹带（连续 S 形卷云，视觉重点） ----------------
def build_rim_clouds():
    parts = []
    r_mid = (R_CLOUD_IN + R_LIP) / 2 + 0.5   # ~83.5
    z = BACK_Z + 1.2
    # 一条贯穿全带的连续 S 波（正弦蛇形阳线）
    pts = []
    steps = 768
    for j in range(steps + 1):
        a = 2 * pi * j / steps
        r = r_mid + 5.4 * sin(12 * a)
        pts.append((r * cos(a), r * sin(a), z))
    parts.append(curve_tube(pts, 1.2, "11_缘云_波带", MAT_PATINA))
    # 波峰 / 波谷各接一个螺旋卷（共 24 个），使云带饱满连续
    for k in range(24):
        a_c = 2 * pi * k / 24
        sgn = 1 if k % 2 == 0 else -1
        cr = r_mid + 5.4 * sgn
        ccx, ccy = cr * cos(a_c), cr * sin(a_c)
        parts.append(curve_tube(
            spiral_pts(ccx, ccy, 0.9, 3.1, 1.3 * sgn, z, steps=22,
                       phase=a_c + sgn * pi / 2),
            0.95, f"11_缘云_卷{k:02d}", MAT_PATINA))
    # 波带两侧填空小涡（位于中性半径处）
    for k in range(12):
        a_c = 2 * pi * (k + 0.5) / 12
        ccx, ccy = r_mid * cos(a_c), r_mid * sin(a_c)
        parts.append(curve_tube(
            spiral_pts(ccx, ccy, 0.6, 2.0, 1.0, z, steps=16, phase=a_c),
            0.8, f"11_缘云_填{k:02d}", MAT_PATINA))
    # 内外缘界圈（阳线，圈住云气带）
    for k, rr in ((0, R_CLOUD_IN + 0.8), (1, R_LIP - 0.6)):
        pts = [(rr * cos(2 * pi * t / 128), rr * sin(2 * pi * t / 128), z)
               for t in range(129)]
        parts.append(curve_tube(pts, 0.7, f"11_缘界圈{k}", MAT_PATINA, cyclic=False))
    return parts

# ---------------- 12. 缘唇（外缘圆角凸起） ----------------
def build_lip():
    bpy.ops.mesh.primitive_torus_add(major_radius=R_LIP, minor_radius=1.9,
                                    major_segments=128, minor_segments=16,
                                    location=(0, 0, 0.6))
    o = bpy.context.object; o.name = "12_缘唇_RimLip"
    o.data.materials.append(MAT_PATINA)
    return [o]

# ---------------- 组装 ----------------
def main():
    global MAT_BRONZE, MAT_PATINA, MAT_POLISH, MAT_RELIEF
    clean_scene()
    MAT_BRONZE = mat_bronze("Bronze_heiqigu", patina=0.15, rough=0.40)
    MAT_PATINA = mat_bronze("Bronze_patina_knob_rim", patina=1.0, rough=0.48)
    MAT_POLISH = mat_polish()
    MAT_RELIEF = mat_relief()
    build_body()
    build_knob()
    build_square()
    build_inner_field()
    build_eight_nipples()
    build_tlv()
    build_spirits()
    build_cloud_scrolls()
    build_hatch()
    build_zigzag()
    build_rim_clouds()
    build_lip()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(
        filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/tlv_mirror_1995_301.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
