# -*- coding: utf-8 -*-
"""Export GLB + FBX with thin axis along +X (decorated back faces +X),
real scale (190 mm diameter). Run:
Blender -b tlv_mirror_1995_301.blend --python export_tlv.py"""
import bpy
from mathutils import Matrix

OUT = "/Users/wangyaomin/Desktop/策展/文物建模"

# 绕 Y 轴 +90°：镜背法线 +Z → +X（薄轴 X，与展柜约定一致）；0.001 → 米制真实尺度
rot = Matrix.Rotation(3.14159265 / 2, 4, 'Y') @ Matrix.Scale(0.001, 4)
root = bpy.data.objects.new("TLV_Mirror_Cleveland_1995.301_root", None)
bpy.context.scene.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is root or o.type in ('CAMERA', 'LIGHT') or o.name == "Cam":
        continue
    if o.parent is None:
        o.parent = root
root.matrix_world = rot

# 只导出网格（不含相机灯光）
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type == 'MESH' or o.type == 'EMPTY':
        o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=f"{OUT}/cleveland_1995_301_tlv_mirror_structured.glb",
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=True,
    export_animations=False,
)
bpy.ops.export_scene.fbx(
    filepath=f"{OUT}/cleveland_1995_301_tlv_mirror.fbx",
    use_selection=True,
    global_scale=1.0,
    apply_scale_options='FBX_SCALE_ALL',
    bake_space_transform=True,
)
print("EXPORT_OK")
