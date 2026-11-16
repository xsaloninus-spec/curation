# -*- coding: utf-8 -*-
"""金背镜导出 GLB + FBX（薄轴 +X、金背朝 +X、米制真实尺度）。
Blender -b jinbei_mirror_xian.blend --python export_jinbei.py"""
import bpy
from mathutils import Matrix

OUT = "/Users/wangyaomin/Desktop/策展/文物建模"
rot = Matrix.Rotation(3.14159265 / 2, 4, 'Y') @ Matrix.Scale(0.001, 4)
root = bpy.data.objects.new("Jinbei_Mirror_XianMuseum_root", None)
bpy.context.scene.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is root or o.type in ('CAMERA', 'LIGHT') or o.name == "Cam":
        continue
    if o.parent is None:
        o.parent = root
root.matrix_world = rot

bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.type in ('MESH', 'EMPTY'):
        o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=f"{OUT}/jinbei_ruishou_putao_mirror_structured.glb",
    export_format='GLB', use_selection=True, export_yup=True,
    export_apply=True, export_animations=False)
bpy.ops.export_scene.fbx(
    filepath=f"{OUT}/jinbei_ruishou_putao_mirror.fbx",
    use_selection=True, global_scale=1.0,
    apply_scale_options='FBX_SCALE_ALL', bake_space_transform=True)
print("EXPORT_OK")
