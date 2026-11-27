# Verificaciones de seguridad

Responsable: Persona A. Solo contra el ambiente QA local (`env/docker-compose.qa.yml`), nunca contra Supabase, OpenRouter ni Gemini. Cada verificación usa usuarios sintéticos nuevos (cédulas que empiezan en 8) y está automatizada en `test_security.py`. Su caso de prueba es `CP-RNF01-0N` en `docs/casos-prueba/casos-A.md`.

Ejecución: 2026-11-26, con `synapseed\src\backend\.venv\Scripts\python -m pytest tests/auth-seguridad -m security`. Resultado: 10 pruebas pasan y 12 confirman defectos (`XFAIL`). Salida completa en `reports/pytest/auth-seguridad.txt` y `.xml`.

| ID | Verificación | Tipo | Prueba o herramienta | Resultado |
|----|--------------|------|----------------------|-----------|
| SEC-01 | Un tercero sin sesión no puede cambiar la contraseña de otra cuenta | Control de acceso y autenticación (OWASP A07) | `test_cp_rnf01_01_*` | **Falla.** Con solo la cédula y el correo de la víctima, `POST /auth/reset-password` responde 204 y la contraseña queda cambiada: toma de la cuenta (hallazgo 27). El error genérico sí evita revelar si la cuenta existe |
| SEC-02 | Un token manipulado no da acceso | Autenticación (OWASP A07, A02) | `test_cp_rnf01_02_*`, 5 tipos de token | **Pasa con defecto.** Ninguno de los 5 tokens da acceso, pero los 5 se responden con 503 y el mensaje "SUPABASE_URL y SUPABASE_ANON_KEY deben estar configurados" en lugar de 401 (hallazgo 29) |
| SEC-03 | Una persona no accede a los datos de otra (IDOR) | Control de acceso (OWASP A01) | `test_cp_rnf01_03_*` | **Pasa con defecto.** Zonas, recomendaciones, proveedores e historial ajenos responden 404 o vacío, y la zona queda intacta. El stream SSE de progreso no exige token y entrega estado y mensaje de error a quien conozca el `ticket_id` (hallazgo 28) |
| SEC-04 | La entrada de zonas se valida y el texto no se ejecuta en la interfaz | Validación de entrada e inyección (OWASP A03, A04) | `test_cp_rnf01_04_*` | **Falla en parte.** Un campo desconocido se acepta con 201, y un nombre numérico o una latitud de texto provocan 500 en vez de 422 (hallazgo 15). El `user_id` del cuerpo se ignora. El frontend no usa `dangerouslySetInnerHTML` ni `innerHTML`, así que un nombre `<script>` se guarda tal cual pero React lo muestra como texto |
| SEC-05 | Los errores no exponen detalles internos | Configuración de seguridad (OWASP A05) | `test_cp_rnf01_05_error_500_sin_traceback` | **Falla.** Un 500 devuelve el traceback completo de Python con rutas del servidor (hallazgo 14). La causa es `debug: bool = True` por defecto en `app/config.py` |
| SEC-06 | El login limita los intentos fallidos | Autenticación (OWASP A07) | `test_cp_rnf01_06_login_limita_intentos_fallidos` | **Falla.** 30 contraseñas incorrectas seguidas contra la misma cédula responden 401, sin 429 ni bloqueo, a unos 4 intentos por segundo; después la contraseña correcta sigue funcionando (hallazgo 30) |

## Detalle de los ataques

### SEC-01 Restablecimiento de contraseña

1. Se registra una víctima.
2. Sin token, se envía `POST /auth/reset-password` con su cédula, su correo y una contraseña nueva.
3. Se intenta iniciar sesión con la contraseña nueva.

El sistema debería exigir una prueba de control de la cuenta, como un enlace o un código enviado al correo. La pantalla de login del frontend ofrece este flujo (`LoginPage.tsx`), así que cualquier persona usuaria llega a él. El endpoint solo está activo en modo de autenticación local (`APP_ENV=development` sin Supabase). Aun así, es el modo que trae `.env.example` si no se llenan las variables de Supabase.

### SEC-02 Tokens manipulados

| Token | Cómo se arma |
|-------|--------------|
| `alg_none` | Encabezado `{"alg": "none"}`, payload legítimo y sin firma |
| `payload_alterado` | `sub` cambiado a otro usuario, conservando la firma original |
| `secreto_ajeno` | Mismos claims firmados con un secreto que no es el del servidor |
| `vencido` | `exp` en el pasado, firmado con un secreto ajeno |
| `basura` | `abc.def.ghi` |

El token vencido con firma válida no se puede fabricar sin el `JWT_SECRET`, que se genera al azar en cada arranque. La expiración de los tokens legítimos se verifica en `CP-RF02-02`. Cuando la validación local falla, el backend intenta validar el token contra Supabase; sin Supabase configurado, responde 503 con el nombre de las variables.

### SEC-03 Acceso a datos de otra persona

Se crean dos personas: la dueña crea una zona y una recomendación, y la otra intenta leerlas, editarlas y borrarlas con su propio token. También se consulta `GET /recommendations/stream/{ticket_id}` sin token: responde 200 con el estado de la recomendación. El `ticket_id` es un UUID, difícil de adivinar, así que la exposición es baja; aun así es el único endpoint con datos de una persona que no exige token.

### SEC-04 Validación de entrada en zonas

`POST /zones` recibe `payload: dict` sin schema. `clean_payload` copia solo los campos conocidos, así que `user_id` y los campos extra no llegan a la base. Lo que no hay es validación de tipos: `name: 123` falla en `.strip()` y `latitude: "texto"` falla en asyncpg, y ambos terminan en 500 con traceback.

### SEC-05 Detalles internos en errores

Con la configuración por defecto, FastAPI se crea con `debug=True`, y cualquier excepción no controlada devuelve el traceback en texto plano. El ambiente QA no define `DEBUG`, y `.env.example` trae `DEBUG=true`: en los dos casos, cualquier instalación que no cambie ese valor expone los tracebacks.

### SEC-06 Fuerza bruta en el login

Ningún middleware ni dependencia limita peticiones (no hay `slowapi` ni equivalente). El criterio se deriva de OWASP ASVS 4.0, requisito 2.2.1, porque la Spec no lo menciona (ver RNF-01, criterio 8).

## Pendiente

- OWASP ZAP baseline contra `http://127.0.0.1:8000` y `http://127.0.0.1:5173`, con el reporte en `reports/zap/`.
