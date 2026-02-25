"""
Prepara el archivo `sep/Reporte_Montos-act_cuotas_completas.xlsx` para usarlo directamente en Power BI.

Acciones:
- Lee la hoja "Montos por socio".
- Normaliza nombres de columnas.
- Separa el texto de cuotas (ej. "25 CUOTAS 38.50") en:
    - num_cuotas (int)
    - monto_cuota (float, USD)
    - monto_calculado = num_cuotas * monto_cuota

Salida:
- `sep/Reporte_Montos_PowerBI_socios.xlsx`
  con columnas limpias: Codigo_socio, Monto_total, Ultima_fecha_liquidacion,
  texto_cuotas, num_cuotas, monto_cuota, monto_calculado.
"""

from pathlib import Path
import re

import pandas as pd

BASE_DIR = Path(__file__).parent
IN_FILE = BASE_DIR / "sep" / "Reporte_Montos-act_cuotas_completas.xlsx"
OUT_FILE = BASE_DIR / "sep" / "Reporte_Montos_PowerBI_socios.xlsx"


def parse_cuotas(texto: str):
    """
    Parsea cadenas del tipo '25 CUOTAS 38.50' -> (25, 38.50).
    Devuelve (None, None) si no se puede parsear.
    """
    if not isinstance(texto, str):
        return None, None
    t = texto.strip().upper()
    if not t:
        return None, None

    # Reemplazar coma decimal por punto por si acaso
    t = t.replace(",", ".")

    m = re.search(r"(\\d+)\\s*CUOTAS?\\s*([0-9.]+)", t)
    if not m:
        # otros formatos como '2 cuotas 16.95' (minúsculas)
        m = re.search(r"(\\d+)\\s*CUOTAS?\\s*DE?\\s*([0-9.]+)", t)
    if not m:
        return None, None

    try:
        num = int(m.group(1))
        monto = float(m.group(2))
        return num, monto
    except Exception:
        return None, None


def main():
    df = pd.read_excel(IN_FILE, sheet_name="Montos por socio", header=3)
    df.columns = [str(c).strip() for c in df.columns]

    # Detectar columnas básicas
    col_socio = next(
        (c for c in df.columns if "código socio" in c.lower() or "codigo socio" in c.lower() or "c\u00f3digo socio" in c.lower()),
        df.columns[0],
    )
    col_monto = next((c for c in df.columns if "monto total" in c.lower()), df.columns[1])
    col_fecha = next(
        (c for c in df.columns if "última fecha" in c.lower() or "ultima fecha" in c.lower()),
        df.columns[2],
    )
    col_cuotas = df.columns[3] if len(df.columns) > 3 else None

    # Construir DataFrame limpio
    out = pd.DataFrame()
    out["Codigo_socio"] = pd.to_numeric(df[col_socio], errors="coerce").astype("Int64")
    out["Monto_total"] = pd.to_numeric(df[col_monto], errors="coerce")
    out["Ultima_fecha_liquidacion"] = pd.to_datetime(df[col_fecha], errors="coerce")
    if col_cuotas is not None:
        out["texto_cuotas"] = df[col_cuotas].astype(str).where(df[col_cuotas].notna(), "")
    else:
        out["texto_cuotas"] = ""

    # Parsear cuotas
    nums = []
    montos_cuota = []
    for txt in out["texto_cuotas"]:
        n, m = parse_cuotas(txt)
        nums.append(n)
        montos_cuota.append(m)
    out["num_cuotas"] = nums
    out["monto_cuota"] = montos_cuota
    out["monto_calculado"] = out["num_cuotas"].fillna(0) * out["monto_cuota"].fillna(0.0)

    # Guardar
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(OUT_FILE, index=False)
    print(f"Archivo preparado para Power BI: {OUT_FILE}")
    print("Columnas:", out.columns.tolist())
    print("Filas:", len(out))


if __name__ == "__main__":
    main()

