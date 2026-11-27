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
| CP-RNF01-01 (SEC-01) | Reset de contraseña sin verificación | RNF-01 (2) | Prueba de ataque: toma de cuenta | Seguridad | Falla (hallazgo 27) |
| CP-RNF01-02 (SEC-02) | Tokens manipulados | RNF-01 (1, 7) | Partición: 5 clases de token inválido | Seguridad | Pasa con defecto (hallazgo 29) |
| CP-RNF01-03 (SEC-03) | Acceso a datos de otra persona | RNF-01 (1, 2) | Prueba de ataque: IDOR con dos cuentas | Seguridad | Pasa con defecto (hallazgo 28) |
| CP-RNF01-04 (SEC-04) | Validación de entrada en zonas | RNF-01 (5) | Partición: campo extra, tipo incorrecto, HTML | Seguridad | Falla (hallazgo 15) |
| CP-RNF01-05 (SEC-05) | Detalles internos en errores | RNF-01 (7) | Adivinación de errores: provocar un 500 | Seguridad | Falla (hallazgo 14) |
| CP-RNF01-06 (SEC-06) | Fuerza bruta en el login | RNF-01 (8) | Prueba de ataque: 30 intentos seguidos | Seguridad | Falla (hallazgo 30) |

Ejecución: 2026-11-26 contra el ambiente QA local (`env/docker-compose.qa.yml`), con `synapseed\src\backend\.venv\Scripts\python -m pytest tests/auth-seguridad`. Resultado: 41 pruebas pasan y 16 fallan como se esperaba (`xfail`): 4 del hallazgo 17 y 12 de las verificaciones de seguridad. El detalle de los ataques está en `tests/auth-seguridad/security/verificaciones.md`.

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

## CP-RNF01-01

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-01 |
| Nombre | Reset de contraseña sin verificación (SEC-01) |
| Objetivo | Verificar que nadie puede cambiar la contraseña de una cuenta ajena sin probar que la controla |
| Requerimiento asociado | RNF-01, criterio 2 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (autenticidad, integridad, resistencia) |
| Precondiciones | Ambiente QA local en modo de autenticación local (sin Supabase); víctima registrada |
| Datos de prueba | Cédula y correo de la víctima; contraseña nueva elegida por el atacante; para el caso negativo, correo que no coincide y cédula inexistente |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_01_reset_sin_verificacion_no_toma_la_cuenta` (xfail), `test_cp_rnf01_01_reset_con_datos_erroneos_no_revela_la_cuenta` (`security/test_security.py`) |
| Resultado esperado | El reset sin prueba de control de la cuenta se rechaza y la contraseña nueva no sirve para iniciar sesión. Con datos que no coinciden, el mismo error genérico para cédula inexistente y correo incorrecto |
| Resultado obtenido | 204: la contraseña cambia y el atacante inicia sesión; la original deja de funcionar. Con datos erróneos, 400 con el mismo mensaje en ambos casos |
| Estado | Falla; confirma el hallazgo 27 |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |

## CP-RNF01-02

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-02 |
| Nombre | Tokens manipulados (SEC-02) |
| Objetivo | Verificar que un token alterado no da acceso y se rechaza como credencial inválida |
| Requerimiento asociado | RNF-01, criterios 1 y 7 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (autenticidad, confidencialidad) |
| Precondiciones | Usuario con un token legítimo |
| Datos de prueba | 5 tokens: `alg: none`, payload con otro `sub` y la firma original, firmado con secreto ajeno, vencido con secreto ajeno, y `abc.def.ghi` |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_02_token_manipulado_no_da_acceso` (5 valores), `test_cp_rnf01_02_token_manipulado_responde_401` (5 valores, xfail) |
| Resultado esperado | `GET /users/me` con cada token: 401, sin datos del perfil ni detalles de configuración |
| Resultado obtenido | Ningún token da acceso, pero los 5 responden 503 "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configurados" |
| Estado | Pasa en el acceso; falla en la respuesta (hallazgo 29) |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |

## CP-RNF01-03

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-03 |
| Nombre | Acceso a datos de otra persona (SEC-03) |
| Objetivo | Verificar que una persona no puede leer ni modificar zonas ni recomendaciones de otra |
| Requerimiento asociado | RNF-01, criterios 1 y 2 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (confidencialidad, integridad) |
| Precondiciones | Dos personas con sesión; la dueña tiene una zona y una recomendación |
| Datos de prueba | Token de la otra persona; IDs de la zona y la recomendación de la dueña; `ticket_id` de la recomendación |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_03_zona_ajena_inaccesible`, `test_cp_rnf01_03_recomendacion_ajena_inaccesible`, `test_cp_rnf01_03_stream_de_progreso_exige_token` (xfail) |
| Resultado esperado | GET, PUT y DELETE de la zona ajena: 404 y la zona intacta. Detalle y proveedores de la recomendación ajena: 404; historial vacío. Stream de progreso sin token: 401 |
| Resultado obtenido | Zonas y recomendaciones protegidas como se esperaba. El stream responde 200 sin token con el estado de la recomendación |
| Estado | Pasa en zonas y recomendaciones; falla en el stream (hallazgo 28) |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |

## CP-RNF01-04

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-04 |
| Nombre | Validación de entrada en zonas (SEC-04) |
| Objetivo | Verificar que la entrada de zonas se valida y que el texto no se ejecuta en la interfaz |
| Requerimiento asociado | RNF-01, criterio 5; RF-03, criterio 5 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Media |
| Característica 25010 que evidencia | Seguridad (integridad); Fiabilidad (tolerancia a fallos) |
| Precondiciones | Dos personas con sesión |
| Datos de prueba | Zona con `user_id` de otra persona; zona con `extra_field`; `name: 123`; `latitude: "texto"`; nombre `<script>alert(1)</script>` |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_04_user_id_del_cuerpo_se_ignora`, `test_cp_rnf01_04_entrada_invalida_en_zona_se_rechaza` (3 valores, xfail), `test_cp_rnf01_04_frontend_no_inserta_html_crudo` |
| Resultado esperado | El `user_id` del cuerpo no asigna la zona a otra persona. Campo desconocido y tipos incorrectos: 422. El frontend no inserta HTML sin escapar |
| Resultado obtenido | El `user_id` se ignora. Campo desconocido: 201. Nombre numérico y latitud de texto: 500 con traceback. El frontend no usa `dangerouslySetInnerHTML` ni `innerHTML` |
| Estado | Falla en la validación (hallazgo 15); pasa en asignación y escape |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |

## CP-RNF01-05

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-05 |
| Nombre | Detalles internos en errores (SEC-05) |
| Objetivo | Verificar que un error del servidor no expone trazas ni rutas internas |
| Requerimiento asociado | RNF-01, criterio 7 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (confidencialidad) |
| Precondiciones | Ambiente QA con la configuración por defecto de `DEBUG` |
| Datos de prueba | `POST /zones` con `name: 123`, que provoca una excepción no controlada |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_05_error_500_sin_traceback` (xfail) |
| Resultado esperado | 500 con un mensaje genérico, sin `Traceback`, rutas de archivos ni `site-packages` |
| Resultado obtenido | 500 con el traceback completo de Python y rutas del servidor |
| Estado | Falla; confirma el hallazgo 14 |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |

## CP-RNF01-06

| Campo | Valor |
|-------|-------|
| ID | CP-RNF01-06 |
| Nombre | Fuerza bruta en el login (SEC-06) |
| Objetivo | Verificar que el login frena los intentos repetidos de adivinar una contraseña |
| Requerimiento asociado | RNF-01, criterio 8 |
| Tipo y nivel de prueba | Seguridad, sistema (API del ambiente QA local) |
| Prioridad | Alta |
| Característica 25010 que evidencia | Seguridad (autenticidad, resistencia) |
| Precondiciones | Usuario registrado |
| Datos de prueba | 30 contraseñas incorrectas seguidas contra la misma cédula |
| Pasos, o nombre de la prueba automatizada | `test_cp_rnf01_06_login_limita_intentos_fallidos` (xfail) |
| Resultado esperado | Antes del intento 30 aparece una respuesta 429 o 423, o un bloqueo temporal |
| Resultado obtenido | Los 30 intentos responden 401, unos 4 por segundo; después la contraseña correcta sigue funcionando |
| Estado | Falla; nuevo hallazgo 30 |
| Evidencia | Corrida de pytest del 2026-11-26; detalle en `tests/auth-seguridad/security/verificaciones.md` |
| Responsable | Persona A |
