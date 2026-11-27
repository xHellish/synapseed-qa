# Registro de defectos

Consolida: Josué Calderón (Persona C). Cada quien registra los defectos que encuentra en su propia sección, con IDs `DEF-A01`, `DEF-B01` o `DEF-C01` según la persona, para que los números no choquen. La severidad la decide quien prueba; la prioridad es una propuesta para quien decide sobre el producto.

Todos los defectos se observaron en el commit `ec14b12` de SynapSeed. Los del ambiente QA local se reproducen con `env/docker-compose.qa.yml` y datos sintéticos.

## Escalas

| Severidad | Criterio |
|-----------|----------|
| Crítica | Compromete cuentas o datos de otras personas, o impide usar el sistema, sin contorno |
| Alta | Falla un requisito de seguridad, rendimiento o una función principal con impacto real, o el contorno no está al alcance de quien usa el sistema |
| Media | Falla parcial con contorno, o un problema que hoy no causa daño pero lo facilita |
| Baja | Impacto mínimo: calidad interna, mensajes o documentación |

| Prioridad | Criterio |
|-----------|----------|
| Alta | Corregir antes de poner el sistema en manos de personas usuarias |
| Media | Corregir en la siguiente versión |
| Baja | Corregir cuando haya capacidad |

## Resumen

| ID | Título | Severidad | Prioridad | Estado | Caso que lo encontró | Responsable |
|----|--------|-----------|-----------|--------|----------------------|-------------|
| DEF-A01 | Restablecimiento de contraseña sin verificación permite tomar cualquier cuenta | Crítica | Alta | Abierto | CP-RNF01-01 (SEC-01) | Ben Farz |
| DEF-A02 | Los errores 500 exponen el traceback y rutas internas | Alta | Alta | Abierto | CP-RNF01-05 (SEC-05) | Ben Farz |
| DEF-A03 | El login no limita los intentos fallidos | Alta | Alta | Abierto | CP-RNF01-06 (SEC-06) | Ben Farz |
| DEF-A04 | Una instalación desde cero falla por enums incompatibles | Alta | Media | Abierto | Construcción del ambiente QA | Ben Farz |
| DEF-A05 | El seed no carga productos porque sus CSV no están en el repo | Alta | Media | Abierto | Construcción del ambiente QA | Ben Farz |
| DEF-A06 | El bcrypt del login bloquea todo el backend | Alta | Media | Abierto | CP-RNF04-01 (PERF-01) | Ben Farz |
| DEF-A07 | Con varias personas, las recomendaciones superan los 50 s documentados | Alta | Media | Abierto | CP-RNF04-02 (PERF-02) | Ben Farz |
| DEF-A08 | Zonas no valida la entrada: acepta campos extra y responde 500 a tipos incorrectos | Media | Media | Abierto | CP-RNF01-04 (SEC-04) | Ben Farz |
| DEF-A09 | El health check responde "ok" con Redis caído | Media | Media | Abierto | Prueba de humo de la API y verificación con Redis detenido | Ben Farz |
| DEF-A10 | El stream de progreso de una recomendación no exige token | Media | Baja | Abierto | CP-RNF01-03 (SEC-03) | Ben Farz |
| DEF-A11 | Un token inválido responde 503 con detalles de configuración | Baja | Baja | Abierto | CP-RNF01-02 (SEC-02) | Ben Farz |
| DEF-A12 | El registro está definido en dos esquemas con reglas distintas | Baja | Baja | Abierto | CP-RF01-07 | Ben Farz |

## Defectos de Ben Farz (Persona A)

### DEF-A01

| Campo | Valor |
|-------|-------|
| Título | Restablecimiento de contraseña sin verificación permite tomar cualquier cuenta |
| Descripción | `POST /api/v1/auth/reset-password` es público y, en modo de autenticación local (sin Supabase configurado), cambia la contraseña de cualquier cuenta con solo la cédula y el correo, sin token, enlace ni código enviado al correo. La pantalla de login ofrece este flujo (`LoginPage.tsx`), y el modo local es el que queda activo si se copia `.env.example` sin llenar Supabase. La cédula y el correo no son secretos, así que cualquier persona que los conozca toma la cuenta |
| Característica 25010 | Seguridad (autenticidad, integridad, resistencia) |
| Severidad | Crítica |
| Prioridad | Alta |
| Pasos para reproducir | 1. Levantar el ambiente QA local. 2. Registrar una cuenta (víctima). 3. Sin token, enviar `POST /auth/reset-password` con la cédula y el correo de la víctima y `new_password` elegida por el atacante. 4. Iniciar sesión con la cédula de la víctima y esa contraseña. 5. Intentar iniciar sesión con la contraseña original |
| Resultado esperado | El restablecimiento exige una prueba de control de la cuenta y, sin ella, la contraseña no cambia (RNF-01, criterio 2) |
| Resultado actual | El paso 3 responde 204, el paso 4 entrega un token y el paso 5 responde 401: la cuenta queda en manos del atacante |
| Evidencia | `test_cp_rnf01_01_reset_sin_verificacion_no_toma_la_cuenta` en `reports/pytest/auth-seguridad.txt`; `tests/auth-seguridad/security/verificaciones.md` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-01 (SEC-01). Hallazgo 27 |

### DEF-A02

| Campo | Valor |
|-------|-------|
| Título | Los errores 500 exponen el traceback y rutas internas |
| Descripción | `app/config.py` define `debug: bool = True` por defecto, `.env.example` trae `DEBUG=true` y FastAPI se crea con `debug=settings.debug`. Cualquier excepción no controlada devuelve el traceback de Python en texto plano, con rutas del servidor y librerías instaladas. Se observó primero en `POST /recommendations/request` con la configuración de Supabase y se reproduce en el ambiente local con `POST /zones` |
| Característica 25010 | Seguridad (confidencialidad) |
| Severidad | Alta |
| Prioridad | Alta |
| Pasos para reproducir | 1. Iniciar sesión con un usuario sintético. 2. Enviar `POST /api/v1/zones` con el cuerpo `{"name": 123}`. 3. Leer el cuerpo de la respuesta |
| Resultado esperado | 500 con un mensaje genérico, sin trazas ni rutas internas (RNF-01, criterio 7) |
| Resultado actual | 500 con `Traceback (most recent call last)`, rutas como `/usr/local/lib/python3.12/site-packages/starlette/...` y el código que falló |
| Evidencia | `test_cp_rnf01_05_error_500_sin_traceback` en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-05 (SEC-05). Hallazgo 14 |

### DEF-A03

| Campo | Valor |
|-------|-------|
| Título | El login no limita los intentos fallidos |
| Descripción | Ningún middleware ni dependencia limita las peticiones al login: no hay espera progresiva, bloqueo temporal ni respuesta 429. Una contraseña se puede adivinar a la velocidad que permita el servidor. Agrava DEF-A01, porque tampoco limita el restablecimiento |
| Característica 25010 | Seguridad (autenticidad, resistencia) |
| Severidad | Alta |
| Prioridad | Alta |
| Pasos para reproducir | 1. Registrar una cuenta. 2. Enviar 30 `POST /auth/login` seguidos con su cédula y contraseñas incorrectas distintas. 3. Iniciar sesión con la contraseña correcta |
| Resultado esperado | Antes del intento 30 aparece una espera, un bloqueo temporal o una respuesta 429 (RNF-01, criterio 8, derivado de OWASP ASVS 4.0, requisito 2.2.1) |
| Resultado actual | Los 30 intentos responden 401, a unos 4 por segundo, y luego la contraseña correcta funciona sin restricción |
| Evidencia | `test_cp_rnf01_06_login_limita_intentos_fallidos` en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-06 (SEC-06). Hallazgo 30 |

### DEF-A04

| Campo | Valor |
|-------|-------|
| Título | Una instalación desde cero falla por enums incompatibles |
| Descripción | `alembic/versions/001_initial_schema.py` crea los tipos `product_category`, `product_status`, `toxic_band`, `recommendation_status`, `audit_action` y `regulationtype` con etiquetas en minúscula. Los modelos usan `SQLEnum` sin `values_callable`, así que escriben el nombre del miembro en mayúscula. En una base creada con las migraciones, el seed y cualquier escritura de productos, recomendaciones o auditoría fallan. La base de Supabase tiene las etiquetas en mayúscula, así que no se creó con estas migraciones |
| Característica 25010 | Flexibilidad (instalabilidad); Mantenibilidad (modificabilidad) |
| Severidad | Alta |
| Prioridad | Media |
| Pasos para reproducir | 1. Crear una base Postgres vacía. 2. Ejecutar `alembic upgrade head` contra ella. 3. Consultar `SELECT enum_range(NULL::regulationtype)`. 4. Ejecutar `SELECT 'DECRETO'::regulationtype`, el valor que escribe el ORM. 5. Alternativamente, correr `python -m app.db.seed` |
| Resultado esperado | Las migraciones crean el mismo esquema que esperan los modelos, y el sistema funciona instalado desde cero |
| Resultado actual | El paso 3 devuelve `{decreto,ley,...}`; el paso 4 falla con `invalid input value for enum regulationtype: "DECRETO"`, el mismo error del seed |
| Evidencia | `reports/manual/def-enums-migraciones.txt`; contorno en `env/align_enums.py` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | Construcción del ambiente QA local (2026-11-26). Hallazgo 26 |

### DEF-A05

| Campo | Valor |
|-------|-------|
| Título | El seed no carga productos porque sus CSV no están en el repo |
| Descripción | `app/db/seed.py` lee `output/plaguicidas.csv`, `output/fertilizantes.csv` y `output/lmr.csv`, pero la carpeta `output/` no existe y el repositorio no versiona ningún CSV. En una instalación nueva el seed termina sin error y sin productos, y el asistente no puede recomendar nada |
| Característica 25010 | Flexibilidad (instalabilidad); Adecuación funcional (completitud) |
| Severidad | Alta |
| Prioridad | Media |
| Pasos para reproducir | 1. Clonar SynapSeed en el commit `ec14b12`. 2. Buscar la carpeta `output/` y los archivos `.csv` versionados (`git ls-files '*.csv'`). 3. Correr el seed en una base nueva y contar los productos |
| Resultado esperado | El repositorio incluye los datos del catálogo, o documenta cómo obtenerlos, y el seed falla con un mensaje claro si faltan |
| Resultado actual | No existe `output/`, hay 0 archivos `.csv` versionados y el seed termina "exitosamente" con 0 productos |
| Evidencia | `reports/manual/def-seed-sin-csv.txt`; contorno en `env/seed_synthetic.py` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | Construcción del ambiente QA local (2026-11-26). Hallazgo 25 |

### DEF-A06

| Campo | Valor |
|-------|-------|
| Título | El bcrypt del login bloquea todo el backend |
| Descripción | `authenticate_user` y `register_user` son funciones `async`, pero llaman a `verify_password` y `get_password_hash` (passlib con bcrypt) de forma síncrona, sin `run_in_threadpool`. Cada login ocupa el event loop unos 250 ms y, mientras tanto, el proceso no atiende ninguna otra petición. Afecta el modo de autenticación local y el respaldo con hash local; en modo Supabase el login es una llamada HTTP asíncrona |
| Característica 25010 | Eficiencia de desempeño (comportamiento temporal, capacidad) |
| Severidad | Alta |
| Prioridad | Media |
| Pasos para reproducir | 1. Medir `GET /catalogs/crops` sin carga. 2. Lanzar 10 hilos que hagan login sin parar. 3. Medir de nuevo `GET /catalogs/crops`, que no usa bcrypt ni token. Automatizado en `tests/auth-seguridad/performance/event_loop_check.py` |
| Resultado esperado | Las lecturas mantienen su tiempo aunque haya logins en curso; p95 de lecturas menor a 500 ms y del login menor a 1000 ms con 20 sesiones (umbrales de RNF-04 en `plan-calidad.md`) |
| Resultado actual | El catálogo pasa de una mediana de 10.4 ms a 2403 ms durante 10 logins, casi 10 x 250 ms. En PERF-01, con 20 usuarios, p95 del login de 5120 ms y de lecturas de 2060 ms |
| Evidencia | `reports/k6/perf-01-diagnostico.txt`, `reports/k6/perf-01.txt`, `tests/auth-seguridad/performance/resultados.md` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF04-01 (PERF-01). Hallazgo 31 |

### DEF-A07

| Campo | Valor |
|-------|-------|
| Título | Con varias personas, las recomendaciones superan los 50 s documentados |
| Descripción | La Spec (línea 201) y `Dockerfile.worker` fijan el worker de Celery con `--concurrency=1`, así que el pipeline procesa una recomendación a la vez y cada solicitud espera a las anteriores. La meta de 10 a 50 s del MVP solo se cumple con una persona. Es una contradicción entre dos decisiones de la Spec más que un error de código |
| Característica 25010 | Eficiencia de desempeño (capacidad, comportamiento temporal) |
| Severidad | Alta |
| Prioridad | Media |
| Pasos para reproducir | 1. Levantar el ambiente QA con `FAKE_LLM_DELAY_MS=3000`. 2. Correr `run_k6.sh recommendation_load.js perf-02-delay-3000`: 10 usuarios piden 2 recomendaciones cada uno. 3. Leer `recommendation_total_ms` |
| Resultado esperado | p95 del tiempo de solicitud a resultado de 50 s o menos (RNF-04, criterio 1) |
| Resultado actual | Una recomendación sola tarda 11 s, pero el p95 es de 94 s y la última llega a los 95 s. Con el LLM real (103 s medidos, hallazgo 21) la décima persona esperaría más de 15 minutos |
| Evidencia | `reports/k6/perf-02-delay-3000.txt` y `.json`; `tests/auth-seguridad/performance/resultados.md` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF04-02 (PERF-02). Hallazgo 32 |

### DEF-A08

| Campo | Valor |
|-------|-------|
| Título | Zonas no valida la entrada: acepta campos extra y responde 500 a tipos incorrectos |
| Descripción | `POST` y `PUT /api/v1/zones` reciben `payload: dict` en lugar de un schema de Pydantic. `clean_payload` copia solo los campos conocidos, así que `user_id` y los campos extra no llegan a la base, pero se aceptan sin aviso. Los tipos no se validan: un nombre numérico falla en `.strip()` y una latitud de texto falla en asyncpg, y ambos terminan en 500 con traceback (ver DEF-A02) |
| Característica 25010 | Seguridad (integridad); Fiabilidad (tolerancia a fallos) |
| Severidad | Media |
| Prioridad | Media |
| Pasos para reproducir | 1. Iniciar sesión. 2. `POST /zones` con una zona válida más `"extra_field": "x"`. 3. `POST /zones` con `"name": 123`. 4. `POST /zones` con `"latitude": "texto"` |
| Resultado esperado | 422 en los tres casos, con el campo que falla (RF-03, criterio 5; RNF-01, criterio 5) |
| Resultado actual | Paso 2: 201. Pasos 3 y 4: 500 con traceback |
| Evidencia | `test_cp_rnf01_04_entrada_invalida_en_zona_se_rechaza` en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-04 (SEC-04). Hallazgo 15 |

### DEF-A09

| Campo | Valor |
|-------|-------|
| Título | El health check responde "ok" con Redis caído |
| Descripción | `GET /api/v1/health` solo verifica la base de datos; Redis y el LLM aparecen siempre como `"pending"`. La Spec lo define como "DB + Redis + LLM API". Con Redis caído el health dice `"ok"`, así que un orquestador o un monitor no detectan que el sistema no puede encolar recomendaciones |
| Característica 25010 | Fiabilidad (disponibilidad); Mantenibilidad (analizabilidad) |
| Severidad | Media |
| Prioridad | Media |
| Pasos para reproducir | 1. Con el ambiente QA arriba, consultar `GET /health` y pedir una recomendación. 2. Detener Redis (`docker compose -f env/docker-compose.qa.yml stop redis`). 3. Repetir ambas peticiones. 4. Volver a levantar Redis |
| Resultado esperado | Con Redis caído, el health check informa `"redis": "error"` y un estado distinto de `"ok"` |
| Resultado actual | El health responde 200 con `"status": "ok"` y `"redis": "pending"` antes, durante y después de la caída, mientras la solicitud de recomendación responde 500 con traceback |
| Evidencia | `reports/manual/def-health-sin-redis.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | Prueba de humo de la API (2026-11-24) y verificación con Redis detenido (2026-11-27). Hallazgo 20 |

### DEF-A10

| Campo | Valor |
|-------|-------|
| Título | El stream de progreso de una recomendación no exige token |
| Descripción | `GET /api/v1/recommendations/stream/{ticket_id}` no usa `get_current_user`: sin token entrega el estado, el paso actual y el mensaje de error de la recomendación de cualquier persona. El `ticket_id` es un UUID y es difícil de adivinar, lo que baja el riesgo, pero es el único endpoint con datos de una persona que no exige autenticación |
| Característica 25010 | Seguridad (confidencialidad) |
| Severidad | Media |
| Prioridad | Baja |
| Pasos para reproducir | 1. Con una sesión, pedir una recomendación y anotar el `ticket_id`. 2. Sin encabezado `Authorization`, consultar `GET /recommendations/stream/{ticket_id}` |
| Resultado esperado | 401 sin token (RNF-01, criterio 1) |
| Resultado actual | 200 con el evento `status` de la recomendación |
| Evidencia | `test_cp_rnf01_03_stream_de_progreso_exige_token` en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-03 (SEC-03). Hallazgo 28 |

### DEF-A11

| Campo | Valor |
|-------|-------|
| Título | Un token inválido responde 503 con detalles de configuración |
| Descripción | En modo de autenticación local, cuando un token no pasa la validación local, `resolve_user_from_token` lo reenvía a la validación de Supabase, que no está configurada. La respuesta es 503 con el mensaje "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configurados". El acceso se niega correctamente, pero el código dice "servicio no disponible" y el mensaje revela la configuración interna |
| Característica 25010 | Seguridad (confidencialidad); Compatibilidad (interoperabilidad) |
| Severidad | Baja |
| Prioridad | Baja |
| Pasos para reproducir | 1. Iniciar sesión y tomar el token. 2. Alterarlo de cualquiera de estas formas: `alg: none`, otro `sub` con la firma original, firma con otro secreto, `abc.def.ghi`. 3. Consultar `GET /users/me` con el token alterado |
| Resultado esperado | 401 "Token inválido o expirado", sin nombres de variables de configuración (RNF-01, criterios 1 y 7) |
| Resultado actual | 503 "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configurados" en los 5 tipos de token |
| Evidencia | `test_cp_rnf01_02_token_manipulado_responde_401` en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RNF01-02 (SEC-02). Hallazgo 29 |

### DEF-A12

| Campo | Valor |
|-------|-------|
| Título | El registro está definido en dos esquemas con reglas distintas |
| Descripción | `app/schemas/auth.py` (`RegisterRequest`: cédula de 5 o más caracteres, contraseña de 6 o más) y `app/schemas/user.py` (`UserRegister`: cédula de 9 a 12 dígitos, contraseña de 8 o más) definen el mismo registro. El router usa `UserRegister`, así que hoy rige la regla más estricta, pero hay dos fuentes de verdad y quien use la otra aceptará datos inválidos |
| Característica 25010 | Mantenibilidad (analizabilidad, modificabilidad) |
| Severidad | Baja |
| Prioridad | Baja |
| Pasos para reproducir | 1. Validar con ambos esquemas una cédula de 5 dígitos, una de 8, una contraseña de 6 caracteres y una de 7. 2. Comparar los resultados |
| Resultado esperado | Una sola definición del registro, o ambas con las mismas reglas |
| Resultado actual | Los 4 valores se aceptan en `RegisterRequest` y se rechazan en `UserRegister` |
| Evidencia | `test_cp_rf01_07_esquemas_de_registro_consistentes` (4 `XFAIL`) en `reports/pytest/auth-seguridad.txt` |
| Estado | Abierto |
| Responsable | Ben Farz |
| Caso de prueba que lo encontró | CP-RF01-07. Hallazgo 17 |
