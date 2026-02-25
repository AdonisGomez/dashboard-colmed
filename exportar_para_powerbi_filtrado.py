"""
Genera un Excel listo para Power BI usando SOLO los socios del reporte filtrado:
- `sep/Reporte_Montos_PEN_lt24_sin_MI.xlsx` (socios con <24 cuotas PEN y sin MI)
- `RECUPERACION_DE_MORA.csv` (rangos de días de mora)

Salida:
- `sep/Dashboard_Cuotas_PowerBI_filtrado.xlsx`
  - Hoja `Resumen_por_rango`: Rango_dias, Cantidad_socios, Monto_USD, Orden
  - Hoja `Detalle_mora_filtrado`: detalle de cuotas solo de esos socios
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent

CSV_MORA = BASE_DIR / "RECUPERACION_DE_MORA.csv"
REPORTE_FILTRADO = BASE_DIR / "sep" / "Reporte_Montos_PEN_lt24_sin_MI.xlsx"
OUT_EXCEL = BASE_DIR / "sep" / "Dashboard_Cuotas_PowerBI_filtrado.xlsx"


def get_col_mapping(df):
    """Encuentra columnas de rango por orden: 0-30, 31-60, 61-90, 91-120, 121+."""
    cols = list(df.columns)
    out = []
    for k in ["0 a 30", "31 a 60", "61 a 90", "91 a 120", "121"]:
        for c in cols:
            if k in str(c) and c not in out:
                out.append(c)
                break
    return out


def main():
    # 1) Socios válidos desde el reporte filtrado
    rep = pd.read_excel(REPORTE_FILTRADO)
    rep.columns = [str(c).strip() for c in rep.columns]
    col_socio_rep = next(
        (c for c in rep.columns if "código socio" in c.lower() or "codigo socio" in c.lower() or "c\u00f3digo socio" in c.lower()),
        rep.columns[0],
    )
    socios_validos = pd.to_numeric(rep[col_socio_rep], errors="coerce").dropna().astype("Int64").unique()
    socios_validos_set = set(int(x) for x in socios_validos)
    print(f"Socios válidos en reporte filtrado: {len(socios_validos_set)}")

    # 2) Cargar RECUPERACION_DE_MORA y filtrar por esos socios
    df = pd.read_csv(CSV_MORA, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    cod = "Codigo asociado"
    df[cod] = pd.to_numeric(df[cod], errors="coerce").astype("Int64")

    df_filtrado = df[df[cod].apply(lambda x: int(x) in socios_validos_set if pd.notna(x) else False)].copy()
    print(f"Filas en RECUPERACION_DE_MORA (original): {len(df)}")
    print(f"Filas después de filtrar por socios válidos: {len(df_filtrado)}")

    # 3) Encontrar columnas de rangos
    col_rangos = get_col_mapping(df_filtrado)
    if len(col_rangos) < 5:
        col_rangos = [c for c in df_filtrado.columns[5:10] if c]
    etiquetas = ["1-30 días", "31-60 días", "61-90 días", "91-120 días", "Más de 121 días"][: len(col_rangos)]

    # 4) Calcular resumen por rango
    filas = []
    for etiq, col in zip(etiquetas, col_rangos):
        v = pd.to_numeric(df_filtrado[col], errors="coerce").fillna(0)
        n_socios = df_filtrado.loc[v > 0, cod].nunique()
        m_total = v.sum()
        filas.append(
            {
                "Rango_dias": etiq,
                "Cantidad_socios": int(n_socios),
                "Monto_USD": round(float(m_total), 2),
            }
        )

    tabla = pd.DataFrame(filas)
    tabla["Orden"] = range(1, len(tabla) + 1)

    # 5) Guardar Excel para Power BI
    OUT_EXCEL.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_EXCEL, engine="openpyxl") as writer:
        tabla.to_excel(writer, sheet_name="Resumen_por_rango", index=False)
        df_filtrado.to_excel(writer, sheet_name="Detalle_mora_filtrado", index=False)

    print(f"Archivo para Power BI (filtrado) generado: {OUT_EXCEL}")
    print("Hoja 'Resumen_por_rango': Rango_dias, Cantidad_socios, Monto_USD, Orden")
    print("Hoja 'Detalle_mora_filtrado': detalle de RECUPERACION_DE_MORA solo para esos socios")
    return OUT_EXCEL


if __name__ == "__main__":
    main()

