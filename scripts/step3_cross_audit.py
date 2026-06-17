#!/usr/bin/env python3
"""Step 3: Cross-audit visual tags with sales data.

Usage:
  python3 scripts/step3_cross_audit.py \
    --products assets/results/step1/products_raw.json \
    --tags assets/results/step2/visual_tags.json \
    --output-dir assets/results/step3/

Outputs:
  - audit_results.json: aggregated stats by dimension
  - audit_table.csv: per-product attribution table
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def safe_num(v):
    """Extract numeric value from price/sales strings like '$29.99' or '1,234'."""
    if v is None:
        return 0
    s = str(v).replace("$", "").replace(",", "").replace("￥", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Step 3: Cross-audit visual tags with sales data")
    parser.add_argument("--products", required=True, help="Path to products_raw.json")
    parser.add_argument("--tags", required=True, help="Path to visual_tags.json")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    args = parser.parse_args()

    products_path = Path(args.products)
    tags_path = Path(args.tags)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not products_path.exists() or not tags_path.exists():
        print(json.dumps({"error": "Missing input files"}, ensure_ascii=False))
        sys.exit(1)

    products = json.loads(products_path.read_text(encoding="utf-8"))
    tags_raw = json.loads(tags_path.read_text(encoding="utf-8"))

    # Build tag lookup by asin — handle nested {"asin":..., "tags": {...}} structure
    tag_map = {}
    if isinstance(tags_raw, list):
        for t in tags_raw:
            asin = t.get("asin", "")
            if asin:
                tag_map[asin] = t.get("tags", t)
    elif isinstance(tags_raw, dict):
        tag_map = {k: v.get("tags", v) if isinstance(v, dict) else v for k, v in tags_raw.items()}

    # Merge and compute
    merged = []
    dim_stats = {
        "geometry": defaultdict(lambda: {"count": 0, "total_sales": 0, "total_revenue": 0, "prices": []}),
        "structure": defaultdict(lambda: {"count": 0, "total_sales": 0, "total_revenue": 0, "prices": []}),
        "surface": defaultdict(lambda: {"count": 0, "total_sales": 0, "total_revenue": 0, "prices": []}),
    }

    total_revenue_all = 0

    for p in products:
        asin = p.get("asin", p.get("ASIN", ""))
        tag = tag_map.get(asin, {})
        price = safe_num(p.get("price", 0))
        sales = safe_num(p.get("monthly_sales", p.get("sales", 0)))
        revenue = price * sales

        row = {
            "asin": asin,
            "title": p.get("title", "")[:80],
            "price": price,
            "monthly_sales": sales,
            "revenue": revenue,
            "geometry": tag.get("geometry", "未识别"),
            "structure": tag.get("structure", "未识别"),
            "surface": tag.get("surface", "未识别"),
        }
        merged.append(row)
        total_revenue_all += revenue

        for dim in ["geometry", "structure", "surface"]:
            val = row[dim]
            dim_stats[dim][val]["count"] += 1
            dim_stats[dim][val]["total_sales"] += sales
            dim_stats[dim][val]["total_revenue"] += revenue
            dim_stats[dim][val]["prices"].append(price)

    # Build aggregated result
    audit = {"total_products": len(merged), "total_revenue": round(total_revenue_all, 2), "dimensions": {}}
    for dim in ["geometry", "structure", "surface"]:
        dim_result = []
        for label, stats in dim_stats[dim].items():
            avg_price = sum(stats["prices"]) / len(stats["prices"]) if stats["prices"] else 0
            revenue_share = stats["total_revenue"] / total_revenue_all if total_revenue_all > 0 else 0
            dim_result.append({
                "label": label,
                "count": stats["count"],
                "total_sales": stats["total_sales"],
                "total_revenue": round(stats["total_revenue"], 2),
                "avg_price": round(avg_price, 2),
                "revenue_share": round(revenue_share, 4),
            })
        dim_result.sort(key=lambda x: x["total_revenue"], reverse=True)
        audit["dimensions"][dim] = dim_result

    # Cross-audit: geometry × structure
    cross = defaultdict(lambda: {"count": 0, "total_sales": 0, "total_revenue": 0, "prices": []})
    for r in merged:
        key = f"{r['geometry']}·{r['structure']}"
        cross[key]["count"] += 1
        cross[key]["total_sales"] += r["monthly_sales"]
        cross[key]["total_revenue"] += r["revenue"]
        cross[key]["prices"].append(r["price"])

    cross_result = []
    for key, stats in cross.items():
        avg_price = sum(stats["prices"]) / len(stats["prices"]) if stats["prices"] else 0
        revenue_share = stats["total_revenue"] / total_revenue_all if total_revenue_all > 0 else 0
        cross_result.append({
            "combo": key,
            "count": stats["count"],
            "total_sales": stats["total_sales"],
            "total_revenue": round(stats["total_revenue"], 2),
            "avg_price": round(avg_price, 2),
            "revenue_share": round(revenue_share, 4),
        })
    cross_result.sort(key=lambda x: x["total_revenue"], reverse=True)
    audit["cross_geometry_structure"] = cross_result

    # Write outputs
    audit_path = out_dir / "audit_results.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = out_dir / "audit_table.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["asin", "title", "price", "monthly_sales", "revenue", "geometry", "structure", "surface"])
        writer.writeheader()
        writer.writerows(merged)

    print(json.dumps({
        "status": "ok",
        "total_products": len(merged),
        "total_revenue": round(total_revenue_all, 2),
        "dimensions": {k: len(v) for k, v in audit["dimensions"].items()},
        "cross_combos": len(cross_result),
        "outputs": [str(audit_path), str(csv_path)]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
