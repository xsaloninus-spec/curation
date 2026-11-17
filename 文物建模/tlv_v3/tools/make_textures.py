# -*- coding: utf-8 -*-
"""v3 贴图生成：由校正照片反演的高程 → 位移/法线/基础色/粗糙度/金属度。"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from relief import blur, srgb_to_linear, linear_to_srgb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
S = 4096


def bilinear(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = x - x0
    fy = y - y0
    out = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) +
           img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
    return out


def main():
    meta = json.loads((OUT / "meta.json").read_text())
    r_out = meta["r_out_px"]
    mm_px = meta["mm_per_px"]
    rgb = np.asarray(Image.open(OUT / "rect_4096.png"), dtype=np.float32) / 255.0
    h = np.load(OUT / "h_try.npy").astype(np.float32)

    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(xx - (S - 1) / 2, yy - (S - 1) / 2)
    disc = r < r_out * 0.999

    # 基准面 z=0，纹饰 ±，缘顶约 0
    z = (h - 0.46) * 1.6
    r_mm = r * mm_px
    # 钮区由独立的立体钮补上：先把照片里的钮与投影抹平，避免“凹坑”
    ring = (r_mm > 13.0) & (r_mm < 17.0) & disc
    z_base = float(np.median(z[ring]))
    flat_w = np.clip((13.4 - r_mm) / 2.0, 0, 1)
    flat_w = flat_w * flat_w * (3 - 2 * flat_w)
    z = z * (1 - flat_w) + z_base * flat_w
    # 外缘收边：r>93 平滑归零，便于与侧壁衔接
    rim_t = np.clip((r_mm - 92.0) / 2.8, 0, 1)
    z = z * (1 - rim_t) + 0.55 * rim_t
    z[~disc] = 0.55

    z = z.astype(np.float32)
    np.save(OUT / "height_mm_4096.npy", z)
    np.save(OUT / "height_mm_disp.npy", blur(z, 10.0).astype(np.float32))
    (OUT / "v3_meta.json").write_text(json.dumps({
        "r_out_px": r_out, "mm_per_px": mm_px, "size": S,
        "z_base_mm": round(float(z_base), 3),
        "z_min": round(float(z[disc].min()), 3), "z_max": round(float(z[disc].max()), 3),
    }, indent=2))

    # ---------------- 法线 ----------------
    z_s = blur(z, 1.6)
    gy, gx = np.gradient(z_s * mm_px)        # 每像素高度增量（mm）
    scale = 1.0
    n = np.dstack([-gx * scale, gy * scale, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    norm_img = ((n * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(norm_img).resize((2048, 2048), Image.LANCZOS).save(OUT / "v3_normal_2048.png")

    # ---------------- 基础色 ----------------
    lin = srgb_to_linear(rgb)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    sh = np.exp(blur(np.log(y + 1e-4), 90))
    sh /= np.median(sh)
    alb = lin / np.clip(sh, 0.25, 4.0)[..., None] ** 0.42
    # 钮区局部去影（照片里钮的投影不能烤进贴图，否则换光后重影）
    shl = blur(y, 42)
    shl = np.clip(shl / np.median(shl), 0.35, 3.0)
    alb_local = lin / shl[..., None] ** 0.5
    w = np.clip((20.0 - r_mm) / 6.0, 0, 1)
    w = (w * w * (3 - 2 * w))[..., None]
    alb = alb * (1 - w) + alb_local * w
    alb[..., 0] *= 1.07
    alb[..., 2] *= 0.94
    alb = np.clip(linear_to_srgb(np.clip(alb, 0, 4) * 0.86), 0, 1)

    # 绿锈掩膜（供粗糙度/金属度）
    green = rgb[..., 1] - 0.5 * (rgb[..., 0] + rgb[..., 2])
    green = blur(np.clip((green - 0.012) * 9.0, 0, 1), 3.0)
    green = np.clip(green * 1.15, 0, 1)
    # 绿锈是“附着物”，不应被当成浮雕：绿锈区高程向局部均值收敛
    h_smooth = blur(h, 60)
    gw = blur(green, 8.0)[..., None]
    h = h * (1 - 0.85 * gw) + h_smooth * (0.85 * gw)

    # 金属高光区（纹饰棱线）略提亮、降粗糙
    lift = np.clip((z - 0.35) / 2.2, 0, 1)
    alb = np.clip(alb * (1 + 0.18 * lift[..., None]), 0, 1)
    alb_jpg = (alb * 255).astype(np.uint8)
    Image.fromarray(alb_jpg).save(OUT / "v3_albedo_4096.jpg", quality=92)

    rough = np.clip(0.26 + 0.52 * green + 0.08 * np.clip(-z, 0, 1) - 0.06 * lift, 0.08, 0.9)
    metal = np.clip(0.96 - 0.92 * green, 0, 1)
    orm = np.dstack([np.ones_like(rough), rough, metal])
    Image.fromarray((orm * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(OUT / "v3_orm_2048.png")

    # 预览
    n2 = n[::4, ::4]
    sh_dir = np.array([-0.42, 0.52, 0.74]); sh_dir /= np.linalg.norm(sh_dir)
    shade = np.clip((n2 * sh_dir).sum(2), 0, 1)
    shade = 0.30 + 0.78 * shade
    prev = np.clip(alb[::4, ::4] * shade[..., None], 0, 1)
    Image.fromarray((prev * 255).astype(np.uint8)).save(OUT / "v3_preview.png")
    print("z range", float(z[disc].min()), float(z[disc].max()), "green mean", float(green.mean()))


if __name__ == "__main__":
    main()
