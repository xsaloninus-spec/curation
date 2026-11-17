# -*- coding: utf-8 -*-
"""
清晚期蓝透明珐琅描金喜字把镜 —— 故宫博物院 故00180346
通长 279 mm、宽 125 mm（馆方）。清宫旧藏，广东进呈。
馆方主图仅展示镜面一侧；镜背布局（卍字地/囍/八宝）依据馆方文字描述数字化布置，非精确复原。
头部形状以官方照片为准（圆形）；柄部各段尺寸为照片比例推定。
Blender 4.5 headless: Blender -b --factory-startup --python build_dpm_handmirror.py
"""
import bpy
import math, os
from math import sin, cos, pi

# ---------------- 参数（mm） ----------------
HEAD_R = 62.5           # 镜身半径（宽 125 馆方 → 圆头直径 125，照片为准）
HEAD_T = 10.0           # 镜身厚（推定）
RIM_W = 9.0             # 珐琅镜圈宽（照片比例）
NECK_L = 28.0           # 染牙连接件长（推定）
BEAD_L = 9.0            # 珊瑚珠长（推定）
HANDLE_L = 165.0        # 柄长（推定，使通长≈279）
FERRULE_L = 14.0        # 金箍长（推定）
Y_TOP = 0.0             # 镜身中心在原点，各段沿 -Y 排布

BLUE = None; GOLD = None; GLASSM = None; IVORY = None
CORAL = None; GILT = None; SILK = None

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

def ring_band(r_in, r_out, z0, z1, name, mat, seg=128):
    verts, faces = [], []
    for z in (z0, z1):
        for r in (r_in, r_out):
            for i in range(seg):
                th = 2 * pi * i / seg
                verts.append((r * cos(th), r * sin(th), z))
    for i in range(seg):
        ni = (i + 1) % seg
        faces += [(i, ni, 2 * seg + ni, 2 * seg + i),
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

def mat_principled(name, color, metallic, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = color
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = rough
    return m

def mat_blue_enamel():
    m = bpy.data.materials.new("Blue_transparent_enamel")
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (0.035, 0.06, 0.30, 1)
    bs.inputs["Metallic"].default_value = 0.35
    bs.inputs["Roughness"].default_value = 0.16
    bs.inputs["Coat Weight"].default_value = 0.55
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    noise.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.03, 0.05, 0.24, 1)
    ramp.color_ramp.elements[1].color = (0.10, 0.16, 0.48, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_glass_mirror():
    m = bpy.data.materials.new("Glass_mirror_aged")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.70, 0.74, 0.74, 1)
    bs.inputs["Metallic"].default_value = 0.5
    bs.inputs["Roughness"].default_value = 0.33
    return m

def mat_ivory_green():
    m = bpy.data.materials.new("Ivory_peacock_green")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.10, 0.34, 0.22, 1)
    bs.inputs["Roughness"].default_value = 0.38
    return m

def mat_silk():
    m = bpy.data.materials.new("Silk_yellow")
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (0.72, 0.58, 0.16, 1)
    bs.inputs["Roughness"].default_value = 0.75
    return m

# ---------------- 1. 镜身（圆头） + 玻璃镜面 ----------------
def build_head():
    # 镜身壳体
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=HEAD_R, depth=HEAD_T, location=(0, 0, 0))
    head = bpy.context.object; head.name = "01_镜身_圆头_Head"
    head.data.materials.append(GILT)
    bevel = head.modifiers.new("soft", 'BEVEL'); bevel.width = 1.2; bevel.segments = 3
    # 玻璃镜面（正面微凸）
    add_sphere(HEAD_R - 1.5, (0, 0, -HEAD_T / 2 - 0.6), "02_玻璃镜面_MirrorGlass", GLASSM,
               scale=(1, 1, 0.12), seg=48)
    # 镜背底板（蓝珐琅地）
    add_cylinder = None
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=HEAD_R - RIM_W + 1.5, depth=1.6,
                                      location=(0, 0, HEAD_T / 2 + 0.8))
    back = bpy.context.object; back.name = "03_镜背底板_蓝珐琅地"
    back.data.materials.append(BLUE)

# ---------------- 2. 镜背纹饰（卍字地 / 囍 / 八宝——依馆方文字的数字化布局） ----------------
def wan_symbol(cx, cy, z, s, name):
    """卍字：方折回纹曲线，s=半宽"""
    pts = [(cx - s, cy - s), (cx - s, cy + s), (cx, cy + s), (cx, cy),
           (cx + s, cy), (cx + s, cy + s), (cx, cy + s)]
    curve_tube([(x, y, z) for x, y in pts], 0.42, name, GOLD)

def build_back_decor():
    z = HEAD_T / 2 + 1.7
    # 卍字纹地：环形阵列小卍字
    for ring, (rc, n, s) in enumerate(((26, 8, 2.6), (40, 12, 2.4))):
        for i in range(n):
            a = 2 * pi * i / n + ring * 0.26
            wan_symbol(rc * cos(a), rc * sin(a), z, s, f"03b_卍字地_{ring}_{i}")
    # 中央囍字：优先加载系统中文字体
    xizi_ok = False
    font_paths = ["/System/Library/Fonts/PingFang.ttc",
                  "/System/Library/Fonts/STHeiti Light.ttc",
                  "/System/Library/Fonts/Hiragino Sans GB.ttc"]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                fnt = bpy.data.fonts.load(fp)
                cu = bpy.data.curves.new("Xizi_curve", 'FONT')
                cu.body = "囍"
                cu.font = fnt
                cu.size = 26
                cu.extrude = 1.2
                cu.bevel_depth = 0.3
                cu.materials.append(GOLD)
                ob = bpy.data.objects.new("03c_囍字_DoubleHappiness", cu)
                bpy.context.scene.collection.objects.link(ob)
                ob.location = (0, 0, z + 0.3)
                xizi_ok = True
                break
            except Exception:
                continue
    if not xizi_ok:
        # 回退：双喜方结装饰（标注于文档）
        for sx in (-6.5, 6.5):
            curve_tube([(sx - 4, -8, z), (sx - 4, 8, z), (sx + 4, 8, z),
                        (sx + 4, -8, z), (sx - 4, -8, z)], 0.9,
                       f"03c_喜字结_{sx}", GOLD)
    # 八宝（环绕推定布局，r≈48 内外圈各四）
    r8 = 47.5
    treasures = ["法轮", "法螺", "宝伞", "白盖", "莲花", "宝罐", "金鱼", "盘肠"]
    for i, nm in enumerate(treasures):
        a = pi / 2 + i * 2 * pi / 8
        cx, cy = r8 * cos(a), r8 * sin(a)
        gname = f"03d_八宝_{nm}"
        zt = z
        if nm == "法轮":
            pts = [(cx + 4.4 * cos(2 * pi * k / 24), cy + 4.4 * sin(2 * pi * k / 24), zt)
                   for k in range(25)]
            curve_tube(pts, 0.5, gname + "_轮", GOLD, cyclic=True)
            for k in range(4):
                aa = k * pi / 4
                curve_tube([(cx, cy, zt), (cx + 4 * cos(aa), cy + 4 * sin(aa), zt)],
                           0.4, f"{gname}_辐{k}", GOLD)
        elif nm == "法螺":
            pts = []
            for k in range(20):
                t = k / 19
                rr = 0.4 + 4.0 * t
                aa = a + 2.6 * pi * t
                pts.append((cx + rr * cos(aa), cy + rr * sin(aa), zt + 0.3 * t))
            curve_tube(pts, 0.6, gname + "_螺", GOLD)
        elif nm in ("宝伞", "白盖"):
            pts = [(cx + 5.2 * cos(pi * k / 16 + pi), cy + 5.2 * sin(pi * k / 16 + pi), zt)
                   for k in range(17)]
            curve_tube(pts, 0.55, gname + "_盖", GOLD)
            curve_tube([(cx, cy - 5.2, zt), (cx, cy + 3.5, zt)], 0.45, gname + "_杆", GOLD)
            if nm == "白盖":
                for k in range(3):
                    curve_tube([(cx - 3 + k * 3, cy - 4.6, zt), (cx - 3 + k * 3, cy - 6.4, zt)],
                               0.35, f"{gname}_旒{k}", GOLD)
        elif nm == "莲花":
            for k in range(8):
                aa = 2 * pi * k / 8
                add_sphere(1.5, (cx + 2.2 * cos(aa), cy + 2.2 * sin(aa), zt), gname + f"_瓣{k}",
                           GOLD, scale=(1.5, 0.7, 0.45), seg=10)
            add_sphere(1.0, (cx, cy, zt + 0.4), gname + "_心", GOLD, seg=10)
        elif nm == "宝罐":
            add_sphere(2.4, (cx, cy + 1.2, zt), gname + "_罐身", GOLD, scale=(1, 1, 0.85), seg=12)
            curve_tube([(cx - 2.2, cy - 2.2, zt), (cx + 2.2, cy - 2.2, zt)], 0.5, gname + "_座", GOLD)
            add_sphere(0.9, (cx, cy + 3.6, zt), gname + "_盖钮", GOLD, seg=10)
        elif nm == "金鱼":
            add_sphere(2.0, (cx + 0.8, cy, zt), gname + "_鱼身", GOLD,
                       scale=(1.5, 0.7, 0.4), seg=12)
            curve_tube([(cx - 2.2, cy, zt), (cx - 4.4, cy + 1.6, zt), (cx - 4.4, cy - 1.6, zt),
                        (cx - 2.2, cy, zt)], 0.5, gname + "_尾", GOLD)
            add_sphere(0.5, (cx + 3.4, cy + 0.6, zt + 0.3), gname + "_目", BLUE, seg=8)
        else:  # 盘肠
            for k in range(2):
                off = -1.6 + k * 3.2
                curve_tube([(cx + off, cy - 3.4, zt), (cx + off, cy + 3.4, zt),
                            (cx - off, cy + 3.4, zt), (cx - off, cy - 3.4, zt),
                            (cx + off, cy - 3.4, zt)], 0.55, f"{gname}_结{k}", GOLD)

# ---------------- 3. 蓝珐琅描金镜圈 ----------------
def build_rim():
    r_in, r_out = HEAD_R - RIM_W, HEAD_R + 1.0
    ring_band(r_in, r_out, -HEAD_T / 2 - 0.5, HEAD_T / 2 + 0.5, "04_蓝珐琅镜圈_EnamelRim", BLUE)
    # 内外细金线
    for r, nm in ((r_in + 0.4, "内"), (r_out - 0.4, "外")):
        pts = [(r * cos(2 * pi * i / 96), r * sin(2 * pi * i / 96), -(HEAD_T / 2 + 0.9))
               for i in range(97)]
        curve_tube(pts, 0.5, f"04_金线缘{nm}", GOLD, cyclic=True)
    # 描金花卉：12 组缠枝小花
    rc = (r_in + r_out) / 2
    for i in range(12):
        a0 = 2 * pi * i / 12
        cx, cy = rc * cos(a0), rc * sin(a0)
        for k in range(5):
            aa = a0 + 2 * pi * k / 5
            add_sphere(1.15, (cx + 1.7 * cos(aa), cy + 1.7 * sin(aa), -(HEAD_T / 2 + 1.0)),
                       f"04_金花卉_{i}_瓣{k}", GOLD, scale=(1.5, 0.75, 0.4), seg=10)
        add_sphere(0.6, (cx, cy, -(HEAD_T / 2 + 1.15)), f"04_金花卉_{i}_心", GOLD, seg=8)
        # 枝藤 S 连接
        a1 = a0 + 2 * pi / 24
        pts = []
        for k in range(9):
            t = k / 8
            aa = a0 + (a1 - a0) * t
            rr = rc + 1.8 * sin(t * pi)
            pts.append((rr * cos(aa), rr * sin(aa), -(HEAD_T / 2 + 0.95)))
        curve_tube(pts, 0.4, f"04_金藤蔓_{i}", GOLD)

# ---------------- 4. 染牙连接件 + 珊瑚珠 ----------------
def build_neck():
    y0 = -HEAD_R - NECK_L / 2 + 4
    # 孔雀绿染牙：饱满梭形
    add_sphere(7.5, (0, y0, 0), "05_染牙连接器_IvoryNeck", IVORY,
               scale=(1.0, NECK_L / 12.0, 0.85), seg=24)
    # 卷草雕刻线（染牙表面）
    for s in (1, -1):
        pts = []
        for k in range(14):
            t = k / 13
            yy = y0 + (NECK_L / 2 - 2) * (1 - 2 * t)
            xx = s * (4.5 + 1.5 * sin(t * 3 * pi))
            pts.append((xx, yy, 5.2 - 1.2 * abs(1 - 2 * t)))
        curve_tube(pts, 0.5, f"05_染牙卷草_{s}", GOLD)
    # 刻瓜式珊瑚珠（纵向凹槽）
    by = y0 - NECK_L / 2 - BEAD_L / 2 + 1
    add_sphere(BEAD_L / 2, (0, by, 0), "06_珊瑚珠_CoralBead", CORAL,
               scale=(1.0, 1.15, 1.0), seg=24)
    for k in range(6):
        aa = 2 * pi * k / 6
        curve_tube([(2.1 * cos(aa), by - BEAD_L / 2 + 0.6, 2.1 * sin(aa)),
                    (2.3 * cos(aa), by, 2.3 * sin(aa)),
                    (2.1 * cos(aa), by + BEAD_L / 2 - 0.6, 2.1 * sin(aa))],
                   0.4, f"06_珠凹槽_{k}", CORAL)
    return by

# ---------------- 5. 蓝珐琅描金直柄 + 金箍 ----------------
def build_handle(bead_y):
    hy0 = bead_y - BEAD_L / 2
    y_c = hy0 - HANDLE_L / 2
    # 柄身：锥形圆柱，轴向 Y
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=6.0, radius2=7.2,
                                    depth=HANDLE_L, location=(0, y_c, 0),
                                    rotation=(pi / 2, 0, 0))
    h = bpy.context.object; h.name = "07_蓝珐琅柄_EnamelHandle"
    h.data.materials.append(BLUE)
    bevel = h.modifiers.new("soft", 'BEVEL'); bevel.width = 1.0; bevel.segments = 2
    # 柄身描金缠枝
    for k in range(5):
        yy = y_c + HANDLE_L / 2 - 12 - k * 30
        pts = []
        for i in range(17):
            t = i / 16
            aa = 2 * pi * 2.2 * t + k * 1.3
            rr = 6.4 + 0.35 * sin(t * pi)
            pts.append((rr * cos(aa), yy - 8 * t, rr * sin(aa)))
        curve_tube(pts, 0.4, f"07_柄描金_{k}", GOLD)
    # 柄端铜镀金箍
    fy = y_c - HANDLE_L / 2 - FERRULE_L / 2 + 1
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=6.4, depth=FERRULE_L,
                                        location=(0, fy, 0), rotation=(pi / 2, 0, 0))
    f = bpy.context.object; f.name = "08_铜镀金箍_Ferrule"
    f.data.materials.append(GILT)
    bevel = f.modifiers.new("soft", 'BEVEL'); bevel.width = 0.8; bevel.segments = 2
    # 箍上錾刻环棱
    for k in range(2):
        yy = fy + (k - 0.5) * FERRULE_L * 0.45
        pts = [(6.55 * cos(2 * pi * i / 32), yy, 6.55 * sin(2 * pi * i / 32))
               for i in range(33)]
        curve_tube(pts, 0.35, f"08_箍棱_{k}", GOLD, cyclic=True)
    return fy - FERRULE_L / 2

# ---------------- 6. 黄丝线穗 + 珊瑚珠 ----------------
def build_tassel(end_y):
    # 系绳（双股）+ 穗头束腰 + 细丝穗
    tie_y = end_y - 2
    pts = []
    for k in range(13):
        t = k / 12
        pts.append((0.8 * sin(t * pi), tie_y - 6 * t, 0.6 * cos(t * pi)))
    curve_tube(pts, 0.55, "09_穗系绳", SILK)
    cap_y = tie_y - 7.5
    add_sphere(3.2, (0, cap_y, 0), "09_穗头束", SILK, scale=(1.0, 0.75, 1.0), seg=16)
    # 细丝 24 根自然垂落
    for i in range(24):
        aa = 2 * pi * i / 24
        x0, z0 = 2.4 * cos(aa), 2.4 * sin(aa)
        pts = []
        for k in range(9):
            t = k / 8
            pts.append((x0 * (1 - 0.35 * t) + 0.65 * sin(t * 5 * pi + i),
                        cap_y - 2 - 52 * t,
                        z0 * (1 - 0.35 * t) + 0.55 * cos(t * 4 * pi + i * 1.7)))
        curve_tube(pts, 0.16, f"09_丝线_{i}", SILK)
    # 穗尾珊瑚珠
    add_sphere(2.2, (0.9, cap_y - 50, 0.8), "09_穗尾珊瑚珠", CORAL, scale=(1, 1.15, 1), seg=14)

def main():
    global BLUE, GOLD, GLASSM, IVORY, CORAL, GILT, SILK
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    BLUE = mat_blue_enamel()
    GOLD = mat_principled("Gold_gilt", (0.78, 0.55, 0.16, 1), 1.0, 0.3)
    GLASSM = mat_glass_mirror()
    IVORY = mat_ivory_green()
    CORAL = mat_principled("Coral_red", (0.62, 0.16, 0.10, 1), 0.15, 0.42)
    GILT = mat_principled("Gilt_copper", (0.55, 0.38, 0.12, 1), 1.0, 0.36)
    SILK = mat_silk()
    build_head()
    build_back_decor()
    build_rim()
    bead_y = build_neck()
    end_y = build_handle(bead_y)
    build_tassel(end_y)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    sc.unit_settings.scale_length = 0.001
    bpy.ops.wm.save_as_mainfile(filepath="/Users/wangyaomin/Desktop/策展/文物建模/blender/dpm_xizi_handmirror.blend")
    print("BUILD_OK objects:", len(bpy.data.objects))

main()
