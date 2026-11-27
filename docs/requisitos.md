# Requerimientos auditados

SynapSeed no trae una lista numerada de requerimientos, así que el equipo los reconstruyó a partir de tres fuentes y los redactó de forma verificable:

| Abreviatura | Fuente |
|-------------|--------|
| Spec | `synapseed/Docs/Spec_validada.md` |
| MVP | `synapseed/README.md`, sección 4.1 Alcance formal del MVP |
| API | Rutas reales en `synapseed/src/backend/app/api/v1/` (commit `ec14b12`) |

Cada criterio de aceptación sale de la documentación, no del comportamiento observado: los resultados esperados de los casos de prueba se toman de aquí. Donde la documentación no define un valor, se indica "no definido" y se reporta en la revisión de requerimientos.

## Requerimientos funcionales

### RF-01 Registro de persona usuaria

**Responsable:** Persona A. **Área de pruebas:** `tests/auth-seguridad`. **Fuente:** Spec 4 y 7, MVP 4.1.

El sistema debe permitir que una persona agricultora cree una cuenta con correo, nombre completo, cédula, teléfono y contraseña (`POST /api/v1/auth/register`).

Criterios de aceptación:

1. Con datos válidos, la cuenta queda creada y la respuesta devuelve el perfil sin la contraseña ni su hash.
2. La cédula es única: un segundo registro con la misma cédula se rechaza.
3. Una cédula con formato inválido (no costarricense) se rechaza con un mensaje que indica el problema.
4. Un correo con formato inválido se rechaza.
5. La contraseña se guarda con bcrypt, nunca en texto plano.
6. Todos los campos son obligatorios; si falta uno, el registro se rechaza.

### RF-02 Inicio de sesión

**Responsable:** Persona A. **Área de pruebas:** `tests/auth-seguridad`. **Fuente:** Spec 4, 5 y 7, MVP 4.1.

El sistema debe autenticar a la persona usuaria con cédula y contraseña, no con correo, y devolver un token JWT (`POST /api/v1/auth/login`).

Criterios de aceptación:

1. Con cédula y contraseña correctas, la respuesta incluye un JWT.
2. El JWT expira según la configuración (24 horas por defecto).
3. Con contraseña incorrecta o cédula inexistente, el inicio de sesión se rechaza con el mismo mensaje en ambos casos.
4. Intentar iniciar sesión con el correo en lugar de la cédula no autentica.
5. Con el JWT recibido se puede consultar el perfil propio (`GET /api/v1/users/me`); sin token, se rechaza.

### RF-03 Gestión de zonas de cultivo

**Responsable:** Persona B. **Área de pruebas:** `tests/zonas-catalogos`. **Fuente:** Spec 4 y 7, MVP 4.1 (flujo de finca).

El sistema debe permitir que la persona usuaria cree, liste, edite y elimine sus zonas o fincas, cada una con nombre, tipo de suelo, humedad, temperatura, calidad del agua y ubicación (`/api/v1/zones`).

Criterios de aceptación:

1. Crear una zona con datos válidos la deja disponible en el listado de la persona usuaria.
2. Editar una zona cambia sus datos guardados; eliminarla la quita del listado.
3. El listado muestra solo las zonas de la persona autenticada.
4. Una persona no puede ver, editar ni eliminar la zona de otra.
5. Los datos de entrada se validan (Spec 5): campos obligatorios ausentes o desconocidos se rechazan.
6. Al seleccionar una zona en el asistente, sus condiciones se precargan y se salta el paso de contexto ambiental.

### RF-04 Catálogos del asistente

**Responsable:** Persona B. **Área de pruebas:** `tests/zonas-catalogos`. **Fuente:** Spec 4 y 7, MVP 4.1 (supporting features).

El sistema debe ofrecer las listas de opciones del asistente (cultivos, etapas, tipos de suelo, problemas, agroquímicos conocidos y rangos de presupuesto) en `/api/v1/catalogs/*`, y el asistente debe usarlas como listas desplegables.

Criterios de aceptación:

1. Cada catálogo responde una lista no vacía.
2. Los problemas vienen categorizados.
3. Todos los campos del asistente son listas desplegables, no campos de texto libre.
4. Los catálogos están disponibles sin datos de la persona usuaria, ya que alimentan el asistente.

### RF-05 Solicitar una recomendación

**Responsable:** Persona C. **Área de pruebas:** `tests/recomendacion`. **Fuente:** Spec 4, 6 y 7, MVP 4.1 (flujo principal).

El sistema debe recibir el contexto del caso (cultivo, etapa, área afectada, suelo, humedad, temperatura, calidad del agua, problema, último agroquímico y presupuesto máximo por litro), procesarlo con el pipeline de 4 agentes y entregar exactamente 3 productos recomendados (`POST /api/v1/recommendations/request`, `GET /api/v1/recommendations/{id}`).

Criterios de aceptación:

1. Una solicitud válida devuelve un identificador de seguimiento sin esperar a que termine el pipeline.
2. El progreso se puede seguir en 4 pasos: analizando, investigando, validando y generando.
3. El resultado contiene exactamente 3 productos con rango 1, 2 y 3.
4. La tabla comparativa muestra ingrediente activo, dosis, precio, toxicidad, método de aplicación e intervalo de seguridad de cada producto.
5. Una solicitud con datos inválidos se rechaza antes de crear el caso.
6. Una persona no puede consultar la recomendación de otra.

### RF-06 Proveedores e historial

**Responsable:** Persona C. **Área de pruebas:** `tests/recomendacion`. **Fuente:** Spec 4 y 7, MVP 4.1 (flujo de historial).

El sistema debe mostrar los proveedores de los productos recomendados (`GET /api/v1/recommendations/{id}/providers`) y el historial de recomendaciones de la persona usuaria (`GET /api/v1/recommendations/history`).

Criterios de aceptación:

1. Cada proveedor muestra nombre, correo, teléfono y ubicación.
2. El botón "Contactar" abre el cliente de correo (`mailto:`) con el correo del proveedor.
3. El historial muestra solo las recomendaciones de la persona autenticada.
4. Desde el historial se puede abrir el detalle de cada recomendación.

## Requerimientos no funcionales

El mínimo exigido es 3 (uno por integrante). RNF-04 y RNF-05 se agregan para que los escenarios de carga y el análisis de Protección queden trazados a un requerimiento.

### RNF-01 Seguridad del acceso y de los datos

**Responsable:** Persona A. **Característica 25010:** Seguridad (confidencialidad, integridad, autenticidad). **Fuente:** Spec 4 y 5.

1. Todo endpoint protegido rechaza peticiones sin token, con token alterado o con token vencido.
2. Ninguna persona puede leer ni modificar zonas, recomendaciones o perfil de otra.
3. Las contraseñas se almacenan con bcrypt.
4. CORS acepta solo el origen del frontend.
5. Las entradas se validan en el backend (Pydantic) y en el frontend (Zod); el texto ingresado no se ejecuta como código en la interfaz.
6. Las llaves y contraseñas viven solo en variables de entorno.
7. Las respuestas de error no exponen detalles internos (rutas, trazas, consultas). Criterio derivado de la confidencialidad; la Spec no lo menciona.
8. El inicio de sesión limita los intentos fallidos seguidos, con espera, bloqueo temporal o respuesta 429. Criterio derivado de OWASP ASVS 4.0, requisito 2.2.1; la Spec no lo menciona.

### RNF-02 Mantenibilidad del código

**Responsable:** Persona B. **Característica 25010:** Mantenibilidad (analizabilidad, modificabilidad, capacidad de ser probado). **Fuente:** Spec 1 y 10, `pyproject.toml`.

1. Cobertura de pruebas del backend mayor o igual a 80%.
2. El código cumple las reglas de Ruff configuradas en el propio proyecto.
3. El backend respeta la separación en capas: routers, servicios, repositorios y modelos.
4. La suite de pruebas del proyecto se ejecuta sin modificar su configuración.

### RNF-03 Fiabilidad del pipeline de recomendación

**Responsable:** Persona C. **Característica 25010:** Fiabilidad (ausencia de fallos, tolerancia a fallos, recuperabilidad). **Fuente:** Spec 6, `CLAUDE.md` de SynapSeed (estados de la recomendación).

1. Toda solicitud termina en `COMPLETED` o `FAILED`; ninguna queda indefinidamente en `PENDING` o `PROCESSING`.
2. Si el pipeline falla, la recomendación pasa a `FAILED` y guarda el mensaje de error.
3. Una recomendación ya completada no se vuelve a procesar (idempotencia).
4. Cada nodo del pipeline actualiza el estado en la base de datos.

### RNF-04 Tiempo de respuesta

**Responsable:** Persona A. **Característica 25010:** Eficiencia de desempeño (comportamiento temporal, capacidad). **Fuente:** MVP 4.1 y README de SynapSeed (sección de polling).

1. El pipeline entrega la recomendación en 10 a 50 segundos.
2. La solicitud HTTP de recomendación responde sin esperar al pipeline.
3. Umbrales de carga para la API: no definidos en la documentación; se declaran en el plan de calidad antes de correr los escenarios.

### RNF-05 Protección de quien aplica el producto

**Responsable:** Persona C. **Característica 25010:** Protección (advertencia de peligro, identificación de riesgos). **Fuente:** Spec 7 (tabla comparativa con toxicidad e intervalo de seguridad), Spec 6 (validador regulatorio).

1. Cada producto recomendado muestra su banda toxicológica y su intervalo de seguridad.
2. Ningún producto recomendado está prohibido por las regulaciones cargadas.
3. Los productos recomendados son pertinentes para el cultivo y el problema indicados.

## Observaciones para la revisión de requerimientos

Diferencias encontradas al reconstruir los requerimientos. La Persona B las clasifica en `revision-requisitos.md` según ISO/IEC/IEEE 29148.

| Tema | Una fuente dice | Otra fuente o el código dice |
|------|-----------------|------------------------------|
| Pasos del asistente | MVP: asistente de 2 pasos | Spec: 4 pasos (zona, contexto ambiental, problema, confirmación) |
| Perfil | MVP: perfil de solo lectura, sin edición | Spec y API: `PUT /users/me` y `PUT /users/me/password` |
| Autenticación | MVP: login vía Supabase Auth | Código: además existe autenticación local con JWT propio |
| Recuperar contraseña | No aparece en Spec ni en MVP | API: `POST /auth/reset-password` público, en modo local |
| Catálogo de agroquímicos | Spec: `GET /catalogs/agrochemicals` | API: no existe; sí existen `humidity`, `temperature`, `water-quality`, `products` y `products/search`, no documentados |
| Detalle de zona | No aparece en la Spec | API: `GET /zones/{zone_id}` |
| Health check | Spec: verifica DB, Redis y API del LLM | API: Redis aparece como `pending` sin verificar (hallazgo 20) |
| Columnas de producto y recomendación | Spec: nombres en inglés y `processing_time_ms` | Base: nombres en español y sin `processing_time_ms` (hallazgos 18 y 24) |
| Reglas de registro | Spec: no define longitud de contraseña ni formato de cédula | Código: dos esquemas con reglas distintas (hallazgo 17) |
| Versiones del stack | Spec: TypeScript ~6 y Vite 8 | `package.json`: TypeScript ~5.7 y Vite 6 |
| Tiempo de respuesta | Solo un rango (10 a 50 s), sin percentil ni carga | Medido: 103 s con una persona (hallazgo 21) |
