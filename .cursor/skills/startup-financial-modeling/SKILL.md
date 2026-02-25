---
name: startup-financial-modeling
description: Help the agent build multi-year financial models for startups, including revenue projections, cost structures, cash runway, and scenario analysis. Use when the user asks for financial projections, burn rate, runway, or investor-ready startup models.
---

# Startup Financial Modeling

## Mission

Guide the user through building **structured, transparent financial models** for early‑stage startups (typically 3–5 years), focusing on:
- Revenue projections.
- Cost structure.
- Headcount planning.
- Cash flow and runway.
- Scenario analysis (conservative, base, optimistic).

## Discovery Questions

Before modeling, ask the user:

1. **Business model**
   - SaaS, marketplace, ecommerce, consumer app, etc.
   - Primary revenue driver (subscriptions, transactions, ads).
2. **Current status**
   - Stage (pre‑revenue, early revenue, growth).
   - Current MRR/ARR, customer count, ARPU, churn (if available).
3. **Time horizon**
   - Typically 3–5 years; clarify monthly vs. quarterly detail.
4. **Key assumptions**
   - Growth expectations, churn/retention, pricing, hiring plans.
5. **Use case**
   - Internal planning, fundraising deck, board reporting, bank loan.

Summarize the modeling plan before creating detailed sheets or code.

## Model Structure

Recommend splitting the model into logical tabs or sections:

1. **Assumptions**
   - Inputs for growth rates, pricing, churn, hiring, unit economics.
   - Keep all major assumptions centralized and easy to edit.
2. **Revenue**
   - Customer acquisition, retention, ARPU, and expansion.
   - Cohort or simple growth curves depending on complexity.
3. **Costs**
   - Cost of Goods Sold (COGS).
   - Sales & Marketing (S&M).
   - Research & Development (R&D).
   - General & Administrative (G&A).
4. **Headcount**
   - Hiring plan by team, with salaries and start dates.
5. **Cash Flow**
   - Monthly burn, cash in/out, runway.
6. **Scenarios**
   - Conservative (P10), Base (P50), Optimistic (P90).

## Key Formulas & Concepts

- **MRR / ARR**
  - MRR = Monthly Recurring Revenue.
  - ARR = MRR × 12.
- **Burn rate**
  - Burn = Cash outflows − Cash inflows (usually per month).
- **Runway**
  - Runway (months) = Current cash balance / Monthly burn.
- **Unit economics (SaaS example)**
  - LTV, CAC, LTV/CAC ratio, payback period.

Explain definitions clearly and avoid ambiguous terminology.

## Scenario Analysis

When the user requests scenarios:

- **Conservative (P10)**
  - Lower growth, higher churn, slower hiring.
- **Base (P50)**
  - Most likely case for planning and board reporting.
- **Optimistic (P90)**
  - Strong growth, better retention, efficient acquisition.

Structure the model so that assumptions drive all three scenarios, ideally with a single scenario selector or parallel blocks.

## Excel / Spreadsheet Integration

If building the model in spreadsheets:

- Clearly label tabs and input cells.
- Use formulas rather than hard‑coded numbers wherever possible.
- Encourage the user to:
  - Highlight input cells.
  - Document key assumptions in a dedicated section.

If using Python + `pandas` (or similar):

- Mirror the same structure in DataFrames.
- Provide export to Excel/CSV for sharing.

## Output Format

When helping the user, structure responses as:

1. **Overview** – what the model will cover and time horizon.
2. **Assumptions** – bullet list of key inputs with suggested starting values.
3. **Structure** – outline of tabs/sections and data flows.
4. **Implementation** – spreadsheet formulas or code snippets.
5. **Insights** – interpretation of runway, growth, and risk.

Avoid giving investment advice; focus on modeling and clarity.

