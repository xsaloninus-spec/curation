# -*- coding: utf-8 -*-
"""Cleveland 1995.301 TLV 镜 —— v3 重建（真实几何位移 + 馆方照片反演细节）。

运行：
  Blender -b --factory-startup --python build_tlv_v3.py
输出：
  tlv_v3/tlv_1995_301_v3.blend
  tlv_v3/cleveland_1995_301_tlv_mirror_v3.glb
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
META = json.loads((OUT / "v3_meta.json").read_text())
S = META["size"]
MM_PX = META["mm_per_px"]
Z0 = META["z_base_mm"]

HEIGHT = np.load(OUT / "height_mm_disp.npy").astype(np.float32)
ALBEDO = str(OUT / "v3_albedo_4096.jpg")
NORMAL = str(OUT / "v3_normal_2048.png")
ORM = str(OUT / "v3_orm_2048.png")

R = 95.0
FRONT_RIM_Z = -6.9
FRONT_CENTER_Z = -5.15
RIM_TOP_Z = 0.55


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        pass


def sample_height(x, y):
    """毫米坐标 → 平滑高程（mm），双线性。"""
    col = x / MM_PX + (S - 1) / 2.0
    row = (S - 1) / 2.0 - y / MM_PX
    col = np.clip(col, 0, S - 1.001)
    row = np.clip(row, 0, S - 1.001)
    c0 = np.floor(col).astype(np.int32)
    r0 = np.floor(row).astype(np.int32)
    fc = col - c0
    fr = row - r0
    a = HEIGHT[r0, c0] * (1 - fc) * (1 - fr) + HEIGHT[r0, c0 + 1] * fc * (1 - fr)
    b = HEIGHT[r0 + 1, c0] * (1 - fc) * fr + HEIGHT[r0 + 1, c0 + 1] * fc * fr
    return a + b


def make_object(name, verts, faces, uvs=None):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=np.float32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())

    starts = []
    loop_idx = []
    n = 0
    for f in faces:
        starts.append(n)
        loop_idx.extend(f)
        n += len(f)
    me.loops.add(len(loop_idx))
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.asarray(starts, dtype=np.int32))
    me.loops.foreach_set("vertex_index", np.asarray(loop_idx, dtype=np.int32))
    me.update(calc_edges=True)

    if uvs is not None:
        layer = me.uv_layers.new(name="UVMap")
        uv_per_loop = np.asarray(uvs, dtype=np.float32)[np.asarray(loop_idx)]
        layer.data.foreach_set("uv", uv_per_loop.ravel())

    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def uv_of(x, y):
    return ((x + R) / (2 * R), (y + R) / (2 * R))


# ---------------------------------------------------------------- 镜背
def build_back():
    nr, nt = 320, 1024
    r0 = 11.2
    rs = np.linspace(r0, R, nr + 1)
    th = np.linspace(0, 2 * math.pi, nt, endpoint=False)
    ct, st = np.cos(th), np.sin(th)
    X = rs[:, None] * ct[None, :]
    Y = rs[:, None] * st[None, :]
    Z = sample_height(X, Y)
    Z[-1, :] = RIM_TOP_Z
    # 缘外一圈稍微压平，保证与侧壁对齐
    Z[-2, :] = Z[-2, :] * 0.5 + RIM_TOP_Z * 0.5

    verts = np.dstack([X, Y, Z]).reshape(-1, 3)
    uv = np.dstack([(X + R) / (2 * R), (Y + R) / (2 * R)]).reshape(-1, 2)

    faces = []
    idx = np.arange((nr + 1) * nt).reshape(nr + 1, nt)
    for i in range(nr):
        for j in range(nt):
            j2 = (j + 1) % nt
            a, b = idx[i, j], idx[i, j2]
            c, d = idx[i + 1, j2], idx[i + 1, j]
            faces.append((a, b, c, d))
    return make_object("Mirror_Back", verts, faces, uv)


# ---------------------------------------------------------------- 镜钮
def build_knob():
    prof = [(11.95, Z0 - 0.70), (11.96, Z0 + 0.55), (11.72, Z0 + 1.55),
            (11.05, Z0 + 2.85), (9.85, Z0 + 3.95), (8.05, Z0 + 4.72),
            (5.60, Z0 + 5.20), (3.00, Z0 + 5.45), (0.0, Z0 + 5.52)]
    nt = 192
    th = np.linspace(0, 2 * math.pi, nt, endpoint=False)
    verts, uvs = [], []
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, (64, 64)).astype(np.float32)
    for k, (r, z) in enumerate(prof):
        for j, t in enumerate(th):
            x, y = r * math.cos(t), r * math.sin(t)
            if r > 0.1:
                # 铸造/锈蚀造成的轻微不规则
                ni = int((x + 50) * 0.7) % 64
                nj = int((y + 50) * 0.7) % 64
                jitter = 0.16 * noise[ni, nj]
                x += jitter * math.cos(t)
                y += jitter * math.sin(t)
                zz = z + 0.10 * noise[(nj + 13) % 64, (ni + 29) % 64]
            else:
                zz = z
            verts.append((x, y, zz))
            uvs.append(uv_of(x, y))
    verts.append((0.0, 0.0, Z0 + 5.52))
    uvs.append(uv_of(0, 0))
    top = len(verts) - 1
    faces = []
    idx = np.arange(len(prof) * nt).reshape(len(prof), nt)
    for k in range(len(prof) - 1):
        for j in range(nt):
            j2 = (j + 1) % nt
            faces.append((idx[k, j], idx[k, j2], idx[k + 1, j2], idx[k + 1, j]))
    last = len(prof) - 1
    for j in range(nt):
        j2 = (j + 1) % nt
        faces.append((idx[last, j], idx[last, j2], top))
    return make_object("Mirror_Knob", verts, faces, uvs)


# ---------------------------------------------------------------- 镜体（镜面 + 侧壁）
def build_body():
    prof = [(0.0, FRONT_CENTER_Z)]
    for r in np.linspace(2.0, 92.0, 24):
        prof.append((r, FRONT_RIM_Z + (FRONT_CENTER_Z - FRONT_RIM_Z) * (1 - (r / R) ** 2)))
    prof += [(94.2, FRONT_RIM_Z), (94.95, FRONT_RIM_Z + 0.5),
             (95.0, -3.0), (95.0, -1.2), (94.98, -0.2), (95.0, RIM_TOP_Z)]

    nt = 512
    th = np.linspace(0, 2 * math.pi, nt, endpoint=False)
    verts, uvs = [], []
    for (r, z) in prof:
        for t in th:
            x, y = r * math.cos(t), r * math.sin(t)
            verts.append((x, y, z))
            uvs.append(uv_of(x, y))
    verts.append((0.0, 0.0, FRONT_CENTER_Z))
    uvs.append(uv_of(0, 0))
    pole = len(verts) - 1
    faces = []
    idx = np.arange(len(prof) * nt).reshape(len(prof), nt)

    for j in range(nt):
        j2 = (j + 1) % nt
        faces.append((idx[0, j], idx[0, j2], pole))
    for k in range(len(prof) - 1):
        for j in range(nt):
            j2 = (j + 1) % nt
            faces.append((idx[k, j], idx[k, j2], idx[k + 1, j2], idx[k + 1, j]))
    return make_object("Mirror_Body", verts, faces, uvs)


# ---------------------------------------------------------------- 材质
def make_relief_material():
    mat = bpy.data.materials.new("Bronze_Relief_v3")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.42
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    alb = nt.nodes.new("ShaderNodeTexImage")
    alb.image = bpy.data.images.load(ALBEDO, check_existing=True)
    alb.image.colorspace_settings.name = "sRGB"
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = bpy.data.images.load(NORMAL, check_existing=True)
    nrm.image.colorspace_settings.name = "Non-Color"
    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(ORM, check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"

    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.85
    sep = nt.nodes.new("ShaderNodeSeparateColor")

    nt.links.new(alb.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    return mat


def make_polished_material():
    mat = bpy.data.materials.new("Bronze_Polished_v3")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.52, 0.44, 0.33, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.17
    return mat


def main():
    clear()
    back = build_back()
    knob = build_knob()
    body = build_body()

    relief = make_relief_material()
    polished = make_polished_material()
    for ob in (back, knob):
        ob.data.materials.append(relief)
    body.data.materials.append(polished)

    for ob in (back, knob, body):
        for p in ob.data.polygons:
            p.use_smooth = True

    # 变换到 glTF 需要的朝向：镜背 +X，上 +Y（Blender 内为 +Z 上，镜背 +X）
    M = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    for ob in (back, knob, body):
        ob.matrix_world = M @ Matrix.Diagonal((0.001, 0.001, 0.001, 1.0))
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        ob.select_set(False)

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "tlv_1995_301_v3.blend"))

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT / "cleveland_1995_301_tlv_mirror_v3.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_image_format="AUTO",
        export_normals=True,
        export_tangents=True,
        export_texcoords=True,
        export_yup=True,
    )
    print("BUILD_OK")


if __name__ == "__main__":
    main()
