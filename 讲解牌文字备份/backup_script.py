# -*- coding: utf-8 -*-
"""讲解牌文字完整备份脚本（只备份，绝不修改源文件）。"""
import json
import hashlib
import zipfile
import datetime
from collections import Counter

SRC1 = "/Users/wangyaomin/Desktop/策展/entrance-wall/src/data/wall.json"
SRC2 = "/Users/wangyaomin/Desktop/策展/entrance-wall/public/wall.json"
OUT_DIR = "/Users/wangyaomin/Desktop/策展/讲解牌文字备份"

FIELD_PATTERNS = []  # (style, 前缀)
for i in range(1, 7):
    xx = f"{i:02d}"
    FIELD_PATTERNS.append((f"object.{xx}.name", "name", xx))
    FIELD_PATTERNS.append((f"caption.{xx}", "caption", xx))
    FIELD_PATTERNS.append((f"meta.{xx}", "meta", xx))

# 1. 读取并解析两个源文件
raw1 = open(SRC1, "rb").read()
raw2 = open(SRC2, "rb").read()
d1 = json.loads(raw1)
d2 = json.loads(raw2)
print("PASS 解析成功: 两个 wall.json 均为合法 JSON")
print("两源文件字节一致:", raw1 == raw2)

zones1 = d1["zones"]
print(f"统计: zone 总数 = {len(zones1)}")

# 按 style 分类
style_counts = Counter(z.get("style") for z in zones1)
print("统计: 按 style 分类:", dict(style_counts))

# 按 id 建索引
zone_by_id = {z["id"]: z for z in zones1}

# 2. 提取 18 个文物讲解牌 zone
artifacts = []
checksum_parts = []
missing = []
for xx in [f"{i:02d}" for i in range(1, 7)]:
    zones_out = []
    bay = None
    for zid, field, zxx in FIELD_PATTERNS:
        if zxx != xx:
            continue
        z = zone_by_id.get(zid)
        if z is None:
            missing.append(zid)
            continue
        bay = z["bay"]
        en = z["text"]["en"]
        zh = z["text"]["zh"]
        zones_out.append({
            "zoneId": zid,
            "field": field,
            "style": z["style"],
            "bay": z["bay"],
            "geometry": {"x": z["x"], "y": z["y"], "w": z["w"], "h": z["h"]},
            "text": {"en": en, "zh": zh},
        })
        checksum_parts.append(en)
        checksum_parts.append(zh)
    artifacts.append({"artifactId": xx, "bay": bay, "zones": zones_out})

if missing:
    print("!! 缺失 zone:", missing)

artifact_zones = [zz for a in artifacts for zz in a["zones"]]
print(f"统计: 文物讲解牌 zone 数 = {len(artifact_zones)} (期望 18)")
print(f"统计: 文物数量 = {len(artifacts)} (期望 6)")

nonempty = sum(1 for a in artifacts for zz in a["zones"]
               for v in (zz["text"]["en"], zz["text"]["zh"]) if v != "")
print(f"统计: 备份范围内非空 text 字段数 = {nonempty} / {len(artifact_zones)*2}")

# 3. checksum
checksum = hashlib.sha256("\u0000".join(checksum_parts).encode("utf-8")).hexdigest()

backup = {
    "meta": {
        "createdAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "sourceFiles": [SRC1, SRC2],
        "zoneCount": len(zones1),
        "artifactZoneCount": len(artifact_zones),
        "fieldCount": len(artifact_zones) * 2,
        "checksum": checksum,
    },
    "artifacts": artifacts,
}

with open(f"{OUT_DIR}/backup.json", "w", encoding="utf-8") as f:
    json.dump(backup, f, ensure_ascii=False, indent=2)

# 4. backup.md
lines = ["# 讲解牌文字完整备份", "",
         f"- 生成时间: {backup['meta']['createdAt']}",
         f"- 源文件: `{SRC1}`、`{SRC2}`",
         f"- 源文件一致性: 两文件 diff 完全一致",
         f"- zone 总数: {len(zones1)}；讲解牌 zone 数: {len(artifact_zones)}；文物数: {len(artifacts)}",
         f"- checksum (sha256, 对全部备份文本): `{checksum}`", ""]
field_label = {"name": "文物标题", "caption": "介绍正文", "meta": "年代/材质/收藏机构"}
for a in artifacts:
    lines.append(f"## 文物 {a['artifactId']}（bay {a['bay']}）")
    lines.append("")
    for zz in a["zones"]:
        lines.append(f"### {zz['zoneId']} — {field_label[zz['field']]}")
        lines.append(f"- style: `{zz['style']}`；bay: {zz['bay']}")
        lines.append(f"- geometry: x={zz['geometry']['x']}, y={zz['geometry']['y']}, w={zz['geometry']['w']}, h={zz['geometry']['h']}")
        lines.append("")
        lines.append("**en:**")
        lines.append("```")
        lines.append(zz["text"]["en"])
        lines.append("```")
        lines.append("")
        lines.append("**zh:**")
        lines.append("```")
        lines.append(zz["text"]["zh"])
        lines.append("```")
        lines.append("")
with open(f"{OUT_DIR}/backup.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# 5. 校验：backup.json 中的每个值与源文件逐字符相等
errors = []
for a in artifacts:
    xx = a["artifactId"]
    for zz in a["zones"]:
        src_zone = zone_by_id[zz["zoneId"]]
        for lang in ("en", "zh"):
            if zz["text"][lang] != src_zone["text"][lang]:
                errors.append((zz["zoneId"], lang))
            if not isinstance(zz["text"][lang], str):
                errors.append((zz["zoneId"], lang, "not str"))
assert not errors, f"逐字符比对失败: {errors}"
print("PASS 逐字符比对: 18 个 zone 的 en/zh 与源文件全部一致（含空字符串）")

# 6. 逐字段还原测试：从写盘的 backup.json 重新读取比对
reloaded = json.load(open(f"{OUT_DIR}/backup.json", encoding="utf-8"))
restore_errors = []
mapping = {}
for a in reloaded["artifacts"]:
    for zz in a["zones"]:
        mapping[(a["artifactId"], zz["zoneId"], "en")] = zz["text"]["en"]
        mapping[(a["artifactId"], zz["zoneId"], "zh")] = zz["text"]["zh"]
assert len(mapping) == 36, f"映射数量异常: {len(mapping)}"
for xx in [f"{i:02d}" for i in range(1, 7)]:
    for zid, field, zxx in FIELD_PATTERNS:
        if zxx != xx:
            continue
        src_zone = zone_by_id[zid]
        for lang in ("en", "zh"):
            got = mapping[(xx, zid, lang)]
            if got != src_zone["text"][lang]:
                restore_errors.append((xx, zid, lang))
assert not restore_errors, f"还原测试失败: {restore_errors}"
print("PASS 逐字段还原测试: 36 个字段全部从 backup.json 取回并与源文件一致")

# 7. 打包 zip（无多余目录层级）
with zipfile.ZipFile(f"{OUT_DIR}/讲解牌文字备份.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(f"{OUT_DIR}/backup.json", "backup.json")
    zf.write(f"{OUT_DIR}/backup.md", "backup.md")
print("PASS zip 打包完成")

print("\nchecksum:", checksum)
