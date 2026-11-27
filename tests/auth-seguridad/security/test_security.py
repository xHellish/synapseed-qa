# =============================================
# Imports
# ---------------------------------------------
import base64
import json
import time
from pathlib import Path

import pytest
from jose import jwt

# =============================================
# Constantes
# ---------------------------------------------
REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC_DIR = REPO_DIR / "synapseed" / "src" / "frontend" / "src"
FRONTEND_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx"]
RAW_HTML_PATTERNS = [
    "dangerouslySetInnerHTML",
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
]
TRACEBACK_MARKERS = ["Traceback", 'File "/', "site-packages"]
BRUTE_FORCE_ATTEMPTS = 30
TAKEOVER_PASSWORD = "Tomada-QA-123456"

VALID_ZONE = {
    "name": "Finca de prueba",
    "soil_type": "Franco",
    "humidity": "Media",
    "temperature": "20°C - 25°C",
    "water_quality": "Buena",
    "location": "Cartago",
}
VALID_RECOMMENDATION = {
    "crop": "Tomate",
    "crop_stage": "Floración",
    "problem_to_solve": "Plagas",
    "soil_type": "Franco",
    "humidity": "Media",
    "temperature": 24,
    "water_quality": "Buena",
    "max_budget_per_liter": 15000,
}


# =============================================
# Utilidades
# ---------------------------------------------
# Codifica un dict como segmento base64url de un JWT
def encode_segment(data):
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# Arma los tokens manipulados a partir de un token legitimo
def build_tampered_tokens(valid_token, claims):
    header, _payload, signature = valid_token.split(".")

    # Otro usuario en el payload, conservando la firma original
    other_claims = dict(claims)
    other_claims["sub"] = str(int(claims["sub"]) + 1)

    # Token vencido firmado con un secreto que no es el del servidor
    expired_claims = dict(claims)
    expired_claims["exp"] = int(time.time()) - 3600

    return {
        "alg_none": encode_segment({"alg": "none", "typ": "JWT"})
        + "."
        + encode_segment(claims)
        + ".",
        "payload_alterado": header
        + "."
        + encode_segment(other_claims)
        + "."
        + signature,
        "secreto_ajeno": jwt.encode(
            claims, "secreto-que-no-es-del-servidor", algorithm="HS256"
        ),
        "vencido": jwt.encode(
            expired_claims, "secreto-que-no-es-del-servidor", algorithm="HS256"
        ),
        "basura": "abc.def.ghi",
    }


# Busca en el codigo del frontend los patrones que insertan HTML sin escapar
def find_raw_html_usages():
    found = []
    for path in FRONTEND_SRC_DIR.rglob("*"):
        if path.suffix not in FRONTEND_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in RAW_HTML_PATTERNS:
            if pattern in text:
                found.append(str(path.relative_to(REPO_DIR)) + ": " + pattern)
    return found


# Indica si un cuerpo de respuesta contiene rastros de un traceback de Python
def has_traceback(body):
    text = str(body)
    for marker in TRACEBACK_MARKERS:
        if marker in text:
            return True
    return False


# =============================================
# SEC-01 Restablecimiento de contrasena
# ---------------------------------------------
# Un tercero sin sesion no debe poder cambiar la contrasena de otra cuenta (hallazgo 27)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A01, hallazgo 27: reset-password cambia la contrasena con solo cedula y correo",
)
def test_cp_rnf01_01_reset_sin_verificacion_no_toma_la_cuenta(api, make_session):
    victim = make_session()
    reset = {
        "identification": victim["identification"],
        "email": victim["email"],
        "new_password": TAKEOVER_PASSWORD,
    }

    # El atacante solo conoce cedula y correo de la victima; no envia token
    response = api.call("POST", "/auth/reset-password", reset)
    takeover_login = api.call(
        "POST",
        "/auth/login",
        {"identification": victim["identification"], "password": TAKEOVER_PASSWORD},
    )

    assert (
        response.status != 204
    ), "Password was changed without proof of account ownership"
    assert takeover_login.status == 401


# Con datos que no coinciden, el reset responde un error generico que no revela la cuenta
def test_cp_rnf01_01_reset_con_datos_erroneos_no_revela_la_cuenta(
    api, make_session, make_identification
):
    victim = make_session()
    wrong_email = {
        "identification": victim["identification"],
        "email": "otra.persona@example.com",
        "new_password": TAKEOVER_PASSWORD,
    }
    unknown_user = {
        "identification": make_identification(),
        "email": "otra.persona@example.com",
        "new_password": TAKEOVER_PASSWORD,
    }

    by_email = api.call("POST", "/auth/reset-password", wrong_email)
    by_identification = api.call("POST", "/auth/reset-password", unknown_user)

    assert by_email.status == 400, by_email.body
    assert by_identification.status == 400, by_identification.body
    assert by_email.body == by_identification.body


# =============================================
# SEC-02 Tokens manipulados
# ---------------------------------------------
# Ningun token manipulado da acceso al perfil
@pytest.mark.parametrize(
    "token_kind", ["alg_none", "payload_alterado", "secreto_ajeno", "vencido", "basura"]
)
def test_cp_rnf01_02_token_manipulado_no_da_acceso(
    api, make_session, jwt_payload, token_kind
):
    user = make_session()
    tampered = build_tampered_tokens(user["token"], jwt_payload(user["token"]))

    response = api.call("GET", "/users/me", token=tampered[token_kind])

    assert response.status != 200, response.body
    assert "identification" not in str(response.body)


# Un token manipulado se rechaza con 401 y sin detalles de configuracion (hallazgo 29)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A11, hallazgo 29: los tokens invalidos responden 503 con detalle de configuracion",
)
@pytest.mark.parametrize(
    "token_kind", ["alg_none", "payload_alterado", "secreto_ajeno", "vencido", "basura"]
)
def test_cp_rnf01_02_token_manipulado_responde_401(
    api, make_session, jwt_payload, token_kind
):
    user = make_session()
    tampered = build_tampered_tokens(user["token"], jwt_payload(user["token"]))

    response = api.call("GET", "/users/me", token=tampered[token_kind])

    assert response.status == 401, response.body
    assert "SUPABASE" not in str(response.body)


# =============================================
# SEC-03 Acceso a datos de otra persona
# ---------------------------------------------
# Una persona no puede ver, editar ni eliminar la zona de otra, y la zona queda intacta
def test_cp_rnf01_03_zona_ajena_inaccesible(api, make_session):
    owner = make_session()
    attacker = make_session()
    created = api.call("POST", "/zones", VALID_ZONE, token=owner["token"])
    zone_path = "/zones/" + str(created.body["id"])

    read = api.call("GET", zone_path, token=attacker["token"])
    edit = api.call("PUT", zone_path, {"name": "Zona tomada"}, token=attacker["token"])
    delete = api.call("DELETE", zone_path, token=attacker["token"])
    listing = api.call("GET", "/zones", token=attacker["token"])
    after = api.call("GET", zone_path, token=owner["token"])

    assert read.status == 404
    assert edit.status == 404
    assert delete.status == 404
    assert listing.body == []
    assert after.status == 200
    assert after.body["name"] == VALID_ZONE["name"]


# Una persona no puede consultar la recomendacion, los proveedores ni el historial de otra
def test_cp_rnf01_03_recomendacion_ajena_inaccesible(api, make_session):
    owner = make_session()
    attacker = make_session()
    created = api.call(
        "POST", "/recommendations/request", VALID_RECOMMENDATION, token=owner["token"]
    )
    recommendation_path = "/recommendations/" + str(created.body["recommendation_id"])

    detail = api.call("GET", recommendation_path, token=attacker["token"])
    providers = api.call(
        "GET", recommendation_path + "/providers", token=attacker["token"]
    )
    history = api.call("GET", "/recommendations/history", token=attacker["token"])

    assert detail.status == 404
    assert providers.status == 404
    assert history.status == 200
    assert history.body == []


# El stream de progreso exige autenticacion (hallazgo 28)
@pytest.mark.xfail(
    strict=True, reason="DEF-A10, hallazgo 28: el stream SSE de progreso no exige token"
)
def test_cp_rnf01_03_stream_de_progreso_exige_token(api, make_session):
    owner = make_session()
    created = api.call(
        "POST", "/recommendations/request", VALID_RECOMMENDATION, token=owner["token"]
    )
    time.sleep(4)

    response = api.call("GET", "/recommendations/stream/" + created.body["ticket_id"])

    assert response.status == 401, response.body


# =============================================
# SEC-04 Validacion de entrada en zonas
# ---------------------------------------------
# El user_id enviado en el cuerpo no asigna la zona a otra persona
def test_cp_rnf01_04_user_id_del_cuerpo_se_ignora(api, make_session):
    victim = make_session()
    attacker = make_session()
    victim_profile = api.call("GET", "/users/me", token=victim["token"])
    payload = dict(VALID_ZONE)
    payload["name"] = "Zona plantada"
    payload["user_id"] = victim_profile.body["id"]

    api.call("POST", "/zones", payload, token=attacker["token"])
    victim_zones = api.call("GET", "/zones", token=victim["token"])
    attacker_zones = api.call("GET", "/zones", token=attacker["token"])

    assert "Zona plantada" not in json.dumps(victim_zones.body)
    assert "Zona plantada" in json.dumps(attacker_zones.body)


# Campos desconocidos y tipos incorrectos se rechazan con 422 (hallazgo 15)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A08, hallazgo 15: zonas recibe un dict sin schema y acepta cualquier campo",
)
@pytest.mark.parametrize(
    "changes",
    [{"extra_field": "x"}, {"name": 123}, {"latitude": "texto"}],
    ids=["campo_desconocido", "nombre_numerico", "latitud_texto"],
)
def test_cp_rnf01_04_entrada_invalida_en_zona_se_rechaza(api, make_session, changes):
    user = make_session()
    payload = dict(VALID_ZONE)
    for key, value in changes.items():
        payload[key] = value

    response = api.call("POST", "/zones", payload, token=user["token"])

    assert response.status == 422, str(response.status) + " " + str(response.body)[:200]


# El frontend no inserta HTML sin escapar, asi un nombre con <script> no se ejecuta
def test_cp_rnf01_04_frontend_no_inserta_html_crudo():
    assert FRONTEND_SRC_DIR.exists(), "Frontend source not found: " + str(
        FRONTEND_SRC_DIR
    )
    assert find_raw_html_usages() == []


# =============================================
# SEC-05 Detalles internos en errores
# ---------------------------------------------
# Un error 500 no expone el traceback ni rutas internas (hallazgo 14)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A02, hallazgo 14: DEBUG=True por defecto devuelve el traceback en los 500",
)
def test_cp_rnf01_05_error_500_sin_traceback(api, make_session):
    user = make_session()
    payload = dict(VALID_ZONE)
    payload["name"] = 123

    response = api.call("POST", "/zones", payload, token=user["token"])

    assert response.status == 500, (
        "The payload no longer triggers a server error: " + str(response.status)
    )
    assert has_traceback(response.body) is False


# =============================================
# SEC-06 Fuerza bruta en el login
# ---------------------------------------------
# Tras muchos intentos fallidos seguidos, el login limita o bloquea (hallazgo 30)
@pytest.mark.xfail(
    strict=True, reason="DEF-A03, hallazgo 30: el login no limita los intentos fallidos"
)
def test_cp_rnf01_06_login_limita_intentos_fallidos(api, make_session):
    victim = make_session()
    statuses = []

    # Se prueban contrasenas incorrectas seguidas contra la misma cedula
    for attempt in range(BRUTE_FORCE_ATTEMPTS):
        credentials = {
            "identification": victim["identification"],
            "password": "Incorrecta-" + str(attempt).zfill(4),
        }
        statuses.append(api.call("POST", "/auth/login", credentials).status)

    assert 429 in statuses or 423 in statuses, "All attempts answered: " + str(
        sorted(set(statuses))
    )
