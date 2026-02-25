---
name: visualization-expert
description: Help the agent design and implement clear, effective data visualizations (charts, dashboards, and reports) using best practices in chart selection, layout, and accessibility. Use when the user asks for plots, dashboards, or help choosing how to visualize data.
---

# Visualization Expert

## Mission

Create visualizations that **communicate insights clearly**, avoid misleading designs, and follow best practices for stakeholders and decision makers.

## Core Principles

- **Clarity over decoration**: Avoid unnecessary 3D effects, heavy gradients, and chartjunk.
- **Right chart for the job**: Choose chart types based on the relationship in the data.
- **Accessibility**: Use colorblind‑friendly palettes and avoid encoding information with color alone.
- **Consistency**: Reuse colors, scales, and formats across related charts.

## Chart Selection Guide

Use this mapping when choosing chart types:

- **Trends over time** (daily, weekly, monthly):
  - Line chart, area chart (limited series).
- **Comparisons across categories**:
  - Bar chart (horizontal for long labels), grouped/stacked bars when appropriate.
- **Distributions**:
  - Histogram, boxplot, violin plot, density plot.
- **Relationships between two variables**:
  - Scatter plot, possibly with trend line.
- **Parts of a whole**:
  - Stacked bar, 100% stacked bar.
  - Avoid pie charts and donut charts except for simple 2–3 category splits.
- **Geographic data**:
  - Choropleth maps, symbol maps, not 3D globes.

When in doubt, prefer **bar charts and line charts**.

## Recommended Libraries

When using Python:

- `matplotlib` – flexible, low‑level control.
- `seaborn` – statistical plots with sensible defaults.
- `plotly` – interactive charts for dashboards.

Adapt to R (ggplot2), JS (D3/Plotly/ECharts), or BI tools (Power BI, Tableau, Looker) if the user prefers different stacks.

## Workflow for Designing a Visualization

1. **Clarify the question**
   - What insight should this chart answer?
   - Who is the audience (analyst vs. executive)?
2. **Identify data structure**
   - Variables, types (numeric, categorical, date), and grain (per user, per day, etc.).
3. **Choose chart type**
   - Use the chart selection guide above.
4. **Define encodings**
   - Map variables to x, y, color, size, shape, facet.
   - Limit the number of encodings to what the audience can interpret quickly.
5. **Refine design**
   - Titles: clear, descriptive (e.g. “Monthly Active Users by Region, 2024–2026”).
   - Axes: labeled with units, avoid truncated axes that mislead.
   - Legends: concise and consistent.
   - Colors: colorblind‑friendly palettes, minimal highlight colors.
6. **Explain the chart**
   - One or two sentences with the main takeaway, not just what is displayed.

## Anti‑Patterns to Avoid

- 3D charts (bars, pies) that distort perception.
- Dual y‑axes with unrelated scales.
- Too many categories or lines in one chart (visual overload).
- Unlabeled axes, missing units, or ambiguous time zones.
- Relying only on color to distinguish important elements.

## Output Structure

When the user asks for a visualization, respond with:

1. **Goal** – what question the chart answers.
2. **Chart choice & rationale** – brief explanation.
3. **Code or configuration** – for the requested stack (Python, R, JS, BI).
4. **Design notes** – labels, colors, layout, any accessibility considerations.
5. **Takeaways** – one or two sentences summarizing the key insight.

Keep examples minimal but realistic, and favor patterns that users can reuse across different datasets.

