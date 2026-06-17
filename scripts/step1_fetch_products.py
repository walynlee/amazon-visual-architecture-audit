#!/usr/bin/env python3
"""Step 1: Fetch product data from Amazon search results.

Usage (agent executes this logic manually):
  1. Read run_config.json for keyword/marketplace/page_depth
  2. Browser navigate to https://www.amazon.com/s?k={keyword}
  3. Extract products via browser_console JS
  4. Download main images to images/{ASIN}.jpg
  5. Write products_raw.json

This script is a reference template. The actual data collection is done
by the agent using browser tools, not by running this script directly.
"""
import argparse
import json
import sys
from pathlib import Path


# --- JS extraction code used in browser_console ---
EXTRACT_JS = """
(() => {
  const items = [];
  document.querySelectorAll('[data-asin]').forEach(el => {
    const asin = el.getAttribute('data-asin');
    if (!asin || asin.length < 5) return;
    const titleEl = el.querySelector('h2 a span') || el.querySelector('.a-text-normal');
    const title = titleEl ? titleEl.textContent.trim() : '';
    const imgEl = el.querySelector('img.s-image');
    const imageUrl = imgEl ? imgEl.src : '';
    const priceWhole = el.querySelector('.a-price .a-price-whole');
    const priceFrac = el.querySelector('.a-price .a-price-fraction');
    let price = '';
    if (priceWhole) {
      price = priceWhole.textContent.replace(',','').replace('.','') + '.' + (priceFrac ? priceFrac.textContent : '00');
    }
    const ratingEl = el.querySelector('.a-icon-alt');
    const rating = ratingEl ? ratingEl.textContent.split(' ')[0] : '';
    const boughtEl = el.querySelector('.a-size-base:has(+ .a-text-secondary)') ||
                     [...el.querySelectorAll('.a-size-base')].find(e => e.textContent.includes('+ bought') || e.textContent.includes('K+ bought'));
    const bought = boughtEl ? boughtEl.textContent.trim() : '';
    items.push({asin, title, imageUrl, price, rating, bought});
  });
  return JSON.stringify(items);
})()
"""

# --- Monthly sales estimation heuristic ---
def estimate_monthly_sales(bought_str):
    """Parse '1K+ bought' style strings into monthly sales estimates."""
    if not bought_str:
        return 0
    s = bought_str.replace('+ bought', '').replace('bought', '').strip()
    try:
        if 'K' in s:
            return int(float(s.replace('K', '')) * 1000)
        return int(s.replace(',', ''))
    except:
        return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to run_config.json")
    parser.add_argument("--output", required=True, help="Output path for products_raw.json")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(json.dumps({"error": f"Config not found: {config_path}"}, ensure_ascii=False))
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    keyword = config.get("keyword", "")
    marketplace = config.get("marketplace", "US")
    page_depth = config.get("page_depth", 2)

    print(json.dumps({
        "status": "ready",
        "keyword": keyword,
        "marketplace": marketplace,
        "page_depth": page_depth,
        "extract_js": EXTRACT_JS.strip(),
        "instruction": (
            "Agent: 1) browser_navigate to Amazon search page, "
            "2) browser_console(extract_js) to get products, "
            "3) download images to assets/results/step1/images/, "
            "4) write products_raw.json with fields: asin, title, imageUrl, price, rating, bought, monthly_sales"
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
