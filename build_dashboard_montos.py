"""
Dashboard HTML interactivo a partir de:
- sep/Reporte_Montos_PowerBI_socios.xlsx

Cada socio se clasifica en rangos de días según la cantidad de cuotas:
  1 cuota       -> de 0 a 30
  2 cuotas      -> de 31 a 60
  3 cuotas      -> de 61 a 90
  4 o 5 cuotas  -> de 91 a 120
  >5 cuotas     -> mas de 121 días

Salidas:
- sep/dashboard_montos_socios.html
"""

from pathlib import Path
import json
import re
from datetime import datetime

import pandas as pd

BASE_DIR = Path(__file__).parent
# Ahora usamos el archivo depurado indicado por el usuario:
# C:\Users\adoni\Downloads\ETL-CTAS\Reporte_act_cuotas_completas.xlsx
IN_FILE = BASE_DIR / "Reporte_act_cuotas_completas.xlsx"
OUT_HTML = BASE_DIR / "sep" / "dashboard_montos_socios.html"
CUOTAS_FILE = BASE_DIR / "BasesDeDatos-CUOTAS.xlsx"


def parse_cuotas(texto: str):
    """'25 CUOTAS 38.50' -> (25, 38.50).
    Implementación robusta: toma simplemente los números que aparezcan en el texto.
    El primero se interpreta como # de cuotas, el segundo como monto de la cuota.
    """
    if not isinstance(texto, str):
        return None, None
    t = texto.strip().upper()
    if not t:
        return None, None
    try:
        # Buscar todos los números en el texto (solo enteros; el primero es # de cuotas, el segundo el monto)
        nums = re.findall("(\\d+)", t)
        if not nums:
            return None, None
        num = int(nums[0])
        monto = float(nums[1]) if len(nums) > 1 else None
        return num, monto
    except Exception:
        return None, None


def rango_por_cuotas(n: float | int | None) -> str:
    if n is None:
        return "Sin rango"
    try:
        n_int = int(n)
    except Exception:
        return "Sin rango"
    if n_int <= 0:
        return "Sin rango"
    if n_int == 1:
        return "de 0 a 30"
    if n_int == 2:
        return "de 31 a 60"
    if n_int == 3:
        return "de 61 a 90"
    if n_int in (4, 5):
        return "de 91 a 120"
    return "mas de 121 días"


def main():
    # El archivo original tiene encabezados en la fila 4 (índice 3) y
    # filas de título antes. Leemos con header=3 y la hoja "Montos por socio".
    df = pd.read_excel(IN_FILE, sheet_name="Montos por socio", header=3)
    df.columns = [str(c).strip() for c in df.columns]

    # Detectar columnas base de forma robusta
    col_socio = next(
        (
            c
            for c in df.columns
            if "código socio" in c.lower()
            or "codigo socio" in c.lower()
            or "c\u00f3digo socio" in c.lower()
        ),
        df.columns[0],
    )
    col_monto = next((c for c in df.columns if "monto total" in c.lower()), df.columns[1])
    col_fecha = next(
        (
            c
            for c in df.columns
            if "última fecha" in c.lower() or "ultima fecha" in c.lower()
        ),
        df.columns[2],
    )
    # La cuarta columna es la de texto de cuotas (sin nombre o Unnamed: 3)
    col_texto = df.columns[3] if len(df.columns) > 3 else None

    # Asegurar tipos
    df[col_socio] = pd.to_numeric(df[col_socio], errors="coerce").astype("Int64")
    df[col_monto] = pd.to_numeric(df[col_monto], errors="coerce")
    if col_texto is not None:
        df[col_texto] = df[col_texto].astype(str).fillna("")
    else:
        df["__tmp_texto__"] = ""
        col_texto = "__tmp_texto__"

    # Traer información de fechas desde BasesDeDatos-CUOTAS (última fecha_creacion por socio)
    # Usamos fecha_creacion porque es la fecha de las cuotas pendientes de los socios
    try:
        cuotas = pd.read_excel(CUOTAS_FILE)
        cuotas.columns = [str(c).strip() for c in cuotas.columns]
        if "socio_id" in cuotas.columns and "fecha_creacion" in cuotas.columns:
            cuotas["socio_id"] = pd.to_numeric(cuotas["socio_id"], errors="coerce").astype("Int64")
            cuotas["fecha_creacion"] = pd.to_datetime(cuotas["fecha_creacion"], errors="coerce")
            ult = (
                cuotas.dropna(subset=["socio_id"])
                .groupby("socio_id")["fecha_creacion"]
                .max()
                .reset_index()
                .rename(columns={"socio_id": col_socio, "fecha_creacion": "Ultima_fecha_cuotas"})
            )
            df = df.merge(ult, on=col_socio, how="left")
            # Si la columna de fecha original está muy vacía, usa la de cuotas
            base_fecha = df["Ultima_fecha_cuotas"]
        else:
            base_fecha = df[col_fecha]
    except Exception:
        base_fecha = df[col_fecha]

    # Recalcular num_cuotas y monto_cuota de forma robusta
    num_list: list[int | None] = []
    monto_cuota_list: list[float | None] = []
    for txt in df[col_texto]:
        n, m = parse_cuotas(txt)
        num_list.append(n)
        monto_cuota_list.append(m)

    df["num_cuotas_calc"] = num_list
    df["monto_cuota_calc"] = monto_cuota_list
    df["monto_calculado_calc"] = (
        pd.Series(num_list, dtype="float").fillna(0) * pd.Series(monto_cuota_list, dtype="float").fillna(0.0)
    )

    # Rango de días según número de cuotas
    df["Rango_dias_por_cuotas"] = [rango_por_cuotas(n) for n in df["num_cuotas_calc"]]

    # Filtrar filas sin socio
    df = df[df[col_socio].notna()].copy()

    # KPIs globales
    total_socios = int(df[col_socio].nunique())
    total_monto = float(df[col_monto].sum())

    # Resumen por rango
    resumen_rows = []
    for rango, sub in df.groupby("Rango_dias_por_cuotas"):
        socios = int(sub[col_socio].nunique())
        monto = float(sub[col_monto].sum())
        cuotas = int(sub["num_cuotas_calc"].fillna(0).sum())
        resumen_rows.append(
            {
                "rango": rango,
                "socios": socios,
                "monto": round(monto, 2),
                "cuotas": cuotas,
            }
        )

    resumen_rows.sort(
        key=lambda r: ["de 0 a 30", "de 31 a 60", "de 61 a 90", "de 91 a 120", "mas de 121 días", "Sin rango"].index(
            r["rango"]
        )
        if r["rango"] in ["de 0 a 30", "de 31 a 60", "de 61 a 90", "de 91 a 120", "mas de 121 días", "Sin rango"]
        else 999
    )

    # Datos detalle para tabla (solo columnas relevantes)
    detalle = df[
        [
            col_socio,
            col_monto,
            base_fecha.name,
            col_texto,
            "num_cuotas_calc",
            "monto_cuota_calc",
            "monto_calculado_calc",
            "Rango_dias_por_cuotas",
        ]
    ].copy()
    # Alias con nombre limpio para usar en el frontend
    detalle["Codigo_socio"] = detalle[col_socio]
    detalle["Monto_total"] = detalle[col_monto]  # Alias para el monto total
    # Convertir fecha a string para que sea serializable a JSON
    fecha_dt = pd.to_datetime(detalle[base_fecha.name], errors="coerce")
    
    # Filtrar fechas futuras irrazonables (más allá del año actual)
    año_actual = datetime.now().year
    año_maximo = año_actual
    
    # Crear serie de años y filtrar los futuros
    año_serie = fecha_dt.dt.year.copy()
    año_serie = año_serie.where(año_serie <= año_maximo, None)
    
    # Para fechas futuras, establecer como NaT
    fecha_dt_filtrada = fecha_dt.where(año_serie.notna() | fecha_dt.isna(), pd.NaT)
    
    detalle["Ultima_fecha_liquidacion"] = fecha_dt_filtrada.dt.strftime("%Y-%m-%d")
    # Extraer año para el segmentador (solo años válidos)
    detalle["Anio"] = año_serie.astype("Int64").astype(str).replace("nan", None).replace("None", None)
    # Extraer año-mes para el segmentador por mes (formato "YYYY-MM")
    mask_valido = año_serie.notna() & (año_serie <= año_maximo)
    detalle["AnioMes"] = fecha_dt_filtrada.dt.strftime("%Y-%m")
    detalle.loc[~mask_valido, "AnioMes"] = None

    # Reemplazar NaN/NaT por None antes de serializar
    detalle = detalle.where(pd.notnull(detalle), None)
    # Quitar la columna interna de fecha cruda, que puede ser Timestamp/NaT
    detalle = detalle.drop(columns=[base_fecha.name])

    detalle_records = []
    for rec in detalle.to_dict(orient="records"):
        clean = {}
        for k, v in rec.items():
            if isinstance(v, pd.Timestamp):
                clean[k] = v.strftime("%Y-%m-%d")
            else:
                clean[k] = v
        detalle_records.append(clean)

    # Calcular estadísticas por año
    # Filtrar fechas futuras irrazonables (más allá del año actual)
    año_actual = datetime.now().year
    año_maximo = año_actual  # Solo mostrar hasta el año actual
    
    df_con_anio = df.copy()
    fecha_dt_anio = pd.to_datetime(df_con_anio[base_fecha.name], errors="coerce")
    df_con_anio["Anio"] = fecha_dt_anio.dt.year
    df_con_anio["AnioMes"] = fecha_dt_anio.dt.strftime("%Y-%m")
    
    # Filtrar filas con fechas futuras irrazonables
    df_con_anio = df_con_anio[
        (df_con_anio["Anio"].isna()) | (df_con_anio["Anio"] <= año_maximo)
    ].copy()
    
    estadisticas_anio = []
    for anio, sub in df_con_anio.groupby("Anio"):
        if pd.notna(anio) and int(anio) <= año_maximo:
            socios_anio = int(sub[col_socio].nunique())
            monto_anio = float(sub[col_monto].sum())
            estadisticas_anio.append({
                "anio": int(anio),
                "socios": socios_anio,
                "monto": round(monto_anio, 2)
            })
    estadisticas_anio.sort(key=lambda x: x["anio"], reverse=True)

    # Lista de años-meses únicos para el segmentador (formato "YYYY-MM", etiqueta "Mes Año")
    MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    anios_meses = []
    for am in df_con_anio["AnioMes"].dropna().unique():
        try:
            y, m = am.split("-")
            label = f"{MESES_ES[int(m) - 1]} {y}"
            anios_meses.append({"value": am, "label": label})
        except Exception:
            continue
    anios_meses.sort(key=lambda x: x["value"], reverse=True)

    # Construir HTML con un poco de JS para interacción
    data_json = json.dumps(detalle_records, ensure_ascii=False)
    resumen_json = json.dumps(resumen_rows, ensure_ascii=False)
    estadisticas_anio_json = json.dumps(estadisticas_anio, ensure_ascii=False)
    anios_meses_json = json.dumps(anios_meses, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard de cuotas hasta septiembre 2025</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* Paleta suave y visual */
    :root {{
      --bg: #f8f9fa;
      --surface: #ffffff;
      --surface-alt: #f1f3f5;
      --text: #2d3436;
      --muted: #636e72;
      --accent: #6c5ce7;
      --accent-soft: #e9ecef;
      --accent-light: #a29bfe;
      --border: #dee2e6;
      --shadow: 0 2px 8px rgba(0,0,0,0.06);
      --green: #00b894;
      --blue: #74b9ff;
      --purple: #a29bfe;
      --orange: #fdcb6e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'DM Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      color: var(--text);
      min-height: 100vh;
      padding: 0.75rem;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
      padding: 0.5rem 0;
    }}
    h1 {{
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      margin: 0;
      color: var(--accent);
    }}
    .subtitle {{
      display: none;
    }}
    .pill {{
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.75rem;
    }}
    .cards-row {{
      display: flex;
      flex-wrap: nowrap;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
      overflow-x: auto;
      scrollbar-width: thin;
      scrollbar-color: var(--border) transparent;
    }}
    .cards {{
      display: flex;
      flex-wrap: nowrap;
      gap: 0.75rem;
      margin-bottom: 0;
      overflow-x: visible;
      flex-shrink: 0;
    }}
    .cards-row .cards {{
      margin-bottom: 0;
    }}
    .cards::-webkit-scrollbar {{
      height: 6px;
    }}
    .cards::-webkit-scrollbar-track {{
      background: var(--surface-alt);
      border-radius: 3px;
    }}
    .cards::-webkit-scrollbar-thumb {{
      background: var(--border);
      border-radius: 3px;
    }}
    .cards .card {{
      flex: 1 1 0;
      min-width: 160px;
    }}
    #montos-por-anio .card {{
      min-width: 140px;
    }}
    #range-cards .card {{
      padding: 0.85rem 1rem;
    }}
    #range-cards .card .value {{
      font-size: 1.3rem;
    }}
    #range-cards .card .hint {{
      font-size: 0.75rem;
      margin-top: 0.1rem;
    }}
    #range-cards .bar-row {{
      margin-top: 0.5rem;
      margin-bottom: 0.5rem;
    }}
    .card {{
      background: var(--surface);
      border-radius: 12px;
      padding: 1rem 1.1rem;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      cursor: default;
      transition: all 0.2s ease;
    }}
    .card.clickable {{ cursor: pointer; }}
    .card.clickable:hover {{
      border-color: var(--accent-light);
      box-shadow: 0 4px 12px rgba(108, 92, 231, 0.15);
      transform: translateY(-2px);
    }}
    .card.active {{
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-soft), 0 4px 16px rgba(108, 92, 231, 0.2);
      background: linear-gradient(135deg, var(--surface) 0%, var(--accent-soft) 100%);
    }}
    .card .label {{ color: var(--muted); font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.25rem; }}
    .card .value {{
      font-size: 1.5rem;
      font-weight: 700;
      text-align: center;
    }}
    .card .hint {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.15rem; }}
    .panel {{
      background: var(--surface);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .panel h2 {{
      font-size: 0.95rem;
      margin-bottom: 0.75rem;
      font-weight: 700;
      text-align: left;
      color: var(--accent);
    }}
    .panel .hint {{
      color: var(--muted);
      font-size: 0.75rem;
      margin-bottom: 0.5rem;
      text-align: left;
    }}
    .block-title {{
      font-size: 1.0rem;
      font-weight: 700;
      margin: 0.75rem 0 0.5rem;
      color: var(--accent);
    }}
    .bar-row {{ margin-bottom: 0.8rem; }}
    .bar-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }}
    .bar-head span:first-child {{ font-size: 0.9rem; }}
    .bar-head span:last-child {{ font-size: 0.9rem; font-weight: 600; }}
    .bar-bg {{
      height: 16px;
      border-radius: 8px;
      background: var(--surface-alt);
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 8px;
      background: linear-gradient(90deg, var(--purple), var(--accent-light));
      transition: width 0.3s ease;
    }}
    .bar-fill.alt {{ background: linear-gradient(90deg, var(--blue), var(--accent)); }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      margin-bottom: 0.75rem;
      flex-wrap: wrap;
      background: var(--surface);
      padding: 0.75rem 1rem;
      border-radius: 10px;
      box-shadow: var(--shadow);
      border: 1px solid var(--border);
    }}
    .search-box {{
      flex: 1;
      min-width: 250px;
    }}
    .search-box input {{
      width: 100%;
      background: var(--surface-alt);
      border-radius: 8px;
      border: 2px solid var(--border);
      color: var(--text);
      padding: 0.65rem 1rem;
      font-size: 0.9rem;
      outline: none;
      transition: all 0.2s ease;
    }}
    .search-box input:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
      background: var(--surface);
    }}
    .search-box input::placeholder {{
      color: var(--muted);
    }}
    .filter-select {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .filter-select label {{
      font-size: 0.75rem;
      color: var(--muted);
      font-weight: 600;
      white-space: nowrap;
    }}
    .filter-select select {{
      background: var(--surface-alt);
      border-radius: 8px;
      border: 2px solid var(--border);
      color: var(--text);
      padding: 0.65rem 1rem;
      font-size: 0.9rem;
      outline: none;
      cursor: pointer;
      transition: all 0.2s ease;
      min-width: 150px;
    }}
    .filter-select select:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
      background: var(--surface);
    }}
    .table-container {{
      max-height: calc(100vh - 550px);
      overflow: auto;
      border-radius: 8px;
      -webkit-overflow-scrolling: touch;
      border: 1px solid var(--border);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
      background: var(--surface);
      border-radius: 8px;
      overflow: hidden;
      min-width: 600px;
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
    }}
    th {{
      text-align: left;
      color: var(--muted);
      font-weight: 600;
      font-size: 0.75rem;
      background: var(--surface-alt);
      position: sticky;
      top: 0;
      z-index: 10;
      padding: 0.4rem 0.5rem;
    }}
    th.num {{
      text-align: right;
    }}
    td {{
      text-align: left;
      padding: 0.4rem 0.5rem;
    }}
    td.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    tr:hover td {{
      background: var(--surface-alt);
    }}
    tr:hover td {{ background: rgba(255,255,255,0.02); }}
    .footer {{
      margin-top: 1.2rem;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    @media (max-width: 1200px) {{
      .cards .card {{
        min-width: 200px;
      }}
    }}
    @media (max-width: 980px) {{
      body {{ padding: 1rem; }}
      h1 {{ font-size: 1.5rem; }}
      .subtitle {{ font-size: 0.85rem; }}
      .cards .card {{
        min-width: 220px;
        padding: 1rem;
      }}
      .card .value {{ font-size: 1.3rem; }}
      .panel {{ padding: 1rem; }}
      .panel h2 {{ font-size: 0.95rem; }}
      table {{ font-size: 0.75rem; }}
      th, td {{ padding: 0.4rem 0.35rem; }}
    }}
    @media (max-width: 768px) {{
      body {{ padding: 0.75rem; }}
      .container {{ max-width: 100%; }}
      h1 {{ font-size: 1.3rem; }}
      .subtitle {{ font-size: 0.8rem; }}
      .cards .card {{
        min-width: 200px;
        padding: 0.9rem;
      }}
      .card .label {{ font-size: 0.7rem; }}
      .card .value {{ font-size: 1.2rem; }}
      .card .hint {{ font-size: 0.7rem; }}
      .panel {{ padding: 0.9rem; }}
      .toolbar {{
        flex-direction: column;
        gap: 0.5rem;
      }}
      .search-box input, .filter-select select {{
        width: 100%;
      }}
      .table-container {{
        max-height: 350px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }}
      table {{
        min-width: 550px;
        font-size: 0.7rem;
      }}
      th, td {{
        padding: 0.35rem 0.25rem;
        font-size: 0.7rem;
      }}
    }}
    @media (max-width: 480px) {{
      body {{ padding: 0.5rem; }}
      h1 {{ font-size: 1.1rem; }}
      .subtitle {{ font-size: 0.75rem; }}
      .cards .card {{
        min-width: 180px;
        padding: 0.8rem;
      }}
      .card .value {{ font-size: 1.1rem; }}
      .bar-row {{ margin-bottom: 0.6rem; }}
      .bar-bg {{ height: 14px; }}
      .table-container {{
        max-height: 300px;
        overflow-x: auto;
      }}
      table {{
        min-width: 500px;
        font-size: 0.65rem;
      }}
      th, td {{
        padding: 0.3rem 0.2rem;
        font-size: 0.65rem;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Dashboard de cuotas hasta septiembre 2025</h1>
      <div class="cards" id="kpi-cards" style="margin:0; gap:0.75rem;">
        <div class="card" style="padding:0.6rem 0.9rem;">
          <div class="label">Monto total</div>
          <div id="kpi-monto-total" class="value" style="font-size:1.2rem;">$ {total_monto:,.2f}</div>
        </div>
      </div>
    </div>

    <div class="toolbar toolbar-top" style="margin-bottom:0.75rem;">
      <div class="search-box">
        <input id="search-input" type="text" placeholder="🔍 Buscar socio por código..." />
      </div>
      <div class="filter-select">
        <label for="year-select">Año:</label>
        <select id="year-select">
          <option value="">Todos los años</option>
        </select>
      </div>
      <div class="filter-select">
        <label for="month-select">Mes:</label>
        <select id="month-select">
          <option value="">Todos los meses</option>
        </select>
      </div>
      <div class="filter-select">
        <label for="filter-select">Rango:</label>
        <select id="filter-select">
          <option value="">Todos los rangos</option>
          <option value="de 0 a 30">de 0 a 30</option>
          <option value="de 31 a 60">de 31 a 60</option>
          <option value="de 61 a 90">de 61 a 90</option>
          <option value="de 91 a 120">de 91 a 120</option>
          <option value="mas de 121 días">mas de 121 días</option>
          <option value="Sin rango">Sin rango</option>
        </select>
      </div>
    </div>

    <h2 class="block-title">Montos por año · Resumen por rango de días (según cuotas)</h2>
    <div class="cards-row">
      <div id="montos-por-anio" class="cards"></div>
      <div id="range-cards" class="cards"></div>
    </div>

    <div class="panel" style="margin-top:0.75rem;">
        <div class="table-container">
          <table id="tabla-socios">
            <thead>
              <tr>
                <th>Código socio</th>
                <th class="num"># cuotas</th>
                <th class="num">Monto cuota</th>
                <th class="num">Monto plan cuotas</th>
                <th>Última fecha</th>
                <th>Rango días</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <p class="footer">
      Generado con <code>build_dashboard_montos.py</code> a partir de <code>Reporte_Montos_PowerBI_socios.xlsx</code>.
    </p>
  </div>

  <script>
    const RESUMEN = {resumen_json};
    const DETALLE = {data_json};
    const ESTADISTICAS_ANIO = {estadisticas_anio_json};
    const ANIOS_MESES = {anios_meses_json};

    let selectedRange = '';
    let selectedYear = '';
    let selectedMonth = '';

    function formatNumber(n) {{
      return n.toLocaleString('es-PE', {{ minimumFractionDigits: 0, maximumFractionDigits: 0 }});
    }}
    function formatMoney(n) {{
      return '$ ' + n.toLocaleString('es-PE', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }}

    /** Obtiene los datos aplicando todos los filtros en orden: año, mes, rango, búsqueda. */
    function getFilteredData() {{
      const filterYear = selectedYear || document.getElementById('year-select').value;
      const filterMonth = selectedMonth || document.getElementById('month-select').value;
      const filterRange = selectedRange || document.getElementById('filter-select').value;
      const search = document.getElementById('search-input').value.trim();

      let rows = DETALLE.slice();

      if (filterYear) {{
        rows = rows.filter(r => {{
          const anio = r.Anio;
          return anio != null && String(anio) === filterYear;
        }});
      }}
      if (filterMonth) {{
        rows = rows.filter(r => {{
          const am = r.AnioMes;
          return am != null && String(am) === filterMonth;
        }});
      }}
      if (filterRange) {{
        rows = rows.filter(r => (r.Rango_dias_por_cuotas || '') === filterRange);
      }}
      if (search) {{
        const s = search.toLowerCase();
        rows = rows.filter(r => String(r.Codigo_socio ?? '').toLowerCase().includes(s));
      }}
      return rows;
    }}

    function updateKpiTotal() {{
      const search = document.getElementById('search-input').value.trim();
      let rows;
      if (search) {{
        // Con socio seleccionado: mostrar el total de ese cliente (todos sus registros)
        const s = search.toLowerCase();
        rows = DETALLE.filter(r => String(r.Codigo_socio ?? '').toLowerCase().includes(s));
      }} else {{
        rows = getFilteredData();
      }}
      const total = rows.reduce((sum, r) => sum + Number(r.Monto_total || 0), 0);
      const el = document.getElementById('kpi-monto-total');
      if (el) el.textContent = formatMoney(total);
    }}

    function renderMontosPorAnio() {{
      const container = document.getElementById('montos-por-anio');
      container.innerHTML = '';
      ESTADISTICAS_ANIO.forEach(stat => {{
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cssText = 'padding:0.75rem 1rem; flex:1 1 auto; min-width:140px; cursor:pointer;';
        if (selectedYear === String(stat.anio)) {{
          card.classList.add('active');
        }}
        card.dataset.anio = stat.anio;
        card.innerHTML = `
          <div class="label" style="font-size:0.7rem;">Año ${{stat.anio}}</div>
          <div class="value" style="font-size:1.1rem; margin-top:0.3rem;">${{formatMoney(stat.monto)}}</div>
          <div class="hint" style="font-size:0.7rem; margin-top:0.3rem;">${{formatNumber(stat.socios)}} socios</div>
        `;
        card.addEventListener('click', () => {{
          selectedYear = selectedYear === String(stat.anio) ? '' : String(stat.anio);
          document.getElementById('year-select').value = selectedYear;
          selectedMonth = '';
          document.getElementById('month-select').value = '';
          populateMonthSelect();
          renderMontosPorAnio();
          renderRangeCards();
          renderTable();
          updateKpiTotal();
        }});
        container.appendChild(card);
      }});
    }}

    function populateYearSelect() {{
      const select = document.getElementById('year-select');
      ESTADISTICAS_ANIO.forEach(stat => {{
        const option = document.createElement('option');
        option.value = String(stat.anio);
        option.textContent = String(stat.anio);
        select.appendChild(option);
      }});
    }}

    function populateMonthSelect() {{
      const select = document.getElementById('month-select');
      const year = selectedYear || document.getElementById('year-select').value;
      const valorActual = selectedMonth || select.value;
      select.innerHTML = '<option value="">Todos los meses</option>';
      ANIOS_MESES.forEach(item => {{
        if (year && item.value.indexOf(year + '-') !== 0) return;
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        select.appendChild(option);
      }});
      select.value = valorActual || '';
    }}

    function renderRangeCards() {{
      const container = document.getElementById('range-cards');
      container.innerHTML = '';

      const datosFiltrados = getFilteredData();

      // Recalcular resumen basado en los mismos filtros (año, mes, rango, búsqueda)
      const resumenFiltrado = {{}};
      datosFiltrados.forEach(r => {{
        const rango = r.Rango_dias_por_cuotas || 'Sin rango';
        if (!resumenFiltrado[rango]) {{
          resumenFiltrado[rango] = {{ socios: new Set(), monto: 0, cuotas: 0 }};
        }}
        resumenFiltrado[rango].socios.add(r.Codigo_socio);
        resumenFiltrado[rango].monto += Number(r.Monto_total || 0);
        resumenFiltrado[rango].cuotas += Number(r.num_cuotas_calc || 0);
      }});
      
      const resumenArray = RESUMEN.map(r => {{
        const filtrado = resumenFiltrado[r.rango] || {{ socios: new Set(), monto: 0, cuotas: 0 }};
        return {{
          rango: r.rango,
          socios: filtrado.socios.size,
          monto: filtrado.monto || 0,
          cuotas: filtrado.cuotas || 0
        }};
      }});
      
      const maxSocios = Math.max(...resumenArray.map(r => r.socios || 0), 1);
      const maxMonto = Math.max(...resumenArray.map(r => r.monto || 0), 1);
      
      resumenArray.forEach(r => {{
        const pctSocios = (r.socios / maxSocios) * 100;
        const pctMonto = (r.monto / maxMonto) * 100;
        const card = document.createElement('div');
        card.className = 'card clickable' + (selectedRange === r.rango ? ' active' : '');
        card.dataset.rango = r.rango;
        card.innerHTML = `
          <div class="label">${{r.rango}}</div>
          <div class="value">${{formatNumber(r.socios)}} socios</div>
          <div class="hint">${{formatMoney(r.monto)}} USD · ${{formatNumber(r.cuotas)}} cuotas</div>
          <div class="bar-row" style="margin-top:0.65rem;">
            <div class="bar-head"><span>Socios</span><span>${{formatNumber(r.socios)}}</span></div>
            <div class="bar-bg"><div class="bar-fill" style="width:${{pctSocios.toFixed(0)}}%;"></div></div>
            <div class="bar-head" style="margin-top:0.3rem;"><span>Monto</span><span>${{formatMoney(r.monto)}}</span></div>
            <div class="bar-bg"><div class="bar-fill alt" style="width:${{pctMonto.toFixed(0)}}%;"></div></div>
          </div>
        `;
        card.addEventListener('click', () => {{
          selectedRange = selectedRange === r.rango ? '' : r.rango;
          document.getElementById('filter-select').value = selectedRange;
          renderRangeCards();
          renderTable();
        }});
        container.appendChild(card);
      }});
    }}

    function renderTable() {{
      const tbody = document.querySelector('#tabla-socios tbody');
      const rows = getFilteredData();

      tbody.innerHTML = '';
      rows.forEach(r => {{
        const tr = document.createElement('tr');
        const codigo = r.Codigo_socio ?? '';
        const ncuotas = r.num_cuotas_calc ?? r.num_cuotas ?? '';
        const mcuota = Number(r.monto_cuota_calc || r.monto_cuota || 0);
        const mplan = Number(r.monto_calculado_calc || r.monto_calculado || 0);
        const fecha = r.Ultima_fecha_liquidacion || '';
        const rango = r.Rango_dias_por_cuotas || 'Sin rango';
        tr.innerHTML = `
          <td>${{codigo}}</td>
          <td class="num">${{ncuotas}}</td>
          <td class="num">${{mcuota ? formatMoney(mcuota) : ''}}</td>
          <td class="num">${{mplan ? formatMoney(mplan) : ''}}</td>
          <td>${{fecha}}</td>
          <td>${{rango}}</td>
        `;
        tbody.appendChild(tr);
      }});
      updateKpiTotal();
    }}

    function refreshAll() {{
      populateMonthSelect();
      renderMontosPorAnio();
      renderRangeCards();
      renderTable();
    }}

    document.getElementById('search-input').addEventListener('input', () => {{
      renderRangeCards();
      renderTable();
    }});
    document.getElementById('filter-select').addEventListener('change', e => {{
      selectedRange = e.target.value;
      refreshAll();
    }});
    document.getElementById('year-select').addEventListener('change', e => {{
      selectedYear = e.target.value;
      selectedMonth = '';
      document.getElementById('month-select').value = '';
      refreshAll();
    }});
    document.getElementById('month-select').addEventListener('change', e => {{
      selectedMonth = e.target.value;
      refreshAll();
    }});

    populateYearSelect();
    populateMonthSelect();
    refreshAll();
  </script>
</body>
</html>
"""

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard montos generado: {OUT_HTML}")


if __name__ == "__main__":
    main()

