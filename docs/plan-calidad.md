# Plan general de calidad

Responsable: Persona A.

## Ficha de identificación del sistema

| Dato | Valor |
|------|-------|
| Nombre y naturaleza de la aplicación | |
| Tecnologías utilizadas | |
| Población meta | |
| URL o forma de acceso al ambiente de pruebas | |
| Curso y equipo de origen del sistema | |
| Perfiles de persona usuaria disponibles | |
| Cantidad total de requerimientos funcionales | |
| Cantidad total de requerimientos no funcionales | |

## Alcance

Cada exclusión se justifica por riesgo.

| Elemento | Incluye | Excluye y por qué el riesgo es aceptable |
|----------|---------|------------------------------------------|
| Módulos | | |
| Funcionalidades | | |
| Interfaces | | |
| APIs | | |
| Servicios de terceros | | |
| Infraestructura externa | | |
| Sistemas externos integrados | | |

## Características de ISO/IEC 25010:2023

| Característica | Seleccionada | Prioridad | Justificación |
|----------------|--------------|-----------|---------------|
| Adecuación funcional | Sí (obligatoria) | | |
| Eficiencia de desempeño | | | |
| Compatibilidad | | | |
| Capacidad de interacción | | | |
| Fiabilidad | | | |
| Seguridad | Sí (obligatoria) | | |
| Mantenibilidad | Sí (obligatoria) | | |
| Flexibilidad | | | |
| Protección (Safety) | | | |

## Objetivos de calidad

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

## Tipos y niveles de prueba

## Riesgos identificados y su priorización

| ID | Riesgo | Probabilidad | Impacto | Prioridad | Mitigación |
|----|--------|--------------|---------|-----------|------------|

## Métricas e indicadores

Ver `gqm-metricas.md`.

## Criterios de entrada

## Criterios de salida y de aceptación

## Recursos necesarios

## Cronograma

## Roles y responsabilidades

| Persona | Área | Requerimientos | Otros frentes |
|---------|------|----------------|---------------|
| Persona A | Auth y seguridad | RF-01, RF-02, RNF-01, RNF-04 | Ambiente QA local, seguridad, carga, plan de calidad |
| Persona B | Zonas y catálogos | RF-03, RF-04, RNF-02 | Revisión de requisitos, inspección, estáticas, deuda técnica, WCAG, GQM, informe |
| Persona C | Recomendación | RF-05, RF-06, RNF-03, RNF-05 | Playwright, UAT, usabilidad, defectos, matriz |

## Herramientas

| Herramienta | Para qué | Por qué |
|-------------|----------|---------|

## Estrategia de automatización

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué se automatizó? | |
| ¿Qué quedó manual y por qué? | |
| ¿Cómo se ejecuta la suite? | |
| ¿Qué evidencia produce? | |
| ¿Corre en integración continua? | |
