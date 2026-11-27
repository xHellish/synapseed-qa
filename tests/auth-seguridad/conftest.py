# =============================================
# Imports
# ---------------------------------------------
import base64
import json
import os
import random
import urllib.error
import urllib.request

import psycopg2
import pytest

# =============================================
# Constantes
# ---------------------------------------------
# Base del ambiente QA local; credenciales desechables definidas en env/docker-compose.qa.yml
DEFAULT_DB_URL = "postgresql://qa:qa@127.0.0.1:5433/synapseed_qa"
REQUEST_TIMEOUT_SECONDS = 30
# Las cedulas de prueba empiezan en 8 para no chocar con los usuarios del seed (9000000xx)
TEST_ID_PREFIX = "8"


# =============================================
# Cliente HTTP
# ---------------------------------------------
# Respuesta simplificada: codigo, cuerpo como dict (o texto) y encabezados
class ApiResponse:
    def __init__(self, status, body, headers):
        self.status = status
        self.body = body
        self.headers = headers


# Cliente minimo sobre urllib para llamar a la API bajo prueba
class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    # Envia una peticion JSON y devuelve un ApiResponse, sin lanzar en codigos 4xx o 5xx
    def call(self, method, path, body=None, token=None):
        # Se arman encabezados y cuerpo
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=headers, method=method
        )

        # Se ejecuta la peticion; los errores HTTP tambien son respuestas validas para las pruebas
        try:
            with urllib.request.urlopen(
                request, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                return ApiResponse(
                    response.status, parse_body(response.read()), dict(response.headers)
                )
        except urllib.error.HTTPError as error:
            return ApiResponse(
                error.code, parse_body(error.read()), dict(error.headers)
            )


# Convierte el cuerpo a dict si es JSON; si no, lo deja como texto
def parse_body(raw):
    text = raw.decode("utf-8")
    if len(text) == 0:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# =============================================
# Utilidades
# ---------------------------------------------
# Decodifica el payload de un JWT sin verificar la firma (solo para leer sus claims)
def decode_jwt_payload(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token is not a JWT with 3 segments: " + str(len(parts)))
    payload = parts[1]
    # Se completa el relleno de base64url que el JWT omite
    padding = "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload + padding))


# Genera una cedula sintetica de 9 digitos que no pertenece a nadie
def new_identification():
    digits = TEST_ID_PREFIX
    for _ in range(8):
        digits = digits + str(random.randint(0, 9))
    return digits


# Arma los datos de un registro valido con valores sinteticos
def new_user_data():
    identification = new_identification()
    return {
        "email": "qa.a." + identification + "@example.com",
        "full_name": "Persona Prueba " + identification,
        "identification": identification,
        "phone": "88880000",
        "password": "QaPrueba-" + identification,
    }


# =============================================
# Fixtures
# ---------------------------------------------
# Cliente para la API del ambiente QA; salta la prueba si el ambiente no esta arriba
@pytest.fixture(scope="session")
def api(api_base_url):
    client = ApiClient(api_base_url)
    try:
        health = client.call("GET", "/health")
    except urllib.error.URLError as error:
        pytest.skip(
            "QA environment is not reachable at "
            + api_base_url
            + ": "
            + str(error.reason)
        )
    if health.status != 200:
        pytest.skip("QA environment health check returned " + str(health.status))
    return client


# Conexion a la base del ambiente QA, configurable con QA_DB_URL
@pytest.fixture(scope="session")
def qa_db():
    connection = psycopg2.connect(os.environ.get("QA_DB_URL", DEFAULT_DB_URL))
    yield connection
    connection.close()


# Datos de un usuario nuevo, todavia sin registrar
@pytest.fixture
def user_data():
    return new_user_data()


# Fabrica de datos de registro, para pruebas que necesitan mas de un usuario
@pytest.fixture
def make_user_data():
    return new_user_data


# Fabrica de cedulas sinteticas que no pertenecen a nadie
@pytest.fixture
def make_identification():
    return new_identification


# Lector de los claims de un JWT
@pytest.fixture
def jwt_payload():
    return decode_jwt_payload


# Usuario recien registrado: devuelve los datos con los que se creo
@pytest.fixture
def registered_user(api, user_data):
    response = api.call("POST", "/auth/register", user_data)
    if response.status != 201:
        raise RuntimeError(
            "Could not register test user: "
            + str(response.status)
            + " "
            + str(response.body)
        )
    return user_data


# Token de acceso del usuario recien registrado
@pytest.fixture
def user_token(api, registered_user):
    credentials = {
        "identification": registered_user["identification"],
        "password": registered_user["password"],
    }
    response = api.call("POST", "/auth/login", credentials)
    if response.status != 200:
        raise RuntimeError(
            "Could not log in test user: "
            + str(response.status)
            + " "
            + str(response.body)
        )
    return response.body["access_token"]
