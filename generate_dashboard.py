"""Generate the interactive HTML dashboard for Kaamil Technology Sales."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DASHBOARD_PATH = OUTPUT_DIR / "dashboard.html"

# Load data
profile = json.load(open(OUTPUT_DIR / "eda_profile.json"))
results = json.load(open(OUTPUT_DIR / "results.json"))

# ---- Helper to serialize safely ----
def s(v):
    return json.dumps(v, default=str)

def money(v):
    return f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)

def pct(v):
    return f"{v*100:.1f}%" if isinstance(v, float) and abs(v) < 1 else str(v)

# ---- Prepare chart data ----
# 1. Revenue by Category (bar)
cat_rev = profile["category_revenue"]
cat_labels = list(cat_rev.keys())
cat_values = [float(v) for v in cat_rev.values()]

# 2. Revenue by Location (horizontal bar)
loc_rev = profile["location_revenue"]
loc_labels = list(loc_rev.keys())
loc_values = [float(v) for v in loc_rev.values()]

# 3. Sales Rep Revenue (horizontal bar)
rep_rev = profile["sales_rep_revenue"]
rep_labels = list(rep_rev.keys())
rep_values = [float(v) for v in rep_rev.values()]

# 4. Monthly revenue trend (line)
monthly = profile["monthly_revenue"]
month_labels = sorted([int(k) for k in monthly.keys()])
month_values = [float(monthly[str(m)]) for m in month_labels]
month_names = {6: "Jun", 7: "Jul", 8: "Aug"}
month_labels_display = [month_names.get(m, str(m)) for m in month_labels]

# 5. Monthly category revenue (stacked area)
monthly_cat = profile["monthly_category_revenue"]
cat_names = list(next(iter(monthly_cat.values())).keys())
cat_colors = ["#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626"]
monthly_cat_datasets = []
for ci, cat in enumerate(cat_names):
    monthly_cat_datasets.append({
        "name": cat,
        "data": [float(monthly_cat[str(m)].get(cat, 0)) for m in month_labels],
        "color": cat_colors[ci % len(cat_colors)],
    })

# 6. Price tier distribution (doughnut)
tier_counts = profile["price_tier_counts"]
tier_labels = list(tier_counts.keys())
tier_values = [float(v) for v in tier_counts.values()]

# 7. Category avg profit margin (bar)
cat_margin = profile["category_avg_profit_margin"]
margin_labels = list(cat_margin.keys())
margin_values = [float(v) * 100 for v in cat_margin.values()]

# 8. Top products (horizontal bar)
top_prods = profile["top_products"]
# Sort by sum descending
sorted_prods = sorted(top_prods.items(), key=lambda x: float(x[1]["sum"]), reverse=True)[:12]
prod_labels = [p[0] for p in sorted_prods]
prod_values = [float(p[1]["sum"]) for p in sorted_prods]

# 9. Payment method distribution (doughnut)
pm_counts = profile["payment_method_counts"]
pm_labels = list(pm_counts.keys())
pm_values = [float(v) for v in pm_counts.values()]

# 10. Category unit counts (bar)
cat_counts = profile["category_counts"]
cc_labels = list(cat_counts.keys())
cc_values = [float(v) for v in cat_counts.values()]

# ---- ML results ----
ml_models = results["models"]
ml_best = results["best_model"]
ml_r2 = results["best_r2_score"]
ml_features = results["n_features"]
ml_train = results["train_rows"]
ml_test = results["test_rows"]

# Top features
top_feats = results.get("top_features", {})
feat_labels = list(top_feats.keys())[:15]
feat_values = [float(v) for v in list(top_feats.values())[:15]]

# ---- KPI cards ----
kpi_total_rev = float(profile["total_revenue"])
kpi_total_profit = float(profile["total_profit"])
kpi_aov = float(profile["avg_order_value"])
kpi_margin = float(profile["avg_profit_margin"]) * 100

# Category profit margin highlight
cat_margin_data = [
    {"label": cat, "margin": float(profile["category_avg_profit_margin"].get(cat, 0)) * 100, "revenue": float(cat_rev.get(cat, 0))}
    for cat in cat_labels
]

# ---- Build HTML ----
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kaamil Technology Sales — Analytics Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ font-family: 'Inter', sans-serif; }}
  body {{ background: #0f172a; color: #e2e8f0; }}
  .kpi-card {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border: 1px solid #334155; border-radius: 16px; padding: 20px; transition: transform 0.2s, box-shadow 0.2s; }}
  .kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 30px rgba(99,102,241,0.15); }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 24px; }}
  .card-header {{ font-size: 14px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }}
  .glow-blue {{ box-shadow: 0 0 20px rgba(59,130,246,0.2); }}
  .glow-green {{ box-shadow: 0 0 20px rgba(16,185,129,0.2); }}
  .glow-amber {{ box-shadow: 0 0 20px rgba(245,158,11,0.2); }}
  .glow-purple {{ box-shadow: 0 0 20px rgba(168,85,247,0.2); }}
  .stat-value {{ font-size: 28px; font-weight: 700; line-height: 1.1; }}
  .stat-label {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; }}
  .fade-in {{ animation: fadeIn 0.6s ease-out; }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: #1e293b; }}
  ::-webkit-scrollbar-thumb {{ background: #475569; border-radius: 3px; }}
</style>
</head>
<body class="min-h-screen">

<!-- Header -->
<header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50">
  <div class="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">K</div>
      <div>
        <h1 class="text-xl font-bold text-white tracking-tight">Kaamil Technology Sales</h1>
        <p class="text-xs text-slate-400">Full Data Science &amp; ML Analytics Dashboard</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <span class="badge bg-green-500/20 text-green-400">● Live</span>
      <span class="text-xs text-slate-500">{profile['date_range']['start']} → {profile['date_range']['end']}</span>
      <span class="badge bg-blue-500/20 text-blue-400">{profile['raw_rows']} Transactions</span>
    </div>
  </div>
</header>

<main class="max-w-[1600px] mx-auto px-6 py-8 space-y-8">

  <!-- KPI Cards -->
  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 fade-in">
    <div class="kpi-card glow-blue">
      <div class="flex items-center justify-between mb-2">
        <span class="stat-label">Total Revenue</span>
        <span class="text-blue-400 text-2xl">💰</span>
      </div>
      <div class="stat-value text-blue-400">{money(kpi_total_rev)}</div>
      <div class="stat-label mt-1">{profile['raw_rows']} orders · {len(profile['location_counts'])} cities</div>
    </div>
    <div class="kpi-card glow-green">
      <div class="flex items-center justify-between mb-2">
        <span class="stat-label">Total Profit</span>
        <span class="text-green-400 text-2xl">📈</span>
      </div>
      <div class="stat-value text-green-400">{money(kpi_total_profit)}</div>
      <div class="stat-label mt-1">Profit margin <span class="text-green-400 font-semibold">{kpi_margin:.1f}%</span></div>
    </div>
    <div class="kpi-card glow-amber">
      <div class="flex items-center justify-between mb-2">
        <span class="stat-label">Avg Order Value</span>
        <span class="text-amber-400 text-2xl">🛒</span>
      </div>
      <div class="stat-value text-amber-400">{money(kpi_aov)}</div>
      <div class="stat-label mt-1">{profile['avg_profit_margin']*100:.1f}% avg margin</div>
    </div>
    <div class="kpi-card glow-purple">
      <div class="flex items-center justify-between mb-2">
        <span class="stat-label">Best ML Model</span>
        <span class="text-purple-400 text-2xl">🤖</span>
      </div>
      <div class="stat-value text-purple-400">{ml_best}</div>
      <div class="stat-label mt-1">R² = <span class="text-purple-400 font-semibold">{ml_r2:.4f}</span> · {ml_features} features</div>
    </div>
  </section>

  <!-- Revenue by Category + Monthly Trend -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
    <div class="card">
      <div class="card-header">📊 Revenue by Category</div>
      <div id="chart-category-revenue" style="height:320px;"></div>
    </div>
    <div class="card">
      <div class="card-header">📈 Monthly Revenue Trend</div>
      <div id="chart-monthly-trend" style="height:320px;"></div>
    </div>
  </section>

  <!-- Revenue by Location + Top Products -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
    <div class="card">
      <div class="card-header">📍 Revenue by City (Somalia)</div>
      <div id="chart-location-revenue" style="height:320px;"></div>
    </div>
    <div class="card">
      <div class="card-header">🏆 Top 12 Products by Revenue</div>
      <div id="chart-top-products" style="height:320px;"></div>
    </div>
  </section>

  <!-- Category Profit Margin + Sales Rep Performance -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
    <div class="card">
      <div class="card-header">💎 Profit Margin by Category</div>
      <div id="chart-category-margin" style="height:320px;"></div>
    </div>
    <div class="card">
      <div class="card-header">👥 Sales Rep Revenue</div>
      <div id="chart-sales-rep" style="height:320px;"></div>
    </div>
  </section>

  <!-- Price Tier + Payment Method -->
  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 fade-in">
    <div class="card">
      <div class="card-header">💰 Price Tier Distribution</div>
      <div id="chart-price-tier" style="height:260px;"></div>
    </div>
    <div class="card">
      <div class="card-header">💳 Payment Methods</div>
      <div id="chart-payment-method" style="height:260px;"></div>
    </div>
    <div class="card">
      <div class="card-header">📦 Category Volume</div>
      <div id="chart-category-volume" style="height:260px;"></div>
    </div>
    <div class="card">
      <div class="card-header">📊 Category Revenue Mix</div>
      <div id="chart-category-mix" style="height:260px;"></div>
    </div>
  </section>

  <!-- ML Model Comparison -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
    <div class="card">
      <div class="card-header">🧪 Model Performance Comparison (R²)</div>
      <div id="chart-model-compare" style="height:300px;"></div>
    </div>
    <div class="card">
      <div class="card-header">🔬 Top 15 Features (Feature Importance)</div>
      <div id="chart-feature-importance" style="height:300px;"></div>
    </div>
  </section>

  <!-- ML Metrics Table + Monthly Category Heatmap -->
  <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in">
    <div class="card">
      <div class="card-header">📋 Model Metrics Detail</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-700 text-slate-400">
              <th class="text-left py-3 px-3 font-semibold">Model</th>
              <th class="text-right py-3 px-3 font-semibold">R² Score</th>
              <th class="text-right py-3 px-3 font-semibold">MAE</th>
              <th class="text-right py-3 px-3 font-semibold">RMSE</th>
              <th class="text-right py-3 px-3 font-semibold">MAPE</th>
            </tr>
          </thead>
          <tbody>
            {''.join(f'''
            <tr class="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
              <td class="py-3 px-3 font-semibold text-white">{name}{" ★" if name == ml_best else ""}</td>
              <td class="py-3 px-3 text-right font-mono">{data["r2_score"]:.4f}</td>
              <td class="py-3 px-3 text-right font-mono">{money(data["mae"])}</td>
              <td class="py-3 px-3 text-right font-mono">{money(data["rmse"])}</td>
              <td class="py-3 px-3 text-right font-mono">{data["mape_pct"]:.1f}%</td>
            </tr>''' for name, data in ml_models.items())}
          </tbody>
        </table>
      </div>
      <div class="mt-4 p-3 bg-slate-800/50 rounded-xl border border-slate-700">
        <p class="text-xs text-slate-400"><span class="text-purple-400 font-semibold">Preprocessing:</span> Median impute → IQR capping (Q1−1.5·IQR / Q3+1.5·IQR) → StandardScaler</p>
        <p class="text-xs text-slate-400"><span class="text-purple-400 font-semibold">Categoricals:</span> Rare-level group (&lt;1% → OTHER) → OneHotEncoder(handle_unknown="ignore")</p>
        <p class="text-xs text-slate-400"><span class="text-purple-400 font-semibold">Train/Test:</span> {ml_train} train / {ml_test} test (stratified by Category, 80/20)</p>
        <p class="text-xs text-slate-400"><span class="text-purple-400 font-semibold">Target validation:</span> {results['verdict']} — best univariate feature: {results['best_univariate_feature']} (R²={results['best_univariate_r2']})</p>
      </div>
    </div>
    <div class="card">
      <div class="card-header">📅 Monthly Revenue by Category</div>
      <div id="chart-monthly-category" style="height:300px;"></div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="text-center text-slate-600 text-xs py-8 border-t border-slate-800">
    Kaamil Technology Sales Analytics · Built with Python (pandas, scikit-learn, ApexCharts) · {profile['generated_at']}
  </footer>

</main>

<script>
const SERIES = {{
  catLabels: {s(cat_labels)},
  catValues: {s(cat_values)},
  locLabels: {s(loc_labels)},
  locValues: {s(loc_values)},
  repLabels: {s(rep_labels)},
  repValues: {s(rep_values)},
  monthLabels: {s(month_labels_display)},
  monthValues: {s(month_values)},
  monthlyCatDatasets: {s(monthly_cat_datasets)},
  tierLabels: {s(tier_labels)},
  tierValues: {s(tier_values)},
  marginLabels: {s(margin_labels)},
  marginValues: {s(margin_values)},
  prodLabels: {s(prod_labels)},
  prodValues: {s(prod_values)},
  pmLabels: {s(pm_labels)},
  pmValues: {s(pm_values)},
  ccLabels: {s(cc_labels)},
  ccValues: {s(cc_values)},
  featLabels: {s(feat_labels)},
  featValues: {s(feat_values)},
  catMixValues: {s([float(v) for v in cat_rev.values()])},
  catMarginData: {s(cat_margin_data)},
}};

const CHART_COLORS = {{
  blue: '#3b82f6', green: '#10b981', amber: '#f59e0b', purple: '#a855f7',
  red: '#ef4444', cyan: '#06b6d4', pink: '#ec4899', indigo: '#6366f1',
}};

const chartDefaults = {{
  theme: {{ mode: 'dark' }},
  toolbar: {{ show: true, tools: {{ download: true, zoom: false, pan: false, reset: true }} }},
  stroke: {{ curve: 'smooth', width: 2 }},
  fill: {{ type: 'gradient', gradient: {{ opacityFrom: 0.3, opacityTo: 0.05 }} }},
  grid: {{ borderColor: '#1e293b', strokeDashArray: 4 }},
  xaxis: {{ labels: {{ style: {{ colors: '#94a3b8', fontSize: 11 }} }} }},
  yaxis: {{ labels: {{ style: {{ colors: '#94a3b8', fontSize: 11 }} }} }},
  legend: {{ labels: {{ style: {{ colors: '#cbd5e1', fontSize: 11 }} }} }},
  tooltip: {{ theme: 'dark' }},
}};

// 1. Revenue by Category
new ApexCharts(document.querySelector('#chart-category-revenue'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 320 }},
  series: [{{ name: 'Revenue ($)', data: SERIES.catValues }}],
  xaxis: {{ categories: SERIES.catLabels }},
  plotOptions: {{ bar: {{ borderRadius: 8, columnWidth: '55%' }} }},
  colors: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.purple],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }}, formatter: v => '$' + v.toLocaleString() }},
}}).render();

// 2. Monthly Trend
new ApexCharts(document.querySelector('#chart-monthly-trend'), {{
  ...chartDefaults,
  chart: {{ type: 'area', height: 320 }},
  series: [{{ name: 'Monthly Revenue', data: SERIES.monthValues }}],
  xaxis: {{ categories: SERIES.monthLabels }},
  stroke: {{ curve: 'smooth', width: 3 }},
  fill: {{ type: 'gradient', gradient: {{ opacityFrom: 0.4, opacityTo: 0.02 }} }},
  colors: [CHART_COLORS.green],
  markers: {{ size: 6, colors: ['#10b981'], strokeColor: '#065f46', strokeWidth: 2 }},
  yaxis: {{ labels: {{ style: {{ colors: '#94a3b8', fontSize: 11 }} }}, formatter: v => '$' + v.toLocaleString() }},
}}).render();

// 3. Location Revenue
new ApexCharts(document.querySelector('#chart-location-revenue'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 320 }},
  series: [{{ name: 'Revenue ($)', data: SERIES.locValues }}],
  xaxis: {{ categories: SERIES.locLabels, labels: {{ style: {{ colors: '#94a3b8', fontSize: 11 }} }} }},
  plotOptions: {{ bar: {{ borderRadius: 6, columnWidth: '60%', horizontal: true }} }},
  colors: [CHART_COLORS.indigo],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }}, formatter: v => '$' + v.toLocaleString() }},
}}).render();

// 4. Top Products
new ApexCharts(document.querySelector('#chart-top-products'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 320 }},
  series: [{{ name: 'Revenue ($)', data: SERIES.prodValues }}],
  xaxis: {{ categories: SERIES.prodLabels, labels: {{ style: {{ colors: '#94a3b8', fontSize: 10 }} }} }},
  plotOptions: {{ bar: {{ borderRadius: 6, columnWidth: '70%', horizontal: true }} }},
  colors: [CHART_COLORS.amber, CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.purple, CHART_COLORS.red, CHART_COLORS.cyan, CHART_COLORS.pink, CHART_COLORS.indigo, CHART_COLORS.amber, CHART_COLORS.green, CHART_COLORS.blue, CHART_COLORS.purple],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }}, formatter: v => '$' + v.toLocaleString() }},
}}).render();

// 5. Category Margin
new ApexCharts(document.querySelector('#chart-category-margin'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 320 }},
  series: [{{ name: 'Profit Margin (%)', data: SERIES.marginValues }}],
  xaxis: {{ categories: SERIES.marginLabels }},
  plotOptions: {{ bar: {{ borderRadius: 8, columnWidth: '50%' }} }},
  colors: [CHART_COLORS.green, CHART_COLORS.blue, CHART_COLORS.amber, CHART_COLORS.purple],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }}, formatter: v => v.toFixed(1) + '%' }},
}}).render();

// 6. Sales Rep
new ApexCharts(document.querySelector('#chart-sales-rep'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 320 }},
  series: [{{ name: 'Revenue ($)', data: SERIES.repValues }}],
  xaxis: {{ categories: SERIES.repLabels, labels: {{ style: {{ colors: '#94a3b8', fontSize: 10 }} }} }},
  plotOptions: {{ bar: {{ borderRadius: 6, columnWidth: '60%', horizontal: true }} }},
  colors: [CHART_COLORS.purple, CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.cyan, CHART_COLORS.pink],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }}, formatter: v => '$' + v.toLocaleString() }},
}}).render();

// 7. Price Tier Doughnut
new ApexCharts(document.querySelector('#chart-price-tier'), {{
  ...chartDefaults,
  chart: {{ type: 'donut', height: 260 }},
  series: SERIES.tierValues,
  labels: SERIES.tierLabels,
  colors: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.purple],
  legend: {{ position: 'bottom', labels: {{ style: {{ colors: '#cbd5e1', fontSize: 11 }} }} }},
}}).render();

// 8. Payment Method Doughnut
new ApexCharts(document.querySelector('#chart-payment-method'), {{
  ...chartDefaults,
  chart: {{ type: 'donut', height: 260 }},
  series: SERIES.pmValues,
  labels: SERIES.pmLabels,
  colors: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.purple, CHART_COLORS.red, CHART_COLORS.cyan],
  legend: {{ position: 'bottom', labels: {{ style: {{ colors: '#cbd5e1', fontSize: 11 }} }} }},
}}).render();

// 9. Category Volume
new ApexCharts(document.querySelector('#chart-category-volume'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 260 }},
  series: [{{ name: 'Transactions', data: SERIES.ccValues }}],
  xaxis: {{ categories: SERIES.ccLabels }},
  plotOptions: {{ bar: {{ borderRadius: 8, columnWidth: '50%' }} }},
  colors: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.purple],
  dataLabels: {{ enabled: true, style: {{ colors: ['#e2e8f0'] }} }},
}}).render();

// 10. Category Mix (100% stacked)
new ApexCharts(document.querySelector('#chart-category-mix'), {{
  ...chartDefaults,
  chart: {{ type: 'pie', height: 260 }},
  series: SERIES.catMixValues,
  labels: SERIES.catLabels,
  colors: [CHART_COLORS.blue, CHART_COLORS.green, CHART_COLORS.amber, CHART_COLORS.purple],
  legend: {{ position: 'bottom', labels: {{ style: {{ colors: '#cbd5e1', fontSize: 11 }} }} }},
}}).render();

// 11. Model Comparison
new ApexCharts(document.querySelector('#chart-model-compare'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 300 }},
  series: [
    {{ name: 'R²', data: Object.values({s(ml_models)}).map(m => m.r2_score) }},
    {{ name: 'MAPE %', data: Object.values({s(ml_models)}).map(m => m.mape_pct) }},
  ],
  xaxis: {{ categories: Object.keys({s(ml_models)}) }},
  plotOptions: {{ bar: {{ borderRadius: 8, columnWidth: '40%' }} }},
  colors: [CHART_COLORS.green, CHART_COLORS.amber],
}}).render();

// 12. Feature Importance
new ApexCharts(document.querySelector('#chart-feature-importance'), {{
  ...chartDefaults,
  chart: {{ type: 'bar', height: 300 }},
  series: [{{ name: 'Importance', data: SERIES.featValues }}],
  xaxis: {{ categories: SERIES.featLabels, labels: {{ style: {{ colors: '#94a3b8', fontSize: 9 }} }} }},
  plotOptions: {{ bar: {{ borderRadius: 4, columnWidth: '70%', horizontal: true }} }},
  colors: [CHART_COLORS.indigo],
  dataLabels: {{ enabled: true, style: {{ colors: ['#94a3b8'] }}, formatter: v => v.toFixed(3) }},
}}).render();

// 13. Monthly Category stacked area
new ApexCharts(document.querySelector('#chart-monthly-category'), {{
  ...chartDefaults,
  chart: {{ type: 'area', height: 300, stacked: true }},
  series: SERIES.monthlyCatDatasets.map(d => ({{ name: d.name, data: d.data }})),
  xaxis: {{ categories: SERIES.monthLabels }},
  colors: SERIES.monthlyCatDatasets.map(d => d.color),
  stroke: {{ curve: 'smooth', width: 2 }},
  fill: {{ type: 'gradient', gradient: {{ opacityFrom: 0.3, opacityTo: 0.05 }} }},
  yaxis: {{ labels: {{ style: {{ colors: '#94a3b8' }}, formatter: v => '$' + v.toLocaleString() }} }},
}}).render();
</script>
</body>
</html>"""

# Write dashboard
DASHBOARD_PATH.write_text(html, encoding="utf-8")
print(f"Dashboard written: {DASHBOARD_PATH}")
print(f"Size: {DASHBOARD_PATH.stat().st_size:,} bytes")