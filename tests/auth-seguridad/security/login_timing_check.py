# =============================================
# Verificacion de enumeracion de cuentas por tiempo de respuesta del login
# ---------------------------------------------
# Compara el tiempo del login con contrasena incorrecta para una cedula registrada
# contra el de una cedula inexistente. El mensaje es el mismo (CP-RF02-03), pero si
# los tiempos se separan, una persona puede saber que cedulas tienen cuenta.
# Uso, desde la raiz del repo con el ambiente QA arriba:
#   synapseed\src\backend\.venv\Scripts\python tests/auth-seguridad/security/login_timing_check.py

# =============================================
# Imports
# ---------------------------------------------
import json
import os
import statistics
import time
import urllib.error
import urllib.request

# =============================================
# Constantes
# ---------------------------------------------
BASE_URL = os.environ.get("QA_API_URL", "http://127.0.0.1:8000/api/v1")
SAMPLES = 20
# Usuario sintetico del seed y una cedula que no genera ninguna prueba
REGISTERED_IDENTIFICATION = "900000001"
UNKNOWN_IDENTIFICATION = "500000000"
WRONG_PASSWORD = "Incorrecta-Timing-123"


# =============================================
# Funciones
# ---------------------------------------------
# Hace un login y devuelve codigo, mensaje y milisegundos
def timed_login(identification):
    body = json.dumps(
        {"identification": identification, "password": WRONG_PASSWORD}
    ).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + "/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            detail = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status = error.code
        detail = error.read().decode("utf-8")
    return status, detail, (time.perf_counter() - started) * 1000


# Toma varias muestras alternando las dos cedulas para no sesgar por el orden
def collect_samples():
    registered = []
    unknown = []
    statuses = set()
    details = set()
    for _ in range(SAMPLES):
        status, detail, elapsed = timed_login(REGISTERED_IDENTIFICATION)
        registered.append(elapsed)
        statuses.add(("registered", status))
        details.add(detail)
        status, detail, elapsed = timed_login(UNKNOWN_IDENTIFICATION)
        unknown.append(elapsed)
        statuses.add(("unknown", status))
        details.add(detail)
    return registered, unknown, statuses, details


# Ejecuta la medicion y muestra el resumen
def main():
    registered, unknown, statuses, details = collect_samples()
    print("Samples per case: " + str(SAMPLES))
    print("Status codes: " + str(sorted(statuses)))
    print("Distinct response bodies: " + str(len(details)))
    print(
        "Registered identification, wrong password: median %.0f ms, min %.0f ms, max %.0f ms"
        % (statistics.median(registered), min(registered), max(registered))
    )
    print(
        "Unknown identification: median %.0f ms, min %.0f ms, max %.0f ms"
        % (statistics.median(unknown), min(unknown), max(unknown))
    )
    print(
        "Slowest unknown vs fastest registered: %.0f ms vs %.0f ms"
        % (max(unknown), min(registered))
    )


main()
