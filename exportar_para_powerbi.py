"""
Genera un Excel listo para Power BI con los datos del dashboard de cuotas por rango de días.
Ejecutar: python exportar_para_powerbi.py
Salida: sep/Dashboard_Cuotas_PowerBI.xlsx

Moneda: USD (dólares estadounidenses).
"""
import pandas as pd
from pathlib import Path

CSV_MORA = Path(__file__).parent / "RECUPERACION_DE_MORA.csv"
OUT_EXCEL = Path(__file__).parent / "sep" / "Dashboard_Cuotas_PowerBI.xlsx"


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


def main():
    df = pd.read_csv(CSV_MORA, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    cod = "Codigo asociado"
    col_rangos = get_col_mapping(df)
    if len(col_rangos) < 5:
        col_rangos = [c for c in df.columns[5:10] if c]
    etiquetas = ["1-30 días", "31-60 días", "61-90 días", "91-120 días", "Más de 121 días"]
    while len(etiquetas) > len(col_rangos):
        etiquetas.pop()

    filas = []
    for etiq, col in zip(etiquetas, col_rangos):
        try:
            v = pd.to_numeric(df[col], errors="coerce").fillna(0)
            n_socios = df.loc[v > 0, cod].nunique()
            m_total = v.sum()
        except Exception:
            n_socios = 0
            m_total = 0.0
        filas.append({
            "Rango_dias": etiq,
            "Cantidad_socios": int(n_socios),
            "Monto_USD": round(float(m_total), 2),
        })

    tabla = pd.DataFrame(filas)

    # Orden para gráficos: 1-30, 31-60, 61-90, 91-120, Más 121
    tabla["Orden"] = range(1, len(tabla) + 1)

    OUT_EXCEL.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_EXCEL, engine="openpyxl") as writer:
        tabla.to_excel(writer, sheet_name="Resumen_por_rango", index=False)
        # Opcional: datos detalle para drill-down (socios por rango)
        df.to_excel(writer, sheet_name="Detalle_mora", index=False)

    print(f"Archivo para Power BI generado: {OUT_EXCEL}")
    print("Hoja 'Resumen_por_rango': Rango_dias, Cantidad_socios, Monto_USD, Orden")
    print("Hoja 'Detalle_mora': datos crudos de RECUPERACION_DE_MORA.csv")
    return OUT_EXCEL


if __name__ == "__main__":
    main()
