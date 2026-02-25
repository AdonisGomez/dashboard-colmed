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

    # Normalizar clasificación/estado
    df["Clasificacion"] = df["Clasificacion"].astype(str)
    df["Estado_socio_odoo_ultimo"] = df["Estado_socio_odoo_ultimo"].astype(str)

    # Fechas a texto
    for col in ["Primer_pago", "Ultimo_pago"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    # KPIs globales (sobre el cruce)
    total_socios = int(df["Codigo_socio"].nunique())
    total_mora = float(df["Monto_mora"].sum())
    total_pagado = float(df["Monto_pagado_total"].sum())
    total_restante = float(df["Monto_mora_restante"].sum())

    # Provisión virtual mensual: suma de la cuota mensual esperada por socio
    # usando el archivo de plan de cuotas (Reporte_Montos_PowerBI_socios.xlsx).
    # Se deriva a partir del texto de cuotas, por ejemplo: "25 CUOTAS 38.50".
    total_provision = 0.0
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
                mc = row.get("monto_cuota")
                try:
                    if mc is not None and not (isinstance(mc, float) and math.isnan(mc)) and float(mc) > 0:
                        montos.append(float(mc))
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

    # Datos para tabla detalle
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

    detalle_records = json.dumps(detalle.to_dict(orient="records"), ensure_ascii=False)
    resumen_records = json.dumps(resumen_clasif.to_dict(orient="records"), ensure_ascii=False)
    pagos_mes_json = json.dumps(pagos_mes_list, ensure_ascii=False)

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
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.75rem;
      margin: 0.75rem 0;
      padding: 0.75rem 1rem;
      background: var(--surface);
      border-radius: 12px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      flex-wrap: wrap;
    }}
    .search-box {{
      flex: 1;
      min-width: 220px;
    }}
    .search-box input {{
      width: 100%;
      padding: 0.6rem 0.9rem;
      border-radius: 8px;
      border: 2px solid var(--border);
      background: var(--surface-alt);
      font-size: 0.9rem;
    }}
    .filter-select {{
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .filter-select label {{
      font-size: 0.75rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .filter-select select {{
      padding: 0.45rem 0.75rem;
      border-radius: 8px;
      border: 2px solid var(--border);
      background: var(--surface-alt);
      font-size: 0.85rem;
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
      <h1>Mora vs Pagos en Odoo</h1>
      <div class="kpi-row">
        <div class="card kpi">
          <div class="label">Socios en cruce</div>
          <div class="value" id="kpi-socios">{total_socios:,}</div>
        </div>
        <div class="card kpi">
          <div class="label">Cartera inicial (mora)</div>
          <div class="value" id="kpi-mora">$ {total_mora:,.2f}</div>
        </div>
        <div class="card kpi">
          <div class="label">Provisión virtual mensual</div>
          <div class="value" id="kpi-prov">$ {total_provision:,.2f}</div>
        </div>
        <div class="card kpi">
          <div class="label">Pagos acumulados (Odoo)</div>
          <div class="value" id="kpi-odoo">$ {total_pagado:,.2f}</div>
        </div>
        <div class="card kpi">
          <div class="label">Nuevo saldo cartera (estimado)</div>
          <div class="value" id="kpi-resto">$ {total_restante:,.2f}</div>
        </div>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <input id="search-input" type="text" placeholder="🔍 Buscar por código o nombre de socio..." />
      </div>
      <div class="filter-select">
        <label for="clasif-select">Clasificación:</label>
        <select id="clasif-select">
          <option value="">Todas</option>
          <option value="Mora_y_paga_en_Odoo">Mora y paga en Odoo</option>
          <option value="Sigue_en_mora">Sigue en mora</option>
          <option value="Al_dia_en_mora_y_paga_en_Odoo">Al día en mora y paga en Odoo</option>
          <option value="Solo_en_Odoo">Solo en Odoo</option>
          <option value="Sin_informacion_clara">Sin información clara</option>
        </select>
      </div>
      <div class="filter-select">
        <label for="estado-odoo-select">Estado Odoo:</label>
        <select id="estado-odoo-select">
          <option value="">Todos</option>
          <option value="active">active</option>
          <option value="confirm">confirm</option>
          <option value="expired">expired</option>
          <option value="mora">mora</option>
        </select>
      </div>
      <div class="filter-select">
        <label for="anio-select">Año último pago:</label>
        <select id="anio-select">
          <option value="">Todos</option>
        </select>
      </div>
      <div class="filter-select">
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
      <div class="filter-select">
        <label for="periodo-select">Periodo (año-mes):</label>
        <select id="periodo-select">
          <option value="">Todos</option>
        </select>
      </div>
    </div>

    <div class="chips" id="chips-resumen"></div>

    <div class="panel">
      <h2>Detalle de socios</h2>
      <div class="table-container">
        <table id="tabla-socios">
          <thead>
            <tr>
              <th>Código socio</th>
              <th>Nombre (membership)</th>
              <th>Nombre Odoo</th>
              <th class="num">Mora</th>
              <th class="num">Pagado Odoo</th>
              <th class="num">Mora restante</th>
              <th class="num"># pagos</th>
              <th>Último pago</th>
              <th>Estado Odoo</th>
              <th>Rango mora</th>
              <th>Clasificación</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const DETALLE = {detalle_records};
    const RESUMEN = {resumen_records};
    const PAGOS_MES = {pagos_mes_json};
    const PROVISION_MENSUAL = {total_provision};
    const TOTAL_SOCIOS_CRUCE = {total_socios};
    const CARTERA_INICIAL = {total_mora};

    let selectedClasif = '';
    let selectedEstado = '';
    let selectedAnio = '';
    let selectedRango = '';
    let selectedPeriodo = '';

    function formatMoney(n) {{
      return '$ ' + Number(n || 0).toLocaleString('es-PE', {{
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }});
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
      document.getElementById('kpi-prov').textContent = formatMoney(PROVISION_MENSUAL);
      // Si NO hay periodo seleccionado, mostramos pagos y saldo globales.
      // Si hay periodo seleccionado, estos valores los actualiza updateKpisPeriodo().
      if (!selectedPeriodo) {{
        document.getElementById('kpi-odoo').textContent = formatMoney(totalPagado);
        document.getElementById('kpi-resto').textContent = formatMoney(totalResto);
      }}
    }}

    function renderChipsResumen() {{
      const cont = document.getElementById('chips-resumen');
      cont.innerHTML = '';
      RESUMEN.forEach(r => {{
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'chip';
        if (r.Clasificacion === 'Mora_y_paga_en_Odoo' || r.Clasificacion === 'Al_dia_en_mora_y_paga_en_Odoo') {{
          chip.classList.add('paga');
        }} else if (r.Clasificacion === 'Sigue_en_mora') {{
          chip.classList.add('mora');
        }} else {{
          chip.classList.add('info');
        }}
        if (selectedClasif === r.Clasificacion) chip.classList.add('active');
        chip.dataset.clasif = r.Clasificacion;
        const descMap = {{
          'Mora_y_paga_en_Odoo': 'Mora y paga en Odoo',
          'Sigue_en_mora': 'Sigue en mora',
          'Al_dia_en_mora_y_paga_en_Odoo': 'Al día en mora y paga en Odoo',
          'Solo_en_Odoo': 'Solo en Odoo',
          'Sin_informacion_clara': 'Sin información clara',
        }};
        const desc = descMap[r.Clasificacion] || r.Clasificacion;
        chip.textContent = `${{desc}} · ${{r.Socios}} socios · ${{formatMoney(r.Monto_mora)}} mora · ${{formatMoney(r.Monto_pagado)}} pagado`;
        chip.addEventListener('click', () => {{
          selectedClasif = selectedClasif === r.Clasificacion ? '' : r.Clasificacion;
          document.getElementById('clasif-select').value = selectedClasif;
          renderChipsResumen();
          renderTable();
        }});
        cont.appendChild(chip);
      }});
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

    function populatePeriodoSelect() {{
      const select = document.getElementById('periodo-select');
      const vistos = new Set();
      const mesesOrdenados = [...PAGOS_MES].sort((a,b) => a.periodo.localeCompare(b.periodo));
      mesesOrdenados.forEach(m => {{
        if (!vistos.has(m.periodo)) {{
          vistos.add(m.periodo);
          const opt = document.createElement('option');
          opt.value = m.periodo;
          opt.textContent = m.periodo;
          select.appendChild(opt);
        }}
      }});
    }}

    function updateKpisPeriodo() {{
      const periodo = selectedPeriodo || document.getElementById('periodo-select').value;
      if (!periodo) {{
        // Sin periodo: dejamos que los KPIs globales de updateKpis dominen.
        selectedPeriodo = '';
        return;
      }}
      // Pagos acumulados hasta el periodo seleccionado (año-mes inclusive)
      const [anioStr, mesStr] = periodo.split('-');
      const anioSel = Number(anioStr);
      const mesSel = Number(mesStr);
      let pagosAcum = 0;
      PAGOS_MES.forEach(p => {{
        const a = Number(p.ANIO || 0);
        const m = Number(p.MES || 0);
        if (a < anioSel || (a === anioSel && m <= mesSel)) {{
          pagosAcum += Number(p.Monto_pagado_mes || 0);
        }}
      }});

      // Provisión mensual esperada (base) no cambia por periodo
      const expectedMes = PROVISION_MENSUAL;
      const nuevoSaldo = Math.max(CARTERA_INICIAL - pagosAcum, 0);

      // Mostramos comparación global hasta el periodo:
      // - Provisión mensual base (meta mensual)
      // - Pagos acumulados hasta el periodo
      // - Nuevo saldo de cartera (mora inicial - pagos acumulados hasta ese mes)
      document.getElementById('kpi-prov').textContent = formatMoney(expectedMes);
      document.getElementById('kpi-odoo').textContent = formatMoney(pagosAcum);
      document.getElementById('kpi-resto').textContent = formatMoney(nuevoSaldo);
    }}

    function renderTable() {{
      const tbody = document.querySelector('#tabla-socios tbody');
      const rows = getFilteredRows();
      tbody.innerHTML = '';
      rows.forEach(r => {{
        const tr = document.createElement('tr');
        const estado = String(r.Estado_socio_odoo_ultimo || '').toLowerCase();
        const clasif = r.Clasificacion || '';
        let badgeClas = '';
        if (clasif === 'Mora_y_paga_en_Odoo') badgeClas = '<span class="badge paga">Mora y paga</span>';
        else if (clasif === 'Sigue_en_mora') badgeClas = '<span class="badge mora">Sigue en mora</span>';
        else if (clasif === 'Solo_en_Odoo') badgeClas = '<span class="badge info">Solo Odoo</span>';
        else if (clasif === 'Al_dia_en_mora_y_paga_en_Odoo') badgeClas = '<span class="badge paga">Al día + paga</span>';
        else if (clasif) badgeClas = `<span class="badge info">${{clasif}}</span>`;

        let badgeEstado = '';
        if (estado === 'active' || estado === 'confirm') badgeEstado = `<span class="badge paga">${{estado}}</span>`;
        else if (estado === 'expired' || estado === 'mora') badgeEstado = `<span class="badge mora">${{estado}}</span>`;
        else if (estado) badgeEstado = `<span class="badge info">${{estado}}</span>`;

        tr.innerHTML = `
          <td>${{r.Codigo_socio ?? ''}}</td>
          <td>${{r.Nombre_socio ?? ''}}</td>
          <td>${{r.CONSUMIDOR ?? ''}}</td>
          <td class="num">${{formatMoney(r.Monto_mora)}}</td>
          <td class="num">${{formatMoney(r.Monto_pagado_total)}}</td>
          <td class="num">${{formatMoney(r.Monto_mora_restante)}}</td>
          <td class="num">${{r.Numero_pagos ?? ''}}</td>
          <td>${{r.Ultimo_pago || ''}}</td>
          <td>${{badgeEstado}}</td>
          <td>${{r.Rango_dias_por_cuotas || ''}}</td>
          <td>${{badgeClas}}</td>
        `;
        tbody.appendChild(tr);
      }});
      updateKpis();
    }}

    document.getElementById('search-input').addEventListener('input', () => {{
      renderTable();
    }});
    document.getElementById('clasif-select').addEventListener('change', e => {{
      selectedClasif = e.target.value;
      renderChipsResumen();
      renderTable();
    }});
    document.getElementById('estado-odoo-select').addEventListener('change', e => {{
      selectedEstado = e.target.value;
      renderTable();
    }});
    document.getElementById('anio-select').addEventListener('change', e => {{
      selectedAnio = e.target.value;
      renderTable();
    }});
    document.getElementById('rango-select').addEventListener('change', e => {{
      selectedRango = e.target.value;
      renderTable();
    }});
    document.getElementById('periodo-select').addEventListener('change', e => {{
      selectedPeriodo = e.target.value;
      if (!selectedPeriodo) {{
        // Si se limpia el periodo, volvemos a KPIs globales.
        renderTable();
      }} else {{
        updateKpisPeriodo();
      }}
    }});

    populateAnioSelect();
    populatePeriodoSelect();
    renderChipsResumen();
    renderTable();
    updateKpisPeriodo();
  </script>
</body>
</html>
"""

    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Dashboard Odoo vs mora generado: {OUT_HTML}")
    print(f"Provisión virtual mensual calculada: {total_provision:,.2f}")


if __name__ == "__main__":
    main()

