# Verificación inicial de SynapSeed

Primera corrida de las herramientas que trae el propio sistema, hecha el 2026-11-24 sobre el commit `ec14b12`, sin ambiente levantado (sin base de datos, Redis ni servicios externos). Estos hallazgos todavía no son reportes formales de defecto: falta pasarlos al formato de defectos con severidad, prioridad y caso de prueba asociado.

## Resultados

| Verificación | Comando | Resultado |
|--------------|---------|-----------|
| Pruebas backend tal como están | `python -m pytest` | No ejecuta: 2 archivos fallan en la recolección |
| Pruebas backend ignorando deprecaciones | `python -m pytest -o "filterwarnings=ignore::DeprecationWarning"` | 18 de 22 pasan |
| Cobertura backend | `--cov=app` | 53%, bajo el umbral de 80% que fija el propio `pyproject.toml` |
| Lint backend | `ruff check app tests` | 169 hallazgos, 146 corregibles automáticamente |
| Formato backend | `ruff format --check app tests` | 36 de 80 archivos no cumplen el formato |
| Pruebas frontend | `npm test` | 3 de 4 pasan; solo existe 1 archivo de pruebas |
| Lint frontend | `npm run lint` | Sin hallazgos |
| Tipos frontend | `npm run typecheck` | Sin errores |
| Build frontend | `npm run build` | Compila; bundle principal de 471.61 kB (150.57 kB gzip) |
| Pruebas E2E | `npm run test:e2e` | El script existe, pero no hay pruebas ni configuración de Playwright |

En el backend, las rutas de la API (`app/api/v1/`), el worker de Celery (`app/workers/`) y el seed (`app/db/seed.py`) tienen 0% de cobertura.

## Hallazgos candidatos a defecto

1. **La suite del backend no se ejecuta sin modificar la configuración.** `anyio` no tiene versión fijada; la versión que se instala hoy (4.16.0) emite un `DeprecationWarning` y `pyproject.toml` convierte toda advertencia en error (`filterwarnings = ["error", ...]`). Resultado: `tests/api/v1/test_recommendations.py` y `tests/test_api_endpoints.py` fallan en la recolección.
2. **Prueba del frontend en rojo.** `src/frontend/src/features/wizard/recommendationMapper.test.ts:73` espera `compatibility: "Excelente"` y el código devuelve `"Sí"`. Hay que determinar si el defecto está en el código o en la prueba.
3. **Código de respuesta no esperado en recomendaciones.** `src/backend/tests/api/v1/test_recommendations.py:117` acepta 200, 401, 404, 422 o 500, y el sistema responde 503 sin base de datos.
4. **Health check degradado.** `GET /api/v1/health` responde `status: "degraded"` cuando la base de datos no está disponible, y `tests/test_api_endpoints.py:13` espera `"ok"`. Hay que revisar si el comportamiento esperado está definido en los requisitos.
5. **Build del frontend no reproducible.** El frontend no versiona `package-lock.json`, así que cada `npm install` puede resolver versiones distintas.

## Hallazgos al levantar el sistema con Docker

Encontrados el 2026-11-24 al ejecutar `docker compose up` con la configuración original de SynapSeed (Supabase, OpenRouter y Gemini).

6. **El worker de Celery no arranca y el backend no puede encolar recomendaciones.** `kombu` no tiene versión fijada; pip instala kombu 5.7.0, que exige `redis>=6.1.0`, mientras `pyproject.toml` fija `redis==5.2.1`. El worker se reinicia en bucle con `kombu.exceptions.VersionMismatch`, y `POST /api/v1/recommendations/request` responde 500. Contorno para pruebas: `env/docker-compose.kombu-fix.yml`.
7. **Modelo de embeddings retirado.** `app/config.py` usa `models/text-embedding-004`, que ya no aparece en la lista de modelos de la API de Gemini (hoy ofrece `gemini-embedding-001`, `gemini-embedding-2` y `gemini-embedding-2-preview`). El seed lo detecta y carga los productos sin embeddings.
8. **Comentario inconsistente con la configuración.** El comentario de `get_embedding()` en `app/db/seed.py` dice "gemini-embedding-001, 768 dims", pero el modelo configurado es `text-embedding-004`.
9. **Recorte silencioso de embeddings.** `get_embedding()` recorta o rellena con ceros cualquier embedding que no mida 768, sin registrar ninguna advertencia.
10. **Alternativa local documentada pero no soportada.** `.env.example` ofrece una base de datos Postgres local en `localhost:5432`, pero `docker-compose.yml` no define ningún servicio de Postgres.

## Hallazgos de la prueba de humo de la API

Prueba de humo del 2026-11-24 contra `http://localhost:8000/api/v1`, con un usuario sintético. Pasan: health, los 8 catálogos, búsqueda de productos, registro, inicio de sesión (válido e inválido), `GET /users/me` con y sin token, CRUD de la zona propia, rechazo con 404 de las zonas de otros usuarios (ids 1 a 9), validación 422 de una solicitud de recomendación inválida, frontend en `:5173` y CORS que rechaza orígenes ajenos.

11. **Errores intermitentes de base de datos con el pooler de Supabase.** Con el Transaction pooler (puerto 6543), backend y worker fallan con `asyncpg.exceptions.DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_N__" already exists`. `app/db/session.py` desactiva la caché de sentencias (`statement_cache_size=0`), pero no define nombres únicos para las sentencias preparadas, así que PgBouncer las reutiliza entre conexiones. El pipeline de recomendación falla en su primera consulta.
12. **Una recomendación que falla queda en PENDING para siempre.** Cuando la tarea del worker lanza una excepción, la recomendación no pasa a `FAILED` ni guarda `error_message`. La recomendación 75 quedó en `PENDING` tras el error del hallazgo 11; el frontend esperaría indefinidamente.
13. **Registro huérfano si falla el encolado.** `POST /recommendations/request` crea la recomendación en la base antes de encolar la tarea; si el encolado falla (hallazgo 6) responde 500, pero la fila queda en `PENDING` (recomendación 74).
14. **La respuesta 500 expone el traceback completo.** El cuerpo de la respuesta de error de `POST /recommendations/request` incluye el traceback de Python con rutas internas del servidor. Probablemente por `DEBUG=true`, el valor por defecto del `.env.example`.
15. **Zonas sin validación de entrada.** `POST` y `PUT /api/v1/zones` reciben `payload: dict` en lugar de un schema de Pydantic. Se aceptó con 201 una zona con nombre `<script>alert(1)</script>` y campos no definidos (`extra_field`, `user_id`). Falta verificar si `user_id` del cuerpo se ignora y si el nombre se escapa en el frontend.
16. **Humedad inválida reemplazada en silencio.** `RecommendationRequest.coerce_humidity` convierte cualquier texto no reconocido en `60.0` en vez de rechazarlo con 422.
17. **Esquemas de usuario duplicados con reglas distintas.** `app/schemas/auth.py` (`RegisterRequest`: cédula mínimo 5, contraseña mínimo 6) y `app/schemas/user.py` (`UserRegister`: cédula mínimo 9, contraseña mínimo 8) definen el registro con reglas diferentes; el router usa el segundo.
18. **Columna documentada que no existe.** La Spec validada y el DBML incluyen `recommendations.processing_time_ms`, pero la tabla no tiene esa columna.
19. **Recomendaciones antiguas atascadas.** La base contiene 7 recomendaciones en `PENDING` y 2 en `PROCESSING` creadas en junio de 2026, nunca resueltas: no hay mecanismo de expiración ni limpieza.
20. **Health check incompleto.** `GET /api/v1/health` responde `status: "ok"` con `redis: "pending"`, es decir, sin haber verificado Redis.

## Flujo de recomendación completo

Con `DATABASE_URL` en el Session pooler (puerto 5432) y `env/docker-compose.kombu-fix.yml`, la recomendación 76 (tomate en floración, áfidos en hojas jóvenes, suelo franco, humedad media, 24 °C, presupuesto 15000 por litro) terminó en `COMPLETED` con 3 productos, proveedores (`GET /recommendations/{id}/providers` devuelve 3) e historial.

21. **Tiempo de respuesta fuera de lo documentado.** La recomendación tardó 1 min 43 s (103 s de creación a completado). El README del MVP declara entre 10 y 50 s.
22. **Pertinencia dudosa de los productos recomendados.** Para áfidos en tomate, el sistema devolvió Crypmont, Californicus System y Neocal. Por su nombre e ingrediente activo, parecen agentes de control biológico orientados a cochinillas (Crypmont) y a ácaros (Neoseiulus californicus), no a áfidos. Requiere validación de una persona con criterio agronómico antes de reportarlo como defecto.
23. **Catálogo incompleto en los productos recomendados.** Los 3 productos tienen `banda_toxicologica` y `cultivo_objetivo` vacíos, y Crypmont no tiene `ingrediente_activo`. La tabla comparativa del resultado no puede mostrar toxicidad, un dato de seguridad para quien aplica el producto.
24. **Nombres de columnas distintos a los documentados.** La Spec validada describe `Product` con columnas en inglés (`name`, `active_ingredient`, `toxicity_band`); el modelo real usa nombres en español (`nombre_comercial`, `ingrediente_activo`, `banda_toxicologica`).

## Hallazgos al construir el ambiente QA local

Encontrados el 2026-11-26 al levantar SynapSeed desde cero con Postgres local (`env/docker-compose.qa.yml`).

25. **El seed depende de archivos que no están en el repo.** `app/db/seed.py` carga productos y LMR desde `output/plaguicidas.csv`, `output/fertilizantes.csv` y `output/lmr.csv`, pero la carpeta `output/` no existe en el repositorio. En una instalación nueva el seed termina "exitosamente" sin cargar ningún producto, y el asistente no puede recomendar nada. Afecta la instalabilidad (Flexibilidad) y la reproducibilidad del sistema.
26. **Las migraciones y los modelos definen enums incompatibles: una instalación desde cero no funciona.** `alembic/versions/001_initial_schema.py` crea los tipos `product_category`, `product_status`, `toxic_band`, `recommendation_status`, `audit_action` y `regulationtype` con etiquetas en minúscula (`pending`, `plaguicida`). Los modelos usan `SQLEnum` sin `values_callable`, así que escriben el nombre en mayúscula (`PENDING`, `PLAGUICIDA`). En una base creada solo con `alembic upgrade head`, el seed falla con `invalid input value for enum regulationtype: "DECRETO"`, y lo mismo pasaría al crear productos, recomendaciones o registros de auditoría. La base de Supabase tiene las etiquetas en mayúscula, así que no se creó con estas migraciones. Contorno para el ambiente QA: `env/align_enums.py`.
27. **Restablecimiento de contraseña sin verificación en modo local.** `POST /api/v1/auth/reset-password` es público y, cuando Supabase no está configurado (`_local_auth_enabled()`), cambia la contraseña de cualquier cuenta con solo conocer su cédula y su correo, sin token ni confirmación. No aparece en la Spec. Confirmado como toma de cuenta en la verificación SEC-01 (ver la sección de seguridad).

Matiz sobre el hallazgo 12: en el ambiente local, una falla del LLM (500 inducido) sí deja la recomendación en `FAILED` con `error_message` en unos 17 s. La recomendación se queda en `PENDING` cuando la excepción ocurre antes, en el acceso a la base de datos.

## Hallazgos de las verificaciones de seguridad

Encontrados el 2026-11-26 con las verificaciones SEC-01 a SEC-06 (`tests/auth-seguridad/security/`) contra el ambiente QA local.

28. **El stream de progreso no exige autenticación.** `GET /api/v1/recommendations/stream/{ticket_id}` no usa `get_current_user`: sin token responde 200 con el estado, el paso actual y el mensaje de error de la recomendación. El `ticket_id` es un UUID, así que adivinarlo es difícil, pero es el único endpoint con datos de una persona que no pide token.
29. **Los tokens inválidos responden 503 con detalles de configuración.** En modo de autenticación local, un token con firma alterada, `alg: none`, secreto ajeno o formato inválido no da acceso, pero `resolve_user_from_token` lo reenvía a la validación de Supabase y la respuesta es 503 "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configurados", en lugar de 401. Revela la configuración interna y confunde al cliente, que interpreta una caída del servicio.
30. **El login no limita los intentos fallidos.** 30 contraseñas incorrectas seguidas contra la misma cédula responden 401 a unos 4 intentos por segundo, sin espera, bloqueo ni 429, y luego la contraseña correcta sigue funcionando. No hay ningún limitador de peticiones en el backend.

Confirmaciones en el ambiente QA local:

- **Hallazgo 14:** se reproduce sin depender de Supabase. `POST /zones` con `name: 123` responde 500 con el traceback completo. La causa es `debug: bool = True` por defecto en `app/config.py`, y `.env.example` también trae `DEBUG=true`.
- **Hallazgo 15:** el `user_id` del cuerpo se ignora, porque `clean_payload` copia solo los campos conocidos. Los campos desconocidos se aceptan con 201 sin aviso, y los tipos no se validan: un nombre numérico o una latitud de texto terminan en 500. El nombre `<script>` se guarda tal cual, pero el frontend no inserta HTML sin escapar (no usa `dangerouslySetInnerHTML` ni `innerHTML`).
- **Hallazgo 27:** confirmado como toma de cuenta. Un tercero sin sesión cambió la contraseña de otra persona con solo su cédula y su correo, y la contraseña original dejó de funcionar. La pantalla de login ofrece este flujo (`LoginPage.tsx`).

## Hallazgos de las pruebas de carga

Encontrados el 2026-11-26 con k6 (`tests/auth-seguridad/performance/`) contra el ambiente QA local. Los resultados completos están en `reports/k6/`.

31. **El login bloquea todo el backend mientras calcula bcrypt.** `authenticate_user` y `register_user` son funciones `async`, pero llaman a `verify_password` y `get_password_hash` (passlib con bcrypt) de forma síncrona, sin `run_in_threadpool`. Cada login ocupa el event loop unos 240 ms, y durante ese tiempo el proceso no atiende ninguna otra petición. Evidencia en `reports/k6/perf-01-diagnostico.txt`: el catálogo de cultivos, que no usa bcrypt ni token, pasa de una mediana de 10.4 ms a 2403 ms mientras hay 10 logins simultáneos, casi exactamente 10 x 250 ms. En PERF-01, con 20 usuarios, el p95 del login fue 5.12 s y el de las lecturas 2.06 s. Afecta el modo de autenticación local y el respaldo con hash local; en modo Supabase el login es una llamada HTTP asíncrona. El `docker-compose.yml` de SynapSeed levanta un solo proceso de uvicorn, igual que el ambiente QA; el `Dockerfile` de producción usa 2 workers de gunicorn, lo que reduce el efecto a la mitad pero no lo elimina.

32. **El pipeline atiende una recomendación a la vez, así que la meta de 10 a 50 s solo se cumple con una persona.** La Spec (línea 201) y `Dockerfile.worker` fijan el worker de Celery con `--concurrency=1`. En PERF-02, con el LLM falso a 3 s por llamada, una recomendación sola tarda 11 s, pero 20 solicitudes de 10 personas terminan con p95 de 94 s y la última a los 95 s: cada una espera a las anteriores. Con el LLM real (103 s medidos en el hallazgo 21), la décima persona en pedir esperaría más de 15 minutos. Es una contradicción entre dos decisiones de la Spec, la concurrencia de 1 y el tiempo de 10 a 50 s, más que un error de código. Con carga creciente (2026-11-27) el p95 fue de 19.4 s con 2 personas, 49.0 s con 5 y 93 s con 10. Evidencia: `reports/k6/perf-02-delay-3000.txt` y `reports/k6/perf-02-rampa-delay-3000.txt`.

## Hallazgos de la revisión de la configuración de seguridad

Encontrado el 2026-11-27 al escribir las pruebas unitarias de `app/core/security.py` y verificado con un backend temporal en el ambiente QA local.

33. **El backend acepta un secreto JWT público y con él cualquiera fabrica tokens válidos.** `app/config.py` define `jwt_secret` con el valor por defecto `"change-me-in-production"`, y `.env.example` publica otro valor fijo. Nada impide arrancar en producción con cualquiera de los dos. Además, `resolve_user_from_token` intenta primero validar el token como JWT local en cualquier modo, también con Supabase configurado. Con un backend levantado con el secreto de `.env.example`, un token fabricado para el id 1, sin contraseña ni login, dio acceso al perfil y a las zonas de esa persona. Evidencia: `reports/manual/def-jwt-secreto-publico.txt`.

## Hallazgos formalizados como defectos

Los hallazgos se formalizan en `docs/defectos.md`, con severidad, prioridad, pasos para reproducir y evidencia. Hallazgos de la Persona A:

| Hallazgo | Defecto | Severidad |
|----------|---------|-----------|
| 27 | DEF-A01 | Crítica |
| 14 | DEF-A02 | Alta |
| 30 | DEF-A03 | Alta |
| 33 | DEF-A13 | Alta |
| 26 | DEF-A04 | Alta |
| 25 | DEF-A05 | Alta |
| 31 | DEF-A06 | Alta |
| 32 | DEF-A07 | Alta |
| 15 | DEF-A08 | Media |
| 20 | DEF-A09 | Media |
| 28 | DEF-A10 | Media |
| 29 | DEF-A11 | Baja |
| 17 | DEF-A12 | Baja |

## Datos existentes en la base

La base de Supabase no está vacía: trae 7 usuarios, 9 zonas, 55 recomendaciones y 3672 registros de auditoría de junio de 2026, además del catálogo cargado por el seed (13401 productos, 565 distribuidores, 8528 LMR, 5 regulaciones, ninguno con embeddings). Las reglas del proyecto exigen datos sintéticos; esos usuarios pueden contener datos personales reales y no deben usarse en las pruebas ni copiarse a la evidencia.

Las pruebas `test_login_endpoint_returns_token` y `test_catalogs_endpoint_returns_seed_data` fallan por falta de base de datos (conexión rechazada), no por un defecto del código.
