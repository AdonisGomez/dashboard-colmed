"""
Dashboard HTML para comparar socios entre:
- Reporte de mora (monto_mora) y
- Pagos en Odoo (Monto_pagado_total, Estado_socio_odoo_ultimo).

Fuente:
- odoo/odoo_vs_mora_socios.xlsx

Salida:
- odoo/dashboard_odoo_vs_mora.html
"""

from pathlib import Path
import json

import pandas as pd


BASE_DIR = Path(__file__).parent
IN_FILE = BASE_DIR / "odoo_vs_mora_socios.xlsx"
OUT_HTML = BASE_DIR / "dashboard_odoo_vs_mora.html"
PLAN_FILE = BASE_DIR.parent / "sep" / "Reporte_Montos_PowerBI_socios.xlsx"
PAGOS_MES_FILE = BASE_DIR / "odoo_pagos_mensuales.xlsx"
PAGOS_DIA_FILE = BASE_DIR / "odoo_pagos_por_dia.xlsx"


def main() -> None:
    df = pd.read_excel(IN_FILE)
    df.columns = [str(c).strip() for c in df.columns]

    # Asegurar tipos
    df["Codigo_socio"] = pd.to_numeric(df["Codigo_socio"], errors="coerce").astype("Int64")
    df["Monto_mora"] = pd.to_numeric(df["Monto_mora"], errors="coerce").fillna(0.0)
    df["Monto_pagado_total"] = pd.to_numeric(df["Monto_pagado_total"], errors="coerce").fillna(0.0)
    if "Monto_mora_restante" in df.columns:
        df["Monto_mora_restante"] = pd.to_numeric(df["Monto_mora_restante"], errors="coerce").fillna(0.0)
    else:
        df["Monto_mora_restante"] = (df["Monto_mora"] - df["Monto_pagado_total"]).clip(lower=0.0)

    # Depuración: normalizar y rellenar NaN para JSON/dashboard (no modifica archivos originales)
    df["Clasificacion"] = df["Clasificacion"].fillna("").astype(str).str.strip()
    df["Estado_socio_odoo_ultimo"] = df["Estado_socio_odoo_ultimo"].fillna("").astype(str).str.strip()
    if "Rango_dias_por_cuotas" in df.columns:
        df["Rango_dias_por_cuotas"] = df["Rango_dias_por_cuotas"].fillna("Sin rango").astype(str).str.strip()

    # Fechas: conservar datetime para primer pago (nuevos socios) y texto para mostrar
    primer_pago_dt = None
    if "Primer_pago" in df.columns:
        primer_pago_dt = pd.to_datetime(df["Primer_pago"], errors="coerce")
        df["Primer_pago_Anio"] = primer_pago_dt.dt.year
        df["Primer_pago_Mes"] = primer_pago_dt.dt.month

    # Fechas a texto (NaT → cadena vacía) para mostrar en la tabla
    for col in ["Primer_pago", "Ultimo_pago"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            df[col] = df[col].fillna("").astype(str)

    # KPIs globales (sobre el cruce)
    total_socios = int(df["Codigo_socio"].nunique())
    total_mora = float(df["Monto_mora"].sum())
    total_pagado = float(df["Monto_pagado_total"].sum())
    # Nuevo saldo de cartera global = cartera inicial histórica - pagos acumulados
    total_nuevo_saldo = max(total_mora - total_pagado, 0.0)

    # Provisión virtual mensual: suma de la cuota mensual esperada por socio
    # usando el archivo de plan de cuotas (Reporte_Montos_PowerBI_socios.xlsx).
    # Se deriva a partir del texto de cuotas, por ejemplo: "25 CUOTAS 38.50".
    total_provision = 0.0
    cuota_por_socio: dict[int, float] = {}
    try:
        plan = pd.read_excel(PLAN_FILE)
        plan.columns = [str(c).strip() for c in plan.columns]
        if "Codigo_socio" in plan.columns:
            plan["Codigo_socio"] = pd.to_numeric(plan["Codigo_socio"], errors="coerce").astype("Int64")

            import re
            import math

            # Usamos únicamente los socios presentes en el cruce
            socios_cruce = set(df["Codigo_socio"].dropna())
            plan_filtrado = plan[plan["Codigo_socio"].isin(socios_cruce)].copy()

            montos: list[float | None] = []
            for _, row in plan_filtrado.iterrows():
                cod_socio = row.get("Codigo_socio")
                mc = row.get("monto_cuota")
                try:
                    if mc is not None and not (isinstance(mc, float) and math.isnan(mc)) and float(mc) > 0:
                        monto_cuota_val = float(mc)
                        montos.append(monto_cuota_val)
                        if pd.notna(cod_socio):
                            cuota_por_socio[int(cod_socio)] = monto_cuota_val
                        continue
                except Exception:
                    pass

                texto = str(row.get("texto_cuotas") or "").upper().strip()
                if not texto:
                    montos.append(None)
                    continue

                # Buscar números (enteros o decimales) en el texto, ej. '25 CUOTAS 38.50'
                nums = re.findall(r"(\d+(?:[.,]\d+)?)", texto)
                monto_cuota = None
                n_cuotas = None
                if nums:
                    try:
                        n_cuotas = int(float(nums[0].replace(",", ".")))
                    except Exception:
                        n_cuotas = None
                    if len(nums) > 1:
                        try:
                            monto_cuota = float(nums[1].replace(",", "."))
                        except Exception:
                            monto_cuota = None

                if (monto_cuota is None or monto_cuota <= 0) and n_cuotas and "Monto_total" in plan.columns:
                    try:
                        mt = float(row.get("Monto_total") or 0.0)
                        if mt > 0 and n_cuotas > 0:
                            monto_cuota = mt / n_cuotas
                    except Exception:
                        pass

                montos.append(monto_cuota)
                if monto_cuota is not None and monto_cuota > 0 and pd.notna(cod_socio):
                    cuota_por_socio[int(cod_socio)] = float(monto_cuota)

            total_provision = float(sum(m for m in montos if m is not None))
    except Exception as e:
        print("Error calculando provisión virtual:", e)
        total_provision = 0.0

    # Pagos mensuales agregados (para selector de periodo)
    pagos_mes_list: list[dict] = []
    try:
        pm = pd.read_excel(PAGOS_MES_FILE)
        pm.columns = [str(c).strip() for c in pm.columns]
        if {"ANIO", "MES", "Monto_pagado_mes"}.issubset(pm.columns):
            pm = pm.dropna(subset=["ANIO", "MES"])
            pm["ANIO"] = pm["ANIO"].astype(int)
            pm["MES"] = pm["MES"].astype(int)
            pm["periodo"] = pm["ANIO"].astype(str) + "-" + pm["MES"].astype(str).str.zfill(2)
            pagos_mes_list = pm[
                ["periodo", "ANIO", "MES", "Monto_pagado_mes", "Numero_pagos_mes", "Socios_unicos_mes"]
            ].to_dict(orient="records")
    except Exception:
        pagos_mes_list = []

    # Información por socio: primer pago y cuota mensual estimada (para nuevos socios)
    # Información por socio (para provisión esperada dinámica por mes/día)
    socios_info_list: list[dict] = []
    try:
        # Mapeo cuota por socio ya calculado en cuota_por_socio
        primer_pago_dt = pd.to_datetime(df.get("Primer_pago"), errors="coerce")
        info_df = df[["Codigo_socio", "Estado_socio_odoo_ultimo"]].copy()
        info_df["Primer_pago_dt"] = primer_pago_dt.dt.strftime("%Y-%m-%d")
        info_df["Cuota_mensual_estimada"] = info_df["Codigo_socio"].map(
            lambda c: float(cuota_por_socio.get(int(c), 0.0)) if pd.notna(c) else 0.0
        )
        info_df["Estado_socio_odoo_ultimo"] = info_df["Estado_socio_odoo_ultimo"].fillna("").astype(str)
        socios_info_list = info_df.to_dict(orient="records")
    except Exception:
        socios_info_list = []

    # Pagos por día (para vista por día específico y acumulado hasta fecha)
    pagos_dia_list: list[dict] = []
    try:
        pdia = pd.read_excel(PAGOS_DIA_FILE)
        pdia.columns = [str(c).strip() for c in pdia.columns]
        if {"fecha", "ANIO", "MES", "DIA", "Monto_pagado_dia"}.issubset(pdia.columns):
            pdia = pdia.dropna(subset=["fecha"])
            pdia["fecha_str"] = pd.to_datetime(pdia["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")
            pdia["ANIO"] = pdia["ANIO"].astype(int)
            pdia["MES"] = pdia["MES"].astype(int)
            pdia["DIA"] = pdia["DIA"].astype(int)
            pagos_dia_list = pdia[
                ["fecha_str", "ANIO", "MES", "DIA", "SEMANA", "Monto_pagado_dia", "Numero_pagos_dia", "Socios_unicos_dia"]
            ].to_dict(orient="records")
            for r in pagos_dia_list:
                if "SEMANA" in r and (pd.isna(r["SEMANA"]) or r["SEMANA"] is None):
                    r["SEMANA"] = ""
                r["SEMANA"] = str(r.get("SEMANA") or "")
    except Exception:
        pagos_dia_list = []

    # Resumen por clasificación
    resumen_clasif = (
        df.groupby("Clasificacion", dropna=False)
        .agg(
            Socios=("Codigo_socio", "nunique"),
            Monto_mora=("Monto_mora", "sum"),
            Monto_pagado=("Monto_pagado_total", "sum"),
        )
        .reset_index()
    )

    # Orden más lógico
    orden_pref = {
        "Mora_y_paga_en_Odoo": 1,
        "Sigue_en_mora": 2,
        "Al_dia_en_mora_y_paga_en_Odoo": 3,
        "Solo_en_Odoo": 4,
        "Sin_informacion_clara": 9,
    }
    resumen_clasif["__orden"] = resumen_clasif["Clasificacion"].map(orden_pref).fillna(9)
    resumen_clasif = resumen_clasif.sort_values("__orden").drop(columns="__orden")

    # Datos para tabla detalle (rellenar NaN para evitar "nan" en JSON)
    detalle = df[
        [
            "Codigo_socio",
            "Nombre_socio",
            "CONSUMIDOR",
            "Monto_mora",
            "Monto_pagado_total",
            "Monto_mora_restante",
            "Numero_pagos",
            "Ultimo_pago",
            "Estado_socio_odoo_ultimo",
            "Clasificacion",
            "Anio_ultimo_pago",
            "Rango_dias_por_cuotas",
        ]
    ].copy()
    detalle["Nombre_socio"] = detalle["Nombre_socio"].fillna("").astype(str)
    detalle["CONSUMIDOR"] = detalle["CONSUMIDOR"].fillna("").astype(str)
    detalle["Numero_pagos"] = pd.to_numeric(detalle["Numero_pagos"], errors="coerce").fillna(0).astype(int)

    detalle_records = json.dumps(detalle.to_dict(orient="records"), ensure_ascii=False, default=str)
    resumen_records = json.dumps(resumen_clasif.to_dict(orient="records"), ensure_ascii=False)
    pagos_mes_json = json.dumps(pagos_mes_list, ensure_ascii=False)
    pagos_dia_json = json.dumps(pagos_dia_list, ensure_ascii=False)
    socios_info_json = json.dumps(socios_info_list, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Dashboard – Mora vs Pagos Odoo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
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
      --orange: #fdcb6e;
      --red: #ff7675;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'DM Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
      padding: 0.75rem;
      color: var(--text);
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }}
    h1 {{
      font-size: 1.4rem;
      color: var(--accent);
      font-weight: 700;
    }}
    .kpi-row {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .card {{
      background: var(--surface);
      border-radius: 12px;
      padding: 0.9rem 1.1rem;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .card.kpi {{
      flex: 1 1 0;
      min-width: 180px;
    }}
    .label {{
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }}
    .value {{
      font-size: 1.3rem;
      font-weight: 700;
    }}
    .kpi-hint {{
      font-size: 0.65rem;
      text-transform: none;
      letter-spacing: 0;
      margin-top: 0.15rem;
      opacity: 0.85;
    }}
    .toolbar {{
      display: flex;
      justify-content: flex-start;
      align-items: center;
      gap: 0.6rem;
      margin: 0.75rem 0;
      padding: 0.75rem 1rem;
      background: var(--surface);
      border-radius: 12px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      flex-wrap: wrap;
    }}
    .search-box {{
      flex: 0 1 420px;
      min-width: 280px;
    }}
    .search-box input {{
      width: 100%;
      padding: 0.55rem 0.85rem;
      border-radius: 999px;
      border: 2px solid var(--border);
      background: #fff;
      color: var(--text);
      font-size: 0.9rem;
    }}
    .search-box input:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(108,92,231,0.15);
    }}
    .filter-select {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .filter-select label {{
      font-size: 0.72rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .filter-select select {{
      padding: 0.5rem 0.8rem;
      border-radius: 999px;
      border: 2px solid var(--border);
      background: #fff;
      color: var(--text);
      font-size: 0.85rem;
      min-width: 84px;
    }}
    #vista-anio {{ min-width: 92px; }}
    #vista-mes {{ min-width: 72px; }}
    #vista-dia {{ min-width: 72px; }}
    .filter-select select option {{
      color: var(--text);
    }}
    .filter-select select:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(108,92,231,0.12);
    }}
    .chips {{
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
      margin-bottom: 0.75rem;
    }}
    .chip {{
      padding: 0.3rem 0.6rem;
      border-radius: 999px;
      font-size: 0.75rem;
      border: 1px solid var(--border);
      background: var(--surface);
      cursor: pointer;
    }}
    .chip.active {{
      border-color: var(--accent);
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
    }}
    .chips .chip.mora {{ border-color: var(--red); color: var(--red); }}
    .chips .chip.paga {{ border-color: var(--green); color: var(--green); }}
    .panel {{
      background: var(--surface);
      border-radius: 12px;
      padding: 0.9rem 1.1rem;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .panel h2 {{
      font-size: 0.95rem;
      margin-bottom: 0.4rem;
      color: var(--accent);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    th, td {{
      padding: 0.4rem 0.45rem;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: var(--surface-alt);
      text-align: left;
      font-size: 0.75rem;
      color: var(--muted);
      position: sticky;
      top: 0;
      z-index: 1;
    }}
    td.num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
    }}
    .table-container {{
      max-height: calc(100vh - 380px);
      overflow: auto;
      border-radius: 10px;
      border: 1px solid var(--border);
      margin-top: 0.5rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.18rem 0.45rem;
      border-radius: 999px;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .badge.mora {{
      background: #ffecec;
      color: var(--red);
    }}
    .badge.paga {{
      background: #e6fff4;
      color: var(--green);
    }}
    .badge.info {{
      background: var(--surface-alt);
      color: var(--muted);
    }}
    .hidden-filter {{
      display: none !important;
    }}
    .link-bar {{
      display: flex;
      justify-content: flex-end;
      margin: 0.4rem 0 0.2rem 0;
    }}
    .link-button {{
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.3rem 0.7rem;
      border-radius: 999px;
      border: 1px solid var(--accent);
      background: #f3f0ff;
      color: var(--accent);
      font-size: 0.75rem;
      text-decoration: none;
      cursor: pointer;
    }}
    .link-button:hover {{
      background: #e5dbff;
    }}
    @media (max-width: 768px) {{
      body {{ padding: 0.5rem; }}
      h1 {{ font-size: 1.2rem; }}
      .toolbar {{
        flex-direction: column;
        align-items: stretch;
      }}
      .filter-select {{
        width: 100%;
        justify-content: space-between;
      }}
      .filter-select select {{
        flex: 1;
      }}
      .table-container {{
        max-height: 320px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>DASHBOARD COLMED</h1>
      <div class="kpi-row">
        <div class="card kpi">
          <div class="label">Socios totales</div>
          <div class="value" id="kpi-socios">{total_socios:,}</div>
        </div>
        <div class="card kpi">
          <div class="label">Cartera inicial hasta dic 2026</div>
          <div class="value" id="kpi-mora">$ {total_mora:,.2f}</div>
        </div>
        <div class="card kpi">
          <div class="label">Provisión esperada</div>
          <div class="value" id="kpi-prov">$ {total_provision:,.2f}</div>
        </div>
        <div class="card kpi">
          <div class="label">Provisión real (pagos a la fecha)</div>
          <div class="value" id="kpi-odoo">$ {total_pagado:,.2f}</div>
          <div class="label kpi-hint" id="kpi-odoo-hint">según periodo elegido abajo</div>
        </div>
        <div class="card kpi">
          <div class="label">Nuevo saldo de cartera</div>
          <div class="value" id="kpi-resto">$ {total_nuevo_saldo:,.2f}</div>
          <div class="label kpi-hint" id="kpi-resto-hint">Cartera inicial − Provisión real</div>
        </div>
      </div>
    </div>

    <div class="link-bar">
      <a class="link-button" href="../sep/dashboard_montos_socios.html" target="_blank" rel="noopener">
        Ver dashboard de montos de socios
      </a>
    </div>

    <div class="toolbar">
      <div class="filter-select hidden-filter">
        <label for="clasif-select">Clasificación:</label>
        <select id="clasif-select">
          <option value="">Todas</option>
          <option value="Mora_y_paga_en_Odoo">Mora y paga en Odoo</option>
          <option value="Sigue_en_mora">Sigue en mora</option>
        </select>
      </div>
      <div class="filter-select hidden-filter">
        <label for="estado-odoo-select">Estado Odoo:</label>
        <select id="estado-odoo-select">
          <option value="">Todos</option>
        </select>
      </div>
      <div class="filter-select hidden-filter">
        <label for="anio-select">Año último pago:</label>
        <select id="anio-select">
          <option value="">Todos</option>
        </select>
      </div>
      <div class="filter-select hidden-filter">
        <label for="rango-select">Rango mora:</label>
        <select id="rango-select">
          <option value="">Todos</option>
          <option value="de 0 a 30">de 0 a 30</option>
          <option value="de 31 a 60">de 31 a 60</option>
          <option value="de 61 a 90">de 61 a 90</option>
          <option value="de 91 a 120">de 91 a 120</option>
          <option value="mas de 121 días">mas de 121 días</option>
          <option value="Sin rango">Sin rango</option>
        </select>
      </div>
      <!-- Vista/Periodo removidos: solo filtros de Año/Mes/Día -->
      <div class="filter-select" id="wrap-vista-dia">
        <label for="vista-anio">Año:</label>
        <select id="vista-anio"><option value="">—</option></select>
      </div>
      <div class="filter-select" id="wrap-vista-mes">
        <label for="vista-mes">Mes:</label>
        <select id="vista-mes"><option value="">—</option></select>
      </div>
      <div class="filter-select" id="wrap-vista-dia-num">
        <label for="vista-dia">Día:</label>
        <select id="vista-dia"><option value="">—</option></select>
      </div>
      <div class="filter-select hidden-filter" id="wrap-vista-semana">
        <label for="vista-semana">Semana:</label>
        <select id="vista-semana"><option value="">—</option></select>
      </div>
      <div class="search-box">
        <input id="search-input" type="text" placeholder="Buscar socio (código o nombre)..." />
      </div>
    </div>

    <!-- chips ocultos (no se muestran en este dashboard) -->
  </div>

  <script>
    const DETALLE = {detalle_records};
    const PAGOS_MES = {pagos_mes_json};
    const PAGOS_DIA = {pagos_dia_json};
    const SOCIOS_INFO = {socios_info_json};
    const PROVISION_MENSUAL = {total_provision};
    const TOTAL_SOCIOS_CRUCE = {total_socios};
    const CARTERA_INICIAL = {total_mora};

    let selectedClasif = '';
    let selectedEstado = '';
    let selectedAnio = '';
    let selectedRango = '';
    let selectedPeriodo = '';
    let selectedVista = 'acumulado';
    let selectedVistaAnio = '';
    let selectedVistaMes = '';
    let selectedVistaDia = '';
    let selectedVistaSemana = '';

    function formatMoney(n) {{
      return '$ ' + Number(n || 0).toLocaleString('es-PE', {{
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }});
    }}

    function updateNuevosSocios(periodo) {{ /* KPI desactivado por ahora */ }}

    function endOfMonthDateStr(anio, mes) {{
      const d = new Date(Number(anio), Number(mes), 0);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2,'0');
      const day = String(d.getDate()).padStart(2,'0');
      return `${{y}}-${{m}}-${{day}}`;
    }}

    function calcProvisionEsperadaMensual(fechaStr) {{
      // Provisión esperada del mes: suma de cuotas mensuales de socios "vigentes" a esa fecha (por primer pago).
      let total = 0;
      SOCIOS_INFO.forEach(s => {{
        const cuota = Number(s.Cuota_mensual_estimada || 0);
        if (!cuota) return;
        const fp = String(s.Primer_pago_dt || '').slice(0,10);
        if (!fp) return;
        if (fp <= fechaStr) total += cuota;
      }});
      return total;
    }}

    function getFilteredRows() {{
      const search = document.getElementById('search-input').value.trim().toLowerCase();
      const filterClasif = selectedClasif || document.getElementById('clasif-select').value;
      const filterEstado = selectedEstado || document.getElementById('estado-odoo-select').value;
      const filterAnio = selectedAnio || document.getElementById('anio-select').value;
      const filterRango = selectedRango || document.getElementById('rango-select').value;

      return DETALLE.filter(r => {{
        if (filterClasif && (r.Clasificacion || '') !== filterClasif) return false;
        if (filterEstado && String(r.Estado_socio_odoo_ultimo || '').toLowerCase() !== filterEstado.toLowerCase()) return false;
        if (filterAnio) {{
          const anio = r.Anio_ultimo_pago;
          if (anio == null || String(anio) !== filterAnio) return false;
        }}
        if (filterRango) {{
          const rango = String(r.Rango_dias_por_cuotas || '');
          if (rango !== filterRango) return false;
        }}
        if (search) {{
          const codigo = String(r.Codigo_socio ?? '').toLowerCase();
          const nombre1 = String(r.Nombre_socio ?? '').toLowerCase();
          const nombre2 = String(r.CONSUMIDOR ?? '').toLowerCase();
          if (!codigo.includes(search) && !nombre1.includes(search) && !nombre2.includes(search)) return false;
        }}
        return true;
      }});
    }}

    function updateKpis() {{
      const rows = getFilteredRows();
      const totalSocios = new Set(rows.map(r => r.Codigo_socio)).size;
      const totalMora = rows.reduce((s, r) => s + Number(r.Monto_mora || 0), 0);
      const totalPagado = rows.reduce((s, r) => s + Number(r.Monto_pagado_total || 0), 0);
      // Mora restante global = mora total - pagado total (sin recortar por socio)
      const totalResto = Math.max(totalMora - totalPagado, 0);
      document.getElementById('kpi-socios').textContent = totalSocios.toLocaleString('es-PE');
      document.getElementById('kpi-mora').textContent = formatMoney(totalMora);
      // Provisión esperada dinámica: depende de socios vigentes en la fecha seleccionada
      const anioSel = document.getElementById('vista-anio')?.value || '';
      const mesSel = document.getElementById('vista-mes')?.value || '';
      const diaSel = document.getElementById('vista-dia')?.value || '';
      let prov = PROVISION_MENSUAL;
      if (anioSel && mesSel) {{
        const fechaCorte = diaSel
          ? `${{anioSel}}-${{mesSel.padStart(2,'0')}}-${{diaSel.padStart(2,'0')}}`
          : endOfMonthDateStr(anioSel, mesSel);
        prov = calcProvisionEsperadaMensual(fechaCorte);
      }}
      document.getElementById('kpi-prov').textContent = formatMoney(prov);
      // Sin periodo (o vista que no usa periodo): totales de los socios filtrados
      if (!selectedPeriodo || selectedPeriodo === '__todo__') {{
        document.querySelector('#kpi-odoo').closest('.card').querySelector('.label').textContent = 'Pagos acumulados (total histórico)';
        document.querySelector('#kpi-resto').closest('.card').querySelector('.label').textContent = 'Nuevo saldo (cartera − total cobrado)';
        const hintOdoo = document.getElementById('kpi-odoo-hint');
        const hintResto = document.getElementById('kpi-resto-hint');
        if (hintOdoo) hintOdoo.textContent = 'todos los meses';
        if (hintResto) hintResto.textContent = 'Cartera inicial − Pagos acumulados';
        document.getElementById('kpi-odoo').textContent = formatMoney(totalPagado);
        document.getElementById('kpi-resto').textContent = formatMoney(totalResto);
      }}
    }}

    function endOfMonthDateStr(anio, mes) {{
      const d = new Date(Number(anio), Number(mes), 0);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2,'0');
      const day = String(d.getDate()).padStart(2,'0');
      return `${{y}}-${{m}}-${{day}}`;
    }}

    function calcProvisionEsperadaMensual(fechaStr) {{
      // Suma de cuota mensual estimada de socios con Primer_pago_dt <= fechaStr
      let total = 0;
      SOCIOS_INFO.forEach(s => {{
        const cuota = Number(s.Cuota_mensual_estimada || 0);
        if (!cuota) return;
        const fp = String(s.Primer_pago_dt || '').slice(0,10);
        if (!fp) return;
        if (fp <= fechaStr) total += cuota;
      }});
      return total;
    }}

    function populateAnioSelect() {{
      const select = document.getElementById('anio-select');
      const anios = Array.from(new Set(DETALLE.map(r => r.Anio_ultimo_pago).filter(a => a != null))).sort();
      anios.forEach(a => {{
        const opt = document.createElement('option');
        opt.value = String(a);
        opt.textContent = String(a);
        select.appendChild(opt);
      }});
    }}

    function populateEstadoOdooSelect() {{
      const select = document.getElementById('estado-odoo-select');
      const clasif = selectedClasif || document.getElementById('clasif-select').value || '';
      const estadosSet = new Set();
      DETALLE.forEach(r => {{
        if (clasif && (r.Clasificacion || '') !== clasif) return;
        const e = String(r.Estado_socio_odoo_ultimo || '').toLowerCase();
        if (!e) return;
        estadosSet.add(e);
      }});
      const prev = select.value;
      select.innerHTML = '';
      const optAll = document.createElement('option');
      optAll.value = '';
      optAll.textContent = 'Todos';
      select.appendChild(optAll);
      const estados = Array.from(estadosSet).sort();
      estados.forEach(e => {{
        const opt = document.createElement('option');
        opt.value = e;
        opt.textContent = e;
        select.appendChild(opt);
      }});
      if (prev && estados.includes(prev)) {{
        select.value = prev;
        selectedEstado = prev;
      }} else {{
        select.value = '';
        selectedEstado = '';
      }}
    }}

    // populatePeriodoSelect removido (no usamos periodo-select)

    function toggleFiltrosVista() {{
      const wrapPeriodo = document.getElementById('wrap-periodo');
      const wrapDia = document.getElementById('wrap-vista-dia');
      const wrapMes = document.getElementById('wrap-vista-mes');
      const wrapDiaNum = document.getElementById('wrap-vista-dia-num');
      const wrapSemana = document.getElementById('wrap-vista-semana');
      // Solo mostramos filtros de Año, Mes y Día.
      wrapPeriodo.style.display = 'none';
      wrapDia.style.display = 'flex';
      wrapMes.style.display = 'flex';
      wrapDiaNum.style.display = 'flex';
      wrapSemana.style.display = 'none';
    }}

    function populateVistaDiaSelects() {{
      const anios = [...new Set(PAGOS_DIA.map(p => p.ANIO))].filter(a => a != null).sort((a,b)=>a-b);
      const selAnio = document.getElementById('vista-anio');
      const selMes = document.getElementById('vista-mes');
      const selDia = document.getElementById('vista-dia');
      const selSemana = document.getElementById('vista-semana');
      const savAnio = selAnio.value;
      const savMes = selMes.value;
      const savDia = selDia.value;

      selAnio.innerHTML = '<option value="">—</option>';
      anios.forEach(a => {{
        const opt = document.createElement('option');
        opt.value = String(a);
        opt.textContent = String(a);
        selAnio.appendChild(opt);
      }});
      if (savAnio) selAnio.value = savAnio;
      if (!selAnio.value && anios.length) selAnio.value = String(anios[anios.length - 1]);

      const anioSel = selAnio.value ? Number(selAnio.value) : null;
      const meses = anioSel == null ? [] : [...new Set(PAGOS_DIA.filter(p => Number(p.ANIO) === anioSel).map(p => p.MES))].filter(m => m != null).sort((a,b)=>a-b);
      selMes.innerHTML = '<option value="">—</option>';
      meses.forEach(m => {{
        const opt = document.createElement('option');
        opt.value = String(m);
        opt.textContent = String(m).padStart(2,'0');
        selMes.appendChild(opt);
      }});
      if (savMes) selMes.value = savMes;
      if (!selMes.value && meses.length) selMes.value = String(meses[meses.length - 1]);

      const mesSel = selMes.value ? Number(selMes.value) : null;
      const semanaSel = selSemana.value || '';
      let diasFiltro = (anioSel == null || mesSel == null) ? [] : PAGOS_DIA.filter(p => Number(p.ANIO) === anioSel && Number(p.MES) === mesSel);
      if (semanaSel) diasFiltro = diasFiltro.filter(p => (p.SEMANA || '').toString() === semanaSel);
      const dias = [...new Set(diasFiltro.map(p => p.DIA))].filter(d => d != null).sort((a,b)=>a-b);
      selDia.innerHTML = '<option value="">—</option>';
      dias.forEach(d => {{
        const opt = document.createElement('option');
        opt.value = String(d);
        opt.textContent = String(d).padStart(2,'0');
        selDia.appendChild(opt);
      }});
      if (savDia) selDia.value = savDia;
      // Por defecto dejamos el día vacío para que el KPI sea mensual (si el usuario quiere día, lo elige).
      if (savDia === '') selDia.value = '';

      let semanas = [...new Set(PAGOS_DIA.map(p => (p.SEMANA || '').toString()).filter(s => s))];
      if (anioSel != null) {{
        const pref = String(anioSel) + '-W';
        semanas = semanas.filter(s => s.startsWith(pref));
      }}
      semanas.sort();
      selSemana.innerHTML = '<option value="">—</option>';
      semanas.forEach(s => {{
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        selSemana.appendChild(opt);
      }});
    }}

    function updateKpisPorVista() {{
      const vistaDia = document.getElementById('vista-dia').value;
      const vista = vistaDia ? 'dia' : 'acumulado';
      const rowsFilt = getFilteredRows();
      const totalMoraFilt = rowsFilt.reduce((s, r) => s + Number(r.Monto_mora || 0), 0);
      const ratioMora = CARTERA_INICIAL > 0 ? (totalMoraFilt / CARTERA_INICIAL) : 1;
      if (vista === 'dia') {{
        const anio = document.getElementById('vista-anio').value;
        const mes = document.getElementById('vista-mes').value;
        const dia = document.getElementById('vista-dia').value;
        if (!anio || !mes || !dia) {{
          updateKpis();
          return;
        }}
        const fechaStr = `${{anio}}-${{mes.padStart(2,'0')}}-${{dia.padStart(2,'0')}}`;
        const provMes = calcProvisionEsperadaMensual(fechaStr) * ratioMora;
        const provDia = provMes / 30;
        const filaDia = PAGOS_DIA.find(p => p.fecha_str === fechaStr);
        const pagosDelDiaGlobal = filaDia ? Number(filaDia.Monto_pagado_dia || 0) : 0;
        const pagosDelDia = pagosDelDiaGlobal * ratioMora;
        let acumulado = 0;
        PAGOS_DIA.forEach(p => {{
          if ((p.fecha_str || '') <= fechaStr) acumulado += Number(p.Monto_pagado_dia || 0);
        }});
        const acumuladoEscalado = acumulado * ratioMora;
        const nuevoSaldo = Math.max(totalMoraFilt - acumuladoEscalado, 0);
        document.querySelector('#kpi-prov').closest('.card').querySelector('.label').textContent = 'Provisión esperada (día)';
        document.querySelector('#kpi-odoo').closest('.card').querySelector('.label').textContent = 'Provisión real (pagos del día)';
        document.getElementById('kpi-prov').textContent = formatMoney(provDia);
        document.getElementById('kpi-odoo').textContent = formatMoney(pagosDelDia);
        document.getElementById('kpi-resto').textContent = formatMoney(nuevoSaldo);
        document.querySelector('#kpi-resto').closest('.card').querySelector('.label').textContent = 'Nuevo saldo de cartera (al día)';
        return;
      }}

      // Vista mensual (año+mes): provisión esperada del mes y provisión real acumulada a la fecha.
      const anio = document.getElementById('vista-anio').value;
      const mes = document.getElementById('vista-mes').value;
      if (!anio || !mes) {{
        updateKpis();
        return;
      }}
      const fechaCorte = endOfMonthDateStr(anio, mes);
      const provMes = calcProvisionEsperadaMensual(fechaCorte) * ratioMora;

      // Provisión real acumulada "a la fecha" (hasta el mes seleccionado)
      let pagosAcum = 0;
      PAGOS_MES.forEach(p => {{
        const a = Number(p.ANIO || 0);
        const m = Number(p.MES || 0);
        if (a < Number(anio) || (a === Number(anio) && m <= Number(mes))) pagosAcum += Number(p.Monto_pagado_mes || 0);
      }});
      const pagosAcumEsc = pagosAcum * ratioMora;

      // Mora acumulada por falta de pago: sum(max(PV_mes - PR_mes, 0)) hasta el corte
      let moraNuevaAcum = 0;
      const periodoCorte = `${{anio}}-${{String(mes).padStart(2,'0')}}`;
      const mesesOrdenados = [...PAGOS_MES].sort((a,b) => a.periodo.localeCompare(b.periodo));
      mesesOrdenados.forEach(p => {{
        const per = String(p.periodo || '');
        if (!per || per > periodoCorte) return;
        const [aa, mm] = per.split('-');
        const fechaMes = endOfMonthDateStr(aa, mm);
        const pv = calcProvisionEsperadaMensual(fechaMes) * ratioMora;
        const pr = Number(p.Monto_pagado_mes || 0) * ratioMora;
        moraNuevaAcum += Math.max(pv - pr, 0);
      }});

      const carteraProyectada = Math.max(totalMoraFilt - pagosAcumEsc + moraNuevaAcum, 0);
      document.querySelector('#kpi-prov').closest('.card').querySelector('.label').textContent = 'Provisión esperada (mes)';
      document.querySelector('#kpi-odoo').closest('.card').querySelector('.label').textContent = 'Provisión real (pagos a la fecha)';
      document.querySelector('#kpi-resto').closest('.card').querySelector('.label').textContent = 'Nuevo saldo de cartera (al corte)';
      const hintOdoo = document.getElementById('kpi-odoo-hint');
      const hintResto = document.getElementById('kpi-resto-hint');
      if (hintOdoo) hintOdoo.textContent = 'hasta el mes seleccionado';
      if (hintResto) hintResto.textContent = 'Cartera inicial − Pagos + Mora no pagada';
      document.getElementById('kpi-prov').textContent = formatMoney(provMes);
      document.getElementById('kpi-odoo').textContent = formatMoney(pagosAcumEsc);
      document.getElementById('kpi-resto').textContent = formatMoney(carteraProyectada);
    }}

    function updateKpisPeriodo() {{
      updateKpisPorVista();
    }}

    function renderTable() {{
      // Tabla eliminada en este dashboard; solo actualizamos KPIs.
      updateKpis();
      updateKpisPorVista();
    }}

    const elSearch = document.getElementById('search-input');
    if (elSearch) elSearch.addEventListener('input', () => {{ renderTable(); }});

    const elClasif = document.getElementById('clasif-select');
    if (elClasif) elClasif.addEventListener('change', e => {{
      selectedClasif = e.target.value;
      populateEstadoOdooSelect();
      renderTable();
    }});
    const elEstado = document.getElementById('estado-odoo-select');
    if (elEstado) elEstado.addEventListener('change', e => {{ selectedEstado = e.target.value; renderTable(); }});
    const elAnioUlt = document.getElementById('anio-select');
    if (elAnioUlt) elAnioUlt.addEventListener('change', e => {{ selectedAnio = e.target.value; renderTable(); }});
    const elRango = document.getElementById('rango-select');
    if (elRango) elRango.addEventListener('change', e => {{ selectedRango = e.target.value; renderTable(); }});
    // periodo-select ya no se usa

    // vista-select ya no se usa

    const elVA = document.getElementById('vista-anio');
    if (elVA) elVA.addEventListener('change', () => {{
      selectedVistaAnio = elVA.value;
      populateVistaDiaSelects();
      updateKpisPorVista();
    }});
    const elVM = document.getElementById('vista-mes');
    if (elVM) elVM.addEventListener('change', () => {{
      selectedVistaMes = elVM.value;
      populateVistaDiaSelects();
      updateKpisPorVista();
    }});
    const elVD = document.getElementById('vista-dia');
    if (elVD) elVD.addEventListener('change', () => {{
      selectedVistaDia = elVD.value;
      updateKpisPorVista();
    }});
    const elVS = document.getElementById('vista-semana');
    if (elVS) elVS.addEventListener('change', () => {{
      selectedVistaSemana = elVS.value;
      updateKpisPorVista();
    }});

    // Inicialización robusta: primero los filtros de fecha (clave del dashboard)
    toggleFiltrosVista();
    if (PAGOS_DIA && PAGOS_DIA.length) populateVistaDiaSelects();
    // Luego (opcionales) los filtros ocultos
    try {{ populateAnioSelect(); }} catch (e) {{}}
    try {{ populateEstadoOdooSelect(); }} catch (e) {{}}
    renderTable();
  </script>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard Odoo vs mora generado: {OUT_HTML}")
    print(f"Provisión virtual mensual calculada: {total_provision:,.2f}")


if __name__ == "__main__":
    main()

