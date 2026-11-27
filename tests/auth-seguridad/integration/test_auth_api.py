# =============================================
# Constantes
# ---------------------------------------------
SENSITIVE_FIELDS = ["password", "password_hash", "hashed_password"]
EXPECTED_EXPIRATION_SECONDS = 24 * 3600


# =============================================
# Utilidades
# ---------------------------------------------
# Devuelve los campos sensibles presentes en un dict de perfil
def sensitive_fields_in(profile):
    found = []
    for field in SENSITIVE_FIELDS:
        if field in profile:
            found.append(field)
    return found


# =============================================
# RF-01 Registro
# ---------------------------------------------
# Registro con datos validos: 201 y perfil sin contrasena ni hash
def test_cp_rf01_01_registro_valido(api, user_data):
    response = api.call("POST", "/auth/register", user_data)

    assert response.status == 201, response.body
    assert response.body["identification"] == user_data["identification"]
    assert response.body["email"] == user_data["email"]
    assert sensitive_fields_in(response.body) == []


# Un segundo registro con la misma cedula se rechaza
def test_cp_rf01_02_cedula_duplicada(api, registered_user, make_user_data):
    duplicate = make_user_data()
    duplicate["identification"] = registered_user["identification"]

    response = api.call("POST", "/auth/register", duplicate)

    assert response.status == 409, response.body
    assert "cédula" in response.body["detail"].lower()


# Una cedula invalida se rechaza en la API y el mensaje senala el campo
def test_cp_rf01_03_cedula_invalida_en_api(api, user_data):
    user_data["identification"] = "81234567"

    response = api.call("POST", "/auth/register", user_data)

    assert response.status == 422, response.body
    assert "identification" in str(response.body)


# Un correo invalido se rechaza en la API
def test_cp_rf01_04_correo_invalido_en_api(api, user_data):
    user_data["email"] = "qa-sin-arroba.example.com"

    response = api.call("POST", "/auth/register", user_data)

    assert response.status == 422, response.body


# La contrasena queda guardada como hash bcrypt, nunca en texto plano
def test_cp_rf01_05_contrasena_guardada_con_bcrypt(api, qa_db, registered_user):
    with qa_db.cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE identification = %s",
            (registered_user["identification"],),
        )
        row = cursor.fetchone()
    qa_db.rollback()

    assert row is not None, "User was not stored"
    password_hash = row[0]
    assert password_hash != registered_user["password"]
    assert password_hash.startswith("$2b$") or password_hash.startswith("$2a$")


# Un registro sin uno de los campos obligatorios se rechaza
def test_cp_rf01_06_campo_obligatorio_ausente_en_api(api, user_data):
    del user_data["phone"]

    response = api.call("POST", "/auth/register", user_data)

    assert response.status == 422, response.body


# =============================================
# RF-02 Inicio de sesion
# ---------------------------------------------
# Login con cedula y contrasena correctas: 200 con un JWT
def test_cp_rf02_01_login_valido(api, registered_user):
    credentials = {
        "identification": registered_user["identification"],
        "password": registered_user["password"],
    }

    response = api.call("POST", "/auth/login", credentials)

    assert response.status == 200, response.body
    assert response.body["token_type"] == "bearer"
    assert len(response.body["access_token"].split(".")) == 3
    assert sensitive_fields_in(response.body["user"]) == []


# El JWT expira 24 horas despues de emitido (valor por defecto)
def test_cp_rf02_02_expiracion_del_jwt(api, registered_user, jwt_payload):
    credentials = {
        "identification": registered_user["identification"],
        "password": registered_user["password"],
    }

    response = api.call("POST", "/auth/login", credentials)
    payload = jwt_payload(response.body["access_token"])

    assert payload["exp"] - payload["iat"] == EXPECTED_EXPIRATION_SECONDS
    assert response.body["expires_in"] == EXPECTED_EXPIRATION_SECONDS


# Contrasena incorrecta y cedula inexistente dan el mismo rechazo
def test_cp_rf02_03_mismo_rechazo_para_contrasena_y_cedula(
    api, registered_user, make_identification
):
    wrong_password = {
        "identification": registered_user["identification"],
        "password": "Incorrecta-123",
    }
    unknown_user = {
        "identification": make_identification(),
        "password": "Incorrecta-123",
    }

    by_password = api.call("POST", "/auth/login", wrong_password)
    by_identification = api.call("POST", "/auth/login", unknown_user)

    assert by_password.status == 401, by_password.body
    assert by_identification.status == 401, by_identification.body
    assert by_password.body["detail"] == by_identification.body["detail"]


# Usar el correo en lugar de la cedula no autentica
def test_cp_rf02_04_login_con_correo_no_autentica(api, registered_user):
    credentials = {
        "identification": registered_user["email"],
        "password": registered_user["password"],
    }

    response = api.call("POST", "/auth/login", credentials)

    assert response.status in (401, 422), response.body
    assert "access_token" not in str(response.body)


# Con el JWT se consulta el perfil propio; sin token se rechaza
def test_cp_rf02_05_perfil_propio_con_y_sin_token(api, registered_user, user_token):
    with_token = api.call("GET", "/users/me", token=user_token)
    without_token = api.call("GET", "/users/me")

    assert with_token.status == 200, with_token.body
    assert with_token.body["identification"] == registered_user["identification"]
    assert sensitive_fields_in(with_token.body) == []
    assert without_token.status == 401, without_token.body
