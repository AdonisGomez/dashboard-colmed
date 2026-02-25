# Receta: Dashboard de cuotas en Power BI (2 minutos)

Sigue estos pasos en **Power BI Desktop**. Al final tendrás un reporte con tarjetas por rango y gráfico de barras.

---

## Paso 1 – Cargar datos

1. Abre **Power BI Desktop**.
2. **Inicio** → **Obtener datos** → **Excel**.
3. Navega a la carpeta **sep** y selecciona **Dashboard_Cuotas_PowerBI.xlsx** → **Abrir**.
4. En el navegador, marca **Resumen_por_rango** y pulsa **Cargar**.

---

## Paso 2 – Ordenar el rango de días

1. En el panel derecho, pestaña **Datos**, localiza la tabla **Resumen_por_rango**.
2. Clic derecho en **Resumen_por_rango** → **Ordenar por columna** → **Orden** (para que **Rango_dias** quede en orden 1-30, 31-60, 61-90, etc.).

---

## Paso 3 – Tarjetas (cantidad de socios por rango)

1. En **Visualizaciones**, elige **Tarjeta** (icono de número).
2. En **Campos**, arrastra **Cantidad_socios** al área **Valor** del visual.
3. Arrastra **Rango_dias** al área **Filtros de este visual** (o a **Leyenda** si quieres segmentar).
4. Si quieres **una tarjeta por rango**: duplica este visual (Ctrl+C, Ctrl+V) 5 veces. En cada tarjeta, en **Filtros de este visual** añade **Rango_dias** y elige un valor (p. ej. "1-30 días", "31-60 días", …). Así tendrás 5 tarjetas en fila.

---

## Paso 4 – Gráfico de barras (socios por rango)

1. Añade un visual **Gráfico de barras agrupadas**.
2. Arrastra **Rango_dias** a **Eje Y**.
3. Arrastra **Cantidad_socios** a **Valores**.
4. Si el orden no es el correcto: en **Más opciones** (⋯) del visual → **Ordenar por** → **Orden** o **Cantidad_socios**.

---

## Paso 5 – Gráfico de barras (monto en PEN)

1. Añade otro **Gráfico de barras agrupadas**.
2. **Eje Y**: **Rango_dias**.
3. **Valores**: **Monto_PEN**.
4. (Opcional) Formato del eje: moneda, 2 decimales.

---

## Paso 6 – Tabla resumen

1. Añade un visual **Tabla**.
2. Arrastra **Rango_dias**, **Cantidad_socios** y **Monto_PEN** a **Valores**.

---

## Resultado

- **Tarjetas**: cantidad de socios por rango (1-30, 31-60, 61-90, 91-120, más de 121 días).
- **Barras**: socios y monto PEN por rango.
- **Tabla**: resumen con los tres campos.

Guarda el reporte como **Dashboard_Cuotas_Pendientes.pbix**.

---

## Actualizar después

Cuando cambies los datos:

1. Ejecuta: `python exportar_para_powerbi.py` (en la carpeta del proyecto).
2. En Power BI: **Inicio** → **Actualizar**.
