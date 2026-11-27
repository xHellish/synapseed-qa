# =============================================
# Imports
# ---------------------------------------------
import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.user import UserLogin, UserRegister

# =============================================
# Constantes
# ---------------------------------------------
VALID_REGISTER = {
    "email": "qa.unit@example.com",
    "full_name": "Persona Prueba",
    "identification": "812345678",
    "phone": "88880000",
    "password": "QaUnit-123",
}
REQUIRED_FIELDS = ["email", "full_name", "identification", "phone", "password"]

# Valores limite de la cedula: (valor, se espera aceptado)
IDENTIFICATION_CASES = [
    ("81234567", False),
    ("812345678", True),
    ("812345678901", True),
    ("8123456789012", False),
    ("8-1234-5678", True),
    ("81234567A", False),
    ("", False),
]

# Correos invalidos por particion de equivalencia
INVALID_EMAILS = [
    "sin-arroba.example.com",
    "qa@",
    "qa@dominio",
    "qa @example.com",
    "@example.com",
]

# Entradas limite que deberian tener la misma respuesta en ambos esquemas de registro
CONSISTENCY_CASES = [
    {"identification": "81234"},
    {"identification": "81234567"},
    {"password": "Qa-123"},
    {"password": "Qa-1234"},
]


# =============================================
# Utilidades
# ---------------------------------------------
# Copia los datos validos de registro y aplica los cambios indicados
def register_data_with(changes):
    data = dict(VALID_REGISTER)
    for key, value in changes.items():
        data[key] = value
    return data


# Indica si un esquema acepta los datos sin error de validacion
def schema_accepts(schema, data):
    try:
        schema(**data)
    except ValidationError:
        return False
    return True


# =============================================
# RF-01 Registro
# ---------------------------------------------
# Valores limite y formato de la cedula en el registro (9 a 12 digitos, guiones permitidos)
@pytest.mark.parametrize("identification, expected_valid", IDENTIFICATION_CASES)
def test_cp_rf01_03_cedula_formato_y_limites(identification, expected_valid):
    data = register_data_with({"identification": identification})
    assert schema_accepts(UserRegister, data) == expected_valid


# El mensaje de rechazo de la cedula indica el problema
def test_cp_rf01_03_cedula_mensaje_de_error():
    with pytest.raises(ValidationError) as error_info:
        UserRegister(**register_data_with({"identification": "81234567A"}))
    assert "identification" in str(error_info.value)


# Los guiones de la cedula se eliminan al registrar
def test_cp_rf01_03_cedula_con_guiones_se_normaliza():
    user = UserRegister(**register_data_with({"identification": "8-1234-5678"}))
    assert user.identification == "812345678"


# Correos con formato invalido se rechazan
@pytest.mark.parametrize("email", INVALID_EMAILS)
def test_cp_rf01_04_correo_invalido(email):
    assert schema_accepts(UserRegister, register_data_with({"email": email})) is False


# Cada campo obligatorio ausente provoca rechazo
@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_cp_rf01_06_campo_obligatorio_ausente(missing_field):
    data = dict(VALID_REGISTER)
    del data[missing_field]
    assert schema_accepts(UserRegister, data) is False


# Los dos esquemas de registro del backend deben aplicar las mismas reglas (hallazgo 17)
@pytest.mark.xfail(
    strict=True,
    reason="DEF-A12, hallazgo 17: RegisterRequest y UserRegister definen reglas distintas",
)
@pytest.mark.parametrize("changes", CONSISTENCY_CASES)
def test_cp_rf01_07_esquemas_de_registro_consistentes(changes):
    data = register_data_with(changes)
    assert schema_accepts(RegisterRequest, data) == schema_accepts(UserRegister, data)


# =============================================
# RF-02 Inicio de sesion
# ---------------------------------------------
# El login exige cedula: un correo en el campo de identificacion se rechaza
def test_cp_rf02_04_login_con_correo_se_rechaza():
    data = {"identification": "qa.unit@example.com", "password": "QaUnit-123"}
    assert schema_accepts(UserLogin, data) is False
