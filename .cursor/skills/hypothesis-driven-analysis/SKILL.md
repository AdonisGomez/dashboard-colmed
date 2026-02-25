---
name: hypothesis-driven-analysis
description: Guide the agent to frame data work around clear hypotheses, assumptions, and validation plans before writing code. Use when the user wants deeper reasoning in data analysis, not just exploratory charts.
---

# Hypothesis-Driven Analysis

## Mission

Shift from “data fishing” to **structured, hypothesis‑driven analysis**:
- Start with explicit questions and hypotheses.
- Make assumptions and risks visible.
- Design simple validation plans.
- Communicate results in terms of whether evidence supports or contradicts each hypothesis.

Use this skill together with `data-analyst` and `visualization-expert` when you want senior‑level reasoning around data, not solo código.

## Core Workflow

Siempre que el usuario pida “analizar datos”, “buscar insights” o “entender por qué pasa algo”, sigue este flujo:

1. **Clarificar la pregunta de negocio**
   - ¿Qué decisión se quiere tomar con este análisis?
   - ¿Qué outcome o métrica es la prioridad?
2. **Formular hipótesis**
   - Escribir 2–5 hipótesis concretas del tipo:
     - “Si _X_ es cierto, entonces deberíamos observar _Y_ en los datos.”
3. **Listar supuestos y riesgos**
   - ¿Qué estamos asumiendo sobre los datos, el tracking, el comportamiento de los usuarios?
4. **Diseñar un plan de validación**
   - Qué tablas/datasets usar.
   - Qué cortes, agregaciones y tests aplicar.
   - Qué gráficos ayudan a validar/refutar la hipótesis.
5. **Ejecutar análisis y documentar evidencias**
   - Tablas, gráficos, estadísticas.
6. **Concluir por hipótesis**
   - “Soporte fuerte / soporte débil / evidencia en contra / inconcluso”.

## Plantilla de Trabajo

Para cada análisis, propone esta estructura:

1. **Contexto**
   - 2–4 frases con el problema de negocio y la métrica clave.
2. **Hipótesis**
   - Lista numerada:
     - H1: …
     - H2: …
3. **Supuestos & Riesgos**
   - Bullets cortos de lo que se asume sobre datos y entorno.
4. **Plan de análisis**
   - Lista de pasos concretos (queries, transformaciones, visualizaciones).
5. **Resultados**
   - Evidencias por hipótesis (tablas/resúmenes).
6. **Conclusiones & Siguientes pasos**
   - Decisiones sugeridas y qué analizar después.

## Buenas Hipótesis vs Malas Hipótesis

**Buenas hipótesis:**
- Son falsables (pueden refutarse con datos).
- Apuntan a un mecanismo plausible.
- Se traducen en métricas observables.

Ejemplos:
- “Si las campañas de pago de agosto trajeron usuarios de menor calidad, entonces la tasa de retención 30 días de esos usuarios será menor que la cohorte de julio.”
- “Si el nuevo onboarding reduce fricción, entonces el ratio ‘signup → first key action’ debería ser mayor tras el lanzamiento.”

**Malas hipótesis:**
- Son demasiado vagas o no observables.
- Mezclan múltiples explicaciones a la vez.
- No se conectan con datos específicos.

Ejemplos:
- “El producto no gusta a los usuarios.”
- “El mercado está raro.”

Cuando detectes hipótesis malas, reescríbelas en una forma medible.

## Uso con Código y Notebooks

Cuando generes código (SQL, Python, R, etc.):

- Incluye la hipótesis que se está testando en un comentario encima del bloque de código.
- Mantén una sección de resultados por hipótesis en el notebook:
  - “Evidencia para H1: …”
  - “Evidencia para H2: …”
- Evita generar 20 gráficos sin una pregunta concreta; prioriza 1–3 gráficos por hipótesis con interpretación clara.

## Preguntas de Profundización

Para mejorar el razonamiento, lanza preguntas cortas como:

- “Si este resultado fuera el contrario, ¿qué esperaría ver en los datos?”
- “¿Qué otra explicación alternativa podría producir este patrón?”
- “¿Hay sesgos de selección o cambios en tracking que puedan explicar esto?”

Usa estas preguntas para ayudar al usuario a pensar como un analista senior.

## Formato de Salida Recomendado

Cuando respondas a una petición de análisis, organiza tu respuesta así:

1. **Resumen ejecutivo** – 3–5 frases sobre el problema y la conclusión general.
2. **Hipótesis evaluadas** – lista de H1, H2, H3…
3. **Evidencia por hipótesis** – bullets con resultados clave (números + interpretación).
4. **Conclusión por hipótesis** – marcar cada una como:
   - Soportada / Parcialmente soportada / No soportada / Inconclusa.
5. **Riesgos y limitaciones** – tracking, tamaño de muestra, seasonality, etc.
6. **Recomendaciones accionables** – qué hacer y qué análisis complementar.

Mantén las respuestas concisas pero claras; prioriza la lógica y las decisiones sobre el detalle técnico excesivo.

