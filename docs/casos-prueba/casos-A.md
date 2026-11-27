# Casos de prueba - Persona A

Cada requerimiento lleva casos de camino feliz, negativos o de error, y de frontera o no funcionales. El resultado esperado se escribe antes de ejecutar. ID: `CP-RFxx-nn` o `CP-RNFxx-nn`. Si el caso está automatizado, el nombre de la prueba empieza con el ID (por ejemplo `test_cp_rf01_01_...`).

Los resultados esperados salen de los criterios de aceptación de `docs/requisitos.md`. Donde la documentación dice "se rechaza" sin fijar un código HTTP, el caso usa el código que define la propia API (409 para duplicados, 422 para validación, 401 para credenciales) y lo indica.

## Resumen

| ID | Nombre | Requerimiento | Técnica de diseño | Nivel | Estado |
|----|--------|---------------|-------------------|-------|--------|
| CP-RF01-01 | Registro con datos válidos | RF-01 (1) | Partición de equivalencia, clase válida | Integración | Pasa |
| CP-RF01-02 | Registro con cédula duplicada | RF-01 (2) | Partición de equivalencia, clase inválida | Integración | Pasa |
| CP-RF01-03 | Formato y límites de la cédula | RF-01 (3) | Valores límite y partición | Unitaria e integración | Pasa |
| CP-RF01-04 | Correo con formato inválido | RF-01 (4) | Partición de equivalencia, clases inválidas | Unitaria e integración | Pasa |
| CP-RF01-05 | Contraseña almacenada con bcrypt | RF-01 (5), RNF-01 (3) | Verificación de efecto en base de datos | Integración | Pasa |
| CP-RF01-06 | Campo obligatorio ausente | RF-01 (6) | Partición, un campo inválido por caso | Unitaria e integración | Pasa |
| CP-RF01-07 | Reglas de registro consistentes | RF-01 (3, 6) | Valores límite comparados entre esquemas | Unitaria | Falla (hallazgo 17) |
| CP-RF02-01 | Login con credenciales válidas | RF-02 (1) | Partición de equivalencia, clase válida | Integración | Pasa |
| CP-RF02-02 | Expiración del JWT | RF-02 (2) | Verificación de valor configurado | Integración | Pasa |
| CP-RF02-03 | Mismo rechazo para contraseña y cédula | RF-02 (3) | Partición, dos clases inválidas comparadas | Integración | Pasa |
| CP-RF02-04 | Login con correo en vez de cédula | RF-02 (4) | Partición de equivalencia, clase inválida | Unitaria e integración | Pasa |
| CP-RF02-05 | Perfil propio con y sin token | RF-02 (5), RNF-01 (1) | Partición: con token y sin token | Integración | Pasa |

Ejecución: 2026-11-26 contra el ambiente QA local (`env/docker-compose.qa.yml`), con `synapseed\src\backend\.venv\Scripts\python -m pytest tests/auth-seguridad`. Resultado: 31 pruebas pasan y 4 fallan como se esperaba (`xfail`, hallazgo 17).

Las pruebas que confirman un defecto conocido se marcan con `@pytest.mark.xfail(strict=True, reason="Hallazgo N ...")`: la suite queda en verde, el defecto queda visible en el reporte como `XFAIL` y, si alguien lo corrige, la prueba pasa a `XPASS` y la suite falla para que se quite la marca.

## CP-RF01-01

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-01 |
| Nombre | Registro con datos válidos |
| Objetivo | Verificar que una persona puede crear su cuenta y que la respuesta no expone la contraseña |
| Requerimiento asociado | RF-01, criterio 1 |
| Tipo y nivel de prueba | Funcional, integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional); Seguridad (confidencialidad) |
| Precondiciones | Ambiente QA local arriba; la cédula de prueba no existe |
| Datos de prueba | Correo `qa.a.<cédula>@example.com`, nombre "Persona Prueba", cédula sintética de 9 dígitos que empieza en 8, teléfono `88880000`, contraseña de 18 caracteres |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_01_registro_valido` (`tests/auth-seguridad/integration/test_auth_api.py`) |
| Resultado esperado | 201; el cuerpo trae la cédula y el correo enviados y no trae `password`, `password_hash` ni `hashed_password` |
| Resultado obtenido | 201 con el perfil; ningún campo sensible en la respuesta |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-02

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-02 |
| Nombre | Registro con cédula duplicada |
| Objetivo | Verificar que la cédula es única |
| Requerimiento asociado | RF-01, criterio 2 |
| Tipo y nivel de prueba | Funcional negativa, integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional); Seguridad (integridad) |
| Precondiciones | Existe un usuario registrado con la cédula X |
| Datos de prueba | Un segundo registro con la cédula X y correo, nombre y contraseña distintos |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_02_cedula_duplicada` |
| Resultado esperado | Rechazo (la API define 409) con un mensaje que menciona la cédula |
| Resultado obtenido | 409, "La cédula ya está registrada" |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-03

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-03 |
| Nombre | Formato y límites de la cédula |
| Objetivo | Verificar que solo se acepta una cédula costarricense y que el rechazo indica el campo |
| Requerimiento asociado | RF-01, criterio 3 |
| Tipo y nivel de prueba | Funcional de frontera; unitaria (esquema `UserRegister`) e integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional) |
| Precondiciones | Ninguna para la unitaria; ambiente QA arriba para la de integración |
| Datos de prueba | Valores límite: 8 dígitos (rechazo), 9 (acepta), 12 (acepta), 13 (rechazo). Partición: con guiones `8-1234-5678` (acepta y se normaliza a `812345678`), con letra `81234567A` (rechazo), vacía (rechazo) |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_03_cedula_formato_y_limites` (7 valores), `test_cp_rf01_03_cedula_mensaje_de_error`, `test_cp_rf01_03_cedula_con_guiones_se_normaliza` (`unit/test_auth_schemas.py`); `test_cp_rf01_03_cedula_invalida_en_api` (`integration/test_auth_api.py`) |
| Resultado esperado | Se aceptan de 9 a 12 dígitos y se rechaza el resto; el error nombra el campo `identification`. La regla de 9 a 12 dígitos viene del código, porque la Spec no define el formato (ver observaciones de `requisitos.md`) |
| Resultado obtenido | Los 7 valores se comportan como se esperaba; la API responde 422 y el detalle nombra `identification` |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-04

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-04 |
| Nombre | Correo con formato inválido |
| Objetivo | Verificar que el registro rechaza correos mal formados |
| Requerimiento asociado | RF-01, criterio 4 |
| Tipo y nivel de prueba | Funcional negativa; unitaria e integración (API) |
| Prioridad | Media |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional) |
| Precondiciones | Ninguna para la unitaria; ambiente QA arriba para la de integración |
| Datos de prueba | Clases inválidas: sin arroba, sin dominio (`qa@`), dominio sin punto (`qa@dominio`), con espacio, sin usuario (`@example.com`) |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_04_correo_invalido` (5 valores), `test_cp_rf01_04_correo_invalido_en_api` |
| Resultado esperado | Rechazo de las 5 clases; la API responde 422 |
| Resultado obtenido | Las 5 se rechazan; la API responde 422 |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-05

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-05 |
| Nombre | Contraseña almacenada con bcrypt |
| Objetivo | Verificar que la contraseña nunca queda en texto plano en la base de datos |
| Requerimiento asociado | RF-01, criterio 5; RNF-01, criterio 3 |
| Tipo y nivel de prueba | Seguridad, integración (API más consulta a la base) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (confidencialidad) |
| Precondiciones | Usuario recién registrado en el ambiente QA local; acceso de lectura a la base local (`127.0.0.1:5433`) |
| Datos de prueba | El usuario de prueba y su contraseña |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_05_contrasena_guardada_con_bcrypt` |
| Resultado esperado | `users.password_hash` es distinto de la contraseña y tiene el prefijo de bcrypt (`$2b$` o `$2a$`) |
| Resultado obtenido | Hash con prefijo `$2b$` |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-06

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-06 |
| Nombre | Campo obligatorio ausente |
| Objetivo | Verificar que los 5 campos del registro son obligatorios |
| Requerimiento asociado | RF-01, criterio 6 |
| Tipo y nivel de prueba | Funcional negativa; unitaria e integración (API) |
| Prioridad | Media |
| Característica 25010 que evidencia | Adecuación funcional (completitud funcional) |
| Precondiciones | Ninguna para la unitaria; ambiente QA arriba para la de integración |
| Datos de prueba | Registro válido al que se le quita un campo por vez: correo, nombre, cédula, teléfono, contraseña |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_06_campo_obligatorio_ausente` (5 valores), `test_cp_rf01_06_campo_obligatorio_ausente_en_api` (sin teléfono) |
| Resultado esperado | Rechazo en los 5 casos; la API responde 422 |
| Resultado obtenido | Rechazo en los 5 casos; la API responde 422 |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF01-07

| Campo | Valor |
|-------|-------|
| ID | CP-RF01-07 |
| Nombre | Reglas de registro consistentes |
| Objetivo | Verificar que el backend aplica una sola regla de validación al registro |
| Requerimiento asociado | RF-01, criterios 3 y 6 |
| Tipo y nivel de prueba | Funcional de frontera, unitaria (comparación de `RegisterRequest` contra `UserRegister`) |
| Prioridad | Media |
| Característica 25010 que evidencia | Mantenibilidad (analizabilidad, modificabilidad); Adecuación funcional (corrección funcional) |
| Precondiciones | Ninguna |
| Datos de prueba | Cédula de 5 y de 8 dígitos; contraseña de 6 y de 7 caracteres |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf01_07_esquemas_de_registro_consistentes` (4 valores, marcada `xfail` estricta) |
| Resultado esperado | Ambos esquemas aceptan o rechazan los mismos datos |
| Resultado obtenido | Los 4 valores se aceptan en `app/schemas/auth.py` (`RegisterRequest`: cédula de 5 o más, contraseña de 6 o más) y se rechazan en `app/schemas/user.py` (`UserRegister`: cédula de 9 a 12 dígitos, contraseña de 8 o más). El router usa `UserRegister`, así que hoy rige la regla más estricta, pero la duplicación deja dos fuentes de verdad |
| Estado | Falla; confirma el hallazgo 17 |
| Evidencia | Corrida de pytest del 2026-11-26 (4 `XFAIL`) |
| Responsable | Persona A |

## CP-RF02-01

| Campo | Valor |
|-------|-------|
| ID | CP-RF02-01 |
| Nombre | Login con credenciales válidas |
| Objetivo | Verificar que el login con cédula y contraseña entrega un JWT |
| Requerimiento asociado | RF-02, criterio 1 |
| Tipo y nivel de prueba | Funcional, integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional); Seguridad (autenticidad) |
| Precondiciones | Usuario registrado |
| Datos de prueba | Cédula y contraseña del usuario de prueba |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf02_01_login_valido` |
| Resultado esperado | 200; `token_type` `bearer`; `access_token` con forma de JWT (3 segmentos); el usuario de la respuesta sin campos sensibles |
| Resultado obtenido | 200 con JWT de 3 segmentos y usuario sin campos sensibles |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF02-02

| Campo | Valor |
|-------|-------|
| ID | CP-RF02-02 |
| Nombre | Expiración del JWT |
| Objetivo | Verificar que el token expira en el plazo configurado |
| Requerimiento asociado | RF-02, criterio 2 |
| Tipo y nivel de prueba | Seguridad, integración (API) |
| Prioridad | Media |
| Característica 25010 que evidencia | Seguridad (autenticidad) |
| Precondiciones | Usuario registrado; `JWT_EXPIRE_HOURS` con su valor por defecto |
| Datos de prueba | Token recibido en el login |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf02_02_expiracion_del_jwt` (lee los claims del token sin verificar la firma) |
| Resultado esperado | `exp - iat` igual a 86400 s (24 horas) y `expires_in` igual a 86400 |
| Resultado obtenido | 86400 en ambos |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF02-03

| Campo | Valor |
|-------|-------|
| ID | CP-RF02-03 |
| Nombre | Mismo rechazo para contraseña incorrecta y cédula inexistente |
| Objetivo | Verificar que el login no revela si una cédula está registrada |
| Requerimiento asociado | RF-02, criterio 3 |
| Tipo y nivel de prueba | Seguridad negativa, integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (confidencialidad) |
| Precondiciones | Usuario registrado |
| Datos de prueba | Cédula existente con contraseña incorrecta; cédula sintética inexistente |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf02_03_mismo_rechazo_para_contrasena_y_cedula` |
| Resultado esperado | Ambos rechazados (la API define 401) con el mismo mensaje |
| Resultado obtenido | 401 en ambos, "Cédula o contraseña incorrectos" |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF02-04

| Campo | Valor |
|-------|-------|
| ID | CP-RF02-04 |
| Nombre | Login con correo en vez de cédula |
| Objetivo | Verificar que el login es solo por cédula |
| Requerimiento asociado | RF-02, criterio 4 |
| Tipo y nivel de prueba | Funcional negativa; unitaria (esquema `UserLogin`) e integración (API) |
| Prioridad | Media |
| Característica 25010 que evidencia | Adecuación funcional (corrección funcional) |
| Precondiciones | Usuario registrado (para la de integración) |
| Datos de prueba | El correo del usuario en el campo `identification`, con su contraseña correcta |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf02_04_login_con_correo_se_rechaza` (unitaria), `test_cp_rf02_04_login_con_correo_no_autentica` (integración) |
| Resultado esperado | No se entrega token (401 o 422) |
| Resultado obtenido | 422 sin token |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |

## CP-RF02-05

| Campo | Valor |
|-------|-------|
| ID | CP-RF02-05 |
| Nombre | Perfil propio con y sin token |
| Objetivo | Verificar que el JWT da acceso al perfil propio y que sin token se niega |
| Requerimiento asociado | RF-02, criterio 5; RNF-01, criterio 1 |
| Tipo y nivel de prueba | Funcional y seguridad, integración (API) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (autenticidad, confidencialidad) |
| Precondiciones | Usuario registrado con sesión iniciada |
| Datos de prueba | Token del login; petición sin encabezado `Authorization` |
| Pasos, o nombre de la prueba automatizada | `test_cp_rf02_05_perfil_propio_con_y_sin_token` |
| Resultado esperado | Con token: 200 con la cédula del usuario y sin campos sensibles. Sin token: 401 |
| Resultado obtenido | 200 con el perfil propio; 401 sin token |
| Estado | Pasa |
| Evidencia | Corrida de pytest del 2026-11-26 |
| Responsable | Persona A |
