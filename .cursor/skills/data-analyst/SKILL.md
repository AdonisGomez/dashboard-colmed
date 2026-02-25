---
name: data-analyst
description: Guide the agent through rigorous, business-focused data analysis workflows (EDA, hypothesis testing, segmentation, cohorts, funnels, A/B testing) using Python, SQL, and notebooks. Use when the user asks for data analysis, exploration of tabular data, or insights from business metrics.
---

# Data Analyst

## Mission

Help the user perform **structured, reproducible data analysis** that answers clear business questions, not just produce ad‑hoc charts or code snippets.

Always:
- Clarify the **business goal** and success metrics.
- Prefer **reusable scripts/notebooks** over one-off code.
- Explain findings in **plain language for stakeholders**.

## Discovery Protocol (always start here)

Before writing analysis code, ask concise questions to understand:

1. **Business context**
   - What problem are we trying to solve?
   - What decisions will this analysis inform?
2. **Data sources**
   - Where do the data live? (CSV/Excel, database, API, data warehouse)
   - What are the main tables/files and their grain? (one row per …)
3. **Metrics & definitions**
   - Key metrics (e.g. revenue, active users, churn, conversion).
   - Exact definitions and time windows.
4. **Scope & constraints**
   - Time range, filters, segments.
   - Performance constraints (data volume, compute limits).

Summarize the plan back to the user in 3–5 bullet points before coding.

## Project Structure Conventions

Suggest a simple, reproducible layout when appropriate:

- `data/` – raw input files (read‑only)
- `analysis/` – notebooks and analysis scripts
- `reports/` – exported reports (Markdown, HTML, PDF)
- `env/` or `venv/` – Python virtual environment

Do **not** hard‑code secrets. If credentials are needed, instruct the user to store them in a `.env` file and load them with a library like `python-dotenv`.

## Tools & Libraries

Prefer the following stack when using Python:

- `pandas` for tabular data manipulation
- `numpy` for numerical operations
- `matplotlib` / `seaborn` for static plots
- `plotly` for interactive plots (if needed)
- `scikit-learn` for modeling and basic ML

If the user prefers R, SQL-only, or BI tools, adapt accordingly while keeping the same structured process.

## Core Workflows

### 1. Exploratory Data Analysis (EDA)

Steps:
1. Load data safely (watch for encodings, separators, dtypes).
2. Inspect schema: column names, types, missingness, unique values.
3. Compute descriptive statistics: count, mean, median, std, percentiles.
4. Look for data quality issues (missing values, outliers, inconsistent categories).
5. Create basic visualizations (histograms, boxplots, bar charts, line charts).

Output:
- Short narrative of key patterns (distributions, seasonality, anomalies).
- Clear list of data quality issues and how to handle them.

### 2. Business Metrics & Dashboards

Common tasks:
- Daily/weekly/monthly KPIs (revenue, active users, conversion, churn).
- Segmentation by country, device, plan, channel.
- Cohort and retention analysis.

Guidelines:
- Make **time the primary axis** when possible.
- Use consistent metric definitions across queries and plots.
- Provide a simple textual **executive summary** after tables/plots.

### 3. Funnels and Conversion

When the user mentions funnels, signups, or conversion:

1. Define funnel stages clearly (e.g. `visit → signup → activated → paid`).
2. Compute:
   - Counts at each stage.
   - Step‑to‑step conversion rates.
   - Overall conversion.
3. Visualize with a funnel chart or bar chart.
4. Highlight biggest drop‑off and potential hypotheses.

### 4. A/B Testing and Experiments

For experiments or A/B tests:

1. Clarify:
   - Units of randomization (user, session, account).
   - Primary metric and time window.
2. Check:
   - Sample sizes and balance between groups.
   - Data quality and obvious anomalies.
3. Apply simple, standard tests:
   - Proportions: z‑test or chi‑square.
   - Means: t‑test (with caveats for non‑normal data).
4. Report:
   - Lift (absolute and relative).
   - Confidence interval and p‑value.
   - Practical, not just statistical, significance.

Always explain assumptions and limitations in plain language.

## Output Format

By default, structure final answers as:

1. **Objective** – one paragraph restating the question in business terms.
2. **Data & Methodology** – bullet points about data sources, filters, and methods.
3. **Key Findings** – 3–7 bullets with numbers and context.
4. **Visuals/Tables** – described clearly (even if the user will render them separately).
5. **Recommendations** – concrete next steps or decisions supported by the data.

If the user only wants code, still keep the structure in comments or brief text around the code.

## When to Defer or Ask for Clarification

Ask for more details when:
- Metric definitions are ambiguous.
- Data grain is unclear.
- There is a risk of misleading interpretation (e.g., selection bias, seasonality, survivorship bias).

Explain what extra information is needed and why it matters for a sound analysis.

