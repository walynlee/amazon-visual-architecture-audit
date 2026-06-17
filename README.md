# Amazon Visual Architecture Audit

An Amazon category audit skill that answers a narrow but high-value question:

**Which visual product form makes more money in a search result set?**

Instead of producing a generic competitor report, this skill samples Amazon search results, downloads the main images, decomposes each product into visual tags, links those tags to sales and price signals, and delivers a strategic dashboard that turns "this looks popular" into a traceable visual-performance map.

## What this skill does

- Samples Amazon search results for a keyword and marketplace
- Extracts ASIN, title, image, price, rating, and recent-bought signals
- Tags each product on three visual dimensions:
  - geometry: round / square / elongated / irregular
  - structure: single / combo / modular
  - surface: glossy / matte / textured / transparent
- Aggregates visual tags against estimated sales and revenue
- Produces a final dashboard with KPI cards, attribution tables, heatmaps, top combinations, and a tagged product gallery

## Why this skill is useful

Most market audits stop at price, reviews, keywords, and listing copy. This one adds a missing layer: **visual structure as a commercial signal**.

That makes it useful for:

- product development teams deciding what visual direction to study first
- operators comparing high-volume vs high-premium shapes
- designers building image systems around category-native visual language
- founders who want a fast visual map before deeper competitor research

## The decomposition logic

This skill is intentionally narrow. It does not try to solve all Amazon analysis. It focuses on one bounded workflow and splits it into clean steps.

### Step 0: Scope the run

The user confirms the marketplace, keyword, and sample depth before anything else happens.

Why this exists:

- it prevents silent drift in sample scope
- it makes the audit reproducible
- it gives the user a clear first checkpoint before data collection

### Step 1: Collect the sample

The agent uses the browser to read Amazon search results and capture:

- ASIN
- title
- main image URL
- price
- rating
- recent-bought signal

It also downloads the main images for downstream visual tagging.

Why this exists:

- it locks the audit to a visible, reviewable sample
- it separates raw collection from later interpretation
- it gives the user a chance to reject or refine the sample set

### Step 2: Tag visual attributes

Each product is transformed from a plain listing record into a visual sample:

- geometry: inferred from title language
- structure: inferred from title language
- surface: inferred from image brightness, saturation, and variance

Why this exists:

- it turns subjective visual impressions into repeatable categories
- it keeps the first version explainable instead of over-modeling image semantics
- it creates a reusable labeling layer for future audits

### Step 3: Cross-audit visual tags with market signals

The skill merges Step 1 and Step 2 outputs and calculates:

- product count by tag
- estimated monthly sales by tag
- revenue by tag
- average price by tag
- cross-combination rankings

Why this exists:

- it moves the workflow from "what products look like" to "what those looks correlate with commercially"
- it reveals whether a shape is a premium signal, a volume signal, or both
- it grounds visual conclusions in concrete product rows

### Step 4: Deliver the strategic dashboard

The final report turns the audit into something a team can actually use:

- KPI overview
- three-dimension revenue distribution
- attribution tables
- geometry x structure heatmap
- price-band distribution
- top visual combination ranking
- full tagged gallery

Why this exists:

- it gives decision-makers a summary first and evidence second
- it makes the workflow presentation-ready without rebuilding the format every time
- it preserves traceability from summary back to product-level evidence

## Skill structure

```text
amazon-visual-architecture-audit/
├── SKILL.md
├── README.md
├── requirements.txt
├── references/
│   └── workflow-node-io.md
├── scripts/
│   ├── step1_fetch_products.py
│   ├── step2_visual_tag.py
│   ├── step3_cross_audit.py
│   └── step4_generate_report.py
└── assets/
    └── results/
```

### What each layer is responsible for

- `SKILL.md`: workflow rules, boundaries, checkpoints, pass conditions
- `references/`: node-level execution contract and handoff logic
- `scripts/`: deterministic transforms that should not rely on ad hoc model behavior
- `assets/results/`: sample outputs and generated reports

This separation is the main reusable pattern. The skill is easier to trust because:

- rules are visible
- execution is deterministic where possible
- outputs are reviewable at every stage

## Reusable framework

This repository is not only a specific Amazon audit. It is also a reusable framework for building stepwise Codex skills.

You can reuse the same pattern for:

- competitor image architecture audits
- category visual language mapping
- packaging-form audits
- review + visual correlation audits
- marketplace-specific product form studies

### The reusable pattern

1. Define one narrow question.
2. Confirm scope before collecting anything.
3. Separate raw collection from interpretation.
4. Turn fuzzy observations into explicit tags.
5. Cross those tags with business metrics.
6. Deliver a fixed-format report with checkpoints.

### Design principles behind the framework

- Narrow boundary beats broad promise.
- Checkpoints beat silent long-running execution.
- Deterministic scripts beat repeated prompt improvisation.
- Stage outputs beat black-box conclusions.
- Final dashboards should summarize, but also let the reader trace back to evidence.

## Included sample outputs

This repo includes example stage outputs under `assets/results/`, including:

- stepwise reports
- tagged visual samples
- audit tables
- final dashboard

They are useful as:

- validation fixtures
- demo assets
- layout references for future skills

## Quick start

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Review the skill contract

Read:

- `SKILL.md`
- `references/workflow-node-io.md`

### 3. Run the stepwise workflow

Step 1 is browser-assisted and uses the extraction pattern documented in `scripts/step1_fetch_products.py`.

Then run:

```bash
python3 scripts/step2_visual_tag.py \
  --input assets/results/step1/products_raw.json \
  --images-dir assets/results/step1/images \
  --output assets/results/step2/visual_tags.json

python3 scripts/step3_cross_audit.py \
  --products assets/results/step1/products_raw.json \
  --tags assets/results/step2/visual_tags.json \
  --output-dir assets/results/step3

python3 scripts/step4_generate_report.py \
  --products assets/results/step1/products_raw.json \
  --tags assets/results/step2/visual_tags.json \
  --audit assets/results/step3/audit_results.json \
  --images-dir assets/results/step1/images \
  --keyword "shower head" \
  --marketplace "US" \
  --output assets/results/report/visual_architecture_audit_report.html
```

## Limits

- Sales are estimated from front-end signals, not backend truth
- Visual tags are intentionally coarse in v1
- Results should guide investigation, not replace full product strategy validation

## Best fit

This skill works best when you want:

- a bounded visual audit
- visible checkpoints
- reusable stage outputs
- a deliverable that can be discussed immediately by operators, founders, or designers
