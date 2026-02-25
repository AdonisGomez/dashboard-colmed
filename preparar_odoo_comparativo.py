from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent
ODOO_DIR = BASE_DIR / "odoo"

OUT_DETALLE = ODOO_DIR / "odoo_cuotas_unificado.xlsx"
OUT_RESUMEN = ODOO_DIR / "odoo_resumen_socios.xlsx"
OUT_PAGOS_MES = ODOO_DIR / "odoo_pagos_mensuales.xlsx"


def cargar_y_unir_archivos() -> pd.DataFrame:
    """Lee todos los archivos cuotas_*.xlsx de la carpeta odoo y los une en un solo DataFrame."""
    if not ODOO_DIR.exists():
        raise SystemExit(f"No existe la carpeta Odoo: {ODOO_DIR}")

    paths = sorted(ODOO_DIR.glob("cuotas_*.xlsx"))
    if not paths:
        raise SystemExit(f"No se encontraron archivos cuotas_*.xlsx en {ODOO_DIR}")

    dfs: list[pd.DataFrame] = []
    for path in paths:
        df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        df["__archivo"] = path.name
        dfs.append(df)

    unido = pd.concat(dfs, ignore_index=True)
    return unido


def preparar_detalle(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas clave y agrega información de periodo (año/mes)."""
    # Asegurar columnas esperadas
    esperadas = [
        "COMPROBANTE",
        "MONTO",
        "TIPO DE COMPROBANTE",
        "TIPO PAGO",
        "FECHA COMPROB.",
        "FECHA REGISTRO",
        "FECHA APLICACION",
        "ESTADO",
        "CONSUMIDOR",
        "ESTADO SOCIO",
        "__archivo",
    ]
    faltantes = [c for c in esperadas if c not in df.columns]
    if faltantes:
        raise SystemExit(f"Faltan columnas en los archivos de Odoo: {faltantes}")

    # Copia de trabajo
    det = df[esperadas].copy()

    # Montos numéricos
    det["MONTO"] = pd.to_numeric(det["MONTO"], errors="coerce").fillna(0.0)

    # Fechas: intentamos usar FECHA APLICACION como fecha principal; si no hay, FECHA COMPROB.
    fecha_apl = pd.to_datetime(det["FECHA APLICACION"], errors="coerce", dayfirst=True)
    fecha_comp = pd.to_datetime(det["FECHA COMPROB."], errors="coerce", dayfirst=True)
    fecha_reg = pd.to_datetime(det["FECHA REGISTRO"], errors="coerce", dayfirst=True)

    fecha_base = fecha_apl.combine_first(fecha_comp).combine_first(fecha_reg)
    det["FECHA_BASE"] = fecha_base
    det["ANIO"] = det["FECHA_BASE"].dt.year
    det["MES"] = det["FECHA_BASE"].dt.month

    return det


def preparar_resumen_por_socio(det: pd.DataFrame) -> pd.DataFrame:
    """Construye un resumen por CONSUMIDOR (socio en Odoo)."""
    # Agrupación básica
    grp = det.groupby("CONSUMIDOR", dropna=False)

    res = grp.agg(
        Monto_pagado_total=("MONTO", "sum"),
        Numero_pagos=("MONTO", "size"),
        Primer_pago=("FECHA_BASE", "min"),
        Ultimo_pago=("FECHA_BASE", "max"),
    )

    # Tomar el ESTADO SOCIO del último pago registrado para cada consumidor
    # Ordenamos por FECHA_BASE y nos quedamos con la última fila por CONSUMIDOR
    ult = (
        det.sort_values(["CONSUMIDOR", "FECHA_BASE"])
        .groupby("CONSUMIDOR", dropna=False)
        .tail(1)
        .set_index("CONSUMIDOR")
    )

    res["Estado_socio_odoo_ultimo"] = ult["ESTADO SOCIO"]
    res["Tipo_pago_ultimo"] = ult["TIPO PAGO"]
    res["Estado_comprobante_ultimo"] = ult["ESTADO"]
    res["Anio_ultimo_pago"] = res["Ultimo_pago"].dt.year
    res["Mes_ultimo_pago"] = res["Ultimo_pago"].dt.month

    # Ordenar por monto pagado descendente
    res = res.sort_values("Monto_pagado_total", ascending=False)
    return res


def main() -> None:
    print(f"Leyendo archivos de Odoo en: {ODOO_DIR}")
    df = cargar_y_unir_archivos()
    print(f"Filas unificadas: {len(df)}")

    det = preparar_detalle(df)
    print(f"Filas en detalle con fecha base: {len(det)}")

    # Guardar detalle completo (todas las cuotas Odoo unificadas)
    OUT_DETALLE.parent.mkdir(parents=True, exist_ok=True)
    det.to_excel(OUT_DETALLE, index=False)
    print(f"Detalle unificado guardado en: {OUT_DETALLE}")

    # Guardar resumen por socio (CONSUMIDOR)
    resumen = preparar_resumen_por_socio(det)
    resumen.to_excel(OUT_RESUMEN, index=True)
    print(f"Resumen por socio guardado en: {OUT_RESUMEN}")

    # Resumen mensual de pagos (para KPIs por periodo)
    pagos_mes = (
        det.dropna(subset=["ANIO", "MES"])
        .groupby(["ANIO", "MES"], dropna=True)
        .agg(
            Monto_pagado_mes=("MONTO", "sum"),
            Numero_pagos_mes=("MONTO", "size"),
            Socios_unicos_mes=("CONSUMIDOR", "nunique"),
        )
        .reset_index()
    )
    pagos_mes.to_excel(OUT_PAGOS_MES, index=False)
    print(f"Resumen mensual de pagos guardado en: {OUT_PAGOS_MES}")


if __name__ == "__main__":
    main()

