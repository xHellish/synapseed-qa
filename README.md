# SynapSeed QA

Auditoría de calidad de SynapSeed para el curso IC-6831 Aseguramiento de la Calidad del Software (TEC), basada en el modelo ISO/IEC 25010:2023. Este repo guarda todo el trabajo del equipo auditor: ambiente de pruebas, pruebas de todos los niveles y tipos, reportes de herramientas y documentación de la auditoría. El sistema auditado vive en el submódulo `synapseed/`, fijado en el commit `ec14b12`.

## ¿Cómo lo corro en mi máquina?

1. Clonar el repo junto con el submódulo:

   ```bash
   git clone --recurse-submodules https://github.com/xHellish/synapseed-qa.git
   cd synapseed-qa
   ```

   Si ya estaba clonado sin el submódulo:

   ```bash
   git submodule update --init
   ```

2. Pruebas del backend de SynapSeed (requiere [uv](https://docs.astral.sh/uv/)):

   ```bash
   cd synapseed/src/backend
   uv venv --python 3.12
   uv pip install -e ".[dev]"
   ```

   Ejecutar desde `synapseed/src/backend` (en Linux o macOS cambiar `.venv\Scripts\python` por `.venv/bin/python`):

   ```bash
   .venv\Scripts\python -m pytest --cov=app --cov-report=term -o "filterwarnings=ignore::DeprecationWarning"
   ```

   La opción `-o "filterwarnings=..."` es necesaria porque, sin ella, la suite no llega a ejecutarse (ver `docs/verificacion-inicial.md`). Sin base de datos ni Redis fallan 4 de las 22 pruebas.

3. Pruebas, lint y tipos del frontend de SynapSeed (requiere Node 22):

   ```bash
   cd synapseed/src/frontend
   npm install
   npm test
   npm run lint
   npm run typecheck
   ```

4. Levantar SynapSeed con su configuración original (Supabase, OpenRouter y Gemini). Requiere Docker, ya sea Docker Desktop o Docker Engine dentro de WSL, y el archivo `synapseed/.env` descrito en la sección siguiente. Desde la raíz de este repo:

   ```bash
   docker compose -f synapseed/docker-compose.yml -f env/docker-compose.kombu-fix.yml up -d --build
   docker compose -f synapseed/docker-compose.yml exec backend python -m app.db.seed
   ```

   `env/docker-compose.kombu-fix.yml` es necesario: sin él, el worker no arranca (ver Decision Log). La aplicación queda en http://localhost:5173 y la documentación de la API en http://localhost:8000/docs.

   Esta configuración solo sirve para exploración manual y pruebas funcionales: usa servicios de terceros, así que no se usa para pruebas de seguridad ni de carga.

5. Levantar el **ambiente QA local**, el único donde se permiten pruebas de seguridad y de carga. No usa Supabase, OpenRouter ni Gemini, y no necesita `.env`. Desde la raíz de este repo:

   ```bash
   docker compose -f env/docker-compose.qa.yml up -d --build
   docker compose -f env/docker-compose.qa.yml exec backend python seed_synthetic.py
   ```

   Usa los mismos puertos que el paso 4 (http://localhost:5173 y http://localhost:8000), así que hay que bajar uno antes de levantar el otro con `docker compose -f <archivo> down`. Para empezar con la base vacía: `docker compose -f env/docker-compose.qa.yml down -v`.

   | Pieza | Qué hace |
   |-------|----------|
   | `db` | Postgres 16 con pgvector, desechable. Para revisar efectos de lado: `localhost:5433`, base `synapseed_qa`, usuario y contraseña `qa` |
   | `fake-llm` (`env/fake_llm/server.py`) | Imita la API de OpenRouter y arma las respuestas de los 4 agentes con los datos del formulario. Una recomendación tarda unos 2 s |
   | `backend` y `worker` | El código del submódulo sin cambios, con autenticación local (sin Supabase) y un `JWT_SECRET` aleatorio en cada arranque |
   | `env/align_enums.py` | Corre después de las migraciones y deja los enums de la base igual que en Supabase (ver hallazgo 26) |
   | `env/seed_synthetic.py` | Regulaciones del SFE, 3 distribuidores y 147 productos inventados, y 2 usuarios de prueba con una zona cada uno |

   Datos para las pruebas:

   - Usuarios de prueba: cédulas `900000001` y `900000002`. Las contraseñas están en `env/seed_synthetic.py`.
   - Hay 3 productos activos por cada cultivo y problema de los catálogos. Además hay 3 casos especiales para Tomate y Papa: un producto con ingrediente prohibido (`QA-PROHIBIDO-1`), uno con registro cancelado (`QA-CANCELADO-1`) y uno sin datos de seguridad (`QA-INCOMPLETO-1`).
   - Para pruebas de fiabilidad, si el problema contiene `QA_FORCE_LLM_ERROR` el LLM falso responde 500, y si contiene `QA_FORCE_INVALID_JSON` responde texto que no es JSON.
   - Para pruebas de carga, `FAKE_LLM_DELAY_MS=3000 docker compose -f env/docker-compose.qa.yml up -d --force-recreate fake-llm` agrega latencia simulada al LLM. Para quitarla, el mismo comando con `FAKE_LLM_DELAY_MS=0`; sin `--force-recreate` el contenedor puede quedar con el valor anterior.

   Si Docker está instalado dentro de WSL y no como Docker Desktop, el comando `docker` no existe en PowerShell: los comandos de este paso se corren en una terminal de Ubuntu, donde el disco `E:` se ve como `/mnt/e`:

   ```bash
   cd "/mnt/e/Escritorio/Proyecto Integrado QA/synapseed-qa"
   docker compose -f env/docker-compose.qa.yml up -d
   docker compose -f env/docker-compose.qa.yml ps
   ```

   La distro se apaga sola si no hay ninguna terminal de WSL abierta, y los contenedores se detienen con ella. Mientras prueban, dejen abierta esa terminal de Ubuntu. Los datos del seed se conservan entre reinicios; solo hay que volver a cargarlos después de un `down -v`.

6. Pruebas del equipo QA. Las de Python usan el entorno del submódulo creado en el paso 2 y se corren desde la raíz de este repo:

   ```bash
   synapseed\src\backend\.venv\Scripts\python -m pytest
   ```

   Variantes útiles:

   | Qué correr | Comando (agregar al anterior) |
   |------------|-------------------------------|
   | Solo un tipo | `-m unit`, `-m integration` o `-m security` |
   | Solo un área | `tests/zonas-catalogos` |
   | Con cobertura | `--cov=synapseed/src/backend/app --cov-report=html:reports/coverage` |
   | Guardando evidencia | `tests/<área> -v -rxX --junitxml=reports/pytest/<área>.xml > reports/pytest/<área>.txt` |

   Las pruebas de integración necesitan el ambiente QA local del paso 5; si no está arriba, se saltan. Las que confirman un defecto conocido aparecen como `XFAIL`, no como fallo (ver Documentation).

   Las E2E (Playwright) se corren desde `tests/`; la primera vez hay que instalar el navegador:

   ```bash
   cd tests
   npm install
   npx playwright install chromium
   npx playwright test
   ```

   El reporte HTML queda en `reports/e2e/html`. Para correr solo un área: `npx playwright test recomendacion`. Las URLs del ambiente se cambian con `QA_API_URL` y `QA_WEB_URL`.

   Las pruebas de carga (k6) se corren desde una terminal de WSL en la raíz del repo, con el ambiente QA arriba. El script usa la imagen `grafana/k6` y deja la salida y el resumen en `reports/k6/`:

   ```bash
   bash tests/auth-seguridad/performance/run_k6.sh auth_read_load.js perf-01
   bash tests/auth-seguridad/performance/run_k6.sh recommendation_load.js perf-02-rampa-delay-0
   ```

   Las colecciones de Postman se corren con Postman CLI desde la raíz, con el ambiente QA arriba; no hace falta iniciar sesión para correrlas localmente:

   ```bash
   postman collection run tests/auth-seguridad/api/auth-seguridad.postman_collection.json > reports/postman/auth-seguridad.txt
   ```

   Si una aserción falla, el comando termina con código 1; las que confirman un defecto conocido llevan su ID en el nombre (por ejemplo `DEF-A01: ...`).

   El escaneo pasivo de OWASP ZAP se corre igual, desde WSL; el script solo acepta URLs del ambiente QA local y deja los reportes en `reports/zap/`:

   ```bash
   bash tests/auth-seguridad/security/run_zap.sh http://127.0.0.1:5173 zap-frontend
   bash tests/auth-seguridad/security/run_zap.sh http://127.0.0.1:8000/docs zap-api
   ```

## Organización del trabajo

Las pruebas están separadas por área funcional; cada área tiene un dueño, que solo hace commit dentro de su carpeta. En la columna Responsable de casos, defectos y matriz va el nombre de cada integrante, que es la base de la nota individual.

| Área | Responsable | Requerimientos | Subcarpetas |
|------|-------------|----------------|-------------|
| `tests/auth-seguridad/` | Persona A: Ben Farz | RF-01, RF-02, RNF-01, RNF-04 | `unit`, `integration`, `e2e`, `api`, `security`, `performance` |
| `tests/zonas-catalogos/` | Persona B: Kevin Alanis | RF-03, RF-04, RNF-02 | `unit`, `integration`, `e2e`, `api` |
| `tests/recomendacion/` | Persona C: Josué Calderón | RF-05, RF-06, RNF-03, RNF-05 | `unit`, `integration`, `e2e`, `api` |

Convenciones:

- Los archivos compartidos (`tests/conftest.py`, `pytest.ini`, `tests/playwright.config.js`) se cambian solo avisando al equipo.
- El nombre de cada prueba automatizada empieza con el ID de su caso, por ejemplo `test_cp_rf03_02_zona_sin_nombre`, para enlazarla en la matriz de trazabilidad.
- Las colecciones de Postman van una por área en su carpeta `api/`.
- Los documentos están en `docs/`; cada persona escribe sus casos en `docs/casos-prueba/casos-<A|B|C>.md`. En `defectos.md`, `matriz-trazabilidad.md` e `informe-final.md` cada quien edita solo sus filas o su sección. Los defectos usan IDs por persona (`DEF-A01`, `DEF-B01`, `DEF-C01`) y las escalas de severidad y prioridad definidas al inicio de `defectos.md`.
- La evidencia de cada corrida va a `reports/`. Lo que se verifica a mano (por ejemplo, detener un servicio y observar la respuesta) se guarda como texto en `reports/manual/`.

## Variables de entorno

Las variables van en `synapseed/.env`, que se crea copiando `synapseed/.env.example` y nunca se versiona. Estas son las que hay que llenar; el resto puede quedar con el valor de la plantilla.

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Conexión async a Supabase por el **Session pooler** (puerto 5432); con el Transaction pooler el pipeline falla | `postgresql+asyncpg://postgres.<ref>:<contraseña>@aws-1-us-east-1.pooler.supabase.com:5432/postgres` |
| `DATABASE_URL_SYNC` | Conexión sync para Alembic, por el Transaction pooler | `postgresql+psycopg2://postgres.<ref>:<contraseña>@aws-1-us-east-1.pooler.supabase.com:6543/postgres` |
| `SUPABASE_URL` | URL del proyecto de Supabase | `https://<ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | Publishable key del proyecto (Settings, API Keys) | `sb_publishable_...` |
| `JWT_SECRET` | Cadena aleatoria para firmar tokens locales | Salida de `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `OPENROUTER_API_KEY` | Llave del LLM de chat, con límite de crédito | `sk-or-...` |
| `GEMINI_API_KEY` | Llave de Google AI Studio para embeddings | `AQ....` |

## Stack

- **Sistema auditado**: SynapSeed - FastAPI (Python 3.12), React 19 + Vite, Celery + Redis, Postgres + pgvector, pipeline de agentes con LangGraph
- **Pruebas del backend**: pytest, pytest-cov, Ruff
- **Pruebas del frontend**: Vitest, ESLint, TypeScript (`tsc`)
- **Pruebas E2E**: Playwright (JavaScript)
- **Pruebas de API**: Postman CLI
- **Carga, seguridad y análisis estático**: k6, OWASP ZAP y SonarQube, corridos como imágenes de Docker
- **Ambiente QA local**: Docker Compose con Postgres 16 + pgvector, Redis 7 y un LLM falso escrito con la librería estándar de Python
- **Control de versiones**: Git con SynapSeed como submódulo
