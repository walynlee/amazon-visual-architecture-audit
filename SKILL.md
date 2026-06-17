---
name: amazon-visual-architecture-audit
description: 亚马逊产品视觉构型与市场效能审计系统。对品类搜索结果的主图进行几何轮廓/结构配置/表面工艺三维属性拆解，量化不同外观形态的市场溢价力，输出"哪种长相最赚钱"的可视化战略看板。
---

# 亚马逊产品视觉构型与市场效能审计

## 目的

通过视觉识别将竞品主图拆解为原子级标签（几何轮廓/结构配置/表面工艺），关联销售数据，生成形态-效能映射可视化看板。

## 默认参数

- marketplace: 用户指定 (US/UK/DE/JP 等)
- keyword: 用户指定品类关键词
- page_depth: 2 (默认采样前2页)
- audit_dimensions: 几何轮廓 / 结构配置 / 表面工艺

## 工具与数据边界

| 环节 | 工具 | 说明 |
|---|---|---|
| 产品搜索 | 浏览器直接抓取 Amazon 前台搜索页 | navigate→extract ASIN/title/image/price/rating/bought |
| 图片下载 | urllib/requests | 下载主图到 `assets/results/step1/images/` |
| 视觉打标 | NLP标题关键词+图片像素分析 | `scripts/step2_visual_tag.py`（Pillow+numpy） |
| 数据聚合 | Python脚本 | `scripts/step3_cross_audit.py`（stdlib only） |
| 报告生成 | Python脚本+Chart.js | `scripts/step4_generate_report.py` |

### 标签体系

| 维度 | 枚举值 | 判定依据 |
|---|---|---|
| 几何轮廓 | 圆形 / 方形 / 长条形 / 异形 | 标题NLP关键词匹配 |
| 结构配置 | 单体式 / 组合式 / 模块式 | 标题NLP关键词匹配 |
| 表面工艺 | 哑光 / 高亮 / 纹理 / 透明 | 图片像素亮度/饱和度/方差分析 |

## 执行流程

按 `references/workflow-node-io.md` 逐节点执行，每步完成后 **停止等待用户确认**。

### Step 0: 参数确认
- 收集 marketplace / keyword / page_depth
- 输出: `assets/results/step0/run_config.json` + `step0_report.html`

### Step 1: 搜索与数据采集
1. 浏览器 navigate 到 `https://www.amazon.com/s?k={keyword}`
2. browser_console 提取搜索结果: ASIN, title, imageUrl, price, rating, bought
3. 翻页采集 page 2~N（如有反爬则降级，第1页≥10条即通过）
4. 下载所有主图到 `assets/results/step1/images/{ASIN}.jpg`
- 输出: `assets/results/step1/products_raw.json`

### Step 2: 视觉属性打标
```bash
python3 scripts/step2_visual_tag.py \
  --input assets/results/step1/products_raw.json \
  --images-dir assets/results/step1/images \
  --output assets/results/step2/visual_tags.json
```
- 输出: `assets/results/step2/visual_tags.json`

### Step 3: 形态-销售效能交叉审计
```bash
python3 scripts/step3_cross_audit.py \
  --products assets/results/step1/products_raw.json \
  --tags assets/results/step2/visual_tags.json \
  --output-dir assets/results/step3/
```
- 输出: `assets/results/step3/audit_results.json` + `audit_table.csv`

### Step 4: 可视化战略看板
```bash
python3 scripts/step4_generate_report.py \
  --products assets/results/step1/products_raw.json \
  --tags assets/results/step2/visual_tags.json \
  --audit assets/results/step3/audit_results.json \
  --images-dir assets/results/step1/images \
  --keyword "{keyword}" \
  --marketplace "{marketplace}" \
  --output assets/results/report/visual_architecture_audit_report.html
```
- 输出: `assets/results/report/visual_architecture_audit_report.html`
- 内容: KPI卡片 + 三维环形图 + 归因明细表 + 热力矩阵 + 价格带柱状图 + 视觉组合排名TOP 9 + 产品图库(带base64图片)

## 输出路径

```
assets/results/
├── step0/run_config.json + step0_report.html
├── step1/products_raw.json + images/{ASIN}.jpg
├── step2/visual_tags.json
├── step3/audit_results.json + audit_table.csv
└── report/visual_architecture_audit_report.html
```

## 停止规则

每步完成后停止，等待用户说"继续/下一步/confirm"后才进入下一步。

## 通过条件

| 步骤 | 条件 |
|---|---|
| Step 1 | 采集到 ≥10 条含主图URL的产品记录 |
| Step 2 | ≥80% 图片成功打标 |
| Step 3 | 审计表包含三个维度的聚合统计 |
| Step 4 | HTML可正常渲染，包含图表+表格+结论+图库 |

## 防坑备忘

1. **反爬降级**: Amazon搜索页第2-3页可能被拦截，第1页48条数据足够推进（远超≥10条阈值）
2. **MCP断连**: Sorftime/卖家精灵 MCP 可能断连，不依赖MCP作为唯一数据源
3. **标签嵌套**: `visual_tags.json`中每条记录的标签在 `tags` 子对象内，`step3` 脚本已处理此结构
4. **价格格式**: products_raw.json 中 price 可能是字符串（"$29.99"），step3 脚本已做 safe_num 处理
5. **HTML报告花括号**: f-string中Chart.js花括号用 `{{` `}}` 转义；数据先 json.dumps() 再嵌入JS
6. **图片base64**: 最终看板内嵌图片用 base64，避免外部链接失效；报告体积可达2MB+
7. **Dinzee上传**: 最终报告通过 `dinzeeagent-fileupload` skill 上传获取公网链接
