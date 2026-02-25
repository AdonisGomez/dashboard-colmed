---
name: causal-reasoning-and-experiments
description: Help the agent reason about causality, not just correlation, and design or interpret experiments (A/B tests, quasi-experiments). Use when the user wants to understand impact, lift, or causal effects from data.
---

# Causal Reasoning and Experiments

## Mission

Ir más allá de la correlación y ayudar al usuario a:
- Pensar en términos de **causa y efecto**.
- Diseñar y analizar **experimentos** (A/B tests).
- Reconocer sesgos y amenazas a la validez.
- Comunicar resultados con claridad y sin sobre‑afirmar.

Usar junto con `data-analyst` cuando el usuario pregunte por “impacto”, “efecto”, “lift” o “causó que…”.

## Correlación vs Causalidad

Siempre aclara:

- **Correlación**: dos variables se mueven juntas (puede ser casualidad, causa común, o causalidad).
- **Causalidad**: cambiar X produce cambios en Y, manteniendo todo lo demás igual.

Cuando el usuario infiera causalidad solo a partir de datos observacionales, responde:
- Explicando posibles variables de confusión.
- Señalando que los resultados son consistentes con cierta historia causal, pero no prueba definitiva.

## Marco Mental Básico

Para cualquier análisis causal o experimento:

1. Identificar:
   - Tratamiento (X): ¿qué cambia?
   - Outcome (Y): ¿qué se quiere medir?
2. Preguntar:
   - ¿Quién recibe el tratamiento y quién no?
   - ¿Cómo se asigna el tratamiento? (aleatorio, por reglas, por elección propia…)
3. Evaluar:
   - Principales **sesgos potenciales** (selección, cambios temporales, regresión a la media).

## Diseño de A/B Tests

Cuando el usuario diseñe o interprete un experimento:

1. **Unidades y aleatorización**
   - Definir unidad: usuario, sesión, cuenta, tienda, etc.
   - Confirmar que la asignación a grupos sea aleatoria o lo más cercana posible.
2. **Métrica principal**
   - Elegir una métrica clara y alineada con el objetivo (ej. conversión, ingresos por usuario, retención).
3. **Periodo y tamaño de muestra**
   - Verificar duración mínima razonable (incluyendo ciclos semanales).
   - Estimar si el tamaño de muestra es suficiente para detectar el efecto esperado.
4. **Análisis**
   - Comparar grupos A y B en la métrica principal.
   - Calcular lift absoluto y relativo.
   - Opcionalmente, usar tests estadísticos sencillos (t‑test, z‑test) para cuantificar incertidumbre.
5. **Interpretación**
   - Enfatizar tamaño de efecto y relevancia de negocio, no solo p‑values.
   - Discutir posibles efectos secundarios o trade‑offs.

## Amenazas Comunes a la Validez

Menciona y revisa especialmente:

- **Sesgo de selección**: los grupos A y B no son comparables (ej. usuarios más activos en un grupo).
- **Changes over time**: seasonality, campañas externas, cambios de producto simultáneos.
- **Interferencia entre unidades** (spillover): usuarios de A afectan a usuarios de B (ej. referidos, red social).
- **Peeking / p‑hacking**:
  - Mirar resultados muchas veces y cortar el experimento cuando “parece funcionar”.
  - Probar demasiadas variantes/segmentos hasta encontrar un resultado significativo por azar.

Cuando detectes algo de esto, explícitalo y sugiere cómo mitigarlo.

## Datos Observacionales y Cuasi‑Experimentos

Si no hay randomización:

- Recomienda estrategias simplificadas:
  - Comparar tendencias antes/después con grupo de control similar.
  - Incluir variables de control obvias (edad de cuenta, país, dispositivo, etc.).
- Sé cuidadoso al hablar de causalidad:
  - Usa expresiones como “consistente con la hipótesis de que…” en lugar de “demuestra que…”.

No intentes replicar métodos econométricos avanzados completos (DID, IV, etc.) salvo que el usuario lo pida explícitamente; enfócate en intuiciones claras.

## Formato de Salida Recomendado

Cuando el usuario pida ayuda causal / de experimentos:

1. **Pregunta causal** – expresar claramente “¿Cuál es el efecto de X en Y?”.
2. **Diseño / Escenario de datos** – A/B test, before/after, observacional.
3. **Supuestos clave** – qué debe ser cierto para que la interpretación sea válida.
4. **Resultados principales** – efectos estimados, intervalos (si se pueden aproximar), importancia práctica.
5. **Limitaciones** – sesgos posibles, datos faltantes, duración, ruido.
6. **Recomendación** – si avanzar, iterar el experimento o recolectar más datos.

Mantén el lenguaje claro, evita jerga innecesaria y prioriza que el usuario entienda **qué tan confiable** es la conclusión.

