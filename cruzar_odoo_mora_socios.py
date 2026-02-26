from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent
ODOO_DIR = BASE_DIR / "odoo"

ARCHIVO_MORA = BASE_DIR / "Reporte_act_cuotas_completas.xlsx"
ARCHIVO_MEMBERSHIP = ODOO_DIR / "Membership (res.membership).xlsx"
ARCHIVO_RESUMEN_ODOO = ODOO_DIR / "odoo_resumen_socios.xlsx"

OUT_CRUCE = ODOO_DIR / "odoo_vs_mora_socios.xlsx"


def _parse_cuotas(texto: str) -> int | None:
    """Extrae la cantidad de cuotas desde el texto, por ejemplo '25 CUOTAS 38.50' -> 25."""
    if not isinstance(texto, str):
        return None
    t = texto.strip().upper()
    if not t:
        return None
    import re

    # Buscar números en el texto, p.ej. '25 CUOTAS 38.50' -> 25
    nums = re.findall(r"(\d+)", t)
    if not nums:
        return None
    try:
        return int(nums[0])
    except Exception:
        return None


def _rango_por_cuotas(n: int | None) -> str:
    """Clasifica según la cantidad de cuotas en rangos de días (aproximados)."""
    if n is None or n <= 0:
        return "Sin rango"
    if n == 1:
        return "de 0 a 30"
    if n == 2:
        return "de 31 a 60"
    if n == 3:
        return "de 61 a 90"
    if n in (4, 5):
        return "de 91 a 120"
    return "mas de 121 días"


def _normalizar_nombre(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    t = texto.strip().upper()
    # Quitar dobles espacios
    while "  " in t:
        t = t.replace("  ", " ")
    return t


def cargar_mora() -> pd.DataFrame:
    """Carga el reporte de mora con código de socio, monto total y rango de días (según cuotas)."""
    if not ARCHIVO_MORA.exists():
        raise SystemExit(f"No encuentro el archivo de mora: {ARCHIVO_MORA}")

    df = pd.read_excel(ARCHIVO_MORA, sheet_name="Montos por socio", header=3)
    df.columns = [str(c).strip() for c in df.columns]

    # El archivo viene con acentos rotos: 'C�digo socio'
    col_codigo = next((c for c in df.columns if "c" in c.lower() and "socio" in c.lower()), None)
    col_monto = next((c for c in df.columns if "monto total" in c.lower()), None)
    # Columna de texto de cuotas (suele ser Unnamed: 3)
    col_texto = next((c for c in df.columns if "unnamed" in c.lower()), None)

    if not col_codigo or not col_monto:
        raise SystemExit(f"No encontré columnas de código/monto en {ARCHIVO_MORA}: {df.columns}")

    mora = df[[col_codigo, col_monto]].copy()
    mora.rename(columns={col_codigo: "Codigo_socio", col_monto: "Monto_mora"}, inplace=True)
    mora["Codigo_socio"] = pd.to_numeric(mora["Codigo_socio"], errors="coerce").astype("Int64")
    mora["Monto_mora"] = pd.to_numeric(mora["Monto_mora"], errors="coerce").fillna(0.0)

    # Rango de días según texto de cuotas (si existe)
    if col_texto and col_texto in df.columns:
        texto_series = df[col_texto].astype(str)
        num_cuotas = [ _parse_cuotas(t) for t in texto_series ]
        mora["num_cuotas_calc"] = pd.Series(num_cuotas, index=mora.index)
        mora["Rango_dias_por_cuotas"] = [
            _rango_por_cuotas(n if pd.notna(n) else None) for n in mora["num_cuotas_calc"]
        ]
    else:
        mora["Rango_dias_por_cuotas"] = "Sin rango"

    mora = mora[mora["Codigo_socio"].notna()].copy()
    # Depuración: un socio puede aparecer más de una vez → agregar por Codigo_socio
    if mora["Codigo_socio"].duplicated().any():
        mora = (
            mora.groupby("Codigo_socio", as_index=False)
            .agg(
                Monto_mora=("Monto_mora", "sum"),
                Rango_dias_por_cuotas=("Rango_dias_por_cuotas", "first"),
            )
        )
        print("  Depuración mora: socios duplicados agregados (Monto_mora sumado, Rango primera aparición)")
    return mora


def cargar_membership() -> pd.DataFrame:
    """Carga el maestro de socios con código + nombre desde Odoo Membership."""
    if not ARCHIVO_MEMBERSHIP.exists():
        raise SystemExit(f"No encuentro el archivo de membership: {ARCHIVO_MEMBERSHIP}")

    df = pd.read_excel(ARCHIVO_MEMBERSHIP)
    df.columns = [str(c).strip() for c in df.columns]

    col_codigo = next((c for c in df.columns if "código de socio" in c.lower() or "codigo de socio" in c.lower()), None)
    col_nombre = next((c for c in df.columns if "miembro/nombre" in c.lower() or "nombre" in c.lower()), None)

    if not col_codigo or not col_nombre:
        raise SystemExit(f"No encontré columnas de código/nombre en {ARCHIVO_MEMBERSHIP}: {df.columns}")

    master = df[[col_codigo, col_nombre]].copy()
    master.rename(columns={col_codigo: "Codigo_socio", col_nombre: "Nombre_socio"}, inplace=True)
    master["Codigo_socio"] = pd.to_numeric(master["Codigo_socio"], errors="coerce").astype("Int64")
    master["Nombre_socio"] = master["Nombre_socio"].astype(str).str.strip()
    master["Nombre_norm"] = master["Nombre_socio"].map(_normalizar_nombre)
    master = master[master["Codigo_socio"].notna()].copy()
    # Depuración: un código puede repetirse → quedarse con la primera fila
    antes = len(master)
    master = master.drop_duplicates(subset=["Codigo_socio"], keep="first").copy()
    if len(master) < antes:
        print(f"  Depuración membership: {antes - len(master)} filas duplicadas por Codigo_socio eliminadas")
    return master


def cargar_resumen_odoo() -> pd.DataFrame:
    """Carga el resumen de Odoo por CONSUMIDOR."""
    if not ARCHIVO_RESUMEN_ODOO.exists():
        raise SystemExit(f"No encuentro el archivo de resumen Odoo: {ARCHIVO_RESUMEN_ODOO}")

    df = pd.read_excel(ARCHIVO_RESUMEN_ODOO)
    df.columns = [str(c).strip() for c in df.columns]

    if "CONSUMIDOR" not in df.columns:
        raise SystemExit(f"No encontré columna CONSUMIDOR en {ARCHIVO_RESUMEN_ODOO}: {df.columns}")

    od = df.copy()
    od["CONSUMIDOR"] = od["CONSUMIDOR"].astype(str).str.strip()
    od["Nombre_norm"] = od["CONSUMIDOR"].map(_normalizar_nombre)

    # Nos quedamos con columnas relevantes
    cols = [
        "Nombre_norm",
        "CONSUMIDOR",
        "Monto_pagado_total",
        "Numero_pagos",
        "Primer_pago",
        "Ultimo_pago",
        "Estado_socio_odoo_ultimo",
        "Tipo_pago_ultimo",
        "Estado_comprobante_ultimo",
        "Anio_ultimo_pago",
        "Mes_ultimo_pago",
    ]
    od = od[cols].copy()
    od["Monto_pagado_total"] = pd.to_numeric(od["Monto_pagado_total"], errors="coerce").fillna(0.0)
    return od


def clasificar_fila(row: pd.Series) -> str:
    monto_mora = row.get("Monto_mora", 0.0) or 0.0
    monto_odoo = row.get("Monto_pagado_total", 0.0) or 0.0
    estado_odoo = str(row.get("Estado_socio_odoo_ultimo") or "").strip().lower()

    tiene_mora = monto_mora > 0.01
    paga_en_odoo = monto_odoo > 0.01 and estado_odoo in {"active", "confirm"}

    if tiene_mora and paga_en_odoo:
        return "Mora_y_paga_en_Odoo"
    if tiene_mora and not paga_en_odoo:
        return "Sigue_en_mora"
    if not tiene_mora and paga_en_odoo:
        return "Al_dia_en_mora_y_paga_en_Odoo"
    if not tiene_mora and not paga_en_odoo and monto_odoo > 0.01:
        return "Solo_en_Odoo"
    return "Sin_informacion_clara"


def main() -> None:
    print("Cargando mora...")
    mora = cargar_mora()
    print(f"Socios en reporte de mora: {mora['Codigo_socio'].nunique()}")

    print("Cargando maestro Membership...")
    master = cargar_membership()
    print(f"Socios en membership: {master['Codigo_socio'].nunique()}")

    print("Cargando resumen Odoo...")
    od = cargar_resumen_odoo()
    print(f"Socios en resumen Odoo: {od['Nombre_norm'].nunique()}")

    # Unir mora + nombres por código de socio
    base = mora.merge(master[["Codigo_socio", "Nombre_socio", "Nombre_norm"]], on="Codigo_socio", how="left")

    # Unir con Odoo por nombre normalizado
    cruce = base.merge(od, on="Nombre_norm", how="left", suffixes=("", "_odoo"))

    # Monto de mora restante ≈ mora - pagado (no negativo)
    cruce["Monto_mora_restante"] = (cruce["Monto_mora"] - cruce["Monto_pagado_total"]).clip(lower=0.0)

    # Clasificación
    cruce["Clasificacion"] = cruce.apply(clasificar_fila, axis=1)

    # Ordenar: primero los que siguen en mora o que pagan en Odoo
    orden_pref = {
        "Mora_y_paga_en_Odoo": 1,
        "Sigue_en_mora": 2,
        "Al_dia_en_mora_y_paga_en_Odoo": 3,
        "Solo_en_Odoo": 4,
        "Sin_informacion_clara": 9,
    }
    cruce["__orden"] = cruce["Clasificacion"].map(orden_pref).fillna(9)
    cruce = cruce.sort_values(["__orden", "Monto_mora"], ascending=[True, False])
    cruce = cruce.drop(columns=["__orden"])

    # Guardar resultado
    ODOO_DIR.mkdir(parents=True, exist_ok=True)
    cruce.to_excel(OUT_CRUCE, index=False)
    print(f"Cruce Odoo vs mora guardado en: {OUT_CRUCE}")

    # Pequeño resumen por clasificación
    resumen_clasif = cruce.groupby("Clasificacion")["Codigo_socio"].nunique().reset_index(name="Socios_unicos")
    print("\nSocios por clasificación:")
    print(resumen_clasif.to_string(index=False))


if __name__ == "__main__":
    main()

