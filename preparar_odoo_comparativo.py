from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent
ODOO_DIR = BASE_DIR / "odoo"

OUT_DETALLE = ODOO_DIR / "odoo_cuotas_unificado.xlsx"
OUT_RESUMEN = ODOO_DIR / "odoo_resumen_socios.xlsx"
OUT_PAGOS_MES = ODOO_DIR / "odoo_pagos_mensuales.xlsx"
OUT_PAGOS_DIA = ODOO_DIR / "odoo_pagos_por_dia.xlsx"


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

    # Fechas:
    # - FECHA_PAGO: cuándo entra el dinero (caja) → FECHA REGISTRO.
    # - FECHA_PERIODO: a qué mes/año se aplica el pago → FECHA APLICACION, si no FECHA COMPROB.
    fecha_apl = pd.to_datetime(det["FECHA APLICACION"], errors="coerce", dayfirst=True)
    fecha_comp = pd.to_datetime(det["FECHA COMPROB."], errors="coerce", dayfirst=True)
    fecha_reg = pd.to_datetime(det["FECHA REGISTRO"], errors="coerce", dayfirst=True)

    fecha_periodo = fecha_apl.combine_first(fecha_comp)
    det["FECHA_PERIODO"] = fecha_periodo
    det["ANIO_PERIODO"] = det["FECHA_PERIODO"].dt.year
    det["MES_PERIODO"] = det["FECHA_PERIODO"].dt.month

    det["FECHA_PAGO"] = fecha_reg
    det["ANIO_PAGO"] = det["FECHA_PAGO"].dt.year
    det["MES_PAGO"] = det["FECHA_PAGO"].dt.month
    det["DIA_PAGO"] = det["FECHA_PAGO"].dt.day
    det["SEMANA_PAGO"] = (
        det["FECHA_PAGO"].dt.isocalendar().year.astype("Int64").astype(str)
        + "-W"
        + det["FECHA_PAGO"].dt.isocalendar().week.astype("Int64").astype(str).str.zfill(2)
    )

    # FECHA_BASE se mantiene para compatibilidad: usamos periodo si existe,
    # y como último recurso FECHA_PAGO.
    fecha_base = fecha_periodo.combine_first(fecha_reg)
    det["FECHA_BASE"] = fecha_base
    det["ANIO"] = det["FECHA_BASE"].dt.year
    det["MES"] = det["FECHA_BASE"].dt.month
    det["DIA"] = det["FECHA_BASE"].dt.day
    det["SEMANA"] = (
        det["FECHA_BASE"].dt.isocalendar().year.astype("Int64").astype(str)
        + "-W"
        + det["FECHA_BASE"].dt.isocalendar().week.astype("Int64").astype(str).str.zfill(2)
    )

    # Código de socio Odoo a partir del comprobante, ej. MEM/2025/7572 → 7572.
    cod_segment = (
        det["COMPROBANTE"]
        .astype(str)
        .str.split("/")
        .str[-1]
        .str.extract(r"(\d+)", expand=False)
    )
    det["CODIGO_SOCIO_ODOO"] = pd.to_numeric(cod_segment, errors="coerce").astype("Int64")

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

    # Resumen mensual de pagos por FECHA_PAGO (caja)
    pagos_mes = (
        det.dropna(subset=["ANIO_PAGO", "MES_PAGO"])
        .groupby(["ANIO_PAGO", "MES_PAGO"], dropna=True)
        .agg(
            Monto_pagado_mes=("MONTO", "sum"),
            Numero_pagos_mes=("MONTO", "size"),
            Socios_unicos_mes=("CONSUMIDOR", "nunique"),
        )
        .reset_index()
    )
    pagos_mes = pagos_mes.rename(columns={"ANIO_PAGO": "ANIO", "MES_PAGO": "MES"})
    pagos_mes.to_excel(OUT_PAGOS_MES, index=False)
    print(f"Resumen mensual de pagos guardado en: {OUT_PAGOS_MES}")

    # Resumen por día de pagos (caja) usando FECHA_PAGO
    det_con_fecha = det.dropna(subset=["FECHA_PAGO"])
    pagos_dia = (
        det_con_fecha.groupby(det_con_fecha["FECHA_PAGO"].dt.normalize(), dropna=True)
        .agg(
            Monto_pagado_dia=("MONTO", "sum"),
            Numero_pagos_dia=("MONTO", "size"),
            Socios_unicos_dia=("CONSUMIDOR", "nunique"),
        )
        .reset_index()
        .rename(columns={"FECHA_PAGO": "fecha"})
    )
    pagos_dia["fecha"] = pd.to_datetime(pagos_dia["fecha"]).dt.date
    pagos_dia["ANIO"] = pd.to_datetime(pagos_dia["fecha"]).dt.year
    pagos_dia["MES"] = pd.to_datetime(pagos_dia["fecha"]).dt.month
    pagos_dia["DIA"] = pd.to_datetime(pagos_dia["fecha"]).dt.day
    pagos_dia["SEMANA"] = (
        pd.to_datetime(pagos_dia["fecha"]).dt.isocalendar().year.astype("Int64").astype(str)
        + "-W"
        + pd.to_datetime(pagos_dia["fecha"]).dt.isocalendar().week.astype("Int64").astype(str).str.zfill(2)
    )
    pagos_dia["fecha_str"] = pagos_dia["fecha"].astype(str)
    pagos_dia.to_excel(OUT_PAGOS_DIA, index=False)
    print(f"Resumen por día de pagos guardado en: {OUT_PAGOS_DIA}")


if __name__ == "__main__":
    main()

