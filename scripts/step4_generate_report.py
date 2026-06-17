#!/usr/bin/env python3
"""Step 4: Generate the full visual architecture audit HTML dashboard.

Usage:
  python3 scripts/step4_generate_report.py \
    --products assets/results/step1/products_raw.json \
    --tags assets/results/step2/visual_tags.json \
    --audit assets/results/step3/audit_results.json \
    --images-dir assets/results/step1/images \
    --keyword "shower head" \
    --marketplace "US" \
    --output assets/results/report/visual_architecture_audit_report.html

Dependencies: Pillow (for base64 image encoding)
Output: Self-contained HTML with embedded Chart.js + base64 product images
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


def img_to_base64(path, max_size=(200, 200)):
    """Convert image to base64 data URI, resize for embedding."""
    if not os.path.exists(path):
        return ""
    try:
        if Image:
            img = Image.open(path).convert("RGB")
            img.thumbnail(max_size, Image.LANCZOS)
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode()
        else:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return ""


def safe_num(v):
    if v is None:
        return 0
    s = str(v).replace("$", "").replace(",", "").replace("￥", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0


CHART_COLORS = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"
]


def build_html(products, tags_list, audit, keyword, marketplace, images_dir):
    dims = audit.get("dimensions", {})
    geo_data = dims.get("geometry", [])
    struct_data = dims.get("structure", [])
    surf_data = dims.get("surface", [])
    cross_data = audit.get("cross_geometry_structure", [])
    total_products = audit.get("total_products", 0)
    total_revenue = audit.get("total_revenue", 0)

    # Build tag lookup
    tag_map = {}
    for t in tags_list:
        asin = t.get("asin", "")
        if asin:
            tag_map[asin] = t.get("tags", t)

    # --- KPI cards ---
    avg_price = sum(safe_num(p.get("price")) for p in products) / max(len(products), 1)
    total_sales = sum(safe_num(p.get("monthly_sales")) for p in products)

    # --- Pie chart data helper ---
    def pie_json(items, key="revenue_share"):
        labels = json.dumps([x["label"] for x in items], ensure_ascii=False)
        values = json.dumps([round(x[key] * 100, 1) for x in items])
        colors = json.dumps(CHART_COLORS[:len(items)])
        return labels, values, colors

    geo_l, geo_v, geo_c = pie_json(geo_data)
    str_l, str_v, str_c = pie_json(struct_data)
    sur_l, sur_v, sur_c = pie_json(surf_data)

    # --- Heat matrix: geometry × structure ---
    geo_labels = [x["label"] for x in geo_data]
    str_labels = [x["label"] for x in struct_data]
    heat_data = []
    cross_map = {}
    for c in cross_data:
        parts = c["combo"].split("·", 1)
        if len(parts) == 2:
            cross_map[(parts[0], parts[1])] = c

    max_rev = max((c["total_revenue"] for c in cross_data), default=1)
    for gi, gl in enumerate(geo_labels):
        for si, sl in enumerate(str_labels):
            c = cross_map.get((gl, sl), {})
            rev = c.get("total_revenue", 0)
            heat_data.append({"x": si, "y": gi, "v": round(rev, 0)})

    heat_json = json.dumps(heat_data, ensure_ascii=False)
    geo_labels_json = json.dumps(geo_labels, ensure_ascii=False)
    str_labels_json = json.dumps(str_labels, ensure_ascii=False)
    max_rev_val = max_rev if max_rev > 0 else 1

    # --- Price band bar chart ---
    price_bands = {"$0-$20": 0, "$20-$40": 0, "$40-$60": 0, "$60-$100": 0, "$100+": 0}
    for p in products:
        pr = safe_num(p.get("price"))
        if pr < 20:
            price_bands["$0-$20"] += 1
        elif pr < 40:
            price_bands["$20-$40"] += 1
        elif pr < 60:
            price_bands["$40-$60"] += 1
        elif pr < 100:
            price_bands["$60-$100"] += 1
        else:
            price_bands["$100+"] += 1
    pb_labels = json.dumps(list(price_bands.keys()))
    pb_values = json.dumps(list(price_bands.values()))

    # --- Attribution table rows ---
    attr_rows = ""
    all_items = []
    for item in geo_data:
        all_items.append({"dim": "几何轮廓", **item})
    for item in struct_data:
        all_items.append({"dim": "结构配置", **item})
    for item in surf_data:
        all_items.append({"dim": "表面工艺", **item})
    for item in all_items:
        share_pct = f"{item['revenue_share'] * 100:.1f}%"
        attr_rows += (
            f"<tr><td>{item['dim']}</td><td>{item['label']}</td>"
            f"<td>{item['count']}</td><td>{item['total_sales']:,.0f}</td>"
            f"<td>${item['total_revenue']:,.0f}</td>"
            f"<td>${item['avg_price']:.2f}</td><td>{share_pct}</td></tr>\n"
        )

    # --- Cross combo ranking (TOP 9) ---
    combo_rows = ""
    for i, c in enumerate(cross_data[:9]):
        share_pct = f"{c['revenue_share'] * 100:.1f}%"
        combo_rows += (
            f"<tr><td>{i+1}</td><td>{c['combo']}</td>"
            f"<td>{c['count']}</td><td>{c['total_sales']:,.0f}</td>"
            f"<td>${c['total_revenue']:,.0f}</td>"
            f"<td>${c['avg_price']:.2f}</td><td>{share_pct}</td></tr>\n"
        )

    # --- Product gallery with base64 images ---
    gallery_html = ""
    for p in products:
        asin = p.get("asin", "")
        title = p.get("title", "")[:60]
        price = p.get("price", "")
        sales = p.get("monthly_sales", "")
        tag = tag_map.get(asin, {})
        geo_tag = tag.get("geometry", "-")
        str_tag = tag.get("structure", "-")
        sur_tag = tag.get("surface", "-")
        img_src = img_to_base64(os.path.join(images_dir, f"{asin}.jpg"))
        img_html = f'<img src="{img_src}" style="width:100%;border-radius:6px;" alt="{asin}">' if img_src else '<div style="width:100%;height:120px;background:#eee;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#999;">无图</div>'
        gallery_html += f"""
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:10px;background:white;">
  {img_html}
  <div style="margin-top:6px;font-size:11px;color:#555;">
    <b>{asin}</b><br>{title}<br>
    💲{price} | 📦{sales}/月<br>
    📐{geo_tag} | 🏗{str_tag} | ✨{sur_tag}
  </div>
</div>"""

    # --- Insight text ---
    top_geo = geo_data[0]["label"] if geo_data else "N/A"
    top_struct = struct_data[0]["label"] if struct_data else "N/A"
    top_surf = surf_data[0]["label"] if surf_data else "N/A"
    top_geo_share = f"{geo_data[0]['revenue_share'] * 100:.1f}%" if geo_data else "0%"
    top_combo = cross_data[0]["combo"] if cross_data else "N/A"
    top_combo_share = f"{cross_data[0]['revenue_share'] * 100:.1f}%" if cross_data else "0%"

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>视觉构型与市场效能审计 - {keyword}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:#f5f7fa; color:#1a1a2e; padding:20px; }}
.header {{ background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; padding:30px; border-radius:12px; margin-bottom:20px; }}
.header h1 {{ font-size:24px; margin-bottom:8px; }}
.header p {{ opacity:0.9; font-size:14px; }}
.kpi-row {{ display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }}
.kpi-box {{ flex:1; min-width:140px; text-align:center; padding:16px; background:white; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
.kpi-box .num {{ font-size:28px; font-weight:700; color:#667eea; }}
.kpi-box .label {{ font-size:12px; color:#888; margin-top:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(380px,1fr)); gap:16px; margin-bottom:20px; }}
.card {{ background:white; border-radius:10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
.card h3 {{ font-size:15px; color:#667eea; margin-bottom:12px; border-bottom:2px solid #667eea; padding-bottom:6px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ background:#667eea; color:white; padding:10px 8px; text-align:left; position:sticky; top:0; }}
td {{ padding:8px; border-bottom:1px solid #eee; }}
tr:hover td {{ background:#f0f2ff; }}
.insight {{ background:linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%); padding:20px; border-radius:10px; margin-bottom:20px; }}
.insight h3 {{ color:#c0392b; margin-bottom:10px; }}
.gallery {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:12px; }}
canvas {{ max-height:320px; }}
</style>
</head>
<body>

<div class="header">
  <h1>🎨 产品视觉构型与市场效能审计</h1>
  <p>关键词: {keyword} | 站点: {marketplace} | 样本量: {total_products} 个产品 | 总月销售额: ${total_revenue:,.0f}</p>
</div>

<div class="kpi-row">
  <div class="kpi-box"><div class="num">{total_products}</div><div class="label">样本产品数</div></div>
  <div class="kpi-box"><div class="num">${total_revenue:,.0f}</div><div class="label">总月销售额</div></div>
  <div class="kpi-box"><div class="num">${avg_price:.2f}</div><div class="label">平均客单价</div></div>
  <div class="kpi-box"><div class="num">{total_sales:,.0f}</div><div class="label">总月销量</div></div>
  <div class="kpi-box"><div class="num">{len(geo_data)}</div><div class="label">几何轮廓类型</div></div>
  <div class="kpi-box"><div class="num">{len(cross_data)}</div><div class="label">视觉组合数</div></div>
</div>

<div class="grid">
  <div class="card">
    <h3>📐 几何轮廓 - 销售额占比</h3>
    <canvas id="geoChart"></canvas>
  </div>
  <div class="card">
    <h3>🏗️ 结构配置 - 销售额占比</h3>
    <canvas id="structChart"></canvas>
  </div>
  <div class="card">
    <h3>✨ 表面工艺 - 销售额占比</h3>
    <canvas id="surfChart"></canvas>
  </div>
  <div class="card">
    <h3>💰 价格带分布</h3>
    <canvas id="priceChart"></canvas>
  </div>
</div>

<div class="card" style="margin-bottom:20px;">
  <h3>🔥 热力矩阵：几何轮廓 × 结构配置 (销售额)</h3>
  <canvas id="heatChart" style="max-height:400px;"></canvas>
</div>

<div class="card" style="margin-bottom:20px;">
  <h3>📊 数据归因明细表</h3>
  <div style="overflow-x:auto;max-height:500px;overflow-y:auto;">
    <table>
      <thead><tr><th>审计维度</th><th>形态标签</th><th>产品数</th><th>月总销量</th><th>月总销售额</th><th>平均客单价</th><th>销售额占比</th></tr></thead>
      <tbody>{attr_rows}</tbody>
    </table>
  </div>
</div>

<div class="card" style="margin-bottom:20px;">
  <h3>🏆 视觉组合排名 TOP 9（几何轮廓 × 结构配置）</h3>
  <div style="overflow-x:auto;">
    <table>
      <thead><tr><th>#</th><th>组合形态</th><th>产品数</th><th>月总销量</th><th>月总销售额</th><th>平均客单价</th><th>销售额占比</th></tr></thead>
      <tbody>{combo_rows}</tbody>
    </table>
  </div>
</div>

<div class="insight">
  <h3>🎯 差异化结论</h3>
  <p><strong>主力形态：</strong>几何轮廓以「{top_geo}」为主导，占据 {top_geo_share} 销售额份额。</p>
  <p><strong>结构偏好：</strong>市场偏好「{top_struct}」结构配置。</p>
  <p><strong>工艺趋势：</strong>「{top_surf}」工艺产品销售额占比最高。</p>
  <p><strong>最强构型：</strong>「{top_combo}」组合占据 {top_combo_share} 销售额份额。</p>
  <p><strong>建议：</strong>新品 ID 设计优先采用 {top_geo} 轮廓 + {top_struct} 结构 + {top_surf} 工艺的组合，在主流审美区间内竞争；若需差异化，可选择份额较低但均价更高的形态组合切入。</p>
</div>

<div class="card" style="margin-bottom:20px;">
  <h3>📦 产品图库（{total_products} 个产品）</h3>
  <div class="gallery">{gallery_html}</div>
</div>

<script>
// Geometry pie
new Chart(document.getElementById('geoChart'), {{
  type:'doughnut',
  data:{{ labels:{geo_l}, datasets:[{{ data:{geo_v}, backgroundColor:{geo_c} }}] }},
  options:{{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});
// Structure pie
new Chart(document.getElementById('structChart'), {{
  type:'doughnut',
  data:{{ labels:{str_l}, datasets:[{{ data:{str_v}, backgroundColor:{str_c} }}] }},
  options:{{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});
// Surface pie
new Chart(document.getElementById('surfChart'), {{
  type:'doughnut',
  data:{{ labels:{sur_l}, datasets:[{{ data:{sur_v}, backgroundColor:{sur_c} }}] }},
  options:{{ responsive:true, plugins:{{ legend:{{ position:'bottom' }} }} }}
}});
// Price band bar
new Chart(document.getElementById('priceChart'), {{
  type:'bar',
  data:{{ labels:{pb_labels}, datasets:[{{ label:'产品数', data:{pb_values}, backgroundColor:'#667eea' }}] }},
  options:{{ responsive:true, plugins:{{ legend:{{ display:false }} }}, scales:{{ y:{{ beginAtZero:true }} }} }}
}});
// Heat matrix as scatter
const heatData = {heat_json};
const maxRev = {max_rev_val};
new Chart(document.getElementById('heatChart'), {{
  type:'scatter',
  data:{{
    datasets: [{{
      label: '销售额热度',
      data: heatData.map(d => ({{ x: d.x, y: d.y }})),
      pointRadius: heatData.map(d => Math.max(8, Math.min(40, Math.sqrt(d.v / maxRev) * 40))),
      pointBackgroundColor: heatData.map(d => {{
        const ratio = d.v / maxRev;
        if (ratio > 0.5) return '#e15759';
        if (ratio > 0.2) return '#f28e2b';
        if (ratio > 0.05) return '#4e79a7';
        return '#bab0ac';
      }}),
      pointHoverRadius: 12
    }}]
  }},
  options: {{
    responsive: true,
    scales: {{
      x: {{
        type: 'linear',
        min: -0.5,
        max: {len(str_labels)} - 0.5,
        ticks: {{
          stepSize: 1,
          callback: function(v) {{ const labels = {str_labels_json}; return labels[v] || ''; }}
        }},
        title: {{ display: true, text: '结构配置' }}
      }},
      y: {{
        type: 'linear',
        min: -0.5,
        max: {len(geo_labels)} - 0.5,
        ticks: {{
          stepSize: 1,
          callback: function(v) {{ const labels = {geo_labels_json}; return labels[v] || ''; }}
        }},
        title: {{ display: true, text: '几何轮廓' }}
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: function(ctx) {{
            const d = heatData[ctx.dataIndex];
            const geoL = {geo_labels_json};
            const strL = {str_labels_json};
            return geoL[d.y] + ' × ' + strL[d.x] + ': $' + d.v.toLocaleString();
          }}
        }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Step 4: Generate full audit dashboard")
    parser.add_argument("--products", required=True, help="Path to products_raw.json")
    parser.add_argument("--tags", required=True, help="Path to visual_tags.json")
    parser.add_argument("--audit", required=True, help="Path to audit_results.json")
    parser.add_argument("--images-dir", required=True, help="Directory containing product images")
    parser.add_argument("--keyword", default="N/A", help="Search keyword")
    parser.add_argument("--marketplace", default="US", help="Marketplace code")
    parser.add_argument("--output", required=True, help="Output HTML path")
    args = parser.parse_args()

    # Load data
    products = json.loads(Path(args.products).read_text(encoding="utf-8"))
    tags_list = json.loads(Path(args.tags).read_text(encoding="utf-8"))
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))

    # Build HTML
    html = build_html(products, tags_list, audit, args.keyword, args.marketplace, args.images_dir)

    # Write
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(json.dumps({
        "status": "ok",
        "output": str(out_path),
        "size_kb": round(size_kb, 1),
        "product_count": len(products),
        "total_revenue": audit.get("total_revenue", 0),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
