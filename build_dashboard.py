"""
Genera el dashboard de socios con cuotas pendientes por rango de días.
Lee RECUPERACION_DE_MORA.csv y cuenta socios únicos con monto > 0 en cada rango.

Moneda: USD (dólares estadounidenses).
Rangos: 1-30, 31-60, 61-90, 91-120, más de 121 días.
"""
import pandas as pd
from pathlib import Path

CSV_MORA = Path(__file__).parent / "RECUPERACION_DE_MORA.csv"
OUT_HTML = Path(__file__).parent / "sep" / "dashboard_cuotas_pendientes.html"

RANGOS = [
    ("1-30 días", "de 0 a 30"),
    ("31-60 días", "de 31 a 60"),
    ("61-90 días", "de 61 a 90"),
    ("91-120 días", "de 91 a 120"),
    ("Más de 121 días", "mas de 121 días"),
]


def main():
    df = pd.read_csv(CSV_MORA, encoding="utf-8-sig")
    # Normalizar nombres de columnas (encoding)
    df.columns = [c.strip().replace("", "í").replace("das", "días") for c in df.columns]
    cod = "Codigo asociado"

    # Por cada rango: socios que tienen al menos una cuota con monto > 0 en ese rango
    resultados = []
    for etiqueta, col in RANGOS:
        col_ok = None
        for c in df.columns:
            if col in c or c.strip() == col:
                col_ok = c
                break
        if col_ok is None:
            col_ok = [c for c in df.columns if "30" in c or "60" in c or "90" in c or "120" in c or "121" in c]
            # Mapear por posición típica
            idx = next((i for i, (_, c) in enumerate(RANGOS) if c in col), 0)
            if idx < len(df.columns):
                col_ok = df.columns[[c for c in df.columns if "30" in str(c) or "60" in str(c) or "90" in str(c) or "120" in str(c) or "121" in str(c)][min(idx, 4)]]
            else:
                col_ok = df.columns[5]  # de 0 a 30
        if isinstance(col_ok, list):
            col_ok = col_ok[0] if col_ok else None
        if col_ok is None:
            continue
        try:
            valores = pd.to_numeric(df[col_ok], errors="coerce").fillna(0)
            socios_rango = df.loc[valores > 0, cod].nunique()
        except Exception:
            socios_rango = 0
        resultados.append((etiqueta, int(socios_rango)))

    # Monto total por rango (opcional para el dashboard)
    montos = []
    for etiqueta, col in RANGOS:
        col_ok = None
        for c in df.columns:
            if "0 a 30" in c and "31" not in c:
                if "1-30" in etiqueta:
                    col_ok = c
                    break
            if "31 a 60" in c:
                if "31-60" in etiqueta:
                    col_ok = c
                    break
            if "61 a 90" in c:
                if "61-90" in etiqueta:
                    col_ok = c
                    break
            if "91 a 120" in c:
                if "91-120" in etiqueta:
                    col_ok = c
                    break
            if "121" in c:
                if "121" in etiqueta:
                    col_ok = c
                    break
        if col_ok is None:
            for c in df.columns:
                if col in c:
                    col_ok = c
                    break
        if col_ok is None:
            montos.append((etiqueta, 0.0))
            continue
        try:
            m = pd.to_numeric(df[col_ok], errors="coerce").fillna(0).sum()
            montos.append((etiqueta, round(float(m), 2)))
        except Exception:
            montos.append((etiqueta, 0.0))

    return resultados, montos


def get_col_mapping(df):
    """Encuentra columnas de rango por orden: 0-30, 31-60, 61-90, 91-120, 121+."""
    cols = list(df.columns)
    out = []
    for k in ["0 a 30", "31 a 60", "61 a 90", "91 a 120", "121"]:
        for c in cols:
            if k in c and c not in out:
                out.append(c)
                break
    return out


if __name__ == "__main__":
    df = pd.read_csv(CSV_MORA, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    cod = "Codigo asociado"
    col_fecha = "Fecha de cuota" if "Fecha de cuota" in df.columns else None

    # Detectar columnas de rangos (por orden)
    col_rangos = get_col_mapping(df)
    if len(col_rangos) < 5:
        col_rangos = [c for c in df.columns[5:10] if c]  # fallback
    etiquetas = ["1-30 días", "31-60 días", "61-90 días", "91-120 días", "Más de 121 días"][: len(col_rangos)]

    # Normalizar a numérico (USD)
    for c in col_rangos:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # KPI globales
    total_cuotas = int(len(df))
    total_socios = int(df[cod].nunique())
    total_monto = float(df[col_rangos].sum(axis=1).sum())

    # Resumen por rango (socios, cuotas, monto, %)
    resumen = []
    for etiq, col in zip(etiquetas, col_rangos):
        v = df[col]
        cuotas_rango = int((v > 0).sum())
        socios_rango = int(df.loc[v > 0, cod].nunique())
        monto_rango = float(v.sum())
        resumen.append(
            {
                "rango": etiq,
                "socios": socios_rango,
                "cuotas": cuotas_rango,
                "monto": round(monto_rango, 2),
                "pct_monto": (monto_rango / total_monto * 100) if total_monto else 0.0,
                "pct_socios": (socios_rango / total_socios * 100) if total_socios else 0.0,
            }
        )

    # Top socios por monto total (suma de rangos)
    df["_monto_total_socio"] = df[col_rangos].sum(axis=1)
    top_socios = (
        df.groupby(cod)["_monto_total_socio"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .reset_index()
        .rename(columns={cod: "socio", "_monto_total_socio": "monto"})
    )
    top_socios["monto"] = top_socios["monto"].round(2)

    # Última fecha de cuota por socio (si existe)
    ult_fecha = None
    if col_fecha is not None:
        fechas = pd.to_datetime(df[col_fecha], errors="coerce")
        ult_fecha = (
            pd.DataFrame({cod: df[cod], "_fecha": fechas})
            .groupby(cod)["_fecha"]
            .max()
            .reset_index()
            .rename(columns={"_fecha": "ultima_fecha"})
        )
        ult_fecha["ultima_fecha"] = ult_fecha["ultima_fecha"].dt.strftime("%Y-%m-%d")
        top_socios = top_socios.merge(ult_fecha, left_on="socio", right_on=cod, how="left").drop(columns=[cod])

    # Generar HTML
    max_socios = max((r["socios"] for r in resumen), default=1)
    max_monto = max((r["monto"] for r in resumen), default=1.0)
    html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard – Cuotas pendientes (USD)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #050816;
      --bg-elevated: #0b1020;
      --card: #111827;
      --card-soft: #161f2f;
      --text: #f9fafb;
      --muted: #9ca3af;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.12);
      --green: #22c55e;
      --yellow: #eab308;
      --orange: #f97316;
      --red: #ef4444;
      --border: rgba(148, 163, 184, 0.4);
    }
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    body {
      font-family: 'DM Sans', sans-serif;
      background:
        radial-gradient(circle at top left, #1d283a 0, transparent 50%),
        radial-gradient(circle at bottom right, #0f172a 0, transparent 55%),
        var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 2.5rem 1.5rem;
      display: flex;
      justify-content: center;
      align-items: flex-start;
    }
    .container {
      width: 100%;
      max-width: 1200px;
      margin: 0 auto;
      background: linear-gradient(145deg, rgba(15,23,42,0.96), rgba(15,23,42,0.98));
      border-radius: 18px;
      border: 1px solid rgba(148, 163, 184, 0.35);
      box-shadow:
        0 24px 60px rgba(15, 23, 42, 0.9),
        0 0 0 1px rgba(15, 23, 42, 1);
      padding: 1.75rem 1.75rem 1.5rem;
      backdrop-filter: blur(14px);
    }
    .header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1.25rem;
      flex-wrap: wrap;
      margin-bottom: 1.5rem;
    }
    h1 {
      font-size: 1.9rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      letter-spacing: -0.03em;
    }
    .subtitle {
      color: var(--muted);
      font-size: 0.95rem;
    }
    .meta {
      color: var(--muted);
      font-size: 0.85rem;
      text-align: right;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(4, minmax(180px, 1fr));
      gap: 1rem;
      margin: 1.35rem 0 1.75rem;
    }
    .card {
      position: relative;
      background: radial-gradient(circle at top left, rgba(56,189,248,0.08), transparent 55%), var(--card);
      border-radius: 14px;
      padding: 1.1rem 1.1rem 1.05rem;
      border: 1px solid rgba(148, 163, 184, 0.32);
      box-shadow:
        0 14px 30px rgba(15, 23, 42, 0.7),
        inset 0 0 0 1px rgba(15, 23, 42, 0.9);
      overflow: hidden;
    }
    .card:before {
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(circle at top right, rgba(56,189,248,0.18), transparent 60%);
      opacity: 0;
      transition: opacity 0.25s ease-out;
      pointer-events: none;
    }
    .card:hover:before {
      opacity: 1;
    }
    .card .label {
      color: var(--muted);
      font-size: 0.8rem;
      margin-bottom: 0.35rem;
    }
    .card .value {
      font-size: 1.8rem;
      font-weight: 700;
      letter-spacing: -0.04em;
    }
    .card .monto {
      font-size: 0.82rem;
      color: var(--muted);
      margin-top: 0.3rem;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 1.1rem;
      align-items: start;
    }
    .panel {
      background: radial-gradient(circle at top left, rgba(15,118,110,0.08), transparent 55%), var(--bg-elevated);
      border-radius: 14px;
      padding: 1.25rem 1.25rem 1.15rem;
      border: 1px solid rgba(148, 163, 184, 0.28);
      box-shadow:
        0 16px 36px rgba(15, 23, 42, 0.75),
        inset 0 0 0 1px rgba(15, 23, 42, 0.9);
    }
    .panel h2 {
      font-size: 1rem;
      margin-bottom: 0.85rem;
      color: var(--text);
      font-weight: 700;
      letter-spacing: -0.01em;
    }
    .panel .hint {
      color: var(--muted);
      font-size: 0.83rem;
      margin-top: -0.3rem;
      margin-bottom: 1rem;
    }
    .bar-row {
      margin-bottom: 1rem;
    }
    .bar-row:last-of-type {
      margin-bottom: 0.2rem;
    }
    .bar-row .flex {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.35rem;
    }
    .bar-row .flex span:first-child {
      font-size: 0.9rem;
    }
    .bar-row .flex span:last-child {
      font-weight: 600;
      font-size: 0.86rem;
      color: var(--accent);
    }
    .bar-bg {
      height: 23px;
      background: rgba(15,23,42,0.85);
      border-radius: 999px;
      overflow: hidden;
      border: 1px solid rgba(148,163,184,0.35);
    }
    .bar-fill {
      height: 100%;
      border-radius: inherit;
      transition: width 0.55s cubic-bezier(0.22, 0.61, 0.36, 1);
    }
    .bar-fill.r1 { background: linear-gradient(90deg, #22c55e, #4ade80); }
    .bar-fill.r2 { background: linear-gradient(90deg, #eab308, #facc15); }
    .bar-fill.r3 { background: linear-gradient(90deg, #f97316, #fdba74); }
    .bar-fill.r4 { background: linear-gradient(90deg, #f97316, #ef4444); }
    .bar-fill.r5 { background: linear-gradient(90deg, #ef4444, #b91c1c); }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }
    th,
    td {
      padding: 0.6rem 0.5rem;
      border-bottom: 1px solid rgba(31,41,55,0.9);
    }
    th {
      text-align: left;
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    td.num {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.22rem 0.6rem;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #e0f2fe;
      font-size: 0.75rem;
      border: 1px solid rgba(56,189,248,0.45);
    }
    .pill::before {
      content: "";
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 0 4px rgba(34,197,94,0.35);
    }
    .footer {
      margin-top: 1.4rem;
      font-size: 0.78rem;
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem 1.1rem;
      justify-content: flex-start;
    }
    .footer code {
      font-size: 0.78rem;
    }
    @media (max-width: 1024px) {
      body {
        padding: 2rem 1.25rem;
      }
      .container {
        padding: 1.5rem 1.4rem 1.3rem;
      }
      .cards {
        grid-template-columns: repeat(2, minmax(160px, 1fr));
      }
      .grid-2 {
        grid-template-columns: 1fr;
      }
      .meta {
        text-align: left;
      }
    }
    @media (max-width: 640px) {
      body {
        padding: 1.5rem 1rem;
      }
      .container {
        padding: 1.25rem 1.1rem 1.05rem;
        border-radius: 14px;
      }
      .header {
        align-items: flex-start;
      }
      h1 {
        font-size: 1.5rem;
      }
      .subtitle {
        font-size: 0.88rem;
      }
      .cards {
        grid-template-columns: 1fr;
      }
      .card {
        padding: 1rem 1rem 0.95rem;
      }
      .card .value {
        font-size: 1.55rem;
      }
      .panel {
        padding: 1.1rem 1rem 1rem;
      }
      th,
      td {
        padding-inline: 0.35rem;
      }
      .footer {
        flex-direction: column;
        align-items: flex-start;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>Cuotas pendientes por rango de días</h1>
        <p class="subtitle">Socios y cuotas en mora según antigüedad · <span class="pill">Moneda: USD</span></p>
      </div>
      <div class="meta">
        <div>Fuente: <strong>RECUPERACION_DE_MORA.csv</strong></div>
      </div>
    </div>

  <div class="cards">
    <div class="card">
      <div class="label">Socios con mora (únicos)</div>
      <div class="value">""" + f"""{total_socios:,}""" + """</div>
      <div class="monto">en el dataset</div>
    </div>
    <div class="card">
      <div class="label">Cuotas pendientes (filas)</div>
      <div class="value">""" + f"""{total_cuotas:,}""" + """</div>
      <div class="monto">cuotas en mora</div>
    </div>
    <div class="card">
      <div class="label">Monto total en mora</div>
      <div class="value">""" + f"""{total_monto:,.2f}""" + """</div>
      <div class="monto">USD</div>
    </div>
    <div class="card">
      <div class="label">Rangos</div>
      <div class="value">""" + f"""{len(resumen)}""" + """</div>
      <div class="monto">segmentos de antigüedad</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="panel">
      <h2>Distribución por rango (socios y monto)</h2>
      <div class="hint">Barras: ancho por # de socios · Porcentaje: sobre total de socios / monto</div>
"""
    for i, r in enumerate(resumen):
        etiq = r["rango"]
        socios = r["socios"]
        cuotas = r["cuotas"]
        monto = r["monto"]
        pct_socios = r["pct_socios"]
        pct_monto = r["pct_monto"]
        w_socios = (socios / max_socios * 100) if max_socios else 0
        w_monto = (monto / max_monto * 100) if max_monto else 0
        rclass = f"r{i + 1}"
        html += f"""
      <div class="bar-row">
        <div class="flex">
          <span><strong>{etiq}</strong> · {cuotas:,} cuotas · {monto:,.2f} USD</span>
          <span>{socios:,} socios · {pct_socios:.1f}%</span>
        </div>
        <div class="bar-bg"><div class="bar-fill {rclass}" style="width:{w_socios:.0f}%"></div></div>
        <div style="display:flex; justify-content:space-between; color:var(--muted); font-size:0.8rem; margin-top:0.25rem;">
          <span>Monto: {pct_monto:.1f}%</span>
          <span>Intensidad (monto): {w_monto:.0f}%</span>
        </div>
      </div>
"""

    # Tabla resumen
    html += """
      <h2 style="margin-top:1.25rem;">Tabla resumen</h2>
      <table>
        <thead>
          <tr>
            <th>Rango</th>
            <th class="num">Socios</th>
            <th class="num">Cuotas</th>
            <th class="num">Monto (USD)</th>
            <th class="num">% Socios</th>
            <th class="num">% Monto</th>
          </tr>
        </thead>
        <tbody>
"""
    for r in resumen:
        html += f"""
          <tr>
            <td>{r['rango']}</td>
            <td class="num">{r['socios']:,}</td>
            <td class="num">{r['cuotas']:,}</td>
            <td class="num">{r['monto']:,.2f}</td>
            <td class="num">{r['pct_socios']:.1f}%</td>
            <td class="num">{r['pct_monto']:.1f}%</td>
          </tr>
"""
    html += """
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h2>Top socios por monto en mora</h2>
      <div class="hint">Top 15 por monto total (suma de cuotas pendientes)</div>
      <table>
        <thead>
          <tr>
            <th>Socio</th>
            <th class="num">Monto (USD)</th>
            <th class="num">Últ. fecha</th>
          </tr>
        </thead>
        <tbody>
"""
    if "ultima_fecha" in top_socios.columns:
        for _, row in top_socios.iterrows():
            html += f"""
          <tr>
            <td>{int(row['socio'])}</td>
            <td class="num">{float(row['monto']):,.2f}</td>
            <td class="num">{row.get('ultima_fecha','')}</td>
          </tr>
"""
    else:
        for _, row in top_socios.iterrows():
            html += f"""
          <tr>
            <td>{int(row['socio'])}</td>
            <td class="num">{float(row['monto']):,.2f}</td>
            <td class="num">-</td>
          </tr>
"""
    html += """
        </tbody>
      </table>
    </div>
  </div>

  <p class="footer">Generado con <code>build_dashboard.py</code> · Fuente: <code>RECUPERACION_DE_MORA.csv</code> · Moneda: USD</p>
  </div>
</body>
</html>
"""
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard generado: {OUT_HTML}")
    for r in resumen:
        print(f"  {r['rango']}: {r['socios']} socios · {r['monto']} USD")
