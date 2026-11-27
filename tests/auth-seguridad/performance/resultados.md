# Resultados de las pruebas de carga

Responsable: Ben Farz (Persona A). Requerimiento: RNF-04 (y RNF-03, criterio 1). Umbrales declarados antes de correr, en `docs/plan-calidad.md`. Solo contra el ambiente QA local, con el LLM falso y usuarios sintéticos (cédulas que empiezan en 7).

Ejecución: 2026-11-26 (PERF-01 y la primera versión de PERF-02) y 2026-11-27 (PERF-02 por escalones), k6 1.0.0 en Docker (`run_k6.sh`), en una sola máquina con Docker dentro de WSL. El backend corre un solo proceso de uvicorn, como el `docker-compose.yml` de SynapSeed.

## Resumen

| Escenario | Corrida | Umbrales cumplidos | Evidencia |
|-----------|---------|--------------------|-----------|
| PERF-01 Autenticación y lectura | 20 usuarios virtuales | 2 de 4 | `reports/k6/perf-01.txt`, `perf-01.json`, `perf-01-diagnostico.txt` |
| PERF-02 Recomendaciones simultáneas | Escalones de 2, 5 y 10 usuarios, LLM sin latencia | 6 de 6 | `reports/k6/perf-02-rampa-delay-0.txt`, `.json` |
| PERF-02 Recomendaciones simultáneas | Escalones de 2, 5 y 10 usuarios, LLM con 3 s por llamada | 4 de 6 | `reports/k6/perf-02-rampa-delay-3000.txt`, `.json` |
| PERF-02, primera versión con carga fija | 10 usuarios, sin latencia y con 3 s | 3 de 3 y 2 de 3 | `reports/k6/perf-02-delay-0.*`, `perf-02-delay-3000.*` |

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

Carga creciente en escalones de 2, 5 y 10 usuarios virtuales, 1 min cada uno, ejecutada el 2026-11-27. Cada usuario pide una recomendación, consulta el estado cada 2 s hasta el final y vuelve a pedir. El tiempo de cada recomendación se asigna al escalón activo cuando se pidió.

| Métrica | Umbral | LLM sin latencia | LLM con 3 s por llamada |
|---------|--------|------------------|-------------------------|
| Recomendaciones procesadas | | 456 | 34 |
| p95 de `POST /recommendations/request` | Menos de 1000 ms | 544 ms, cumple | 271 ms, cumple |
| p95 de solicitud a resultado, total | 50 s o menos | 4.9 s, cumple | **92 s, no cumple** |
| p95 con 2 usuarios | 50 s o menos | 2.2 s, cumple | 19.4 s, cumple |
| p95 con 5 usuarios | 50 s o menos | 3.4 s, cumple | 49.0 s, cumple al límite |
| p95 con 10 usuarios | 50 s o menos | 5.1 s, cumple | **93 s, no cumple** |
| Recomendaciones en `COMPLETED` | 100% | 100% (456 de 456), cumple | 100% (34 de 34), cumple |

El sistema no pierde ninguna recomendación bajo carga, y la solicitud responde sin esperar al pipeline. Lo que no escala es el tiempo de entrega. El worker procesa una recomendación a la vez (`--concurrency=1`, fijado en la Spec), así que el tiempo crece casi en proporción a la cantidad de personas: con 3 s por llamada al LLM, una recomendación sola tarda 10.5 s, con 5 personas el p95 roza los 50 s y con 10 los duplica (hallazgo 32). Con el LLM real, que tardó 103 s con una sola persona (hallazgo 21), el umbral no se cumpliría ni siquiera sin carga.

La latencia de 3 s se verificó por el efecto en los tiempos (una recomendación sola: 10.5 s contra 2.1 s sin latencia). El LLM falso se devolvió a 0 ms al terminar.

### Primera versión de PERF-02 (carga fija)

Corrida el 2026-11-26 con 10 usuarios fijos y 2 solicitudes cada uno, antes de pasar a carga creciente. Se conserva como evidencia y coincide con la versión por escalones:

| Métrica | LLM sin latencia | LLM con 3 s por llamada |
|---------|------------------|-------------------------|
| p95 de la solicitud | 837 ms | 704 ms |
| p95 de solicitud a resultado | 5.6 s | 94 s |
| Recomendaciones en `COMPLETED` | 20 de 20 | 20 de 20 |

## Limitaciones

- El LLM es falso: las corridas miden el sistema, no al proveedor. Con OpenRouter una sola recomendación tardó 103 s (hallazgo 21), así que los tiempos reales serían mayores.
- k6 y el sistema comparten la misma máquina, así que una parte de la latencia puede venir de la competencia por CPU. El diagnóstico de bcrypt se hizo con 10 hilos de Python y no depende de k6.
- La configuración de producción del `Dockerfile` usa 2 workers de gunicorn; no se probó porque el compose de SynapSeed levanta la configuración de desarrollo.
