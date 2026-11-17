# 宋代仙人骑鹿铜镜 3D 模型说明
## 实物参照：大英博物馆藏青铜具柄圆镜（藏品号 1990,0531.8）

**年代**：宋（12–13 世纪）　**材质**：青铜　**镜面直径**：103 mm（馆方）　**连柄总长**：188 mm（馆方）　**重量**：291 g（馆方）

---

## 一、交付物清单

| 文件 | 说明 |
|---|---|
| `blender/bm_xianren_qilu.blend` | Blender 4.5 工程，镜体/镜面/镜缘/钮/仙人/鹿/侍者/松/山石流水/镜柄分层，真实毫米尺寸 |
| `bm_xianren_qilu_mirror_structured.glb` | 结构化 GLB（柄沿 -Y、镜背朝 +Z、米制真实尺度 0.188 m 全长） |
| `bm_xianren_qilu_mirror.fbx` | FBX 交换格式（同约定） |
| `bm_xianren_qilu_tripo.glb`（同目录） | Tripo API 单图生成展示模型（展柜展示用，已实测） |
| `renders_blender_bm/*.png` | Cycles 渲染 9 帧：镜背/镜面/45°/侧视/仙人近景/鹿近景/侍者山石流水/镜柄/全形侧视 |

## 二、Blender 模型分层（命名即分组）

01 镜体（Φ103 mm 圆盘网格，厚 4.5 mm——推定）+ 02 镜面（独立圆面，镜面朝 -Z）+ 03 镜缘（凸缘环，缘宽 3 mm——照片描摹）
04 中央钮（半球钮，半径 5.5 mm——照片描摹）
05 仙人（左，坐姿有背光：环形背光 + 首 + 高髻 + 袍身 + 袍摆 + 双臂捧物 + 衣纹线）
06 鹿（中下，立姿面向左：躯干 + 颈 + 首 + 吻 + 分叉双角及角杈 ×4 + 四肢 + 尾 + 鞍鞯 + 缰绳）
07 侍者（右，立姿拱手：首 + 袍身 + 袍摆 + 双臂前伸 + 衣纹线）
08 松枝（上方：斜伸松干 + 4 组松枝 + 针叶簇小球）
09 山石与流水（右下：山岩多面体 + 岩棱 + 三组流水波纹弧线 + 左下小石）
10 镜柄（推定：简洁直柄 + 柄端收圆 + 两道弦纹饰线）

## 三、依据分层

**馆方确认**：宋代（12–13 世纪）；青铜具柄圆镜；镜面直径 103 mm；连柄总长 188 mm；重 291 g；镜背浅浮雕场景含乘鹿神祇（馆方仅称 "a deity mounted on a deer"，人物身份不做定名）；现藏大英博物馆，藏品号 1990,0531.8。

**照片推定**：镜背构图布局——左侧有背光仙人（坐姿、捧物）、中央半球钮、下方立鹿（面向左、有鞍鞯、双角分叉）、右侧侍者（立姿拱手）、上方松枝、右下山石与三组流水波纹；镜缘凸缘形制；钮半径 5.5 mm、缘宽 3 mm 等均按藏品照片比例自 103 mm 推定，非馆方实测。

**技术性补全**：镜体厚 4.5 mm、柄宽 11 mm、柄厚 4 mm 无官方数据；镜柄形制（简洁直柄、两道弦纹）因馆方无侧面照片而为推定；人物面部、衣纹、鹿角细节为风格化曲线浮雕，不做身份与种属命名。

## 四、声明

- 人物身份不做定名（依馆方表述 "a deity mounted on a deer"）✓
- 镜柄形制为推定，已在命名（10_镜柄_推定_Handle）与本文档中标注 ✓
- 推定尺寸（镜体厚、柄宽/厚、浮雕高 1.2 mm）未标注为实测 ✓
- 材质为暗灰褐青铜（PBR：金属度 0.7、糙度 0.55 + 噪声斑驳），非亮金色鎏金效果 ✓

## 五、展签建议措辞

> Bronze mirror with handle, Song dynasty (12th–13th century). The back shows a deity with a halo seated beside a saddled deer, attended by a standing figure, beneath pine branches and beside rocks and running water — an immortal realm scene cast in low relief. Diameter 103 mm, length with handle 188 mm, weight 291 g. The British Museum (1990,0531.8).
>
> 宋代青铜具柄圆镜（12–13 世纪）。镜背浅浮雕：左侧有背光仙人临坐，中央立鹿负鞍、双角分叉，右侧侍者拱手，上方松枝垂覆，右下山石间流水蜿蜒——一幅仙界行旅图景。镜面直径 103 毫米，连柄长 188 毫米，重 291 克。大英博物馆藏（1990,0531.8）。

## 六、CREDITS

- 资料：大英博物馆藏品页（British Museum collection online, object 1990,0531.8）
- 展柜展示模型：Tripo API 单图生成（模型 v3.1）
- 结构化模型与渲染：Blender 4.5 LTS 程序化建模（build_bm_mirror.py），Cycles CPU 渲染
