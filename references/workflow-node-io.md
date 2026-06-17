# 亚马逊产品视觉构型与市场效能审计

## Execution Rule

The agent executes one node at a time, writes the node output, verifies the pass condition, then stops for user confirmation.

## Node IO Table

| Node | Type | Data Source | Input | Action | Output | Pass Condition | Fail/Adjust | Stop Point |
|---|---|---|---|---|---|---|---|---|
| Step 0: 参数确认 | manual_confirm | 用户输入 | marketplace (站点), keyword (搜索关键词), page_depth (采样页数, 默认2) | 校验必填字段, 构建 run_config.json 和 step0_report.html | assets/results/step0/run_config.json + step0_report.html | marketplace 和 keyword 非空 | 仅追问缺失字段 | 确认后进入 Step 1 |
| Step 1: 搜索与数据采集 | mcp_data_call | 浏览器直接抓取 Amazon 前台搜索页 | run_config.json 中的 marketplace, keyword, page_depth | browser_navigate 到 Amazon 搜索页 → browser_console 提取产品数据 (ASIN/title/imageUrl/price/rating/bought) → 翻页采集 → 下载主图到 images/ 目录 | assets/results/step1/products_raw.json + images/{ASIN}.jpg | 采集到 ≥10 条含主图URL的产品记录 | 放宽关键词或增加页数; 第1页48条足够时可降级 | 确认产品列表后进入 Step 2 |
| Step 2: 视觉属性打标 | script_transform | Step 1 产品标题 + 主图 | products_raw.json + images/ 目录 | `python3 scripts/step2_visual_tag.py --input ... --images-dir ... --output ...` 标题NLP提取几何轮廓/结构配置 + 图片像素分析提取表面工艺 | assets/results/step2/visual_tags.json | ≥80% 图片成功打标 | 检查图片URL有效性, 重试失败项 | 确认打标结果后进入 Step 3 |
| Step 3: 形态-销售效能交叉审计 | script_transform | Step 1 销售数据 + Step 2 视觉标签 | products_raw.json + visual_tags.json | `python3 scripts/step3_cross_audit.py --products ... --tags ... --output-dir ...` 按各视觉维度聚合销售额/销量/均价; 交叉分析(轮廓×结构)的溢价矩阵 | assets/results/step3/audit_results.json + audit_table.csv | 审计表包含三个维度的聚合统计 + 交叉组合 | 检查标签字段完整性 | 确认审计结果后进入 Step 4 |
| Step 4: 可视化战略看板 | report_generation | Step 1~3 全部产出 | products_raw.json + visual_tags.json + audit_results.json + images/ 目录 | `python3 scripts/step4_generate_report.py --products ... --tags ... --audit ... --images-dir ... --keyword ... --marketplace ... --output ...` 生成含KPI/图表/归因表/热力矩阵/组合排名/图库的完整看板 | assets/results/report/visual_architecture_audit_report.html | HTML 可正常渲染, 包含图表+表格+图库+结论 | 修复图表数据绑定或样式问题 | 报告交付后流程结束 |

## Artifact Rule

Every node output should be saved under `assets/results/{step_id}/`.

## Stop Rule

Do not continue to the next node until the user confirms.
