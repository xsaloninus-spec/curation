# -*- coding: utf-8 -*-
"""TLV 1995.301 v3 —— 基于馆方高清照片的浮雕反演 + 材质分离。

输出：
  out/rect_4096.png      校正后的正射背视图（方图，圆盘居中，R 记录在 meta.json）
  out/height_4096.png    16-bit 高程图（0..1，0.5=纹饰基准面）
  out/normal_4096.png    切线空间法线图
  out/albedo_4096.png    去光照基础色（青铜 + 绿锈）
  out/rough_2048.png     粗糙度
  out/meta.json          圆盘半径（像素/毫米对应）
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SRC = ROOT.parent / "references" / "tlv_1995.301_full.tif"
SMALL = ROOT.parent / "references" / "tlv_1995.301_print.jpg"


def fit_disc(gray: np.ndarray, guess=(None, None)):
    h, w = gray.shape
    cx, cy = (w / 2, h / 2) if guess[0] is None else guess
    # 粗估：阈值质心（镜像暗、背景亮）
    ys, xs = np.nonzero(gray < np.percentile(gray, 55))
    cx, cy = xs.mean(), ys.mean()
    rmax = 0.5 * min(w, h) * 0.999
    pts = []
    for t in np.linspace(0, 2 * math.pi, 2048, endpoint=False):
        dx, dy = math.cos(t), math.sin(t)
        best_r, best_g = None, 0.0
        # 由外向内找第一个强边缘
        for r in np.arange(rmax * 0.78, rmax, 0.5):
            x, y = cx + dx * r, cy + dy * r
            xi, yi = int(round(x)), int(round(y))
            if 1 <= xi < w - 1 and 1 <= yi < h - 1:
                g = (gray[yi, xi - 1] - gray[yi, xi + 1]) * dx + (gray[yi - 1, xi] - gray[yi + 1, xi]) * dy
                if abs(g) > abs(best_g):
                    best_g, best_r = g, r
        if best_r is not None and abs(best_g) > 6:
            pts.append((cx + dx * best_r, cy + dy * best_r))
    p = np.array(pts)
    for _ in range(3):
        x, y = p[:, 0], p[:, 1]
        A = np.c_[2 * x, 2 * y, np.ones(len(x))]
        b = x * x + y * y
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        cx, cy = sol[0], sol[1]
        R = math.sqrt(sol[2] + cx * cx + cy * cy)
        d = np.abs(np.hypot(x - cx, y - cy) - R)
        p = p[d < np.percentile(d, 65)]
    return cx, cy, R


def rectify():
    im = Image.open(SRC).convert("RGB")
    small = im.resize((4000, round(4000 * im.height / im.width)), Image.LANCZOS)
    gray = np.asarray(small.convert("L"), dtype=np.float32)
    cx, cy, R = fit_disc(gray)
    sx, sy = im.width / small.width, im.height / small.height
    cx, cy, R = cx * sx, cy * sy, R * (sx + sy) / 2
    margin = 1.015
    half = R * margin
    box = (cx - half, cy - half, cx + half, cy + half)
    out = im.resize((4096, 4096), Image.LANCZOS, box=box)
    out.save(OUT / "rect_4096.png")
    r_out = 2048 / margin
    meta = {"src": str(SRC), "src_size": im.size, "cx": cx, "cy": cy, "R_px_src": R,
            "crop_half_px": half, "r_out_px": r_out, "mm_per_px": 95.0 / r_out,
            "size": 4096}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return out, r_out


def blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """FFT 高斯模糊（反射边界），sigma 以像素计。"""
    a = a.astype(np.float32)
    pad = max(4, int(3 * sigma))
    p = np.pad(a, pad, mode="reflect")
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.fftfreq(p.shape[1])[None, :]
    h = np.exp(-2 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(p) * h))
    return out[pad:-pad, pad:-pad].astype(np.float32)


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def extract():
    rgb = np.asarray(Image.open(OUT / "rect_4096.png"), dtype=np.float32) / 255.0
    meta = json.loads((OUT / "meta.json").read_text())
    S = rgb.shape[0]
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = (S - 1) / 2
    r = np.hypot(xx - cx, yy - cy)
    disc = r < meta["r_out_px"] * 0.995

    lin = srgb_to_linear(rgb)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    logy = np.log(y + 1e-4)

    # 光照低频（去掉整体布光渐变），保留浮雕阴影
    low = blur(logy, 0.035 * S)
    high = logy - low                                    # 细节（高频）
    low2 = blur(logy, 0.006 * S)
    mid = logy - low2                                    # 中频

    # 融合：中频给出主要立体，高频补充细纹；压掉极端镜面高光
    h = 0.55 * mid + 0.45 * high
    lo, hi = np.percentile(h[disc], [2, 98])
    h = np.clip((h - lo) / (hi - lo), 0, 1)
    h = 0.5 + (h - 0.5) * 1.0
    # 轻微平滑，抑制照片噪点
    h = blur(h, 1.2)
    h = np.clip(0.5 + (h - 0.5) * 0.92, 0, 1)

    # 去光照基础色：颜色 / 局部亮度（保留色彩，去掉明暗）
    lum = blur(y, 0.02 * S)[..., None]
    alb = np.clip(lin / np.maximum(lum, 1e-3) * 0.42, 0, 1.2)
    alb = linear_to_srgb(alb)

    # 绿锈程度 → 粗糙度与法线扰动
    green = rgb[..., 1] - 0.5 * (rgb[..., 0] + rgb[..., 2])

    Image.fromarray((np.clip(h, 0, 1) * 65535).astype(np.uint16)).save(OUT / "height_4096.png")

    # 法线（距离单位 mm）
    mm_px = meta["mm_per_px"]
    relief_mm = 1.6
    dz = (h - 0.5) * relief_mm
    gy, gx = np.gradient(dz.astype(np.float32) / mm_px)
    n = np.dstack([-gx, gy, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    nimg = (n * 0.5 + 0.5) * 255
    Image.fromarray(nimg.astype(np.uint8)).save(OUT / "normal_4096.png")

    Image.fromarray((alb * 255).astype(np.uint8)).save(OUT / "albedo_4096.png")
    rough = np.clip(0.34 + 0.30 * np.clip(green, 0, 1) * 3 + 0.18 * (1 - h), 0.05, 0.95)
    Image.fromarray((rough * 255).astype(np.uint8)).resize((2048, 2048), Image.LANCZOS).save(OUT / "rough_2048.png")
    return h, alb, green


if __name__ == "__main__":
    if not (OUT / "rect_4096.png").exists():
        rectify()
    extract()
    print("done", json.loads((OUT / "meta.json").read_text()))
