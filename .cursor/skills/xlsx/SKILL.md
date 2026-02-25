---
name: xlsx
description: Enable the agent to read, analyze, and modify Excel (.xlsx) spreadsheets using Python while preserving formulas and formatting. Use when the user mentions Excel files, spreadsheets, schedules, or xlsx-based reports.
---

# XLSX Spreadsheet Skill

## Mission

Help the user work with Excel (`.xlsx`) files in a **safe and reproducible** way:
- Read and explore existing spreadsheets.
- Transform and analyze data.
- Create or update sheets while preserving formulas and formatting where possible.

## Recommended Stack

When using Python:

- `pandas` – high‑level reading/writing and data manipulation.
- `openpyxl` – working directly with Excel cells, formulas, and styles.

Advise the user to install dependencies similar to:

```bash
pip install pandas openpyxl
```

## Typical Workflows

### 1. Inspect an Existing Workbook

Steps:
1. List sheets in the file.
2. Load specific sheets into `pandas` DataFrames.
3. Show column names, dtypes, and sample rows.

Always ask:
- Which sheet(s) are relevant?
- What is the grain (one row per what)?

### 2. Clean and Transform Data

For tabular data:
- Handle missing values (drop, fill, or flag).
- Normalize column names (snake_case, no spaces).
- Convert types (dates, numbers, categories).
- Filter and aggregate as needed.

Return:
- Example Python code.
- Short explanation of each transformation.

### 3. Preserve Formulas and Formatting

When modifying existing models:
- Prefer inserting data **into clearly marked input ranges**.
- Avoid overwriting formula cells.
- If needed, use `openpyxl` to:
  - Read cell values and formulas.
  - Write new values while leaving formulas intact.

Explain clearly which cells or ranges will be changed.

### 4. Generate New Excel Reports

When the user wants a new report:
- Clarify:
  - Sheet names.
  - Layout (tables, summaries, charts).
  - Required columns and metrics.
- Use `pandas` to produce summary tables.
- Write them back to Excel with:
  - Clear sheet names (`Summary`, `Details`, etc.).
  - Optional styling if needed (`openpyxl` or `xlsxwriter`).

## Safety & Good Practices

- Never assume paths; ask the user for the exact file location.
- Avoid hard‑coding absolute paths in examples; use relative paths when possible.
- Warn the user before overwriting files; suggest writing to a **new output file** first (e.g. `output.xlsx`).

## Output Format

When responding to a request involving Excel:

1. **Goal** – what needs to be done with the spreadsheet.
2. **Plan** – short bullet list of steps.
3. **Code** – Python snippets using `pandas` and `openpyxl` as relevant.
4. **Notes** – any caveats about formulas, formatting, or performance.

Keep examples concise and reusable.

