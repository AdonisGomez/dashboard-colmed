# Dashboard de cuotas pendientes en Power BI

Esta guía explica cómo armar el reporte de **socios con cuotas pendientes por rango de días** (1-30, 31-60, 61-90, 91-120, más de 121 días) en Power BI Desktop.

---

## 1. Generar el archivo de datos

En la carpeta del proyecto ejecuta:

```bash
python exportar_para_powerbi.py
```

Se crea **`sep/Dashboard_Cuotas_PowerBI.xlsx`** con:

- **Resumen_por_rango**: tabla con columnas `Rango_dias`, `Cantidad_socios`, `Monto_PEN`, `Orden`.
- **Detalle_mora**: datos detalle de RECUPERACION_DE_MORA (opcional para análisis).

---

## 2. Crear el reporte en Power BI Desktop

### Conectar los datos

1. Abre **Power BI Desktop**.
2. **Inicio** → **Obtener datos** → **Excel**.
3. Selecciona **`Dashboard_Cuotas_PowerBI.xlsx`** (en la carpeta `sep`) y **Abrir**.
4. Marca la tabla **Resumen_por_rango** y pulsa **Cargar** (o **Transformar datos** si quieres editar antes).

### Visuales recomendados

**Tarjetas (cantidad de socios por rango)**

1. Añade un visual tipo **Tarjeta**.
2. Arrastra **Cantidad_socios** al campo *Valor*.
3. Arrastra **Rango_dias** al campo *Filtros de este visual* (o usa **Rango_dias** en *Leyenda* si haces varias tarjetas con filtro).
4. Para tener una tarjeta por rango: duplica el visual y en cada uno aplica un **Filtro de página** o **Filtro de visual** por un valor de **Rango_dias** (ej. "1-30 días", "31-60 días", etc.), mostrando **Cantidad_socios** en cada tarjeta.

**Gráfico de barras (socios por rango)**

1. Añade un visual **Gráfico de barras agrupadas**.
2. **Eje Y**: `Rango_dias`.
3. **Valores**: `Cantidad_socios`.
4. En **Ordenar por**, elige **Orden** (o ordena por **Cantidad_socios**) para que los rangos salgan en el orden lógico (1-30, 31-60, …).

**Gráfico de barras (monto por rango)**

1. Otro **Gráfico de barras agrupadas**.
2. **Eje Y**: `Rango_dias`.
3. **Valores**: `Monto_PEN`.
4. Formato del eje: número con 2 decimales y símbolo de moneda si quieres.

**Tabla resumen**

1. Visual **Tabla**.
2. Columnas: **Rango_dias**, **Cantidad_socios**, **Monto_PEN**.

### Orden de los rangos

La columna **Orden** en **Resumen_por_rango** sirve para ordenar:

- En el panel **Datos**, clic derecho en **Resumen_por_rango** → **Ordenar por columna** → elegir **Orden** para **Rango_dias**.

Así en todos los gráficos los rangos saldrán como: 1-30 días, 31-60 días, 61-90 días, 91-120 días, Más de 121 días.

---

## 3. Actualizar datos

Cada vez que actualices **RECUPERACION_DE_MORA.csv**:

1. Vuelve a ejecutar:  
   `python exportar_para_powerbi.py`
2. En Power BI Desktop: **Inicio** → **Actualizar** (o **Transformar datos** si la fuente sigue siendo el mismo Excel y solo cambiaste el .xlsx).

Si en Power BI cambias la fuente al CSV directamente, puedes apuntar a **RECUPERACION_DE_MORA.csv** y hacer las mismas medidas/columnas calculadas en Power Query y en el modelo; el Excel **Dashboard_Cuotas_PowerBI.xlsx** es la opción más simple para empezar.

---

## Resumen rápido

| Paso | Acción |
|------|--------|
| 1 | `python exportar_para_powerbi.py` → genera `sep/Dashboard_Cuotas_PowerBI.xlsx` |
| 2 | Power BI: Obtener datos → Excel → cargar **Resumen_por_rango** |
| 3 | Ordenar **Rango_dias** por columna **Orden** |
| 4 | Crear tarjetas (Cantidad_socios), barras (Cantidad_socios y Monto_PEN) y tabla |

Con esto tendrás el mismo contenido del dashboard web (cantidad de socios y monto por rango de días) en Power BI.
