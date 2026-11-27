# Plan general de calidad

Responsable: Ben Farz (Persona A). Versión del 2026-11-27, sobre SynapSeed en el commit `ec14b12`.

Este plan es el eje de la auditoría: las características seleccionadas definen los objetivos, los objetivos definen las métricas (`gqm-metricas.md`) y las pruebas, y los resultados se reportan por característica en el informe final.

## Ficha de identificación del sistema

| Dato | Valor |
|------|-------|
| Nombre y naturaleza de la aplicación | SynapSeed: aplicación web que recomienda agroquímicos a personas agricultoras costarricenses según cultivo, etapa, condiciones de la zona, problema y presupuesto. Un pipeline de 4 agentes de IA analiza el caso, busca productos, los valida contra las regulaciones del SFE y entrega exactamente 3 recomendaciones con tabla comparativa y proveedores. Solo informa: no vende ni procesa pagos |
| Tecnologías utilizadas | Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic 2, Celery con Redis 7, LangGraph con OpenRouter. Datos: Postgres 16 con pgvector (Supabase). Autenticación: Supabase Auth o JWT local con bcrypt. Frontend: React 19, Vite, TypeScript, TailwindCSS, Zustand, React Query, Zod. Infraestructura: Docker Compose |
| Población meta | Personas agricultoras costarricenses de pequeña y mediana escala, sin formación técnica en agroquímicos, que hoy dependen de lo que les recomienda el distribuidor |
| URL o forma de acceso al ambiente de pruebas | Ambiente QA local, levantado con `docker compose -f env/docker-compose.qa.yml up -d --build` (README, paso 5): interfaz en http://127.0.0.1:5173, API en http://127.0.0.1:8000/api/v1 y documentación en http://127.0.0.1:8000/docs. La configuración original con Supabase y OpenRouter (README, paso 4) se usa solo para exploración funcional |
| Curso y equipo de origen del sistema | Diseño de Software, Instituto Tecnológico de Costa Rica, Caso #2. Equipo SynapSeed; repositorio `github.com/xHellish/synapseed`, auditado en el commit `ec14b12` |
| Perfiles de persona usuaria disponibles | Un solo perfil autenticado: persona agricultora registrada. Sin sesión solo se accede al registro, al inicio de sesión y a la recuperación de contraseña. No existe perfil de administración |
| Cantidad total de requerimientos funcionales | 6 (RF-01 a RF-06, en `requisitos.md`) |
| Cantidad total de requerimientos no funcionales | 5 (RNF-01 a RNF-05, en `requisitos.md`) |

SynapSeed no traía una lista numerada de requerimientos. El equipo los reconstruyó a partir de la Spec validada, el alcance del MVP y la API real, y registró las contradicciones entre esas fuentes para la revisión de requerimientos.

## Alcance

### Lo que incluye

| Elemento | Incluye |
|----------|---------|
| Módulos auditados | Backend: routers `auth`, `users`, `zones`, `catalogs`, `recommendations` y `health`; servicios; repositorios; modelos y migraciones; seed. Worker de Celery con el pipeline de 4 agentes. Frontend: registro e inicio de sesión, asistente de recomendación, resultado con tabla comparativa, proveedores e historial |
| Funcionalidades evaluadas | RF-01 a RF-06: registro, inicio de sesión, zonas de cultivo, catálogos del asistente, solicitud de recomendación, proveedores e historial |
| Interfaces incluidas | Interfaz web en Chromium de escritorio; API REST `/api/v1`; stream SSE de progreso |
| APIs incluidas | `/auth/register`, `/auth/login`, `/auth/reset-password`, `/users/me`, `/zones` (CRUD), `/catalogs/*`, `/recommendations/request`, `/recommendations/{id}`, `/recommendations/{id}/providers`, `/recommendations/history`, `/recommendations/stream/{ticket_id}`, `/health` |

### Lo que excluye y por qué el riesgo es aceptable

| Elemento excluido | Justificación por riesgo |
|-------------------|--------------------------|
| Edición del perfil y cambio de contraseña (`PUT /users/me`, `PUT /users/me/password`) como funcionalidad | El MVP declara el perfil de solo lectura, así que no forman parte de los requerimientos auditados. Solo modifican datos de la propia cuenta, detrás de una autenticación que sí se verifica (SEC-02 y SEC-03), así que su falla no expone ni borra datos de otras personas. `reset-password` sí se incluye, porque es público y permite actuar sobre cuentas ajenas |
| Servicios de terceros: OpenRouter, Google Gemini y Supabase | Las reglas del curso prohíben pruebas de seguridad y de carga contra terceros, y usarlos tiene costo y datos reales. Se reemplazan por un LLM falso y autenticación local en el ambiente QA, que ejercitan el mismo código de SynapSeed. Lo que se pierde es la calidad de las respuestas del LLM real; ese riesgo se cubre con corridas funcionales exploratorias en la configuración original (hallazgos 21 a 23), no con pruebas automatizadas |
| Infraestructura externa: hosting y pooler de Supabase | SynapSeed no tiene un despliegue público que auditar. El comportamiento del pooler se observó y quedó registrado (hallazgo 11), pero no se prueba de forma sistemática porque depende de la configuración del proveedor y no del código |
| Sistemas externos integrados: fuentes de datos del SFE y MAG | El sistema consume una copia cargada por el seed; no se integra en línea con ellas. Se audita cómo el sistema usa las regulaciones cargadas (validador legal, RNF-05), no la exactitud de la fuente oficial |
| Navegadores distintos de Chromium y dispositivos móviles | Compatibilidad no es una característica seleccionada. El frontend usa React y Vite estándar sin APIs específicas de un navegador. El riesgo conocido en móvil, la tabla comparativa que se corta, ya lo reportó el UX testing original del equipo de SynapSeed y se revisa en la prueba de usabilidad |
| Scripts que generaron los CSV del catálogo | No están en el repositorio (hallazgo 25), así que no hay código que auditar. Su ausencia se registra como defecto (DEF-A05) |

## Características de ISO/IEC 25010:2023

Se seleccionan las 5 características mínimas: las 3 obligatorias y 2 elegidas por el riesgo de este sistema en particular.

| Característica | Seleccionada | Prioridad | Justificación |
|----------------|--------------|-----------|---------------|
| Adecuación funcional | Sí (obligatoria) | Alta | Una recomendación incorrecta o no pertinente lleva a aplicar un químico equivocado, con costo para la persona y riesgo para el cultivo. Incluye la corrección y pertinencia de lo recomendado: que no aparezcan productos prohibidos y que se muestren la toxicidad y el intervalo de seguridad (RNF-05) |
| Seguridad | Sí (obligatoria) | Alta | El sistema guarda cédula, nombre, correo y teléfono de personas reales, y la cuenta es la puerta a su historial. Una falla de autenticación o de control de acceso expone datos personales o permite actuar en nombre de otra persona |
| Mantenibilidad | Sí (obligatoria) | Media | Es un proyecto académico que seguirá evolucionando. La verificación inicial encontró cobertura de 53%, 169 hallazgos de Ruff y una suite que no corre sin modificar la configuración: cada cambio futuro tiene alto riesgo de romper algo sin que nadie lo note |
| Eficiencia de desempeño | Sí | Media | El MVP promete una recomendación en 10 a 50 s, y la medición con el LLM real dio 103 s. Una persona que espera demasiado abandona el asistente y vuelve a preguntarle al distribuidor, que es justo el problema que SynapSeed quiere resolver |
| Fiabilidad | Sí | Alta | El pipeline es asíncrono y depende de un LLM externo que puede fallar o tardar. Ya se observaron recomendaciones atascadas para siempre en `PENDING` (hallazgos 12, 13 y 19): la persona queda esperando una respuesta que nunca llega |
| Compatibilidad | No | | El sistema no intercambia datos con otros sistemas salvo con servicios de terceros fuera de alcance, y tiene una sola interfaz web estándar |
| Capacidad de interacción | No | | No se mide con métricas propias. La prueba de usabilidad con 3 personas y la revisión WCAG 2.2 AA de 3 pantallas se hacen igual porque son obligatorias, y sus problemas se registran como defectos |
| Flexibilidad | No | | El sistema no se distribuye para que terceros lo instalen. Los problemas de instalación que se encontraron al montar el ambiente QA (DEF-A04 y DEF-A05) se registran como defectos, pero no se definen métricas de instalabilidad |
| Protección (Safety) | No | | La decisión de aplicar un producto la toma la persona, con la etiqueta registrada en el SFE, y el sistema no controla equipos ni procesos físicos. El riesgo de recomendar algo peligroso no se ignora: se cubre dentro de Adecuación funcional con RNF-05 |

## Objetivos de calidad

Cada objetivo se mide con las métricas de `gqm-metricas.md`. Los umbrales de cada métrica se fijan en su ficha antes de ejecutar.

| ID | Característica | Objetivo | Requerimientos | Responsable |
|----|----------------|----------|----------------|-------------|
| OC-1 | Adecuación funcional | Verificar que cada requerimiento funcional se cumple en su camino feliz, sus errores y sus fronteras, y que lo recomendado es correcto y pertinente | RF-01 a RF-06, RNF-05 | Ben Farz, Kevin Alanis, Josué Calderón |
| OC-2 | Seguridad | Verificar que solo la dueña de una cuenta accede a ella y a sus datos, que las entradas se validan y que los errores no exponen detalles internos | RNF-01 | Ben Farz |
| OC-3 | Mantenibilidad | Medir qué tan fácil es analizar, probar y modificar el código, y estimar la deuda técnica | RNF-02 | Kevin Alanis |
| OC-4 | Eficiencia de desempeño | Verificar que el sistema responde dentro de los tiempos documentados con varias personas a la vez | RNF-04 | Ben Farz |
| OC-5 | Fiabilidad | Verificar que toda recomendación termina, que las fallas del LLM se manejan y que el sistema se recupera | RNF-03 | Josué Calderón |

### Umbrales de desempeño (RNF-04)

Declarados el 2026-11-26, antes de la primera corrida de k6. La documentación de SynapSeed solo fija que el pipeline entrega en 10 a 50 s (MVP 4.1) y que la solicitud responde sin esperar al pipeline. El resto se fija aquí con estos criterios:

- La población meta es un piloto regional de personas agricultoras: pocas decenas de sesiones a la vez, no miles.
- La lectura de datos debe sentirse inmediata: menos de 0.5 s, la referencia habitual para respuestas de API interactivas.
- El login usa bcrypt, que es lento a propósito, así que tiene más margen.

Los escenarios corren en el ambiente QA local con el LLM falso, así que miden la capacidad del sistema y no la del proveedor del LLM.

| Escenario | Carga | Métrica | Umbral | Fuente |
|-----------|-------|---------|--------|--------|
| PERF-01 Autenticación y lectura (`auth_read_load.js`) | Rampa hasta 20 usuarios virtuales, 1 min sostenido. Cada iteración: login, perfil, catálogo de cultivos y zonas, con 1 s de pausa | Peticiones fallidas | Menos de 1% | Plan |
| | | p95 del login | Menos de 1000 ms | Plan |
| | | p95 de las lecturas (perfil, catálogo, zonas) | Menos de 500 ms | Plan |
| | | Verificaciones de contenido que pasan | Más de 99% | Plan |
| PERF-02 Recomendaciones simultáneas (`recommendation_load.js`) | 10 usuarios virtuales que piden 2 recomendaciones cada uno (20 en total) y consultan el estado cada 2 s hasta el final | p95 de `POST /recommendations/request` | Menos de 1000 ms | RNF-04, criterio 2 |
| | | p95 del tiempo de solicitud a resultado | 50 s o menos | RNF-04, criterio 1 (MVP: 10 a 50 s) |
| | | Recomendaciones que terminan en `COMPLETED` | 100% | RNF-03, criterio 1 |

PERF-02 se corre dos veces:

- **LLM sin latencia** (`FAKE_LLM_DELAY_MS=0`): mide el costo propio del sistema, es decir, la cola, la base de datos y el pipeline.
- **LLM con 3 s por llamada** (`FAKE_LLM_DELAY_MS=3000`): se acerca a un proveedor real, sin llegar a los 103 s medidos con OpenRouter (hallazgo 21).

Los umbrales son los mismos en las dos corridas.

## Estrategia de pruebas

La estrategia se basa en riesgo: se prueba primero y con más profundidad lo que más daño causa si falla (ver la tabla de riesgos).

1. **Versión fija.** SynapSeed se audita como submódulo fijado en `ec14b12`; nadie modifica su código. Los contornos necesarios para probar (kombu, enums, seed) viven en `env/` y se documentan.
2. **Ambiente propio.** Las pruebas de seguridad, carga y fallos inducidos corren solo en el ambiente QA local, con datos sintéticos y un LLM falso que permite inducir errores y latencia de forma reproducible.
3. **Requerimientos verificables primero.** Los resultados esperados salen de los criterios de aceptación de `requisitos.md` y se escriben antes de ejecutar. Donde la documentación no define un valor, se declara la fuente (código o estándar) en el caso.
4. **Estáticas antes que dinámicas.** La revisión de requerimientos, la inspección de código y el análisis de Ruff y SonarQube orientan dónde buscar defectos en las pruebas dinámicas.
5. **Todos los niveles por área.** Cada integrante cubre sus requerimientos en unitarias, integración, sistema y aceptación, y suma los tipos no funcionales que le tocan.
6. **Evidencia guardada.** Cada ejecución deja un archivo en `reports/`. Un caso sin evidencia guardada no se da por ejecutado.
7. **Defectos conocidos visibles.** Una prueba que confirma un defecto queda como `xfail` estricto con el ID del defecto, así la suite sigue siendo útil para detectar regresiones.

## Tipos y niveles de prueba

| Nivel o tipo | Qué se prueba | Contra qué se compara | Herramienta | Dónde |
|--------------|---------------|-----------------------|-------------|-------|
| Estática: revisión de requerimientos | Ambigüedad, completitud, consistencia, trazabilidad y verificabilidad | ISO/IEC/IEEE 29148:2018 | Revisión manual | `revision-requisitos.md` |
| Estática: inspección de código | Legibilidad, duplicación, complejidad, convenciones, código muerto | Convenciones del propio proyecto | Inspección formal con roles | `inspeccion-formal.md` |
| Estática: mantenibilidad y deuda técnica | Complejidad, duplicación, smells, dependencias | Umbrales de `gqm-metricas.md` | Ruff, SonarQube, ESLint | `deuda-tecnica.md`, `reports/ruff`, `reports/sonar` |
| Unitaria | Esquemas, validadores, mapeos y nodos del pipeline aislados | Diseño detallado | pytest con cobertura | `tests/<área>/unit` |
| Integración | API con base de datos, API con cola, worker con LLM, verificando el efecto de lado | Arquitectura y contratos | pytest contra el ambiente QA, consultas a la base | `tests/<área>/integration` |
| API | Contratos de los endpoints | Requerimientos y Spec | Postman CLI | `tests/<área>/api` |
| Sistema (E2E) | La aplicación completa por su interfaz | Requerimientos | Playwright | `tests/<área>/e2e` |
| Seguridad | Control de acceso, tokens, validación, errores, fuerza bruta | RNF-01 y OWASP Top 10 | pytest dirigido, OWASP ZAP en modo pasivo | `tests/auth-seguridad/security` |
| Rendimiento y carga | Tiempo de respuesta y capacidad con carga | Umbrales declarados en este plan | k6 | `tests/auth-seguridad/performance` |
| Fiabilidad | Fallos inducidos del LLM y recuperación | RNF-03 | pytest con el LLM falso | `tests/recomendacion` |
| Aceptación (UAT) | Aptitud para el uso real | Procesos de la persona agricultora | 3 escenarios con al menos 2 personas externas | `uat.md` |
| Usabilidad y accesibilidad | Facilidad de uso y WCAG 2.2 AA | Tareas reales y criterios WCAG | Prueba con 3 personas, axe DevTools, Lighthouse, teclado | `usabilidad.md`, `accesibilidad-wcag.md` |

Playwright se usa solo para pruebas de sistema: para verificar que la API escribe bien en la base se usan pruebas de integración con pytest, que son más rápidas y menos frágiles.

## Riesgos identificados y su priorización

Probabilidad e impacto en escala Alta, Media o Baja. La prioridad combina ambos: Alta si alguno es Alto y el otro no es Bajo. Los riesgos de producto orientan las pruebas; los de proyecto, la forma de trabajar.

| ID | Riesgo | Tipo | Probabilidad | Impacto | Prioridad | Mitigación |
|----|--------|------|--------------|---------|-----------|------------|
| R-01 | Una persona toma o usa la cuenta de otra | Producto | Alta | Alto | Alta | SEC-01, SEC-02, SEC-03 y SEC-06. Se materializó: DEF-A01, DEF-A03 |
| R-02 | Se recomienda un producto prohibido, cancelado o no pertinente | Producto | Media | Alto | Alta | Casos de RF-05 y RNF-05 con productos especiales del seed sintético (`QA-PROHIBIDO-1`, `QA-CANCELADO-1`); revisión de pertinencia con criterio agronómico |
| R-03 | Una recomendación nunca termina y la persona espera sin respuesta | Producto | Alta | Alto | Alta | Fallos inducidos con el LLM falso (RNF-03). Ya observado en los hallazgos 12, 13 y 19 |
| R-04 | Los datos personales quedan expuestos en errores o a otras personas | Producto | Media | Alto | Alta | SEC-03 y SEC-05. Se materializó: DEF-A02, DEF-A10 |
| R-05 | El sistema se vuelve inutilizable cuando varias personas lo usan a la vez | Producto | Media | Medio | Media | PERF-01 y PERF-02 con umbrales previos. Se materializó: DEF-A06, DEF-A07 |
| R-06 | Un cambio futuro rompe funcionalidad sin que la suite lo detecte | Producto | Alta | Medio | Alta | Cobertura, Ruff, SonarQube e inspección; regresión automatizada del equipo QA |
| R-07 | El sistema no se puede instalar ni reproducir desde cero | Producto | Alta | Medio | Alta | Construcción del ambiente QA desde cero. Se materializó: DEF-A04, DEF-A05 y los hallazgos 5 y 6 |
| R-08 | Las pruebas generan costo o dependen de la disponibilidad de terceros | Proyecto | Alta | Medio | Alta | LLM falso y autenticación local; las llaves reales nunca se usan en pruebas automatizadas |
| R-09 | Se usan o publican datos personales reales | Proyecto | Media | Alto | Alta | Solo datos sintéticos; la base de Supabase con 7 usuarios reales no se usa en pruebas ni se copia a la evidencia; se revisa la evidencia antes de publicarla |
| R-10 | Las respuestas del LLM real no son deterministas y los resultados no se pueden repetir | Proyecto | Alta | Medio | Alta | Las pruebas automatizadas usan el LLM falso; las corridas con el LLM real son exploratorias y se reportan como tales |
| R-11 | Falta tiempo: 7 días y 3 personas para todos los tipos de prueba | Proyecto | Alta | Alto | Alta | Reparto por área con un dueño por carpeta, plantillas comunes desde el día 2 y automatización de lo repetitivo |
| R-12 | El ambiente se cae durante las pruebas (WSL apaga la distro y los contenedores) | Proyecto | Media | Bajo | Media | `restart: unless-stopped`, instrucciones en el README y verificación del health antes de cada corrida |

## Métricas e indicadores

Las métricas se derivan con GQM y se especifican con la ficha de ISO/IEC 25023 en `gqm-metricas.md`, al menos una por característica seleccionada. Indicadores que el informe final reporta por característica:

| Característica | Indicadores |
|----------------|-------------|
| Adecuación funcional | Porcentaje de requerimientos con al menos un caso aprobado; casos aprobados, fallidos, bloqueados y no ejecutados por requerimiento |
| Seguridad | Verificaciones de seguridad aprobadas sobre las 6; defectos de seguridad por severidad; porcentaje de endpoints protegidos que rechazan peticiones sin token |
| Mantenibilidad | Cobertura de líneas del backend; hallazgos de Ruff y de SonarQube por tipo; deuda técnica estimada por SonarQube |
| Eficiencia de desempeño | p95 de tiempo de respuesta por escenario contra su umbral; p95 del tiempo de solicitud a resultado |
| Fiabilidad | Porcentaje de recomendaciones que terminan en un estado final; tiempo hasta `FAILED` ante un fallo inducido |

Indicadores generales: defectos por severidad y por característica, y porcentaje de casos automatizados.

## Criterios de entrada

La ejecución de pruebas dinámicas de un área empieza cuando se cumplen todos:

- `requisitos.md` tiene los criterios de aceptación del requerimiento.
- El caso tiene su resultado esperado escrito antes de ejecutar.
- El ambiente QA local está arriba: `GET /api/v1/health` responde 200 y el seed sintético está cargado.
- SynapSeed sigue fijado en `ec14b12` y su carpeta no tiene cambios.
- Para rendimiento, los umbrales están declarados en este plan.
- Para UAT y usabilidad, las personas participantes están confirmadas y las tareas escritas.

## Criterios de salida y de aceptación

**Criterios de salida.** La etapa de pruebas termina cuando:

- Todos los casos planificados están ejecutados o justificados como bloqueados.
- Cada requerimiento funcional y no funcional tiene al menos un caso ejecutado.
- Cada característica seleccionada tiene evidencia y al menos una métrica medida.
- Todos los defectos encontrados están registrados en `defectos.md`.
- La matriz de trazabilidad está completa y la evidencia de cada caso está guardada en `reports/`.

**Criterios de aceptación para la recomendación de liberación.** El informe final emite una de estas tres recomendaciones:

| Recomendación | Condición |
|---------------|-----------|
| Liberar | Ningún defecto Crítico ni Alto abierto, todos los umbrales de RNF-04 cumplidos, cobertura del backend de 80% o más y al menos 90% de los casos de camino feliz aprobados |
| Liberar con condiciones | Ningún defecto Crítico abierto, y los Altos abiertos tienen contorno documentado y plan de corrección |
| No liberar | Al menos un defecto Crítico abierto, o un requerimiento funcional sin ningún caso aprobado |

## Recursos necesarios

| Recurso | Detalle |
|---------|---------|
| Personas | 3 integrantes del equipo auditor durante 7 días. Al menos 2 personas externas para UAT y 3 para usabilidad, sin relación con el desarrollo de SynapSeed |
| Equipo | Una computadora por integrante con Docker (Docker Desktop o Docker dentro de WSL2) capaz de levantar los 6 contenedores del ambiente QA |
| Software | Python 3.12 con uv, Node 22, Docker, Postman CLI y las imágenes de k6, OWASP ZAP y SonarQube (ver Herramientas) |
| Datos | Seed sintético (`env/seed_synthetic.py`): 147 productos inventados, 3 distribuidores y 2 usuarios de prueba; usuarios adicionales creados por las propias pruebas |
| Acceso | Repositorios `synapseed` y `synapseed-qa` en GitHub; la configuración original con Supabase y OpenRouter solo para exploración, con llaves en `synapseed/.env`, que no se versiona |

## Cronograma

| Fecha | Actividad | Responsable | Estado |
|-------|-----------|-------------|--------|
| 2026-11-24 | Verificación inicial, levantamiento con la configuración original y prueba de humo | Ben Farz | Hecho |
| 2026-11-25 | Estructura del repo QA, reparto por área y plantillas | Equipo | Hecho |
| 2026-11-26 | Requerimientos, ambiente QA local, casos y pruebas de RF-01 y RF-02, seguridad y carga | Ben Farz | Hecho |
| 2026-11-27 | Defectos de A y plan de calidad | Ben Farz | Hecho |
| 2026-11-27 a 28 | Revisión de requerimientos, inspección formal, Ruff, SonarQube, GQM y casos de RF-03 y RF-04 | Kevin Alanis | Planificado |
| 2026-11-27 a 28 | Casos de RF-05 y RF-06, fiabilidad, Playwright y defectos de C | Josué Calderón | Planificado |
| 2026-11-28 | OWASP ZAP, Postman y E2E de autenticación | Ben Farz | Planificado |
| 2026-11-28 a 29 | UAT, prueba de usabilidad y revisión WCAG | Josué Calderón y Kevin Alanis | Planificado |
| 2026-11-29 | Matriz de trazabilidad, consolidación de defectos e informe final | Equipo | Planificado |
| 2026-11-30 | Entrega | Equipo | Planificado |

## Roles y responsabilidades

| Persona | Nombre | Área | Requerimientos | Otros frentes |
|---------|--------|------|----------------|---------------|
| Persona A | Ben Farz | Auth y seguridad (`tests/auth-seguridad`) | RF-01, RF-02, RNF-01, RNF-04 | Ambiente QA local, verificaciones de seguridad, carga, plan de calidad |
| Persona B | Kevin Alanis | Zonas y catálogos (`tests/zonas-catalogos`) | RF-03, RF-04, RNF-02 | Revisión de requerimientos, inspección formal (modera), análisis estático, deuda técnica, WCAG, GQM, edición del informe |
| Persona C | Josué Calderón | Recomendación (`tests/recomendacion`) | RF-05, RF-06, RNF-03, RNF-05 | Playwright, UAT, usabilidad, consolidación de defectos y matriz de trazabilidad |

Cada persona registra sus defectos (`DEF-A`, `DEF-B`, `DEF-C`) y figura con su nombre en la columna Responsable de sus casos y de la matriz.

## Herramientas

| Herramienta | Para qué | Por qué |
|-------------|----------|---------|
| pytest y pytest-cov | Pruebas unitarias, de integración, de seguridad y de fiabilidad del backend, con cobertura | Ya es la herramienta del propio SynapSeed, así que se reutiliza su entorno sin agregar dependencias |
| Ruff | Lint y formato del backend | Es el linter que el propio proyecto configura en `pyproject.toml`: se mide contra sus propias reglas |
| SonarQube (Docker) | Mantenibilidad, duplicación, smells y deuda técnica estimada | Da una estimación de deuda comparable y un reporte que se puede anexar |
| ESLint, `tsc` y Vitest | Lint, tipos y pruebas del frontend | Son los del propio frontend |
| Playwright | Pruebas de sistema de punta a punta | Corre sin interfaz y guarda traza y captura de cada fallo como evidencia |
| Postman CLI | Pruebas de los contratos de la API | Colecciones versionadas por área que se corren con un comando |
| k6 (Docker) | Rendimiento y carga | Scripts en JavaScript con umbrales que hacen fallar la corrida si no se cumplen |
| OWASP ZAP (Docker) | Escaneo de seguridad en modo pasivo | Es la herramienta sugerida por el curso y su modo pasivo no ataca el sistema |
| LLM falso (`env/fake_llm`) | Respuestas reproducibles del pipeline y fallos inducidos | Permite probar fiabilidad y carga sin costo ni dependencia de OpenRouter |
| axe DevTools, Lighthouse y teclado | Revisión WCAG 2.2 AA | Combinan la detección automática con lo que solo se ve a mano |
| Docker Compose y WSL2 | Ambiente QA local | El ambiente se levanta igual en las 3 máquinas con dos comandos |

## Estrategia de automatización

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué se automatizó? | Lo que se repite y lo que protege caminos críticos: validaciones de entrada (unitarias), contratos de la API con efecto en la base (integración), las 6 verificaciones de seguridad, los escenarios de carga, los fallos inducidos del pipeline y los flujos principales en la interfaz (Playwright). Las pruebas que confirman un defecto quedan como `xfail` estricto para detectar cuándo se corrige |
| ¿Qué quedó manual y por qué? | La revisión de requerimientos, la inspección de código, la UAT, la prueba de usabilidad, la revisión WCAG con teclado y la pertinencia agronómica de las recomendaciones del LLM real. Requieren criterio humano o se hacen una sola vez, así que automatizarlas costaría más de lo que ahorran. Lo verificado a mano se guarda como texto en `reports/manual/` |
| ¿Cómo se ejecuta la suite? | Desde la raíz del repo, con el ambiente QA arriba: `synapseed\src\backend\.venv\Scripts\python -m pytest` para todo lo de Python, `npx playwright test` desde `tests/` para E2E y `run_k6.sh` para carga. Los comandos completos están en el README, paso 6 |
| ¿Qué evidencia produce? | Por corrida: salida de pytest en texto y JUnit XML (`reports/pytest`), reporte de cobertura (`reports/coverage`), salida y resumen JSON de k6 (`reports/k6`), reporte HTML con traza y captura de cada fallo de Playwright (`reports/e2e`) y reportes de ZAP y SonarQube |
| ¿Corre en integración continua? | No. La suite depende del ambiente Docker de 6 contenedores y del LLM falso; montarlo en un pipeline de CI no cabe en los 7 días del proyecto. Se mitiga con comandos únicos documentados que corren igual en las 3 máquinas |
