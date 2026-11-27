# =============================================
# Imports
# ---------------------------------------------
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.services.auth_service import _is_unconfigured

# =============================================
# Constantes
# ---------------------------------------------
REPO_DIR = Path(__file__).resolve().parents[3]
ENV_EXAMPLE_PATH = REPO_DIR / "synapseed" / ".env.example"
EXPECTED_EXPIRATION_SECONDS = 24 * 3600
PASSWORD = "QaUnit-Clave-123"
# Secretos publicos: el valor por defecto de app/config.py y el de .env.example
PUBLIC_DEFAULT_SECRETS = [
    "change-me-in-production",
    "change-me-in-production-please-use-a-long-random-string",
]


# =============================================
# Utilidades
# ---------------------------------------------
# Lee el valor de una variable en .env.example (archivo publico del repositorio)
def read_env_example(name):
    for line in ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise KeyError("Variable not found in .env.example: " + name)


# Configuracion limpia: sin variables del sistema que cambien los valores por defecto
@pytest.fixture
def clean_settings(monkeypatch):
    for name in ["JWT_SECRET", "JWT_EXPIRE_HOURS", "APP_ENV"]:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# =============================================
# RF-01 Registro
# ---------------------------------------------
# El hash de la contrasena es bcrypt y solo verifica con la contrasena correcta
def test_cp_rf01_05_hash_bcrypt_y_verificacion():
    password_hash = get_password_hash(PASSWORD)

    assert password_hash.startswith("$2b$")
    assert password_hash != PASSWORD
    assert verify_password(PASSWORD, password_hash) is True
    assert verify_password("Otra-Clave-123", password_hash) is False


# =============================================
# RF-02 Inicio de sesion
# ---------------------------------------------
# El token local expira 24 horas despues de emitido
def test_cp_rf02_02_token_expira_segun_configuracion(clean_settings):
    payload = decode_access_token(create_access_token(subject="1"))

    assert payload["sub"] == "1"
    assert payload["exp"] - payload["iat"] == EXPECTED_EXPIRATION_SECONDS


# Un token legitimo pero vencido se rechaza con 401
def test_cp_rf02_02_token_vencido_se_rechaza(clean_settings):
    expired_token = create_access_token(
        subject="1", expires_delta=timedelta(minutes=-1)
    )

    with pytest.raises(HTTPException) as error_info:
        decode_access_token(expired_token)

    assert error_info.value.status_code == 401


# =============================================
# RNF-01 Seguridad
# ---------------------------------------------
# Un token firmado con otro secreto se rechaza con 401
def test_cp_rnf01_02_token_con_secreto_ajeno_se_rechaza(clean_settings):
    forged_token = jwt.encode(
        {"sub": "1"}, "secreto-que-no-es-del-servidor", algorithm="HS256"
    )

    with pytest.raises(HTTPException) as error_info:
        decode_access_token(forged_token)

    assert error_info.value.status_code == 401


# Los valores de ejemplo de Supabase en .env.example activan la autenticacion local (precondicion de DEF-A01)
def test_cp_rnf01_01_env_example_activa_autenticacion_local():
    assert _is_unconfigured(read_env_example("SUPABASE_URL")) is True
    assert _is_unconfigured(read_env_example("SUPABASE_ANON_KEY")) is True
    assert read_env_example("APP_ENV") == "development"


# Con el secreto por defecto, un token fabricado por cualquiera es valido (mecanismo de DEF-A13)
def test_cp_rnf01_07_secreto_por_defecto_permite_fabricar_tokens(clean_settings):
    forged_token = jwt.encode(
        {"sub": "1"}, PUBLIC_DEFAULT_SECRETS[0], algorithm="HS256"
    )

    payload = decode_access_token(forged_token)

    assert payload["sub"] == "1"


# La configuracion de produccion rechaza un secreto JWT publico (hallazgo 33)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A13, hallazgo 33: el backend arranca en produccion con un JWT_SECRET publico",
)
@pytest.mark.parametrize(
    "public_secret", PUBLIC_DEFAULT_SECRETS, ids=["config_py", "env_example"]
)
def test_cp_rnf01_07_produccion_rechaza_secreto_publico(clean_settings, public_secret):
    with pytest.raises(ValueError):
        Settings(app_env="production", jwt_secret=public_secret)
