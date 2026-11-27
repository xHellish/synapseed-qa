# Resultados de las pruebas de carga

Responsable: Persona A. Requerimiento: RNF-04 (y RNF-03, criterio 1). Umbrales declarados antes de correr, en `docs/plan-calidad.md`. Solo contra el ambiente QA local, con el LLM falso y usuarios sintéticos (cédulas que empiezan en 7).

Ejecución: 2026-11-26, k6 1.0.0 en Docker (`run_k6.sh`), en una sola máquina con Docker dentro de WSL. El backend corre un solo proceso de uvicorn, como el `docker-compose.yml` de SynapSeed.

## Resumen

| Escenario | Corrida | Umbrales cumplidos | Evidencia |
|-----------|---------|--------------------|-----------|
| PERF-01 Autenticación y lectura | 20 usuarios virtuales | 2 de 4 | `reports/k6/perf-01.txt`, `perf-01.json`, `perf-01-diagnostico.txt` |
| PERF-02 Recomendaciones simultáneas | LLM sin latencia | 3 de 3 | `reports/k6/perf-02-delay-0.txt`, `.json` |
| PERF-02 Recomendaciones simultáneas | LLM con 3 s por llamada | 2 de 3 | `reports/k6/perf-02-delay-3000.txt`, `.json` |

## PERF-01 Autenticación y lectura

Rampa de 30 s hasta 20 usuarios virtuales, 1 min sostenido y 15 s de bajada: 280 iteraciones y 1140 peticiones.

| Métrica | Umbral | Obtenido | Cumple |
|---------|--------|----------|--------|
| Peticiones fallidas | Menos de 1% | 0% (0 de 1140) | Sí |
| p95 del login | Menos de 1000 ms | 5120 ms | **No** |
| p95 de las lecturas | Menos de 500 ms | 2060 ms (mediana 318 ms) | **No** |
| Verificaciones de contenido | Más de 99% | 100% (1960 de 1960) | Sí |

El sistema responde bien a todas las peticiones, pero lento. Un login aislado tarda unos 240 ms y una lectura unos 5 ms. El diagnóstico (`event_loop_check.py`) muestra la causa:

| Medición | Resultado |
|----------|-----------|
| Catálogo de cultivos, sin carga | Mediana 10.4 ms |
| Un login aislado | 250 ms |
| Catálogo durante 10 logins simultáneos | Mediana 2403 ms |

El catálogo no usa bcrypt ni token, y aun así espera casi 10 x 250 ms: el bcrypt del login corre de forma síncrona dentro del event loop y frena todas las peticiones del proceso (hallazgo 31).

## PERF-02 Recomendaciones simultáneas

10 usuarios virtuales piden 2 recomendaciones cada uno (20 en total) y consultan el estado cada 2 s.

| Métrica | Umbral | LLM sin latencia | LLM con 3 s por llamada |
|---------|--------|------------------|-------------------------|
| p95 de `POST /recommendations/request` | Menos de 1000 ms | 837 ms, cumple | 704 ms, cumple |
| p95 de solicitud a resultado | 50 s o menos | 5.6 s, cumple | **94 s, no cumple** (mínimo 11 s, máximo 95 s) |
| Recomendaciones en `COMPLETED` | 100% | 100% (20 de 20), cumple | 100% (20 de 20), cumple |

El sistema no pierde ninguna recomendación bajo carga, y la solicitud responde sin esperar al pipeline. Lo que no escala es el tiempo de entrega: el worker procesa una recomendación a la vez (`--concurrency=1`, fijado en la Spec), así que cada solicitud espera a las anteriores. Con 3 s por llamada al LLM, una recomendación sola tarda 11 s, pero la vigésima de la cola tarda 95 s (hallazgo 32).

## Limitaciones

- El LLM es falso: las corridas miden el sistema, no al proveedor. Con OpenRouter una sola recomendación tardó 103 s (hallazgo 21), así que los tiempos reales serían mayores.
- k6 y el sistema comparten la misma máquina, así que una parte de la latencia puede venir de la competencia por CPU. El diagnóstico de bcrypt se hizo con 10 hilos de Python y no depende de k6.
- La configuración de producción del `Dockerfile` usa 2 workers de gunicorn; no se probó porque el compose de SynapSeed levanta la configuración de desarrollo.
