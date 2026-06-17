#!/usr/bin/env python3
"""Step 2: Visual attribute tagging via NLP + pixel analysis.

Usage:
  python3 scripts/step2_visual_tag.py \
    --input assets/results/step1/products_raw.json \
    --images-dir assets/results/step1/images \
    --output assets/results/step2/visual_tags.json

Dependencies: Pillow, numpy (pip3 install Pillow numpy)

Tag taxonomy:
  - geometry (几何轮廓): 圆形 / 方形 / 长条形 / 异形  [NLP from title]
  - structure (结构配置): 单体式 / 组合式 / 模块式       [NLP from title]
  - surface (表面工艺): 哑光 / 高亮 / 纹理 / 透明        [pixel analysis of image]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print(json.dumps({"error": "Missing dependencies. Run: pip3 install Pillow numpy"}, ensure_ascii=False))
    sys.exit(1)


# --- Geometry detection via title NLP ---
def detect_geometry(title):
    t = title.lower()
    if any(w in t for w in ["round", "circular"]):
        return "圆形"
    if any(w in t for w in ["square", "rectangular", "rectangle"]):
        return "方形"
    if any(w in t for w in ["wide", "oblong", "flat", "panel"]):
        return "长条形"
    if "handheld" in t and "rain" not in t:
        return "长条形"
    if "rain" in t or "rainfall" in t:
        return "圆形"
    if "fixed" in t:
        return "圆形"
    return "异形"


# --- Structure detection via title NLP ---
def detect_structure(title):
    t = title.lower()
    if any(w in t for w in ["combo", "2-in-1", "dual", "2 in 1", "with handheld", "detachable"]):
        return "组合式"
    if any(w in t for w in ["modular", "module"]):
        return "模块式"
    return "单体式"


# --- Surface detection via image pixel analysis ---
def detect_surface(img_path):
    try:
        img = Image.open(img_path).convert("RGB").resize((50, 50))
        arr = np.array(img, dtype=np.float64)
        avg_brightness = arr.mean()
        std_brightness = arr.std()
        avg_r, avg_g, avg_b = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
        max_ch = max(avg_r, avg_g, avg_b)
        min_ch = min(avg_r, avg_g, avg_b)
        saturation = (max_ch - min_ch) / max(max_ch, 1)

        if avg_brightness < 70:
            return "哑光"
        if avg_brightness > 170 and std_brightness > 50:
            return "高亮"
        if avg_brightness > 150 and saturation < 0.3:
            return "高亮"
        if saturation > 0.4 and avg_brightness > 100:
            return "高亮"
        if std_brightness > 40:
            return "纹理"
        if avg_brightness > 120:
            return "高亮"
        return "哑光"
    except Exception:
        return "未知"


def main():
    parser = argparse.ArgumentParser(description="Step 2: Visual attribute tagging")
    parser.add_argument("--input", required=True, help="Path to products_raw.json")
    parser.add_argument("--images-dir", required=True, help="Directory containing product images")
    parser.add_argument("--output", required=True, help="Output path for visual_tags.json")
    args = parser.parse_args()

    input_path = args.input
    images_dir = args.images_dir
    output_path = args.output

    if not os.path.exists(input_path):
        print(json.dumps({"error": f"Input not found: {input_path}"}, ensure_ascii=False))
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        products = json.load(f)

    results = []
    for p in products:
        asin = p.get("asin", p.get("ASIN", ""))
        title = p.get("title", "")
        img_path = os.path.join(images_dir, f"{asin}.jpg")

        geometry = detect_geometry(title)
        structure = detect_structure(title)
        surface = detect_surface(img_path) if os.path.exists(img_path) else "未知"

        try:
            price = float(str(p.get("price", 0)).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            price = 0

        results.append({
            "asin": asin,
            "title": title,
            "image_url": p.get("imageUrl", p.get("image_url", "")),
            "price": price,
            "monthly_sales": p.get("monthly_sales", 0),
            "rating": p.get("rating", ""),
            "tags": {
                "geometry": geometry,
                "structure": structure,
                "surface": surface
            }
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Stats
    total = len(results)
    tagged = sum(1 for r in results if r["tags"]["geometry"] != "未知" and r["tags"]["surface"] != "未知")
    geo_counts = Counter(r["tags"]["geometry"] for r in results)
    str_counts = Counter(r["tags"]["structure"] for r in results)
    sur_counts = Counter(r["tags"]["surface"] for r in results)

    summary = {
        "status": "ok",
        "total_products": total,
        "tagged_products": tagged,
        "tag_success_rate": round(tagged / total * 100, 1) if total > 0 else 0,
        "geometry_distribution": dict(geo_counts.most_common()),
        "structure_distribution": dict(str_counts.most_common()),
        "surface_distribution": dict(sur_counts.most_common()),
        "output": output_path,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
