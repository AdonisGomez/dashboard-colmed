"""
Genera un nuevo reporte de montos filtrado:
- Solo socios con menos de 24 cuotas PENDIENTES (estado = 'PEN')
- Excluye cualquier socio que tenga al menos una cuota con estado 'MI' (mora irrecuperable)

Entradas:
- sep/Reporte_Montos-act_cuotas_completas.xlsx  (hoja: Montos por socio)
- BasesDeDatos-CUOTAS.xlsx                      (detalle de cuotas con columna 'estado')

Salida:
- sep/Reporte_Montos_PEN_lt24_sin_MI.xlsx
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent

PATH_REPORTE = BASE_DIR / "sep" / "Reporte_Montos-act_cuotas_completas.xlsx"
PATH_CUOTAS = BASE_DIR / "BasesDeDatos-CUOTAS.xlsx"
OUT_FILE = BASE_DIR / "sep" / "Reporte_Montos_PEN_lt24_sin_MI.xlsx"


def cargar_reporte():
    df = pd.read_excel(PATH_REPORTE, sheet_name="Montos por socio", header=3)
    df.columns = [str(c).strip() for c in df.columns]

    col_socio = next(
        (c for c in df.columns if "código socio" in c.lower() or "codigo socio" in c.lower() or "c\u00f3digo socio" in c.lower()),
        df.columns[0],
    )
    return df, col_socio


def cargar_cuotas():
    df = pd.read_excel(PATH_CUOTAS)
    df.columns = [str(c).strip() for c in df.columns]

    col_socio = next((c for c in df.columns if c.lower() in ("socio_id", "codigo_socio", "codigo")), None)
    if col_socio is None:
        raise ValueError("No se encontró columna de socio en BasesDeDatos-CUOTAS.xlsx")

    col_estado = next((c for c in df.columns if "estado" in c.lower()), None)
    if col_estado is None:
        raise ValueError("No se encontró columna de estado en BasesDeDatos-CUOTAS.xlsx")

    return df, col_socio, col_estado


def main():
    # Cargar datos
    reporte, col_socio_rep = cargar_reporte()
    cuotas, col_socio_cuotas, col_estado = cargar_cuotas()

    # Normalizar socio a entero
    reporte[col_socio_rep] = pd.to_numeric(reporte[col_socio_rep], errors="coerce").astype("Int64")
    cuotas[col_socio_cuotas] = pd.to_numeric(cuotas[col_socio_cuotas], errors="coerce").astype("Int64")

    # Normalizar estado a mayúsculas
    cuotas[col_estado] = cuotas[col_estado].astype(str).str.upper().str.strip()

    # Socios con al menos una cuota MI (mora irrecuperable)
    socios_mi = cuotas.loc[cuotas[col_estado] == "MI", col_socio_cuotas].dropna().unique()
    socios_mi_set = set(int(x) for x in socios_mi)
    print(f"Socios con MI en la base de cuotas: {len(socios_mi_set)}")

    # Contar cuotas PEN por socio
    pen_mask = cuotas[col_estado] == "PEN"
    pen_por_socio = (
        cuotas.loc[pen_mask, [col_socio_cuotas]]
        .groupby(col_socio_cuotas)
        .size()
        .rename("cuotas_PEN")
        .reset_index()
    )

    # Construir tabla auxiliar: por socio → cuotas_PEN, tiene_MI
    socios = pd.DataFrame({"socio_id": reporte[col_socio_rep].dropna().unique().astype("Int64")})
    socios = socios.merge(pen_por_socio, left_on="socio_id", right_on=col_socio_cuotas, how="left")
    socios["cuotas_PEN"] = socios["cuotas_PEN"].fillna(0).astype(int)
    socios["tiene_MI"] = socios["socio_id"].apply(lambda x: int(x) in socios_mi_set)

    # Condición de inclusión:
    # - menos de 24 cuotas PENDIENTES
    # - y NO tiene MI
    socios["incluir"] = (socios["cuotas_PEN"] < 24) & (~socios["tiene_MI"])

    socios_incluir = set(socios.loc[socios["incluir"], "socio_id"].astype(int).tolist())
    print(f"Socios que pasan el filtro (PEN < 24 y sin MI): {len(socios_incluir)}")

    # Aplicar filtro al reporte
    filtrado = reporte[reporte[col_socio_rep].apply(lambda x: int(x) in socios_incluir if pd.notna(x) else False)]
    print(f"Filas reporte original: {len(reporte)}")
    print(f"Filas después del filtro: {len(filtrado)}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    filtrado.to_excel(OUT_FILE, index=False)
    print(f"Reporte filtrado guardado en: {OUT_FILE}")


if __name__ == "__main__":
    main()

